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

## Decision Log
| Decision | Rationale |
|----------|-----------|
| Latest report per unit (N=37) | Units re-tested for rework/recalibration; latest = released state |
| I-MR charts (not Xbar-R) | Production rate ~2-3 units/month, subgroup size = 1 |
| Suppress OOC rules when σ=0 | WOB A10 reads 0.06 for all units — measurement resolution, not a process signal |
| First-pass yield removed | All reports are passing units; failed units don't generate reports, so FPY is unmeasurable from this data |
| Cpk one-sided for WOB | WOB specs are upper limits only — lower is always better |
| Volume specs two-sided | NFPA 1850 defines ±0.1 L acceptance band |
