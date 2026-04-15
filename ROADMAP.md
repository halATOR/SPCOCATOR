# SPCOCATOR Roadmap — Phased Expansion

Last updated: 2026-04-15

## Current State
Multi-module QA data platform. Final inspection SPC dashboard complete (37 units, 11 metrics). Bin parsing and cal cert generator complete. Auto-watcher code-complete but not deployed. Receipt inspection module in active development. Repo: halATOR/SPCOCATOR.

---

## Phase 1: .bin File Parsing + Rework Tracking

**Goal:** Reverse-engineer the test .bin format to unlock raw waveform data, NFPA 40/102 WOB values, and failing-test records (for real first-pass yield).

### What we know about test .bin files
- **Size:** ~111 KB each (55 files, 35 unique units)
- **Header:** 4 length-prefixed strings: Unit ID, Time, Date, Technician
- **Payload:** ~13,600 big-endian IEEE 754 doubles (~109 KB) — raw waveform data from the breathing test
- **Trailer:** Embedded calibration data starting at ~offset 0x1AA56 (sensor metadata, cal curve points in same length-prefixed format as .cal files)
- **Key insight:** .bin files exist for BOTH passing and failing tests. Only passing tests get PDFs. This means .bin-only records = failures.

### New data unlocked
- **WOB at NFPA 40 RMV** — not in PDFs, only in .bin
- **WOB at NFPA 102 RMV** — not in PDFs, only in .bin
- **Raw waveform data** — pressure/flow time series for each breathing rate
- **Failure records** — .bin files without matching PDFs = failed tests

### Tasks
1. **Map the .bin payload structure** — use the 11 units with both .bin and PDF data as Rosetta stones. Cross-reference known PDF values against candidate float positions. Identify byte offsets for each measurement section.
2. **Extract NFPA 40/102 WOB values** — locate these in the payload, validate against physical constraints (positive, monotonic with flow rate, plausible kPa range)
3. **Identify pass/fail .bin files** — .bin files without a matching PDF = test failures. Extract what data is available from failures.
4. **Add .bin-derived metrics to dashboard** — new SPC charts for NFPA 40/102 WOB, real FPY metric
5. **WOB→Volume prediction model** — correlate WOB at NFPA 40/102 breathing rates with bell prover volume results. If R² is high enough, WOB alone can predict volume (eliminating the need for bell prover testing).

### Rework workflow change
With the engineer's cooperation, establish the convention:
- Every test (pass or fail) saves a .bin to a known folder
- Final inspection PDF only saved for passing units (current behavior)
- SPCOCATOR scans .bin folder, identifies failures by absence of matching PDF
- Dashboard shows real FPY and failure-mode data

### Dependencies
- Engineer to confirm .bin payload field ordering (or provide documentation)
- Access to .bin files from known-failing tests for validation

---

## Phase 2: Calibration Certificate Generator

**Goal:** Auto-generate customer-facing cal certs from .cal files.

### What we know about .cal files
- **Size:** ~1.5 KB, `.cal` extension
- **Format:** Same length-prefixed string format as test .bin headers
- **Location:** `~/Desktop/projects backup/calibrator/` (currently 1 file: `OMNI-021FDBB6_20260321_Cal.cal`)
- **Content per sensor (6 sensors):**
  - Manufacturer, Model, Serial Number
  - Range + units (e.g., "0to5800 psi")
  - Accuracy spec (e.g., "±0.5%")
  - Calibration curve: voltage→engineering-unit point pairs
- **DAQ info:** NI USB-6001 with serial number
- **Unit ID:** embedded at end of file (e.g., "12092024OCS14")
- **Filename format:** `OMNI-{MAC}_{YYYYMMDD}_Cal.cal`

### Cal cert output
Generate a PDF certificate per unit containing:
- ATOR Labs header, cert number, date
- Unit ID, OMNIcheck configuration type
- Per-sensor table: Type, Manufacturer, Model, S/N, Range, Accuracy, Cal points (applied vs measured), Pass/Fail
- Reference equipment: NI USB-6001 serial, calibration standard traceability
- Signature block, expiration date (1 year from cal date)

### Tasks
1. **Parse .cal file format** — write `modules/cal_certs/parse_cal.py`
2. **Design cert template** — HTML template rendered to PDF (weasyprint or browser print)
3. **Generate certs** — `modules/cal_certs/generate_cert.py` reads .cal, fills template, outputs PDF
4. **Batch processing** — scan a folder of .cal files, generate certs for any not yet processed
5. **Constant cal equipment info** — config file for reference equipment details (expander to dynamic once multiple cal sensors exist)

### Dependencies
- Access to more .cal files (currently only 1 sample)
- Confirmation of what customers need on the cert (regulatory requirements, traceability chain)
- Decision on PDF generation library (weasyprint vs browser print vs reportlab)

---

## Phase 3: Auto-Watcher + ATORcloud Integration

**Goal:** Folder watcher that auto-triggers dashboard regeneration and cal cert creation when new files appear.

