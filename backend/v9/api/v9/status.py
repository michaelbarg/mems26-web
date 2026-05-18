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
STATUS_REDIS_TIMEOUT_S = float(os.getenv("V9_STATUS_REDIS_TIMEOUT_S", "0.2"))
STATUS_BRIDGE_BUDGET_S = float(os.getenv("V9_STATUS_BRIDGE_BUDGET_S", "0.8"))


def _redis_cmd(args: list, timeout: float = STATUS_REDIS_TIMEOUT_S):
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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
    started = time.monotonic()
    active = 0
    errors = 0
    checked = 0
    partial = False
    for key in stream_keys:
        if time.monotonic() - started > STATUS_BRIDGE_BUDGET_S:
            partial = True
            break
        hb = _redis_cmd(["GET", f"{key}:heartbeat"])
        checked += 1
        if hb is not None:
            try:
                age = time.time() - int(hb)
                if age < 120:
                    active += 1
            except (ValueError, TypeError):
                errors += 1

    # LivePriceStream check: XLEN of price.tick stream as proxy
    price_xlen = None
    live_price_active = False
    if time.monotonic() - started <= STATUS_BRIDGE_BUDGET_S:
        price_xlen = _redis_cmd(["XLEN", "mems26:events:price.tick"])
        live_price_active = price_xlen is not None and int(price_xlen) > 0
    else:
        partial = True

    if live_price_active:
        active += 1

    total = len(stream_keys) + 1  # +1 for live_price

    return {
        "running": active > 0,
        "streams_active": active,
        "streams_total": total,
        "streams_checked": checked + (1 if price_xlen is not None else 0),
        "partial": partial,
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


def _check_audit() -> dict:
    """Check audit consumer status."""
    try:
        from backend.v9.audit.runner import get_consumer
        consumer = get_consumer()
        if consumer and consumer.is_running:
            lag = time.time() - consumer.last_write_ts if consumer.last_write_ts > 0 else -1
            return {
                "running": True,
                "events_written": consumer.events_written,
                "events_skipped": consumer.events_skipped,
                "errors": consumer.errors,
                "lag_seconds": round(lag, 1),
                "events_per_minute": round(consumer.events_per_minute, 1),
            }
    except Exception:
        pass
    # Fallback: check if audit_events table has recent rows
    try:
        from backend.v9.db.session import SessionLocal
        from backend.v9.db.models.audit import AuditEvent
        from sqlalchemy import func
        db = SessionLocal()
        count = db.query(func.count(AuditEvent.id)).scalar() or 0
        db.close()
        return {"running": False, "events_in_db": count}
    except Exception:
        return {"running": False, "events_in_db": 0}


def _check_day_type() -> dict:
    """Check Day Type system status."""
    try:
        from backend.v9.systems.day_type.api import _get_engine
        from backend.v9.systems.day_type.schemas import BarInput
        engine = _get_engine()
        state = engine._build_state(
            BarInput(ts=0, session_min=0, open=0, high=0, low=0, close=0)
        )
        dt_val = state.day_type.value if hasattr(state.day_type, 'value') else str(state.day_type)
        status_val = str(state.lock_state)
        return {
            "running": True,
            "current_type": dt_val,
            "status": status_val,
            "confidence": state.confidence,
            "stage": state.stage.value if hasattr(state.stage, 'value') else str(state.stage),
        }
    except Exception:
        return {"running": False, "current_type": None}


def _check_hydration() -> dict:
    """Check hydration status for bar ingestion + systems (D-077)."""
    result = {"bar_ingestion": {"running": False, "bars_in_db": 0}, "systems": {}}
    try:
        from backend.v9.services.bar_ingestion import bar_ingestion_service
        result["bar_ingestion"] = {
            "running": bar_ingestion_service.is_running,
            "bars_in_db": bar_ingestion_service.bars_in_db,
        }
    except Exception:
        pass
    try:
        from backend.v9.systems.day_type.hydration import hydrate_day_type
        hr = hydrate_day_type()
        result["systems"]["day_type"] = {
            "hydrated": hr.success,
            "reached_state": hr.reached_state,
            "confidence": hr.confidence,
            "notes": hr.notes,
        }
    except Exception:
        result["systems"]["day_type"] = {"hydrated": False, "error": "import_failed"}
    try:
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem
        fm = FiveMinSystem()
        hr = fm.hydrate()
        state = fm.get_state()
        result["systems"]["five_min"] = {
            "hydrated": hr.success,
            "reached_state": hr.reached_state,
            "mode": state.get("mode"),
            "notes": hr.notes,
        }
    except Exception:
        result["systems"]["five_min"] = {"hydrated": False, "error": "import_failed"}
    return result


def _check_session() -> dict:
    """Current trading session via SessionClassifier (D-083)."""
    try:
        from backend.v9.common.session_classifier import SessionClassifier
        sc = SessionClassifier()
        info = sc.classify()
        return {
            "current": info.session.value,
            "et_time": info.et_time.isoformat(),
            "is_trading_active": info.is_trading_active,
            "is_globex": sc.is_globex(info.session),
            "is_cash": sc.is_cash(info.session),
        }
    except Exception:
        return {"current": "UNKNOWN", "error": "classifier_failed"}


def _check_bar_router() -> dict:
    """BarRouter stats (D1.7)."""
    try:
        from backend.v9.api.v9.bars import _bar_router
        if _bar_router:
            return _bar_router.get_stats()
    except Exception:
        pass
    return {"available": False}


@router.get("/api/v9/status")
def system_status():
    """10-layer health dashboard for MEMS26."""
    import os
    trading_mode = os.getenv("MEMS26_MODE", "shadow")
    return {
        "ts": time.time(),
        "mode": trading_mode,
        "session": _check_session(),
        "sierra": _check_sierra(),
        "bridge": _check_bridge(),
        "event_bus": _check_event_bus(),
        "ws": _check_ws(),
        "frontend": _check_frontend(),
        "audit": _check_audit(),
        "day_type": _check_day_type(),
        "hydration": _check_hydration(),
        "bar_router": _check_bar_router(),
        "historical_replay": _check_historical_replay(),
    }


def _check_historical_replay() -> dict:
    """HistoricalReplay stats (D2.3)."""
    try:
        # Try module-level import from where it's stored
        # The replay is stored on app.state but we can't access it here without request
        # Fallback: check if the module is importable and return basic info
        from backend.v9.services.historical_replay import HistoricalReplay
        return {"available": True, "note": "stats available after restart via /api/v9/status with request context"}
    except Exception:
        return {"available": False}
