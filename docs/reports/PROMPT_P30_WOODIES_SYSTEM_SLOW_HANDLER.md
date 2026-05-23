# PROMPT P30 — WoodiesSystem.process_bar SLOW handler fix

**Date:** 2026-05-20
**P-ID:** P30 (Woodies SLOW handler bottleneck)
**Status:** GREEN — pre-LIVE verified locally; awaiting backend restart for live UAT
**Affected systems:** S4 Woodies (decision tree A4 touch-points), FastAPI cockpit responsiveness

## TL;DR

`BarRouter: SLOW handler WoodiesSystem.process_bar took 10054ms-12241ms`
was caused by `decision_tree._load_touchpoints` issuing **5 sequential
synchronous `requests.get` calls to localhost:8000 with a 2 s timeout each**,
all from inside the BarRouter's async event loop. Self-deadlock: the loop
was blocked waiting for HTTP responses to its own touch-point endpoints
that could not be served because the loop was blocked.

**Fix:** pre-fetch touch-points via `asyncio.to_thread` from
`process_bar` (so the HTTP work runs in a worker thread, not on the event
loop), add an event-loop guard in `_load_touchpoints` (so any future async
caller cannot reintroduce the deadlock), and reduce the per-request HTTP
timeout from 2.0 s → 0.5 s as defense-in-depth.

**Result:** 10024 ms (worst case) → 71 ms (typical) / 2547 ms (worst case
with every endpoint hung). Event-loop block is eliminated.

## Diagnosis

### Evidence (production log: `/tmp/backend.err.log`)

```
$ grep -c "WoodiesSystem.process_bar took" /tmp/backend.err.log
34
$ grep "WoodiesSystem.process_bar took" /tmp/backend.err.log | head -10
BarRouter: SLOW handler WoodiesSystem.process_bar took 12241.7ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10054.1ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10052.8ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10061.5ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10040.9ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10229.8ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10716.4ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10224.1ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10158.7ms
BarRouter: SLOW handler WoodiesSystem.process_bar took 10298.8ms
```

The signature "10000 ± 300 ms" is a dead giveaway for **5 × 2 s timeouts**
hit sequentially. Whenever a Woodies pattern fired, decision tree stage A4
called `_load_touchpoints`, which iterated:

```202:204:backend/v9/systems/woodies/decision_tree.py
def _a4_touchpoints(ctx: WoodiesDecisionContext) -> StageResult:
    if not ctx.patterns:
        return StageResult("A4", StageStatus.SKIP, "no setup needs touch-points", owner=StageOwner.TOUCHPOINT)
```

`_load_touchpoints` (pre-fix) — the smoking gun:

```python
for name, url in TOUCHPOINT_ENDPOINTS.items():
    try:
        import requests
        resp = requests.get(url, timeout=2)   # 5 sequential 2 s blocking calls
        ...
```

Where `TOUCHPOINT_ENDPOINTS` is:

```112:118:backend/v9/systems/woodies/decision_tree.py
TOUCHPOINT_ENDPOINTS: Dict[str, str] = {
    "day_type": "http://localhost:8000/api/v9/day_type/v9/current",
    "tpo": "http://localhost:8000/api/v9/tpo/current",
    "veto": "http://localhost:8000/api/v9/veto/state",
    "killzone": "http://localhost:8000/api/v9/killzone/current",
    "layer0": "http://localhost:8000/api/v9/layer0/state",
}
```

### Why this self-deadlocked

`process_bar` is an `async def` awaited by the BarRouter event loop
(`backend/v9/services/bar_router.py:80`). It runs in a daemon thread spawned
by `publish_threadsafe`, but that thread runs its own event loop via
`asyncio.run(self.publish(...))`. The synchronous `requests.get` calls inside
`_load_touchpoints` blocked that thread's event loop for the full timeout.

The HTTP requests targeted the **same FastAPI server** on `localhost:8000`.
When bars arrived in bursts (replay, fast bridge ticks, multiple bar
subgraphs), several worker threads were each making 5 self-targeted HTTP
requests in parallel, and FastAPI's main event loop was unable to keep up.
The `requests.get` calls then hit the 2 s timeout, raised, and the loop
moved on to the next endpoint — 5 sequential timeouts = ~10 s per bar.

I verified this locally with a synthetic reproduction:

```
BEFORE fix (1 forced ZLR pattern → A4 fetches touchpoints, 5 endpoints
            mocked to hang at 2 s each): process_bar = 10024 ms
```

