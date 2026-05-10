"""V9 API: Trades + management log CRUD."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.v9.db.session import get_db
from backend.v9.db.models import V9Trade, V9TradeManagementLog
from backend.v9.api.v9.auth import verify_bridge_token
from backend.v9.api.v9.ws_manager import publish_event, CHANNEL_TRADES

router = APIRouter(prefix="/api/v9/trades", tags=["v9-trades"])


def _ts(unix_ts) -> Optional[datetime]:
    if unix_ts is None:
        return None
    return datetime.fromtimestamp(float(unix_ts), tz=timezone.utc)


class TradeIn(BaseModel):
    mode: str
    dominant_system: int
    direction: str
    entry_ts: Optional[float] = None
    entry_price: Optional[float] = None
    stop_initial: Optional[float] = None
    stop_final: Optional[float] = None
    t1_price: Optional[float] = None
    t1_filled_at: Optional[float] = None
    t2_price: Optional[float] = None
    t2_filled_at: Optional[float] = None
    t3_price: Optional[float] = None
    exit_ts: Optional[float] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_usd: Optional[float] = None
    pnl_r: Optional[float] = None
    outcome: Optional[str] = None
    quality_review: Optional[dict] = None
    sierra_bracket_id: Optional[str] = None
    context_json: Optional[dict] = None


class TradeLogIn(BaseModel):
    trade_id: int
    ts: Optional[float] = None
    action: str
    value: Optional[dict] = None


@router.post("")
def create_trade(
    trade: TradeIn,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    row = V9Trade(
        mode=trade.mode,
        dominant_system=trade.dominant_system,
        direction=trade.direction,
        entry_ts=_ts(trade.entry_ts),
        entry_price=trade.entry_price,
        stop_initial=trade.stop_initial,
        stop_final=trade.stop_final,
        t1_price=trade.t1_price,
        t1_filled_at=_ts(trade.t1_filled_at),
        t2_price=trade.t2_price,
        t2_filled_at=_ts(trade.t2_filled_at),
        t3_price=trade.t3_price,
        exit_ts=_ts(trade.exit_ts),
        exit_price=trade.exit_price,
        exit_reason=trade.exit_reason,
        pnl_usd=trade.pnl_usd,
        pnl_r=trade.pnl_r,
        outcome=trade.outcome,
        quality_review=trade.quality_review,
        sierra_bracket_id=trade.sierra_bracket_id,
        context_json=trade.context_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    publish_event(CHANNEL_TRADES, {
        "trade_id": row.id, "mode": row.mode,
        "direction": row.direction, "system": row.dominant_system,
    })
    return {"ok": True, "trade_id": row.id}


@router.get("")
def get_trades(
    mode: Optional[str] = None,
    dominant_system: Optional[int] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    q = db.query(V9Trade)
    if mode:
        q = q.filter(V9Trade.mode == mode)
    if dominant_system is not None:
        q = q.filter(V9Trade.dominant_system == dominant_system)
    rows = q.order_by(V9Trade.entry_ts.desc()).limit(limit).all()
    return {"trades": [
        {"id": r.id, "mode": r.mode, "system": r.dominant_system,
         "direction": r.direction,
         "entry_ts": r.entry_ts.isoformat() if r.entry_ts else None,
         "entry_price": r.entry_price,
         "exit_ts": r.exit_ts.isoformat() if r.exit_ts else None,
         "exit_price": r.exit_price, "exit_reason": r.exit_reason,
         "pnl_usd": r.pnl_usd, "pnl_r": r.pnl_r, "outcome": r.outcome,
         "sierra_bracket_id": r.sierra_bracket_id}
        for r in rows
    ]}


@router.get("/{trade_id}")
def get_trade(
    trade_id: int,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    trade = db.get(V9Trade,trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    logs = db.query(V9TradeManagementLog).filter(
        V9TradeManagementLog.trade_id == trade_id
    ).order_by(V9TradeManagementLog.ts).all()
    return {
        "trade": {
            "id": trade.id, "mode": trade.mode,
            "system": trade.dominant_system, "direction": trade.direction,
            "entry_ts": trade.entry_ts.isoformat() if trade.entry_ts else None,
            "entry_price": trade.entry_price,
            "stop_initial": trade.stop_initial, "stop_final": trade.stop_final,
            "t1_price": trade.t1_price,
            "t1_filled_at": trade.t1_filled_at.isoformat() if trade.t1_filled_at else None,
            "t2_price": trade.t2_price,
            "t2_filled_at": trade.t2_filled_at.isoformat() if trade.t2_filled_at else None,
            "t3_price": trade.t3_price,
            "exit_ts": trade.exit_ts.isoformat() if trade.exit_ts else None,
            "exit_price": trade.exit_price, "exit_reason": trade.exit_reason,
            "pnl_usd": trade.pnl_usd, "pnl_r": trade.pnl_r,
            "outcome": trade.outcome,
            "quality_review": trade.quality_review,
            "sierra_bracket_id": trade.sierra_bracket_id,
            "context_json": trade.context_json,
        },
        "management_log": [
            {"id": l.id, "ts": l.ts.isoformat(), "action": l.action, "value": l.value}
            for l in logs
        ],
    }


@router.post("/log")
def add_trade_log(
    entry: TradeLogIn,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    trade = db.get(V9Trade,entry.trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    row = V9TradeManagementLog(
        trade_id=entry.trade_id,
        ts=_ts(entry.ts) or datetime.now(timezone.utc),
        action=entry.action,
        value=entry.value,
    )
    db.add(row)
    db.commit()
    return {"ok": True, "log_id": row.id}
