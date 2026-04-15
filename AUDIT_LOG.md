# OMNIcheck SPC Dashboard — Audit Log

## Implemented Features

### Core SPC (v1.0)
- **I-MR Control Charts** — 11 metrics: 5 WOB Protocol A, 3 WOB Protocol B, leak pressure drop, NFPA 40 volume, NFPA 102 volume
- **Control Limits** — UCL/LCL calculated via I-MR method (MR̄ / d₂, d₂=1.128)
- **Spec Limits** — USL from ISO 16900-5 (WOB), 0.4 inWg leak (ISO 16900-5), ±0.1 L volume (NFPA 1850)
- **OOC Detection** — Rule 1: beyond 3σ (red triangle). Rule 2: 8 consecutive same side (amber diamond). Rule 3: 6 consecutive trending (amber diamond). Rules suppressed for zero-variation metrics.
- **Moving Range Subcharts** — MR chart below each I-chart with MR̄ centerline and UCL

### Filters
- **Time Window** — All Time / Yearly / Quarterly / Monthly. Control limits always from full dataset.
- **Configuration Type** — Dropdown: All / MSA Firetech / AVON / ATOR Labs. Does not affect control limits.
- **Technician** — Checkboxes, multi-select. All checked by default.

### Analytics
- **Cpk Scorecards** — Color-coded capability index per metric. Green ≥1.33, amber ≥1.0, red <1.0. One-sided Cpu for WOB/leak, min(Cpu,Cpl) for two-sided volume specs.
- **Production Throughput** — Stacked bar chart, units/month by config type.
- **OOC Pareto** — Horizontal bar chart ranking metrics by OOC count, split beyond-limits vs run-rules.
- **Trend Annotations** — Vertical dotted lines from `data/events.json` marking process changes on all SPC charts.

### Technician Analysis Tab
- **Box Plots** — Per metric, grouped by technician with individual data points overlaid.
- **Summary Table** — N, Mean, Std Dev per tech per metric. Low-N (<10) values styled in amber.
- **Gauge R&R** — Reproducibility (between-tech variation as % of total). <10% acceptable, 10-30% marginal, >30% unacceptable.

### Export
- **Print / Export** — Browser print dialog with print-optimized CSS. Hides controls, formats for PDF.

## Data Pipeline
- **PDF Extraction** — `tools/extract_and_parse.py` handles 63 PDFs (11 text-based via PyMuPDF, 52 image-based via Tesseract OCR at 600 DPI)
- **OCR Corrections** — 7 units have manual leak pressure corrections for OCR-mangled values, verified from visual PDF reads
- **Deduplication** — Latest report per unit by Date Performed, N=37
- **Validation** — WOB monotonicity, positive leak delta, volume plausibility (all 37/37 pass)
- **Output** — `data/inspections.json` (with `_meta` block), `data/inspections.csv`

---

### Phase 1: .bin File Parsing (completed 2026-04)
- **Shared Binary Parser** (`shared/bin_parser.py`) — `BinaryReader` class for OMNIcheck binary files: 4-byte big-endian length-prefixed UTF-8 strings, IEEE 754 doubles, LabVIEW timestamps (16-byte: I64 seconds since 1904 + U64 fractional)
- **Test .bin Parser** (`shared/parse_test_bin.py`) — Extracts header (unit ID, date, time, technician), MAC address from embedded cal trailer, V1/V2 format detection (V2 > 150KB)
- **V2 WOB Correction Blocks** — Parses 3 WOB correction summary blocks (NFPA 40, ISO High, NFPA 103): total WOB avg, inhale/exhale WOB avg, pressure max/min avg, elastance avg, waveform sample counts. Validates Total WOB ≈ Inhale + Exhale.
- **V1 vs V2 Detection** — V1 files ~111KB (raw waveform only), V2 files ~206KB (waveform + WOB correction summaries). Size threshold at 150KB.
- **MAC Address Extraction** — Locates MAC by finding "USB-6001" marker in cal trailer, reads length-prefixed string immediately after

### Phase 2: Calibration Certificate Generator (completed 2026-04)
- **Cal File Parser** (`modules/cal_certs/parse_cal.py`) — Full .cal binary parser: LabVIEW timestamp, 6 sensor blocks (barometric, temperature, HP, IP, eye, mouth), each with manufacturer/model/SN/range/units/accuracy/polynomial coefficients/cal table points. DAQ info (NI USB-6001 serial). Trailing unit ID. Handles LabVIEW special chars (0xB1→±, 0xB0→°).
- **Certificate Generator** (`modules/cal_certs/generate_cert.py`) — Jinja2 HTML renderer with MAC→serial lookup fallback (`data/mac_serial_map.json`), batch directory processing, auto-skip for already-generated certs
- **Certificate Template** (`modules/cal_certs/templates/cert.html`) — Print-optimized A4/Letter HTML: ATOR Labs header, cert number (`CAL-{UNIT_ID}-{YYYYMMDD}`), unit info, per-sensor summary table, per-sensor detail (polynomial coefficients + cal point tables), reference equipment section, signature block, NIST traceability statement, 12-month expiration
- **Reference Equipment Config** (`modules/cal_certs/equipment.json`) — Placeholder config for 5 reference sensor categories + DAQ. Fields for manufacturer, model, SN, accuracy, cal cert traceability.
- **Output** — Generated certs at `output/cal_certs/`

---

