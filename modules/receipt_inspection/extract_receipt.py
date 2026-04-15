#!/usr/bin/env python3
"""
Extract receipt inspection data from AcroForm PDFs.

Scans completed receipt inspection forms, extracts metadata and dimensional
measurements from AcroForm fields, and outputs structured JSON for the
receipt inspection SPC dashboard.

Usage:
    python3 modules/receipt_inspection/extract_receipt.py [forms_dir]

Default forms_dir:
    /Volumes/OC/OC QA Reports/Receipt Inspection QA Forms/Completed QA Forms/Dimensional/
"""

import json
import os
import re
import sys
from pathlib import Path

import pymupdf

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_PATH = DATA_DIR / "receipt_inspections.json"

DEFAULT_FORMS_DIR = Path(
    "/Volumes/OC/OC QA Reports/Receipt Inspection QA Forms/"
    "Completed QA Forms/Dimensional"
)

# --- Part registry: spec limits from master template drawings ---

PART_REGISTRY = {
    "Trachea Base": {
        "drawing": "0000214",
        "material": "ABS",
        "units": "inches",
        "dimensions": {
            "OD":  {"nominal": 7.130, "usl": 7.150, "lsl": 7.110},
            "A":   {"nominal": 7.000, "usl": 7.050, "lsl": 6.950},
            "D1":  {"nominal": 1.750, "usl": 1.755, "lsl": 1.745},
            "ID1": {"nominal": 1.625, "usl": 1.627, "lsl": 1.623},
            "ID2": {"nominal": 1.500, "usl": 1.505, "lsl": 1.495},
            "ID3": {"nominal": 1.375, "usl": 1.378, "lsl": 1.375},
            "H":   {"nominal": 0.375, "usl": 0.425, "lsl": 0.325},
        },
    },
    "Top Hat": {
        "drawing": "000020J-I",
        "material": "Injection Molded",
        "units": "inches",
        "dimensions": {
            "OD1": {"nominal": 12.000, "usl": 12.010, "lsl": 11.990},
            "OD2": {"nominal": 10.375, "usl": 10.390, "lsl": 10.360},
            "OD3": {"nominal": 1.620,  "usl": 1.621,  "lsl": 1.619},
            "OD4": {"nominal": 1.525,  "usl": 1.526,  "lsl": 1.524},
            "ID1": {"nominal": 10.000, "usl": 10.015, "lsl": 9.985},
            "ID2": {"nominal": 1.399,  "usl": 1.404,  "lsl": 1.394},
            "A":   {"nominal": 1.000,  "usl": 1.050,  "lsl": 0.950},
        },
    },
    "Piston Cap": {
        "drawing": "00001HG",
        "material": "PLA",
        "units": "inches",
        "dimensions": {
            "OD": {"nominal": 9.625, "usl": 9.675, "lsl": 9.575},
            "ID": {"nominal": 9.375, "usl": 9.425, "lsl": 9.325},
            "D1": {"nominal": 0.470, "usl": 0.485, "lsl": 0.455},
            "D2": {"nominal": 0.250, "usl": 0.265, "lsl": 0.235},
            "H":  {"nominal": 0.438, "usl": 0.453, "lsl": 0.423},
        },
    },
    "Piston Body": {
        "drawing": "00001JC",
        "material": "PLA",
        "units": "inches",
        "dimensions": {
            "OD": {"nominal": 9.250, "usl": 9.255, "lsl": 9.245},
            "ID": {"nominal": 8.800, "usl": 8.850, "lsl": 8.750},
            "D1": {"nominal": 0.266, "usl": 0.271, "lsl": 0.261},
            "D2": {"nominal": 0.772, "usl": 0.777, "lsl": 0.767},
            "D3": {"nominal": 1.125, "usl": 1.130, "lsl": 1.120},
            "D4": {"nominal": 0.340, "usl": 0.355, "lsl": 0.325},
            "D5": {"nominal": 0.265, "usl": 0.270, "lsl": 0.260},
            "D6": {"nominal": 0.154, "usl": 0.159, "lsl": 0.149},
            "H":  {"nominal": 5.250, "usl": 5.300, "lsl": 5.200},
        },
    },
    "Piston Housing": {
        "drawing": "0000209-I",
        "material": "Injection Molded",
        "units": "inches",
        "dimensions": {
            "OD1": {"nominal": 12.000, "usl": 12.020, "lsl": 11.980},
            "OD2": {"nominal": 10.800, "usl": 10.850, "lsl": 10.750},
            "OD3": {"nominal": 13.750, "usl": 13.755, "lsl": 13.745},
            "ID":  {"nominal": 10.000, "usl": 10.005, "lsl": 9.995},
            "A":   {"nominal": 0.221,  "usl": 0.271,  "lsl": 0.171},
            "H":   {"nominal": 9.535,  "usl": 9.540,  "lsl": 9.530},
        },
    },
    "10mm Linear Rod": {
        "drawing": "000020V",
        "material": "Aluminum",
        "units": "mm",
        "dimensions": {
            "OD": {"nominal": 10.000, "usl": 10.127, "lsl": 9.873},
            "H":  {"nominal": 279.000, "usl": 279.381, "lsl": 278.619},
        },
    },
    "Lead Screw": {
        "drawing": "DSK-00060281",
        "material": "Engineered Polymer (Drylin)",
        "units": "inches",
        "dimensions": {
            "OD": {"nominal": 0.375, "usl": 0.375, "lsl": 0.373},
            "H1": {"nominal": 5.275, "usl": 5.280, "lsl": 5.270},
            "H2": {"nominal": 6.000, "usl": 6.005, "lsl": 5.995},
        },
    },
}


