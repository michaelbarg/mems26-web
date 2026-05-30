"""V9 API: Trades + management log CRUD."""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.v9.db.session import get_db
from backend.v9.db.models import V9Trade, V9TradeManagementLog
from backend.v9.api.v9.auth import verify_bridge_token
from backend.v9.api.v9.ws_manager import publish_event, CHANNEL_TRADES
from backend.v9.services.trade_context import (
    extract_trade_display,
    extract_trade_systems_panel,
    extract_system_agreement,
    extract_trade_insight,
    compute_trade_pnl,
    _stop_initial_from_trade,
)
from backend.v9.services.trade_excursion import compute_trade_excursion
from backend.v9.services.trade_manager.state_machine import TradeState, InvalidTransition

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v9/trades", tags=["v9-trades"])


def _ts(unix_ts) -> Optional[datetime]:
    if unix_ts is None:
        return None
    return datetime.fromtimestamp(float(unix_ts), tz=timezone.utc)


class TradeIn(BaseModel):
    mode: str
    dominant_system: Optional[int] = None
    firing_system: Optional[int] = None
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


class TradeExitIn(BaseModel):
    """Manual close from cockpit — optional mark-to-market exit price."""
    exit_price: Optional[float] = None
    reason: str = "manual"


def _trade_manager(request: Request):
    tm = getattr(request.app.state, "trade_manager", None)
    if tm is None:
        raise HTTPException(status_code=503, detail="TradeManager not available")
    return tm


def _stop_note(r: V9Trade) -> Optional[str]:
    """How stop relates to entry after management (Smart BE overwrites stop)."""
    if r.entry_price is None or r.stop is None:
        return None
    if r.t1_hit_ts is not None and abs(float(r.stop) - float(r.entry_price)) < 0.5:
        return "BE@entry"
    return "initial"


def _stop_issue(r: V9Trade) -> Optional[str]:
    """UAT flag when T1 hit but stop was not moved to breakeven."""
    if r.t1_hit_ts is None or r.entry_price is None or r.stop is None:
        return None
    if abs(float(r.stop) - float(r.entry_price)) < 0.5:
        return None
    return "T1_NO_BE"


def _trade_list_row(r: V9Trade, db: Optional[Session] = None) -> dict:
    """Shared fields for trades table / recent strip."""
    row = {
        "id": r.id,
        "mode": r.mode,
        "system": r.firing_system,
        "direction": r.direction,
        "state": r.state,
        "entry_ts": r.entry_ts.isoformat() if r.entry_ts else None,
        "entry_price": r.entry_price,
        "stop": r.stop,
        "stop_initial": _stop_initial_from_trade(r),
        "stop_note": _stop_note(r),
        "stop_issue": _stop_issue(r),
        "systems_agreement": extract_system_agreement(r),
        "t1": r.t1,
        "t2": r.t2,
        "t3": r.t3,
        "t1_hit": r.t1_hit_ts is not None,
        "t2_hit": r.t2_hit_ts is not None,
        "t3_hit": r.t3_hit_ts is not None,
        "exit_ts": r.exit_ts.isoformat() if r.exit_ts else None,
        "exit_price": r.exit_price,
        "exit_reason": r.exit_reason,
        "pnl_usd": r.pnl_usd,
        "pnl_r": r.pnl_r,
        "outcome": r.outcome,
        "sierra_bracket_id": r.sierra_bracket_id,
    }
    row.update(extract_trade_display(r))
    pnl = compute_trade_pnl(r)
    row["pnl_usd"] = pnl["pnl_usd"]
    row["pnl_r"] = pnl["pnl_r"]
    row["pnl_mode"] = pnl["pnl_mode"]
    row["contracts_pnl"] = pnl["contracts_pnl"]
    if db is not None:
        row.update(compute_trade_excursion(r, db))
    return row


