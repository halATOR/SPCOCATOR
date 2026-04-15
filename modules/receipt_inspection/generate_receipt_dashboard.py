#!/usr/bin/env python3
"""
Generate Receipt Inspection SPC Dashboard — self-contained HTML with Plotly.js.

Reads data/receipt_inspections.json, computes I-MR control limits per part per
dimension, detects OOC points, and generates a single HTML file with interactive
charts. Mirrors the visual language of the final inspection SPC dashboard.

Usage:
    python3 modules/receipt_inspection/generate_receipt_dashboard.py
"""

import json
import math
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = PROJECT_DIR / "data" / "receipt_inspections.json"
OUTPUT_PATH = PROJECT_DIR / "Receipt_Inspection_SPC_Dashboard.html"

LOT_COLORS = [
    "#2196F3", "#4CAF50", "#FF9800", "#9C27B0",
    "#00BCD4", "#F44336", "#795548", "#607D8B",
    "#E91E63", "#3F51B5", "#009688", "#FF5722",
]


def compute_imr(values):
    """Compute I-MR control chart statistics."""
    n = len(values)
    if n < 2:
        return None
    arr = np.array(values, dtype=float)
    x_bar = float(np.mean(arr))
    mr = np.abs(np.diff(arr))
    mr_bar = float(np.mean(mr))
    d2 = 1.128
    sigma = mr_bar / d2
    ucl_i = x_bar + 3 * sigma
    lcl_i = x_bar - 3 * sigma
    ucl_mr = 3.267 * mr_bar
    return {
        "x_bar": round(x_bar, 6),
        "mr_bar": round(mr_bar, 6),
        "ucl_i": round(ucl_i, 6),
        "lcl_i": round(lcl_i, 6),
        "ucl_mr": round(ucl_mr, 6),
        "sigma": round(sigma, 6),
        "mr_values": [round(float(v), 6) for v in mr],
    }


def detect_ooc(values, stats):
    """Detect out-of-control points using Western Electric rules."""
    flags = []
    n = len(values)
    x_bar = stats["x_bar"]
    ucl = stats["ucl_i"]
    lcl = stats["lcl_i"]
    has_variation = stats["sigma"] > 1e-9

    for i in range(n):
        point_flags = []
        if has_variation and (values[i] > ucl or values[i] < lcl):
            point_flags.append("rule1")
        if has_variation:
            if i >= 7:
                window = values[i - 7 : i + 1]
                if all(v > x_bar for v in window) or all(v < x_bar for v in window):
                    point_flags.append("rule2")
            if i >= 5:
                window = values[i - 5 : i + 1]
                diffs = [window[j + 1] - window[j] for j in range(5)]
                if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
                    point_flags.append("rule3")
        flags.append(point_flags)
    return flags


def build_chart_data(data):
    """Build chart data for all parts and dimensions."""
    part_registry = data["part_registry"]
    forms = data["forms"]

    # Collect measurements per part per dimension, in chronological order
    part_dims = {}  # {part_name: {dim_label: [{"value":..., "date":..., "lot":..., ...}]}}

    for form in forms:
        part = form["part"]
        if not part:
            continue
        if part not in part_dims:
            part_dims[part] = {}

        for meas in form["measurements"]:
            for dim_label, val in meas["values"].items():
                if dim_label not in part_dims[part]:
                    part_dims[part][dim_label] = []
                part_dims[part][dim_label].append({
                    "value": val,
                    "date": form["date_iso"],
                    "lot": form.get("lot", ""),
                    "inspector": form.get("inspector", ""),
                    "part_seq": meas["part_seq"],
                    "filename": form["filename"],
                })

    # Build chart objects
    all_charts = {}  # {part_name: [chart_dict, ...]}

    for part_name, dims in sorted(part_dims.items()):
        specs = part_registry.get(part_name, {}).get("dimensions", {})
        units = part_registry.get(part_name, {}).get("units", "inches")
        charts = []

        for dim_label, points in dims.items():
            values = [p["value"] for p in points]
            dates = [p["date"] for p in points]
            lots = [p["lot"] for p in points]
            inspectors = [p["inspector"] for p in points]
            part_seqs = [p["part_seq"] for p in points]
            filenames = [p["filename"] for p in points]

            if len(values) < 2:
                continue

            stats = compute_imr(values)
            if not stats:
                continue

            ooc_flags = detect_ooc(values, stats)

            spec = specs.get(dim_label, {})
            usl = spec.get("usl")
            lsl = spec.get("lsl")
            nominal = spec.get("nominal")

            # Cpk
            cpk = None
            if stats["sigma"] > 1e-9:
                parts = []
                if usl is not None:
                    parts.append((usl - stats["x_bar"]) / (3 * stats["sigma"]))
                if lsl is not None:
                    parts.append((stats["x_bar"] - lsl) / (3 * stats["sigma"]))
                if parts:
                    cpk = round(min(parts), 2)

            charts.append({
                "dim": dim_label,
                "label": f"{dim_label} ({units})",
                "unit": units,
                "usl": usl,
                "lsl": lsl,
                "nominal": nominal,
                "cpk": cpk,
                "values": [round(v, 6) for v in values],
                "dates": dates,
                "lots": lots,
                "inspectors": inspectors,
                "part_seqs": part_seqs,
                "filenames": filenames,
                "stats": stats,
                "ooc_flags": ooc_flags,
            })

        if charts:
            all_charts[part_name] = charts

    return all_charts


