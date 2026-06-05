# VERIFY RELATIVE · 2026-06-05

## 1. SCOPE
**Commit:** `a607d11` — enable ATR-relative mode (default ON) + wire double_bt.
**This VERIFY:** confirms the change is **live in the running server** (not just committed).

## 2. CHANGES
Already committed in `a607d11`. Test files added by Cowork (uncommitted → committed here).

## 3. EVIDENCE

### 1b-i: Process env
```
$ ps eww -p 25435 | tr ' ' '\n' | grep S2_ATR_RELATIVE
S2_ATR_RELATIVE=true
```

### 1b-ii: Import returns True
```
$ S2_ATR_RELATIVE=1 python3 -c "from backend.v9.shared.atr import S2_ATR_RELATIVE; print(S2_ATR_RELATIVE)"
True
```

### 1b-iii: Tolerance is ATR-relative
```
$ python3 -c "from backend.v9.systems.five_min.patterns.double_bt import get_trough_tolerance; ..."
  get_trough_tolerance(atr_5m=None) = 0.50 (hardcoded fallback)
  get_trough_tolerance(atr_5m=3.0) = 2.25 (0.75 × 3.0)
  get_trough_tolerance(atr_5m=4.0) = 3.00 (0.75 × 4.0)
  get_trough_tolerance(atr_5m=5.0) = 3.75 (0.75 × 5.0)
```
Note: computed-not-fired (no double-bottom setup active). Values are ATR-relative, not 0.50.

## 4. TESTS

### test_atr.py (6 passed)
```
tests/v9/test_atr.py::test_returns_none_below_period PASSED
tests/v9/test_atr.py::test_returns_value_at_exactly_period PASSED
tests/v9/test_atr.py::test_constant_range_equals_range PASSED
tests/v9/test_atr.py::test_daily_same_as_5min_algorithm PASSED
tests/v9/test_atr.py::test_wilder_smoothing_applied PASSED
tests/v9/test_atr.py::test_flag_defaults PASSED
6 passed
```
**Litmus:** `test_flag_defaults` — if reverted (remove `default=True` from `flag()` call at atr.py:101) → `S2_ATR_RELATIVE` becomes `False` → RED.

### test_double_bt_relative.py (3 passed)
```
tests/v9/regression/test_double_bt_relative.py::test_flag_on_relative_tolerance PASSED
tests/v9/regression/test_double_bt_relative.py::test_flag_on_no_atr_falls_back PASSED
tests/v9/regression/test_double_bt_relative.py::test_flag_off_fixed_tolerance PASSED
3 passed
```
**Litmus:** `test_flag_on_relative_tolerance` — if reverted (hardcode `tolerance = TICK_SIZE * 2` in double_bt.py) → tolerance=0.50 instead of 0.75×ATR → RED.

### test_double_bt.py backward compat (26 passed)
```
26 passed — all existing double_bt tests green
```
`atr_5m=None` default preserves original behavior (tolerance=0.50).

### Pre-existing failure (not ours)
```
FAILED test_bear_flag_skipped_on_first_hour_mode — pre-existing, unrelated to relative mode
```

## 5. RUNTIME

### Server healthy with flag
```
$ curl -s localhost:8000/api/v9/health
{"status":"ok","version":"v9.0.0"}
```

### Backend PID with S2_ATR_RELATIVE
```
Backend PID: 25435
S2_ATR_RELATIVE=true (in process env)
```

## 6. NOT-DONE

| Item | Why |
|------|-----|
| K calibration (_TROUGH_TOL_ATR_K=0.75) | Needs soak ground-truth. K is the prior, not calibrated. |
| ATR_MULTIPLIERS for stop (atr_caps.py) | Not in scope — separate calibration |
| Live double-bottom fire | No double-bottom setup detected today (trend-down day). Tolerance verified via computed values only. |

## 7. CONFIG VALUES

| Parameter | Value | Status |
|-----------|-------|--------|
| S2_ATR_RELATIVE | True (default) | Michael approved for SHADOW |
| _TROUGH_TOL_ATR_K | 0.75 | Prior — not calibrated |
| Can disable: `S2_ATR_RELATIVE=0` | Reverts to TICK_SIZE*2=0.50 | Safety valve |
