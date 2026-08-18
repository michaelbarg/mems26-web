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
        # T3 semantics (from targets_table via manager): "trail" / "4R+trail" / None.
        # Lets the UI distinguish "no fixed T3 → trail" from a real T3 price.
        "t3_label": (r.quality or {}).get("t3_label"),
        "trail_after_t2": (r.quality or {}).get("trail_after_t2"),
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
        "is_synthetic": bool(r.is_synthetic),
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


def _flatten_sierra_position(trade, tm, request) -> bool:
    """Send CANCEL to Sierra to flatten a demo/live position before DB close.

    Returns True if:
      - trade is shadow (no Sierra position) → nothing to flatten
      - trade has no sierra_order_id (not yet submitted) → nothing to flatten
      - CANCEL sent and ack received within timeout
    Returns False if CANCEL sent but no ack → CRITICAL, caller must NOT close.
    """
    import time
    import json
    from pathlib import Path

    mode = getattr(trade, "mode", "shadow")
    if mode not in ("demo", "live"):
        return True  # shadow — no Sierra position

    oid = tm._get_sierra_order_id(trade) if hasattr(tm, "_get_sierra_order_id") else None
    if oid is None:
        # No sierra_order_id → order was never submitted/acked by Sierra
        logger.warning(
            "[trades] exit: trade %d has no sierra_order_id — no Sierra CANCEL needed",
            trade.id,
        )
        return True

    from backend.v9.services.sierra_command import write_cancel
    write_cancel(trade_id=str(trade.id), order_id=oid, mode=mode)
    logger.info("[trades] exit: CANCEL sent to Sierra for trade %d (order_id=%d)", trade.id, oid)

    # Poll for ack (trade_result.json) — short timeout, Sierra responds fast
    result_path = Path("/Users/michael/SierraChart_Data/v9_export/trade_result.json")
    deadline = time.time() + 5.0  # 5 second timeout
    while time.time() < deadline:
        try:
            if result_path.stat().st_size > 0:
                with open(result_path) as f:
                    result = json.load(f)
                status = result.get("status", "")
                if "CANCEL" in status.upper() or "FLAT" in status.upper():
                    logger.info(
                        "[trades] exit: Sierra ack received for trade %d: %s",
                        trade.id, status,
                    )
                    return True
        except (json.JSONDecodeError, OSError):
            pass
        time.sleep(0.3)

    logger.critical(
        "[trades] exit: NO Sierra ack within 5s for trade %d (order_id=%d) — "
        "POSITION MAY STILL BE OPEN IN SIERRA. Record NOT closed.",
        trade.id, oid,
    )
    return False


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

    # Phase-0 fix (07-09 live finding, trade 318): exit MUST flatten Sierra before
    # closing the DB record. Without this, the record closes + slot frees but the
    # Sierra position stays open — orphan position with no system monitoring it.
    sierra_flatten_ok = _flatten_sierra_position(trade, tm, request)
    if not sierra_flatten_ok:
        raise HTTPException(
            status_code=409,
            detail=f"Sierra flatten failed for trade {trade_id} — position may still be open in Sierra. "
                   "DO NOT close the record. Check Sierra manually.",
        )

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

    # I-57 via cockpit (2026-07-08 live): exit closed trade 310 but the gateway
    # live_slot stayed occupied → ALL new fires blocked until restart. Notify the
    # gateway exactly like the FillPoller close path. Fail-safe, never raises.
    try:
        _gw = getattr(request.app.state, "trading_gateway", None)
        if _gw is not None and getattr(trade, "mode", "shadow") in ("demo", "live"):
            _gw.on_trade_close({
                "trade_id": trade_id,
                "mode": getattr(trade, "mode", "shadow"),
                "pnl_usd": getattr(trade, "pnl_usd", 0.0) or 0.0,
                "outcome": getattr(trade, "outcome", "") or (body.reason or "manual"),
                "direction": getattr(trade, "direction", "") or "",
            })
            logger.info("[trades] exit: gateway notified — slot released for trade %s", trade_id)
    except Exception as exc:
        logger.warning("[trades] exit: gateway notify failed (non-fatal): %s", exc)

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


def _contracts_of(trade) -> int:
    """This trade's contract count, from the one resolver."""
    try:
        from backend.v9.services.trade_manager.manager import trade_contract_count
        return int(trade_contract_count(trade))
    except Exception:
        return 0


