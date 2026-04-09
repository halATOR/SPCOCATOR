# CLAUDE.md — OMNIcheck SPC Dashboard

## Project Overview
SPC dashboard for OMNIcheck final QA inspection reports. Extracts data from PDFs, computes I-MR control charts, and generates a self-contained HTML dashboard.

## Quick Reference
- **Data source:** `~/Desktop/Final QA REPORTS/*.pdf` (63 PDFs, 37 unique units)
- **Extraction:** `python3 tools/extract_and_parse.py` → `data/inspections.json`
- **Dashboard:** `python3 generate_dashboard.py` → `OMNIcheck_SPC_Dashboard.html`
- **Events:** Add process annotations to `data/events.json`

## Architecture
- `tools/extract_and_parse.py` — PDF text extraction (PyMuPDF) + OCR (Tesseract 600 DPI) + regex parsing + dedup
- `generate_dashboard.py` — Reads JSON, computes SPC stats (numpy), generates self-contained HTML with Plotly.js (CDN)
- No Python plotly dependency — all chart rendering is in embedded JavaScript
- Dashboard is a single HTML file with data embedded as JSON in a `<script>` tag

## Dependencies
- Python 3.9+ with `pymupdf` and `numpy` (both pip-installable)
- Tesseract OCR (Homebrew: `brew install tesseract`)
- No runtime dependencies for the HTML dashboard (just a browser)

## Key Conventions
- Control limits always computed from the full dataset regardless of active filters
- WOB specs are USL-only (ISO 16900-5); volume specs are two-sided ±0.1 L (NFPA 1850); leak USL = 0.4 inWg
- 7 units have hardcoded leak pressure corrections in `extract_and_parse.py` due to OCR errors — verified from visual PDF reads
- OOC rules suppressed for zero-variation metrics (WOB A10)
- Unit ID prefixes: OCS/OCSA = MSA Firetech, OCA = AVON, OCB = ATOR Labs

## Data Format
`data/inspections.json` has structure:
```json
{
  "_meta": { "total_units": 37, "total_reports": 63, ... },
  "records": [ { "unit_id_canonical": "...", "wob_A_10": 0.06, ... }, ... ]
}
```

## Adding New Data
1. Drop new PDF into `~/Desktop/Final QA REPORTS/`
2. Run `python3 tools/extract_and_parse.py`
3. Run `python3 generate_dashboard.py`
4. Open `OMNIcheck_SPC_Dashboard.html`

If OCR mangles a leak pressure, add a correction to the `leak_corrections` dict in `extract_and_parse.py` (search for "Manual corrections").
