# S1-Opening — CVD-Based Opening Type Detection Report

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Commits:** `9888a5e` (golden) → `0c47bb9` (implementation)  
**Flag:** `S1_CVD_OPENING=False` (OFF)

---

## Golden Baseline

```
test_opening_type_enum_values   PASSED
test_drive_detection            PASSED
test_auction_in_detection       PASSED
test_test_drive_detection       PASSED
```

---

## Manifest — What Changed

### New function: `detect_opening_type_cvd()`

**File:** `backend/v9/systems/day_type/detector.py`

Flag OFF → delegates to original `detect_opening_type()`, returns empty shadow dict.  
Flag ON → computes CVD metrics from `footprint_deltas`, produces shadow label **alongside** original result. Original result is **always the live path**.

| Metric | Formula | Source |
|--------|---------|--------|
| PE (Participation Efficiency) | `net_CVD / Σ|delta|` | `v9_bars_footprint.delta` |
| net_CVD_ratio | `|net_CVD| / total_vol` | same |
| CVD sign flip | first half vs second half sign | same |
| Divergence | price direction ≠ CVD direction | price from bars, CVD from deltas |

### Shadow labels (priors)

| Label | Conditions | Confidence |
|-------|-----------|------------|
| DRIVE | PE_30 > 0.65, range expansion, no divergence | 0.7 + PE×0.3 |
| AUCTION | net_CVD_ratio < 0.15, PE < 0.25 | 0.5 |
| REJECTION_REVERSE | CVD sign flip + divergence | 0.6 |

### New function: `classify_gap_atr()`

| Tier | gap/ATR14_daily | Absolute fallback |
|------|----------------|-------------------|
| TINY | < 0.25 | < 3 pt |
| SMALL | 0.25–0.50 | 3–6 pt |
| MEDIUM | 0.50–1.0 | 6–12 pt |
| LARGE | ≥ 1.0 | ≥ 12 pt |

### Not Changed

- Original `detect_opening_type()` — unchanged, still the live path
- OpeningType enum — unchanged
- directional_ratio, pullback thresholds — unchanged
- No routing to playbook/order

---

## Flag State

| Flag | Value | Effect |
|------|-------|--------|
| `S1_CVD_OPENING` | `False` | Original detection unchanged, empty shadow dict |

---

## Regression Output (raw)

```
$ BRIDGE_TOKEN=michael-mems26-2026 python3 -m pytest tests/v9/regression/ tests/v9/test_atr.py -v

52 passed in 0.11s

Breakdown:
  S2 golden:    9 passed
  S2 relative: 13 passed
  S3 golden:    4 passed
  S3 relative:  7 passed
  S1 golden:    4 passed
  S1 relative:  9 passed
  ATR:          6 passed
```

---

## Next: S1-daytype (IB width ATR + staged confidence model)
