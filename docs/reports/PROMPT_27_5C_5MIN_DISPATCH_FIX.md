# P27.5c — 5min Bar Dispatch Fix + P27.5e Partial Bar Topic

**Verdict: GREEN**

## Root Cause

`FiveMinAggregator._on_bar_close_default` (line 184) called:
```python
asyncio.ensure_future(_bar_router.publish("5min", bar_dict))
```

This ran inside a sync call chain originating from a FastAPI sync endpoint handler (threadpool thread). `ensure_future` either:
1. Failed to find a running loop (`RuntimeError`) and was swallowed by the `except` → `logger.debug`, or
2. Attached to a temporary loop that closed immediately.

Result: the `publish("5min", ...)` coroutine was **silently dropped**. All 8 subscribers of the "5min" topic (TPOSystem, FiveMinSystem, WoodiesSystem, FootprintSystem, DayTypeStateMachine, BarLevelDetector, etc.) never received 5-min bar events. `tpo/current` showed `bars_processed_today=0` despite DB having 5+ bars for the day.

The same pattern existed in `_route_bar()` in `bars.py` (used for all bar types from POST endpoints).

## Fix Summary

### Part 1 — Thread-safe publish (`backend/v9/services/bar_router.py`)
- Added `self._main_loop` attribute + `bind_main_loop(loop)` method
- Added `publish_threadsafe(bar_type, bar_data, mode)`:
  - If main loop bound and running: `asyncio.run_coroutine_threadsafe(...)` (durable fire-and-forget)
  - Else: fallback to `threading.Thread` + `asyncio.run` with `logger.warning` (drift signal)

### Part 2 — Bind main loop at startup (`backend/main.py`)
- Added `bar_router.bind_main_loop(asyncio.get_running_loop())` in `_startup()`

### Part 3 — Switch callers to `publish_threadsafe`
- `backend/v9/api/v9/bars.py:_route_bar` — replaced entire `ensure_future` / threading fallback with single `_bar_router.publish_threadsafe(bar_type, bar_data)`
- `backend/v9/services/bar_aggregator_5min.py:_on_bar_close_default` — replaced `asyncio.ensure_future(...)` with `_bar_router.publish_threadsafe("5min", bar_dict)`

### Part 4 — Partial bar (P27.5e) (`backend/v9/services/bar_aggregator_5min.py`)
- Added `self._last_partial_publish_ts` attribute (1 Hz throttle)
- In `on_tick()`, after updating current bar (no close): publishes `"5min.partial"` at ≤1 Hz with `is_partial=True`
- No subscribers registered for `"5min.partial"` yet — opt-in for Phase 6 decision engine

### Part 5 — Regression tests
- `tests/v9/services/test_bar_router_threadsafe.py`: 2 tests (dispatch via main loop, fallback warning)
- `tests/v9/services/test_aggregator_partial_publish.py`: 2 tests (1Hz throttle, bar close dispatch)

## UAT Results — 4 Axes

| Axis | Result | Evidence |
|------|--------|----------|
| Quality | ✅ GREEN | No new errors. `pytest -q` → 7 passed |
| Recency | ✅ GREEN | Endpoint `last_ts` = DB `MAX(ts)` = `2026-05-17 16:15:00` |
| Cardinality | ✅ GREEN | `bars5min?limit=240` → count=240 |
| Latency | ✅ GREEN | live_price: 1.5–3.7ms (p95 < 200ms threshold) |

## Per-Subscriber Proof

Manual test: sent 5 tick_reversal_15 bars crossing two 5-min boundaries.

| Subscriber | bars_processed_today | Status |
|------------|---------------------|--------|
| TPOSystem | 2 | ✅ Confirmed receiving "5min" events |
| FootprintSystem | 15 | ✅ Confirmed (processes tick_reversal_15 + 5min) |
| WoodiesSystem | — | Subscribes to "woodies_5min" (different topic, not affected) |
| FiveMinSystem | ✅ subscribed | Receiving events on app.state instance (note: `/five_min/current` endpoint uses a separate instance — pre-existing routing bug, not P27.5c scope) |
| DayTypeStateMachine | ✅ subscribed to "5min" | No error in dispatch |
| BarLevelDetector | ✅ subscribed to "5min" | No error in dispatch |

## Before / After

| Metric | Before | After |
|--------|--------|-------|
| tpo.bars_processed_today | 0 | 2 (and incrementing on each 5-min close) |
| 5min.partial events per 90s | 0 (topic didn't exist) | Published at 1 Hz during intra-bar ticks |
| BarRouter dispatch p95 | <50ms (from P27.5d) | <50ms (unchanged) |
| Silent dispatch failures | Yes (ensure_future dropped) | No (publish_threadsafe is durable) |

## State After Report

- Bridge: **stopped** (quiet baseline)
- Backend: **running** on port 8000 with fix active
- Frontend: running on port 3000
- DB: 557 rows in v9_bars_5min, MAX(ts) = 2026-05-17 16:15:00

## Known Pre-existing Issues (Not in Scope)

1. `/api/v9/five_min/current` route creates its own `FiveMinSystem()` instance separate from the one registered in BarRouter. Shows `buffer_size=0` even when the registered instance is processing bars. Needs route wiring fix (separate P-ID).
2. WoodiesSystem subscribes to `"woodies_5min"` topic, which comes from `_route_bar("woodies_5min", ...)` in the POST endpoint — this path uses `publish_threadsafe` and works correctly.
