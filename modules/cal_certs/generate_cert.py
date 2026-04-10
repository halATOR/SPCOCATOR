#!/usr/bin/env python3
"""
Generate calibration certificates from .cal files.

Usage:
  python3 modules/cal_certs/generate_cert.py [cal_file_or_directory]

If given a directory, processes all .cal files found.
Outputs HTML files (print to PDF via browser).
"""

import sys
import glob
from pathlib import Path
from datetime import datetime, timedelta

from jinja2 import Environment, FileSystemLoader

# Add project root to path
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))
from modules.cal_certs.parse_cal import parse_cal_file

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
OUTPUT_DIR = PROJECT_DIR / "output" / "cal_certs"

# Sensor display names and ordering
SENSOR_MAP = [
    ("low_pressure_eye", "Low Pressure (Eye)"),
    ("low_pressure_mouth", "Low Pressure (Mouth)"),
    ("medium_pressure", "Medium Pressure (IP)"),
    ("high_pressure", "High Pressure (HP)"),
    ("barometric", "Barometric Pressure"),
    ("temperature", "Gas Temperature"),
]


def build_cert_context(cal_data: dict) -> dict:
    """Build the Jinja2 template context from parsed cal data."""
    cal_date = datetime.fromisoformat(cal_data["cal_date"])
    expiration = cal_date + timedelta(days=365)
    unit_id = cal_data.get("unit_id", "UNKNOWN")

    sensors = []
    for key, display_name in SENSOR_MAP:
        if key not in cal_data:
            continue
        s = cal_data[key]
        sensor = {
            "name": display_name,
            "manufacturer": s.get("manufacturer", ""),
            "model": s.get("model", ""),
            "serial_number": s.get("serial_number", ""),
            "range": s.get("range", ""),
            "units": s.get("units", ""),
            "accuracy": s.get("accuracy", ""),
            "polynomial": s.get("polynomial", []),
            "cal_table": s.get("cal_table"),
            "lookup_table": s.get("lookup_table"),
            "num_points": len(s.get("cal_table") or s.get("lookup_table") or []),
        }
        sensors.append(sensor)

    return {
        "unit_id": unit_id,
        "cert_number": f"CAL-{unit_id}-{cal_date.strftime('%Y%m%d')}",
        "cal_date_display": cal_date.strftime("%B %d, %Y"),
        "expiration_date": expiration.strftime("%B %d, %Y"),
        "mac_address": cal_data.get("mac_address", cal_data.get("daq_serial", "")),
        "daq_model": cal_data.get("daq_model", "USB-6001"),
        "daq_serial": cal_data.get("daq_serial", ""),
        "sensors": sensors,
    }


def generate_cert(cal_path: str, output_dir: Path = None) -> Path:
    """Generate an HTML cal cert from a .cal file. Returns output path."""
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    cal_data = parse_cal_file(cal_path)
    context = build_cert_context(cal_data)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("cert.html")
    html = template.render(**context)

    out_name = f"{context['cert_number']}.html"
    out_path = output_dir / out_name
    out_path.write_text(html)
    return out_path


def main():
    if len(sys.argv) < 2:
        # Default to the known sample
        target = Path.home() / "Desktop" / "projects backup" / "calibrator" / "OMNI-021FDBB6_20260321_Cal.cal"
    else:
        target = Path(sys.argv[1])

    if target.is_dir():
        cal_files = sorted(target.glob("*.cal"))
        if not cal_files:
            print(f"No .cal files found in {target}")
            return
    else:
        cal_files = [target]

    print(f"Processing {len(cal_files)} .cal file(s)")

    for cal_path in cal_files:
        try:
            out = generate_cert(str(cal_path))
            print(f"  {cal_path.name} -> {out.name}")
        except Exception as e:
            print(f"  {cal_path.name} -> ERROR: {e}")

    print(f"\nOutput directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
