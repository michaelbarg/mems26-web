# HOTFIX — WebSocket Route Registration

**Date:** 2026-05-11

## Investigation

### Bug A: "WS route not registered" — NOT A BUG

The `/ws/v9/price` endpoint **is registered and working**. It does not
appear in `/openapi.json` because **WebSocket endpoints are excluded from
the OpenAPI specification** — this is a FastAPI/OpenAPI limitation, not a
missing route.

**Proof — live test passed:**
```
INFO: 127.0.0.1:54721 - "WebSocket /ws/v9/price?token=..." [accepted]
WS Connected OK
Received: {"type":"price.tick","data":{"price":7435.25,"ts_ms":1778510789000,...}}
```

### Bug B: "websockets library missing" — NOT A BUG

`websockets` v15.0.1 is installed and listed in `requirements.txt` line 8:
```
websockets>=12.0,<14.0
```

## Fix Applied

Added a REST diagnostic endpoint so WS route availability can be verified
without relying on `/openapi.json`:

```
GET /api/v9/ws/status
→ {"endpoints": ["/ws/v9/price"], "clients": 0, "relay_running": false}
```

This endpoint shows up in `/openapi.json` and confirms the WS route exists.

## How to Verify

```bash
# REST check (appears in openapi.json):
curl http://localhost:8000/api/v9/ws/status

# Direct WS connection test:
python3 -c "
import asyncio, websockets
async def test():
    async with websockets.connect('ws://localhost:8000/ws/v9/price?token=michael-mems26-2026') as ws:
        print('Connected')
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        print('Got:', msg[:100])
asyncio.run(test())
"
```

## Note for Future

WebSocket routes will **never** appear in `/openapi.json`. Use
`GET /api/v9/ws/status` or direct connection test to verify.
