# P30.8 — 5min.json Sierra Export Contract

**Date:** 2026-05-18  
**Status:** HISTORY/BACKFILL/CHART GREEN; bars-only live path GREEN — full 12-stream bridge still blocked by overload  
**No SHADOW/DEMO/LIVE activation. No trade command writes.**

---

## Root Cause

The bridge was already designed to load recent 5-minute history on startup, but
the expected source file did not exist:

```text
[bars_5min] History: file not found at /Users/michael/SierraChart_Data/v9_export/5min.json
```

The stream contract existed in `bridge/v9_streams/bars_5min_stream.py`, but the
file itself was marked as not yet implemented:

```text
Source: DLL export — 5min.json (NOT YET IMPLEMENTED AS STANDALONE DLL EXPORT).
```

So Sierra was running and writing other files, but not the one required by
`Bars5MinStream`.

---

## Fix

### Sierra study export

Added canonical 5-minute OHLCV export in the ACSIL code:

- `sc_study/v9_types.h`
  - Added `V9FiveMinBar`.
- `sc_study/v9_exports.h`
  - Added 5-minute bucket builder.
  - Aggregates chart bars into 5-minute buckets.
  - Emits the existing bridge contract:

```json
{
  "type": "5min",
  "version": "v9.3.0",
  "export_ts": 1779120000,
  "bar_count": 120,
  "bars": [
    {
      "ts": 1779119700,
      "o": 7400.0,
      "h": 7410.0,
      "l": 7398.0,
      "c": 7405.0,
      "vol": 1234,
      "poc_vol": 0,
      "vah": 0,
      "val": 0,
      "cumulative_delta": 22
    }
  ]
}
```

- `sc_study/MES_AI_DataExport.cpp`
  - Writes `5min.json` into the configured V9 export directory.

### Bridge/backend safety

- `bridge/v9_streams/base_stream.py`
  - For `/api/v9/bars/5min`, posts `data["bars"]` instead of the wrapper object,
    matching the FastAPI endpoint contract.

- `bridge/v9_history.py`
  - Historical startup load uses the same payload normalization for 5-minute
    bars.

- `backend/v9/api/v9/bars.py`
  - `/api/v9/bars/5min` now upserts by `ts + symbol`.
  - This prevents every repeated `5min.json` export from duplicating the same
    historical bars in `v9_bars_5min`.

---

## Tests

```text
python3 -m pytest tests/v9/bridge/test_streams.py tests/v9/db/test_api.py tests/v9/api/test_chart_bars5min_integrity.py -q
34 passed
```

```text
python3 -m pytest tests/v9/ -q
1296 passed, 1 skipped, 8 warnings
```

Added coverage:

- `Bars5MinStream._push_api()` posts the bars array, not the wrapper.
- `/api/v9/bars/5min` upserts a repeated timestamp instead of duplicating it.

---

## Live UAT

Earlier status was code-only until the Sierra DLL could be compiled/reloaded.
That live UAT is now recorded below.

Build follow-up:

- First Sierra remote build attempt failed because
  `MES_AI_DataExport_merged.cpp` called `v9_woodies_5min_to_json()` without the
  inlined definition.
- The monolith was regenerated from the modular sources using
  `scripts/build_monolithic_cpp.sh`, so it now includes `v9_woodies_export.h`
  content and the missing function.
- Verified in `MES_AI_DataExport_merged.cpp`:
  - one `SCDLLName`
  - one `#include "sierrachart.h"`
  - `v9_woodies_5min_to_json` present
  - `v9_write_json(v9dir, "5min.json", ...)` present
  - `GraphName = "MES AI Data Export v9.3.1-p30.8"`

Post-Sierra reload verification:

```text
/Users/michael/SierraChart_Data/v9_export/5min.json
exists: true
fresh: true
size: 86393 bytes
type: 5min
version: v9.3.2-p30.8
bar_count: 601
bars_len: 601
ascending: true
missing_required_first10: []
bad_ohlc_count: 0
first_ts: 1778753400
last_ts: 1779113400
```

Pre-bridge DB baseline:

```text
v9_bars_5min count: 556
min_ts: 2026-05-12 07:50:00.000000
max_ts: 2026-05-17 16:15:00.000000
bridge_running: false
```

Final UAT, 2026-05-18 21:12-21:20 local:

- Sierra generated a fresh
  `/Users/michael/SierraChart_Data/v9_export/5min.json` with
  `version=v9.3.2-p30.8` and 601 bars.
- Pre-bridge DB baseline: `v9_bars_5min` had 556 rows with
  `max_ts=2026-05-17 16:15:00`.
- Ran `bridge/json_bridge.py --history-only` with
  `CLOUD_URL=http://localhost:8000` and `V9_DISABLE_WATCHDOG=1`.
  It exited 0 and logged:

