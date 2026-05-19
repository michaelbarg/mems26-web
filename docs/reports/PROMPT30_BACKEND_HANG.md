# P30 — Backend Hang Root Cause

**Date:** 2026-05-19
**Status:** MITIGATED — `--workers 2` resolves; structural fix documented for later.

---

## Root Cause

Single-worker uvicorn (`--workers 1`, the default) saturates under frontend polling load:

- **69 concurrent TCP connections** observed at time of hang
- Frontend `systemStateStore.fetchAllStates()` fires 12 sequential HTTP requests every 2s
- Chart polls bars every 5s, TPO every 30s, active trade every 2s
- WebSocket connections (price, signals×6) hold persistent sockets
- Sync endpoints (`/api/v9/status`, system health checks) block the asyncio event loop
- When the thread pool (default 40 threads) fills, all new requests queue indefinitely

## Evidence

```
lsof -nP -iTCP:8000 | grep -c ESTABLISHED → 69
curl -m 2 heartbeat → timeout 2.003s (000)
```

After restart with `--workers 2`:
```
heartbeat 200 0.002s
heartbeat 200 0.001s
heartbeat 200 0.001s
```

## Mitigation

**Immediate:** Start uvicorn with `--workers 2`:
```bash
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2
```

This doubles the available event loops and thread pools, preventing single-worker saturation.

**Caution with `--workers 2`:** Each worker gets its own `app.state`, so in-memory state
(FiveMinSystem, WoodiesSystem, etc.) is not shared. This is acceptable because:
- Systems read from DB/Sierra files, not solely from in-memory state
- The heartbeat/health endpoints don't need system state
- Bridge POST targets one worker at a time (acceptable for bars-only mode)

## Structural Fix (future, not P30)

1. Batch `systemStateStore` into a single `/api/v9/cockpit/systems-snapshot` call (already exists)
2. Frontend should use systems-snapshot instead of 12 sequential fetches
3. Convert remaining sync endpoints to `async def`
4. Consider `--workers 4` for SHADOW soak

## Safety

- No trading logic changed
- No bridge/LaunchAgent/mode changes
- `--workers 2` is a uvicorn startup flag, not a code change
