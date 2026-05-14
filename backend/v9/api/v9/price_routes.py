"""Live price endpoint — reads Sierra DLL live_price.json (updated every ~200ms).

Per Sierra V9 Inputs LOCKED §1 (Input #11).
Direct file read for lowest latency (same machine).
"""
import json
import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(tags=["price"])

EXPORT_DIR = os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
LIVE_PRICE_PATH = os.path.join(EXPORT_DIR, "live_price.json")


@router.get("/api/v9/live_price")
async def live_price():
    """Return current live price from Sierra DLL export.

    File: live_price.json (written every ~200ms by DLL)
    Shape: { price, bid, ask, volume, ts_utc, age_ms }
    """
    try:
        mtime = os.path.getmtime(LIVE_PRICE_PATH)
        age_ms = int((time.time() - mtime) * 1000)

        with open(LIVE_PRICE_PATH, "r") as f:
            data = json.load(f)

        return {
            "price": data.get("price"),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "volume": data.get("vol") or data.get("volume"),
            "ts_utc": datetime.fromtimestamp(data.get("ts", 0), tz=timezone.utc).isoformat() if data.get("ts") else None,
            "age_ms": age_ms,
        }
    except FileNotFoundError:
        return {"error": "live_price.json not found", "price": None}
    except json.JSONDecodeError:
        return {"error": "live_price.json parse error", "price": None}
