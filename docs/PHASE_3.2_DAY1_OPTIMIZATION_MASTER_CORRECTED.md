# Phase 3.2 Day 1 Optimization — CORRECTED Results

**Date:** 2026-05-05 (re-run with outcome-based PnL)
**Fix applied:** `sim_dec_runner.py` now uses `outcome` column instead of `mfe_R >= 1.0`

---

## What Changed

The original Day 1 optimization (`run_all_tracks.py`) used `mfe_pnl()` which
counts MFE reaching a price level as a "fill." In reality, 19% of setups that
TOUCH 1R subsequently reverse and hit the stop loss.

The sequential filter (`apply_sequential_filter`) reduces 4,996 setups to ~46 trades.
These 46 trades are the ONLY ones that matter for PnL projection.

---

## CFG-alpha/beta: Before vs After

### CFG-alpha: `t70 | skip_OFF_HOURS | w20_20_40 (FVG heavy)`

| Metric | MFE-based (original) | Outcome-based (corrected) |
|--------|---------------------|--------------------------|
| Trades (5 days) | 14 | 14 |
| WR | 84.6% | **84.6%** |
| Net PnL | $559.50 | **$559.50** |
| Profit Factor | 5.50 | **5.50** |
| Avg/trade | $39.96 | **$39.96** |
| $/day | $111.90 | **$111.90** |

### CFG-beta: `t60 | skip_OFF_HOURS | w30_30_20 (Vegas+TPO heavy)`

| Metric | MFE-based (original) | Outcome-based (corrected) |
|--------|---------------------|--------------------------|
| Trades (5 days) | 15 | 15 |
| WR | 85.7% | **85.7%** |
| Net PnL | $506.50 | **$506.50** |
| Profit Factor | 7.00 | **7.00** |
| Avg/trade | $33.77 | **$33.77** |
| $/day | $101.30 | **$101.30** |

### Why CFG-alpha/beta Numbers Didn't Change

The sequential filter + high threshold means these configs only take trades
where `sim_outcome = HIT_C1` (winner) or `HIT_STOP` (loser). The MFE vs
outcome distinction only matters when MFE >= 1R but outcome = HIT_STOP.

For CFG-alpha: 11/13 decisive trades are HIT_C1. These same 11 also have MFE >= 1R.
The 2 HIT_STOP trades have MFE < 1R. So for THIS subset, MFE and outcome agree.

**The bug only affects configs with MORE trades** (lower thresholds) where the
19% "touch-and-reverse" population becomes significant.

---

## What DID Change (High-Volume Configs)

| Config | Original $/day | Corrected $/day | Change |
|--------|---------------|-----------------|--------|
| V1 baseline (t0, all) | +$60/day* | **-$24/day** | -$84 |
| V2 skip_DEV (t50) | +$40/day* | **-$108/day** | -$148 |
| DL-best (t30, skip_DEV) | +$25/day* | **-$66/day** | -$91 |

*Original estimates from Day 1 MFE-based run

**Configs with 30+ trades/day are NET NEGATIVE** because the 19% reversal rate
turns paper wins into actual losses.

---

## Corrected Conclusion

### The Only Profitable Approach: Ultra-Selective

```
Sequential filter (1 at a time)
  + High threshold (60-70)
  + Skip OFF_HOURS
  + Correct weight mix (FVG or Vegas+TPO dominant)
  = 2-3 trades/day at 85% WR = ~$100/day
```

### Invalid Approaches (all net-negative with outcome logic)

- "Trade more with lower threshold" — fails (47% WR × costs = net loss)
- "Skip DEVELOPING only" — insufficient (still 39% WR)
- "VWAP + FP filters only" — improves WR to 50% but costs eat profit
- "DL V1.1 approved subset" — 37.6% WR (worse than random!)

---

## Walk-Forward Stability

| Config | IS (70%) | OOS (30%) | Verdict |
|--------|----------|-----------|---------|
| CFG-alpha | +$426, 81.8% | +$134, 100% | **STABLE** |
| CFG-beta | +$373, 83.3% | +$134, 100% | **STABLE** |

Both configs profitable in both periods. Small OOS sample (3-4 trades) but
direction is correct.

---

## Revised Phase 3.3 Targets

| Metric | Original Target | Corrected Target |
|--------|----------------|------------------|
| $/day | $292 | **$100-112** |
| $/month | $5,840 | **$2,000-2,200** |
| Trades/day | 14 | **2-3** |
| WR | 85% | **85%** |
| Max daily loss | -$100 | **-$100** (1 stop) |
| Breakeven days needed | 5 | **20+** (due to low volume) |

---

## Key Takeaway

**The edge is REAL but SMALL in dollar terms.**

85% WR with PF 5.5 is exceptional. But 2-3 trades/day × $35 avg profit = $100/day.
This compounds to $2K+/month which is meaningful for MES.

The danger is trying to "scale up" by lowering thresholds or taking more trades.
Every attempt to increase volume drives WR below 50% and turns profitable into losing.

**Discipline = the edge.** The system works by saying NO to 99% of signals.
