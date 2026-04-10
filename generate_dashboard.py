#!/usr/bin/env python3
"""
Generate OMNIcheck SPC Dashboard — self-contained HTML with Plotly.js.

Reads data/inspections.json, computes I-MR control limits, detects OOC points,
and generates a single HTML file with interactive charts.
"""

import json
import math
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent
DATA_PATH = PROJECT_DIR / "data" / "inspections.json"
OUTPUT_PATH = PROJECT_DIR / "OMNIcheck_SPC_Dashboard.html"

# --- Metric definitions ---
METRICS = [
    # (key, label, section, usl_value_or_None)
    ("wob_A_10", "WOB @ 10 LPM (A)", "Protocol A", 0.06 + 0.01),
    ("wob_A_20", "WOB @ 20 LPM (A)", "Protocol A", 0.22 + 0.02),
    ("wob_A_35", "WOB @ 35 LPM (A)", "Protocol A", 0.62 + 0.03),
    ("wob_A_50", "WOB @ 50 LPM (A)", "Protocol A", 1.22 + 0.06),
    ("wob_A_65", "WOB @ 65 LPM (A)", "Protocol A", 2.02 + 0.10),
    ("wob_B_65", "WOB @ 65 LPM (B)", "Protocol B", 0.62 + 0.03),
    ("wob_B_85", "WOB @ 85 LPM (B)", "Protocol B", 1.05 + 0.05),
    ("wob_B_105", "WOB @ 105 LPM (B)", "Protocol B", 1.58 + 0.08),
    ("leak_delta", "Leak Pressure Drop", "Leak & Volume", 0.4),
    ("vol_nfpa40", "NFPA 40 Tidal Volume", "Leak & Volume", (1.565, 1.765)),  # 1.665 ± 0.1 L per NFPA 1850
    ("vol_nfpa102", "NFPA 102 Tidal Volume", "Leak & Volume", (3.3, 3.5)),   # 3.4 ± 0.1 L per NFPA 1850
]

CONFIG_COLORS = {
    "MSA Firetech": "#2196F3",
    "AVON": "#4CAF50",
    "ATOR Labs": "#9C27B0",
}


def compute_imr(values):
    """Compute I-MR control chart statistics."""
    n = len(values)
    if n < 2:
        return None

    arr = np.array(values, dtype=float)
    x_bar = float(np.mean(arr))

    # Moving ranges (consecutive pairs)
    mr = np.abs(np.diff(arr))
    mr_bar = float(np.mean(mr))
    d2 = 1.128  # for n=2

    sigma = mr_bar / d2
    ucl_i = x_bar + 3 * sigma
    lcl_i = x_bar - 3 * sigma
    ucl_mr = 3.267 * mr_bar  # D4 for n=2

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

    # Skip run rules if there's no real variation (e.g., all values identical)
    has_variation = stats["sigma"] > 1e-9

    for i in range(n):
        point_flags = []

        # Rule 1: beyond 3-sigma (only if limits differ from center)
        if has_variation and (values[i] > ucl or values[i] < lcl):
            point_flags.append("rule1")

        if has_variation:
            # Rule 2: 8 consecutive on same side of centerline
            if i >= 7:
                window = values[i - 7 : i + 1]
                if all(v > x_bar for v in window) or all(v < x_bar for v in window):
                    point_flags.append("rule2")

            # Rule 3: 6 consecutive trending in one direction
            if i >= 5:
                window = values[i - 5 : i + 1]
                diffs = [window[j + 1] - window[j] for j in range(5)]
                if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
                    point_flags.append("rule3")

        flags.append(point_flags)

    return flags


def build_chart_data(records, metrics):
    """Build all chart data for the dashboard."""
    charts = []

    for key, label, section, usl in metrics:
        values = [r[key] for r in records if key in r]
        dates = [r["date_iso"] for r in records if key in r]
        unit_ids = [r["unit_id_canonical"] for r in records if key in r]
        configs = [r.get("config_type", "Unknown") for r in records if key in r]
        technicians = [r.get("technician", "") for r in records if key in r]

        if len(values) < 3:
            continue

        stats = compute_imr(values)
        if not stats:
            continue

        ooc_flags = detect_ooc(values, stats)

        unit = "kPa" if "wob" in key else ("inWg" if "leak" in key else "L")

        # Spec limits: either a single USL (one-sided) or (LSL, USL) tuple (two-sided)
        if isinstance(usl, tuple):
            lsl_val, usl_val = usl
        elif usl is not None:
            lsl_val, usl_val = None, usl
        else:
            lsl_val, usl_val = None, None

        # Cpk: min(Cpu, Cpl) for two-sided, Cpu only for one-sided upper
        cpk = None
        if stats["sigma"] > 1e-9:
            parts = []
            if usl_val is not None:
                parts.append((usl_val - stats["x_bar"]) / (3 * stats["sigma"]))
            if lsl_val is not None:
                parts.append((stats["x_bar"] - lsl_val) / (3 * stats["sigma"]))
            if parts:
                cpk = round(min(parts), 2)

        charts.append({
            "key": key,
            "label": label,
            "section": section,
            "unit": unit,
            "usl": usl_val,
            "lsl": lsl_val,
            "cpk": cpk,
            "values": [round(v, 4) for v in values],
            "dates": dates,
            "unit_ids": unit_ids,
            "configs": configs,
            "technicians": technicians,
            "stats": stats,
            "ooc_flags": ooc_flags,
        })

    return charts


def generate_html(charts, records, meta=None):
    """Generate the self-contained HTML dashboard."""
    meta = meta or {}

    # Build sections
    sections = {}
    for c in charts:
        sections.setdefault(c["section"], []).append(c)

    config_types = sorted(set(r.get("config_type", "Unknown") for r in records))
    technicians = sorted(set(r.get("technician", "") for r in records if r.get("technician")))
    n_units = len(records)
    date_range = f"{records[0]['date_iso']} to {records[-1]['date_iso']}"
    total_ooc = sum(1 for c in charts for flags in c["ooc_flags"] if flags)
    fpy = meta.get("first_pass_yield", 0)
    fpy_count = meta.get("first_pass_count", 0)
    total_reports = meta.get("total_reports", n_units)

    # Load events if file exists
    events_path = PROJECT_DIR / "data" / "events.json"
    events = []
    if events_path.exists():
        with open(events_path) as f:
            events = json.load(f)

    # Load reference equipment config if file exists
    equip_path = PROJECT_DIR / "modules" / "cal_certs" / "equipment.json"
    ref_equipment = []
    daq_equip = {}
    if equip_path.exists():
        with open(equip_path) as f:
            equip = json.load(f)
        ref_equipment = [r for r in equip.get("reference_sensors", []) if r.get("manufacturer")]
        daq_equip = equip.get("daq", {})

    charts_json = json.dumps(charts)
    config_colors_json = json.dumps(CONFIG_COLORS)
    technicians_json = json.dumps(technicians)
    events_json = json.dumps(events)
    ref_equipment_json = json.dumps(ref_equipment)
    daq_equip_json = json.dumps(daq_equip)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OMNIcheck SPC Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }}
