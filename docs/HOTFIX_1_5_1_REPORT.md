# HOTFIX 1.5.1 — Status Endpoint Bridge Check

**Date:** 2026-05-11

## Bug
`/api/v9/status` reported `bridge.running: false, streams_active: 0`
despite bridge being alive and actively pushing to Redis.

## Root Cause
Status endpoint checked heartbeat keys with wrong prefix:
- Used: `v9:tick_reversal_15:heartbeat`
- Actual: `mems26:v9:tick_reversal_15:heartbeat`

The `redis_key` field on each stream class uses the `mems26:v9:` prefix.
The status check was missing this prefix.

Additionally, `LivePriceStream` doesn't extend `BaseV9Stream` and doesn't
write heartbeat keys — it publishes directly to the Event Bus. Added XLEN
check as proxy for live_price activity.

## Fix
Updated `_check_bridge()` in `backend/v9/api/v9/status.py`:
1. Corrected key prefix to `mems26:v9:<stream_name>:heartbeat`
2. Added XLEN check for `mems26:events:price.tick` as live_price proxy

## After Fix
```json
{"running": true, "streams_active": 11, "streams_total": 11, "errors": 0}
```
