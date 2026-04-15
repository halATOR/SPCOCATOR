# Receipt Inspection SPC Dashboard — Specification

**Document ID:** SPC-SPEC-002
**Status:** Draft
**Date:** 2026-04-15
**Author:** Rob Moran / ATOR Labs
**Project directory:** `~/Documents/OMNIcheck-SPC/`

---

## 1. Purpose

Extend SPCOCATOR with a receipt inspection SPC dashboard that tracks dimensional quality of incoming components over time. The dashboard enables detection of supplier process drift, provides evidence for supplier quality management (ISO 9001:2015 clause 8.4), and supports management review with a high-level incoming quality summary.

This is a **separate HTML file** from the final inspection dashboard, with a shared navigation bar for switching between the two. It follows the same visual language, statistical methods, and self-contained HTML architecture as the existing final inspection dashboard.

---

## 2. Source Data

### 2.1 Form Template
- **Master template:** `/Volumes/OC/Receipt Inspection Form_Dimensional Master.pdf`
- **QMS document ID:** QAF-009-005
- **Format:** Adobe AcroForm PDF with fillable fields, dropdowns, checkboxes, and e-signature
- **Structure:** 3 core pages (metadata, data grid, notes/signature) + dynamically added data pages for large lots

### 2.2 Completed Forms
- **Location:** `/Volumes/OC/OC QA Reports/Receipt Inspection QA Forms/Completed QA Forms/Dimensional/`
- **Count:** 21 forms (Oct 2025 – Mar 2026)
- **Filename convention:** `YYYY-MM-DD{Part Name}.pdf` (e.g., `2025-10-14Top Hat.pdf`)

### 2.3 Drawing Specifications
- **Location:** Embedded in the master template PDF, pages 4–11
- **Content:** One drawing per part with dimension identifiers, nominal values, and tolerances
- **Also available separately:** `/Volumes/OC/QA Drawings/` (Piston Cap, Top Hat, Trachea Base)

### 2.4 Products
Two products are receipt-inspected (form Dropdown3):
- **OmniCheck** — respiratory testing device (primary)
- **ABMS** — Automated Breathing Machine System

---

## 3. Part Registry

7 part numbers are defined in the master template. Spec limits are extracted from the embedded drawings.

### 3.1 Trachea Base (Trachea Flange)
- **Drawing:** 0000214, Rev A
- **Material:** ABS
- **Units:** inches
- **Forms:** 5

| POI | Identifier | Nominal | Tolerance | USL | LSL |
|-----|-----------|---------|-----------|-----|-----|
| 1 | OD | 7.130 | ±.020 | 7.150 | 7.110 |
| 2 | A | 7.000 | ±.050 | 7.050 | 6.950 |
| 3 | D1 | 1.750 | ±.005 | 1.755 | 1.745 |
| 4 | ID1 | 1.625 | ±.002 | 1.627 | 1.623 |
| 5 | ID2 | 1.500 | ±.005 | 1.505 | 1.495 |
| 6 | ID3 | 1.375 | +.003/-.000 | 1.378 | 1.375 |
| 7 | H | 0.375 | ±.050 | 0.425 | 0.325 |

> **Note:** Form dropdown says "Trachea Base"; drawing title says "Trachea Flange." Same part.

### 3.2 Top Hat (Injection Molded)
- **Drawing:** 000020J-I, Rev A
- **Material:** Injection molded
- **Units:** inches
- **Forms:** 5

| POI | Identifier | Nominal | Tolerance | USL | LSL |
|-----|-----------|---------|-----------|-----|-----|
| 1 | OD1 | 12.000 | ±.010 | 12.010 | 11.990 |
| 2 | OD2 | 10.375 | ±.015 | 10.390 | 10.360 |
| 3 | OD3 | 1.620 | ±.001 | 1.621 | 1.619 |
| 4 | OD4 | 1.525 | ±.001 | 1.526 | 1.524 |
| 5 | ID1 | 10.000 | ±.015 | 10.015 | 9.985 |
| 6 | ID2 | 1.399 | ±.005 | 1.404 | 1.394 |
| 7 | A | 1.000 | ±.050 | 1.050 | 0.950 |

### 3.3 Piston Cap
- **Drawing:** 00001HG, Rev A
- **Material:** PLA
- **Units:** inches
- **Forms:** 4

| POI | Identifier | Nominal | Tolerance | USL | LSL |
|-----|-----------|---------|-----------|-----|-----|
| 1 | OD | 9.625 | ±.050 | 9.675 | 9.575 |
| 2 | ID | 9.375 | ±.050 | 9.425 | 9.325 |
| 3 | D1 | 0.470 | ±.015 | 0.485 | 0.455 |
| 4 | D2 | 0.250 | ±.015 | 0.265 | 0.235 |
| 5 | H | 0.438 | ±.015 | 0.453 | 0.423 |

