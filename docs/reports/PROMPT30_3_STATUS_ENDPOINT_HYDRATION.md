# P30.3 — Status Endpoint + Hydration Overlay

**Date:** 2026-05-18  
**Status:** PARTIAL GREEN — status code hardened; live frontend-load latency remains P30.4 blocker  
**Backend was restarted with `.env` after approval. No bridge action. No SHADOW/DEMO/LIVE activation. No trade command writes.**

---

## Summary

P30.3 addressed the operational blocker found in P30.2:

- `/api/v9/status` could exceed the operator-dashboard latency budget because
  `_check_bridge()` performed many synchronous Upstash Redis REST calls, each
  previously allowed to wait up to 3 seconds.
- The status endpoint now uses a bounded Redis timeout, a total bridge-health
  budget, and a total endpoint budget. If Redis or another layer is slow, that
  layer returns an explicit `timeout` result instead of blocking the whole
  dashboard.
- The React hydration overlay observed during browser automation was rechecked
  and identified as a Cursor browser-tool artifact from injected
  `data-cursor-ref` attributes, not a MEMS26 UI defect. No application UI code
  change was kept for this.

After backend restart, `/api/v9/status` returned `200`, but live latency under
the already-open frontend load remained above the operator target. Follow-up
audit points to frontend request amplification and duplicated polling as the
next blocker.

---

## Code Change

Changed `backend/v9/api/v9/status.py` only:

- Added `V9_STATUS_REDIS_TIMEOUT_S`, default `0.2`.
- Added `V9_STATUS_BRIDGE_BUDGET_S`, default `0.8`.
- Changed `_redis_cmd()` to use the bounded timeout.
- Changed `_check_bridge()` to stop checking Redis heartbeat keys once the budget
  is exceeded.
- Added `streams_checked` and `partial` fields so degraded Redis visibility is
  explicit, not silent.
- Added `V9_STATUS_ENDPOINT_BUDGET_S`, default `0.9`.
- Changed `system_status()` to run independent health checks in parallel and mark
  late checks as `{"available": false, "status": "timeout"}`.

New regression test:

- `tests/v9/api/test_status_endpoint_budget.py`

The tests monkeypatch Redis/status checks to be slow and verify `_check_bridge()`
and `system_status()` return within budget with explicit timeout/partial fields.

---

## Verification

Targeted tests:

```text
python3 -m pytest tests/v9/api/test_status_endpoint_budget.py -q
2 passed
```

Related targeted suite:

```text
python3 -m pytest tests/v9/api/test_status_endpoint_budget.py tests/v9/api/test_chart_bars5min_integrity.py tests/v9/shadow/test_shadow_schemas.py -q
35 passed
```

Full V9 regression:

```text
python3 -m pytest tests/v9/ -q
1287 passed, 1 skipped, 4 warnings
```

Lint:

```text
ReadLints: no linter errors for edited backend/test files
```

Frontend hydration recheck:

- Browser page still rendered TopBar, chart area, and right panel.
- Hydration warning remained visible only in Cursor browser automation.
- Console evidence pointed to injected `data-cursor-ref` attributes, not the
  app's source code.
- A temporary TopBar code change was removed after this diagnosis.

---

## Live Verification Status

Initial live direct probe before backend reload:

```text
GET http://127.0.0.1:8000/api/v9/status
ERR timeout after 5011.93ms
```

After approved backend restart with `.env`, the backend loaded the code and
served `/api/v9/status` with explicit timeout warnings for slow Redis-backed
layers:

```text
WARNING [status] check timed out: bridge
WARNING [status] check timed out: event_bus
GET /api/v9/status HTTP/1.1 200 OK
```

However, under the already-open frontend load, direct probe latency was still
not operator-green:

```text
/api/v9/health: 3764.96ms, then 79.29ms, 59.15ms
/api/v9/status: 4467.76ms, 4420.31ms, 2504.20ms
/api/v9/live_price: 2017.34ms, 1952.58ms, 2044.10ms
```

Interpretation:

- P30.3 fixed the status endpoint's internal timeout behavior.
- The remaining blocker is broader backend responsiveness under frontend polling
  load, not only `/api/v9/status`.
- CC read-only audit identified duplicated/high-frequency frontend polling:
  `ChartV5b` polls `/api/v9/live_price` every 1s despite an existing price
  WebSocket store; `TopBar` and `BannerStack` both poll `/api/v9/status`; and
  `useSystemStatePolling(2000)` triggers many system/current requests.

---

## Next Required Step

Open P30.4 — frontend polling/backend responsiveness:

1. Remove duplicated `/api/v9/live_price` polling from `ChartV5b` and use the
   existing `priceStore`/WebSocket path.
2. Add in-flight guards or shared status state so `/api/v9/status` polling does
   not overlap between UI components.
3. Re-measure `/api/v9/status`, `/api/v9/live_price`, chart endpoints, and
   system endpoints with the frontend open.
4. Only call the cockpit visual gate GREEN if status latency is under target and
   bars5min still passes quality/recency/cardinality/latency.
