# SIM-CONF-04: Pattern Sequence Memory

**Date:** 2026-05-05 (Day 2 Evening)

---

## Method

- Analyzed 4,992 sequential pairs (setup A → setup B within 60 minutes)
- Grouped by: previous setup's (direction + outcome) → current direction
- Minimum 30 samples per group for statistical validity
- Base WR for comparison: 47.3% (outcome-based)

---

## Top Sequences by Edge

| Sequence | N | WR | Edge vs Base | Avg MFE |
|----------|---|-----|---|---|
| LONG_HIT_C1 → LONG | 395 | 87.9% | **+40.6pp** | 2.62R |
| SHORT_HIT_C1 → SHORT | 188 | 87.5% | +40.2pp | 2.28R |
| LONG_HIT_STOP → SHORT | 824 | 86.9% | +39.6pp | 2.52R |
| SHORT_HIT_STOP → LONG | 818 | 85.4% | +38.1pp | 3.06R |
| LONG_HIT_STOP → LONG | 378 | 13.3% | **-34.0pp** | 1.68R |
| SHORT_HIT_STOP → SHORT | 245 | 6.7% | -40.6pp | 0.95R |
| SHORT_HIT_C1 → LONG | 725 | 2.9% | -44.4pp | 1.58R |
| LONG_HIT_C1 → SHORT | 726 | 2.6% | -44.7pp | 0.76R |

### Meta-Patterns

| Pattern | N | WR | Edge |
|---------|---|-----|------|
| After win → same direction | 583 | 87.8% | +40.5pp |
| After win → reverse direction | 1,451 | 2.8% | **-44.5pp** |
| After loss → same direction | 623 | 10.7% | -36.5pp |
| After loss → reverse direction | 1,642 | 86.2% | +38.9pp |

---

## Stale Entry Verification

| Sequence | % Stale (same price) | Genuine N | Genuine WR |
|----------|---------------------|-----------|-----------|
| LONG_C1 → LONG | 36% | 254 | **82.3%** |
| LONG_STOP → SHORT | 72% | 227 | **74.7%** |

After removing stale duplicates, edges remain large:
- Continuation after win: **+35pp** (genuine)
- Reversal after loss: **+27pp** (genuine)

---

## Interpretation

### Why These Edges Exist (Caution Required)

The edges are **real but not predictive** in the traditional sense:

1. **Shared measurement window:** When setup A (LONG) hits C1 at minute 20, the market has moved up. Setup B (LONG, emitted at minute 21) enters the SAME favorable move. Both use the same 60-min forward window measured from their respective entry times, but those windows heavily overlap.

2. **Direction persistence:** The "after win → same direction" rule essentially says: "if the market is trending, the next setup in that direction also wins." This is market momentum, not sequence prediction.

3. **Reversal after loss → opposite:** Same logic inverted. If LONG hits stop (market went down), the next SHORT benefits from the same downward move.

### What's Actually Useful

The **anti-patterns** are more actionable:
- After win → reverse: 2.8% WR (AVOID)
- After loss → same direction: 10.7% WR (AVOID)

**Rule: Never reverse direction immediately after a win. Never re-enter same direction after a loss.**

---

## Hypothetical PnL

If only taking "after win → same direction" setups: **+$12,578** on 395 trades
(vs -$38,741 for all 4,996 trades)

---

## VERDICT

| Criterion | Target | Result |
|-----------|--------|--------|
| Top sequence >10pp edge | >10pp | **+40.6pp (PASS)** |
| Survives stale dedup | Yes | **+35pp genuine (PASS)** |
| Predictive (new information) | ? | **CAUTION — shared measurement window** |

### Recommendation

1. **Implement anti-pattern filter:** Reject setups that reverse direction within 5 min of a win, or repeat direction within 5 min of a loss
2. **Do NOT implement as entry signal** — the edge comes from overlapping measurement, not from true sequence prediction
3. **Test on deduped sequential data** to verify genuine predictive power
