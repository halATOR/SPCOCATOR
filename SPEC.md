# OMNIcheck SPC Dashboard — Specification & Requirements

**Document ID:** SPC-SPEC-001  
**Status:** Draft  
**Date:** 2026-04-08  
**Author:** Rob Moran / ATOR Labs  
**Project directory:** `~/Documents/OMNIcheck-SPC/`

---

## 1. Purpose

Develop statistical process control (SPC) limits for the OMNIcheck final inspection metrics and deliver an interactive dashboard that visualizes unit-by-unit performance trends across time. The dashboard enables early detection of process drift, supports ISO 9001:2015 continuous improvement objectives, and provides evidence of sustained product quality.

---

## 2. Source Data

### 2.1 Raw Reports
- **Location:** `~/Desktop/Final QA REPORTS/`
- **Count:** 63 PDF reports covering **37 unique units** (Feb 2024 – Mar 2026)
- **Multiple reports per unit:** Many units have 2–6 PDFs with different test dates (re-tests, recalibrations, or configuration changes). See Section 2.5 for how to select which report enters the SPC dataset.
- **Format:** Paired `.pdf` + `.bin` per unit/test; 11 `.md` files with pre-parsed content (see Section 2.3 caveat)

### 2.2 Binary Data Files
- **Location:** `~/Desktop/Final QA REPORTS/Raw Data/`
- **Count:** 55 `.bin` files (~110 KB each) covering 35 unique units
- **Format:** Custom proprietary binary — length-prefixed UTF-8 strings (4-byte big-endian length header) followed by IEEE 754 floating-point measurement data
- **Parsing strategy:** Reverse-engineer field layout by correlating known numeric values against binary float sequences. Validate using **physical constraints** (WOB results must monotonically increase within each protocol, leak delta must be positive, volume must be positive) rather than relying solely on extracted markdown (see Section 2.3 caveat).

### 2.3 Fallback Extraction & Markdown Caveat
- For any units whose `.bin` cannot be fully parsed, extract data from the corresponding PDF using `pymupdf4llm` (already available in the vault toolchain)
- **CAVEAT:** The 11 pre-parsed `.md` files have **column alignment issues** in the WOB table. The original PDF uses a side-by-side layout (leak test left, WOB right) that causes the markdown extraction to shift RMV labels and WOB limit labels relative to result values. Specifically, in some extractions rows 6–8 have their RMV/limit columns shifted up by one position while the Result column remains correct. The `.md` files **cannot be used as unvalidated ground truth** — results must be cross-checked for monotonicity and physical plausibility before use.

### 2.4 Unit ID Format
Unit IDs encode manufacture date and sequential serial. Two formats exist:

**Current format:** `YYYYMMDD[prefix]NN`
- **OCS** — OMNIcheck Standard (e.g., `20251001OCS21`) → Config: MSA Firetech
- **OCA** — OMNIcheck AVON (e.g., `20251023OCA27`) → Config: AVON
- **OCB** — OMNIcheck Breathe (e.g., `20251017OCB29`) → Config: ATOR Labs
- **OCSA** — OMNIcheck Standard, Rev A — new design revision (e.g., `20260312OCSA52`) → Config: MSA Firetech (same as OCS)

**Legacy format:** `OC-MMDDYYYY-NN` (e.g., `OC-10042024-13`)

Note: The date in the Unit ID is the **manufacture/build date**, not the test date. The test date is in the "Date Performed" field inside the report. These can differ by weeks or months.

### 2.5 Report Selection for SPC
With 63 reports across 37 units, the dataset uses the **latest report per unit** (N=37).

Rationale: Units may be tested multiple times during production (re-calibration, rework, or accidental duplicate exports). The most recent report represents the unit's final released state. Deduplication selects by unit ID, keeping the report with the latest "Date Performed" value. Ties are broken by filename (lexicographically last).

---

## 3. Metrics

The following measurements are recorded per unit and are candidates for SPC tracking. All are continuous numeric values (not pass/fail).

### 3.1 Leak Tightness Test

| Metric | Field | Units | Spec |
|--------|-------|-------|------|
| Start pressure | `leak_start_pressure` | inWg | — |
| End pressure | `leak_end_pressure` | inWg | — |
| **Pressure differential** | `leak_delta` (derived: abs(start) − abs(end)) | inWg | See note |

