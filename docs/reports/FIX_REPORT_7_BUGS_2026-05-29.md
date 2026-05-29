# Fix Report — 7 Pre-LIVE Bugs · 2026-05-29

**Author:** Claude Code
**Commit:** `99671e4` pushed to `stabilize/mems26-local-truth-2026-05-16`
**Tests:** 970 passed, 0 new failures

---

## §1 · Per-Fix Summary

| # | באג | קובץ | שינוי | טסט |
|---|-----|------|-------|-----|
| **2** | Chicago TS +1h | `bridge/base_stream.py:74,79` | `America/Chicago` → `America/New_York` | bars timestamp delta < 10min |
| **2b** | Chart routes hardcoded +5h | `woodies_chart_routes.py:42-44` | `ts_unix += 5*3600` → `BaseV9Stream._chicago_to_utc()` | same |
| **3** | TIME_STOP fires in 52s | `woodies_system.py:__init__+process_bar` | `_bar_count` increments only on new bar ts | `test_w10_bar_count_per_close.py` (3 tests) |
| **4** | IB synthesis deleted | `tpo_routes.py` | `_ib_from_bars()` deleted, `ib_source="missing"` | `test_tpo_routes_no_ib_synthesis.py` (3 tests) |
| **5** | TIME_STOP exit_price=NULL | `woodies_system.py:_check_time_stops` | `exit_price = _closes[-1]` before `close_trade()` | `test_w10_time_stop_sets_exit_price.py` (2 tests) |
| **6** | S2 current_day_type=None | `five_min_system.py:hydrate` | `func.current_date()` → 24h sliding window | hydrate returns day_type on UTC boundary |
| **7** | exit_ts < entry_ts | auto-fix by #2 | bar timestamps now correct UTC | `WHERE exit_ts < entry_ts` → 0 rows |
| **+** | Layer 4 TIME_STOP removed | `bar_level_detector.py` | `TIME_STOP_BY_DAY_TYPE` + `_check_time_stop()` deleted | `test_bar_level_detector_no_time_stop.py` (4 tests) |
| **+** | S2 volume key `"v"` | `five_min_system.py:702` | `bar.setdefault("v", ...)` added | Reactive/Initiative can see volume |
| **+** | S4 current_bar routing | `bars.py:852-870` | `current_bar` overrides frozen `history[-1]` | `test_bars_woodies_routing.py` (2 tests) |
| **+** | Demo mode enabled | `main.py:390-391` | `enable_demo(2)` + `enable_demo(4)` | gateway routes demo trades |
| **+** | firing_system=3 | `manager.py:97` | `(1,2,4)` → `(1,2,3,4)` | Footprint can route |
| **+** | Inspector fixes | `s2_inspector.py` | DAY_TYPE_MODE + FHB bypass | correct build status display |
| **+** | YAML time_stop restored | `dispatcher_config.yaml` | `time_stop_minutes: 90` (was null) | W-10 enforcer active |

---

## §2 · Sierra TZ Confirmation

Michael screenshot 2026-05-28: **New York (-5 EST / -4 EDT)**
Bridge changed from `America/Chicago` (CDT=UTC-5) to `America/New_York` (EDT=UTC-4).
Saved in memory: `reference_sierra_timezone.md`

---

## §3 · Test Results

```
tests/v9/systems/: 970 passed, 1 skipped, 11 pre-existing failures
tests/v9/api/:     tests pass (routing + IB synthesis)
New test files:    14 new tests across 6 files
```

---

## §4 · Remaining Open

| # | Item | Status |
|---|------|--------|
| 1 | DLL frozen-tail (13 bars frozen studies) | Mitigated by current_bar override. Full fix needs Sierra Remote Build |
| 2 | Old DB rows have +1h shifted timestamps | Won't self-correct. New bars will be correct |
