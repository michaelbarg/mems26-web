# SIM-DISC-01: Bar Resolution Audit

**Date:** 2026-05-05
**Investigator:** Claude Code (V8.4.0-RESEARCH-2)

---

## Question

Does MDS use tick-level data or bar-aggregated data?

## Findings

### Data Source Chain

```
sim_dec_runner.py
  → _load_dataset()
    → pl.read_parquet("cache/setups_clean_2026-05-05_full.parquet")

The parquet was created by data_loader.py:
  → fetch_raw_from_pg() 
    → SELECT hypothetical_mae_60min_pts, hypothetical_mfe_60min_pts
    → These are renamed to mae_pts, mfe_pts
```

### What `hypothetical_mae_60min_pts` Actually Is

This column measures the **Maximum Adverse/Favorable Excursion within a 60-minute window** after setup detection. It is:

- **NOT tick-level outcome data** (no retro tick columns present)
- **NOT real execution data** (no fill prices, no slippage)
- A **60-minute forward measurement** aggregated at bar level
- Resolution: 0.25pt (MES tick size) — values align perfectly to tick grid
- All `duration_minutes` values = 60.0 (hardcoded)

### Retro Data Status

```
Retro columns present: NONE
```

The retro runner (`retro/retro_runner.py`) exists but its output was NOT merged into the sim_dec_runner. The SIM-DEC simulations ran without tick-level validation.

### MAE/MFE Characteristics

| Metric | Value |
|--------|-------|
| MAE range | 0.0 - 49.25 pts |
| MFE range | 0.0 - 49.0 pts |
| MAE mean | 9.05 pts |
| MFE mean | 9.04 pts |
| Tick alignment | Perfect (0.0 residual) |

### Critical Issue: MFE != Win

```
MFE >= 1R:     59.7% of setups (price REACHED target at some point)
Outcome HIT_C1: 40.7% of setups (trade CLOSED at target)
Gap:            19.0pp
```

**948 setups (19.0%) touched 1R target but then reversed to hit stop.**

This means MFE measures "did price ever reach this level" — not "did the trade close profitably."

## Verdict

| Check | Result |
|-------|--------|
| Tick-level data | **NO** — uses 60min aggregated MAE/MFE |
| Retro tick merged | **NO** — retro columns absent |
| WR inflation | **YES — 19.0pp** from using MFE as win proxy |

### Impact on Discrepancy

The SIM-DEC simulations used `if mfe_R >= 1.0: WIN` which reports 59.7% WR.
Production outcome-based WR is 40.7% on the same dataset.

**This single bug explains 19.0pp of the gap** — nearly half the total discrepancy.

### Recommendation

All future simulations MUST use the `outcome` column (HIT_C1/HIT_STOP/TIMEOUT), NOT `mfe_R >= 1.0`.
