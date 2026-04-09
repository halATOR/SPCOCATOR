# .bin and .cal File Format Definitions

Source: OMNIcheck LabVIEW software UI screenshots from Jake Cornman (2026-04-09).

---

## Test .bin File Layout

Each test .bin file (~111 KB) stores a complete final inspection test record.

### Header (length-prefixed strings)
| Field | Example |
|-------|---------|
| Unit ID | `20251104OCS32` |
| Time | `9:30 AM` |
| Date | `11/12/2025` |
| Technician | `Sieggy Bennicoff Yundt` |

### Leak Tightness Test Section
| Field | Units | Notes |
|-------|-------|-------|
| Test Pressure | inH2O | Constant: -8 inH2O (-2 kPa) |
| Test Duration | sec | Constant: 60 sec (1 min) |
| Settling Time | sec | Constant: 60 sec (1 min) |
| Leakage Allowed | inH2O | Constant: 0.4 inH2O (0.1 kPa) |
| Start Pressure | inH2O | Measured |
| End Pressure | inH2O | Measured |
| Test Time | sec | Measured (should be 60) |
| Leakage | inH2O | Derived: Start - End |
| Status | Pass/Fail | |

### Orifice Test Data (WOB)
7 RMV levels tested, split across two physical orifices:

**Orifice A (RMV 1–5):**

| RMV Level | Minute Ventilation (LPM) | Limit (kPa) |
|-----------|--------------------------|--------------|
| RMV 1 | 10.0 | 0.06 ± 0.01 |
| RMV 2 | 20.0 | 0.22 ± 0.02 |
| RMV 3 | 35.0 | 0.62 ± 0.03 |
| RMV 4 | 50.0 | 1.22 ± 0.06 |
| RMV 5 | 65.0 | 2.02 ± 0.10 |

Each level stores: WOB value (kPa), Status (Pass/Fail)

**Orifice B (RMV 5–7):**

| RMV Level | Minute Ventilation (LPM) | Limit (kPa) |
|-----------|--------------------------|--------------|
| RMV 5 | 65.0 | 0.62 ± 0.03 |
| RMV 6 | 85.0 | 1.05 ± 0.05 |
| RMV 7 | 105.0 | 1.58 ± 0.08 |

Each level stores: WOB value (kPa), Status (Pass/Fail)

### NFPA 40 Captured Volume Check
| Field | Units | Notes |
|-------|-------|-------|
| Bell Prover Serial Number | — | Reference equipment (e.g., 2852) |
| **Per test (3 tests):** | | |
| Start | mm | Bell prover start position |
| End | mm | Bell prover end position |
| Travel | mm | End - Start |
| Breaths | count | Fixed: 20 |
| Time | sec | Measured |
| Vol | L | Calculated volume |
| **Averages:** | | |
| Avg Vol | L | Mean of 3 tests |
| STD DEV | L | Std dev of 3 tests |
| BPM | breaths/min | Breathing rate |
| RMV | LPM | Achieved respiratory minute volume |
| Status | Pass/Fail | |

### NFPA 103 Captured Volume Check
Same structure as NFPA 40 section above, with different target breathing rate.

### Embedded Calibration Data (trailer)
Starts at ~offset 0x1AA56. Contains the full calibration record for the unit's sensors in the same format as the .cal file (see below).

---

## Calibration .cal File Layout

Each .cal file (~1.5 KB) stores calibration data for one OMNIcheck unit. Extension: `.cal`. Filename format: `OMNI-{MAC}_{YYYYMMDD}_Cal.cal`.

### Header
| Field | Example |
|-------|---------|
| Last Cal Date | `11:23:16.135 AM 1/16/2020` |
| Last Cal Status | `Pass` |
| DAQ Model | `NI USB-6001` |
| DAQ Serial Number | (string) |
| New Sensor Wiring? | ON/OFF |
| OMNI Serial Number | (string) |

### Sensor Blocks (6 sensors)

Each sensor stores:

| Field | Notes |
|-------|-------|
| Manufacturer | e.g., Alpha Instruments, ifm electronics, Amphenol, Apogee |
| Model | e.g., Model 161, PT9559, MA 100, SBY-110 |
| Range | e.g., 0to14, 0to5800, 32-128, 112.5-862.6 |
| Units | inWg, psi, °F, mmHg |
| Serial Number | Per-sensor |
| Accuracy | e.g., ±0.25%, ±0.5%, ±0.5°F, ±11.25 |
| Polynomial Coefficients | 4 coefficients for voltage→engineering unit conversion |
| Calibration Table | Raw Input (X) → Calibration Input (Y) point pairs |

#### Sensor order in file:
1. **Eye Sensor** (Low Pressure) — Alpha Instruments Model 161, inWg
2. **Mouth Sensor** (Low Pressure) — Alpha Instruments Model 161, inWg
3. **IP Sensor** (Medium Pressure) — ifm PT9559, psi
4. **Gas Temp Thermistor** — Amphenol MA 100, °F (uses voltage→°F lookup table instead of cal table)
5. **Barometric Sensor** — Apogee SBY-110, mmHg
6. **HP Sensor** (High Pressure) — ifm PT9559, psi

### Unit ID
Embedded at end of file (e.g., `12092024OCS14`).

---

## Binary Encoding

Both file types use the same encoding for structured fields:
- **Strings:** 4-byte big-endian length prefix + UTF-8 bytes
- **Doubles:** IEEE 754, big-endian (8 bytes each)
- **Section separators:** Runs of `0x01` bytes between major sections

The test .bin payload between the header and trailer contains ~13,600 raw doubles of waveform/measurement data. The exact field ordering within this payload needs to be mapped against the UI layout above.
