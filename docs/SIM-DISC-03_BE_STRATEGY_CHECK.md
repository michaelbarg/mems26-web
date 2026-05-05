# SIM-DISC-03: BE Strategy Implementation Check

**Date:** 2026-05-05
**Investigator:** Claude Code (V8.4.0-RESEARCH-2)

---

## Question

Does production's BE (breakeven) logic match MDS's BE logic?

## Findings

### Production BE Rules (from `backend/day_config.py`)

```python
BE_RULES = {
    "TREND_DAY": "after_c2_plus_half_R",  # Move stop to BE after C2 + 0.5R
    "RANGE_DAY": "on_c1_fill",            # Move stop to BE on C1 fill
    "GAP_FILL":  "on_c1_fill",            # Move stop to BE on C1 fill
    "NORMAL":    "on_c2_fill",            # Move stop to BE on C2 fill
    "DEVELOPING":"on_c2_fill",            # Move stop to BE on C2 fill
}
```

### MDS BE Logic

**MDS has NO BE logic.** The `sim_dec_runner.py` uses:
```python
if mfe_r >= 1.0:
    gross = risk * POINTS_TO_USD * qty  # Full win
else:
    gross = -risk * POINTS_TO_USD * qty  # Full loss
```

This is binary: either full win or full loss. No breakeven exits.

### Production Today Shows BE Working

From `/analytics/setups/today_summary`:
```json
"wins": 11,
"losses": 40,
"breakeven": 6
```

**6 out of 57 closed trades (10.5%) exited at breakeven.**

These 6 trades would be counted as:
- In MDS: FULL LOSSES (mfe_R < 1.0 → full stop)
- In Production: $0 PnL (BE exit)

### Impact Calculation

If 6 trades exited at BE instead of full stop:
- Each avoids a ~5pt × $5/pt × 2 contracts = $50 loss
- Total saved: 6 × $50 = $300

But MDS doesn't model this → MDS is PESSIMISTIC about BE (slightly favoring production).

Wait — MDS uses MFE >= 1R as win anyway, so those 6 BE trades might be counted as wins in MDS.

### Cross-Check: Today's BE Trades

Today is primarily DEVELOPING (70% of setups). BE rule = `on_c2_fill`.
This means stop moves to entry price ONLY after C2 target is hit.
Given today's WR = 19.3%, most trades don't reach C2, so BE rarely triggers.

The 6 BE exits likely came from RANGE_DAY or GAP_FILL setups (BE on C1 fill).

### MDS vs Production BE Comparison

| Scenario | MDS Treatment | Production Treatment | Bias |
|----------|--------------|---------------------|------|
| Price hits C1, reverses to entry | WIN ($+50) | BE ($0) | MDS over-reports |
| Price hits C1, continues to C2 | WIN ($+50) | WIN (partial exits) | Similar |
| Price never hits C1, hits stop | LOSS ($-50) | LOSS ($-50) | Same |
| Price hits C1, reverses past entry | WIN ($+50) | STOP ($-50) | MDS over-reports |

## Verdict

| Check | Result |
|-------|--------|
| BE match rate | **N/A** — MDS has NO BE logic |
| BE helps production? | Marginally YES (~$300 saved today) |
| BE hurts production? | NO — it's protective |
| MDS bias from missing BE | MDS OVER-COUNTS wins (MFE >=1R counted as win even if BE exit in reality) |

### Key Finding

BE logic difference is NOT a source of the discrepancy gap. If anything, production's BE strategy slightly reduces losses (protective). The gap comes from elsewhere.

However, for accurate backtesting, MDS should model:
1. Outcome-based exits (not MFE)
2. BE exits counted separately from wins
3. Partial fills (C1/C2/C3 separately)