> SPC tracks `leak_delta` (the drop over 60 seconds). Larger drop = worse seal. Start pressure values observed: −8.40 to −11.31 inWg. Observed delta range: 0.05–0.36 inWg.
>
> **Spec limit:** USL = 0.1 kPa = 0.4 inWg (max allowable pressure drop over 60 seconds). All 6 parsed reports pass with margin (max observed: 0.21 inWg). Dashboard displays the USL in inWg (native report units).

### 3.2 Work of Breathing (WOB)

Two test protocols (A and B) run on every unit. 8 total measurement rows per report. All results are in kPa and represent upper-limit specifications (lower WOB is better). Results must be monotonically increasing within each protocol.

**Protocol A — 5 levels (standard breathing circuit):**

| Metric | Field | Units | USL (nom ± tol) | Observed range |
|--------|-------|-------|------------------|----------------|
| WOB @ 10 LPM | `wob_A_10` | kPa | 0.06 ± 0.01 | 0.06 (constant) |
| WOB @ 20 LPM | `wob_A_20` | kPa | 0.22 ± 0.02 | 0.21–0.22 |
| WOB @ 35 LPM | `wob_A_35` | kPa | 0.62 ± 0.03 | 0.60–0.64 |
| WOB @ 50 LPM | `wob_A_50` | kPa | 1.22 ± 0.06 | 1.20–1.27 |
| WOB @ 65 LPM | `wob_A_65` | kPa | 2.02 ± 0.10 | 1.95–2.11 |

**Protocol B — 3 levels (alternate breathing circuit):**

| Metric | Field | Units | USL (nom ± tol) | Observed range |
|--------|-------|-------|------------------|----------------|
| WOB @ 65 LPM | `wob_B_65` | kPa | 0.62 ± 0.03 | 0.61–0.65 |
| WOB @ 85 LPM | `wob_B_85` | kPa | 1.05 ± 0.05 | 1.04–1.10 |
| WOB @ 105 LPM | `wob_B_105` | kPa | 1.58 ± 0.08 | 1.58–1.65 |

> **Note on extraction artifacts:** Some `.md` extractions show a phantom "85 LPM Protocol A" row with limit 3.39 ± 0.17 kPa. This row exists in the PDF template but is **not measured**. Its label bleeds into the Protocol B rows during extraction, shifting the RMV/limit columns by one position while the Result column remains correct. The correctly-extracted reports (OCS32, OCS43) confirm the 5A+3B structure. All units run both protocols.
>
> **Note on spec limits as USL only:** WOB specifications are upper limits — lower WOB is always better. The dashboard should display USL (nominal + tolerance) as the spec line, with no LSL. The nominal ± tolerance values derive from **ISO 16900-5** (Respiratory protective devices — Test methods and test equipment — Part 5: Breathing machine, metabolic simulator, RPD headforms).

### 3.3 Captured Volume

| Metric | Field | Units | Spec (NFPA 1850) | Observed range |
|--------|-------|-------|------------------|----------------|
| NFPA 40 tidal volume | `vol_nfpa40` | L | 1.665 ± 0.1 (LSL=1.565, USL=1.765) | 1.654–1.687 |
| NFPA 102 tidal volume | `vol_nfpa102` | L | 3.4 ± 0.1 (LSL=3.3, USL=3.5) | 3.357–3.468 |

> Spec limits are two-sided per **NFPA 1850** (Standard on Selection, Care, and Maintenance of Open-Circuit Self-Contained Breathing Apparatus). Std deviation and achieved RMV values are printed on the reports but not extracted into the SPC dataset (they show negligible variation).

### 3.4 Excluded from SPC
- Sensor calibration accuracy — these are instrument specifications (not measured performance values); no process variation to track. However, sensor serial numbers are captured per unit for traceability.
- Pass/Fail status — binary, not suitable for variable control charts
- Gasometer serial number — constant (2852) across all reports; reference equipment, not a process variable

---

## 4. Statistical Methods

### 4.1 Control Chart Type
**Individuals and Moving Range (I-MR) charts** for all metrics.