def _find_scale_in_child(db, parent_id: int, active_states):
    """A still-open reinforcement whose parent is `parent_id`.

    The link is written into the child's quality.metadata by the scale-in
    call site; the parent is only marked `scaled_in`, so the child is the
    side that carries the pointer.
    """
    try:
        from backend.v9.db.models.trades import V9Trade as _T
        for c in (db.query(_T)
                  .filter(_T.state.in_(active_states), _T.id > parent_id)
                  .order_by(_T.entry_ts.desc()).limit(10).all()):
            q = c.quality if isinstance(c.quality, dict) else {}
            m = q.get("metadata") if isinstance(q.get("metadata"), dict) else {}
            if int(m.get("scale_in_parent") or q.get("scale_in_parent") or 0) == int(parent_id):
                return c
    except Exception:
        pass
    return None


# NOTE (2026-08-18): this decorator must stay glued to get_active_trade. It was
# separated from it by two helpers inserted above, so FastAPI registered
# /active against `_contracts_of` — the route answered 422 "field required:
# trade", the dashboard's fetch returned null, and every surface fell through
# to "No Active Trade": no position badge, no target rows, no percentages.
# tests/v9/regression/test_active_trade_route.py now issues a real request.
@router.get("/active")
def get_active_trade(db: Session = Depends(get_db)):
    """Return the current active trade with C1/C2/C3 contract details.

    Derives per-contract status from t1/t2/t3 + hit timestamps.
    MES: 1 point = $5 per contract.
    """
    _active_states = ["FILLED", "PARTIAL", "OPEN"]
    # L3 (2026-07-08 live incident): priority LIVE → DEMO → nothing. The old
    # any-mode fallback rendered a SHADOW row as the "active trade" — tonight it
    # masked the real live position (310) with its shadow twin (313), so the
    # dashboard never showed Michael's manual Sierra close. A shadow trade is a
    # simulation record and must NEVER render as the supervised position.
    trade = None
    for _mode in ("live", "demo"):
        trade = (
            db.query(V9Trade)
            .filter(V9Trade.state.in_(_active_states), V9Trade.mode == _mode)
            .order_by(V9Trade.entry_ts.desc())
            .first()
        )
        if trade is not None:
            break
    if not trade:
        return None

    # SCALE-IN (Michael 2026-08-18: "בפרונט אנד זה לא סומן הגדלת חוזים").
    # The reinforcement DID fire on 17.08 — [ScaleIn] 22:32:05 parent=699
    # child=708 +2c. What he saw was not a missing badge: `entry_ts.desc()`
    # picked the CHILD, so the winning parent vanished from the card and was
    # replaced by a new smaller trade — entry moved 7776.25 -> 7769.75,
    # "1/2 hit" became "0/2 hit", P&L went to $0. The trade looked lost.
    # A reinforcement is an addition to the SAME position, so the card must
    # keep showing the parent and say the position grew.
    _scale_in = None
    _meta = trade.quality if isinstance(trade.quality, dict) else {}
    _parent_id = (_meta.get("metadata") or {}).get("scale_in_parent") \
        if isinstance(_meta.get("metadata"), dict) else None
    _parent_id = _parent_id or _meta.get("scale_in_parent")
    if _parent_id:
        _parent = (
            db.query(V9Trade)
            .filter(V9Trade.id == int(_parent_id),
                    V9Trade.state.in_(_active_states))
            .first()
        )
        if _parent is not None:
            _scale_in = {"child_id": trade.id,
                         "added": _contracts_of(trade),
                         "at": trade.entry_ts.isoformat() if trade.entry_ts else None,
                         "child_entry": trade.entry_price}
            trade = _parent          # the card shows the position, not the add-on
    else:
        # parent side: find a still-open child pointing back at us
        _child = _find_scale_in_child(db, trade.id, _active_states)
        if _child is not None:
            _scale_in = {"child_id": _child.id,
                         "added": _contracts_of(_child),
                         "at": _child.entry_ts.isoformat() if _child.entry_ts else None,
                         "child_entry": _child.entry_price}

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

    # L7 (2026-07-08): build only the contract rows this trade actually has —
    # a 2-contract trade showed a phantom C3 row ("1/3 hit") and its stop-out
    # P&L summed 3 legs.
    #
    # 2026-08-18: and only THREE rows could ever be built, because the list was
    # written as C1/C2/C3 → t1/t2/t3 and then sliced. Above four contracts the
    # slice is a no-op, so a 5-contract trade rendered three bars under the
    # heading "0/5 hit", the first bar measured against T1 when that contract
    # actually exits at T0, and the P&L summed three legs out of five. The rows
    # now come from the SAME ladder the DLL brackets with
    # (contract_size.target_index_for_contract), so the screen and the broker
    # cannot describe the position differently.
    from backend.v9.services.trade_manager.manager import trade_contract_count
    from backend.v9.services.contract_size import target_index_for_contract
    n_contracts = trade_contract_count(trade)
    _q = trade.quality if isinstance(trade.quality, dict) else {}
    _t0 = _q.get("t0")
    try:
        _t0 = float(_t0) if _t0 is not None else None
    except (TypeError, ValueError):
        _t0 = None
    # index 0..3 → the price that leg exits at. T0 stays None when the trade was
    # not built with one (Rule 1) rather than silently borrowing T1's price.
    _targets = [_t0, trade.t1, trade.t2, trade.t3]
    _hits = [None, trade.t1_hit_ts, trade.t2_hit_ts, trade.t3_hit_ts]
    contracts = []
    for _i in range(max(0, int(n_contracts))):
        _leg = target_index_for_contract(_i, n_contracts)
        contracts.append(_contract(
            "C%d" % (_i + 1), _targets[_leg], _hits[_leg],
            smart_be=(trade.t1_hit_ts is not None and _hits[_leg] is None)))

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
        "summary": f"{hits}/{len(contracts)} hit",
        # The size actually in the market, parent + reinforcement. `contracts`
        # above is this trade's own legs; when a scale-in child is open the
        # POSITION is bigger, and that is the number Michael is watching.
        # Counted from the same place the scale-in ceiling counts it, so the
        # screen and the guard can never disagree.
        "position_contracts": (_contracts_of(trade)
                               + int((_scale_in or {}).get("added") or 0)),
        "scale_in": _scale_in,
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
    limit: int = Query(50, le=1000),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    # Include synthetic trades (shown with badge); was previously hidden
    q = db.query(V9Trade)
    if mode:
        q = q.filter(V9Trade.mode == mode)
    system_filter = firing_system if firing_system is not None else dominant_system
    if system_filter is not None:
        q = q.filter(V9Trade.firing_system == system_filter)
    total = q.count()
    rows = q.order_by(V9Trade.entry_ts.desc()).limit(limit).all()
    return {"trades": [_trade_list_row(r, db) for r in rows], "total": total, "truncated": total > limit}


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
        .order_by(V9Trade.entry_ts.desc().nullslast(), V9Trade.id.desc())
        .limit(limit)
        .all()
    )
    return [_trade_list_row(r, db) for r in rows]


