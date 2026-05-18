# P30.8 — 5min.json Sierra Export Contract

**Date:** 2026-05-18  
**Status:** CODE GREEN / LIVE UAT PENDING — requires Sierra DLL compile/reload  
**No bridge started by this prompt. No SHADOW/DEMO/LIVE activation. No trade command writes.**

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

## Live UAT Still Required

This prompt changed source code only. The Sierra DLL must be compiled/reloaded
before live UAT can pass.

Required next steps:

1. Compile/reload `sc_study/MES_AI_DataExport.cpp` in Sierra.
2. Confirm Sierra writes:

```text
/Users/michael/SierraChart_Data/v9_export/5min.json
```

3. Validate `5min.json`:
   - fresh mtime
   - `type == "5min"`
   - `bar_count > 0`
   - `bars[].ts/o/h/l/c/vol` present
   - bars sorted ascending

4. Start/restart bridge only after the file exists and is fresh.
5. Verify DB:
   - `v9_bars_5min` row count increases or updates without duplicates.
   - `MAX(ts)` reaches the latest Sierra bar.
6. Verify chart endpoint four axes:
   - Quality: `bad_count=0`
   - Recency: endpoint latest equals DB `MAX(ts)`
   - Cardinality: endpoint returns requested limit where enough rows exist
   - Latency: remains under budget

---

## Gate

P30.8 is code-green but not live-green until Sierra is recompiled/reloaded and
the bridge UAT confirms `5min.json -> /api/v9/bars/5min -> v9_bars_5min -> chart`.
