# WOB → Volume Prediction Study

**Objective:** Determine if Total WOB Avg at NFPA 40 and NFPA 103 breathing rates can reliably predict bell prover tidal volume, potentially eliminating the gasometer test.

## Data Sources

1. **Manual spreadsheet** (`OC QA Notes.xlsx`): Historical WOB + bell prover data from V1-era manual tracking. Multiple attempts per unit — use latest per unit.
2. **V2 .bin files**: Automatic WOB extraction from V2 test software. Paired with bell prover volumes from PDF reports.

## Preliminary Results (2026-04-13, n=14/12)

### NFPA 40 (n=14)
```
Model: Vol = 0.8748 + 1.0503 × WOB
R² = 0.26
95% PI = ±0.016 L (INSIDE ±0.1 L spec)
```
Low R² but extremely tight prediction interval. Both WOB and volume have almost no variation — the process is inherently consistent at NFPA 40 flow rates. The gasometer isn't adding information here.

### NFPA 103 (n=12)
```
Model: Vol = -38.852 + 36.028 × WOB
R² = 0.55
95% PI = ±0.181 L (OUTSIDE ±0.1 L spec)
```
Higher variation in volume, WOB explains only half. Not yet sufficient to replace gasometer. Need more data with wider WOB range.

## Decision Criteria

| Metric | Threshold | NFPA 40 | NFPA 103 |
|--------|-----------|---------|----------|
| 95% PI width | < ±0.1 L | ±0.016 ✓ | ±0.181 ✗ |
| R² | > 0.80 (informational) | 0.26 | 0.55 |

**The binding criterion is prediction interval width vs spec tolerance**, not R². A low R² with tight PI (like NFPA 40) still passes because the process variation is small enough that any prediction is within spec.

## Milestones

| Units | Status | Action |
|-------|--------|--------|
| 20 matched pairs | Email notification to sby@atorlabs.com + jkc@atorlabs.com | Re-run regression, update dashboard, report R² and PI |
| 30 matched pairs | Email notification | Final go/no-go recommendation |

## Accelerator
Re-test existing V1 units on V2 software (just for WOB data). Bell prover volumes already exist in the PDF dataset. Each re-test adds a matched pair immediately.

## Data Collection
Automated: as V2 .bin files accumulate, the parser extracts Total WOB Avg. Matched against bell prover volumes from PDF extraction. Study auto-updates on each dashboard regeneration.
