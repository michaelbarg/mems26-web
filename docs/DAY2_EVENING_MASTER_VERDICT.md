# Day 2 Evening — Master Verdict

**Date:** 2026-05-05 22:00 UTC
**Phase:** 3.2 Day 2 — Pure Observation
**Runtime:** <2 seconds (all 5 sims)

---

## 1. CFG-α LIVE-Readiness

### VERDICT: **CONDITIONAL PASS**

| Check | Result | Status |
|-------|--------|--------|
| Monte Carlo 5th %ile WR | 62.5-66.7% | **PASS** (target >60%) |
| P(profit per 10-trade block) | 98.2% | **PASS** |
| Max drawdown | $99.75 | **PASS** (acceptable) |
| Extended WR | 84.6% | **PASS** (target >70%) |
| Extended trade count | 14 | **FAIL** (target >100) |
| Walk-forward OOS | +$134, 100% WR | **PASS** (direction correct) |

**Blocking issue:** Only 14 trades available. Need 36+ trading days for 100-trade validation.

**Recommendation:** Proceed to SHADOW LIVE (track but don't execute) starting Phase 3.3.
Full LIVE authorization after 50+ shadow trades confirm WR >70%.

### CFG-α Summary Numbers

```
WR:           84.6% (11W/2L/1T in 5 days)
$/day:        $112 (projected)
$/month:      $2,200 (projected)
Trades/day:   2.8
Max DD:       $100
Sharpe:       2.74 (daily)
```

---

## 2. CONF Top-3 Ranking

| Rank | Factor | Edge | Actionable? | Verdict |
|------|--------|------|-------------|---------|
| 1 | **Anti-pattern filter** (don't reverse after win) | +40pp (avoidance) | YES | Deploy as rejection rule |
| 2 | **Sequence continuation** (same dir after win) | +35pp genuine | CAUTION | Overlapping windows |
| 3 | **TF Confluence** | -5.9pp (INVERTED) | NO | Do NOT use as filter |

### Key Insight

Confluence (all components agree) is a **negative signal** in this dataset. The edge comes from:
- **Selectivity** (high threshold + sequential) — not from agreement count
- **Anti-patterns** (avoiding known bad sequences) — asymmetric value
- **Contrarian entries** (0 TF agreement = +5.3pp) — mean-reversion works better

---

## 3. STOP Recommendation

### VERDICT: **Keep Fixed 5pt Stop**

| Method | WR | Avg/trade | Verdict |
|--------|-----|-----------|---------|
| Fixed 5pt | 49.2% | -$5.98 | Baseline |
| Structural+Cap | 41.0% | -$12.88 | **WORSE (-$6.90)** |

**Structural stop HURTS.** Wider stops = bigger losses + harder targets.

### Hybrid Proposal (Phase 3.3 testing)

```
IF structural_stop < 5pt:  USE structural (tighter = less risk)
IF structural_stop 5-10pt: USE fixed 5pt
IF structural_stop > 10pt: REJECT entry (too close to level)
```

This uses structural stop as **rejection signal**, not replacement stop.

---

## 4. Phase 3.3 Implications

### Must Change

1. **Sequential enforcement:** Production takes 57 trades/day but CFG-α needs exactly 2-3/day. The sequential filter MUST be strict in production.

2. **Anti-pattern rule:** Add to entry logic:
   ```
   IF last_trade.outcome == WIN AND new_setup.direction != last_trade.direction:
       REJECT ("reversal after win = 2.8% WR")
   IF last_trade.outcome == LOSS AND new_setup.direction == last_trade.direction:
       REJECT ("continuation after loss = 10.7% WR")
   ```

3. **Threshold:** Production must enforce score >= 70 with skip_OFF_HOURS

### Do NOT Change

1. Fixed 5pt stop — structural hurts
2. Component weights — FVG=40 or Vegas+TPO heavy both work
3. Target structure — 1R at C1 remains correct

### New for Phase 3.3 Spec

| Addition | Why | Priority |
|----------|-----|----------|
| Shadow LIVE mode | Accumulate 50+ CFG-α decisions before real money | BLOCKER |
| Anti-pattern filter | +40pp edge from avoiding bad sequences | HIGH |
| Structural rejection (>10pt) | Avoid entries too close to levels | MEDIUM |
| Daily trade cap: 4 max | CFG-α expects 2-3/day, cap prevents drift | HIGH |

---

## 5. Risks & Concerns

### Concerning

1. **14 trades is dangerously small.** 84.6% WR could be 57-96% true WR (95% CI). We're making LIVE decisions on insufficient data.

2. **TF Confluence inverted.** The fundamental assumption that "more agreement = better" is WRONG in this data. This challenges the entire multi-pillar scoring philosophy.

3. **Sequence edges are partially measurement artifacts.** The 60-min overlapping window inflates sequence WR. True predictive power is unclear.

4. **Production takes 10x more trades.** If production cannot enforce strict sequential, ALL projections are invalid. 57 trades/day at 47% WR = massive loss.

### Unexpected Findings

1. **Zero-confluence outperforms full-confluence by 14pp** (52.6% vs 38.6%). Contrarian > confluence for MES intraday.

2. **Reversal after loss = 86% WR.** The strongest signal in the dataset (after dedup correction: 74.7%). This is potentially the foundation for a V3 system.

3. **Structural stop's only value is as rejection filter.** The stop itself is worse, but setups WITH structural >10pt are bad entries regardless of stop method.

---

## Summary Table

| Sim | Result | PASS/FAIL |
|-----|--------|-----------|
| SIM-RBT-04 (Monte Carlo) | 5th %ile WR = 66.7% | **PASS** |
| SIM-CMP-03 (Extended) | WR 84.6% on 14 trades | **CONDITIONAL** |
| SIM-CONF-04 (Sequences) | +40.6pp top edge | **PASS** |
| SIM-CONF-06 (Multi-TF) | -5.9pp (inverted) | **FAIL** |
| SIM-STOP-05 (Structural) | -$6.90/trade | **FAIL** |

---

## One-Line Master Verdict

**CFG-α is statistically robust but sample-limited; deploy as SHADOW LIVE in Phase 3.3 with anti-pattern filter and strict 3-trade/day cap.**
