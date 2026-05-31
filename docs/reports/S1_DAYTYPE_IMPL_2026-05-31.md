# S1-Daytype — IB Width ATR + Staged Confidence Report

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Commits:** `b419c9c` (golden) → `7a64361` (implementation)  
**Flags:** `S1_IB_WIDTH_ATR=False`, `S1_DAYTYPE_STAGING=False` (both OFF)

---

## Golden Baseline

```
test_ib_width_enum_has_original_values  PASSED
test_classify_ib_width_defaults         PASSED
test_classify_ib_width_functional       PASSED
test_confidence_base                    PASSED
test_confidence_max                     PASSED
```

---

## Manifest — What Changed

### 1. IBWidth.EXTREME (schemas.py)

New enum value added: `EXTREME = "EXTREME"` — only reachable when `S1_IB_WIDTH_ATR=True` and `IB_range/ATR > 1.5`.

### 2. classify_ib_width_atr() (detector.py)

| Tier | ATR ratio | Absolute fallback |
|------|----------|-------------------|
| NARROW | < 0.5 | < 15 pt |
| MEDIUM (Normal) | 0.5–1.0 | 15–25 pt |
| WIDE | 1.0–1.5 | > 25 pt |
| EXTREME | > 1.5 | (not reachable when flag OFF) |

Flag OFF → delegates to original `classify_ib_width()`.  
Flag ON + ATR None → fallback to absolute.

### 3. DECISION_MATRIX: EXTREME rows (decision_matrix.py)

| Opening Type | EXTREME maps to |
|-------------|-----------------|
| OPEN_DRIVE | Trend_Normal |
| OPEN_TEST_DRIVE | Variation |
| OPEN_REJECTION_REVERSE | Normal |
| OPEN_AUCTION_IN | Normal |
| OPEN_AUCTION_OUT | Trend_Normal |
| INDETERMINATE | Normal |

Priors — same as WIDE, to be calibrated during soak.

### 4. cap_confidence_staged() (detector.py)

Flag OFF → confidence unchanged.  
Flag ON:
- session_min < 60 (before IB lock): cap at 60%
- session_min ≥ 60 (after IB lock): full confidence

### 5. check_c_period_reeval() (detector.py)

Flag OFF → returns None (no action).  
Flag ON, C-period (session_min 60–90, i.e. 10:30–11:00 ET):
- retrace < 25% → `"HOLD"` (maintain classification)
- retrace ≥ 50% → `"RE_DIAGNOSE"` (re-evaluate)
- between 25–50% → None (no forced action)

### Not Changed

- directional_ratio, delta/width rules, structural votes
- Existing classify_ib_width() — unchanged
- calculate_confidence() — unchanged
- check_reeval_triggers() — unchanged
- No 90-min checkpoint (per spec: "אין צ'קפוינט 90 נפרד")
- No routing to playbook/order

---

## Flag State

| Flag | Value | Effect |
|------|-------|--------|
| `S1_IB_WIDTH_ATR` | `False` | Original classify_ib_width unchanged |
| `S1_DAYTYPE_STAGING` | `False` | Confidence not capped, no C-period reeval |

---

## Regression Output (raw)

```
$ BRIDGE_TOKEN=michael-mems26-2026 python3 -m pytest tests/v9/regression/ tests/v9/test_atr.py -q

71 passed in 0.15s

Breakdown:
  S2 golden:           9 passed
  S2 relative:        13 passed
  S3 golden:           4 passed
  S3 relative:         7 passed
  S1-opening golden:   4 passed
  S1-opening relative: 9 passed
  S1-daytype golden:   5 passed
  S1-daytype relative: 14 passed
  ATR:                 6 passed
```

---

## E2E 2/2 — COMPLETE

All 4 stages implemented behind feature flags:

| Stage | Flag(s) | Files Changed | Tests | Status |
|-------|---------|--------------|-------|--------|
| ATR infra | — | 1 new | 6 | DONE |
| S2 | `S2_ATR_RELATIVE=False` | 8 modified | 22 (9 golden + 13 relative) | DONE |
| S3 | `S3_RELATIVE=False` | 2 modified | 11 (4 golden + 7 relative) | DONE |
| S1-opening | `S1_CVD_OPENING=False` | 1 modified | 13 (4 golden + 9 relative) | DONE |
| S1-daytype | `S1_IB_WIDTH_ATR=False`, `S1_DAYTYPE_STAGING=False` | 3 modified | 19 (5 golden + 14 relative) | DONE |
| **Total** | **5 flags, all OFF** | **15 files** | **71/71 pass** | **GREEN** |

### Gate conditions met:
- All flags OFF — zero behavior change from pre-implementation
- k-values are priors — calibration deferred to soak
- ATR=None → fallback to absolute constants in all modules
- Shadow scoring infrastructure ready (detect_opening_type_cvd shadow dict)
- No order/risk/sizing/polling changes
- Flag activation + k-lock = after ~60-day soak + Michael approval
