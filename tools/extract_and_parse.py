#!/usr/bin/env python3
"""
Extract and parse OMNIcheck final inspection PDFs into a structured dataset.

Handles two PDF types:
- Text-based PDFs (manually created, ~11 files) → direct text extraction via PyMuPDF
- Image-based PDFs (OMNIcheck software exports, ~52 files) → OCR via tesseract at 600 DPI

Outputs: data/inspections.json and data/inspections.csv
"""

import pymupdf
import subprocess
import tempfile
import os
import re
import json
import csv
import glob
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = Path.home() / "Desktop" / "Final QA REPORTS"
DATA_DIR = PROJECT_DIR / "data"

# Unit prefix → configuration type mapping
PREFIX_CONFIG = {
    "OCS": "MSA Firetech",
    "OCSA": "MSA Firetech",
    "OCA": "AVON",
    "OCB": "ATOR Labs",
}


def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF, using OCR if needed."""
    doc = pymupdf.open(pdf_path)
    page = doc[0]
    text = page.get_text().strip()

    if len(text) > 100:
        return text  # Text-based PDF

    # Image-based PDF — OCR with tesseract
    pix = page.get_pixmap(dpi=600)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        pix.save(tmp.name)
        result = subprocess.run(
            ["tesseract", tmp.name, "-", "--psm", "4", "--oem", "3"],
            capture_output=True, text=True,
        )
        os.unlink(tmp.name)
    return result.stdout


def parse_unit_id_from_filename(filename: str) -> str:
    """Extract unit ID from PDF filename."""
    base = Path(filename).stem
    base = base.replace(" CALSHEET", "")
    m = re.match(r"^(.+?)(?:_\d+_Prod QA)?$", base)
    return m.group(1) if m else base


def get_config_type(unit_id: str) -> str:
    """Derive configuration type from unit ID prefix."""
    # Handle legacy format
    if unit_id.startswith("OC-"):
        return "MSA Firetech"  # default assumption for legacy

    # Extract prefix: everything between the date and the number
    m = re.match(r"\d{8}(OCS|OCSA|OCA|OCB)\d+", unit_id)
    if m:
        return PREFIX_CONFIG.get(m.group(1), "Unknown")
    return "Unknown"


def parse_text_based(text: str) -> dict:
    """Parse text extracted from a text-based PDF (columnar newline-separated)."""
    lines = text.split("\n")
    record = {}

    # Metadata: labels appear before values in the Basic Inspection Data section
    # Pattern: labels block, then values block
    try:
        tech_idx = lines.index("Technician Name")
        # Values are 4 lines after the 4 labels
        record["technician"] = lines[tech_idx + 4].strip()
        record["config_type"] = lines[tech_idx + 5].strip()
        record["date_performed"] = lines[tech_idx + 6].strip()
        record["unit_id"] = lines[tech_idx + 7].strip()
    except (ValueError, IndexError):
        # Try alternate: labels and values might be interleaved
        for i, line in enumerate(lines):
            if "Technician Name" in line and i + 1 < len(lines):
                # Check if value is on same line or next
                rest = line.replace("Technician Name", "").strip()
                if rest:
                    record["technician"] = rest
            if "Configuration Type" in line:
                rest = line.replace("Configuration Type", "").strip()
                if rest:
                    record["config_type"] = rest
            if "Date Performed" in line:
                rest = line.replace("Date Performed", "").strip()
                if rest:
                    record["date_performed"] = rest
            if "OMNICHECK ID" in line:
                rest = line.replace("OMNICHECK ID", "").strip()
                if rest:
                    record["unit_id"] = rest

    # WOB Results: find "Result (kPa)" header, then 8 values
    try:
        ri = lines.index("Result (kPa)")
        wob_results = []
        for j in range(ri + 1, min(ri + 9, len(lines))):
            val = lines[j].strip()
            try:
                wob_results.append(float(val))
            except ValueError:
                break
        if len(wob_results) == 8:
            record["wob_A_10"] = wob_results[0]
            record["wob_A_20"] = wob_results[1]
            record["wob_A_35"] = wob_results[2]
            record["wob_A_50"] = wob_results[3]
            record["wob_A_65"] = wob_results[4]
            record["wob_B_65"] = wob_results[5]
            record["wob_B_85"] = wob_results[6]
            record["wob_B_105"] = wob_results[7]
    except ValueError:
        pass

    # Leak test: find negative pressure values (inWg) — exclude sensor ranges like "-14to14"
    leak_vals = re.findall(r"(-\d+\.\d+)\s*\(inWg\)", text)
    if len(leak_vals) >= 2:
        record["leak_start"] = float(leak_vals[0])
        record["leak_end"] = float(leak_vals[1])
        record["leak_delta"] = abs(float(leak_vals[0])) - abs(float(leak_vals[1]))

    # Volume: text-based PDFs extract columns separately.
    # "Avg Vol (L)" header appears, then the two volume values follow on subsequent lines.
    for i, line in enumerate(lines):
        if "Avg Vol" in line:
            # Grab next two numeric values
            vals = []
            for j in range(i + 1, min(i + 6, len(lines))):
                try:
                    vals.append(float(lines[j].strip()))
                except ValueError:
                    continue
                if len(vals) == 2:
                    break
            if len(vals) >= 2:
                record["vol_nfpa40"] = vals[0]
                record["vol_nfpa102"] = vals[1]
            break

    return record


def parse_ocr_text(text: str) -> dict:
    """Parse text from OCR'd image-based PDF (all on lines with mixed fields)."""
    record = {}
    lines = text.split("\n")

    # Metadata
    for line in lines:
        if "Technician Name" in line:
            m = re.search(r"Technician Name\s+(.+?)(?:\s+Pass|\s*$)", line)
            if m:
                record["technician"] = m.group(1).strip()
        if "Configuration Type" in line:
            m = re.search(r"Configuration Type\s+(.+)", line)
            if m:
                record["config_type"] = m.group(1).strip()
        if "Date Performed" in line:
            m = re.search(r"Date Performed\s+(\d+/\d+/\d+)", line)
            if m:
                record["date_performed"] = m.group(1)
        if "OMNICHECK ID" in line or "OMNICHECK" in line:
            m = re.search(r"(?:OMNICHECK ID|OMNICHECK)\s+(\d{8}\w+|OC-\S+)", line)
            if m:
                record["unit_id"] = m.group(1)

    # Leak test pressures — OCR often mangles these values:
    #   "-9 99 (inWg)" instead of "-9.99", "_9 98" instead of "-9.98", etc.
    # Strategy: find the line with "60 Sec" (the leak test row), extract pressure-like values
    for line in lines:
        if "60" in line and "Sec" in line and "Pass" in line and "inW" in line:
            # Extract all values that look like pressures before "60 Sec"
            before_sec = line.split("60")[0] if "60" in line else line
            # Find patterns: optional minus/underscore, digits, optional space/dot, digits, followed by (inW...)
            pressure_matches = re.findall(
                r"[-_]?\d+[.\s]\d+\s*\(?inW[a-z]?\)?", before_sec
            )
            cleaned = []
            for pm in pressure_matches:
                # Extract just the numeric part, fix OCR artifacts
                num = re.search(r"([-_]?\d+[.\s]\d+)", pm)
                if num:
                    val_str = num.group(1).replace(" ", ".").replace("_", "-")
                    # Ensure it starts with minus (leak pressures are negative)
                    if not val_str.startswith("-"):
                        val_str = "-" + val_str
                    try:
                        cleaned.append(float(val_str))
                    except ValueError:
                        pass
            if len(cleaned) >= 2:
                record["leak_start"] = cleaned[0]
                record["leak_end"] = cleaned[1]
                record["leak_delta"] = abs(cleaned[0]) - abs(cleaned[1])
            elif len(cleaned) == 1:
                # Try to find second value with looser pattern
                all_neg = re.findall(r"(-\d+\.\d+)", before_sec)
                if len(all_neg) >= 2:
                    record["leak_start"] = float(all_neg[0])
                    record["leak_end"] = float(all_neg[1])
                    record["leak_delta"] = abs(float(all_neg[0])) - abs(float(all_neg[1]))
            break

    # WOB results: extract from lines containing (A) or (B) protocol markers
    # OCR format: "RMV  limit (A/B)  result  Pass"
    wob_a = []
    wob_b = []
    for line in lines:
        # Match lines with protocol markers and result values
        # Pattern: ... (A) followed by a decimal result, then Pass
        m_a = re.findall(r"\(A\)\s+([\d.]+)\s+Pass", line)
        m_b = re.findall(r"\(B\)\s+([\d.]+)\s+Pass", line)
        for val in m_a:
            try:
                wob_a.append(float(val))
            except ValueError:
                pass
        for val in m_b:
            try:
                wob_b.append(float(val))
            except ValueError:
                pass

    if len(wob_a) == 5 and len(wob_b) == 3:
        record["wob_A_10"] = wob_a[0]
        record["wob_A_20"] = wob_a[1]
        record["wob_A_35"] = wob_a[2]
        record["wob_A_50"] = wob_a[3]
        record["wob_A_65"] = wob_a[4]
        record["wob_B_65"] = wob_b[0]
        record["wob_B_85"] = wob_b[1]
        record["wob_B_105"] = wob_b[2]

    # Volume
    for line in lines:
        m40 = re.search(r"NFPA\s*40\s+([\d.]+)", line)
        m102 = re.search(r"NFPA\s*102\s+([\d.]+)", line)
        if m40:
            record["vol_nfpa40"] = float(m40.group(1))
        if m102:
            record["vol_nfpa102"] = float(m102.group(1))

    return record


