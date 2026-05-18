# P30.3 — Status Endpoint + Hydration Overlay

**Date:** 2026-05-18  
**Status:** CODE GREEN / LIVE RESTART PENDING  
**No services started or restarted. No bridge action. No SHADOW/DEMO/LIVE activation. No trade command writes.**

---

## Summary

P30.3 addressed the operational blocker found in P30.2:

- `/api/v9/status` could exceed the operator-dashboard latency budget because
  `_check_bridge()` performed many synchronous Upstash Redis REST calls, each
  previously allowed to wait up to 3 seconds.
- The status endpoint now uses a bounded Redis timeout and a total bridge-health
  budget. If Redis is slow, bridge status returns a partial health result instead
  of blocking the whole dashboard.
- The React hydration overlay observed during browser automation was rechecked
  and identified as a Cursor browser-tool artifact from injected
  `data-cursor-ref` attributes, not a MEMS26 UI defect. No application UI code
  change was kept for this.

The already-running backend did not auto-reload the Python code. A live
`/api/v9/status` probe still timed out after the code fix, so live endpoint
verification requires an approved backend restart/reload.

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

New regression test:

- `tests/v9/api/test_status_endpoint_budget.py`

The test monkeypatches Redis calls to be slow and verifies `_check_bridge()`
returns quickly with `partial=true`.

---

## Verification

Targeted tests:

```text
python3 -m pytest tests/v9/api/test_status_endpoint_budget.py -q
1 passed
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

Live direct probe after the code change:

```text
GET http://127.0.0.1:8000/api/v9/status
ERR timeout after 5011.93ms
```

Interpretation:

- The running backend did not reload the changed `status.py`.
- Code and tests are GREEN.
- Live `/api/v9/status` cannot be declared GREEN until the backend is restarted
  or reloaded and the endpoint is probed again.

---

## Next Required Step

Ask Michael before restarting backend. After approval:

1. Restart/reload backend only. Do not start bridge unless explicitly requested.
2. Probe `/api/v9/status` and require latency under the documented threshold.
3. Re-run browser visual proof and confirm no app-caused hydration overlay.
4. Update this report with live latency evidence.
