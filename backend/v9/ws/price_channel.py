"""WebSocket endpoint: /ws/v9/price — real-time price ticks from Event Bus."""

import asyncio
import logging
import os
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from .manager import price_ws_manager, HEARTBEAT_INTERVAL

logger = logging.getLogger("mems26.ws")
router = APIRouter(tags=["v9-ws-price"])

BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")


@router.get("/api/v9/ws/status", tags=["v9-ws-price"])
def ws_status():
    """Diagnostic: shows WS endpoint status (WebSocket routes don't appear in /openapi.json)."""
    return {
        "endpoints": ["/ws/v9/price"],
        "clients": len(price_ws_manager._clients),
        "relay_running": (
            price_ws_manager._relay_task is not None
            and not price_ws_manager._relay_task.done()
        ) if price_ws_manager._relay_task else False,
    }


@router.websocket("/ws/v9/price")
async def ws_price(
    websocket: WebSocket,
    token: str = Query(""),
):
    """Real-time price tick stream from the Event Bus.

    Clients connect, receive price.tick events as they arrive.
    Heartbeat sent every 30s to keep the connection alive.
    """
    if token != BRIDGE_TOKEN:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await price_ws_manager.connect(websocket)

    # Heartbeat task
    async def heartbeat():
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await websocket.send_json({"type": "heartbeat", "ts": time.time()})
        except Exception:
            pass

    hb_task = asyncio.create_task(heartbeat())

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "ts": time.time()})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        hb_task.cancel()
        price_ws_manager.disconnect(websocket)
