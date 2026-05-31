# D-094: R:R Fire Selection (DRAFT — PROPOSED)

**Status:** PROPOSED · awaiting Michael approval  
**Date:** 2026-05-31  
**Context:** GAP-3 (FULL_PATH_MEGA_TABLE), STATUS_BOARD §⚙️3  
**Scope:** Gateway DEMO/LIVE slot fill logic (SHADOW unaffected)

---

## Problem Statement

Currently the gateway uses **first-wins** for DEMO/LIVE slot fill. When multiple systems (S2, S3, S4) fire on the same bar, whichever `route_setup()` arrives first occupies the slot. There is no comparison of risk-reward quality between competing setups.

---

## Proposed Formula

### Risk (USD)
```
risk_usd = |entry_price − stop_price| × contracts × MES_POINT_VALUE($5)
```

### Reward (USD, weighted by contract split)
```
reward_usd = Σ (|target_i − entry| × split_pct_i × contracts × $5)
           = contracts × $5 × Σ (|target_i − entry| × split_pct_i)
```

Where `split_pct_i` comes from `contract_split.py`:
- Example (OFA 3 contracts): T1=25%→0.75c, T2=50%→1.5c, T3=25%→0.75c
- Example (Flag 2 contracts): T1=50%→1c, T2=50%→1c, T3=0%

### R:R Ratio
```
R_R = reward_usd / risk_usd
    = Σ(|target_i − entry| × split_pct_i) / |entry − stop|
```

Note: contracts cancel out (same for both). R:R is price-distance weighted by split, independent of contract count.

---

## Selection Alternatives

### Option A: Pure R:R (highest wins)

```
winner = argmax(R_R) among competing setups in window
```

**Pro:** Simple, transparent, maximizes expected value.  
**Con:** Ignores confidence. A low-confidence setup with slightly better R:R wins over high-confidence setup.

### Option B: R:R × Confidence (composite score) ← RECOMMENDED

```
score = R_R × confidence
winner = argmax(score)
```

**Pro:** Balances quality (confidence) with value (R:R). A 0.8-confidence setup with 3.0 R:R (score=2.4) beats a 0.5-confidence setup with 4.0 R:R (score=2.0).  
**Con:** Slightly more complex. Confidence scales differ between systems (S2: 0-1.0, S4: 0-1.0, S3: 0-1.0 but differently calibrated).

### Option C: R:R with minimum threshold + confidence tiebreak

```
candidates = [s for s in setups if s.R_R >= MIN_RR_THRESHOLD]
winner = max(candidates, key=lambda s: (s.R_R, s.confidence))
```

**Pro:** Ensures minimum quality bar (e.g., R:R ≥ 1.5). Confidence only for ties.  
**Con:** Threshold choice is arbitrary without calibration.

---

## Buffering Window

**Trade-off:** latency vs completeness.

| Window | Pro | Con |
|--------|-----|-----|
| 0 (no buffer, first-wins) | Zero latency | Current behavior, no improvement |
| Same bar (flush at bar close) | All systems that fire on same bar compete | Max 5 seconds additional latency (bar duration) |
| N bars (e.g., 2 bars = 10 min) | Catches delayed detections | Significant delay; stale entries might move |

**Recommendation:** **Same-bar flush.** Collect all `route_setup` calls within a single 5-min bar, then select at bar close. Implementation: gateway buffers DEMO/LIVE candidates; SHADOW records immediately (unaffected).

---

## Tie-Breaking

When scores are equal:
1. Higher confidence wins
2. If still tied: lower firing_system number wins (S2 > S3 > S4 — more granular detection priority)
3. If still tied: first-wins (arrival order)

---

## Interaction with Existing Gates

```
route_setup() arrives
  ├── cooldown/SSV/chop gates → reject ALL (no SHADOW either)
  ├── cluster_guard → blocks DEMO/LIVE only
  │
  ├── SHADOW: always record (no selection, no buffer) ← UNCHANGED
  │
  └── DEMO/LIVE buffer:
      ├── collect candidates within bar window
      ├── at bar-close: compute R:R × confidence for each
      ├── winner fills slot
      └── losers: logged as "outranked" (not "blocked")
```

**SHADOW is never affected** by selection logic. It records every setup that passes hard risk gates.

---

## Open Questions for Michael

1. **Which option?** A (pure R:R) / B (R:R × confidence) / C (threshold + tiebreak)?
2. **Minimum R:R threshold?** Should there be a floor below which no setup fires DEMO/LIVE regardless? (e.g., R:R < 1.0 already rejected by pre_fire_validator — is that sufficient?)
3. **Buffering window:** Same-bar (recommended) or longer? Zero (keep first-wins)?
4. **Cross-system confidence calibration:** S2/S3/S4 confidence scales are independently derived. Should they be normalized before composite scoring?
5. **Implementation phase:** P5 (alongside LIVE wiring) or separate earlier milestone?
6. **MES_POINT_VALUE dedup:** Fix the 4-file duplication as part of this or separately?

---

## Implementation Sketch (NOT executed — for estimation only)

1. Add `compute_rr_score(setup_dict)` utility (~20 lines)
2. Gateway: add `_demo_candidates: List[dict]` buffer
3. Gateway: on bar-close event (from bar_router), select winner and fill slot
4. Tests: verify SHADOW unaffected, verify R:R ranking, verify tie-breaking
5. Estimated: ~100-150 lines of new code + tests

**Gate:** No implementation without Michael locking answers to Q1-Q5 above.
