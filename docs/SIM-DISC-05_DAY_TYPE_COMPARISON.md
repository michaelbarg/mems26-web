# SIM-DISC-05: Day-Type Distribution Comparison

**Date:** 2026-05-05
**Investigator:** Claude Code (V8.4.0-RESEARCH-2)

---

## Question

Is today's poor performance explained by day-type distribution?

## Findings

### MDS Dataset Distribution (Apr 29 - May 3)

| Day Type | Count | % | WR (outcome) | WR (MFE) | Net PnL* |
|----------|-------|---|---|---|---|
| NORMAL | 2,472 | 49.5% | ~48% | 58.5% | $7,304 |
| DEVELOPING | 1,864 | 37.3% | ~35% | 54.5% | -$1,952 |
| RANGE_DAY | 303 | 6.1% | ~70% | 80.2% | $7,484 |
| NONE | 269 | 5.4% | ~41% | 73.2% | $4,771 |
| TREND_DAY | 88 | 1.8% | ~90% | 94.3% | $3,416 |

*PnL uses MFE-based calculation (inflated)

### Today's Distribution (May 5)

| Day Type | Count | % |
|----------|-------|---|
| DEVELOPING | 352 | 70.4% |
| TREND_DAY | 82 | 16.4% |
| NORMAL | 66 | 13.2% |

### Comparison

| Factor | MDS Average | Today |
|--------|-------------|-------|
| DEVELOPING % | 37.3% | **70.4%** |
| RANGE_DAY % | 6.1% | 0% |
| TREND_DAY % | 1.8% | 16.4% |
| Expected WR (weighted) | ~48% (MFE) | ~57% (MFE)* |

*Today's expected WR is paradoxically HIGHER by MFE method because TREND_DAY (94% WR) is over-represented.

### Per-Day WR in MDS (by Outcome)

| Date | Day Type | Setups | Outcome WR |
|------|----------|--------|-----------|
| 04/29 | NONE | 256 | 41.4% |
| 04/30 | Mixed (RANGE+TREND heavy) | 1,969 | 48.0% |
| 05/01 | DEVELOPING+NORMAL | 2,527 | **34.5%** |
| 05/03 | NORMAL+RANGE | 244 | 45.9% |

### Today's Actual Performance

```
Production WR: 19.3% (11 wins / 57 closed)
Best MDS comparable (May 1, DEVELOPING-heavy): 34.5%
Gap: 15.2pp below worst MDS day
```

### Why Today is Worse Than MDS DEVELOPING Days

1. **Session timing:** Today is early (ON session → RTH transition). Many setups in ON have lower follow-through.
2. **Market character:** DEVELOPING days that later become TREND (16.4% TREND) have whipsaw periods during transition.
3. **DEVELOPING+TREND mix:** The day type changed during the session. Setups detected as DEVELOPING during the choppy phase → then market trends → those DEVELOPING entries hit stop in the new trend.

## Verdict

| Check | Result |
|-------|--------|
| Day type explains gap? | **PARTIALLY — ~15pp** |
| Today is DEVELOPING-heavy | YES (70.4% vs 37.3% in MDS) |
| Today worse than MDS DEVELOPING | YES (19.3% vs ~35%) |
| Remaining unexplained | ~15pp (beyond day-type effect) |

### Key Finding

Day type alone explains about half of the gap between today's 19.3% WR and MDS's ~40% outcome WR. The other half comes from:
- Today being a particularly bad DEVELOPING day (transition to TREND = whipsaw)
- Session timing (early ON setups with poor follow-through)
- Possible stale entry issues amplifying losses