def classify_value(raw):
    """Classify a form field value as numeric, attribute, or empty."""
    if not raw or raw.strip() == "":
        return "empty", None

    s = raw.strip().lower()

    if s == "n/a":
        return "na", None
    if s == "ft":
        return "ft", None
    if s == "fc":
        return "fc", None
    if s == "fail":
        return "fail", None

    # Try parsing as float
    try:
        val = float(s)
        return "numeric", val
    except ValueError:
        return "unknown", raw


def extract_page2_grid(page):
    """Extract measurements from the standard page 2 grid (10 rows x 9 cols)."""
    fields = {}
    for w in page.widgets():
        fn = w.field_name or ""
        val = w.field_value or ""
        fields[fn] = val

    rows = []
    for row_idx in range(1, 11):
        row_data = {}
        for col_idx in range(1, 10):
            if row_idx == 10:
                key = f"POI {col_idx}10"
            else:
                key = f"POI {col_idx}{row_idx}"
            raw = fields.get(key, "")
            row_data[col_idx] = raw
        # Check if row has any non-empty values
        if any(v.strip() for v in row_data.values() if v):
            rows.append({"seq": row_idx, "values": row_data})

    # Extract visual inspection checkboxes
    # SAT checkboxes are odd-numbered (7,9,11,...), UNSAT are even (8,10,12,...)
    sat_count = 0
    unsat_count = 0
    for row_idx in range(1, 11):
        sat_key = f"Check Box{7 + (row_idx - 1) * 2}"
        unsat_key = f"Check Box{8 + (row_idx - 1) * 2}"
        # Alternative numbering for rows 6+
        if row_idx >= 6:
            sat_key = f"Check Box{17 + (row_idx - 6) * 2}"
            unsat_key = f"Check Box{18 + (row_idx - 6) * 2}"

        sat_val = fields.get(sat_key, "")
        unsat_val = fields.get(unsat_key, "")
        if sat_val == "Yes":
            sat_count += 1
        if unsat_val == "Yes":
            unsat_count += 1

    return rows, sat_count, unsat_count