@router.post("/{trade_id}/exit")
def exit_trade(
    trade_id: int,
    request: Request,
    body: TradeExitIn = TradeExitIn(),
):
    """Manual close — wires cockpit Exit button to TradeManager.close_trade."""
    tm = _trade_manager(request)
    try:
        trade = tm._get_trade(trade_id)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")

    if trade.state == TradeState.CLOSED.value:
        return {
            "ok": True,
            "trade_id": trade_id,
            "already_closed": True,
            "state": trade.state,
            "exit_reason": trade.exit_reason,
            "pnl_usd": trade.pnl_usd,
            "outcome": trade.outcome,
        }

    if body.exit_price is not None:
        trade.exit_price = float(body.exit_price)
    elif trade.exit_price is None and trade.entry_price is not None:
        trade.exit_price = float(trade.entry_price)

    try:
        tm.close_trade(trade_id, body.reason)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("[trades] exit failed trade_id=%s: %s", trade_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        tm._db.commit()
    except Exception as exc:
        logger.error("[trades] exit commit failed trade_id=%s: %s", trade_id, exc)
        raise HTTPException(status_code=500, detail="Failed to persist trade close") from exc

    trade = tm._get_trade(trade_id)
    publish_event(CHANNEL_TRADES, {
        "trade_id": trade.id,
        "mode": trade.mode,
        "direction": trade.direction,
        "system": trade.firing_system,
        "state": trade.state,
        "exit_reason": trade.exit_reason,
        "pnl_usd": trade.pnl_usd,
        "outcome": trade.outcome,
    })
    return {
        "ok": True,
        "trade_id": trade_id,
        "state": trade.state,
        "exit_reason": trade.exit_reason,
        "exit_price": trade.exit_price,
        "pnl_usd": trade.pnl_usd,
        "pnl_r": trade.pnl_r,
        "outcome": trade.outcome,
    }


@router.get("/active")
def get_active_trade(db: Session = Depends(get_db)):
    """Return the current active trade with C1/C2/C3 contract details.

    Derives per-contract status from t1/t2/t3 + hit timestamps.
    MES: 1 point = $5 per contract.
    """
    trade = (
        db.query(V9Trade)
        .filter(V9Trade.state.in_(["FILLED", "PARTIAL", "OPEN"]))
        .order_by(V9Trade.entry_ts.desc())
        .first()
    )
    if not trade:
        return None

    entry = trade.entry_price or 0
    stop = trade.stop or 0
    is_long = trade.direction == "LONG"
    mul = 1.0 if is_long else -1.0
    risk_pts = abs(entry - stop) if entry and stop else 1.0
    risk_usd = risk_pts * 5.0  # MES $5/point

    def _contract(label, target, hit_ts, smart_be=False):
        status = "HIT_TARGET" if hit_ts else ("HIT_STOP" if trade.stop_hit_ts else "OPEN")
        if hit_ts:
            pnl = (target - entry) * mul * 5.0
        elif trade.stop_hit_ts:
            pnl = (stop - entry) * mul * 5.0
        else:
            pnl = 0.0
        r = pnl / risk_usd if risk_usd > 0 else 0.0
        return {
            "id": label,
            "target_price": target,
            "status": status,
            "pnl": round(pnl, 2),
            "r": round(r, 2),
            "exit_ts": hit_ts.isoformat() if hit_ts else None,
            "smart_be": smart_be,
        }

    contracts = [
        _contract("C1", trade.t1, trade.t1_hit_ts),
        _contract("C2", trade.t2, trade.t2_hit_ts,
                  smart_be=(trade.t1_hit_ts is not None and trade.t2_hit_ts is None)),
        _contract("C3", trade.t3, trade.t3_hit_ts),
    ]

    hits = sum(1 for c in contracts if c["status"] == "HIT_TARGET")
    total_pnl = sum(c["pnl"] for c in contracts)
    total_r = sum(c["r"] for c in contracts)

    display = extract_trade_display(trade)
    systems_panel = extract_trade_systems_panel(trade)
    return {
        "trade_id": trade.id,
        "direction": trade.direction,
        "entry_price": entry,
        "entry_ts": trade.entry_ts.isoformat() if trade.entry_ts else None,
        "stop_price": stop,
        "state": trade.state,
        "firing_system": trade.firing_system,
        "contracts": contracts,
        "hits": hits,
        "total_pnl": round(total_pnl, 2),
        "total_r": round(total_r, 2),
        "summary": f"{hits}/3 hit",
        **display,
        **systems_panel,
    }


@router.post("")
def create_trade(
    trade: TradeIn,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    firing_system = trade.firing_system or trade.dominant_system
    if firing_system is None:
        raise HTTPException(status_code=422, detail="firing_system or dominant_system is required")

    row = V9Trade(
        mode=trade.mode,
        firing_system=firing_system,
        direction=trade.direction,
        entry_ts=_ts(trade.entry_ts),
        entry_price=trade.entry_price,
        stop=trade.stop_initial or trade.stop_final,
        t1=trade.t1_price,
        t1_hit_ts=_ts(trade.t1_filled_at),
        t2=trade.t2_price,
        t2_hit_ts=_ts(trade.t2_filled_at),
        t3=trade.t3_price,
        exit_ts=_ts(trade.exit_ts),
        exit_price=trade.exit_price,
        exit_reason=trade.exit_reason,
        pnl_usd=trade.pnl_usd,
        pnl_r=trade.pnl_r,
        outcome=trade.outcome,
        quality=trade.quality_review,
        sierra_bracket_id=trade.sierra_bracket_id,
        cross_context=trade.context_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    publish_event(CHANNEL_TRADES, {
        "trade_id": row.id, "mode": row.mode,
        "direction": row.direction, "system": row.firing_system,
    })
    return {"ok": True, "trade_id": row.id}


@router.get("")
def get_trades(
    mode: Optional[str] = None,
    dominant_system: Optional[int] = None,
    firing_system: Optional[int] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    q = db.query(V9Trade).filter(V9Trade.is_synthetic == 0)
    if mode:
        q = q.filter(V9Trade.mode == mode)
    system_filter = firing_system if firing_system is not None else dominant_system
    if system_filter is not None:
        q = q.filter(V9Trade.firing_system == system_filter)
    rows = q.order_by(V9Trade.entry_ts.desc()).limit(limit).all()
    return {"trades": [_trade_list_row(r, db) for r in rows]}


@router.get("/recent")
def get_recent_trades(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Read-only feed for the cockpit's TradeHistoryStrip.

    P30 2026-05-20: the frontend has polled `/api/v9/trades/recent` every 5 s
    forever, but no route existed — FastAPI routed it to
    `/api/v9/trades/{trade_id}` with `trade_id='recent'` and returned 422.
    The console was getting flooded (40+ errors per minute) and the
    `useConnection` indicator interpreted the failures as DISCONNECTED.
    Token-less because this is read-only display data, mirroring
    `/active` which is also auth-free for cockpit consumption.
    """
    rows = (
        db.query(V9Trade)
        .filter(V9Trade.is_synthetic == 0)
        .order_by(V9Trade.entry_ts.desc().nullslast(), V9Trade.id.desc())
        .limit(limit)
        .all()
    )
    return [_trade_list_row(r, db) for r in rows]


@router.get("/{trade_id}")
def get_trade(
    trade_id: int,
    db: Session = Depends(get_db),
):
    """Read-only trade detail + entry insight (P31 /trades expand panel).

    Token-less like ``/recent`` — display-only; mutations stay behind
    ``verify_bridge_token``.
    """
    trade = db.get(V9Trade,trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    logs = db.query(V9TradeManagementLog).filter(
        V9TradeManagementLog.trade_id == trade_id
    ).order_by(V9TradeManagementLog.ts).all()
    row = _trade_list_row(trade, db)
    row["quality_review"] = trade.quality
    row["context_json"] = trade.cross_context
    return {
        "trade": row,
        "insight": extract_trade_insight(trade),
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
