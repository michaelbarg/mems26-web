# P30.6 — Systems Snapshot Batch

**Date:** 2026-05-18  
**Status:** GREEN — frontend system polling batched; cockpit data endpoints within budget  
**Backend and frontend restarted to load current code. No bridge started. No SHADOW/DEMO/LIVE activation. No trade command writes.**

---

## Root Cause

After P30.5, `/api/v9/cockpit/heartbeat` was lightweight in code but still
showed live spikes because the frontend had stale intervals and continued to
generate many system requests:

- `systemStateStore.fetchAllStates()` still had a fallback path with up to 12
  serial requests.
- The running Next dev process/browser tab retained older polling intervals
  until the frontend was restarted and the page reloaded.

This kept the backend queue busy and made cheap endpoints appear slow.

---

## Fix

Backend:

- Added `GET /api/v9/cockpit/systems-snapshot`.
- Returns all S1-S6 state in one local response.
- No Redis/Upstash.
- No HTTP self-calls.
- No `/api/v9/status`.

Frontend:

- `systemStateStore.fetchAllStates()` now tries `/api/v9/cockpit/systems-snapshot`
  first.
- Existing per-system polling remains only as fallback if the snapshot fails.
- `_fetchInFlight` guard remains in place.

Operational:

- Backend was restarted with `.env`.
- Frontend dev server was restarted to clear stale HMR intervals.
- Only one MEMS26 browser tab was left open before final measurement.

---

## Tests

```text
python3 -m pytest tests/v9/api/test_cockpit_heartbeat.py tests/v9/api/test_cockpit_systems_snapshot.py tests/v9/api/test_chart_bars5min_integrity.py -q
9 passed
```

```text
python3 -m pytest tests/v9/ -q
1294 passed, 1 skipped, 4 warnings
```

```text
cd frontend/v9 && npx eslint src/v9/store/systemStateStore.ts
PASS
```

---

## Live UAT

After frontend restart and page reload:

```text
/api/v9/cockpit/heartbeat:
  242.51ms first sample after reload, then 18.95ms, 3.61ms

/api/v9/cockpit/systems-snapshot:
  5.47ms, 5.33ms, 7.05ms

/api/v9/live_price:
  4.08ms, 5.50ms, 5.14ms

/api/v9/chart/bars5min?limit=240:
  40.63ms, 41.73ms, 37.91ms
```

Bars5min four axes:

| Axis | Result |
|---|---|
| Quality | PASS — `bad_count=0` |
| Recency | PASS — endpoint latest equals DB `MAX(ts)` |
| Cardinality | PASS — `count=240` |
| Latency | PASS — `37.91ms` to `41.73ms` |

---

## Residuals

- `/api/v9/status` remains diagnostic-only and should not be used as a cockpit
  heartbeat.
- Some other UI strips still poll independently (`trades`, `layer0`, TPO/chart
  overlays), but live data endpoints are now within budget with one cockpit tab.
- If latency returns, first check for duplicate browser tabs or stale Next HMR
  intervals before changing backend code.

---

## Gate

P30.6 is GREEN for the cockpit data/connection foundation. It is now reasonable
to proceed to P31 design/UX adaptation against the existing cockpit base.