def extract_added_pages(doc, start_page=2):
    """Extract measurements from dynamically added pages (P{N} prefix)."""
    all_rows = []
    sat_total = 0
    unsat_total = 0

    for page_idx in range(start_page, len(doc)):
        page = doc[page_idx]
        fields = {}
        for w in page.widgets():
            fn = w.field_name or ""
            val = w.field_value or ""
            fields[fn] = val

        # Detect if this is a data page by looking for the P{N} prefix pattern
        page_prefix = None
        for fn in fields:
            m = re.match(r"(P\d+\.Point of Inspection Measured Dimensions Template)\.", fn)
            if m:
                page_prefix = m.group(1)
                break

        if not page_prefix:
            # Check for notes page (Text27)
            if "Text27" in fields:
                continue
            # Not a data page, skip
            continue

        rows = []
        for row_idx in range(1, 11):
            seq_key = f"{page_prefix}.NORow{row_idx}"
            seq_val = fields.get(seq_key, "").strip()
            if not seq_val:
                continue

            try:
                part_seq = int(seq_val)
            except ValueError:
                part_seq = None

            row_data = {}
            for col_idx in range(1, 10):
                if row_idx == 1:
                    key = f"{page_prefix}.POI {col_idx}Row1_2"
                else:
                    key = f"{page_prefix}.POI {col_idx}Row{row_idx}"
                raw = fields.get(key, "")
                row_data[col_idx] = raw

            if any(v.strip() for v in row_data.values() if v):
                rows.append({"seq": part_seq or row_idx, "values": row_data})

        # Count visual inspection checkboxes on added pages
        sat_count = 0
        unsat_count = 0
        for fn, val in fields.items():
            if "Check Box" in fn and val == "Yes":
                # SAT boxes are odd numbers, UNSAT are even
                m2 = re.search(r"Check Box(\d+)", fn)
                if m2:
                    box_num = int(m2.group(1))
                    if box_num % 2 == 1:
                        sat_count += 1
                    else:
                        unsat_count += 1

        all_rows.extend(rows)
        sat_total += sat_count
        unsat_total += unsat_count

    return all_rows, sat_total, unsat_total


def extract_form(filepath):
    """Extract all data from a single receipt inspection form PDF."""
    doc = pymupdf.open(str(filepath))
    warnings = []

    # --- Page 1: Metadata ---
    page1_fields = {}
    for w in doc[0].widgets():
        fn = w.field_name or ""
        val = w.field_value or ""
        page1_fields[fn] = val

    inspector = page1_fields.get("Dropdown1", "").strip()
    if inspector == "- Select -":
        inspector = ""
    date_str = page1_fields.get("Date1", "").strip()
    part_name = page1_fields.get("Dropdown2", "").strip()
    if part_name == "- Select -":
        part_name = ""
    product = page1_fields.get("Dropdown3", "").strip()
    if product == "- Select -":
        product = ""
    lot = page1_fields.get("Text1", "").strip()
    po = page1_fields.get("Text2", "").strip()
    drawing = page1_fields.get("Text3", "").strip()

    delivery_qty_raw = page1_fields.get("Text4", "").strip()
    insp_qty_raw = page1_fields.get("Text5", "").strip()
    try:
        delivery_qty = int(delivery_qty_raw) if delivery_qty_raw else None
    except ValueError:
        delivery_qty = None
    try:
        insp_qty = int(insp_qty_raw) if insp_qty_raw else None
    except ValueError:
        insp_qty = None

    # POI labels (dimension identifiers)
    poi_labels = []
    for i in range(9):
        field_name = f"Text{6 + i}"
        label = page1_fields.get(field_name, "").strip()
        poi_labels.append(label)

    # Trim trailing empty labels
    while poi_labels and not poi_labels[-1]:
        poi_labels.pop()

    # --- Page 2: Data grid ---
    page2_rows, sat_p2, unsat_p2 = extract_page2_grid(doc[1])

    # --- Pages 3+: Additional data pages ---
    added_rows, sat_added, unsat_added = extract_added_pages(doc, start_page=2)

    # --- Notes ---
    notes = ""
    for page in doc:
        for w in page.widgets():
            if (w.field_name or "") == "Text27":
                notes = (w.field_value or "").strip()
                break
        if notes:
            break

    doc.close()

    # --- Build measurements list ---
    all_raw_rows = page2_rows + added_rows
    measurements = []
    attr_counts = {"ft": {}, "fc": {}, "fail": {}}

    for row in all_raw_rows:
        m = {}
        for col_idx, raw_val in row["values"].items():
            if col_idx > len(poi_labels) or col_idx < 1:
                continue
            label = poi_labels[col_idx - 1]
            if not label:
                continue

            vtype, val = classify_value(raw_val)

            if vtype == "numeric":
                m[label] = val
            elif vtype in ("ft", "fc", "fail"):
                attr_counts[vtype][label] = attr_counts[vtype].get(label, 0) + 1
            # na, empty, unknown: skip

        if m:
            measurements.append({"part_seq": row["seq"], "values": m})

    # --- Plausibility check against spec ---
    part_specs = PART_REGISTRY.get(part_name, {}).get("dimensions", {})
    for meas in measurements:
        for dim_label, val in meas["values"].items():
            if dim_label in part_specs:
                spec = part_specs[dim_label]
                spec_range = spec["usl"] - spec["lsl"]
                nom = spec["nominal"]
                # Warn if value is more than 5x the spec range away from nominal
                if spec_range > 0 and abs(val - nom) > 5 * spec_range:
                    w = (
                        f"{os.path.basename(filepath)}: {dim_label} = {val} "
                        f"is far from nominal {nom} (spec range {spec_range:.4f})"
                    )
                    warnings.append(w)

    return {
        "filename": os.path.basename(filepath),
        "date": date_str,
        "inspector": inspector,
        "part": part_name,
        "product": product,
        "lot": lot,
        "po": po,
        "drawing": drawing,
        "delivery_qty": delivery_qty,
        "insp_qty": insp_qty,
        "poi_labels": poi_labels,
        "notes": notes,
        "measurements": measurements,
        "attribute_checks": {
            "ft": attr_counts["ft"],
            "fc": attr_counts["fc"],
            "fail": attr_counts["fail"],
            "visual_sat": sat_p2 + sat_added,
            "visual_unsat": unsat_p2 + unsat_added,
        },
    }, warnings