### Architecture
```
ATORcloud (WD MyCloud NAS)
  ├── Final QA Reports/         ← test PDFs + .bin files land here
  ├── Calibration/              ← .cal files land here
  └── SPCOCATOR Output/
      ├── Dashboard/            ← latest dashboard HTML
      └── Cal Certs/            ← generated PDF certificates
```

### Tasks
1. **`watcher.py`** — uses `watchdog` library to monitor folders for new .bin/.pdf/.cal files
2. **On new test file:** re-run extract_and_parse.py + generate_dashboard.py, copy HTML to output folder
3. **On new .cal file:** run cal cert generator, copy PDF to output folder
4. **Run as launchd service** (macOS) — auto-starts on boot, runs in background
5. **Logging** — append to a run log with timestamps, files processed, errors

### Dependencies
- ATORcloud folder paths confirmed and accessible from this Mac
- Decision on whether watcher runs on this Mac mini or on the NAS itself

---

## Phase 4: Receipt + In-Process Inspection

**Status: IN PROGRESS** (receipt inspection); NOT STARTED (in-process)

**Goal:** Extend SPCOCATOR to track incoming material quality and in-process checks.

### Receipt Inspection — What we know (as of 2026-04-15)
- Data is in **fillable PDF AcroForms** (field values extractable programmatically — no OCR)
- **Data access resolved:** Forms on mounted OC drive at `/Volumes/OC/OC QA Reports/Receipt Inspection QA Forms/Completed QA Forms/Dimensional/`
- **21 completed forms** (Oct 2025 – Mar 2026), 5 active part numbers
- **Master template:** `/Volumes/OC/Receipt Inspection Form_Dimensional Master.pdf` (QAF-009-005)
- **7 part numbers defined:** Trachea Base, Top Hat, Piston Cap, Piston Body, Piston Housing, 10mm Linear Shaft, Lead Screw
- **100% inspection** currently; sampling plans planned once data is sufficient
- **1 supplier per part** (3–4 major suppliers total)
- **Spec limits from embedded drawings** in master template
- **Known issue:** Metrics on form have drifted from current drawings; using drawing specs as baseline for v1
- **Non-numeric values:** FT (fit test), FC (fit check), fail, n/a — mixed with numeric dimensional data
- **Multi-page forms:** "Add Page" button creates additional data pages with `P{N}.Point of Inspection...` field naming
- **Full spec:** `RECEIPT_INSPECTION_SPEC.md`

### Architecture Decision
- **Separate HTML dashboard** (not tab in existing dashboard) — data model is fundamentally different (part-centric vs unit-centric)
- **Shared navigation bar** between final inspection and receipt inspection dashboards
- **Cross-part summary** with drill-down to per-part I-MR charts

### Tasks
1. ~~Obtain sample AcroForm PDFs~~ — **DONE** (21 forms on OC drive)
2. ~~Design receipt inspection data model~~ — **DONE** (spec written)
3. **Write AcroForm parser** — `modules/receipt_inspection/extract_receipt.py`
4. **Generate receipt SPC dashboard** — `modules/receipt_inspection/generate_receipt_dashboard.py`
5. **Add shared nav bar** to both dashboards
6. **In-process inspection** — format TBD, deferred

### Dependencies
- ~~Access to the receipt/in-process inspection PDFs~~ **RESOLVED**
- ~~Understanding of which metrics matter and what the spec limits are per part~~ **RESOLVED (from drawings)**
- Updated dimension list from user (nice-to-have, not blocking v1)

---

## Repo Structure (target)

```
SPCOCATOR/
├── CLAUDE.md
├── AUDIT_LOG.md
├── design.md
├── ROADMAP.md                       ← this file
├── shared/
│   ├── bin_parser.py                ← common length-prefixed string/float parser
│   ├── config.py                    ← unit ID prefixes, config types, colors
│   └── watcher.py                   ← folder monitor (Phase 3)
├── modules/
│   ├── final_inspection/
│   │   ├── extract_and_parse.py     ← current tools/extract_and_parse.py
│   │   └── generate_dashboard.py    ← current generate_dashboard.py
│   ├── cal_certs/
│   │   ├── parse_cal.py
│   │   ├── generate_cert.py
│   │   └── templates/cert.html
│   ├── receipt_inspection/          ← Phase 4
│   └── in_process/                  ← Phase 4
├── data/
│   ├── inspections.json
│   ├── inspections.csv
│   └── events.json
└── output/
    ├── OMNIcheck_SPC_Dashboard.html
    └── cal_certs/
```

---

## Priority Order (updated 2026-04-15)
1. ~~**Phase 1** — .bin parsing~~ **DONE**
2. ~~**Phase 2** — Cal certs~~ **DONE**
3. **Phase 4** — Receipt inspection dashboard (actively building)
4. **Phase 3** — Auto-watcher deployment (code done, blocked on cal template + ATORcloud paths)
5. **Phase 4b** — In-process inspection (deferred, format TBD)