### 3.4 Piston Body
- **Drawing:** 00001JC, Rev A
- **Material:** PLA
- **Units:** inches
- **Forms:** 3

| POI | Identifier | Nominal | Tolerance | USL | LSL |
|-----|-----------|---------|-----------|-----|-----|
| 1 | OD | 9.250 | ±.005 | 9.255 | 9.245 |
| 2 | ID | 8.800 | ±.050 | 8.850 | 8.750 |
| 3 | D1 | 0.266 | ±.005 | 0.271 | 0.261 |
| 4 | D2 | 0.772 | ±.005 | 0.777 | 0.767 |
| 5 | D3 | 1.125 | ±.005 | 1.130 | 1.120 |
| 6 | D4 | 0.340 | ±.015 | 0.355 | 0.325 |
| 7 | D5 | 0.265 | ±.005 | 0.270 | 0.260 |
| 8 | D6 | 0.154 | ±.005 | 0.159 | 0.149 |
| 9 | H | 5.250 | ±.050 | 5.300 | 5.200 |

### 3.5 Piston Housing (Injection Molded Piston Cage)
- **Drawing:** 0000209-I, Rev A
- **Material:** Injection molded
- **Units:** inches
- **Forms:** 4

| POI | Identifier | Nominal | Tolerance | USL | LSL |
|-----|-----------|---------|-----------|-----|-----|
| 1 | OD1 | 12.000 | ±.020 | 12.020 | 11.980 |
| 2 | OD2 | 10.800 | ±.050 | 10.850 | 10.750 |
| 3 | OD3 | 13.750 | ±.005 | 13.755 | 13.745 |
| 4 | ID | 10.000 | ±.005 | 10.005 | 9.995 |
| 5 | A | 0.221 | ±.050 | 0.271 | 0.171 |
| 6 | H | 9.535 | ±.005 | 9.540 | 9.530 |

### 3.6 10mm Linear Shaft
- **Drawing:** 000020V, Rev A
- **Material:** Aluminum
- **Units:** mm
- **Forms:** 0 (no data yet)

| POI | Identifier | Nominal | Tolerance | USL | LSL |
|-----|-----------|---------|-----------|-----|-----|
| 1 | OD | 10.000 | ±.127 | 10.127 | 9.873 |
| 2 | H | 279.000 | ±.381 | 279.381 | 278.619 |

### 3.7 Lead Screw
- **Drawing:** DSK-00060281, Rev A
- **Material:** Engineered Polymer (Drylin)
- **Units:** inches
- **Forms:** 0 (no data yet)

| POI | Identifier | Nominal | Tolerance | USL | LSL |
|-----|-----------|---------|-----------|-----|-----|
| 1 | OD | 0.375 | +.000/-.002 | 0.375 | 0.373 |
| 2 | H1 | 5.275 | ±.005 | 5.280 | 5.270 |
| 3 | H2 | 6.000 | ±.005 | 6.005 | 5.995 |

---

## 4. Data Model

### 4.1 Unit of Observation
Each measurement of a **single dimension on a single incoming part** is one data point for SPC purposes. Within one form, multiple parts are measured (rows), each producing independent observations for each dimension (columns).

### 4.2 AcroForm Field Mapping

**Page 1 — Metadata:**

| Field Name | Content | Type |
|-----------|---------|------|
| `Dropdown1` | Inspector name | ComboBox |
| `Date1` | Inspection date (YYYY-MM-DD) | Text |
| `Dropdown2` | Part description | ComboBox |
| `Dropdown3` | Product (OmniCheck / ABMS) | ComboBox |
| `Text1` | Lot number | Text |
| `Text2` | PO number | Text |
| `Text3` | Drawing number | Text |
| `Text4` | Delivery quantity | Text |
| `Text5` | Inspection quantity | Text |
| `Text6`–`Text14` | POI labels (dimension identifiers, up to 9) | Text |

**Page 2 — Data Grid (first 10 parts):**

| Field Pattern | Content |
|--------------|---------|
| `POI {col}{row}` | Measurement value for POI column (1–9), part row (1–10). Exception: row 10 uses `{col}10` (e.g., `POI 110`) |

**Pages 3+ — Additional Data Pages (added via "Add Page" button):**

