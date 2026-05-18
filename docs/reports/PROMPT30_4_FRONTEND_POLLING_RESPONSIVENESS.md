# P30.4 — Frontend Polling / Backend Responsiveness

**Date:** 2026-05-18
**Status:** GREEN — request amplification reduced, latency within budget
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

Post-review hardening:

- `_fetchInFlight` is now released in `finally`, so an unexpected exception
  cannot permanently disable system-state polling until page refresh.
- `systemStateStore.ts` now passes targeted ESLint after replacing the local
  `raw` type from `any` to `unknown`.

## Tests

Backend (no regressions):
```
python3 -m pytest tests/v9/ -q → 1288 passed, 1 skipped
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

## Bars5min 4-Axis UAT

| Axis | Threshold | Actual | Result |
|------|-----------|--------|--------|
| Quality | bad_count=0 | 0 | PASS |
| Recency | Latest bar timestamp | 2026-05-17 16:15:00 | PASS |
| Cardinality | count=240 | 240 | PASS |
| Latency | <100ms | 13ms | PASS |

## Residual Notes

- `/api/v9/status` is ~0.9s due to `STATUS_ENDPOINT_BUDGET_S` timeout on Redis-backed
  checks (bridge, event_bus). This is by design — slow external dependencies are capped,
  not eliminated.
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
