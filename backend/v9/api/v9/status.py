"""GET /api/v9/status — 5-layer health dashboard.

Returns JSON with: sierra, bridge, event_bus, ws, frontend.
Used by UAT scripts and humans. Target: < 1s response time.
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger("mems26.status")
router = APIRouter(tags=["v9-status"])

LIVE_PRICE_JSON = Path(
    os.getenv("V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export")
) / "live_price.json"

REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")


def _redis_cmd(args: list):
    """Quick Redis command via Upstash REST."""
    if not REDIS_URL or not REDIS_TOKEN:
        return None
    try:
        body = json.dumps(args).encode()
        req = urllib.request.Request(
            REDIS_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {REDIS_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode()).get("result")
    except Exception:
        return None


def _check_sierra() -> dict:
    """Check if Sierra Chart is writing live_price.json."""
    if not LIVE_PRICE_JSON.exists():
        return {"writing": False, "last_write_age_s": -1, "status": "file_missing"}
    mtime = LIVE_PRICE_JSON.stat().st_mtime
    age = time.time() - mtime
    writing = age < 10  # Consider "writing" if updated within 10s
    status = "active" if writing else "stale"
    return {"writing": writing, "last_write_age_s": round(age, 1), "status": status}


def _check_bridge() -> dict:
    """Check bridge status via Redis heartbeat keys.

    BaseV9Stream writes heartbeat to {redis_key}:heartbeat every 30s.
    redis_key format: mems26:v9:<stream_name>
    LivePriceStream publishes to Event Bus directly (no heartbeat key),
    so we also check the price stream XLEN as a proxy.
    """
    # Actual redis_key values from bridge/v9_streams/*.py
    stream_keys = [
        "mems26:v9:tick_reversal_15",
        "mems26:v9:tick_reversal_12",
        "mems26:v9:footprint",
        "mems26:v9:volume_profile",
        "mems26:v9:imbalance",
        "mems26:v9:stacked_imbalance",
        "mems26:v9:cumulative_delta",
        "mems26:v9:woodies",
        "mems26:v9:tpo",
        "mems26:v9:bars_5min",
    ]
    active = 0
    errors = 0
    for key in stream_keys:
        hb = _redis_cmd(["GET", f"{key}:heartbeat"])
        if hb is not None:
            try:
                age = time.time() - int(hb)
                if age < 120:
                    active += 1
            except (ValueError, TypeError):
                errors += 1

    # LivePriceStream check: XLEN of price.tick stream as proxy
    price_xlen = _redis_cmd(["XLEN", "mems26:events:price.tick"])
    live_price_active = price_xlen is not None and int(price_xlen) > 0

    if live_price_active:
        active += 1

    total = len(stream_keys) + 1  # +1 for live_price

    return {
        "running": active > 0,
        "streams_active": active,
        "streams_total": total,
        "errors": errors,
    }


def _check_event_bus() -> dict:
    """Check Event Bus Redis Streams."""
    xlen = _redis_cmd(["XLEN", "mems26:events:price.tick"])
    reachable = xlen is not None
    return {
        "reachable": reachable,
        "xlen_price_tick": int(xlen) if xlen is not None else 0,
    }


def _check_ws() -> dict:
    """Check WebSocket layer status."""
    try:
        from backend.v9.ws.manager import price_ws_manager
        clients = len(price_ws_manager._clients)
        relay = (
            price_ws_manager._relay_task is not None
            and not price_ws_manager._relay_task.done()
        ) if price_ws_manager._relay_task else False
    except Exception:
        clients = 0
        relay = False

    return {
        "endpoints": ["/ws/v9/price"],
        "clients": clients,
        "relay_running": relay,
    }


def _check_frontend() -> dict:
    """Check if frontend is reachable on port 3000."""
    try:
        req = urllib.request.Request("http://localhost:3000", method="HEAD")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return {"reachable": True, "status": resp.status}
    except Exception:
        return {"reachable": False, "status": 0}


@router.get("/api/v9/status")
def system_status():
    """5-layer health dashboard for MEMS26."""
    return {
        "ts": time.time(),
        "sierra": _check_sierra(),
        "bridge": _check_bridge(),
        "event_bus": _check_event_bus(),
        "ws": _check_ws(),
        "frontend": _check_frontend(),
    }
