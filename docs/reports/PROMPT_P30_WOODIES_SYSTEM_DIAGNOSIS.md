# P30 Diagnosis: WoodiesSystem.process_bar 10s Slow Handler

**Status:** ROOT CAUSE IDENTIFIED  
**Date:** 2026-05-20  
**Investigator:** Claude Code (CC)

---

## 1. Symptom

BarRouter logs 10-12s per 5-min bar for `WoodiesSystem.process_bar`:

```
BarRouter: SLOW handler WoodiesSystem.process_bar took 12241.7ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10054.1ms
... (repeats every bar)
```

Cockpit probes to `/api/v9/trades/recent`, `/tpo/current`, `/cumulative_delta/current`
all timeout while process_bar is running. Frontend feels disconnected.

## 2. Timing Distribution (23 SLOW entries)

| Bucket       | Count | Values (ms)                                |
|-------------|-------|--------------------------------------------|
| 100-200ms   | 9     | 107, 112, 116, 116, 149, 151, 179, 185, 202 |
| 400-500ms   | 1     | 461                                         |
| 2000ms      | 1     | 2070                                        |
| 8500-9500ms | 2     | 8586, 9204                                  |
| 10000-10700ms | 8   | 10041, 10053, 10054, 10062, 10159, 10224, 10230, 10299 |
| 12000ms+    | 1     | 12242                                       |

**Bimodal distribution:** ~100-200ms (fast path, no deadlock) vs ~10000ms (deadlock path).
The 10s cluster = 5 endpoints x 2s HTTP timeout. The 8.5-9.2s entries = 4-5 endpoints
where one or two responded before the event loop stalled.

## 3. Root Cause

**File:** `backend/v9/systems/woodies/decision_tree.py`  
**Function:** `_load_touchpoints()` (lines 182-204)  
**Called from:** `_a4_touchpoints()` -> `WoodiesDecisionTree.evaluate_bar()` -> `process_bar()`

### The self-deadlock

`_load_touchpoints` makes **5 synchronous `requests.get()` calls** to the same
uvicorn process (localhost:8000) from inside `async def process_bar()`:

```python
TOUCHPOINT_ENDPOINTS = {
    "day_type": "http://localhost:8000/api/v9/day_type/v9/current",
    "tpo":      "http://localhost:8000/api/v9/tpo/current",
    "veto":     "http://localhost:8000/api/v9/veto/state",
    "killzone": "http://localhost:8000/api/v9/killzone/current",
    "layer0":   "http://localhost:8000/api/v9/layer0/state",
}

for name, url in TOUCHPOINT_ENDPOINTS.items():
    resp = requests.get(url, timeout=2)    # <-- BLOCKS EVENT LOOP
```

Since uvicorn runs a **single worker** (`python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`, no `--workers` flag), the event loop is single-threaded.

**Deadlock sequence:**
1. BarRouter dispatches `process_bar()` on the event loop.
2. `process_bar` reaches `_a4_touchpoints` -> `_load_touchpoints`.
3. `requests.get("http://localhost:8000/api/v9/day_type/...")` blocks the event loop thread.
4. The same uvicorn process needs to serve the response, but the event loop is blocked.
5. `requests.get` waits for a response that can never arrive -> **times out after 2s**.
6. Repeat for endpoints 2-5: 5 x 2s = **10 seconds**.

### Why some bars are fast (100-200ms)

When `ctx.patterns` is empty, `_a4_touchpoints()` returns `SKIP` at line 147 without
calling `_load_touchpoints`. No HTTP calls = no deadlock. The fast bars had no pattern
detections that bar.

For the few 100-200ms bars WITH patterns: the touchpoint endpoints are sync `def` (not
`async def`) in FastAPI, which runs them in a threadpool. If threads were already in-flight
when the event loop blocked, their responses could drain through the kernel's TCP buffer
before the timeout, racing against the deadlock.

## 4. Stage-by-Stage Timing Breakdown (estimated)