.header {{ background: #1a1a2e; color: white; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; }}
.header h1 {{ font-size: 22px; font-weight: 600; }}
.header .subtitle {{ font-size: 13px; color: #888; }}
.controls {{ background: white; padding: 15px 30px; border-bottom: 1px solid #ddd; display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }}
.controls label {{ font-size: 13px; font-weight: 600; color: #666; }}
.controls select, .controls .btn-group button {{
  padding: 6px 14px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px;
  background: white; cursor: pointer;
}}
.btn-group {{ display: inline-flex; }}
.btn-group button {{ border-radius: 0; border-right: none; }}
.btn-group button:first-child {{ border-radius: 4px 0 0 4px; }}
.btn-group button:last-child {{ border-radius: 0 4px 4px 0; border-right: 1px solid #ccc; }}
.btn-group button.active {{ background: #1a1a2e; color: white; border-color: #1a1a2e; }}
.summary {{ background: white; padding: 15px 30px; border-bottom: 1px solid #ddd; display: flex; gap: 40px; }}
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
.legend {{ display: flex; gap: 15px; padding: 10px 30px; background: white; border-bottom: 1px solid #ddd; flex-wrap: wrap; }}
.legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 12px; }}
.legend-item .swatch {{ width: 14px; height: 14px; border-radius: 3px; }}
.legend-item .line {{ width: 20px; height: 0; border-top: 2px; }}
.tech-filter {{ display: flex; align-items: center; gap: 10px; }}
.tech-checkboxes {{ display: flex; gap: 12px; flex-wrap: wrap; }}
.tech-checkboxes label {{ display: flex; align-items: center; gap: 4px; font-size: 13px; cursor: pointer; }}
.tech-checkboxes input {{ cursor: pointer; }}
.tab-bar {{ display: flex; background: #1a1a2e; padding: 0 30px; }}
.tab-bar button {{ background: none; border: none; color: #888; padding: 10px 20px; font-size: 13px; font-weight: 600; cursor: pointer; border-bottom: 3px solid transparent; }}
.tab-bar button.active {{ color: white; border-bottom-color: #4FC3F7; }}
.tab-bar button:hover {{ color: #ccc; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
.tech-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
.tech-table th {{ background: #fafafa; padding: 8px 10px; text-align: left; border-bottom: 2px solid #ddd; font-weight: 600; color: #555; }}
.tech-table td {{ padding: 6px 10px; border-bottom: 1px solid #eee; }}
.tech-table tr:hover {{ background: #f9f9f9; }}
.tech-table .low-n {{ color: #FF9800; font-style: italic; }}
.low-n-note {{ font-size: 12px; color: #888; margin: 10px 0 15px; }}
.cpk-row {{ display: flex; gap: 10px; padding: 15px 30px; background: white; border-bottom: 1px solid #ddd; flex-wrap: wrap; }}
.cpk-card {{ flex: 0 0 120px; padding: 10px; border-radius: 6px; text-align: center; color: white; }}
.cpk-card .cpk-val {{ font-size: 20px; font-weight: 700; }}
.cpk-card .cpk-lbl {{ font-size: 10px; opacity: 0.9; margin-top: 2px; }}
.cpk-green {{ background: #4CAF50; }}
.cpk-amber {{ background: #FFC107; color: #333; }}
.cpk-red {{ background: #F44336; }}
.cpk-na {{ background: #E0E0E0; color: #666; }}
.cpk-header {{ font-size: 13px; font-weight: 600; color: #666; align-self: center; margin-right: 5px; }}
.throughput-card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; margin-bottom: 15px; }}
.throughput-card .chart-container {{ height: 250px; }}
.pareto-card {{ background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }}
.pareto-card .chart-container {{ height: 300px; }}
.grr-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
.grr-table th {{ background: #fafafa; padding: 8px 10px; text-align: left; border-bottom: 2px solid #ddd; font-weight: 600; color: #555; }}
.grr-table td {{ padding: 6px 10px; border-bottom: 1px solid #eee; }}
.grr-ok {{ color: #4CAF50; font-weight: 600; }}
.grr-marginal {{ color: #FFC107; font-weight: 600; }}
.grr-bad {{ color: #F44336; font-weight: 600; }}
.drop-zone {{ margin: 15px 30px; padding: 25px; border: 2px dashed #ccc; border-radius: 8px; text-align: center; color: #999; font-size: 13px; background: #fafafa; transition: all 0.2s; cursor: default; }}
.drop-zone.drag-over {{ border-color: #4FC3F7; background: #e3f2fd; color: #1a1a2e; }}
.drop-zone .drop-icon {{ font-size: 24px; margin-bottom: 5px; }}
.drop-zone .drop-status {{ margin-top: 8px; font-size: 12px; color: #4CAF50; display: none; }}
@media print {{
  .controls, .tab-bar, .tech-filter, #printBtn {{ display: none !important; }}
  .tab-content {{ display: block !important; }}
  .header {{ padding: 10px 20px; }}
  .section {{ padding: 10px 20px; page-break-inside: avoid; }}
  .chart-grid {{ grid-template-columns: 1fr 1fr; }}
  .chart-card {{ break-inside: avoid; }}
  body {{ background: white; }}
}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>OMNIcheck SPC Dashboard</h1>
    <div class="subtitle">Statistical Process Control — Final Inspection Metrics</div>
  </div>
  <div style="text-align:right;display:flex;align-items:center;gap:15px">
    <button id="printBtn" onclick="window.print()" style="padding:6px 14px;border:1px solid #555;border-radius:4px;background:transparent;color:white;cursor:pointer;font-size:12px">Print / Export</button>
    <button onclick="document.getElementById('calFileInput').click()" style="padding:6px 14px;border:1px solid #555;border-radius:4px;background:transparent;color:white;cursor:pointer;font-size:12px">Generate Cal Cert(s)</button>
    <input type="file" id="calFileInput" accept=".cal" multiple style="display:none">
    <div>
      <div style="font-size:14px;font-weight:600">ATOR Labs</div>
      <div style="font-size:11px;color:#888">Generated {__import__('datetime').date.today().isoformat()}</div>
    </div>
  </div>
</div>

<div class="tab-bar" id="tabBar">
  <button class="active" data-tab="spc">SPC Charts</button>
  <button data-tab="tech">Technician Analysis</button>
</div>

<div class="tab-content active" id="tab-spc">

<div class="controls">
  <div>
    <label>Time Window</label>&nbsp;
    <span class="btn-group" id="timeButtons">
      <button class="active" data-window="all">All Time</button>
      <button data-window="yearly">Yearly</button>
      <button data-window="quarterly">Quarterly</button>
      <button data-window="monthly">Monthly</button>
    </span>
  </div>
  <div>
    <label>Configuration</label>&nbsp;
    <select id="configFilter">
      <option value="all">All Types</option>
      {"".join(f'<option value="{ct}">{ct}</option>' for ct in config_types)}
    </select>
  </div>
  <div class="tech-filter">
    <label>Technician</label>
    <div class="tech-checkboxes" id="techCheckboxes">
      {"".join(f'<label><input type="checkbox" value="{t}" checked> {t}</label>' for t in technicians)}
    </div>
  </div>
</div>

<div class="summary">
  <div class="stat"><div class="val" id="sumUnits">{n_units}</div><div class="lbl">Units</div></div>
  <div class="stat"><div class="val" id="sumRange">{date_range}</div><div class="lbl">Date Range</div></div>
  <div class="stat ooc"><div class="val" id="sumBeyond">0</div><div class="lbl">Beyond Limits</div></div>
  <div class="stat"><div class="val" id="sumRun" style="color:#FFC107">0</div><div class="lbl">Run Rule Flags</div></div>
</div>

<div class="legend">
  {"".join(f'<div class="legend-item"><div class="swatch" style="background:{CONFIG_COLORS.get(ct,"#999")}"></div>{ct}</div>' for ct in config_types)}
  <div class="legend-item"><div style="width:20px;border-top:2px solid #9E9E9E"></div>Center (X̄)</div>
  <div class="legend-item"><div style="width:20px;border-top:2px dashed #F44336"></div>UCL/LCL (3σ)</div>
  <div class="legend-item"><div style="width:20px;border-top:2px dotted #FF9800"></div>Spec Limits (ISO 16900-5 / NFPA 1850)</div>
  <div class="legend-item"><div class="swatch" style="background:#F44336;clip-path:polygon(50% 0%,0% 100%,100% 100%)"></div>Beyond Limits</div>
  <div class="legend-item"><div class="swatch" style="background:#FFC107;clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%)"></div>Run Rule</div>
</div>

<div id="calDropZone" class="drop-zone">
  <div class="drop-icon">&#128203;</div>
  Drop .cal files here to generate calibration certificates
  <div class="drop-status" id="calDropStatus"></div>
</div>

<div id="cpkRow" class="cpk-row"></div>

<div class="section">
  <h2>Production Throughput</h2>
  <div class="throughput-card"><div class="chart-container" id="throughputChart"></div></div>
</div>

<div id="chartsContainer"></div>

<div class="section">
  <h2>OOC Pareto — Flags by Metric</h2>
  <div class="pareto-card"><div class="chart-container" id="paretoChart"></div></div>
</div>

</div><!-- end tab-spc -->

<div class="tab-content" id="tab-tech">
  <div class="section">
    <h2>Technician Comparison — Box Plots</h2>
    <p class="low-n-note">Comparisons with fewer than 10 samples per technician are marked in amber and should be interpreted cautiously.</p>
    <div class="chart-grid" id="techBoxPlots"></div>
  </div>
  <div class="section">
    <h2>Technician Summary Table</h2>
    <div id="techTableContainer"></div>
  </div>
  <div class="section">
    <h2>Gauge R&R — Reproducibility (Technician Effect)</h2>
    <p class="low-n-note">Shows what % of total measurement variation is attributable to technician differences. &lt;10% = acceptable, 10-30% = marginal, &gt;30% = unacceptable. Current data has uneven group sizes — interpret with caution.</p>
    <div id="grrContainer"></div>
  </div>
</div><!-- end tab-tech -->

<script>
const CHARTS = {charts_json};
const CONFIG_COLORS = {config_colors_json};
const TECHNICIANS = {technicians_json};
const EVENTS = {events_json};
const REF_EQUIPMENT = {ref_equipment_json};
const DAQ_EQUIP = {daq_equip_json};
const DEFAULT_COLOR = '#999';

let currentWindow = 'all';
let currentConfig = 'all';
let selectedTechs = new Set(TECHNICIANS);

function getDateCutoff(window) {{
  const now = new Date();
  switch(window) {{
    case 'monthly': return new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
    case 'quarterly': return new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
    case 'yearly': return new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
    default: return new Date('2000-01-01');
  }}
}}

function renderCharts() {{
  const container = document.getElementById('chartsContainer');
  container.innerHTML = '';
  const cutoff = getDateCutoff(currentWindow);

  // Group by section
  const sections = {{}};
  CHARTS.forEach(c => {{
    if (!sections[c.section]) sections[c.section] = [];
    sections[c.section].push(c);
  }});

  let visibleUnits = 0;
  let visibleBeyond = 0;
  let visibleRun = 0;
  const seenUnits = new Set();

  for (const [sectionName, charts] of Object.entries(sections)) {{
    const secDiv = document.createElement('div');
    secDiv.className = 'section';
    secDiv.innerHTML = `<h2>${{sectionName}}</h2><div class="chart-grid" id="grid-${{sectionName.replace(/\\s/g,'_')}}"></div>`;
    container.appendChild(secDiv);
    const grid = secDiv.querySelector('.chart-grid');

    charts.forEach(chart => {{
      const card = document.createElement('div');
      card.className = 'chart-card';

      const titleSuffix = currentConfig !== 'all' ? ` — ${{currentConfig}}` : '';
      card.innerHTML = `
        <div class="chart-title">${{chart.label}} (${{chart.unit}})${{titleSuffix}}</div>
        <div class="chart-container" id="i-${{chart.key}}"></div>
        <div class="mr-container" id="mr-${{chart.key}}"></div>
      `;
      grid.appendChild(card);

      // Filter data
      const indices = [];
      for (let i = 0; i < chart.values.length; i++) {{
        const d = new Date(chart.dates[i]);
        const configOk = currentConfig === 'all' || chart.configs[i] === currentConfig;
        const techOk = selectedTechs.has(chart.technicians[i]);
        if (d >= cutoff && configOk && techOk) {{
          indices.push(i);
        }}
      }}

      indices.forEach(i => {{
        seenUnits.add(chart.unit_ids[i]);
        if (chart.ooc_flags[i] && chart.ooc_flags[i].length > 0) {{
          if (chart.ooc_flags[i].includes('rule1')) visibleBeyond++;
          else visibleRun++;
        }}
      }});

      const dates = indices.map(i => chart.dates[i]);
      const vals = indices.map(i => chart.values[i]);
      const colors = indices.map(i => CONFIG_COLORS[chart.configs[i]] || DEFAULT_COLOR);
      const hoverText = indices.map(i =>
        `${{chart.unit_ids[i]}}<br>Date: ${{chart.dates[i]}}<br>Tech: ${{chart.technicians[i]}}<br>Config: ${{chart.configs[i]}}<br>Value: ${{chart.values[i]}} ${{chart.unit}}`
      );
      const oocIdx = indices.map((origI, newI) => ({{origI, newI}})).filter(x => chart.ooc_flags[x.origI] && chart.ooc_flags[x.origI].length > 0);

      // I-chart traces
      const traces = [
        // Data points
        {{
          x: dates, y: vals, mode: 'markers', type: 'scatter',
          marker: {{ color: colors, size: 8, line: {{ width: 1, color: '#fff' }} }},
          text: hoverText, hoverinfo: 'text', name: 'Data',
          showlegend: false,
        }},
        // Center line
        {{
          x: [dates[0], dates[dates.length-1]], y: [chart.stats.x_bar, chart.stats.x_bar],
          mode: 'lines', line: {{ color: '#9E9E9E', width: 1.5 }},
          hoverinfo: 'skip', showlegend: false,
        }},
        // UCL
        {{
          x: [dates[0], dates[dates.length-1]], y: [chart.stats.ucl_i, chart.stats.ucl_i],
          mode: 'lines', line: {{ color: '#F44336', width: 1.5, dash: 'dash' }},
          hoverinfo: 'skip', showlegend: false,
        }},
        // LCL
        {{
          x: [dates[0], dates[dates.length-1]], y: [chart.stats.lcl_i, chart.stats.lcl_i],
          mode: 'lines', line: {{ color: '#F44336', width: 1.5, dash: 'dash' }},
          hoverinfo: 'skip', showlegend: false,
        }},
      ];

      // Spec limits (USL and/or LSL)
      if (chart.usl !== null && chart.usl !== undefined) {{
        traces.push({{
          x: [dates[0], dates[dates.length-1]], y: [chart.usl, chart.usl],
          mode: 'lines', line: {{ color: '#FF9800', width: 1.5, dash: 'dot' }},
          hoverinfo: 'skip', showlegend: false,
        }});
      }}
      if (chart.lsl !== null && chart.lsl !== undefined) {{
        traces.push({{
          x: [dates[0], dates[dates.length-1]], y: [chart.lsl, chart.lsl],
          mode: 'lines', line: {{ color: '#FF9800', width: 1.5, dash: 'dot' }},
          hoverinfo: 'skip', showlegend: false,
        }});
      }}

      // OOC markers — split by severity
      const beyondLimits = oocIdx.filter(x => chart.ooc_flags[x.origI].includes('rule1'));
      const runRules = oocIdx.filter(x => !chart.ooc_flags[x.origI].includes('rule1'));

      if (beyondLimits.length > 0) {{
        traces.push({{
          x: beyondLimits.map(x => dates[x.newI]),
          y: beyondLimits.map(x => vals[x.newI]),
          mode: 'markers', type: 'scatter',
          marker: {{ color: '#F44336', size: 12, symbol: 'triangle-up', line: {{ width: 1, color: '#B71C1C' }} }},
          hoverinfo: 'text', showlegend: false,
          text: beyondLimits.map(x => `Beyond control limit`),
        }});
      }}

      if (runRules.length > 0) {{
        traces.push({{
          x: runRules.map(x => dates[x.newI]),
          y: runRules.map(x => vals[x.newI]),
          mode: 'markers', type: 'scatter',
          marker: {{ color: '#FFC107', size: 10, symbol: 'diamond', line: {{ width: 1, color: '#F57F17' }} }},
          hoverinfo: 'text', showlegend: false,
          text: runRules.map(x => {{
            const flags = chart.ooc_flags[x.origI];
            const rules = [];
            if (flags.includes('rule2')) rules.push('8 consecutive same side');
            if (flags.includes('rule3')) rules.push('6 consecutive trending');
            return `Run rule: ${{rules.join(', ')}}`;
          }}),
        }});
      }}

      // Event annotations (vertical lines)
      const eventShapes = [];
      const eventAnnotations = [];
      EVENTS.forEach(ev => {{
        const evDate = new Date(ev.date);
        if (dates.length > 0 && evDate >= new Date(dates[0]) && evDate <= new Date(dates[dates.length-1])) {{
          eventShapes.push({{
            type: 'line', x0: ev.date, x1: ev.date, y0: 0, y1: 1, yref: 'paper',
            line: {{ color: ev.color || '#666', dash: 'dot', width: 1.5 }},
          }});
          eventAnnotations.push({{
            x: ev.date, y: 0.97, yref: 'paper', text: ev.label,
            showarrow: false, font: {{ size: 8, color: ev.color || '#666' }},
            yanchor: 'top', xanchor: 'left', textangle: 0, xshift: 4,
          }});
        }}
      }});

      const iLayout = {{
        margin: {{ t: 5, b: 25, l: 55, r: 15 }},
        xaxis: {{ type: 'date', showgrid: false, tickfont: {{ size: 10 }} }},
        yaxis: {{ title: {{ text: chart.unit, font: {{ size: 11 }} }}, tickfont: {{ size: 10 }}, gridcolor: '#eee' }},
        plot_bgcolor: 'white',
        hovermode: 'closest',
        shapes: eventShapes,
        annotations: eventAnnotations,
      }};

      setTimeout(() => {{
        Plotly.newPlot(`i-${{chart.key}}`, traces, iLayout, {{ responsive: true, displayModeBar: false }});
      }}, 0);

      // MR chart
      const mrDates = dates.slice(1);
      const mrVals = [];
      for (let i = 1; i < vals.length; i++) {{
        mrVals.push(Math.round(Math.abs(vals[i] - vals[i-1]) * 10000) / 10000);
      }}

      const mrTraces = [
        {{
          x: mrDates, y: mrVals, mode: 'markers+lines', type: 'scatter',
          marker: {{ color: '#78909C', size: 5 }}, line: {{ color: '#B0BEC5', width: 1 }},
          hoverinfo: 'y', showlegend: false,
        }},
        // MR center
        {{
          x: [mrDates[0], mrDates[mrDates.length-1]], y: [chart.stats.mr_bar, chart.stats.mr_bar],
          mode: 'lines', line: {{ color: '#9E9E9E', width: 1 }},
          hoverinfo: 'skip', showlegend: false,
        }},
        // MR UCL
        {{
          x: [mrDates[0], mrDates[mrDates.length-1]], y: [chart.stats.ucl_mr, chart.stats.ucl_mr],
          mode: 'lines', line: {{ color: '#F44336', width: 1, dash: 'dash' }},
          hoverinfo: 'skip', showlegend: false,
        }},
      ];

      const mrLayout = {{
        margin: {{ t: 5, b: 25, l: 55, r: 15 }},
        xaxis: {{ type: 'date', showgrid: false, tickfont: {{ size: 9 }} }},
        yaxis: {{ title: {{ text: 'MR', font: {{ size: 10 }} }}, tickfont: {{ size: 9 }}, gridcolor: '#eee' }},
        plot_bgcolor: 'white',
      }};

      setTimeout(() => {{
        Plotly.newPlot(`mr-${{chart.key}}`, mrTraces, mrLayout, {{ responsive: true, displayModeBar: false }});
      }}, 0);
    }});
  }}

  // Update summary
  visibleUnits = seenUnits.size;
  document.getElementById('sumUnits').textContent = visibleUnits;
  document.getElementById('sumBeyond').textContent = visibleBeyond;
  document.getElementById('sumRun').textContent = visibleRun;

  const filteredDates = [];
  CHARTS[0].dates.forEach((d, i) => {{
    const dt = new Date(d);
    if (dt >= cutoff && (currentConfig === 'all' || CHARTS[0].configs[i] === currentConfig)) {{
      filteredDates.push(d);
    }}
  }});
  if (filteredDates.length > 0) {{
    document.getElementById('sumRange').textContent = `${{filteredDates[0]}} to ${{filteredDates[filteredDates.length-1]}}`;
  }}
}}

function renderCpkCards() {{
  const row = document.getElementById('cpkRow');
  row.innerHTML = '<span class="cpk-header">Cpk</span>';
  CHARTS.forEach(c => {{
    const card = document.createElement('div');
    card.className = 'cpk-card';
    if (c.cpk === null || c.cpk === undefined) {{
      card.className += ' cpk-na';
      card.innerHTML = `<div class="cpk-val">N/A</div><div class="cpk-lbl">${{c.label.replace('WOB @ ','').replace(' Tidal Volume','')}}</div>`;
    }} else {{
      const cls = c.cpk >= 1.33 ? 'cpk-green' : c.cpk >= 1.0 ? 'cpk-amber' : 'cpk-red';
      card.className += ` ${{cls}}`;
      card.innerHTML = `<div class="cpk-val">${{c.cpk.toFixed(2)}}</div><div class="cpk-lbl">${{c.label.replace('WOB @ ','').replace(' Tidal Volume','')}}</div>`;
    }}
    row.appendChild(card);
  }});
}}

function renderThroughput() {{
  // Group records by month and config type
  const months = {{}};
  const configSet = new Set();
  CHARTS[0].dates.forEach((d, i) => {{
    const month = d.substring(0, 7); // YYYY-MM
    const cfg = CHARTS[0].configs[i];
    if (!months[month]) months[month] = {{}};
    months[month][cfg] = (months[month][cfg] || 0) + 1;
    configSet.add(cfg);
  }});

  const sortedMonths = Object.keys(months).sort();
  const traces = [];
  Array.from(configSet).sort().forEach(cfg => {{
    traces.push({{
      x: sortedMonths,
      y: sortedMonths.map(m => months[m][cfg] || 0),
      name: cfg,
      type: 'bar',
      marker: {{ color: CONFIG_COLORS[cfg] || DEFAULT_COLOR }},
    }});
  }});

  const layout = {{
    margin: {{ t: 10, b: 40, l: 45, r: 15 }},
    barmode: 'stack',
    xaxis: {{ title: {{ text: 'Month', font: {{ size: 11 }} }}, tickfont: {{ size: 10 }} }},
    yaxis: {{ title: {{ text: 'Units', font: {{ size: 11 }} }}, tickfont: {{ size: 10 }}, dtick: 1 }},
    plot_bgcolor: 'white',
    legend: {{ orientation: 'h', y: -0.2 }},
  }};

  Plotly.newPlot('throughputChart', traces, layout, {{ responsive: true, displayModeBar: false }});
}}

function renderPareto() {{
  // Count OOC by metric, split by type
  const metrics = [];
  CHARTS.forEach(c => {{
    let beyond = 0, run = 0;
    c.ooc_flags.forEach(flags => {{
      if (flags && flags.length > 0) {{
        if (flags.includes('rule1')) beyond++;
        else run++;
      }}
    }});
    if (beyond + run > 0) {{
      metrics.push({{ label: c.label.replace('WOB @ ','').replace(' Tidal Volume',''), beyond, run, total: beyond + run }});
    }}
  }});

  metrics.sort((a, b) => b.total - a.total);

  const traces = [
    {{
      y: metrics.map(m => m.label),
      x: metrics.map(m => m.beyond),
      name: 'Beyond Limits',
      type: 'bar',
      orientation: 'h',
      marker: {{ color: '#F44336' }},
    }},
    {{
      y: metrics.map(m => m.label),
      x: metrics.map(m => m.run),
      name: 'Run Rules',
      type: 'bar',
      orientation: 'h',
      marker: {{ color: '#FFC107' }},
    }},
  ];

  const layout = {{
    margin: {{ t: 10, b: 40, l: 140, r: 15 }},
    barmode: 'stack',
    xaxis: {{ title: {{ text: 'OOC Count', font: {{ size: 11 }} }}, tickfont: {{ size: 10 }}, dtick: 1 }},
    yaxis: {{ tickfont: {{ size: 10 }}, autorange: 'reversed' }},
    plot_bgcolor: 'white',
    legend: {{ orientation: 'h', y: -0.15 }},
  }};

  Plotly.newPlot('paretoChart', traces, layout, {{ responsive: true, displayModeBar: false }});
}}

// Event listeners
document.getElementById('timeButtons').addEventListener('click', e => {{
  if (e.target.tagName === 'BUTTON') {{
    document.querySelectorAll('#timeButtons button').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    currentWindow = e.target.dataset.window;
    renderCharts();
  }}
}});

document.getElementById('configFilter').addEventListener('change', e => {{
  currentConfig = e.target.value;
  renderCharts();
}});

document.getElementById('techCheckboxes').addEventListener('change', e => {{
  if (e.target.type === 'checkbox') {{
    if (e.target.checked) {{
      selectedTechs.add(e.target.value);
    }} else {{
      selectedTechs.delete(e.target.value);
    }}
    renderCharts();
  }}
}});

// Tab switching
document.getElementById('tabBar').addEventListener('click', e => {{
  if (e.target.tagName === 'BUTTON') {{
    document.querySelectorAll('#tabBar button').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById(`tab-${{e.target.dataset.tab}}`).classList.add('active');
    if (e.target.dataset.tab === 'tech' && !techRendered) {{
      renderTechAnalysis();
      techRendered = true;
    }}
  }}
}});

let techRendered = false;

const TECH_COLORS = {{}};
const TECH_PALETTE = ['#26A69A', '#EF5350', '#5C6BC0', '#FFA726', '#66BB6A'];
TECHNICIANS.forEach((t, i) => TECH_COLORS[t] = TECH_PALETTE[i % TECH_PALETTE.length]);

const METRIC_DEFS = [
  {{ key: 'wob_A_10', label: 'WOB A 10 LPM', unit: 'kPa' }},
  {{ key: 'wob_A_20', label: 'WOB A 20 LPM', unit: 'kPa' }},
  {{ key: 'wob_A_35', label: 'WOB A 35 LPM', unit: 'kPa' }},
  {{ key: 'wob_A_50', label: 'WOB A 50 LPM', unit: 'kPa' }},
  {{ key: 'wob_A_65', label: 'WOB A 65 LPM', unit: 'kPa' }},
  {{ key: 'wob_B_65', label: 'WOB B 65 LPM', unit: 'kPa' }},
  {{ key: 'wob_B_85', label: 'WOB B 85 LPM', unit: 'kPa' }},
  {{ key: 'wob_B_105', label: 'WOB B 105 LPM', unit: 'kPa' }},
  {{ key: 'leak_delta', label: 'Leak Pressure Drop', unit: 'inWg' }},
  {{ key: 'vol_nfpa40', label: 'NFPA 40 Volume', unit: 'L' }},
  {{ key: 'vol_nfpa102', label: 'NFPA 102 Volume', unit: 'L' }},
];

function renderTechAnalysis() {{
  const grid = document.getElementById('techBoxPlots');
  grid.innerHTML = '';

  // Build per-tech data from CHARTS
  // CHARTS[0] has all technician names aligned with values
  METRIC_DEFS.forEach(metric => {{
    const chart = CHARTS.find(c => c.key === metric.key);
    if (!chart) return;

    const card = document.createElement('div');
    card.className = 'chart-card';
    card.innerHTML = `<div class="chart-title">${{metric.label}} (${{metric.unit}})</div><div class="chart-container" id="tech-${{metric.key}}"></div>`;
    grid.appendChild(card);

    const traces = [];
    TECHNICIANS.forEach(tech => {{
      const vals = [];
      for (let i = 0; i < chart.values.length; i++) {{
        if (chart.technicians[i] === tech) vals.push(chart.values[i]);
      }}
      if (vals.length === 0) return;
      traces.push({{
        y: vals,
        type: 'box',
        name: `${{tech}} (n=${{vals.length}})`,
        marker: {{ color: TECH_COLORS[tech] }},
        boxpoints: 'all',
        jitter: 0.4,
        pointpos: 0,
        hoverinfo: 'y+name',
      }});
    }});

    const layout = {{
      margin: {{ t: 10, b: 40, l: 55, r: 15 }},
      yaxis: {{ title: {{ text: metric.unit, font: {{ size: 11 }} }}, tickfont: {{ size: 10 }}, gridcolor: '#eee' }},
      xaxis: {{ tickfont: {{ size: 10 }} }},
      plot_bgcolor: 'white',
      showlegend: false,
    }};

    setTimeout(() => {{
      Plotly.newPlot(`tech-${{metric.key}}`, traces, layout, {{ responsive: true, displayModeBar: false }});
    }}, 0);
  }});

  // Build summary table
  const container = document.getElementById('techTableContainer');
  let html = '<table class="tech-table"><thead><tr><th>Metric</th>';
  TECHNICIANS.forEach(t => {{ html += `<th colspan="3" style="text-align:center">${{t}}</th>`; }});
  html += '</tr><tr><th></th>';
  TECHNICIANS.forEach(() => {{ html += '<th>N</th><th>Mean</th><th>Std Dev</th>'; }});
  html += '</tr></thead><tbody>';

  METRIC_DEFS.forEach(metric => {{
    const chart = CHARTS.find(c => c.key === metric.key);
    if (!chart) return;

    html += `<tr><td><strong>${{metric.label}}</strong></td>`;
    TECHNICIANS.forEach(tech => {{
      const vals = [];
      for (let i = 0; i < chart.values.length; i++) {{
        if (chart.technicians[i] === tech) vals.push(chart.values[i]);
      }}
      const n = vals.length;
      if (n === 0) {{
        html += '<td>—</td><td>—</td><td>—</td>';
        return;
      }}
      const mean = vals.reduce((a, b) => a + b, 0) / n;
      const sd = n > 1 ? Math.sqrt(vals.reduce((s, v) => s + (v - mean) ** 2, 0) / (n - 1)) : 0;
      const cls = n < 10 ? ' class="low-n"' : '';
      html += `<td${{cls}}>${{n}}</td><td${{cls}}>${{mean.toFixed(4)}}</td><td${{cls}}>${{sd.toFixed(4)}}</td>`;
    }});
    html += '</tr>';
  }});

  html += '</tbody></table>';
  container.innerHTML = html;

  // Gauge R&R — reproducibility
  const grrContainer = document.getElementById('grrContainer');
  let grrHtml = '<table class="grr-table"><thead><tr><th>Metric</th><th>Total Std Dev</th><th>Between-Tech Std Dev</th><th>%GRR (Reproducibility)</th><th>Rating</th></tr></thead><tbody>';

  METRIC_DEFS.forEach(metric => {{
    const chart = CHARTS.find(c => c.key === metric.key);
    if (!chart) return;

    // Overall stats
    const allVals = chart.values;
    const n = allVals.length;
    const grandMean = allVals.reduce((a, b) => a + b, 0) / n;
    const totalVar = allVals.reduce((s, v) => s + (v - grandMean) ** 2, 0) / (n - 1);

    // Within-tech variance (pooled)
    let ssWithin = 0, dfWithin = 0;
    const techMeans = {{}};
    const techCounts = {{}};
    TECHNICIANS.forEach(tech => {{
      const vals = [];
      for (let i = 0; i < chart.values.length; i++) {{
        if (chart.technicians[i] === tech) vals.push(chart.values[i]);
      }}
      if (vals.length < 2) return;
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      techMeans[tech] = mean;
      techCounts[tech] = vals.length;
      vals.forEach(v => {{ ssWithin += (v - mean) ** 2; }});
      dfWithin += vals.length - 1;
    }});

    const withinVar = dfWithin > 0 ? ssWithin / dfWithin : 0;
    const betweenVar = Math.max(0, totalVar - withinVar);
    const totalSD = Math.sqrt(totalVar);
    const betweenSD = Math.sqrt(betweenVar);
    const grrPct = totalSD > 0 ? (betweenSD / totalSD) * 100 : 0;

    let rating, ratingCls;
    if (grrPct < 10) {{ rating = 'Acceptable'; ratingCls = 'grr-ok'; }}
    else if (grrPct < 30) {{ rating = 'Marginal'; ratingCls = 'grr-marginal'; }}
    else {{ rating = 'Unacceptable'; ratingCls = 'grr-bad'; }}

    grrHtml += `<tr><td><strong>${{metric.label}}</strong></td><td>${{totalSD.toFixed(4)}}</td><td>${{betweenSD.toFixed(4)}}</td><td>${{grrPct.toFixed(1)}}%</td><td class="${{ratingCls}}">${{rating}}</td></tr>`;
  }});

  grrHtml += '</tbody></table>';
  grrContainer.innerHTML = grrHtml;
}}

// === Calibration Certificate Generator (client-side) ===

class CalReader {{
  constructor(buf) {{ this.dv = new DataView(buf); this.pos = 0; }}
  u32() {{ const v = this.dv.getUint32(this.pos); this.pos += 4; return v; }}
  i64() {{
    const hi = this.dv.getInt32(this.pos); const lo = this.dv.getUint32(this.pos+4);
    this.pos += 8; return hi * 0x100000000 + lo;
  }}
  skip(n) {{ this.pos += n; }}
  f64() {{ const v = this.dv.getFloat64(this.pos); this.pos += 8; return v; }}
  f32() {{ const v = this.dv.getFloat32(this.pos); this.pos += 4; return v; }}
  str() {{
    const len = this.u32();
    const bytes = new Uint8Array(this.dv.buffer, this.pos, len);
    this.pos += len;
    // Replace 0xB1->±, 0xB0->°
    let s = '';
    for (let i = 0; i < bytes.length; i++) {{
      if (bytes[i] === 0xB1) s += '±';
      else if (bytes[i] === 0xB0) s += '°';
      else s += String.fromCharCode(bytes[i]);
    }}
    return s;
  }}
  doubles(n) {{ const a = []; for (let i=0;i<n;i++) a.push(this.f64()); return a; }}
}}

function parseCalFile(buf, filename) {{
  const r = new CalReader(buf);
  // LabVIEW timestamp: I64 seconds since 1904-01-01
  const lvSec = r.i64(); r.skip(8);
  const epoch1904 = new Date(1904, 0, 1).getTime();
  const calDate = new Date(epoch1904 + lvSec * 1000);

  function readSensorBase() {{
    return {{ model: r.str(), serial_number: r.str(), manufacturer: r.str(), range: r.str(), units: r.str(), accuracy: r.str() }};
  }}
  function readCalTable() {{
    const np = r.u32(); const nc = r.u32();
    const pts = [];
    for (let i=0;i<np;i++) pts.push([parseFloat(r.str()), parseFloat(r.str())]);
    return pts;
  }}

  // Barometric
  const baro = readSensorBase();
  let np = r.u32(); baro.polynomial = r.doubles(np);
  baro.name = 'Barometric Pressure';

  // Temperature
  const temp = {{ model: r.str(), serial_number: r.str(), manufacturer: r.str(), range: r.str(), units: r.str(), accuracy: r.str() }};
  const nLookup = r.u32();
  temp.lookup_table = [];
  for (let i=0;i<nLookup;i++) temp.lookup_table.push([r.f32(), r.f32()]);
  np = r.u32(); temp.polynomial = r.doubles(np);
  temp.name = 'Gas Temperature';

  r.skip(2); // flag bytes
  const daqModel = r.str();
  const daqSerial = r.str();

  // HP, IP, Eye, Mouth
  const sensorNames = ['High Pressure (HP)', 'Medium Pressure (IP)', 'Low Pressure (Eye)', 'Low Pressure (Mouth)'];
  const sensors = [baro, temp];
  for (const sName of sensorNames) {{
    const s = readSensorBase();
    np = r.u32(); s.polynomial = r.doubles(np);
    s.cal_table = readCalTable();
    s.name = sName;
    sensors.push(s);
  }}

  r.skip(1);
  const unitId = r.str();

  let mac = '';
  const stem = filename.replace('.cal','');
  if (stem.includes('_')) {{ mac = stem.split('_')[0].replace('OMNI-',''); }}

  return {{ calDate, unitId, daqModel, daqSerial, mac, sensors }};
}}

function renderCalCert(cal, filename) {{
  const d = cal.calDate;
  const calDateStr = d.toLocaleDateString('en-US', {{year:'numeric',month:'long',day:'numeric'}});
  const expDate = new Date(d); expDate.setFullYear(expDate.getFullYear()+1);
  const expStr = expDate.toLocaleDateString('en-US', {{year:'numeric',month:'long',day:'numeric'}});
  const certNum = `CAL-${{cal.unitId}}-${{d.getFullYear()}}${{String(d.getMonth()+1).padStart(2,'0')}}${{String(d.getDate()).padStart(2,'0')}}`;

  // Reorder: Eye, Mouth, IP, HP, Baro, Temp
  const order = ['Low Pressure (Eye)','Low Pressure (Mouth)','Medium Pressure (IP)','High Pressure (HP)','Barometric Pressure','Gas Temperature'];
  const sorted = order.map(n => cal.sensors.find(s => s.name === n)).filter(Boolean);

  let summaryRows = '';
  sorted.forEach(s => {{
    const nPts = (s.cal_table || s.lookup_table || []).length;
    summaryRows += `<tr><td>${{s.name}}</td><td>${{s.manufacturer}}</td><td>${{s.model}}</td><td>${{s.serial_number}}</td><td>${{s.range}}</td><td>${{s.units}}</td><td>${{s.accuracy}}</td><td>${{nPts}}</td></tr>`;
  }});

  let sensorSections = '';
  sorted.forEach(s => {{
    const polyStr = s.polynomial.map((c,i) => `C${{i}}=${{c.toFixed(6)}}`).join(', ');
    let tableHtml = '';
    if (s.cal_table && s.cal_table.length) {{
      tableHtml = `<table class="cp"><tr><th>#</th><th>Raw Input (V)</th><th>Reference (${{s.units}})</th></tr>`;
      s.cal_table.forEach((p,i) => {{ tableHtml += `<tr><td>${{i+1}}</td><td>${{p[0].toFixed(6)}}</td><td>${{p[1].toFixed(3)}}</td></tr>`; }});
      tableHtml += '</table>';
    }} else if (s.lookup_table && s.lookup_table.length) {{
      tableHtml = `<table class="cp"><tr><th>#</th><th>Voltage (V)</th><th>Temperature (${{s.units}})</th></tr>`;
      s.lookup_table.forEach((p,i) => {{ tableHtml += `<tr><td>${{i+1}}</td><td>${{p[0].toFixed(4)}}</td><td>${{p[1].toFixed(1)}}</td></tr>`; }});
      tableHtml += '</table>';
    }}
    sensorSections += `<div style="margin-bottom:8px"><h2>${{s.name}} — Calibration Data</h2><div style="margin-bottom:6px;font-size:8.5pt"><strong>Polynomial Coefficients:</strong> ${{polyStr}}</div>${{tableHtml}}</div>`;
  }});

  // Reference equipment table
  let refTableHtml = '';
  if (REF_EQUIPMENT.length > 0 || (DAQ_EQUIP && DAQ_EQUIP.manufacturer)) {{
    refTableHtml = `<h2 style="font-size:10pt;color:#1a1a2e;margin:12px 0 6px;border-bottom:1px solid #ccc;padding-bottom:3px">Reference Calibration Equipment</h2>
    <table><thead><tr><th>Reference Standard</th><th>Calibrates</th><th>Manufacturer</th><th>Model</th><th>S/N</th><th>Accuracy</th><th>Cal Cert #</th><th>Cal Cert Exp.</th></tr></thead><tbody>`;
    REF_EQUIPMENT.forEach(r => {{
      refTableHtml += `<tr><td>${{r.name}}</td><td>${{(r.calibrates||[]).join(', ')}}</td><td>${{r.manufacturer}}</td><td>${{r.model}}</td><td>${{r.serial_number}}</td><td>${{r.accuracy}}</td><td>${{r.cal_cert_number}}</td><td>${{r.cal_cert_expiration}}</td></tr>`;
    }});
    if (DAQ_EQUIP && DAQ_EQUIP.manufacturer) {{
      refTableHtml += `<tr><td>Data Acquisition</td><td>All sensors</td><td>${{DAQ_EQUIP.manufacturer}}</td><td>${{cal.daqModel}}</td><td>${{cal.daqSerial}}</td><td>—</td><td>${{DAQ_EQUIP.cal_cert_number||''}}</td><td>${{DAQ_EQUIP.cal_cert_expiration||''}}</td></tr>`;
    }}
    refTableHtml += '</tbody></table>';
  }}

  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Cal Cert — ${{cal.unitId}}</title>
<style>
@page{{size:letter;margin:.75in}}*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Arial,sans-serif;font-size:10pt;color:#222;line-height:1.4}}
.hdr{{display:flex;justify-content:space-between;border-bottom:3px solid #1a1a2e;padding-bottom:12px;margin-bottom:15px}}
.hdr .co{{font-size:18pt;font-weight:700;color:#1a1a2e}}.hdr .sub{{font-size:8pt;color:#666}}
.hdr .ci{{text-align:right;font-size:9pt;color:#555}}.hdr .cn{{font-size:11pt;font-weight:600;color:#1a1a2e}}
h1{{font-size:14pt;color:#1a1a2e;text-align:center;margin:10px 0}}
h2{{font-size:10pt;color:#1a1a2e;margin:12px 0 6px;border-bottom:1px solid #ccc;padding-bottom:3px}}
.ui{{display:grid;grid-template-columns:1fr 1fr;gap:4px 20px;margin-bottom:12px;font-size:9pt}}
.ui .lb{{font-weight:600;color:#555}}
table{{width:100%;border-collapse:collapse;margin-bottom:10px;font-size:8.5pt}}
th{{background:#f0f0f0;padding:4px 6px;text-align:left;border:1px solid #ccc;font-weight:600}}
td{{padding:3px 6px;border:1px solid #ddd}}tr:nth-child(even){{background:#fafafa}}
.cp{{font-size:8pt}}.cp th{{font-size:7.5pt}}
.ft{{margin-top:20px;border-top:1px solid #ccc;padding-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:20px;font-size:8.5pt}}
.sl{{border-bottom:1px solid #999;height:30px;margin-bottom:3px}}.slb{{color:#666;font-size:7.5pt}}
.ref{{margin-top:10px;font-size:8pt;color:#666}}.nt{{font-size:7.5pt;color:#888;margin-top:8px;font-style:italic}}
.pass{{color:#2e7d32;font-weight:600}}
@media print{{body{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>
<div class="hdr"><div><div class="co">ATOR Labs</div><div class="sub">Mine Survival, Inc. DBA ATOR Labs</div></div>
<div class="ci"><div class="cn">${{certNum}}</div><div>Calibration Certificate</div></div></div>
<h1>OMNIcheck Calibration Certificate</h1>
<div class="ui">
<div><span class="lb">Unit ID:</span> ${{cal.unitId}}</div><div><span class="lb">Calibration Date:</span> ${{calDateStr}}</div>
<div><span class="lb">MAC Address:</span> ${{cal.mac}}</div><div><span class="lb">Expiration Date:</span> ${{expStr}}</div>
<div><span class="lb">DAQ:</span> NI ${{cal.daqModel}} (S/N: ${{cal.daqSerial}})</div><div><span class="lb">Status:</span> <span class="pass">PASS</span></div>
</div>
<h2>Sensor Calibration Summary</h2>
<table><thead><tr><th>Sensor</th><th>Manufacturer</th><th>Model</th><th>S/N</th><th>Range</th><th>Units</th><th>Accuracy</th><th>Cal Points</th></tr></thead>
<tbody>${{summaryRows}}</tbody></table>
${{sensorSections}}
${{refTableHtml}}
<div class="ft"><div><div class="sl"></div><div class="slb">Calibrated By (Print Name / Signature)</div></div>
<div><div class="sl"></div><div class="slb">Date</div></div></div>
<div class="ref">All reference standards are traceable to NIST.</div>
<div class="nt">This certificate documents the calibration state of the OMNIcheck unit at the time of calibration. Calibration valid for 12 months from calibration date. Recalibration required before ${{expStr}}.</div>
</body></html>`;

  return html;
}}

// --- Cal cert drop zone ---
const dropZone = document.getElementById('calDropZone');
const dropStatus = document.getElementById('calDropStatus');

async function processCalFiles(files) {{
  const calFiles = Array.from(files).filter(f => f.name.endsWith('.cal'));
  if (!calFiles.length) {{
    dropStatus.textContent = 'No .cal files found in drop';
    dropStatus.style.color = '#F44336';
    dropStatus.style.display = 'block';
    setTimeout(() => dropStatus.style.display = 'none', 3000);
    return;
  }}
  let count = 0;
  for (const file of calFiles) {{
    try {{
      const buf = await file.arrayBuffer();
      const cal = parseCalFile(buf, file.name);
      const html = renderCalCert(cal, file.name);
      const blob = new Blob([html], {{type: 'text/html'}});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const d = cal.calDate;
      a.download = `CAL-${{cal.unitId}}-${{d.getFullYear()}}${{String(d.getMonth()+1).padStart(2,'0')}}${{String(d.getDate()).padStart(2,'0')}}_CalCert.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      count++;
    }} catch (err) {{
      alert(`Error processing ${{file.name}}: ${{err.message}}`);
    }}
  }}
  dropStatus.textContent = `Generated ${{count}} certificate${{count !== 1 ? 's' : ''}}`;
  dropStatus.style.color = '#4CAF50';
  dropStatus.style.display = 'block';
  setTimeout(() => dropStatus.style.display = 'none', 4000);
}}

dropZone.addEventListener('dragover', (e) => {{ e.preventDefault(); dropZone.classList.add('drag-over'); }});
dropZone.addEventListener('dragleave', () => {{ dropZone.classList.remove('drag-over'); }});
dropZone.addEventListener('drop', (e) => {{
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  processCalFiles(e.dataTransfer.files);
}});
// Also allow clicking the drop zone as a fallback
dropZone.addEventListener('click', () => document.getElementById('calFileInput').click());

document.getElementById('calFileInput').addEventListener('change', async (e) => {{
  await processCalFiles(e.target.files);
  e.target.value = '';
}});

// Initial render
renderCpkCards();
renderThroughput();
renderPareto();
renderCharts();
</script>
</body>
</html>"""

    return html


def main():
    with open(DATA_PATH) as f:
        raw = json.load(f)

    # Handle both old format (list) and new format (dict with _meta)
    if isinstance(raw, dict):
        records = raw["records"]
        meta = raw.get("_meta", {})
    else:
        records = raw
        meta = {}

    print(f"Loaded {len(records)} records")

    charts = build_chart_data(records, METRICS)
    print(f"Built {len(charts)} charts")

    # Print summary stats
    for c in charts:
        ooc_count = sum(1 for f in c["ooc_flags"] if f)
        print(
            f"  {c['label']:<28} X̄={c['stats']['x_bar']:8.4f}  "
            f"UCL={c['stats']['ucl_i']:8.4f}  LCL={c['stats']['lcl_i']:8.4f}  "
            f"OOC={ooc_count}"
            + (f"  USL={c['usl']:.4f}" if c["usl"] else "")
        )

    html = generate_html(charts, records, meta)
    OUTPUT_PATH.write_text(html)
    print(f"\nDashboard written to {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
