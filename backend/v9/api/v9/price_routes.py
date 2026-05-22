"""Live price endpoint — reads Sierra DLL live_price.json (updated every ~200ms).

GET  /api/v9/live_price  — returns cached price (from POST) or falls back to file
POST /api/v9/live_price  — bridge pushes tick → cached + broadcast via WS

Per Sierra V9 Inputs LOCKED §1 (Input #11).
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["price"])

EXPORT_DIR = os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
LIVE_PRICE_PATH = os.path.join(EXPORT_DIR, "live_price.json")

# In-memory price cache — updated by bridge POST, read by GET + WS
_price_cache: dict = {}
_price_cache_ts: float = 0.0


class LivePriceTick(BaseModel):
    price: float
    ts: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    vol: Optional[float] = None


@router.post("/api/v9/live_price")
async def post_live_price(tick: LivePriceTick, request: Request):
    """Bridge pushes Sierra tick here — cache + broadcast to WS clients.

    Called by LivePriceStream every ~200ms. No auth required (local-only).
    """
    global _price_cache, _price_cache_ts
    now = time.time()
    ts_ms = int((tick.ts or now) * 1000)

    _price_cache = {
        "price": tick.price,
        "bid": tick.bid,
        "ask": tick.ask,
        "volume": tick.vol,
        "ts_utc": datetime.fromtimestamp(tick.ts or now, tz=timezone.utc).isoformat(),
        "age_ms": 0,
    }
    _price_cache_ts = now

    # Update health/streams push_count for live_price
    try:
        from backend.v9.api.v9.bars import _record_push
        _record_push("live_price")
    except Exception:
        pass

    # Broadcast to all connected WS clients via price_ws_manager
    try:
        from backend.v9.ws.manager import price_ws_manager
        await price_ws_manager.broadcast({
            "type": "price.tick",
            "data": {
                "price": tick.price,
                "bid": tick.bid,
                "ask": tick.ask,
                "last_size": tick.vol,
                "ts_ms": ts_ms,
                "source": "bridge.live_price",
            },
        })
    except Exception:
        pass

    return {"ok": True}


@router.get("/api/v9/live_price")
async def live_price():
    """Return current live price.

    Prefers in-memory cache (updated by bridge POST, <1s latency).
    Falls back to reading live_price.json directly if cache is stale (>5s).
    """
    now = time.time()
    cache_age_ms = int((now - _price_cache_ts) * 1000) if _price_cache_ts else None

    # Use cache if fresh (bridge is posting)
    if _price_cache and _price_cache_ts and (now - _price_cache_ts) < 5.0:
        return {**_price_cache, "age_ms": cache_age_ms, "source": "cache"}

    # Fallback: read file directly (bridge not posting yet)
    try:
        mtime = os.path.getmtime(LIVE_PRICE_PATH)
        age_ms = int((now - mtime) * 1000)
        with open(LIVE_PRICE_PATH, "r") as f:
            data = json.load(f)
        return {
            "price": data.get("price"),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "volume": data.get("vol") or data.get("volume"),
            "ts_utc": datetime.fromtimestamp(data.get("ts", 0), tz=timezone.utc).isoformat() if data.get("ts") else None,
            "age_ms": age_ms,
            "source": "file",
        }
    except FileNotFoundError:
        return {"error": "live_price.json not found", "price": None}
    except json.JSONDecodeError:
        return {"error": "live_price.json parse error", "price": None}
