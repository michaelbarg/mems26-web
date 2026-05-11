# HOTFIX — LivePriceStream Tick Deduplication

**Date:** 2026-05-11
**File:** `bridge/v9_streams/live_price_stream.py`

## Bug

Only ~5 events in Redis Stream after 32+ seconds of bridge runtime.
Expected: 150-200 (5 ticks/sec × 30s).

## Root Cause

DLL writes `ts` as `time(nullptr)` — **seconds resolution**. Multiple
200ms ticks within the same second share the same `ts` value. The dedup
logic `if ts == self._last_ts: return` filtered all but the first tick
per second, yielding ~1 tick/sec instead of ~5 tick/sec.

## Fix

Changed dedup key from `ts` alone to `(mtime, price)`:
- `mtime` = file modification time (sub-second, from OS)
- `price` = current price value
- Same mtime + same price = genuine duplicate (skip)
- Different mtime = new DLL write (publish)

Also reduced log interval from every 100 ticks to every 20 for easier
monitoring during UAT.

## Expected Throughput After Fix

- DLL writes every 200ms → **5 ticks/sec**
- 60 seconds → **~300 events** in `mems26:events:price.tick`
- Bridge log: `[live_price] 20 ticks pushed` then `40`, `60`, etc.

## Verification

```bash
# Restart bridge, wait 60s, then:
redis-cli XLEN mems26:events:price.tick
# Expected: 150-300
```
