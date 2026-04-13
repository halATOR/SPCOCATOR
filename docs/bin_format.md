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

---

## Test .bin V2 Layout ("QA Report Data Complete Cluster")

New software version adds WOB volume correction data, operator comments, and an explicit pass/fail disposition. V2 files come from units tested with the updated OMNIcheck calibrator software. V1 files remain for historical data.

### How to distinguish V1 vs V2
**File size:** V1 files are ~111 KB. V2 files are ~206 KB (nearly double). The extra ~95 KB is raw P-V waveform data for the WOB volume correction calculations.

### V2 file structure (confirmed from hex analysis)
```
Bytes 0x0000 - 0x003A:  Header strings (same as V1: unit ID, time, date, technician)
Bytes 0x003B - 0x1AB8E:  V1-compatible payload (~109 KB, same as V1)
                          - Orifice test raw data
                          - Leak test raw data
                          - Bell prover test raw data
                          - Per-breath volume correction arrays
Bytes 0x1AB8F - 0x1B1A1:  Embedded cal data trailer (same as V1)
Bytes 0x1B1A2 - end:      V2-extra: ~95 KB of raw P-V waveform data
                          - NFPA 40 pressure/volume loops
                          - ISO High pressure/volume loops
                          - NFPA 103 pressure/volume loops
```

### V2 WOB summary values
The UI shows computed summary values (Pressure Max/Min Avg, Elastance Avg, Inhale/Exhale/Total WOB Avg) but these are **not stored as separate fields** in the .bin file. They are computed on-the-fly by LabVIEW from the raw waveform data.

To extract Total WOB Avg: compute the area inside the pressure-volume hysteresis loop from the raw P-V waveform data. Requires identifying which doubles are pressure vs volume and the array boundaries for each NFPA test condition.

### V2-extra section layout (CONFIRMED via hex analysis)

**Header:** 13 bytes (`U32=1, U16=4, U32=1, 3 bytes padding`)

**3 sequential WOB correction blocks** (NFPA 40, ISO High, NFPA 103). Each block:

```
6 × float64   Summary values (see below)
1 × float32   Adj L to V volume correction factor
1 × U32       Columns (always 2 — pressure + volume channels)
1 × U32       Rows (varies: 1429–2500 per condition)
N×2 × float64 Interleaved P-V waveform data (pressure, volume, pressure, volume, ...)
```

**Block size formula:** `6×8 + 4 + 4 + 4 + cols × rows × 8` bytes

**Summary value order:**
| Index | Field | Units | Validation |
|-------|-------|-------|------------|
| 0 | Pressure Max Avg | kPa | Positive |
| 1 | Total WOB Avg | kPa·L | = Inhale + Exhale |
| 2 | Pressure Min Avg | kPa | Negative |
| 3 | Inhale WOB Avg | kPa·L | Positive |
| 4 | Exhale WOB Avg | kPa·L | Positive |
| 5 | Elastance Avg | kPa/L | Small positive |

**Note on Block 1 (NFPA 40):** The Adj L to V float32 at the expected position (byte 48 of the block) reads as 0.946 — which may indicate the format is slightly different for Block 1 (7 doubles instead of 6+f32, with the first double being the Adj L to V = 0.0). Blocks 2 and 3 clearly follow the 6-double + float32 pattern, with Adj L to V values of 2.575 and 2.640 respectively.

**Verified values from OCSA57 (2026-04-10):**

| Metric | NFPA 40* | ISO High | NFPA 103 |
|--------|---------|----------|----------|
| Pressure Max Avg | 0.086 | 4.978 | 3.421 |
| Total WOB Avg | 0.007 | **1.576** | **1.165** |
| Pressure Min Avg | -0.115 | -5.102 | -3.471 |
| Inhale WOB Avg | 0.003 | 0.804 | 0.605 |
| Exhale WOB Avg | 0.004 | 0.772 | 0.560 |
| Elastance Avg | 0.004 | 0.006 | 0.017 |
| Adj L to V | — | 2.575 | 2.640 |
| Waveform rows | 2500 | 1429 | 2001 |

*NFPA 40 values appear suspect for this unit — engineer investigating raw data.
Validation: ISO High Total WOB (1.576) = Inhale (0.804) + Exhale (0.772) ✓
Validation: NFPA 103 Total WOB (1.165) = Inhale (0.605) + Exhale (0.560) ✓

**File tail:** ~210 bytes after Block 3 (padding or metadata).

### New/Changed Fields vs V1

**Comments** (NEW):
- Free text field for operator notes
- Used in failure reports to document why the test failed

**Basic Information** (expanded):
| Field | Example |
|-------|---------|
| Date | `1/30/2024` |
| Time | `10:02 AM` |
| OMNI S/N | `12345678` |
| Technician | `Jake C.` |

**Configuration** (NEW):
| Field | Example |
|-------|---------|
| OMNI S/N | (serial number) |
| Customer | `Ator Labs` |
| Pressure Limit (inH2O) | `14.1` |

**Overall Disposition** (NEW — top-level):
- Pass/Fail status for the entire test

**WOB Volume Correction Factors** (NEW — the key new data):

Three test conditions: NFPA 40, ISO High, NFPA 103. Each stores:

| Field | Units | Notes |
|-------|-------|-------|
| Adj L to V | — | Volume correction factor (e.g., 2.620, 2.580) |
| Pressure Max Avg | kPa | Average peak positive pressure across breathing cycles |
| Pressure Min Avg | kPa | Average peak negative pressure |
| Elastance Avg | kPa/L | Average elastance of the breathing circuit |
| Inhale WOB Avg | kPa·L | Average work of breathing on inhalation |
| Exhale WOB Avg | kPa·L | Average work of breathing on exhalation |
| Total WOB Avg | kPa·L | Inhale + Exhale WOB (3 decimal precision) |

> **SPC value:** Total WOB Avg at NFPA 40 and NFPA 103 breathing rates may predict bell prover volume results. If correlation is strong (high R²), WOB alone can replace the gasometer test — saving significant test time.

**WOB Avg Graph**: per-condition graphical data (waveform or trend — likely stored as array of doubles in the .bin)

**Leak test + Orifice Test Data**: same as V1.

### Failure .bin Files

V2 software allows technicians to save .bin files for **failed** tests. These are stored in a separate folder from passing tests.

Failure .bins contain:
- All the same fields as a passing test
- Overall Disposition = FAIL
- Comments field with operator notes on failure cause
- Partial or complete test data (depending on which section failed)

**SPC value from failure data:**
- Fail count per unit (number of .bin files before the passing one)
- Which test section caused failure (leak? WOB? volume?)
- Operator failure comments for root cause analysis
- Real first-pass yield: (units with 0 fail bins) / (total units tested)
- Note: elapsed time between fail and pass is NOT useful for rework time estimation — units may sit idle between attempts

---

## Binary Encoding

Both file types use the same encoding for structured fields:
- **Strings:** 4-byte big-endian length prefix + UTF-8 bytes
- **Doubles:** IEEE 754, big-endian (8 bytes each)
- **Section separators:** Runs of `0x01` bytes between major sections

The test .bin payload between the header and trailer contains ~13,600 raw doubles of waveform/measurement data. The exact field ordering within this payload needs to be mapped against the UI layout above.