| Field Pattern | Content |
|--------------|---------|
| `P{N}.Point of Inspection Measured Dimensions Template.NORow{row}` | Part sequence number |
| `P{N}.Point of Inspection Measured Dimensions Template.POI {col}Row{row}` | Measurement value. Row 1 uses `Row1_2` suffix. |

Where `N` = page sequence number (starting at 3).

**Visual Inspection Checkboxes:**
- `Check Box{N}` (page 2) and prefixed variants on added pages
- SAT (satisfactory) / UNSAT (unsatisfactory) per row
- Paired checkboxes: odd = SAT, even = UNSAT (interleaved)

**Notes and Signature (last content page):**
- `Text27` — free-text notes
- `Signature28` — e-signature field

### 4.3 Value Types

Form field values fall into these categories:

| Value | Meaning | SPC Treatment |
|-------|---------|---------------|
| Numeric (e.g., `9.250`) | Measured dimension | **Variable data** — used in I-MR charts |
| `n/a` or blank | Dimension not measured for this part | Excluded |
| `FT` | Fit test (go/no-go gauge check, passed) | **Attribute data** — counted, not charted |
| `FC` | Fit check (functional check, passed) | **Attribute data** — counted, not charted |
| `fail` | Measured dimension failed spec | **Variable data if numeric available**, otherwise attribute |

### 4.4 Known Data Quality Issues

1. **Metric drift:** The dimensions actually measured under a given POI column may change between forms for the same part. The POI labels (Text6–Text14) on page 1 of each form are the source of truth for that form's column assignments. Values that are implausible for the labeled dimension (off by an order of magnitude from the drawing spec) should be flagged with a warning in the extraction log but still included in the dataset — they may represent intentional measurement changes.

2. **Inconsistent precision:** Measurements range from 2 to 4+ decimal places. No normalization needed — store as-is.

3. **Missing lot numbers:** Some forms have blank lot fields. These records are still valid.

### 4.5 Output Format

```json
{
  "_meta": {
    "total_forms": 21,
    "total_measurements": 683,
    "parts_with_data": ["Trachea Base", "Top Hat", "Piston Cap", "Piston Body", "Piston Housing"],
    "date_range": ["2025-10-08", "2026-03-27"],
    "extraction_date": "2026-04-15",
    "warnings": []
  },
  "part_registry": {
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
        "H":   {"nominal": 0.375, "usl": 0.425, "lsl": 0.325}
      }
    }
  },
  "forms": [
    {
      "filename": "2025-10-14Top Hat.pdf",
      "date": "2025-10-14",
      "inspector": "Sieggy Bennicoff Yundt",
      "part": "Top Hat",
      "product": "OmniCheck",
      "lot": "L00219",
      "drawing": "000020J-I",
      "delivery_qty": 15,
      "insp_qty": 15,
      "poi_labels": ["OD1", "OD2", "OD3", "OD4", "ID1", "ID2", "A"],
      "notes": "",
      "measurements": [
        {
          "part_seq": 1,
          "values": {"OD1": 11.96, "OD2": 10.37, "OD3": 1.619, "OD4": 1.529, "ID1": 9.962, "ID2": 1.398, "A": 1.000}
        }
      ],
      "attribute_checks": {
        "FT": {"OD1": 0, "OD3": 0},
        "FC": {},
        "fail": {},
        "visual_sat": 15,
        "visual_unsat": 0
      }
    }
  ]
}
```

---

## 5. Statistical Methods

### 5.1 Control Chart Type
**I-MR charts** for all numeric dimensions, same as final inspection.

Rationale: 100% inspection currently, but each received lot is small and irregular. Individual measurements are the natural subgroup. When sampling plans are adopted, migrate to Xbar-R with lot as subgroup.

### 5.2 Control Limit Calculation
Same formulas as final inspection:
- **CL:** X-bar (mean of all observations for that part + dimension)
- **UCL/LCL:** X-bar ± 3 × (MR-bar / d2), where d2 = 1.128
- **Calculated from the full dataset** regardless of active filters
- Control limits are recalculated when new data is added

### 5.3 Specification Limits
Drawn from the part registry (Section 3). Two-sided for all dimensions (USL and LSL). Asymmetric tolerances (e.g., ID3: +.003/-.000) produce asymmetric USL/LSL relative to nominal.

### 5.4 Out-of-Control Rules
Same three rules as final inspection:
- Rule 1: Any point beyond ±3σ
- Rule 2: 8 consecutive points same side of centerline
- Rule 3: 6 consecutive points trending

OOC rules are suppressed when σ = 0 (all identical values).