| Stage | Code Location | Est. Time | Notes |
|-------|-------------|-----------|-------|
| Parse bar data | woodies_system.py:139-145 | <1ms | Dict access |
| Buffer append + trim | woodies_system.py:148-156 | <1ms | List ops |
| `compute_all_studies()` | cci_calc.py:136-178 | ~2ms | 50-bar buffer, pure math |
| Build WoodiesBar | woodies_system.py:169-173 | <1ms | Dataclass init |
| `detect_all_patterns()` | pattern_engine.py:37-59 | ~5ms | 9 detectors on 50 bars |
| `detect_direction_change()` | direction_change_detector.py:65-74 | <1ms | 2-bar comparison |
| Pattern classification | woodies_system.py:189-208 | <1ms | Comparisons |
| **A4 `_load_touchpoints()`** | **decision_tree.py:186-204** | **~10,000ms** | **5 x 2s self-deadlock** |
| Other A-stages | decision_tree.py | ~1ms | Pure logic |
| State update | woodies_system.py:237-268 | <1ms | Dict update |
| `_persist_bar` | woodies_system.py:324-346 | ~5ms | SQLite INSERT |
| `_persist_pattern` (per pat) | woodies_system.py:348-386 | ~5ms | SQLite INSERT |

**Total without A4:** ~15-20ms  
**Total with A4 deadlock:** ~10,015-10,020ms

## 5. Recommended Fix (smallest correct change)

### Option A: Pass pre-cached touchpoints (RECOMMENDED)

In `woodies_system.py:process_bar()`, pass `touchpoints={}` to the
`WoodiesDecisionContext` constructor:

```python
dt_ctx = WoodiesDecisionContext(
    bars=list(self._bar_buffer),
    studies=studies,
    patterns=patterns,
    classification=classification,
    direction=direction,
    sizing=sizing,
    current_state=self.current_state,
    fire_setup=fire_setup,
    touchpoints={},  # <-- ADD THIS: skip HTTP self-calls
)
```

This makes `_load_touchpoints` return an empty dict with all 5 endpoints reported
as "missing". Stage A4 still PASS (degraded), preserving decision-tree integrity.
Touch-point advisory context is lost but was already unreliable due to the deadlock.

**Impact:** 1-line change. process_bar drops from ~10s to ~20ms. No signal accuracy
risk since touchpoints are advisory only (they never block routing).

### Option B: Async touchpoint fetch (future improvement)

Replace `requests.get` with `await httpx.AsyncClient.get()` in `_load_touchpoints`
(making it async). Requires changing the call chain through `_a4_touchpoints` and
`evaluate_bar`. Correct but larger blast radius.

### Option C: Background cache

Run a periodic task that fetches touchpoints every 5s and caches them. Pass the cached
dict into `WoodiesDecisionContext`. Best long-term solution but more code.

## 6. Safety Assessment

- **Signal accuracy risk:** NONE. Touchpoints (A4) are advisory context only. They
  never block or modify pattern detection, sizing, or routing decisions. The decision
  tree already handles degraded/missing touchpoints gracefully (PASS with advisories).
- **Pre-LIVE safety:** SAFE. Option A actually improves pre-LIVE reliability by
  eliminating the 10s event loop blockage that causes cockpit timeouts.
- **Regression risk:** LOW. The only change is that `dt_summary["pre_fire"]` stage A4
  will report `"touch-point advisory context degraded: ..."` instead of actual data.
  This is already the fallback path for when endpoints are unavailable.

## 7. Suggested Regression Test

**Path:** `tests/v9/systems/test_woodies/test_process_bar_latency.py`

```python
import time
import pytest

@pytest.mark.asyncio
async def test_process_bar_completes_under_500ms(woodies_system_hydrated):
    """P30 regression: process_bar must not self-deadlock on touchpoint HTTP."""
    system = woodies_system_hydrated  # fixture with 50 hydrated bars
    bar = {"ts": time.time(), "o": 5500, "h": 5510, "l": 5490, "c": 5505, "v": 100}

    t0 = time.perf_counter()
    await system.process_bar(bar)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 500, f"process_bar took {elapsed_ms:.0f}ms, expected < 500ms"
```

**Assertion:** `process_bar` must complete in < 500ms for a 50-bar buffer.

## 8. Cross-check: /api/v9/woodies/signals endpoint

The cockpit polls `/api/v9/woodies/signals` ~3-5x/sec. This endpoint
(`backend/v9/systems/woodies/api.py:50`) is a sync `def` that queries
`v9_system_signals` via SQLAlchemy. It does NOT share computation with
`process_bar` and does NOT need caching. However, during the 10s deadlock,
these requests queue up and timeout, causing the cockpit disconnect symptom.
Fixing the deadlock fixes this too.

---

**Conclusion:** Single-line fix (Option A) eliminates the 10s self-deadlock.
No risk to signal accuracy. Safe for pre-LIVE.
