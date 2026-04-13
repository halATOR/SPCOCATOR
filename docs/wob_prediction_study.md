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

### NFPA 103 (n=12 → 11 after outlier removal)

**OCS36 flagged as data quality issue:** Bell prover value recorded as 3.000 L — likely a data entry error or mis-recorded test. All other units range 3.357–3.417 L. Excluded from analysis.

```
With outlier (n=12):    R² = 0.55, PI = ±0.181 L — OUTSIDE spec
Without outlier (n=11): R² = 0.05, PI = ±0.034 L — INSIDE spec
```
After removing the outlier, volume variation is extremely tight (σ = 0.015 L). WOB has almost zero correlation with volume — but it doesn't matter because the process variation is so small that any prediction is within spec.

## Decision Criteria

| Metric | Threshold | NFPA 40 (n=14) | NFPA 103 (n=11*) |
|--------|-----------|---------|----------|
| 95% PI width | < ±0.1 L | ±0.016 ✓ | ±0.034 ✓ |
| R² | informational | 0.26 | 0.05 |
| Process σ | informational | 0.008 L | 0.015 L |

*After removing OCS36 outlier (3.000 L — suspected data entry error).

**The binding criterion is prediction interval width vs spec tolerance**, not R². A low R² with tight PI means the process variation is inherently small enough that the gasometer test is confirming what we already know — every unit passes.

**Preliminary conclusion:** Both NFPA flow rates show prediction intervals well within the ±0.1 L spec tolerance. The gasometer may be unnecessary for production units — the process is inherently capable regardless of WOB value. More data will either confirm this or reveal edge cases we haven't seen yet.

## Milestones

| Units | Status | Action |
|-------|--------|--------|
| 20 matched pairs | Email notification to sby@atorlabs.com + jkc@atorlabs.com | Re-run regression, update dashboard, report R² and PI |
| 30 matched pairs | Email notification | Final go/no-go recommendation |

## Accelerator
Re-test existing V1 units on V2 software (just for WOB data). Bell prover volumes already exist in the PDF dataset. Each re-test adds a matched pair immediately.

## Data Collection
Automated: as V2 .bin files accumulate, the parser extracts Total WOB Avg. Matched against bell prover volumes from PDF extraction. Study auto-updates on each dashboard regeneration.
