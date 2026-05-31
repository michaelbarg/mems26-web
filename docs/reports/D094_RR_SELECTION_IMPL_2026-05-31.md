# D-094: R:R Fire Selection — Implementation Report

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Commit:** `612a665`  
**Flag:** `RR_FIRE_SELECTION=False` (OFF)  
**Decision:** D-094 LOCKED (Michael 31/5) — Option A pure R:R, same-bar flush

---

## D1 · Bar-Close Hook

**Finding:** `BarRouter` dispatches to subscribers on each new bar. Gateway can subscribe to "5min" channel — new bar arrival = previous bar closed → flush buffer.

**Wiring (in main.py, to be added when flag activated):**
```python
bar_router.subscribe("5min", trading_gateway.on_bar_close)
```

Currently the `on_bar_close` method exists but is NOT wired in main.py (flag is OFF, method is a no-op when flag off). Wiring will be added when flag is activated for SHADOW testing.

---

## D2 · `compute_rr_score(setup) -> float`

**File:** `backend/v9/gateway/rr_score.py`

```python
R:R = Σ(|target_i - entry| × split_pct_i) / |entry - stop|
```

- Uses `contract_split.get_contract_split(classification)` for split percentages
- Unknown patterns → equal split across non-zero targets
- Returns `None` for invalid inputs (entry==stop, no targets)

---

## D3 · Gateway Buffering

**File:** `backend/v9/gateway/trading_gateway.py`

### Flag OFF (default): Unchanged

```python
# Original first-wins logic (flag OFF)
if self._is_demo_enabled(system_id):
    if self.demo_slot is None:
        demo_trade = self._execute_demo(...)
```

### Flag ON: Buffer + Flush

```python
# D-094: Buffer candidate (slot NOT filled yet)
self._slot_candidates.append(candidate)

# on_bar_close(): Select winner
scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)  # R:R, conf, -sys_id
winner fills slot; losers logged "OUTRANKED"
```

---

## D4 · Invariants Preserved

| Invariant | Status |
|-----------|--------|
| 5 risk gates run before buffering | PRESERVED (lines 88-121 unchanged) |
| SHADOW always records immediately | PRESERVED (line 110, before buffer logic) |
| Cluster guard blocks DEMO/LIVE only | PRESERVED |
| Single slot per mode | PRESERVED (winner fills, rest outranked) |
| Flag OFF = identical behavior | VERIFIED (golden tests pass) |

---

## D5 · Test Output (raw)

### Flag OFF = identical (golden):

```
tests/v9/gateway/test_rr_selection.py::TestFlagOff::test_demo_first_wins PASSED
tests/v9/gateway/test_rr_selection.py::TestFlagOff::test_shadow_always_records PASSED
tests/v9/gateway/test_rr_selection.py::TestFlagOn::test_no_flush_when_flag_off PASSED
```

### Flag ON (R:R selection):

```
tests/v9/gateway/test_rr_selection.py::TestFlagOn::test_candidates_buffered_not_filled_immediately PASSED
tests/v9/gateway/test_rr_selection.py::TestFlagOn::test_bar_close_selects_highest_rr PASSED
tests/v9/gateway/test_rr_selection.py::TestFlagOn::test_shadow_unaffected_by_buffering PASSED
tests/v9/gateway/test_rr_selection.py::TestFlagOn::test_losers_logged_as_outranked PASSED
tests/v9/gateway/test_rr_selection.py::TestFlagOn::test_tie_break_confidence_then_system PASSED
```

### R:R score unit tests:

```
tests/v9/gateway/test_rr_selection.py::TestComputeRRScore::test_long_ofa_reactive PASSED (R:R=4.0)
tests/v9/gateway/test_rr_selection.py::TestComputeRRScore::test_short_flag PASSED (R:R=3.0)
tests/v9/gateway/test_rr_selection.py::TestComputeRRScore::test_entry_equals_stop_returns_none PASSED
tests/v9/gateway/test_rr_selection.py::TestComputeRRScore::test_unknown_pattern_equal_split PASSED
tests/v9/gateway/test_rr_selection.py::TestComputeRRScore::test_missing_prices_returns_none PASSED
```

### Full suite:

```
2548 passed, 10 skipped, 0 failed (34.47s)
```

---

## Activation Checklist (when Michael approves)

1. Set `export RR_FIRE_SELECTION=true` in environment
2. Wire in main.py: `bar_router.subscribe("5min", trading_gateway.on_bar_close)`
3. Monitor logs for "D-094 WINNER" and "D-094 OUTRANKED" entries
4. Compare SHADOW trades: R:R of selected vs outranked for soak validation
