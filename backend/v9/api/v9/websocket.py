"""V9 WebSocket endpoints for real-time Dashboard feeds."""

import asyncio
import os
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from backend.v9.db.session import SessionLocal
from backend.v9.db.models import (
    V9Bar5Min, V9BarTickReversal, V9Bar30MinWoodies,
    V9SystemMarker, V9SystemSignal, V9Trade, V9AccountStatus, V9TpoBar,
)
from backend.v9.api.v9.ws_manager import (
    manager, CHANNEL_BARS_5MIN, CHANNEL_BARS_TICK_REVERSAL,
    CHANNEL_BARS_WOODIES, CHANNEL_BARS_TPO, CHANNEL_MARKERS,
    CHANNEL_SIGNALS, CHANNEL_TRADES, CHANNEL_ACCOUNT, CHANNEL_LEVELS,
    HEARTBEAT_INTERVAL,
)

router = APIRouter(tags=["v9-websocket"])

BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "michael-mems26-2026")


def _verify_ws_token(token: str) -> bool:
    """Verify token passed as query parameter."""
    return token == BRIDGE_TOKEN


def _get_db() -> Session:
    return SessionLocal()


# ─── Snapshot helpers ───────────────────────────────────────

def _snapshot_bars_5min(db: Session, limit: int = 50) -> list:
    rows = db.query(V9Bar5Min).order_by(V9Bar5Min.ts.desc()).limit(limit).all()
    return [
        {"id": r.id, "ts": r.ts.isoformat(), "o": r.open, "h": r.high,
         "l": r.low, "c": r.close, "vol": r.volume,
         "poc_vol": r.poc_vol, "vah": r.vah, "val": r.val,
         "cumulative_delta": r.cumulative_delta}
        for r in reversed(rows)
    ]


def _snapshot_tick_reversal(db: Session, limit: int = 50) -> list:
    rows = db.query(V9BarTickReversal).order_by(
        V9BarTickReversal.ts.desc()
    ).limit(limit).all()
    return [
        {"id": r.id, "ts": r.ts.isoformat(), "tick_size": r.tick_size,
         "o": r.open, "h": r.high, "l": r.low, "c": r.close,
         "vol": r.volume, "delta": r.delta, "dir": r.direction}
        for r in reversed(rows)
    ]


def _snapshot_woodies(db: Session, limit: int = 30) -> list:
    rows = db.query(V9Bar30MinWoodies).order_by(
        V9Bar30MinWoodies.ts.desc()
    ).limit(limit).all()
    return [
        {"id": r.id, "ts": r.ts.isoformat(),
         "o": r.open, "h": r.high, "l": r.low, "c": r.close,
         "cci_14": r.cci_14, "cci_6_tcci": r.cci_6_tcci,
         "trend_state": r.trend_state, "zlr_detected": r.zlr_detected,
         "zlr_direction": r.zlr_direction}
        for r in reversed(rows)
    ]


def _snapshot_markers(db: Session, system_id: int, limit: int = 50) -> list:
    rows = db.query(V9SystemMarker).filter(
        V9SystemMarker.system_id == system_id
    ).order_by(V9SystemMarker.ts.desc()).limit(limit).all()
    return [
        {"id": r.id, "ts": r.ts.isoformat(), "system_id": r.system_id,
         "type": r.marker_type, "price": r.price,
         "color": r.color, "label": r.label}
        for r in reversed(rows)
    ]


def _snapshot_signals(db: Session, system_id: int, limit: int = 20) -> list:
    rows = db.query(V9SystemSignal).filter(
        V9SystemSignal.system_id == system_id
    ).order_by(V9SystemSignal.ts.desc()).limit(limit).all()
    return [
        {"id": r.id, "ts": r.ts.isoformat(), "system_id": r.system_id,
         "classification": r.classification, "direction": r.direction,
         "confidence": r.confidence}
        for r in reversed(rows)
    ]


def _snapshot_trades(db: Session, limit: int = 20) -> list:
    rows = db.query(V9Trade).order_by(V9Trade.entry_ts.desc()).limit(limit).all()
    return [
        {"id": r.id, "mode": r.mode, "system": r.dominant_system,
         "direction": r.direction,
         "entry_ts": r.entry_ts.isoformat() if r.entry_ts else None,
         "entry_price": r.entry_price,
         "exit_ts": r.exit_ts.isoformat() if r.exit_ts else None,
         "pnl_usd": r.pnl_usd, "outcome": r.outcome}
        for r in reversed(rows)
    ]