@router.get("/{trade_id}/timeline")
def get_trade_timeline(
    trade_id: int,
    db: Session = Depends(get_db),
):
    """Unified timeline: fills + stop_moves + management-log + blocks.

    Returns events sorted chronologically for the trade detail panel.
    """
    trade = db.get(V9Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    events = []

    # Entry fill
    if trade.entry_ts:
        events.append({
            "ts": trade.entry_ts.isoformat() if hasattr(trade.entry_ts, 'isoformat') else str(trade.entry_ts),
            "type": "ENTRY_FILL",
            "detail": {
                "price": float(trade.entry_price) if trade.entry_price else None,
                "direction": trade.direction,
            },
        })

    # Target hits
    for label, ts_field in [("T1", "t1_hit_ts"), ("T2", "t2_hit_ts"), ("T3", "t3_hit_ts")]:
        ts = getattr(trade, ts_field, None)
        if ts:
            events.append({
                "ts": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                "type": f"{label}_HIT",
                "detail": {"target": float(getattr(trade, label.lower(), 0) or 0)},
            })

    # Exit
    if trade.exit_ts:
        events.append({
            "ts": trade.exit_ts.isoformat() if hasattr(trade.exit_ts, 'isoformat') else str(trade.exit_ts),
            "type": "EXIT",
            "detail": {
                "price": float(trade.exit_price) if trade.exit_price else None,
                "reason": trade.exit_reason,
                "pnl_usd": float(trade.pnl_usd) if trade.pnl_usd else None,
            },
        })

    # Management log entries (stop moves, BE, trail, etc.)
    logs = db.query(V9TradeManagementLog).filter(
        V9TradeManagementLog.trade_id == trade_id
    ).order_by(V9TradeManagementLog.ts).all()
    for l in logs:
        events.append({
            "ts": l.ts.isoformat() if hasattr(l.ts, 'isoformat') else str(l.ts),
            "type": f"MGMT_{l.action}",
            "detail": l.value if isinstance(l.value, dict) else {"value": l.value},
        })

    # Cross-context (stop moves from audit trail)
    cc = trade.cross_context
    if isinstance(cc, dict):
        for key, val in cc.items():
            if isinstance(val, dict) and "ts" in val:
                events.append({
                    "ts": str(val["ts"]),
                    "type": f"CROSS_{key.upper()}",
                    "detail": {k: v for k, v in val.items() if k != "ts"},
                })

    # Sort chronologically
    events.sort(key=lambda e: e["ts"])

    return {
        "trade_id": trade_id,
        "direction": trade.direction,
        "state": trade.state,
        "outcome": trade.outcome,
        "events": events,
        "event_count": len(events),
    }


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
