# SIM-STOP-05: Structural Stop with Cap

**Date:** 2026-05-05 (Day 2 Evening)

---

## Method

- Parsed `shadow_structural_stop` from `score_reasons` field
  (format: "Shadow stop: X.XXpt (trigger_TYPE, width) vs 5pt fixed")
- Applied cap: min(structural, 10pt ATR proxy)
- Reject threshold: >15pt (none triggered — max was 15pt)
- Compared vs fixed 5pt stop using MAE/MFE forward measurement
- N = 970 setups with structural stop data (19.4% of dataset)

---

## Structural Stop Distribution

| Range | Count | WR (fixed outcome) |
|-------|-------|---|
| 3-5pt | 182 | 35.7% |
| 5-7pt | 155 | 47.4% |
| 7-10pt | 227 | 44.4% |
| 10-12pt | 154 | 43.2% |
| 12-15pt | 180 | 59.2% |
| 15pt+ | 72 | 88.9% |

Mean: 8.91pt, Median: 8.50pt

---

## Comparison Results

| Method | Trades | Wins | Losses | Timeouts | WR | Net PnL | Avg/trade |
|--------|--------|------|--------|----------|-----|---------|-----------|
| Fixed 5pt | 970 | 472 | 488 | — | 49.2% | -$5,798 | -$5.98 |
| Structural+Cap | 970 | 388 | 559 | 23 | 41.0% | -$12,489 | -$12.88 |

**Improvement: -$6.90/trade (NEGATIVE)**

---

## Why Structural Stop Performs Worse

### Problem 1: Wider stop = bigger loss

Fixed stop: loss = 5pt × $5 × 2 = $50 per loss
Structural stop: loss = 8.91pt × $5 × 2 = $89 per loss (78% bigger!)

### Problem 2: Target unreachable

With 1R target at 8.91pt, fewer setups reach target within 60 minutes.
- Fixed (5pt target): 49.2% reach it
- Structural (8.91pt target): 41.0% reach it

### Problem 3: The "wide stop = high WR" paradox

The 12-15pt band shows 59.2% WR with fixed stop because those setups have
more room to breathe. But if you SET the stop at 12-15pt:
- Losses are $120-150 each
- Wins need 12-15pt move (fewer)
- Net result is worse despite higher stop-survival rate

### What About Asymmetric R:R?

If structural stop is 8.91pt but target stays at 5pt (original C1):
- R:R becomes 0.56:1 (worse than 1:1)
- Need >64% WR to break even
- Actual WR at 5pt target with 8.91pt stop: ~65% (MAE < 8.91pt AND MFE >= 5pt)
- Barely breakeven after costs

---

## VERDICT

| Criterion | Target | Result |
|-----------|--------|--------|
| Outperforms fixed by >$10/trade | >+$10 | **-$6.90 (FAIL)** |

### Recommendation

1. **KEEP fixed 5pt stop** as default
2. Structural stop data IS useful — but as a **rejection filter**, not replacement:
   - If structural stop would be >12pt → the level is too far → REJECT entry
   - If structural stop is 3-5pt (tighter than fixed) → TIGHTEN stop to structural
3. **Hybrid approach for Phase 3.3:**
   - Stop = min(5pt, structural) when structural < 5pt
   - Reject when structural > 10pt (setup too close to level for good entry)
   - Keep 5pt when structural is 5-10pt