### 5.5 Cpk Calculation
`min(Cpu, Cpl)` for all dimensions (all have two-sided specs).
- Cpu = (USL - X-bar) / (3σ)
- Cpl = (X-bar - LSL) / (3σ)

### 5.6 X-Axis Ordering
Data points are plotted in **chronological order by inspection date**, then by part sequence within a form. This means a single lot receipt (one form with 15 parts) produces 15 consecutive points on the chart at the same date.

---

## 6. Dashboard Specification

### 6.1 Deliverable Format
**Single self-contained HTML file** — same architecture as final inspection.
- Plotly.js via CDN
- All data embedded as JSON
- Shareable, no dependencies

### 6.2 Generation
**Python script:** `modules/receipt_inspection/generate_receipt_dashboard.py`
- Reads `data/receipt_inspections.json`
- Computes I-MR statistics, Cpk, OOC detection per part per dimension
- Outputs `Receipt_Inspection_SPC_Dashboard.html`

### 6.3 Navigation Bar
Both dashboards include a shared nav bar at the top:
```
┌─────────────────────────────────────────────────────────┐
│  SPCOCATOR          [Final Inspection] [Receipt Inspection] │
└─────────────────────────────────────────────────────────┘
```
Active tab is highlighted. Links are relative (`./OMNIcheck_SPC_Dashboard.html`, `./Receipt_Inspection_SPC_Dashboard.html`).

### 6.4 Layout