```text
[bars_5min] History: API push OK
bars_5min: OK
```

- First run hit an old backend process that had not loaded the new upsert code.
  DB reached 1157 rows with 304 duplicate `(ts, symbol)` groups. Backend was
  restarted to load current code, then `v9_bars_5min` was deduped by keeping
  the newest `id` per `(ts, symbol)` and deleting 304 duplicate rows.
- After repair: DB had 853 rows, `duplicate_groups=0`, and
  `max_ts=2026-05-18 14:10:00`.
- Started full bridge with local `CLOUD_URL`. It pushed `bars_5min`; DB
  advanced without duplicates to 854 then 855 rows, with
  `max_ts=2026-05-18 14:20:00` and `duplicate_groups=0`.
- Full bridge caused backend overload / chart endpoint timeout under
  all-stream push load. Bridge was stopped and backend restarted cleanly.
  Bridge is not left running.

Final endpoint UAT after backend restart and bridge stopped:

```text
/api/v9/chart/bars5min?limit=600
latency_ms: 66.04
endpoint_count: 600
db_count: 855
duplicate_groups: 0
bad_count: 0
latest_ts: 2026-05-18 14:20:00
db_max_ts: 2026-05-18 14:20:00
```

```text
/api/v9/chart/bars5min?limit=240
latency_ms: 22.29
endpoint_count: 240
duplicate_groups: 0
bad_count: 0
latest_ts: 2026-05-18 14:20:00
db_max_ts: 2026-05-18 14:20:00
```

Quality, recency, cardinality, and latency are GREEN for the 5-minute history
backfill and chart endpoint with the bridge stopped.

---

## P30.8 Follow-Up Addendum — Bars-Only Live Path

Follow-up window: 2026-05-18 21:44-21:56 local.

User correctly questioned whether the frontend was still receiving live data
directly from Sierra. Actual architecture is:

```text
Sierra DLL -> /Users/michael/SierraChart_Data/v9_export/5min.json -> bridge -> backend/DB -> frontend
```

Sierra `5min.json` was fresh, but DB/API had lagged because the bridge had been
stopped after the full 12-stream overload. A safe narrow live path was
implemented and verified: `json_bridge.py` now supports stream selection via
`--bars-5min-only`, `--streams=...`, or `V9_STREAMS`. The bridge was started
with `CLOUD_URL=http://localhost:8000`, `V9_DISABLE_WATCHDOG=1`,
`V9_SKIP_HISTORY=1`, and `--bars-5min-only`.

In bars-only live mode, `bars_5min` skips startup history and pushes only the
latest bar from `5min.json` during live polling. Full history remains available
through `--history-only`.

POST `/api/v9/bars/5min` timeout diagnosis: DB commit succeeded, but the
response hung because Redis publish had no short timeout and 5-minute ingestion
synchronously triggered `EventDispatcher` / `BarRouter` / `FiveMinSystem`.
Fixes applied:

- Redis publish uses short socket timeouts and warns on failure.
- `BarRouter` runs handlers in a background thread.
- 5-minute POST no longer dispatches as `cumulative_delta`.
- 5-minute `BarRouter` route runs only for newly inserted bars, not every
  update of the active current bar.

Targeted regression suite:

```text
pytest tests/v9/db/test_api.py tests/v9/bridge/test_streams.py -q
35 passed, 5 warnings
```

Final UAT with bars-only bridge running:

```text
bridge:
MEMS26 V9 Bridge starting — 1 streams
Historical backfill skipped via V9_SKIP_HISTORY
New data push #1..#6
API push target local

backend:
POST /api/v9/bars/5min 200 OK repeatedly

/api/v9/chart/bars5min?limit=600
rows: 600
latest: 2026-05-18 14:55:00.000000
bad_count: 0
latency_ms: 39.21

/api/v9/chart/bars5min?limit=240
rows: 240
latest: 2026-05-18 14:55:00.000000
bad_count: 0
latency_ms: 13.97

DB count: 862
duplicates: 0
Sierra file age: ~2s
Sierra last local: 17:55 -> DB UTC-normalized storage: 14:55
```

Current final state: backend running and bars_5min-only bridge running. This is
not a GREEN for the full live bridge. Remaining risks: `poc_vol` / VAH / VAL
parity is not fixed; full bridge overload is not fixed; frontend poll/request
storm still exists, though bars history now loads.

---

## Gate

P30.8 is GREEN for `5min.json -> /api/v9/bars/5min -> v9_bars_5min -> chart`
history/backfill/chart validation and for the narrow bars-only live path.

Remaining risk / next P-ID: full 12-stream bridge live mode still overloads the
backend and needs a separate fix before declaring full live bridge GREEN.