def normalize_date(date_str):
    """Normalize date string to ISO format (YYYY-MM-DD)."""
    if not date_str:
        return ""
    # Already ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    # MM/DD/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_str)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return date_str


def main():
    forms_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FORMS_DIR

    if not forms_dir.exists():
        print(f"Error: Forms directory not found: {forms_dir}")
        print("Is the OC drive mounted?")
        sys.exit(1)

    pdfs = sorted(forms_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files found in {forms_dir}")
        sys.exit(1)

    print(f"Found {len(pdfs)} receipt inspection forms")

    all_forms = []
    all_warnings = []
    total_measurements = 0

    for pdf_path in pdfs:
        print(f"  Parsing {pdf_path.name}...", end=" ")
        try:
            form_data, warnings = extract_form(pdf_path)
            form_data["date_iso"] = normalize_date(form_data["date"])
            all_forms.append(form_data)
            n_meas = sum(len(m["values"]) for m in form_data["measurements"])
            total_measurements += n_meas
            n_parts = len(form_data["measurements"])
            print(f"{n_parts} parts, {n_meas} measurements")
            if warnings:
                for w in warnings:
                    print(f"    WARNING: {w}")
                all_warnings.extend(warnings)
        except Exception as e:
            print(f"ERROR: {e}")
            all_warnings.append(f"{pdf_path.name}: extraction failed: {e}")

    # Sort by date
    all_forms.sort(key=lambda f: f.get("date_iso", ""))

    # Collect parts that have data
    parts_with_data = sorted(set(f["part"] for f in all_forms if f["part"]))

    # Date range
    dates = [f["date_iso"] for f in all_forms if f["date_iso"]]
    date_range = [min(dates), max(dates)] if dates else []

    output = {
        "_meta": {
            "total_forms": len(all_forms),
            "total_measurements": total_measurements,
            "parts_with_data": parts_with_data,
            "date_range": date_range,
            "extraction_date": "2026-04-15",
            "warnings": all_warnings,
        },
        "part_registry": PART_REGISTRY,
        "forms": all_forms,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nExtracted {len(all_forms)} forms, {total_measurements} total measurements")
    print(f"Parts with data: {', '.join(parts_with_data)}")
    if date_range:
        print(f"Date range: {date_range[0]} to {date_range[1]}")
    if all_warnings:
        print(f"\n{len(all_warnings)} warnings:")
        for w in all_warnings:
            print(f"  - {w}")
    print(f"\nOutput: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