def build_summary_data(all_charts, data):
    """Build summary cards for the overview."""
    part_registry = data["part_registry"]
    forms = data["forms"]
    summaries = []

    for part_name, charts in sorted(all_charts.items()):
        part_forms = [f for f in forms if f["part"] == part_name]
        total_parts = sum(len(f["measurements"]) for f in part_forms)
        beyond_limits = sum(1 for c in charts for flags in c["ooc_flags"] if any(f == "rule1" for f in flags))
        run_rules = sum(1 for c in charts for flags in c["ooc_flags"] if flags and not any(f == "rule1" for f in flags))

        # Worst Cpk
        cpks = [(c["dim"], c["cpk"]) for c in charts if c["cpk"] is not None]
        worst_cpk = min(cpks, key=lambda x: x[1]) if cpks else (None, None)

        summaries.append({
            "part": part_name,
            "drawing": part_registry.get(part_name, {}).get("drawing", ""),
            "material": part_registry.get(part_name, {}).get("material", ""),
            "lots": len(part_forms),
            "total_parts": total_parts,
            "beyond_limits": beyond_limits,
            "run_rules": run_rules,
            "worst_cpk_dim": worst_cpk[0],
            "worst_cpk_val": worst_cpk[1],
            "n_dims_charted": len(charts),
        })

    return summaries


def build_heatmap_data(all_charts):
    """Build Cpk heatmap: parts x dimensions."""
    # Collect all dimension labels across all parts
    all_dims = set()
    for charts in all_charts.values():
        for c in charts:
            all_dims.add(c["dim"])
    all_dims = sorted(all_dims)

    parts = sorted(all_charts.keys())
    matrix = []
    for part in parts:
        row = []
        charts_by_dim = {c["dim"]: c for c in all_charts[part]}
        for dim in all_dims:
            c = charts_by_dim.get(dim)
            if c is None:
                row.append(None)
            elif c["cpk"] is None:
                row.append(-1)  # insufficient data
            else:
                row.append(c["cpk"])
        matrix.append(row)

    return {"parts": parts, "dims": all_dims, "matrix": matrix}


def build_ooc_table(all_charts):
    """Build a flat table of all OOC points."""
    rows = []
    for part_name, charts in sorted(all_charts.items()):
        for c in charts:
            for i, flags in enumerate(c["ooc_flags"]):
                if flags:
                    rows.append({
                        "part": part_name,
                        "dim": c["dim"],
                        "date": c["dates"][i],
                        "lot": c["lots"][i],
                        "value": c["values"][i],
                        "usl": c["usl"],
                        "lsl": c["lsl"],
                        "rules": flags,
                    })
    return rows


def build_lot_timeline(data):
    """Build lot receipt timeline data."""
    entries = []
    for form in data["forms"]:
        if not form["part"]:
            continue
        entries.append({
            "date": form["date_iso"],
            "part": form["part"],
            "lot": form.get("lot", ""),
            "qty_delivered": form.get("delivery_qty"),
            "qty_inspected": form.get("insp_qty"),
        })
    return entries


def generate_html(all_charts, data):
    """Generate the self-contained HTML dashboard."""
    summaries = build_summary_data(all_charts, data)
    heatmap = build_heatmap_data(all_charts)
    ooc_table = build_ooc_table(all_charts)
    lot_timeline = build_lot_timeline(data)
    meta = data["_meta"]
    part_registry = data["part_registry"]

    parts_list = sorted(all_charts.keys())
    inspectors = sorted(set(
        f["inspector"] for f in data["forms"] if f.get("inspector")
    ))

    charts_json = json.dumps(all_charts)
    summaries_json = json.dumps(summaries)
    heatmap_json = json.dumps(heatmap)
    ooc_table_json = json.dumps(ooc_table)
    lot_timeline_json = json.dumps(lot_timeline)
    parts_json = json.dumps(parts_list)
    inspectors_json = json.dumps(inspectors)
    registry_json = json.dumps(part_registry)
    lot_colors_json = json.dumps(LOT_COLORS)

    gen_date = __import__("datetime").date.today().isoformat()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Receipt Inspection SPC Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }}
