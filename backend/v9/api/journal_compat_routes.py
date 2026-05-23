"""Canonical trade journal HTTP API — v9_trades → /trades/log (Render journal UI).

Single read path for SHADOW/LIVE P&L display. Cockpit + /journal page both use
these endpoints; execution still uses /api/v9/trades/* (TradeManager).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, load_only

from backend.v9.db.session import SessionLocal
from backend.v9.db.models.trades import V9Trade
from backend.v9.services.trade_context import compute_trade_pnl
from backend.v9.services.trade_excursion import (
    _bars_hl_in_window,
    _trade_window,
    compute_trade_excursion,
    prefetch_bars_for_trades,
)
from backend.v9.services.trade_legs import extract_trade_legs

logger = logging.getLogger("mems26.journal_compat")

router = APIRouter(tags=["journal-compat"])

MES_POINT_VALUE = 5.0

# Journal list: skip ~25KB cross_context blobs per row (P31-04).
_JOURNAL_TRADE_COLUMNS = (
    V9Trade.id,
    V9Trade.mode,
    V9Trade.firing_system,
    V9Trade.direction,
    V9Trade.state,
    V9Trade.entry_ts,
    V9Trade.entry_price,
    V9Trade.stop,
    V9Trade.t1,
    V9Trade.t2,
    V9Trade.t3,
    V9Trade.t1_hit_ts,
    V9Trade.t2_hit_ts,
    V9Trade.t3_hit_ts,
    V9Trade.stop_hit_ts,
    V9Trade.exit_ts,
    V9Trade.exit_price,
    V9Trade.exit_reason,
    V9Trade.pnl_usd,
    V9Trade.pnl_r,
    V9Trade.outcome,
    V9Trade.quality,
)


def _modes_for_types(types_list: List[str]) -> List[str]:
    modes: List[str] = []
    if "shadow" in types_list:
        modes.append("shadow")
    if "live" in types_list:
        modes.extend(["demo", "live"])
    return modes or ["shadow", "demo", "live"]


def _journal_display_fields(row: V9Trade) -> Dict[str, Any]:
    """Lightweight display — quality JSON only, no cross_context walk."""
    quality = row.quality if isinstance(row.quality, dict) else {}
    meta = quality.get("metadata") if isinstance(quality.get("metadata"), dict) else {}
    classification = (
        quality.get("classification")
        or meta.get("pattern")
        or meta.get("signal")
        or ""
    )
    trigger = quality.get("trigger") or classification or f"S{row.firing_system}"
    pattern_id = meta.get("pattern") or meta.get("signal") or classification or None
    return {
        "pattern_id": pattern_id,
        "trigger": str(trigger),
        "classification": str(classification) if classification else None,
        "confidence": quality.get("confidence"),
        "day_type": meta.get("day_type") or "UNKNOWN",
    }


def _to_unix(ts: Optional[datetime]) -> float:
    if ts is None:
        return 0.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.timestamp()


def _map_state(state: str, outcome: Optional[str]) -> str:
    if state == "CLOSED":
        return "CLOSED"
    if state in ("FILLED", "PARTIAL", "OPEN"):
        return "OPEN"
    return state or "PENDING"


def _duration_min(entry_ts: Optional[datetime], exit_ts: Optional[datetime]) -> Optional[float]:
    if entry_ts is None:
        return None
    end = exit_ts or datetime.now(timezone.utc)
    if entry_ts.tzinfo is None:
        entry_ts = entry_ts.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return round((end - entry_ts).total_seconds() / 60.0, 1)


def _v9_row_to_journal(row: V9Trade, db: Session, bar_cache: list) -> Dict[str, Any]:
    entry = row.entry_price or 0.0
    stop = row.stop or 0.0
    risk_pts = abs(entry - stop) if entry and stop else 0.0

    pnl = compute_trade_pnl(row)
    pnl_usd = pnl["pnl_usd"]
    pnl_pts = (pnl_usd / MES_POINT_VALUE) if pnl_usd is not None else 0.0

    start, end = _trade_window(row)
    if bar_cache and start is not None:
        ex = compute_trade_excursion(row, bars=_bars_hl_in_window(bar_cache, start, end))
    else:
        ex = compute_trade_excursion(row, db)

    entry_unix = _to_unix(row.entry_ts)
    exit_unix = _to_unix(row.exit_ts)
    is_shadow = (row.mode or "").lower() == "shadow"

    display = _journal_display_fields(row)
    quality = row.quality if isinstance(row.quality, dict) else {}
    initial_stop = quality.get("initial_stop")
    if initial_stop is not None:
        try:
            initial_stop = float(initial_stop)
        except (TypeError, ValueError):
            initial_stop = None
    day_type = display.get("day_type") or "UNKNOWN"
    killzone = "UNKNOWN"

    status = _map_state(row.state or "", row.outcome)
    win = (pnl_usd or 0) > 0 if pnl_usd is not None else False
    return {
        "id": str(row.id),
        "ts": entry_unix,
        "entry_ts": entry_unix,
        "exit_ts": exit_unix if exit_unix else None,
        "direction": row.direction,
        "entry": entry,
        "entry_price": entry,
        "exit_price": row.exit_price,
        "stop": stop,
        "initial_stop": initial_stop if initial_stop is not None else stop,
        "t1": row.t1 or 0,
        "t2": row.t2 or 0,
        "t3": row.t3 or 0,
        "risk_pts": risk_pts,
        "pnl_pts": pnl_pts,
        "pnl_usd": pnl_usd or 0,
        "status": status,
        "close_reason": row.exit_reason or "",
        "is_shadow": is_shadow,
        "day_type": day_type,
        "killzone": killzone,
        "setup_type": display.get("pattern_id") or f"S{row.firing_system}",
        "pattern": display.get("pattern_id"),
        "trigger": display.get("trigger"),
        "classification": display.get("classification"),
        "score": 100 if is_shadow else 0,
        "source": "trade",
        "win": win,
        "executed_in_sim": not is_shadow,
        "mode": row.mode,
        "outcome": row.outcome,
        "firing_system": row.firing_system,
        "confidence": display.get("confidence"),
        "exit_reason": row.exit_reason,
        "pnl_mode": pnl.get("pnl_mode"),
        "price_high": ex.get("price_high"),
        "price_low": ex.get("price_low"),
        "mfe_pts": ex.get("mfe_pts"),
        "mae_pts": ex.get("mae_pts"),
        "t1_closest_pts": ex.get("t1_closest_pts"),
        "t1_hit": row.t1_hit_ts is not None,
        "t2_hit": row.t2_hit_ts is not None,
        "t3_hit": row.t3_hit_ts is not None,
        "stop_hit": row.stop_hit_ts is not None,
        "t1_hit_ts": _to_unix(row.t1_hit_ts) or None,
        "t2_hit_ts": _to_unix(row.t2_hit_ts) or None,
        "t3_hit_ts": _to_unix(row.t3_hit_ts) or None,
        "stop_hit_ts": _to_unix(row.stop_hit_ts) or None,
        "duration_min": _duration_min(row.entry_ts, row.exit_ts),
        "trade_legs": extract_trade_legs(row),
        "range_note": "5m bars" if (ex.get("bars_count") or 0) > 0 else None,
    }


def _fetch_v9_trades(
    types_list: List[str],
    limit: int,
    min_score: int = 0,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        cap = min(max(limit, 1), 500)
        modes = _modes_for_types(types_list)
        q = (
            db.query(V9Trade)
            .options(load_only(*_JOURNAL_TRADE_COLUMNS))
            .filter(or_(*[func.lower(V9Trade.mode) == m for m in modes]))
            .order_by(V9Trade.entry_ts.desc().nullslast(), V9Trade.id.desc())
            .limit(cap)
        )
        rows = q.all()
        bar_cache = prefetch_bars_for_trades(db, rows)
        out: List[Dict[str, Any]] = []
        for row in rows:
            mapped = _v9_row_to_journal(row, db, bar_cache)
            if min_score > 0 and (mapped.get("score") or 0) < min_score:
                continue
            out.append(mapped)
        return out
    finally:
        if owns_session:
            db.close()


@router.get("/trades/log")
def trades_log_compat(
    limit: int = Query(50, ge=1, le=500),
    types: Optional[str] = Query(None, description="shadow,live comma-separated"),
    min_score: int = Query(0, ge=0),
    include_closed: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
):
    """Drop-in for legacy `mems26-web` journal — backed by v9_trades."""
    types_list = [t.strip().lower() for t in (types or "shadow,live").split(",") if t.strip()]
    try:
        results = _fetch_v9_trades(types_list, limit, min_score=min_score)
        logger.info(
            "[journal_compat] /trades/log types=%s limit=%d -> %d rows",
            types_list,
            limit,
            len(results),
        )
        return results
    except Exception as e:
        logger.error("[journal_compat] /trades/log failed: %s", e, exc_info=True)
        return []


@router.get("/analytics/setups/recent")
def setups_recent_compat(limit: int = Query(500, ge=1, le=1000)):
    """Journal merges setups — V9 path uses v9_trades only for now."""
    return {"setups": [], "ok": True}


@router.get("/analytics/setups/today_summary")
def shadow_today_summary(min_score: int = Query(0, ge=0)):
    """SHADOW KPI strip for journal — derived from v9_trades today."""
    rows = _fetch_v9_trades(["shadow"], limit=500, min_score=min_score)
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    open_rows = [r for r in rows if r.get("status") != "CLOSED"]
    wins = [r for r in closed if (r.get("pnl_usd") or 0) > 0]
    total_pnl = sum((r.get("pnl_usd") or 0) for r in closed)
    return {
        "total_setups": len(rows),
        "closed": len(closed),
        "still_open": len(open_rows),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "total_pnl_net_usd": round(total_pnl, 2),
    }


@router.get("/analytics/setups/sequential_today_summary")
def sequential_today_summary_compat():
    """REAL/sequential tab — no V9 sequential sim yet."""
    return {
        "total_executed_in_sim": 0,
        "executed_closed": 0,
        "executed_open": 0,
        "sequential_wr": 0,
        "sequential_pnl_usd": 0,
    }