def _snapshot_account(db: Session) -> dict:
    row = db.query(V9AccountStatus).order_by(
        V9AccountStatus.ts.desc()
    ).first()
    if not row:
        return {"daily_pnl": 0, "trade_count": 0, "margin_used_pct": 0}
    return {
        "mode": row.mode, "daily_pnl": row.daily_pnl,
        "trade_count": row.trade_count, "margin_used_pct": row.margin_used_pct,
        "ts": row.ts.isoformat(),
    }


def _snapshot_levels(db: Session, limit: int = 100) -> list:
    rows = db.query(V9TpoBar).order_by(V9TpoBar.ts.desc()).limit(limit).all()
    return [
        {"id": r.id, "ts": r.ts.isoformat(), "letter": r.letter,
         "price": r.price, "level": r.level, "period_id": r.period_id}
        for r in reversed(rows)
    ]


# ─── WebSocket endpoints ───────────────────────────────────

async def _ws_handler(
    websocket: WebSocket,
    channel: str,
    snapshot_fn,
    token: str,
):
    """Generic WS handler: auth → snapshot → subscribe → heartbeat."""
    if not _verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, channel)

    # Send initial snapshot
    db = _get_db()
    try:
        snapshot = snapshot_fn(db)
        await websocket.send_json({
            "type": "snapshot",
            "channel": channel,
            "data": snapshot,
            "ts": time.time(),
        })
    finally:
        db.close()

    # Start heartbeat in background
    heartbeat_task = asyncio.create_task(manager.send_heartbeat(websocket))

    try:
        while True:
            # Keep connection alive, receive pings/messages from client
            data = await websocket.receive_text()
            # Client can send "ping" to get immediate pong
            if data == "ping":
                await websocket.send_json({"type": "pong", "ts": time.time()})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket, channel)


@router.websocket("/ws/v9/bars/5min")
async def ws_bars_5min(
    websocket: WebSocket,
    token: str = Query(""),
):
    await _ws_handler(websocket, CHANNEL_BARS_5MIN, _snapshot_bars_5min, token)


@router.websocket("/ws/v9/bars/tick_reversal")
async def ws_bars_tick_reversal(
    websocket: WebSocket,
    token: str = Query(""),
):
    await _ws_handler(
        websocket, CHANNEL_BARS_TICK_REVERSAL, _snapshot_tick_reversal, token
    )


@router.websocket("/ws/v9/bars/woodies")
async def ws_bars_woodies(
    websocket: WebSocket,
    token: str = Query(""),
):
    await _ws_handler(websocket, CHANNEL_BARS_WOODIES, _snapshot_woodies, token)


@router.websocket("/ws/v9/bars/tpo")
async def ws_bars_tpo(
    websocket: WebSocket,
    token: str = Query(""),
):
    await _ws_handler(websocket, CHANNEL_BARS_TPO, _snapshot_levels, token)


@router.websocket("/ws/v9/markers/{system_id}")
async def ws_markers(
    websocket: WebSocket,
    system_id: int,
    token: str = Query(""),
):
    channel = CHANNEL_MARKERS.format(system_id=system_id)
    await _ws_handler(
        websocket, channel,
        lambda db: _snapshot_markers(db, system_id),
        token,
    )


@router.websocket("/ws/v9/signals/{system_id}")
async def ws_signals(
    websocket: WebSocket,
    system_id: int,
    token: str = Query(""),
):
    channel = CHANNEL_SIGNALS.format(system_id=system_id)
    await _ws_handler(
        websocket, channel,
        lambda db: _snapshot_signals(db, system_id),
        token,
    )


@router.websocket("/ws/v9/trades")
async def ws_trades(
    websocket: WebSocket,
    token: str = Query(""),
):
    await _ws_handler(websocket, CHANNEL_TRADES, _snapshot_trades, token)


@router.websocket("/ws/v9/account")
async def ws_account(
    websocket: WebSocket,
    token: str = Query(""),
):
    await _ws_handler(
        websocket, CHANNEL_ACCOUNT,
        lambda db: _snapshot_account(db),
        token,
    )


@router.websocket("/ws/v9/levels")
async def ws_levels(
    websocket: WebSocket,
    token: str = Query(""),
):
    await _ws_handler(websocket, CHANNEL_LEVELS, _snapshot_levels, token)
