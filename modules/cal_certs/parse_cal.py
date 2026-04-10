#!/usr/bin/env python3
"""
Parse OMNIcheck .cal calibration files.

File layout (sequential):
1. 16-byte LabVIEW timestamp (cal date)
2. Barometric sensor block
3. Temperature sensor block (with voltage→°F lookup table)
4. 1-byte flag
5. DAQ info (model, serial)
6. HP sensor block (with cal table as strings)
7. IP sensor block (with cal table as strings)
8. Eye sensor block (with cal table as strings)
9. Mouth sensor block (with cal table as strings)
10. 1-byte flag
11. Unit ID string
"""

import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.bin_parser import BinaryReader


def _read_accuracy_string(reader: BinaryReader) -> str:
    """Read an accuracy string that may have a leading 0xb1 (±) byte."""
    length = reader.read_u32()
    raw = reader.read_bytes(length)
    # Replace LabVIEW special characters: 0xb1=±, 0xb0=°
    raw = raw.replace(b"\xb1", b"\xc2\xb1")  # ±
    raw = raw.replace(b"\xb0", b"\xc2\xb0")  # °
    return raw.decode("utf-8", errors="replace")


def _read_sensor_base(reader: BinaryReader) -> dict:
    """Read common sensor fields: model, SN, manufacturer, range, units, accuracy."""
    sensor = {}
    sensor["model"] = reader.read_string()
    sensor["serial_number"] = reader.read_string()
    sensor["manufacturer"] = reader.read_string()
    sensor["range"] = reader.read_string()
    sensor["units"] = reader.read_string()
    sensor["accuracy"] = _read_accuracy_string(reader)
    return sensor


def _read_polynomial(reader: BinaryReader, count: int) -> list:
    """Read polynomial coefficients as doubles."""
    return [reader.read_double() for _ in range(count)]


def _read_cal_table_strings(reader: BinaryReader) -> list:
    """Read calibration table: U32 num_points, U32 num_columns (always 2), then string pairs."""
    num_points = reader.read_u32()
    _num_cols = reader.read_u32()  # always 2 (Raw Input X, Calibration Input Y)
    points = []
    for _ in range(num_points):
        raw_x = reader.read_string()
        raw_y = reader.read_string()
        points.append((float(raw_x), float(raw_y)))
    return points


def parse_cal_file(filepath: str) -> dict:
    """Parse a .cal file and return a structured dict."""
    with open(filepath, "rb") as f:
        data = f.read()

    reader = BinaryReader(data)
    result = {"_source": str(filepath)}

    # --- Header: LabVIEW timestamp ---
    result["cal_date"] = reader.read_labview_timestamp().isoformat()

    # --- Barometric Sensor ---
    baro = {}
    baro["model"] = reader.read_string()  # "SBY-110"
    baro["serial_number"] = reader.read_string()
    baro["manufacturer"] = reader.read_string()  # "Apogee Instruments"
    baro["range"] = reader.read_string()  # "112.5-862.6"
    baro["units"] = reader.read_string()  # "mmHg"
    baro["accuracy"] = _read_accuracy_string(reader)
    # Polynomial coefficients (2 doubles)
    num_poly = reader.read_u32()
    baro["polynomial"] = _read_polynomial(reader, num_poly)
    result["barometric"] = baro

    # --- Temperature Sensor ---
    temp = {}
    temp["model"] = reader.read_string()  # "MA 100"
    temp["serial_number"] = reader.read_string()
    temp["manufacturer"] = reader.read_string()  # "Amphenol Thermometrics"
    temp["range"] = reader.read_string()  # "32-128"
    temp["units"] = _read_accuracy_string(reader)  # "°F" (has special chars)
    temp["accuracy"] = _read_accuracy_string(reader)
    # Voltage→°F lookup table: count, then pairs of 32-bit floats
    num_lookup = reader.read_u32()
    temp["lookup_table"] = []
    for _ in range(num_lookup):
        voltage = reader.read_float()
        temp_val = reader.read_float()
        temp["lookup_table"].append((round(voltage, 4), round(temp_val, 1)))
    # Polynomial coefficients (4 doubles)
    num_poly = reader.read_u32()
    temp["polynomial"] = _read_polynomial(reader, num_poly)
    result["temperature"] = temp

    # --- Flag bytes ---
    reader.skip(2)

    # --- DAQ Info ---
    result["daq_model"] = reader.read_string()  # "USB-6001"
    result["daq_serial"] = reader.read_string()  # "021FDBB6"

    # --- HP Sensor ---
    hp = _read_sensor_base(reader)
    num_poly = reader.read_u32()
    hp["polynomial"] = _read_polynomial(reader, num_poly)
    hp["cal_table"] = _read_cal_table_strings(reader)
    result["high_pressure"] = hp

    # --- IP Sensor ---
    ip = _read_sensor_base(reader)
    num_poly = reader.read_u32()
    ip["polynomial"] = _read_polynomial(reader, num_poly)
    ip["cal_table"] = _read_cal_table_strings(reader)
    result["medium_pressure"] = ip

    # --- Eye Sensor ---
    eye = _read_sensor_base(reader)
    num_poly = reader.read_u32()
    eye["polynomial"] = _read_polynomial(reader, num_poly)
    eye["cal_table"] = _read_cal_table_strings(reader)
    result["low_pressure_eye"] = eye

    # --- Mouth Sensor ---
    mouth = _read_sensor_base(reader)
    num_poly = reader.read_u32()
    mouth["polynomial"] = _read_polynomial(reader, num_poly)
    mouth["cal_table"] = _read_cal_table_strings(reader)
    result["low_pressure_mouth"] = mouth

    # --- Flag byte ---
    reader.skip(1)

    # --- Unit ID ---
    result["unit_id"] = reader.read_string()

    # --- Derive additional info from filename ---
    fname = Path(filepath).stem
    if "_Cal" in fname:
        parts = fname.split("_")
        if len(parts) >= 2:
            result["mac_address"] = parts[0].replace("OMNI-", "")
            result["cal_date_from_filename"] = parts[1]

    return result


def main():
    import json

    if len(sys.argv) < 2:
        # Default to the known sample file
        cal_path = Path.home() / "Desktop" / "projects backup" / "calibrator" / "OMNI-021FDBB6_20260321_Cal.cal"
    else:
        cal_path = Path(sys.argv[1])

    result = parse_cal_file(str(cal_path))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