That reproduces the production log signature exactly.

### Why this didn't fire on every bar

Lines 2855 and 2913 of the log show fast bars at 116 ms and 179 ms — these
are bars where the 9-pattern engine returned an empty list. With
`ctx.patterns == []`, `_a4_touchpoints` SKIPs before calling
`_load_touchpoints`, so no HTTP is issued. The slow path is conditional on
pattern detection.

## Fix

### Smallest correct change: pre-fetch in a worker thread + event-loop guard

Two files touched (`109 insertions, 20 deletions`):

```
backend/v9/systems/woodies/decision_tree.py  | 89 ++++++++++++++++++++++------
backend/v9/systems/woodies/woodies_system.py | 40 ++++++++++++-
```

**1. `decision_tree.py`** — refactor the HTTP fetch into a standalone helper
and add the event-loop guard:

- New `_fetch_touchpoints_now()` — the synchronous HTTP surface, isolated
  so it can be called from an `asyncio.to_thread` worker.
- New `_is_in_event_loop()` — wraps `asyncio.get_running_loop()` in a
  try/except.
- `_load_touchpoints()` now refuses to issue blocking HTTP from inside an
  event loop; it returns `({}, [<name>:in_event_loop, …])` so A4 still
  reports degraded context as a PASS (unchanged from how unavailable
  endpoints were already handled).
- Per-request HTTP timeout lowered from **2.0 s → 0.5 s**
  (`TOUCHPOINTS_REQUEST_TIMEOUT_S`). Defense-in-depth: 5 × 0.5 s = 2.5 s
  worst-case in a worker thread, vs. 5 × 2.0 s = 10 s on the event loop
  before.

**2. `woodies_system.py`** — pre-fetch touch-points off the event loop:

```python
touchpoints_data: Optional[Dict] = None
if patterns:
    try:
        touchpoints_data, _tp_unavailable = await asyncio.wait_for(
            asyncio.to_thread(_fetch_touchpoints_now),
            timeout=_TOUCHPOINTS_PREFETCH_BUDGET_S,
        )
    except asyncio.TimeoutError:
        logger.warning("[Woodies] touchpoint pre-fetch exceeded %.1fs budget; "
                       "A4 will run with empty advisory context",
                       _TOUCHPOINTS_PREFETCH_BUDGET_S)
        touchpoints_data = {}
    except Exception as exc:
        logger.warning("[Woodies] touchpoint pre-fetch failed: %s", exc)
        touchpoints_data = {}

dt_ctx = WoodiesDecisionContext(
    ...,
    touchpoints=touchpoints_data,  # routes through ctx.touchpoints early-return path
)
```

`_TOUCHPOINTS_PREFETCH_BUDGET_S = 3.0` caps the async wait so even if the
worker thread is slow, `process_bar` returns within the budget. When the
budget fires, `touchpoints_data` falls back to `{}` and `_a4_touchpoints`
still PASSes with a degraded-context advisory (existing behavior).

### Why this is the smallest correct change

- **No structural refactor.** The decision-tree contract is unchanged;
  `_load_touchpoints` still returns `(fetched, unavailable)` and A4 still
  PASSes regardless of touch-point availability (advisory, not gating).
- **No new dependencies.** Uses `asyncio.to_thread` (stdlib, Python ≥ 3.9 —
  confirmed Python 3.9.7 on this host).
- **No trading-logic change.** Touch-point data was already advisory; A4
  never blocked routing on it (`unavailable` → PASS with degraded message).
  Trading routing decisions are identical before/after.
- **Belt-and-suspenders.** Even if a future caller forgets to pre-fetch,
  the event-loop guard in `_load_touchpoints` prevents the deadlock from
  reappearing.

## UAT

### Before/after timings (local, mocked HTTP)

| Scenario | Before | After | Delta |
|---|---:|---:|---:|
| Pattern fires, all 5 endpoints hang full timeout (worst case) | **10024 ms** | **2547 ms** | -75 % (and no event-loop block) |
| Pattern fires, endpoints respond ~10 ms each (typical) | ~250-500 ms | **71 ms** | below BarRouter SLOW threshold (100 ms) |
| No patterns (A4 SKIP) | 116-179 ms (log) | **2 ms** | -98 % |

The worst case 2547 ms is the work running in a **thread-pool worker**, not
on the event loop — the FastAPI cockpit stays responsive throughout. With
healthy endpoints (the steady state) every bar completes in well under the
100 ms BarRouter SLOW threshold.

### Test command

