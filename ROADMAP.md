# SPCOCATOR Roadmap — Phased Expansion

## Current State
Single-module SPC dashboard for OMNIcheck final inspection data extracted from PDFs. 37 units, 11 metrics, self-contained HTML output. Repo: halATOR/SPCOCATOR.

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

**Goal:** Extend SPCOCATOR to track incoming material quality and in-process checks.

### What we know
- Data is in **fillable PDF AcroForms** (field values extractable programmatically — no OCR)
- **Receipt inspection:** per-component/incoming-material, NOT per-OMNIcheck unit. Different part numbers, different metrics per part.
- **In-process inspection:** format TBD
- Data access currently limited — user working on connectivity

### Tasks (deferred until data is accessible)
1. **Obtain sample AcroForm PDFs** — extract field names programmatically to understand schema
2. **Design receipt inspection data model** — part number, supplier, metrics vary by part
3. **Write AcroForm parser** — `modules/receipt_inspection/parse_acroform.py` using PyMuPDF or pikepdf
4. **Receipt SPC dashboard** — separate tab or separate HTML, grouped by part number
5. **In-process inspection** — same approach once format is understood

### Dependencies
- Access to the receipt/in-process inspection PDFs
- Understanding of which metrics matter and what the spec limits are per part

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

## Priority Order
1. **Phase 1** — .bin parsing (highest value: new metrics, failure data, WOB prediction model)
2. **Phase 2** — Cal certs (customer-facing deliverable, revenue-adjacent)
3. **Phase 3** — Auto-watcher (operational efficiency, depends on Phases 1+2 being stable)
4. **Phase 4** — Receipt/in-process (blocked on data access)