Rationale: Production rate is ~2–3 units/month; subgroup size = 1. I-MR is the statistically correct choice for individual unit data. As production volume increases (subgroup size ≥ 2 regularly), migrate to Xbar-R.

### 4.2 Control Limit Calculation
- **Center line (CL):** X̄ (mean of all observations)
- **Control limits:** UCL = X̄ + 3 × (MR̄ / d₂), LCL = X̄ − 3 × (MR̄ / d₂)
  - Where MR̄ = average moving range (consecutive pairs), d₂ = 1.128 for n=2
- **Calculated from the full dataset** regardless of active filter
- Control limits are recalculated when new data is added

### 4.3 Specification Limits
Drawn separately from control limits (different color) using the nominal ± tolerance values from Section 3 above.
- **WOB charts:** USL only (nominal + tolerance per ISO 16900-5). WOB is an upper-limit specification — there is no lower spec limit because lower WOB is always acceptable.
- **Leak test chart:** USL = 0.4 inWg (= 0.1 kPa). No LSL.
- **Volume charts:** Two-sided limits per NFPA 1850. NFPA 40: 1.665 ± 0.1 L (LSL=1.565, USL=1.765). NFPA 102: 3.4 ± 0.1 L (LSL=3.3, USL=3.5).

### 4.4 Out-of-Control Rules Applied
- Rule 1: Any single point beyond ±3σ (UCL/LCL)
- Rule 2: 8 consecutive points on the same side of the centerline (run rule)
- Rule 3: 6 consecutive points trending in one direction

Out-of-control points are visually flagged on the chart (distinct marker symbol + color).