### Phase 3: Auto-Watcher Deployment (completed 2026-04-15)
- **Watcher Service** — launchd service `com.atorlabs.spcocator-watcher`, RunAtLoad + KeepAlive
- **Watch Paths** — 3 folders on OC drive: Final QA PDFs, test .bin files, calibration .cal files
- **Actions** — `.pdf/.bin` triggers file sync + dashboard regeneration; `.cal` triggers cal cert generation
- **Output Paths** — Dashboards to `/Volumes/OC/QMS/SPC Dashboards`, cal certs to `/Volumes/OC/QMS/Calibration Documentation`
- **Startup Scan** — On every launch, compares watched folders against `logs/processed_files.json` manifest to catch files added while offline
- **Reference Equipment** — `modules/cal_certs/equipment.json` populated with 4 calibrated reference sensors (Additel low pressure, Crystal M1-300PSI, Crystal M1-10KPSI, Sper barometric) + factory-cal temperature. Bell prover info still pending.

### Phase 4: Receipt Inspection SPC Dashboard (completed 2026-04-15)
- **Spec** — `RECEIPT_INSPECTION_SPEC.md`: full requirements for receipt inspection data model, AcroForm parsing, metrics, SPC methods, and dashboard layout
- **AcroForm Parser** (`modules/receipt_inspection/extract_receipt.py`) — Extracts metadata + dimensional measurements from fillable PDF forms (QAF-009-005). Handles: standard 10-row page 2 grid (`POI {col}{row}`), dynamically added pages (`P{N}.Point of Inspection Measured Dimensions Template.POI {col}Row{row}`), visual inspection SAT/UNSAT checkboxes, notes field. Classifies values as numeric, n/a, FT (fit test), FC (fit check), fail. Validates against drawing specs with 5x-range plausibility check.
- **Part Registry** — 7 parts with drawing specs embedded: Trachea Base (7 dims), Top Hat (7 dims), Piston Cap (5 dims), Piston Body (9 dims), Piston Housing (6 dims), 10mm Linear Shaft (2 dims, mm), Lead Screw (3 dims). Specs from master template drawings.
- **Dashboard Generator** (`modules/receipt_inspection/generate_receipt_dashboard.py`) — Self-contained HTML with Plotly.js. Two views: summary (part cards, Cpk heatmap, lot timeline, OOC table) and per-part detail (Cpk scorecards, I-MR charts per dimension, lot history). Lot-based coloring. Nominal line on charts. Inspector filter.
- **Dataset** — 21 completed forms (Oct 2025 – Mar 2026), 5 active parts, 905 total measurements
- **Known Issue** — Metric drift: POI column labels stay the same but actual dimensions measured change over time. Parser uses per-form POI labels as truth and flags implausible values (78 warnings, mostly Piston Cap and Top Hat).
- **Shared Nav Bar** — Both dashboards include SPCOCATOR nav bar linking to each other (Final Inspection / Receipt Inspection)

### Config Stratification: Welch/KW Tests (completed 2026-04-15)
- **Config Stratification Tab** — New tab on final inspection dashboard with Kruskal-Wallis H test results and per-metric box plots by config type
- **Implementation** — Pure numpy + math (no scipy dependency): Kruskal-Wallis with tie correction for 3 groups, Welch's t-test for 2 groups, chi-squared survival function via regularized gamma series expansion
- **Results** — No significant differences across any of 11 metrics (all p > 0.05). WOB @ 105 LPM (B) nearest at p=0.056. Combined control limits statistically validated.
- **Summary Table** — Metric, test used, statistic, p-value, significance flag, per-config n/mean/std
- **Box Plots** — Per metric with spec limit overlay and p-value annotation

---

## Decision Log
| Decision | Rationale |
|----------|-----------|
| Latest report per unit (N=37) | Units re-tested for rework/recalibration; latest = released state |
| I-MR charts (not Xbar-R) | Production rate ~2-3 units/month, subgroup size = 1 |
| Suppress OOC rules when σ=0 | WOB A10 reads 0.06 for all units — measurement resolution, not a process signal |
| First-pass yield removed | All reports are passing units; failed units don't generate reports, so FPY is unmeasurable from this data |
| Cpk one-sided for WOB | WOB specs are upper limits only — lower is always better |
| Volume specs two-sided | NFPA 1850 defines ±0.1 L acceptance band |
| Shared BinaryReader for .cal and .bin | Same length-prefixed encoding in both file types; single parser avoids duplication |
| V2 detection by file size | V2 files consistently ~206KB vs V1 ~111KB; no version field in header, size is the reliable discriminator |
| MAC extraction via "USB-6001" anchor | MAC string always follows DAQ model string in cal trailer; more robust than fixed byte offset |
| HTML cert output (not direct PDF) | Browser Print→PDF is universal; avoids weasyprint/reportlab dependency. Print CSS handles layout. |
| Equipment.json with empty fields | Placeholder until user provides actual reference equipment details; generator gracefully skips empty entries |
| Separate HTML for receipt inspection | Data model is fundamentally different (part-centric vs unit-centric); cramming both into one file would mean conditional rendering and bloated JSON |
| Per-form POI labels as truth | Metric drift means the same column label can refer to different actual dimensions over time; parser trusts each form's declared labels and flags implausible values |
| Drawing specs as baseline | Form tolerances have drifted; user has updated list but drawings embedded in master template are the v1 source of truth |
| I-MR for receipt inspection | 100% inspection currently, individual measurements are natural subgroup; migrate to Xbar-R when sampling plans adopted |
| Kruskal-Wallis over ANOVA | Non-parametric; robust to small/unequal group sizes (AVON n=3). No scipy needed — implemented from scratch with numpy. |
| Dashboard output to /Volumes/OC/QMS/SPC Dashboards | Central location on shared OC drive accessible to all stakeholders |
