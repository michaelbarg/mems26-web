# P30.4 — Frontend Polling / Backend Responsiveness

**Date:** 2026-05-18
**Status:** PARTIAL GREEN — chart/live data latency fixed; `/api/v9/status` remains diagnostic-only residual
**No SHADOW/DEMO/LIVE enabled. No bridge started. No trade_command writes.**

---

## Root Cause

Under frontend load, backend endpoints exhibited high latency (2-4s) due to:

1. **`ChartV5b` polled `/api/v9/live_price` every 1s** via HTTP fetch, despite a
   WebSocket price stream (`/ws/v9/price` → `priceStore`) already delivering
   real-time ticks. This added 1 req/sec of unnecessary HTTP load.

2. **`TopBar` polled `/api/v9/day_type/v9/current` every 10s** separately from
   `systemStateStore.fetchAllStates()` which already polls the same endpoint
   every 2s. Duplicate requests.

3. **`systemStateStore.fetchAllStates()` had no in-flight guard** — if the
   backend took >2s to respond (common under load), the next 2s interval would
   fire a second concurrent batch before the first completed, creating
   request amplification.

4. **`TopBar` status polling had no in-flight guard** — same overlap issue.

## Fix (4 changes, 3 files)

| File | Change |
|------|--------|
| `ChartV5b.tsx` | Replaced 1s `/api/v9/live_price` poll with `usePriceStore.subscribe()`. Chart forming bar now updates from the WebSocket price stream. |
| `TopBar.tsx` | Removed separate 10s `day_type/v9/current` poll. TopBar now reads from `systemStateStore` (already polled by `useSystemStatePolling`). Added in-flight guard to status polling. |
| `systemStateStore.ts` | Added `_fetchInFlight` guard — `fetchAllStates()` skips if previous call hasn't returned yet. Prevents overlapping request batches. |
| `five_min_system.py` | Replaced incorrect `backend/data/mems26_local.db` path calculation with `SessionLocal` + `V9Bar5Min`, eliminating repeated `DB bar replay failed` warnings. |
| `app.py`, `bars_5min_history.py` | Changed cheap health/chart routes to `async def` so they do not queue behind saturated sync threadpool work. |

Post-review hardening:

- `_fetchInFlight` is now released in `finally`, so an unexpected exception
  cannot permanently disable system-state polling until page refresh.
- `systemStateStore.ts` now passes targeted ESLint after replacing the local
  `raw` type from `any` to `unknown`.

## Tests

Backend (no regressions):
```
python3 -m pytest tests/v9/ -q → 1288 passed, 1 skipped
python3 -m pytest tests/v9/api/test_status_endpoint_budget.py tests/v9/api/test_chart_bars5min_integrity.py tests/test_five_min_system.py tests/v9/api/test_five_min_routes.py -q → 23 passed
```

Frontend lint (changed files only):
```
npx eslint ChartV5b.tsx systemStateStore.ts TopBar.tsx
→ 17 errors in ChartV5b.tsx (pre-existing @typescript-eslint/no-explicit-any)
npx eslint systemStateStore.ts
→ PASS
```

## Live Latency (with frontend open)

### Before P30.4 (from P30.3 report)
```
/api/v9/health:     3765ms, 79ms, 59ms
/api/v9/status:     4468ms, 4420ms, 2504ms
/api/v9/live_price: 2017ms, 1953ms, 2044ms
/api/v9/bars5min:   not measured under load
```

### After P30.4
```
/api/v9/health:     2ms, 2ms, 7ms (occasional spike to 3s during GIL contention)
/api/v9/status:     917ms, 920ms, 918ms (capped by STATUS_ENDPOINT_BUDGET_S=0.9)
/api/v9/live_price: 2ms, 2ms, 2ms (was 2000ms — eliminated HTTP polling)
/api/v9/bars5min:   15ms, 15ms, 14ms
```

### Post-Review Final Verification
After closing duplicate MEMS26 browser tabs and fixing FiveMin DB replay +
threadpool queueing for cheap routes:

```text
/api/v9/health:     1465ms first sample after reload, then 3ms, 3ms
/api/v9/live_price: 5ms, 3ms, 4ms
/api/v9/bars5min:   21ms, 33ms, 38ms
```

`/api/v9/status` still showed intermittent slow/timeout behavior when directly
probed repeatedly. Treat it as a diagnostic endpoint until a dedicated lightweight
UI heartbeat endpoint exists.

## Bars5min 4-Axis UAT

| Axis | Threshold | Actual | Result |
|------|-----------|--------|--------|
| Quality | bad_count=0 | 0 | PASS |
| Recency | Latest bar timestamp | 2026-05-17 16:15:00 | PASS |
| Cardinality | count=240 | 240 | PASS |
| Latency | <100ms | 13ms | PASS |

Post-review final latency samples: `20.55ms`, `33.11ms`, `37.60ms`.

## Residual Notes

- `/api/v9/status` remains too heavy for repeated UI/probe usage. It is now a
  diagnostic endpoint, not the GREEN criterion for chart/live data readiness.
- Occasional GIL contention spikes (2-3s on health) happen when many system-state
  requests arrive simultaneously. The in-flight guard prevents amplification but cannot
  eliminate single-threaded Python contention.
- The `systemStateStore` still makes 12 sequential fetches every 2s. A future improvement
  could batch these into a single backend endpoint or use `Promise.all()` for parallelism.

## Safety

- SHADOW/DEMO/LIVE: **not enabled**
- `trade_command.json`: **not written**
- Bridge: **not started**
- Services: **not started/stopped** (frontend hot-reloaded, backend was already running)
