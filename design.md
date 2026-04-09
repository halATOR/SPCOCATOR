# Design

This document describes the architecture, data flow, and key design decisions for the OMNIcheck SPC Dashboard.

## Overview

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────────┐
│  PDF Reports (63)   │────▶│  extract_and_parse.py │────▶│  data/inspections.json   │
│  ~/Desktop/Final QA │     │  PyMuPDF + Tesseract  │     │  37 records + _meta      │
└─────────────────────┘     └──────────────────────┘     └────────────┬────────────┘
                                                                      │
                            ┌──────────────────────┐                  │
                            │  data/events.json     │──────┐          │
                            │  process annotations  │      │          │
                            └──────────────────────┘      ▼          ▼
                                                    ┌──────────────────────┐
                                                    │  generate_dashboard.py│
                                                    │  numpy + HTML gen     │
                                                    └──────────┬───────────┘
                                                               │
                                                               ▼
                                                    ┌──────────────────────┐
                                                    │  Dashboard.html       │
                                                    │  Self-contained       │
                                                    │  Plotly.js + JSON     │
                                                    └──────────────────────┘
```

The system is a two-stage pipeline: **extract** then **render**. There is no server, no database, and no runtime dependency beyond a browser.

## Repository Structure

```
SPCOCATOR/
├── CLAUDE.md                        # AI agent context
├── AUDIT_LOG.md                     # Implemented features and decision log
├── design.md                        # This file
├── generate_dashboard.py            # Stage 2: SPC computation + HTML generation
├── tools/
│   └── extract_and_parse.py         # Stage 1: PDF → structured JSON
├── data/
│   ├── inspections.json             # Extracted dataset (source of truth)
│   ├── inspections.csv              # Same data in tabular form
│   └── events.json                  # Process event annotations
└── OMNIcheck_SPC_Dashboard.html     # Generated output (single-file dashboard)
```

### Local-only files (gitignored)

```
├── SPEC.md                          # Full requirements specification
├── TODO.md                          # Feature backlog (historical)
```

## Stage 1: Data Extraction

**Script:** `tools/extract_and_parse.py`

### Input
PDF inspection reports at `~/Desktop/Final QA REPORTS/`. Each report is a single-page document containing metadata, WOB test results, leak test, captured volume, and sensor calibration data.

### Extraction Strategy

PDFs come in two formats:

| Format | Count | Method | Notes |
|--------|-------|--------|-------|
| Text-based | 11 | `pymupdf` direct text extraction | Clean, reliable |
| Image-based | 52 | Tesseract OCR at 600 DPI, `--psm 4` | Requires post-processing |

The image-based PDFs are software-generated screenshots (not scanned paper), so OCR quality is generally good. However, leak pressure values are occasionally mangled (spaces in numbers, wrong characters). Seven units have hardcoded corrections in a `leak_corrections` dict, each verified by visual PDF read.

### Parsing

All parsing uses regex on the extracted text. Key patterns:

- **Metadata:** Named fields (`Technician Name`, `Configuration Type`, etc.)
- **WOB results:** 8 sequential values extracted positionally — 5 Protocol A then 3 Protocol B. Labels ignored due to known alignment issues in some extractions.
- **Leak test:** Negative pressure values matching `(-\d+\.\d+)\s*\(?inW[a-z]\)?` from the line containing "60 Sec"
- **Volume:** Numeric values following "Avg Vol" header

### Deduplication

Many units have multiple reports (re-tests, accidental duplicates). The pipeline groups by unit ID and keeps the report with the latest `Date Performed`. Output: N=37 unique units.

### Validation

Every record is validated:
- WOB Protocol A values must be monotonically increasing
- WOB Protocol B values must be monotonically increasing
- Leak delta must be positive
- Volume must be in plausible range (0.5–5.0 L)

### Output Format

```json
{
  "_meta": {
    "total_units": 37,
    "total_reports": 63,
    "first_pass_count": 22,
    "retest_count": 15,
    "first_pass_yield": 0.5946,
    "retest_units": ["20240221OCS7", "..."]
  },
  "records": [
    {
      "unit_id_canonical": "20251001OCS21",
      "unit_id": "20251001OCS21",
      "date_performed": "10/1/2025",
      "date_iso": "2025-10-01",
      "technician": "Rob Moran",
      "config_type": "MSA Firetech",
      "leak_start": -8.64,
      "leak_end": -8.59,
      "leak_delta": 0.05,
      "wob_A_10": 0.06, "wob_A_20": 0.21, "wob_A_35": 0.62,
      "wob_A_50": 1.23, "wob_A_65": 2.05,
      "wob_B_65": 0.64, "wob_B_85": 1.10, "wob_B_105": 1.65,
      "vol_nfpa40": 1.68, "vol_nfpa102": 3.468,
      "filename": "20251001OCS21.pdf",
      "source": "text"
    }
  ]
}
```

## Stage 2: Dashboard Generation

**Script:** `generate_dashboard.py`

### Computation (Python / numpy)

1. **I-MR statistics** per metric: X̄, MR̄, UCL/LCL (3σ via MR̄/d₂), UCL_MR
2. **Cpk** — one-sided `(USL - X̄) / (3σ)` for WOB/leak, `min(Cpu, Cpl)` for volume
3. **OOC detection** — Rule 1 (beyond 3σ), Rule 2 (8 consecutive same side), Rule 3 (6 consecutive trending). Suppressed when σ = 0.

### HTML Generation

The dashboard is a single HTML file with all data and logic embedded:

```
┌─────────────────────────────────────────────────┐
│ <script> const CHARTS = [...]; </script>         │  ← JSON data blob
│ <script> const EVENTS = [...]; </script>         │  ← Event annotations
│ <script> const CONFIG_COLORS = {...}; </script>  │  ← Color scheme
│ <script src="plotly-CDN"></script>                │  ← Plotly.js from CDN
│ <script>                                         │
│   renderCpkCards();                              │  ← Static render
│   renderThroughput();                            │  ← Static render
│   renderPareto();                                │  ← Static render
│   renderCharts();                                │  ← Filtered render
│ </script>                                        │
└─────────────────────────────────────────────────┘
```

No Python plotly is used. All chart rendering happens in browser JavaScript via Plotly.js loaded from CDN. This keeps the Python side dependency-light (only numpy + pymupdf).

### Tab Architecture

| Tab | Content | Render trigger |
|-----|---------|----------------|
| SPC Charts | Control charts, Cpk cards, throughput, Pareto | `renderCharts()` on load + filter change |
| Technician Analysis | Box plots, summary table, Gauge R&R | `renderTechAnalysis()` on first tab switch (lazy) |

### Filter Model

Three independent filters combine with AND logic:

- **Time window** — clips the x-axis date range (All / Yearly / Quarterly / Monthly)
- **Config type** — shows/hides points by configuration (dropdown)
- **Technician** — shows/hides points by tech (checkboxes, multi-select)

Control limits and Cpk are **always** computed from the full unfiltered dataset. Filters only affect which points are visible.

## Metrics

### 11 SPC Metrics

| Key | Metric | Unit | Spec Source | Spec Type |
|-----|--------|------|-------------|-----------|
| `wob_A_10` | WOB @ 10 LPM (A) | kPa | ISO 16900-5 | USL only |
| `wob_A_20` | WOB @ 20 LPM (A) | kPa | ISO 16900-5 | USL only |
| `wob_A_35` | WOB @ 35 LPM (A) | kPa | ISO 16900-5 | USL only |
| `wob_A_50` | WOB @ 50 LPM (A) | kPa | ISO 16900-5 | USL only |
| `wob_A_65` | WOB @ 65 LPM (A) | kPa | ISO 16900-5 | USL only |
| `wob_B_65` | WOB @ 65 LPM (B) | kPa | ISO 16900-5 | USL only |
| `wob_B_85` | WOB @ 85 LPM (B) | kPa | ISO 16900-5 | USL only |
| `wob_B_105` | WOB @ 105 LPM (B) | kPa | ISO 16900-5 | USL only |
| `leak_delta` | Leak Pressure Drop | inWg | ISO 16900-5 | USL = 0.4 |
| `vol_nfpa40` | NFPA 40 Tidal Volume | L | NFPA 1850 | ±0.1 L |
| `vol_nfpa102` | NFPA 102 Tidal Volume | L | NFPA 1850 | ±0.1 L |

### Unit ID Prefixes

| Prefix | Product Variant | Config Type |
|--------|----------------|-------------|
| OCS | OMNIcheck Standard | MSA Firetech |
| OCSA | OMNIcheck Standard Rev A | MSA Firetech |
| OCA | OMNIcheck AVON | AVON |
| OCB | OMNIcheck Breathe | ATOR Labs |

Legacy format: `OC-MMDDYYYY-NN` (mapped to MSA Firetech)

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single HTML output | No server needed; shareable as email attachment; opens in any browser |
| Plotly.js via CDN (not Python plotly) | Keeps Python deps minimal; all interactivity in JS |
| OCR at 600 DPI with `--psm 4` | Best balance of accuracy and speed for these software-generated image PDFs |
| Hardcoded OCR corrections | 7 units had mangled leak values; corrections verified from visual PDF reads. Pragmatic vs over-engineering the regex. |
| I-MR charts (not Xbar-R) | Production rate ~2-3 units/month, subgroup size = 1 |
| Control limits from full dataset | Filters are for visual exploration; statistical baselines should not shift with filter state |
| OOC rules suppressed at σ=0 | WOB A10 reads 0.06 for all 37 units — measurement resolution floor, not a real signal |
| Two OOC marker styles | Red triangles (beyond limits) vs amber diamonds (run rules) — different severity, different action |
| Lazy tech tab render | Box plots + Gauge R&R only computed when tab is first opened, avoiding startup cost |

## Extension Points

### Adding a new metric
1. Add extraction regex to `extract_and_parse.py` (in `parse_text_based` and `parse_ocr_text`)
2. Add field to CSV `fieldnames` list
3. Add tuple to `METRICS` list in `generate_dashboard.py`: `(key, label, section, spec_limit)`
4. Regenerate

### Adding a process event
Append to `data/events.json`:
```json
{"date": "2026-05-01", "label": "Description", "color": "#FF5722"}
```

### Adding a new config type
1. Add prefix mapping to `PREFIX_CONFIG` in `extract_and_parse.py`
2. Add color to `CONFIG_COLORS` in `generate_dashboard.py`