```
┌─────────────────────────────────────────────────────────┐
│  Receipt Inspection SPC Dashboard      [ATOR Labs]       │
│  Nav: [Final Inspection] [Receipt Inspection*]           │
│                                                          │
│  Inspector Filter: [All] [Rob] [Sieggy] [...]           │
│  Part Filter: [All] [specific part dropdown]             │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  SUMMARY PANEL (shown when Part Filter = "All")          │
│                                                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ Trachea Base │ │  Top Hat     │ │ Piston Cap   │    │
│  │ 5 lots       │ │ 5 lots       │ │ 4 lots       │    │
│  │ 142 parts    │ │ 55 parts     │ │ 64 parts     │    │
│  │ OOC: 3       │ │ OOC: 0       │ │ OOC: 1       │    │
│  │ Worst Cpk:   │ │ Worst Cpk:   │ │ Worst Cpk:   │    │
│  │ ID1 = 0.82   │ │ OD3 = 1.45   │ │ D1 = 0.91    │    │
│  │ [■■■□□□□]    │ │ [■■■■■□□]    │ │ [■■■■□□□]    │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│  ... (one card per part with data)                       │
│                                                          │
│  Cpk Heatmap: Part × Dimension matrix, color-coded      │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  PART DETAIL (shown when a specific part is selected)    │
│                                                          │
│  Part: Top Hat (000020J-I) | Material: Injection Molded  │
│  Lots inspected: 5 | Total parts: 55 | OOC flags: 0     │
│                                                          │
│  Cpk Scorecards (per dimension)                          │
│  [OD1: 1.8 ■] [OD2: 2.1 ■] [OD3: 1.45 ■] ...         │
│                                                          │
│  SECTION: I-MR Charts per dimension                      │
│  [OD1 I-chart + MR subchart]                             │
│  [OD2 I-chart + MR subchart]                             │
│  [OD3 I-chart + MR subchart]                             │
│  ... (one per dimension that has numeric data)           │
│                                                          │
│  SECTION: Lot Summary Table                              │
│  Date | Lot | Qty Delivered | Qty Inspected | Notes      │
│                                                          │
│  SECTION: Attribute Check Summary                        │
│  (FT/FC/fail counts per dimension per lot)               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 6.5 Chart Specification (per I chart)

Same visual encoding as final inspection:

| Element | Visual |
|---------|--------|
| Data points | Circles, colored by lot |
| Center line (X-bar) | Solid gray |
| UCL / LCL (3σ) | Dashed red |
| USL / LSL (spec) | Dotted orange |
| Nominal | Thin dotted gray (new — receipt inspection has meaningful nominals) |
| OOC points (Rule 1) | Red triangle |
| Run rule violations | Amber diamond |
| Hover tooltip | Date, lot #, inspector, part seq #, value, spec, status |

X-axis: measurement sequence (chronological by date, then by part within lot)
Y-axis: dimension in appropriate units (inches or mm)

### 6.6 Color Scheme

Lot-based coloring (cycling through a palette) to visually distinguish different receipts on the same chart:

```python
LOT_COLORS = [
    "#2196F3",  # blue
    "#4CAF50",  # green
    "#FF9800",  # orange
    "#9C27B0",  # purple
    "#00BCD4",  # cyan
    "#F44336",  # red
    "#795548",  # brown
    "#607D8B",  # blue-gray
]
```

Control/spec lines use the same colors as final inspection.

### 6.7 Cpk Heatmap (Summary View)

Matrix with parts as rows, dimensions as columns. Each cell is color-coded:
- Green: Cpk >= 1.33
- Amber: 1.0 <= Cpk < 1.33
- Red: Cpk < 1.0
- Gray: insufficient data or no numeric measurements
- Blank: dimension not applicable to this part

Click a cell to navigate to that part's detail view with the relevant chart scrolled into view.

### 6.8 Filters

| Filter | Behavior |
|--------|----------|
| Part | Switches between summary view (All) and part detail view (specific part) |
| Inspector | Shows/hides measurements by inspector. Does not change control limits. |

### 6.9 Additional Features

**Lot Receipt Timeline:** Horizontal bar chart showing receipts over time, colored by part. Gives a visual history of when material came in.

**OOC Flag Table:** Sortable table of all out-of-control points across all parts: date, part, dimension, value, spec, rule violated, lot #.

**Print/Export:** Same browser-print approach as final inspection.

---

## 7. Data Pipeline

### 7.1 Step 1 — Extract Receipt Inspection Forms

**Script:** `modules/receipt_inspection/extract_receipt.py`

1. Scan `/Volumes/OC/OC QA Reports/Receipt Inspection QA Forms/Completed QA Forms/Dimensional/*.pdf`
2. For each PDF:
   a. Extract metadata from page 1 AcroForm fields
   b. Map POI labels from `Text6`–`Text14` to dimension identifiers
   c. Extract page 2 data grid (`POI {col}{row}` fields, rows 1–10)
   d. Detect and extract additional pages (`P{N}.Point of Inspection...` fields)
   e. Classify each value: numeric, n/a, FT, FC, fail, blank
   f. Parse numeric values as floats
   g. Extract notes from `Text27`
   h. Extract visual inspection checkboxes (SAT/UNSAT counts)
3. Look up spec limits from the embedded part registry
4. Validate: warn if any numeric value is implausible (>5× outside spec range)
5. Output: `data/receipt_inspections.json`

### 7.2 Step 2 — Generate Dashboard

**Script:** `modules/receipt_inspection/generate_receipt_dashboard.py`

1. Load `data/receipt_inspections.json`
2. For each part with data, for each dimension with numeric data:
   a. Compute I-MR statistics
   b. Compute Cpk
   c. Run OOC detection
3. Build the Cpk heatmap data
4. Generate self-contained HTML with embedded data and Plotly.js
5. Output: `Receipt_Inspection_SPC_Dashboard.html`

### 7.3 Adding New Data
When new receipt inspection forms are completed:
1. Completed form PDF is saved to the Dimensional folder on the OC drive
2. Re-run `python3 modules/receipt_inspection/extract_receipt.py`
3. Re-run `python3 modules/receipt_inspection/generate_receipt_dashboard.py`
4. Open `Receipt_Inspection_SPC_Dashboard.html`

---

## 8. Project File Structure (additions)

```
~/Documents/OMNIcheck-SPC/
├── ... (existing files)
├── modules/
│   └── receipt_inspection/
│       ├── __init__.py
│       ├── extract_receipt.py          ← AcroForm parser
│       └── generate_receipt_dashboard.py ← dashboard generator
├── data/
│   ├── ... (existing files)
│   └── receipt_inspections.json        ← extracted receipt data
└── Receipt_Inspection_SPC_Dashboard.html ← generated output
```

---

## 9. Out of Scope (v1)

- Supplier-level stratification (only 1 supplier per part currently)
- Attribute control charts for FT/FC/fail data (P-charts deferred)
- Automatic form-to-drawing spec reconciliation (metric drift is a known issue, not automated)
- Integration with RIQA scan-based inspection
- Real-time watcher (Phase 3 watcher can be extended later)
- In-process inspection forms

---

## 10. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Updated dimension list vs. drawing specs — which is current? | Spec limits may be stale for some dimensions | Non-blocking; using drawing specs from master template for v1. User has updated list for later. |
| 2 | What does "FT" mean exactly? | Classification of attribute data | Assumed "Fit Test" (go/no-go gauge, passed). Confirm with user. |
| 3 | What does "FC" mean exactly? | Classification of attribute data | Assumed "Fit Check" (functional check, passed). Confirm with user. |
| 4 | Piston Cap metric drift (POI 2 shifted from ID to unknown dim) | SPC continuity across forms | Parser will use per-form POI labels and warn on implausible values. Not blocking. |