def parse_report(pdf_path: str) -> dict:
    """Extract and parse a single PDF report."""
    text = extract_text(pdf_path)
    doc = pymupdf.open(pdf_path)
    is_text_based = len(doc[0].get_text().strip()) > 100

    if is_text_based:
        record = parse_text_based(text)
    else:
        record = parse_ocr_text(text)

    # Ensure unit_id from filename as fallback
    fname_unit = parse_unit_id_from_filename(pdf_path)
    if "unit_id" not in record or not record["unit_id"]:
        record["unit_id"] = fname_unit
    record["filename"] = Path(pdf_path).name
    record["source"] = "text" if is_text_based else "ocr"

    # Derive config type from unit ID if not extracted
    if "config_type" not in record or not record["config_type"]:
        record["config_type"] = get_config_type(record.get("unit_id", fname_unit))

    # Normalize technician name — clean OCR artifacts
    tech = record.get("technician", "")
    tech = re.sub(r"[|'\"]", "", tech).strip()       # remove pipes, quotes
    tech = re.sub(r"\s+rs$", "", tech)                # trailing "rs" OCR artifact
    tech = re.sub(r"\s+", " ", tech)                  # collapse multiple spaces
    if tech:
        record["technician"] = tech

    # Normalize config type
    ct = record.get("config_type", "").strip().lower()
    if ct in ("msa firetech", "msa", "firetech"):
        record["config_type"] = "MSA Firetech"
    elif ct in ("avon",):
        record["config_type"] = "AVON"
    elif ct in ("ator labs", "ator", "ator labs"):
        record["config_type"] = "ATOR Labs"

    # Parse date
    if "date_performed" in record:
        try:
            record["date_iso"] = datetime.strptime(
                record["date_performed"], "%m/%d/%Y"
            ).strftime("%Y-%m-%d")
        except ValueError:
            record["date_iso"] = None
    else:
        record["date_iso"] = None

    return record


