# P27.5b — Live-Price Freshness (`age_ms < 60000` during RTH)

**Date:** 2026-05-18 (preparation)
**Status:** PREPARED — awaiting RTH live validation

---

## Architecture Map

```
Sierra Chart DLL (MES_AI_DataExport.cpp)
  └─ writes live_price.json every ~200ms
     Path: /Users/michael/SierraChart_Data/v9_export/live_price.json
     Shape: { price, ts, bid, ask, vol }

Backend (direct file read — no bridge involvement)
  └─ backend/v9/api/v9/price_routes.py : live_price()
     Reads live_price.json, computes age_ms = (time.time() - file mtime) * 1000
     Returns: { price, bid, ask, volume, ts_utc, age_ms }

Bridge (parallel, independent path — NOT involved in /api/v9/live_price)
  └─ bridge/v9_streams/live_price_stream.py : LivePriceStream
     Watches same live_price.json, publishes price.tick to Redis Streams (Event Bus)
     Used by: pre_fire_validator (bridge health check, age < 5s)
     NOT used by: the /api/v9/live_price route
```

**Key insight:** The `/api/v9/live_price` route reads the file directly —
the bridge is NOT in the data path for this endpoint. The only requirement
is that **Sierra Chart is running and writing `live_price.json`**.

## Files/Functions Involved

| File | Function | Role |
|------|----------|------|
| `backend/v9/api/v9/price_routes.py` | `live_price()` | API endpoint — reads file, computes age_ms from mtime |
| `bridge/v9_streams/live_price_stream.py` | `LivePriceStream` | Bridge stream — publishes to Redis (not used by endpoint) |
| `backend/v9/api/v9/status.py` | `_check_sierra()` | Status check — uses same file mtime, writing=age<10s |
| `backend/v9/services/pre_fire_validator/validator.py` | `_check_bridge_health()` | Pre-fire gate — checks file mtime age < 5s |

## Root-Cause Hypotheses (from code reading)

### H1: Sierra Chart not running (MOST LIKELY for weekend observation)
- The DLL writes `live_price.json` only when Sierra is open with a chart.
- Weekend: Sierra is off → file not updated → `age_ms` grows unbounded.
- **This is expected behavior, not a bug.** The observed `age_ms ≈ 64 min` from
  session 2026-05-16 was likely during a period when Sierra was closed or
  the chart was not active.

### H2: Export directory mismatch
- `V9_EXPORT_DIR` defaults to `/Users/michael/SierraChart_Data/v9_export`.
- If Sierra writes to a different directory, the backend reads a stale file.
- **Evidence:** File exists at the expected path with plausible content
  (`price=7524.25`, `ts=2026-05-17T21:35:37Z`). Not likely the issue.

### H3: Timezone/clock drift
- `age_ms` is computed from `os.path.getmtime()` vs `time.time()` — both
  use the local system clock. No timezone conversion involved.
- **Not likely** unless the system clock is wrong.

### H4: File locking / write contention
- Sierra DLL writes every ~200ms. Backend reads on each request.
- No file locking in either direction. Could theoretically read a partial
  write, but this would cause a JSON parse error (handled), not stale data.
- **Low risk.**

### H5: Market-closed behavior not explicit
- The endpoint does NOT distinguish "market closed, stale is expected" from
  "market open, stale is a problem." It always returns `age_ms` with no
  `stale` or `market_status` field.
- **This is a clarity issue, not a data-path bug.** The frontend already
  filters `age_ms > 60s` client-side.

## Predicted Outcome

P27.5b will likely PASS automatically once Sierra Chart is running during RTH,
because the route reads the file directly (no bridge relay needed). The bridge
is only needed for the Event Bus path used by `pre_fire_validator`.

If P27.5b fails during RTH with Sierra running, the root cause is likely H2
(export dir mismatch) or a DLL issue (not writing the file).

## UAT Script

**Path:** `scripts/uat_prompt_27_5b_live_price.sh`
**Usage:**
```bash
cd /Users/michael/Downloads/mems26_web_git
bash scripts/uat_prompt_27_5b_live_price.sh
```

**Behavior:**
- Does NOT start/stop any services.
- Checks backend is reachable at `127.0.0.1:8000`.
- Calls `/api/v9/live_price` 10 times, 1s apart.
- For each sample: prints HTTP code, price, age_ms, ts_utc, latency_ms.
- Samples with `age_ms > 600000` (10 min) are marked SKIP (market likely closed).
- PASS: all 10 samples have `age_ms < 60000`.
- DEFERRED: all samples skipped (market closed).
- FAIL: any sample exceeds threshold during apparent RTH.

## RTH Acceptance Criteria

P27.5b goes GREEN when:
1. Sierra Chart is running with MES chart open.
2. Backend is running at `127.0.0.1:8000`.
3. `bash scripts/uat_prompt_27_5b_live_price.sh` returns **PASS** (10/10 samples
   with `age_ms < 60000`).
4. The 4 UAT axes are verified (see below).

Bridge is NOT required for the endpoint itself, but should be running for
full system validation (pre_fire_validator depends on it).

## 4 UAT Axes

| Axis | Threshold | Current Status |
|------|-----------|----------------|
| **Quality** | No errors, valid JSON with price + age_ms | Pending live sample |
| **Recency** | `age_ms < 60000` during RTH | Pending RTH — currently 615 min (Sierra off, weekend) |
| **Cardinality** | 10/10 consecutive PASS samples | Pending RTH validation |
| **Latency** | Endpoint response < 100ms | Expected <5ms (direct file read, no DB) |

## Important Note

**P27.5b cannot be GREEN until Sierra Chart is running during RTH and
`age_ms < 60000` passes 10 consecutive checks.** No code change is expected
to be needed — the likely root cause of the original observation was Sierra
not actively writing the file.

## Possible Enhancement (NOT in scope — note for future)

The endpoint could return an explicit `market_status` or `stale` field based
on market hours, so clients don't need to infer staleness from `age_ms` alone.
This is a clarity improvement, not a P27.5b blocker.