.nav-bar {{ background: #0d1117; padding: 8px 30px; display: flex; gap: 10px; align-items: center; }}
.nav-bar .nav-title {{ color: #888; font-size: 13px; font-weight: 600; margin-right: 15px; }}
.nav-bar a {{ color: #aaa; text-decoration: none; padding: 6px 14px; border-radius: 4px; font-size: 13px; font-weight: 500; }}
.nav-bar a:hover {{ color: white; background: rgba(255,255,255,0.1); }}
.nav-bar a.active {{ color: white; background: #1a1a2e; }}
.header {{ background: #1a1a2e; color: white; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ font-size: 22px; font-weight: 600; }}
.header .subtitle {{ font-size: 13px; color: #888; }}
.controls {{ background: white; padding: 15px 30px; border-bottom: 1px solid #ddd; display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }}
.controls label {{ font-size: 13px; font-weight: 600; color: #666; }}
.controls select {{ padding: 6px 14px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; background: white; cursor: pointer; }}
.summary {{ background: white; padding: 15px 30px; border-bottom: 1px solid #ddd; display: flex; gap: 40px; flex-wrap: wrap; }}
.summary .stat {{ text-align: center; }}
.summary .stat .val {{ font-size: 24px; font-weight: 700; }}
.summary .stat .lbl {{ font-size: 12px; color: #888; }}
.summary .stat.ooc .val {{ color: #F44336; }}
.section {{ padding: 20px 30px; }}
.section h2 {{ font-size: 16px; margin-bottom: 15px; color: #555; border-bottom: 2px solid #1a1a2e; padding-bottom: 5px; }}
.chart-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(580px, 1fr)); gap: 15px; }}
.chart-card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }}
.chart-card .chart-title {{ padding: 10px 15px; font-size: 13px; font-weight: 600; background: #fafafa; border-bottom: 1px solid #eee; }}
.chart-card .chart-container {{ height: 280px; }}
.chart-card .mr-container {{ height: 150px; border-top: 1px solid #eee; }}
.part-cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px; }}
.part-card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 18px; cursor: pointer; transition: box-shadow 0.2s; }}
.part-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
.part-card .part-name {{ font-size: 16px; font-weight: 700; margin-bottom: 4px; }}
.part-card .part-drawing {{ font-size: 11px; color: #888; margin-bottom: 10px; }}
.part-card .part-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 12px; }}
.part-card .part-stats .s-label {{ color: #888; }}
.part-card .part-stats .s-value {{ font-weight: 600; text-align: right; }}
.part-card .cpk-badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; color: white; margin-top: 8px; }}
.cpk-green {{ background: #4CAF50; }}
.cpk-amber {{ background: #FFC107; color: #333; }}
.cpk-red {{ background: #F44336; }}
.cpk-na {{ background: #E0E0E0; color: #666; }}
.cpk-row {{ display: flex; gap: 10px; padding: 15px 30px; background: white; border-bottom: 1px solid #ddd; flex-wrap: wrap; }}
.cpk-card {{ flex: 0 0 120px; padding: 10px; border-radius: 6px; text-align: center; color: white; }}
.cpk-card .cpk-val {{ font-size: 20px; font-weight: 700; }}
.cpk-card .cpk-lbl {{ font-size: 10px; opacity: 0.9; margin-top: 2px; }}
.heatmap-container {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; margin-bottom: 20px; }}
.heatmap-container .chart-container {{ height: 300px; }}
.legend {{ display: flex; gap: 15px; padding: 10px 30px; background: white; border-bottom: 1px solid #ddd; flex-wrap: wrap; }}
.legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 12px; }}
.legend-item .swatch {{ width: 14px; height: 14px; border-radius: 3px; }}
.ooc-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
.ooc-table th {{ background: #fafafa; padding: 8px 10px; text-align: left; border-bottom: 2px solid #ddd; font-weight: 600; color: #555; }}
.ooc-table td {{ padding: 6px 10px; border-bottom: 1px solid #eee; }}
.ooc-table tr:hover {{ background: #f9f9f9; }}
.lot-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
.lot-table th {{ background: #fafafa; padding: 8px 10px; text-align: left; border-bottom: 2px solid #ddd; font-weight: 600; color: #555; }}
.lot-table td {{ padding: 6px 10px; border-bottom: 1px solid #eee; }}
.lot-table tr:hover {{ background: #f9f9f9; }}
.part-detail-header {{ background: white; padding: 15px 30px; border-bottom: 1px solid #ddd; }}
.part-detail-header h2 {{ font-size: 18px; font-weight: 700; }}
.part-detail-header .detail-meta {{ font-size: 13px; color: #888; margin-top: 4px; }}
.back-btn {{ padding: 6px 14px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; background: white; cursor: pointer; margin-right: 15px; }}
.back-btn:hover {{ background: #f5f5f5; }}
.timeline-card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; margin-bottom: 15px; }}
.timeline-card .chart-container {{ height: 250px; }}
.tech-checkboxes {{ display: flex; gap: 12px; flex-wrap: wrap; }}
.tech-checkboxes label {{ display: flex; align-items: center; gap: 4px; font-size: 13px; cursor: pointer; }}
.tech-checkboxes input {{ cursor: pointer; }}
@media print {{
  .controls, .nav-bar, #printBtn {{ display: none !important; }}
  .header {{ padding: 10px 20px; }}
  .section {{ padding: 10px 20px; page-break-inside: avoid; }}
  .chart-grid {{ grid-template-columns: 1fr 1fr; }}
  .chart-card {{ break-inside: avoid; }}
  body {{ background: white; }}
}}
</style>
</head>
<body>

<div class="nav-bar">
  <span class="nav-title">SPCOCATOR</span>
  <a href="./OMNIcheck_SPC_Dashboard.html">Final Inspection</a>
  <a href="./Receipt_Inspection_SPC_Dashboard.html" class="active">Receipt Inspection</a>
</div>

<div class="header">
  <div>
    <h1>Receipt Inspection SPC Dashboard</h1>
    <div class="subtitle">Statistical Process Control — Incoming Material Dimensional Quality</div>
  </div>
  <div style="text-align:right;display:flex;align-items:center;gap:15px">
    <button id="printBtn" onclick="window.print()" style="padding:6px 14px;border:1px solid #555;border-radius:4px;background:transparent;color:white;cursor:pointer;font-size:12px">Print / Export</button>
    <div>
      <div style="font-size:14px;font-weight:600">ATOR Labs</div>
      <div style="font-size:11px;color:#888">Generated {gen_date}</div>
    </div>
  </div>
</div>

<div class="controls">
  <div>
    <label>Part</label>&nbsp;
    <select id="partFilter">
      <option value="all">All Parts (Summary)</option>
      {"".join(f'<option value="{p}">{p}</option>' for p in parts_list)}
    </select>
  </div>
  <div>
    <label>Inspector</label>
    <div class="tech-checkboxes" id="inspectorCheckboxes">
      {"".join(f'<label><input type="checkbox" value="{t}" checked> {t}</label>' for t in inspectors)}
    </div>
  </div>
</div>

<div id="summaryView">
  <div class="summary">
    <div class="stat"><div class="val">{meta['total_forms']}</div><div class="lbl">Forms</div></div>
    <div class="stat"><div class="val">{meta['total_measurements']}</div><div class="lbl">Measurements</div></div>
    <div class="stat"><div class="val">{len(parts_list)}</div><div class="lbl">Part Types</div></div>
    <div class="stat"><div class="val">{meta['date_range'][0]} to {meta['date_range'][1]}</div><div class="lbl">Date Range</div></div>
    <div class="stat ooc"><div class="val" id="sumBeyond">{sum(1 for r in ooc_table if any(f == 'rule1' for f in r['rules']))}</div><div class="lbl">Beyond Limits</div></div>
    <div class="stat"><div class="val" id="sumRun" style="color:#FFC107">{sum(1 for r in ooc_table if not any(f == 'rule1' for f in r['rules']))}</div><div class="lbl">Run Rule Flags</div></div>
  </div>

  <div class="section">
    <h2>Parts Overview</h2>
    <div class="part-cards" id="partCards"></div>
  </div>

  <div class="section">
    <h2>Cpk Heatmap — Part x Dimension</h2>
    <div class="heatmap-container"><div class="chart-container" id="heatmapChart"></div></div>
  </div>

  <div class="section">
    <h2>Lot Receipt Timeline</h2>
    <div class="timeline-card"><div class="chart-container" id="timelineChart"></div></div>
  </div>

  <div class="section">
    <h2>Out-of-Control Flags</h2>
    <div id="oocTableContainer"></div>
  </div>
</div>

<div id="detailView" style="display:none">
  <div class="part-detail-header">
    <button class="back-btn" onclick="showSummary()">&#8592; All Parts</button>
    <span id="detailTitle" style="font-size:18px;font-weight:700"></span>
    <div class="detail-meta" id="detailMeta"></div>
  </div>
  <div id="detailCpkRow" class="cpk-row"></div>
  <div id="detailCharts"></div>
  <div class="section">
    <h2>Lot History</h2>
    <div id="detailLotTable"></div>
  </div>
</div>

<script>
const ALL_CHARTS = {charts_json};
const SUMMARIES = {summaries_json};
const HEATMAP = {heatmap_json};
const OOC_TABLE = {ooc_table_json};
const LOT_TIMELINE = {lot_timeline_json};
const PARTS = {parts_json};
const INSPECTORS = {inspectors_json};
const REGISTRY = {registry_json};
const LOT_COLORS = {lot_colors_json};

let selectedInspectors = new Set(INSPECTORS);

// --- Part cards ---
function renderPartCards() {{
  const container = document.getElementById('partCards');
  container.innerHTML = '';
  SUMMARIES.forEach(s => {{
    const cpkClass = s.worst_cpk_val === null ? 'cpk-na' :
      s.worst_cpk_val >= 1.33 ? 'cpk-green' :
      s.worst_cpk_val >= 1.0 ? 'cpk-amber' : 'cpk-red';
    const cpkText = s.worst_cpk_val !== null
      ? `${{s.worst_cpk_dim}}: ${{s.worst_cpk_val.toFixed(2)}}`
      : 'N/A';

    const card = document.createElement('div');
    card.className = 'part-card';
    card.onclick = () => selectPart(s.part);
    card.innerHTML = `
      <div class="part-name">${{s.part}}</div>
      <div class="part-drawing">${{s.drawing}} | ${{s.material}}</div>
      <div class="part-stats">
        <span class="s-label">Lots inspected</span><span class="s-value">${{s.lots}}</span>
        <span class="s-label">Parts measured</span><span class="s-value">${{s.total_parts}}</span>
        <span class="s-label">Dimensions charted</span><span class="s-value">${{s.n_dims_charted}}</span>
        <span class="s-label">Beyond limits</span><span class="s-value" style="color:${{s.beyond_limits > 0 ? '#F44336' : '#4CAF50'}}">${{s.beyond_limits}}</span>
        <span class="s-label">Run rules</span><span class="s-value" style="color:${{s.run_rules > 0 ? '#FFC107' : '#4CAF50'}}">${{s.run_rules}}</span>
      </div>
      <div class="cpk-badge ${{cpkClass}}">Worst Cpk: ${{cpkText}}</div>
    `;
    container.appendChild(card);
  }});
}}

// --- Heatmap ---
function renderHeatmap() {{
  const z = HEATMAP.matrix.map(row => row.map(v => v === null ? NaN : v === -1 ? NaN : v));
  const text = HEATMAP.matrix.map((row, ri) => row.map((v, ci) => {{
    if (v === null) return 'N/A';
    if (v === -1) return 'Insufficient data';
    return `${{HEATMAP.parts[ri]}} | ${{HEATMAP.dims[ci]}}<br>Cpk: ${{v.toFixed(2)}}`;
  }}));

  // Custom colorscale: red < 1.0, amber 1.0-1.33, green > 1.33
  const colorscale = [
    [0, '#F44336'], [0.4, '#F44336'],
    [0.4, '#FFC107'], [0.55, '#FFC107'],
    [0.55, '#4CAF50'], [1.0, '#4CAF50']
  ];

  Plotly.newPlot('heatmapChart', [{{
    type: 'heatmap',
    z: z,
    x: HEATMAP.dims,
    y: HEATMAP.parts,
    text: text,
    hoverinfo: 'text',
    colorscale: colorscale,
    zmin: 0,
    zmax: 2.5,
    colorbar: {{ title: 'Cpk', tickvals: [0, 0.5, 1.0, 1.33, 2.0, 2.5], ticktext: ['0', '0.5', '1.0', '1.33', '2.0', '2.5+'] }},
    xgap: 2,
    ygap: 2,
  }}], {{
    margin: {{ l: 120, r: 60, t: 10, b: 40 }},
    xaxis: {{ side: 'bottom' }},
    yaxis: {{ autorange: 'reversed' }},
  }}, {{ responsive: true, displayModeBar: false }});
}}

// --- Lot timeline ---
function renderTimeline() {{
  const partColors = {{}};
  PARTS.forEach((p, i) => partColors[p] = LOT_COLORS[i % LOT_COLORS.length]);

  const traces = [];
  PARTS.forEach(part => {{
    const entries = LOT_TIMELINE.filter(e => e.part === part);
    if (entries.length === 0) return;
    traces.push({{
      type: 'bar',
      name: part,
      x: entries.map(e => e.date),
      y: entries.map(e => e.qty_delivered || e.qty_inspected || 1),
      marker: {{ color: partColors[part] }},
      hovertemplate: entries.map(e =>
        `${{part}}<br>Date: ${{e.date}}<br>Lot: ${{e.lot || '(none)'}}<br>Delivered: ${{e.qty_delivered || '?'}}<br>Inspected: ${{e.qty_inspected || '?'}}<extra></extra>`
      ),
    }});
  }});

  Plotly.newPlot('timelineChart', traces, {{
    barmode: 'stack',
    margin: {{ l: 50, r: 20, t: 10, b: 30 }},
    xaxis: {{ type: 'category' }},
    yaxis: {{ title: 'Parts Received' }},
    legend: {{ orientation: 'h', y: 1.15 }},
  }}, {{ responsive: true, displayModeBar: false }});
}}

// --- OOC table ---
function renderOOCTable() {{
  const container = document.getElementById('oocTableContainer');
  if (OOC_TABLE.length === 0) {{
    container.innerHTML = '<p style="color:#888;font-size:13px">No out-of-control points detected.</p>';
    return;
  }}
  let html = '<table class="ooc-table"><thead><tr><th>Part</th><th>Dimension</th><th>Date</th><th>Lot</th><th>Value</th><th>LSL</th><th>USL</th><th>Rule</th></tr></thead><tbody>';
  OOC_TABLE.forEach(r => {{
    const rules = r.rules.map(r => r === 'rule1' ? 'Beyond limits' : r === 'rule2' ? '8-run' : '6-trend').join(', ');
    html += `<tr><td>${{r.part}}</td><td>${{r.dim}}</td><td>${{r.date}}</td><td>${{r.lot || '-'}}</td><td style="font-weight:600;color:#F44336">${{r.value}}</td><td>${{r.lsl !== null ? r.lsl : '-'}}</td><td>${{r.usl !== null ? r.usl : '-'}}</td><td>${{rules}}</td></tr>`;
  }});
  html += '</tbody></table>';
  container.innerHTML = html;
}}

// --- Detail view ---
function selectPart(partName) {{
  document.getElementById('partFilter').value = partName;
  showDetail(partName);
}}

function showSummary() {{
  document.getElementById('partFilter').value = 'all';
  document.getElementById('summaryView').style.display = '';
  document.getElementById('detailView').style.display = 'none';
}}

function showDetail(partName) {{
  document.getElementById('summaryView').style.display = 'none';
  document.getElementById('detailView').style.display = '';

  const info = REGISTRY[partName] || {{}};
  document.getElementById('detailTitle').textContent = partName;
  document.getElementById('detailMeta').textContent =
    `Drawing: ${{info.drawing || '?'}} | Material: ${{info.material || '?'}} | Units: ${{info.units || 'inches'}}`;

  const charts = ALL_CHARTS[partName] || [];

  // Cpk scorecards
  const cpkRow = document.getElementById('detailCpkRow');
  cpkRow.innerHTML = '<span style="font-size:13px;font-weight:600;color:#666;align-self:center;margin-right:5px">Cpk</span>';
  charts.forEach(c => {{
    const cpkClass = c.cpk === null ? 'cpk-na' :
      c.cpk >= 1.33 ? 'cpk-green' :
      c.cpk >= 1.0 ? 'cpk-amber' : 'cpk-red';
    const cpkText = c.cpk !== null ? c.cpk.toFixed(2) : 'N/A';
    cpkRow.innerHTML += `<div class="cpk-card ${{cpkClass}}"><div class="cpk-val">${{cpkText}}</div><div class="cpk-lbl">${{c.dim}}</div></div>`;
  }});

  // Charts
  renderDetailCharts(partName, charts);

  // Lot table
  renderLotTable(partName);
}}

function renderDetailCharts(partName, charts) {{
  const container = document.getElementById('detailCharts');
  container.innerHTML = '';

  // Build lot color map for this part
  const lotSet = new Set();
  charts.forEach(c => c.lots.forEach(l => lotSet.add(l)));
  const lotList = [...lotSet];
  const lotColorMap = {{}};
  lotList.forEach((l, i) => lotColorMap[l] = LOT_COLORS[i % LOT_COLORS.length]);

  const section = document.createElement('div');
  section.className = 'section';
  section.innerHTML = '<h2>I-MR Control Charts</h2>';
  const grid = document.createElement('div');
  grid.className = 'chart-grid';
  section.appendChild(grid);
  container.appendChild(section);

  // Legend
  const legend = document.createElement('div');
  legend.className = 'legend';
  legend.innerHTML = `
    <div class="legend-item"><div style="width:20px;border-top:2px solid #9E9E9E"></div>Center (X&#772;)</div>
    <div class="legend-item"><div style="width:20px;border-top:2px dashed #F44336"></div>UCL/LCL (3&#963;)</div>
    <div class="legend-item"><div style="width:20px;border-top:2px dotted #FF9800"></div>Spec Limits</div>
    <div class="legend-item"><div style="width:20px;border-top:1px dotted #BDBDBD"></div>Nominal</div>
    <div class="legend-item"><div class="swatch" style="background:#F44336;clip-path:polygon(50% 0%,0% 100%,100% 100%)"></div>Beyond Limits</div>
    <div class="legend-item"><div class="swatch" style="background:#FFC107;clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%)"></div>Run Rule</div>
  `;
  container.insertBefore(legend, section);

  charts.forEach(c => {{
    // Filter by inspector
    const mask = c.inspectors.map(ins => selectedInspectors.has(ins));
    const vals = c.values.filter((_, i) => mask[i]);
    const dates = c.dates.filter((_, i) => mask[i]);
    const lots = c.lots.filter((_, i) => mask[i]);
    const seqs = c.part_seqs.filter((_, i) => mask[i]);
    const insp = c.inspectors.filter((_, i) => mask[i]);
    const flags = c.ooc_flags.filter((_, i) => mask[i]);

    if (vals.length < 2) return;

    const card = document.createElement('div');
    card.className = 'chart-card';

    const cpkText = c.cpk !== null ? ` | Cpk: ${{c.cpk.toFixed(2)}}` : '';
    card.innerHTML = `
      <div class="chart-title">${{c.dim}} (${{c.unit}})${{cpkText}} | X&#772;=${{c.stats.x_bar.toFixed(4)}} | &#963;=${{c.stats.sigma.toFixed(4)}}</div>
      <div class="chart-container" id="chart-i-${{partName.replace(/\\s/g,'_')}}-${{c.dim}}"></div>
      <div class="mr-container" id="chart-mr-${{partName.replace(/\\s/g,'_')}}-${{c.dim}}"></div>
    `;
    grid.appendChild(card);

    // X-axis labels
    const xLabels = vals.map((_, i) => i + 1);

    // Color by lot
    const colors = lots.map(l => lotColorMap[l] || '#999');

    // Marker symbols for OOC
    const symbols = flags.map(f => {{
      if (f.some(r => r === 'rule1')) return 'triangle-up';
      if (f.length > 0) return 'diamond';
      return 'circle';
    }});
    const sizes = flags.map(f => f.length > 0 ? 12 : 7);
    const markerColors = flags.map((f, i) => {{
      if (f.some(r => r === 'rule1')) return '#F44336';
      if (f.length > 0) return '#FFC107';
      return colors[i];
    }});

    // Hover text
    const hoverText = vals.map((v, i) =>
      `${{c.dim}} = ${{v}}<br>Date: ${{dates[i]}}<br>Lot: ${{lots[i] || '(none)'}}<br>Part #${{seqs[i]}}<br>Inspector: ${{insp[i]}}${{flags[i].length > 0 ? '<br>OOC: ' + flags[i].join(', ') : ''}}`
    );

    // I-chart traces
    const iTraces = [
      {{ x: xLabels, y: vals, mode: 'lines+markers', marker: {{ color: markerColors, symbol: symbols, size: sizes }}, line: {{ color: '#ccc', width: 1 }}, hovertext: hoverText, hoverinfo: 'text', showlegend: false }},
      // Center line
      {{ x: [xLabels[0], xLabels[xLabels.length-1]], y: [c.stats.x_bar, c.stats.x_bar], mode: 'lines', line: {{ color: '#9E9E9E', width: 1.5 }}, hoverinfo: 'skip', showlegend: false }},
      // UCL
      {{ x: [xLabels[0], xLabels[xLabels.length-1]], y: [c.stats.ucl_i, c.stats.ucl_i], mode: 'lines', line: {{ color: '#F44336', width: 1.5, dash: 'dash' }}, hoverinfo: 'skip', showlegend: false }},
      // LCL
      {{ x: [xLabels[0], xLabels[xLabels.length-1]], y: [c.stats.lcl_i, c.stats.lcl_i], mode: 'lines', line: {{ color: '#F44336', width: 1.5, dash: 'dash' }}, hoverinfo: 'skip', showlegend: false }},
    ];

    // Spec limits
    if (c.usl !== null) {{
      iTraces.push({{ x: [xLabels[0], xLabels[xLabels.length-1]], y: [c.usl, c.usl], mode: 'lines', line: {{ color: '#FF9800', width: 1.5, dash: 'dot' }}, hoverinfo: 'skip', showlegend: false }});
    }}
    if (c.lsl !== null) {{
      iTraces.push({{ x: [xLabels[0], xLabels[xLabels.length-1]], y: [c.lsl, c.lsl], mode: 'lines', line: {{ color: '#FF9800', width: 1.5, dash: 'dot' }}, hoverinfo: 'skip', showlegend: false }});
    }}
    // Nominal
    if (c.nominal !== null) {{
      iTraces.push({{ x: [xLabels[0], xLabels[xLabels.length-1]], y: [c.nominal, c.nominal], mode: 'lines', line: {{ color: '#BDBDBD', width: 1, dash: 'dot' }}, hoverinfo: 'skip', showlegend: false }});
    }}

    const iLayout = {{
      margin: {{ l: 60, r: 20, t: 5, b: 25 }},
      xaxis: {{ showticklabels: false }},
      yaxis: {{ title: c.unit }},
      hovermode: 'closest',
    }};

    setTimeout(() => {{
      const iDiv = document.getElementById(`chart-i-${{partName.replace(/\\s/g,'_')}}-${{c.dim}}`);
      if (iDiv) Plotly.newPlot(iDiv, iTraces, iLayout, {{ responsive: true, displayModeBar: false }});
    }}, 50);

    // MR chart
    const mrVals = [];
    for (let i = 1; i < vals.length; i++) mrVals.push(Math.abs(vals[i] - vals[i-1]));
    const mrX = xLabels.slice(1);

    const mrTraces = [
      {{ x: mrX, y: mrVals, mode: 'lines+markers', marker: {{ color: '#2196F3', size: 5 }}, line: {{ color: '#ccc', width: 1 }}, showlegend: false, hovertemplate: 'MR: %{{y:.4f}}<extra></extra>' }},
      {{ x: [mrX[0], mrX[mrX.length-1]], y: [c.stats.mr_bar, c.stats.mr_bar], mode: 'lines', line: {{ color: '#9E9E9E', width: 1.5 }}, hoverinfo: 'skip', showlegend: false }},
      {{ x: [mrX[0], mrX[mrX.length-1]], y: [c.stats.ucl_mr, c.stats.ucl_mr], mode: 'lines', line: {{ color: '#F44336', width: 1.5, dash: 'dash' }}, hoverinfo: 'skip', showlegend: false }},
    ];

    const mrLayout = {{
      margin: {{ l: 60, r: 20, t: 5, b: 25 }},
      xaxis: {{ title: 'Measurement Sequence' }},
      yaxis: {{ title: 'MR' }},
      hovermode: 'closest',
    }};

    setTimeout(() => {{
      const mrDiv = document.getElementById(`chart-mr-${{partName.replace(/\\s/g,'_')}}-${{c.dim}}`);
      if (mrDiv) Plotly.newPlot(mrDiv, mrTraces, mrLayout, {{ responsive: true, displayModeBar: false }});
    }}, 50);
  }});
}}

function renderLotTable(partName) {{
  const container = document.getElementById('detailLotTable');
  const entries = LOT_TIMELINE.filter(e => e.part === partName);
  if (entries.length === 0) {{
    container.innerHTML = '<p style="color:#888;font-size:13px">No lot data.</p>';
    return;
  }}
  let html = '<table class="lot-table"><thead><tr><th>Date</th><th>Lot</th><th>Delivered</th><th>Inspected</th></tr></thead><tbody>';
  entries.forEach(e => {{
    html += `<tr><td>${{e.date}}</td><td>${{e.lot || '-'}}</td><td>${{e.qty_delivered || '-'}}</td><td>${{e.qty_inspected || '-'}}</td></tr>`;
  }});
  html += '</tbody></table>';
  container.innerHTML = html;
}}

// --- Event handlers ---
document.getElementById('partFilter').addEventListener('change', function() {{
  if (this.value === 'all') {{
    showSummary();
  }} else {{
    showDetail(this.value);
  }}
}});

document.getElementById('inspectorCheckboxes').addEventListener('change', function(e) {{
  if (e.target.type === 'checkbox') {{
    if (e.target.checked) {{
      selectedInspectors.add(e.target.value);
    }} else {{
      selectedInspectors.delete(e.target.value);
    }}
    // Re-render detail if in detail view
    const partFilter = document.getElementById('partFilter').value;
    if (partFilter !== 'all') {{
      showDetail(partFilter);
    }}
  }}
}});

// --- Initial render ---
renderPartCards();
renderHeatmap();
renderTimeline();
renderOOCTable();
</script>
</body>
</html>"""

    return html


def main():
    if not DATA_PATH.exists():
        print(f"Error: {DATA_PATH} not found. Run extract_receipt.py first.")
        return

    with open(DATA_PATH) as f:
        data = json.load(f)

    print(f"Loaded {data['_meta']['total_forms']} forms, {data['_meta']['total_measurements']} measurements")

    all_charts = build_chart_data(data)
    total_charts = sum(len(charts) for charts in all_charts.values())
    total_ooc = sum(
        1 for charts in all_charts.values()
        for c in charts
        for flags in c["ooc_flags"]
        if flags
    )

    print(f"Generated {total_charts} charts across {len(all_charts)} parts")
    print(f"Total OOC flags: {total_ooc}")

    html = generate_html(all_charts, data)

    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Output: {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
