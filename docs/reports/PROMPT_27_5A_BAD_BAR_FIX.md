# PROMPT 27.5A — Bad Bar Fix

**Date:** 2026-05-17  
**Scope:** `/api/v9/chart/bars5min` backend bad-bar integrity  
**Status:** GREEN — code + tests + live backend UAT all green; bad DB rows removed.

## Root Cause

The local SQLite table `v9_bars_5min` already contains invalid 5-minute bars with impossible MES ranges. The ingestion path accepted OHLC values without validating them before UPSERT, so bad bars could persist and later be returned by chart/history endpoints.

Confirmed bad rows currently in `data/mems26_local.db`:

| ts | open | high | low | close | volume |
|---|---:|---:|---:|---:|---:|
| `2026-05-16 05:05:00.000000` | 7462.25 | 7463.0 | 7180.25 | 7180.25 | 890003 |
| `2026-05-16 09:05:00.000000` | 7430.75 | 7463.0 | 7172.5 | 7461.0 | 55871343 |
| `2026-05-16 09:10:00.000000` | 7264.75 | 7462.75 | 7172.5 | 7460.0 | 40580682 |

The existing client-side `looksOk` guard is not sufficient as the source of truth. Backend ingestion and backend history reads must enforce integrity.

## Fix

Implemented backend-side integrity enforcement:

- `backend/v9/services/bar_integrity.py`
  - Rejects null, non-positive, and `low > high` OHLC.
  - Keeps wick/body checks.
  - Adds MES-specific wide-range protection: reject bars where `high - low > 20` points and `(high - low) / low > 2%`.

- `backend/v9/api/v9/bars.py`
  - Rejects invalid `/api/v9/bars/5min` payload bars before DB insert.
  - Does not publish, dispatch, or route rejected bars as the latest bar.
  - Returns `rejected` count.

- `backend/v9/services/bar_ingestion.py`
  - Rejects invalid bars before opening a DB session or performing UPSERT.

- `backend/v9/api/v9/bars_5min_history.py`
  - Filters invalid historical rows before returning chart data.
  - This is defense-in-depth for bad rows already present in the DB.

After UAT, the three confirmed bad rows were also deleted from the local DB (see DB Cleanup section).

## Evidence

### Before — code reload pending

The pre-restart backend process still returned the three known bad rows:

```text
live_endpoint_count 240
live_endpoint_bad_count 3
live_endpoint_bad [
  (198, '2026-05-16 05:05:00.000000'),
  (228, '2026-05-16 09:05:00.000000'),
  (229, '2026-05-16 09:10:00.000000')
]
```

Calling the updated backend fetch function directly against the same DB already filtered those rows:

```text
direct_fetch_count 240
direct_fetch_bad_count 0
```

### After — backend restarted, bad rows deleted

Backend was restarted manually by Michael (orphaned PID could not be killed from the agent sandbox). Live endpoint UAT after restart:

```text
GET http://127.0.0.1:8000/api/v9/chart/bars5min?limit=240
live_endpoint_count 240
live_endpoint_bad_count 0
```

Local DB after explicit cleanup of the three known bad rows:

```text
SELECT COUNT(*) FROM v9_bars_5min
  WHERE (high - low) > 20 AND (high - low) / low > 0.02;
-> 0

SELECT COUNT(*) FROM v9_bars_5min;
-> 549

SELECT MAX(ts) FROM v9_bars_5min;
-> 2026-05-16 11:05:00.000000
```

The latest `ts` (2026-05-16 11:05) reflects the last fully ingested replay session before the post-reboot downtime; new bars will resume once the backend is back up alongside the bridge.

## Tests

Targeted P27.5a tests:

```text
PYTHONPATH="/Users/michael/Downloads/mems26_web_git" python3 -m pytest \
  "/Users/michael/Downloads/mems26_web_git/tests/v9/services/test_bar_integrity.py" \
  "/Users/michael/Downloads/mems26_web_git/tests/v9/api/test_chart_bars5min_integrity.py" -q

15 passed in 1.10s
```

Hydration regression:

```text
PYTHONPATH="/Users/michael/Downloads/mems26_web_git" python3 -m pytest \
  "/Users/michael/Downloads/mems26_web_git/tests/test_hydration.py" -q

9 passed in 0.79s
```

## UAT Result

P27.5a is closed:

- Live endpoint returns `bad_count = 0` for `limit=240`.
- DB query for the same impossible-range pattern returns `0` rows.
- No client-side filter is required for the three previously-known bad bars.

## DB Cleanup Decision (resolved)

The three previously-confirmed bad rows were deleted from `data/mems26_local.db` after the live UAT passed. Going forward:

- Backend ingestion (`bars.py`, `bar_ingestion.py`) rejects invalid OHLC bars before any DB write.
- Backend history (`bars_5min_history.py`) over-fetches and filters with `bar_is_valid` as defense-in-depth.
- No client-side `looksOk` patch is needed for new ingest.
