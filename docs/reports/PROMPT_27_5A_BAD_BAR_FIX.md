# PROMPT 27.5A — Bad Bar Fix

**Date:** 2026-05-17  
**Scope:** `/api/v9/chart/bars5min` backend bad-bar integrity  
**Status:** Code + tests complete; live backend restart still required for endpoint UAT

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

No existing DB rows were deleted or modified in this prompt.

## Evidence

Before code reload, the live backend process still returns the three known bad rows:

```text
live_endpoint_count 240
live_endpoint_bad_count 3
live_endpoint_bad [
  (198, '2026-05-16 05:05:00.000000'),
  (228, '2026-05-16 09:05:00.000000'),
  (229, '2026-05-16 09:10:00.000000')
]
```

Calling the updated backend fetch function directly against the same DB filters those rows:

```text
direct_fetch_count 240
direct_fetch_bad_count 0
```

The live endpoint will require a backend restart/reload before endpoint UAT can show the new behavior.

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

## Remaining UAT

Do not consider P27.5a fully closed until backend is restarted and the live endpoint returns clean data:

```bash
curl -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=240"
```

Expected after backend reload:

- `0` rows with `high - low > 20` and `(high - low) / low > 0.02`.
- No client-side filter should be required for these three known bad bars.

## DB Cleanup Decision

The bad rows still exist in the local DB. They are now filtered from backend history reads once the backend reloads, and future ingestion paths reject similar rows.

Recommended next decision before long replay/SHADOW evidence:

- Keep raw bad rows for audit and rely on server-side filtering, or
- Add a separate quarantine/delete script with explicit approval.
