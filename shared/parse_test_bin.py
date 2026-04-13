#!/usr/bin/env python3
"""
Parse OMNIcheck test .bin files (V1 and V2).

Extracts:
- Header: unit ID, date, time, technician (both V1/V2)
- MAC address from embedded cal trailer (both V1/V2)
- V2 WOB correction summaries: Total WOB Avg at NFPA 40, ISO High, NFPA 103

Does NOT extract orifice WOB, leak, or volume display values — those are
computed by LabVIEW and not stored as dedicated fields. Use PDF extraction
for those values.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.bin_parser import BinaryReader

# V2 files are ~206KB, V1 files are ~111KB
V2_SIZE_THRESHOLD = 150000


def _find_mac(data: bytes) -> str:
    """Find MAC address by locating 'USB-6001' in the cal trailer."""
    usb_idx = data.find(b"USB-6001")
    if usb_idx < 0:
        return ""
    # MAC string follows immediately after "USB-6001" with a 4-byte length prefix
    mac_pos = usb_idx + 8
    if mac_pos + 4 > len(data):
        return ""
    mac_len = struct.unpack(">I", data[mac_pos:mac_pos + 4])[0]
    if mac_len > 20 or mac_pos + 4 + mac_len > len(data):
        return ""
    return data[mac_pos + 4:mac_pos + 4 + mac_len].decode("utf-8", errors="replace")


def _parse_v2_wob_block(data: bytes, offset: int, is_first_block: bool = False) -> tuple:
    """Parse one V2 WOB correction block. Returns (summary_dict, next_offset).

    Block 1 (NFPA 40): 7 doubles (first = spare/AdjLtoV) + U32(2) + U32(N) + 2N doubles
    Blocks 2-3: 6 doubles + float32(AdjLtoV) + U32(2) + U32(N) + 2N doubles
    """
    summary = {}
    fields = [
        "pressure_max_avg", "total_wob_avg", "pressure_min_avg",
        "inhale_wob_avg", "exhale_wob_avg", "elastance_avg",
    ]

    if is_first_block:
        # Block 1: 7 doubles, then U32(2), U32(N)
        summary["adj_l_to_v"] = struct.unpack(">d", data[offset:offset + 8])[0]
        for i, field in enumerate(fields):
            pos = offset + 8 + i * 8  # Skip first double
            summary[field] = struct.unpack(">d", data[pos:pos + 8])[0]
        arr_marker = offset + 7 * 8  # After 7 doubles
        cols = struct.unpack(">I", data[arr_marker:arr_marker + 4])[0]
        rows = struct.unpack(">I", data[arr_marker + 4:arr_marker + 8])[0]
        next_offset = arr_marker + 8 + cols * rows * 8
    else:
        # Blocks 2-3: 6 doubles + float32 + U32(2) + U32(N)
        for i, field in enumerate(fields):
            pos = offset + i * 8
            summary[field] = struct.unpack(">d", data[pos:pos + 8])[0]
        adj_pos = offset + 48
        summary["adj_l_to_v"] = struct.unpack(">f", data[adj_pos:adj_pos + 4])[0]
        cols = struct.unpack(">I", data[adj_pos + 4:adj_pos + 8])[0]
        rows = struct.unpack(">I", data[adj_pos + 8:adj_pos + 12])[0]
        next_offset = adj_pos + 12 + cols * rows * 8

    summary["waveform_samples"] = rows if is_first_block else rows

    return summary, next_offset


def parse_test_bin(filepath: str) -> dict:
    """Parse a test .bin file. Returns structured dict."""
    with open(filepath, "rb") as f:
        data = f.read()

    r = BinaryReader(data)
    result = {
        "_source": str(filepath),
        "_size": len(data),
    }

    # Header
    result["unit_id"] = r.read_string()
    result["time"] = r.read_string()
    result["date"] = r.read_string()
    result["technician"] = r.read_string()

    # MAC from cal trailer
    result["mac"] = _find_mac(data)

    # Detect V1 vs V2
    is_v2 = len(data) > V2_SIZE_THRESHOLD
    result["version"] = "v2" if is_v2 else "v1"

    # V2: parse WOB correction section
    if is_v2:
        # V2-extra section starts after the V1-equivalent portion
        # Find cal trailer end, then skip to V2-extra
        usb_idx = data.find(b"USB-6001")
        if usb_idx > 0:
            # The V1 portion is roughly the first ~111KB
            # V2-extra has a 13-byte header after the V1 section ends
            # Find the V2-extra start by looking for the header pattern
            # Search for the first WOB block after the cal trailer
            # V1 files end around byte 111000, V2-extra starts there
            # The header is: U32=1, U16=4, U32=1, 3 bytes padding (13 bytes)
            # Then 3 WOB correction blocks

            # Find V2-extra header: last occurrence of the 6-byte pattern
            # 00 00 00 01 00 04 after the cal trailer
            v2_header_pattern = b'\x00\x00\x00\x01\x00\x04'
            v2_extra_start = None
            search_pos = usb_idx
            while True:
                idx = data.find(v2_header_pattern, search_pos)
                if idx < 0:
                    break
                v2_extra_start = idx + 13  # Skip 13-byte header
                search_pos = idx + 1

            if v2_extra_start:
                try:
                    nfpa40, offset = _parse_v2_wob_block(data, v2_extra_start, is_first_block=True)
                    result["wob_nfpa40"] = nfpa40

                    iso_high, offset = _parse_v2_wob_block(data, offset)
                    result["wob_iso_high"] = iso_high

                    nfpa103, offset = _parse_v2_wob_block(data, offset)
                    result["wob_nfpa103"] = nfpa103

                    # Validate: Total WOB should ≈ Inhale + Exhale
                    for block_name in ["wob_nfpa40", "wob_iso_high", "wob_nfpa103"]:
                        b = result[block_name]
                        expected = b["inhale_wob_avg"] + b["exhale_wob_avg"]
                        if abs(b["total_wob_avg"] - expected) > 0.01:
                            b["_validation"] = f"Total WOB mismatch: {b['total_wob_avg']:.4f} vs {expected:.4f}"
                except Exception as e:
                    result["_v2_parse_error"] = str(e)

    return result


def main():
    import json

    if len(sys.argv) < 2:
        path = "/Volumes/OC/QMS/Final Inspection QA/Final QA REPORTS/Raw Data/20260401OCSA57_4102026_Prod QA.bin"
    else:
        path = sys.argv[1]

    result = parse_test_bin(path)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