### 4.5 Configuration Type Stratification
- Statistical test (Welch's t-test or Kruskal-Wallis H) run at dataset build time to determine whether any metric differs significantly across configuration types (MSA Firetech, AVON, ATOR Labs)
- If no significant difference detected: control limits use the combined population; color-coding by config type is cosmetic only
- If significant difference detected: chart is annotated with a warning; user can filter to see per-config limits

---

## 5. Dashboard Specification

### 5.1 Deliverable Format
**Single self-contained HTML file** — no server, no runtime dependencies, no install.  
- All JavaScript (Plotly.js) bundled inline or loaded from CDN with offline fallback
- Can be opened in any modern browser (Chrome, Safari, Firefox)
- Shareable as an email attachment or file share
- Regenerated by re-running a Python script whenever new data is added

### 5.2 Generation
**Python script** at `~/Documents/OMNIcheck-SPC/generate_dashboard.py`  
- Reads structured dataset from `data/inspections.json` (or `.csv`)
- Computes control limits, runs OOC tests
- Outputs `OMNIcheck_SPC_Dashboard.html`

### 5.3 Layout

```
┌─────────────────────────────────────────────────────────┐
│  OMNIcheck SPC Dashboard          [ATOR Labs logo/title] │
│                                                          │
│  Time Window: [All Time] [Yearly] [Quarterly] [Monthly]  │
│  Unit Type Filter: [All] [MSA Firetech] [AVON] [ATOR]   │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  SUMMARY PANEL                                           │
│  Total units: N  |  Date range: …  |  OOC flags: N      │
├─────────────────────────────────────────────────────────┤
│  SECTION: Work of Breathing (Protocol A)                 │
│  [WOB 10 LPM chart] [WOB 20 LPM chart]                  │
│  [WOB 35 LPM chart] [WOB 50 LPM chart]                  │
│  [WOB 65 LPM chart]                                      │
├─────────────────────────────────────────────────────────┤
│  SECTION: Work of Breathing (Protocol B)                 │
│  [WOB 65 LPM chart] [WOB 85 LPM chart]                  │
│  [WOB 105 LPM chart]                                     │
├─────────────────────────────────────────────────────────┤
│  SECTION: Leak Test & Volume                             │
│  [Pressure Δ chart]  [NFPA 40 Vol chart]                 │
│  [NFPA 102 Vol chart]                                    │
└─────────────────────────────────────────────────────────┘
```

### 5.4 Chart Specification (per I chart)

Each individual chart displays:

| Element | Visual encoding |
|---------|----------------|
| Data points | Circles, colored by configuration type (see color scheme) |
| Center line (X̄) | Solid gray horizontal line |
| UCL / LCL (3σ) | Dashed red lines |
| USL / LSL (spec limits) | Dotted orange lines |
| Out-of-control points | Filled red triangle marker, red glow |
| Run-rule violations | Yellow diamond marker |
| Hover tooltip | Unit ID, date, technician, config type, value, status |

X-axis: inspection date (chronological)  
Y-axis: measurement in appropriate units

Each chart is accompanied by a **Moving Range (MR) subchart** directly below it (same x-axis, half the height).

### 5.5 Color Scheme

**Configuration types:**
| Config | Color |
|--------|-------|
| MSA Firetech | `#2196F3` (blue) |
| AVON | `#4CAF50` (green) |
| ATOR Labs | `#9C27B0` (purple) |

**Control and spec lines:**
| Line | Color |
|------|-------|
| Center line | `#9E9E9E` (gray) |
| UCL / LCL | `#F44336` dashed (red) |
| USL / LSL | `#FF9800` dotted (orange) |
| OOC point | `#F44336` filled triangle (red) |
| Run rule violation | `#FFC107` diamond (amber) |

### 5.6 Time Window Behavior
- **All Time:** full dataset, all points visible
- **Yearly:** last 12 months of data
- **Quarterly:** last 3 months of data
- **Monthly:** last 30 days of data
- Control limits are **always computed from the full dataset**, regardless of selected window
- The filtered view zooms the x-axis but the UCL/LCL/X̄ lines remain anchored to global values

### 5.7 Configuration Type Filter
- Dropdown or toggle buttons
- "All" is the default
- Filtering changes which data points are visible and their opacity; it does not change control limits
- When a single config is selected, the chart title updates to indicate the filter is active

### 5.8 Technician Filter
- Checkbox per technician, all checked by default
- Unchecking hides that technician's data points across all charts
- Does not affect control limits

### 5.9 Additional Dashboard Features

**Cpk Scorecards:** Row of color-coded cards showing process capability index per metric. Green (Cpk >= 1.33), amber (1.0–1.33), red (< 1.0), gray (no spec limit). Cpk uses one-sided Cpu for WOB/leak (USL only), min(Cpu, Cpl) for volume (two-sided). Computed from full dataset.

**Production Throughput Chart:** Stacked bar chart showing units tested per month, colored by configuration type.

**OOC Pareto Chart:** Horizontal bar chart ranking metrics by total OOC flags, split into "Beyond Limits" (red) and "Run Rules" (amber).

**Trend Annotations:** Vertical dotted lines on all SPC charts marking process events loaded from `data/events.json`.

**Print / Export:** Button triggers browser print dialog. Print-specific CSS hides controls and formats charts for clean PDF output.

**Technician Analysis Tab:** Separate tab with:
- Box plots per metric grouped by technician (with individual data points overlaid)
- Summary table with N, Mean, Std Dev per tech per metric
- Gauge R&R reproducibility table showing between-tech variation as % of total variation, with acceptability rating (< 10% acceptable, 10–30% marginal, > 30% unacceptable)

---

## 6. Data Pipeline

### 6.1 Step 1 — Extract and Parse PDFs
Script: `tools/extract_and_parse.py`  
- Scans `~/Desktop/Final QA REPORTS/*.pdf` (all 63 reports)
- Text-based PDFs (11 files): direct text extraction via PyMuPDF
- Image-based PDFs (52 files): OCR via Tesseract at 600 DPI (`--psm 4`)
- 7 units have manual leak pressure corrections for OCR-mangled values (verified from visual PDF reads)
- Parses metadata, WOB (8 values), leak test, and volume via regex
- Deduplicates to latest report per unit (N=37)
- Validates: WOB monotonicity, leak delta positive, volume plausibility
- Output: `data/inspections.json` (with `_meta` block for FPY stats) and `data/inspections.csv`

### 6.2 Step 2 — Generate Dashboard
Script: `generate_dashboard.py`  
- Loads `data/inspections.json` and optionally `data/events.json`
- Computes I-MR statistics, Cpk, and OOC detection for each metric
- Generates self-contained HTML with Plotly.js via CDN
- Output: `OMNIcheck_SPC_Dashboard.html`

### 6.3 X-Axis Chronology
The x-axis on all charts uses the **Date Performed** (test date), not the build date embedded in the unit ID. These can differ by weeks or months. This ensures the charts reflect when the measurement was taken, which is what matters for SPC trend analysis.

### 6.4 Adding New Data
When new inspection reports arrive:
1. Drop the PDF into `~/Desktop/Final QA REPORTS/`
2. Re-run `python3 tools/extract_and_parse.py`
3. Re-run `python3 generate_dashboard.py`
4. Open `OMNIcheck_SPC_Dashboard.html`

### 6.5 Adding Process Events
To annotate charts with process changes (new sensor batch, rev change, etc.), add entries to `data/events.json`:
```json
{"date": "2026-05-01", "label": "New sensor batch", "color": "#FF5722"}
```

---

## 7. Project File Structure

```
~/Documents/OMNIcheck-SPC/
├── SPEC.md                        ← this document
├── TODO.md                        ← feature backlog and implementation notes
├── generate_dashboard.py          ← dashboard generator (reads JSON, outputs HTML)
├── data/
│   ├── inspections.json           ← structured dataset with _meta block
│   ├── inspections.csv            ← same data in tabular form
│   └── events.json                ← process event annotations for charts
├── tools/
│   └── extract_and_parse.py       ← PDF extraction + OCR + parsing + dedup
└── OMNIcheck_SPC_Dashboard.html   ← generated output
```

---

## 8. Open Questions / Decisions Pending

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | ~~Which reports enter SPC?~~ | — | **RESOLVED:** Latest report per unit, N=37 |
| 2 | ~~What do the unit prefixes mean?~~ | — | **RESOLVED:** OCS=Standard, OCA=AVON, OCB=Breathe, OCSA=Standard Rev A |
| 3 | ~~Why do some units have many re-tests?~~ | — | **RESOLVED:** Likely rework cycles. No special handling needed — latest report captures final state. |
| 4 | Is there a minimum subgroup size policy for when to migrate from I-MR to Xbar-R? | Future migration plan | Non-blocking; revisit when production rate supports subgroups |
| 5 | ~~Fully offline HTML or CDN?~~ | — | **RESOLVED:** CDN with inline fallback |
| 6 | ~~Is there a numeric spec limit for the leak test?~~ | — | **RESOLVED:** USL = 0.1 kPa = 0.4 inWg |
| 7 | ~~Are there spec limits for captured volume?~~ | — | **RESOLVED:** ±0.1 L per NFPA 1850. Two-sided limits on dashboard. |

---

## 9. Out of Scope (v1)

- Web server / hosted dashboard
- Real-time data ingestion (auto-poll for new files)
- Integration with the Memory-Layer vault (this project uses the vault's tools and conventions but is maintained independently)
- Gauge R&R / Measurement System Analysis
- Attribute control charts (P or U charts for defect rates)

---

## 10. Success Criteria

- [x] All 37 unique units parsed and in `inspections.json` (latest report per unit)
- [x] No missing WOB fields; all 8 WOB values (5A + 3B) present per report
- [x] WOB results validated for monotonicity within each protocol (37/37 pass)
- [x] I-MR charts generated for all 11 metrics (5 WOB-A + 3 WOB-B + leak + 2 volume)
- [x] Control limits calculated correctly (validated against manual calculation for WOB A20)
- [x] USL visible on all WOB and leak charts; USL+LSL on volume charts
- [x] Time window toggle functional (All/Yearly/Quarterly/Monthly)
- [x] Config type filter functional and does not alter control limits
- [x] Technician checkbox filter functional
- [x] Cpk scorecards displayed for all metrics with spec limits
- [x] Production throughput chart (stacked bar by month)
- [x] OOC Pareto chart (beyond limits vs run rules)
- [x] Trend annotations from events.json
- [x] Technician Analysis tab with box plots, summary table, and Gauge R&R
- [x] Print/export via browser print dialog
- [x] Dashboard opens in Chrome/Safari/Firefox without errors
- [x] Single HTML file (~67 KB), sharable with no dependencies