def validate_record(record: dict) -> list:
    """Validate a parsed record. Returns list of warnings."""
    warnings = []
    uid = record.get("unit_id", "?")

    # Check WOB fields present
    wob_a_keys = ["wob_A_10", "wob_A_20", "wob_A_35", "wob_A_50", "wob_A_65"]
    wob_b_keys = ["wob_B_65", "wob_B_85", "wob_B_105"]
    missing_wob = [k for k in wob_a_keys + wob_b_keys if k not in record]
    if missing_wob:
        warnings.append(f"{uid}: missing WOB fields: {missing_wob}")

    # Check WOB monotonicity
    wob_a = [record.get(k) for k in wob_a_keys if k in record]
    wob_b = [record.get(k) for k in wob_b_keys if k in record]
    if len(wob_a) >= 2 and wob_a != sorted(wob_a):
        warnings.append(f"{uid}: WOB-A not monotonic: {wob_a}")
    if len(wob_b) >= 2 and wob_b != sorted(wob_b):
        warnings.append(f"{uid}: WOB-B not monotonic: {wob_b}")

    # Check leak delta
    if "leak_delta" in record and record["leak_delta"] < 0:
        warnings.append(f"{uid}: negative leak delta: {record['leak_delta']}")

    # Check volume plausibility
    for vk in ["vol_nfpa40", "vol_nfpa102"]:
        if vk in record and not (0.5 < record[vk] < 5.0):
            warnings.append(f"{uid}: implausible volume {vk}={record[vk]}")

    return warnings


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Find all PDFs
    pdfs = sorted(glob.glob(str(PDF_DIR / "*.pdf")))
    print(f"Found {len(pdfs)} PDFs")

    # Parse all reports
    all_records = []
    all_warnings = []
    for i, pdf_path in enumerate(pdfs, 1):
        fname = Path(pdf_path).name
        print(f"  [{i:2d}/{len(pdfs)}] {fname}...", end=" ", flush=True)
        try:
            record = parse_report(pdf_path)
            warnings = validate_record(record)
            all_warnings.extend(warnings)
            all_records.append(record)
            status = "OK" if not warnings else f"WARN({len(warnings)})"
            print(status)
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\nParsed {len(all_records)} reports")

    # Deduplicate: latest report per unit ID
    units = defaultdict(list)
    for rec in all_records:
        uid = parse_unit_id_from_filename(rec["filename"])
        units[uid].append(rec)

    deduped = []
    for uid, recs in sorted(units.items()):
        # Prefer records with dates, sort by date descending
        dated = [r for r in recs if r.get("date_iso")]
        if dated:
            latest = max(dated, key=lambda r: r["date_iso"])
        else:
            latest = recs[-1]  # Last alphabetically
        # Use filename-based unit ID as canonical
        latest["unit_id_canonical"] = uid
        if "config_type" not in latest or latest["config_type"] == "Unknown":
            latest["config_type"] = get_config_type(uid)
        deduped.append(latest)

    print(f"Deduplicated to {len(deduped)} unique units")

    # Report completeness
    complete = sum(1 for r in deduped if all(
        k in r for k in ["wob_A_10", "wob_A_65", "wob_B_105", "leak_delta", "vol_nfpa40"]
    ))
    print(f"Complete records: {complete}/{len(deduped)}")

    if all_warnings:
        print(f"\nWarnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  {w}")

    # Manual corrections for OCR-mangled leak pressures (verified from PDF visual read)
    leak_corrections = {
        "20251104OCS31": (-9.99, -9.91),
        "20251120OCS35": (-9.77, -9.64),
        "20251205OCS36": (-9.74, -9.58),
        "20260121OCS45": (-11.11, -11.03),
        "20260127OCB50": (-11.16, -10.99),
        "20260312OCSA53": (-10.78, -10.60),
        "20260312OCSA54": (-11.31, -11.12),
    }
    for r in deduped:
        uid = r.get("unit_id_canonical", "")
        if uid in leak_corrections:
            start, end = leak_corrections[uid]
            r["leak_start"] = start
            r["leak_end"] = end
            r["leak_delta"] = abs(start) - abs(end)

    # Sort by date
    deduped.sort(key=lambda r: r.get("date_iso") or "9999")

    # Compute first-pass yield: units with only 1 report = first-pass
    reports_per_unit = {uid: len(recs) for uid, recs in units.items()}
    first_pass_units = [uid for uid, count in reports_per_unit.items() if count == 1]
    retest_units = [uid for uid, count in reports_per_unit.items() if count > 1]
    fpy = len(first_pass_units) / len(units) if units else 0
    print(f"First-pass yield: {len(first_pass_units)}/{len(units)} = {fpy:.1%}")

    # Build output with metadata
    output = {
        "_meta": {
            "total_units": len(deduped),
            "total_reports": len(all_records),
            "first_pass_count": len(first_pass_units),
            "retest_count": len(retest_units),
            "first_pass_yield": round(fpy, 4),
            "retest_units": sorted(retest_units),
        },
        "records": deduped,
    }

    # Write JSON
    json_path = DATA_DIR / "inspections.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote {json_path}")

    # Write CSV
    csv_path = DATA_DIR / "inspections.csv"
    fieldnames = [
        "unit_id_canonical", "unit_id", "date_performed", "date_iso",
        "technician", "config_type",
        "leak_start", "leak_end", "leak_delta",
        "wob_A_10", "wob_A_20", "wob_A_35", "wob_A_50", "wob_A_65",
        "wob_B_65", "wob_B_85", "wob_B_105",
        "vol_nfpa40", "vol_nfpa102",
        "filename", "source",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(deduped)
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