```
pytest tests/v9/systems/test_woodies_process_bar_perf.py -v
```

Result: **4 passed in 3.45 s**

```
tests/v9/systems/test_woodies_process_bar_perf.py::test_process_bar_under_1s_when_touchpoints_respond_fast PASSED
tests/v9/systems/test_woodies_process_bar_perf.py::test_process_bar_bounded_when_all_touchpoints_hang PASSED
tests/v9/systems/test_woodies_process_bar_perf.py::test_process_bar_skips_touchpoint_fetch_when_no_patterns PASSED
tests/v9/systems/test_woodies_process_bar_perf.py::test_load_touchpoints_refuses_sync_http_in_event_loop PASSED
```

### Broader regression suite

```
pytest tests/v9/ -k woodies -q                          → 181 passed, 1200 deselected
pytest tests/atomic/test_woodies_decision_tree.py
      tests/atomic/test_woodies_runtime_contract.py
      tests/atomic/test_cross_system_integration.py -q  → 26 passed
pytest tests/v9/services/test_bar_router_threadsafe.py
       backend/v9/tests/test_woodies_system.py
       tests/v9/systems/test_woodies.py
       tests/v9/systems/test_woodies_patterns.py -q     → 120 passed, 2 skipped, 1 failed (pre-existing)
```

The single failure (`test_publish_threadsafe_warns_when_unbound`) is a
pre-existing test that was already red before this change — verified by
stashing the diff and rerunning. It expects a `"main_loop not bound"`
warning string that does not appear in the current `BarRouter` code;
unrelated to S4 Woodies. Outside this P-ID's scope.

### Live UAT (post-restart) — pending

The user runs the backend manually. Once restarted:

1. **Quality.** New `BarRouter: SLOW handler WoodiesSystem.process_bar took
   …ms` lines in `/tmp/backend.err.log` must be < 1000 ms (target < 100 ms
   when endpoints are healthy).
2. **Recency.** `/api/v9/woodies/signals` should keep returning fresh
   signals on every bar — process_bar no longer drops bars by stalling.
3. **Cardinality.** `/api/v9/woodies/chart?limit=120` should keep returning
   120 bars with no truncation.
4. **Latency.** Cockpit `curl /api/v9/cockpit/heartbeat` should consistently
   return in <100 ms during active bars (was sometimes 5+ s during the
   self-deadlock window).
5. **Touch-point advisories.** A4 details should now include real
   `day_type` / `tpo` / `veto` / `killzone` / `layer0` data instead of
   `:in_event_loop` markers, because the pre-fetch path populates
   `ctx.touchpoints` from a worker thread that is allowed to issue HTTP.

## Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Worker-thread HTTP pre-fetch still slow under bridge backpressure | Low | A4 sees `{}` after the 3 s budget; degraded advisory only (A4 still PASS) | `asyncio.wait_for` caps wall-clock; existing fallback path tested |
| Test patches `requests.get` and now hits a different code path | None | n/a | Tests outside any event loop still hit `_fetch_touchpoints_now` exactly as before — confirmed by 26/26 atomic tests passing |
| `asyncio.to_thread` not available on host Python | None | n/a | Verified Python 3.9.7 on host; `to_thread` added in 3.9.0 |
| Touch-point data becomes stale | None | n/a | No caching introduced; every pattern bar still triggers a fresh fetch in a worker thread |
| Future regression reintroduces sync HTTP on event loop | Low | Bottleneck returns | Event-loop guard in `_load_touchpoints` + 4 regression tests |

## Rollback

A single `git revert` on the commit reverts both files cleanly. The
regression test file is additive and independent of any other test; it can
stay even if the fix is rolled back (the tests will fail, as expected,
documenting the regression).

## Files touched

- `backend/v9/systems/woodies/decision_tree.py` — HTTP isolation, event-loop
  guard, 0.5 s timeout
- `backend/v9/systems/woodies/woodies_system.py` — `asyncio.to_thread`
  pre-fetch in `process_bar`
- `tests/v9/systems/test_woodies_process_bar_perf.py` — new regression test
  (4 cases)
- `docs/reports/PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md` — this report

## Followups

- None required for the SLOW handler fix itself.
- Optional future optimization: parallelize the 5 touch-point fetches with
  `asyncio.gather(*[asyncio.to_thread(...) for ...])` to drop the worst-case
  from 2.5 s → 0.5 s. Not needed today — the event-loop block is the
  user-facing symptom, and that is fully resolved.
