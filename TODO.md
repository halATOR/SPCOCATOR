# OMNIcheck SPC Dashboard — Feature TODO (All Complete)

All work modifies `generate_dashboard.py`. Data source: `data/inspections.json` (37 records, 3 techs, 3 config types, 11 metrics).

---

## 1. Cpk/Ppk Capability Scorecards

**What:** Color-coded scorecard panel at the top of the SPC Charts tab showing Cpk for each metric that has a spec limit (USL).

**Calculation:**
- Ppk = (USL - X̄) / (3 * σ)  where σ = sample std dev
- Cpk = (USL - X̄) / (3 * σ_within)  where σ_within = MR̄ / 1.128
- Since WOB specs are USL-only (one-sided), use Cpu = (USL - X̄) / (3σ)
- For leak_delta: USL = 0.4 inWg
- Volume metrics have no USL → show "N/A"

**Color coding:**
- Cpk >= 1.33: green (#4CAF50) — capable
- 1.0 <= Cpk < 1.33: amber (#FFC107) — marginal  
- Cpk < 1.0: red (#F44336) — not capable

**Layout:** Row of cards between the summary bar and the charts, each card ~120px wide showing metric name, Cpk value, and color background. Only shown on the SPC Charts tab.

**Metrics with USL (from METRICS list in generate_dashboard.py):**
```
wob_A_10: 0.07    wob_A_20: 0.24    wob_A_35: 0.65
wob_A_50: 1.28    wob_A_65: 2.12    wob_B_65: 0.65
wob_B_85: 1.10    wob_B_105: 1.66   leak_delta: 0.40
```

**Implementation:** Add to `build_chart_data()` — compute cpk per chart. Add HTML section. Add JS to render the cards (static, no filtering needed since Cpk uses full dataset).

---

## 2. First-Pass Yield

**What:** Percentage of units that passed all tests on their first inspection (no re-test). Displayed as a metric in the summary bar.

**Data needed:** The extraction script already has all 63 reports before dedup. Need to pass first-pass info into the dashboard.

**Calculation (in extract_and_parse.py):**
- Group all 63 reports by unit ID
- For each unit: if it has only 1 report, it's a first-pass. If multiple reports, the earliest-dated one is the first attempt — check if it's the same as the latest (i.e., no rework needed).
- Actually simpler: count units with only 1 PDF vs units with multiple PDFs. Units with 1 PDF = first-pass pass. Units with multiple = required re-test.
- FPY = (units with 1 report) / (total units) × 100%

**Implementation:**
1. In `extract_and_parse.py`: after dedup, compute `first_pass_count` and add to JSON metadata
2. In `generate_dashboard.py`: read from JSON, display in summary bar as "XX% FPY" 
3. Add a `_meta` key to inspections.json: `{"first_pass_yield": 0.XX, "first_pass_count": N, "total_units": 37, "retest_units": [list of unit IDs]}`

---

## 3. Production Throughput Chart

**What:** Bar chart showing units tested per month. X-axis = month, Y-axis = count. Stacked by config type.

**Data:** Group records by month (from date_iso), count per config type.

**Layout:** Full-width chart at the top of the SPC Charts tab (before the metric sections), or as its own section. Use the existing config type colors for stacking.

**Implementation:** Pure JS — group CHARTS[0].dates by YYYY-MM, count, render a Plotly bar chart. Add as the first section in the chartsContainer.

---

## 4. Export to PDF Button

**What:** Button in the header that exports the current view as a downloadable image/PDF.

**Implementation:** Use Plotly's built-in `Plotly.downloadImage()` for individual charts, or use `window.print()` with a print-specific CSS stylesheet. The simplest approach:
- Add a "Print / Export" button in the header
- On click: `window.print()`
- Add `@media print` CSS rules to: hide controls/filters, make charts full-width, force page breaks between sections, white background

This gives a clean PDF via the browser's native Print → Save as PDF.

---

## 5. Trend Annotations

**What:** Vertical dashed lines on all SPC charts marking known process events (new sensor batch, rev change, new tech, etc.).

**Data source:** A JSON file at `data/events.json`:
```json
[
  {"date": "2026-01-21", "label": "OCSA Rev A introduced", "color": "#9C27B0"},
  {"date": "2025-12-05", "label": "New sensor batch", "color": "#FF5722"}
]
```

**Implementation:**
1. Create `data/events.json` with an initial example or two (the OCSA introduction is real — first OCSA unit is 20260312OCSA52, tested 3/12/2026; but the build date in the unit ID suggests the rev started around 2026-03-12)
2. In `generate_dashboard.py`: load events.json if it exists, embed in HTML as JSON
3. In JS renderCharts: for each chart, add vertical line shapes for each event within the visible date range
4. Plotly shapes: `{type: 'line', x0: date, x1: date, y0: 0, y1: 1, yref: 'paper', line: {color, dash: 'dot', width: 1.5}}` plus an annotation for the label

---

## 6. Pareto of OOC by Metric

**What:** Horizontal bar chart showing which metrics generate the most OOC flags, sorted descending. Separate bars for "beyond limits" vs "run rule" using the existing red/amber colors.

**Layout:** New section at the bottom of the SPC Charts tab, or as a card at the top near the summary.

**Implementation:** Pure JS — iterate CHARTS, count ooc_flags by type per metric, render a Plotly horizontal bar chart with two stacked traces (beyond limits + run rules).

---

## 7. Gauge R&R Stub (table + note)

**What:** A section on the Technician Analysis tab showing a basic reproducibility summary:
- % of total variation attributable to technician (between-tech variance / total variance)
- Per-metric breakdown

**Calculation:**
- For each metric: compute overall variance, then within-tech variance (pooled), then between-tech variance
- %GRR (reproducibility only) = sqrt(between-tech variance) / sqrt(total variance) × 100
- If < 10%: acceptable. 10-30%: marginal. > 30%: unacceptable.

**Caveat:** With current data (28/7/2 split), this is statistically weak. Show the numbers but with a prominent warning.

**Implementation:** Add to `renderTechAnalysis()` in JS. New section below the summary table with a colored table similar to the Cpk scorecards.
