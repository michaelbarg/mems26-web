# P30.5 — Cockpit Health / Connection Truth

**Date:** 2026-05-18
**Status:** GREEN — heartbeat endpoint added, UI connection truth fixed
**Backend restarted with `.env`. No bridge started. No SHADOW/DEMO/LIVE activation. No trade_command writes.**

---

## Root Cause

The cockpit showed misleading "DISCONNECTED" status because:

1. **TopBar used `/api/v9/status`** as its sole heartbeat — this endpoint runs
   11 health checks (including Redis/Upstash calls) and takes 0.9-4.5s under load.
   When it timed out, the UI had no backend health signal.

2. **BannerStack also polled `/api/v9/status`** every 10s, adding more load and
   also calling 6 system `/current` endpoints serially.

3. **ConnectionIndicator** (price WebSocket truth) was actually correct — it
   showed "LIVE" when the WS was connected. But TopBar's status dots showed
   "no subscribers" because the heavy status endpoint failed.

## Fix

### Backend: `/api/v9/cockpit/heartbeat` (new endpoint)

Added in `backend/v9/app.py`. Returns only cheap local truth:

```json
{
  "alive": true,
  "mode": "shadow",
  "ts": 1779116101.27,
  "price_file_age_ms": 1009,
  "ws_clients": 2
}
```

- No Redis/Upstash calls
- No external dependencies
- `os.path.getmtime()` for price file age (1 syscall)
- `len(price_ws_manager._clients)` for WS count (in-memory)
- Target: <20ms baseline, <100ms under load

### Frontend changes

| File | Change |
|------|--------|
| `TopBar.tsx` | Switched from `/api/v9/status` to `/api/v9/cockpit/heartbeat`. Status dots now show price file health + WS client count. |
| `BannerStack.tsx` | Switched bridge health check from `/api/v9/status` to `/api/v9/cockpit/heartbeat`. Removed 6 redundant system `/current` calls (systemStateStore already polls those). Interval 10s → 30s. Added in-flight guard. |

### Connection truth model (after P30.5)

| Signal | Source | What it means |
|--------|--------|---------------|
| Green dot (left) | Heartbeat `price_file_age_ms < 120s` | Sierra is writing price data |
| Green dot (right) | Heartbeat `ws_clients > 0` | Price WebSocket has connected clients |
| ConnectionIndicator | `priceStore.connected + lastUpdateMs` | Real-time WebSocket tick flow |

## Tests

```
python3 -m pytest tests/v9/api/test_cockpit_heartbeat.py -q → 3 passed
python3 -m pytest tests/v9/ -q → 1291 passed, 1 skipped
```

3 new tests:
- `test_heartbeat_returns_200` — schema validation
- `test_heartbeat_latency_under_100ms` — budget check
- `test_heartbeat_does_not_call_status` — no heavy status keys leaked

Frontend lint (TopBar.tsx, BannerStack.tsx): **0 errors**.

## Live Latency

Heartbeat endpoint (with frontend open):
```
12ms, 50ms, 80ms (baseline)
Occasional 2s spike from single-worker GIL contention
```

Comparison with heavy `/api/v9/status`:
```
/api/v9/status:              917ms-4468ms
/api/v9/cockpit/heartbeat:   12ms-80ms (baseline)
```

## Bars5min 4-Axis UAT

| Axis | Threshold | Actual | Result |
|------|-----------|--------|--------|
| Quality | bad_count=0 | 0 | PASS |
| Recency | Latest bar | 2026-05-17 16:15:00 | PASS |
| Cardinality | count=240 | 240 | PASS |
| Latency | <100ms baseline | 15-50ms baseline | PASS |

## Residual

- Single-worker uvicorn with `systemStateStore` making 12 sequential fetches
  every 2s can still cause GIL contention spikes (2-4s) on any endpoint when
  requests overlap. The heartbeat is cheap but not immune to GIL blocking.
- A future improvement would be `--workers 2` or batching system state into
  one backend call, but this is outside P30.5 scope.

## Safety

- SHADOW/DEMO/LIVE: **not enabled**
- `trade_command.json`: **not written**
- Bridge: **not started**
- Backend: **restarted** to load new heartbeat endpoint (with `.env`)
