"""API routes for Trading Gateway status + manual route_setup (P-TG.5)."""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v9/gateway", tags=["gateway"])


@router.get("/status")
async def gateway_status(request: Request):
    """Return gateway slot states, daily PnL, trade count."""
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        return {"running": False, "error": "TradingGateway not initialized"}
    return gw.get_status()


class RouteSetupIn(BaseModel):
    firing_system: int
    direction: str
    classification: Optional[str] = None
    confidence: Optional[float] = 0.75
    entry_price: Optional[float] = None
    stop: Optional[float] = 0.0
    t1: Optional[float] = 0.0
    t2: Optional[float] = 0.0
    t3: Optional[float] = 0.0


@router.get("/risk")
async def gateway_risk(request: Request):
    """ζ.A4/A5/B2: Risk filter states (cooldown, cluster guard, SSV)."""
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        return {"error": "TradingGateway not initialized"}
    return {
        "cooldown": gw.cooldown.get_state(),
        "cluster_guard": gw.cluster_guard.get_state(),
        "ssv": gw.ssv.get_state(),
        "chop_state": gw._get_chop_state(),
    }


@router.get("/decisions")
async def gateway_decisions(request: Request, limit: int = 60):
    """07-15 (Michael): live "why didn't it fire" feed — every route_setup
    attempt with its outcome (fired live/demo, shadow-only, or blocked+gate).
    In-memory since backend start; full history remains in logs/DB."""
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        return {"error": "TradingGateway not initialized", "decisions": []}
    buf = list(getattr(gw, "decisions", []))
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI
    _il = _ZI("Asia/Jerusalem")
    today_il = _dt.now(_il).date()
    by_gate: dict = {}
    fired = blocked = shadow_only = 0
    for d in buf:
        try:
            ts_il = _dt.fromisoformat(d["ts"]).astimezone(_il)
            if ts_il.date() != today_il:
                continue
        except Exception:
            continue
        if d.get("blocked_by"):
            blocked += 1
            by_gate[d["blocked_by"]] = by_gate.get(d["blocked_by"], 0) + 1
        elif d.get("outcome") in ("live", "demo"):
            fired += 1
        elif d.get("outcome") == "shadow_only":
            shadow_only += 1
    # P10 (2026-07-22): enrich fired decisions with the trade's actual DB state.
    # A decision with outcome="live" but trade.state="CANCELLED" should show
    # "order_failed", not "live" (the #462 bug: Sierra r=-1 but panel said "live").
    _trade_states = {}
    try:
        _fired_ids = []
        for d in buf:
            _tid = d.get("trade_id")
            if _tid and d.get("outcome") in ("live", "demo"):
                try:
                    _fired_ids.append(int(_tid))
                except (ValueError, TypeError):
                    pass
        if _fired_ids:
            from backend.v9.db.read import read_all as _r
            _rows = _r(
                "SELECT id, state, outcome FROM v9_trades WHERE id = ANY(:ids)",
                {"ids": list(set(_fired_ids))})
            _trade_states = {int(r["id"]): {"state": r["state"], "outcome": r["outcome"]}
                             for r in _rows}
    except Exception:
        pass  # enrichment is best-effort

    out = []
    for d in buf[-max(1, min(int(limit), 200)):][::-1]:  # newest first
        e = dict(d)
        try:
            e["t_il"] = _dt.fromisoformat(d["ts"]).astimezone(_il).strftime("%H:%M:%S")
        except Exception:
            e["t_il"] = None
        # P10: override outcome for cancelled/failed trades
        tid = e.get("trade_id")
        try:
            _tid_int = int(tid) if tid else None
        except (ValueError, TypeError):
            _tid_int = None
        if _tid_int is not None and _tid_int in _trade_states:
            ts = _trade_states[_tid_int]
            if ts["state"] == "CANCELLED" or ts["outcome"] == "CANCELLED":
                e["outcome"] = "order_failed"
                e["trade_state"] = ts["state"]
                e["trade_outcome"] = ts["outcome"]
        out.append(e)
    return {
        "decisions": out,
        "today": {"fired": fired, "blocked": blocked,
                  "shadow_only": shadow_only, "by_gate": by_gate},
        "buffer_len": len(buf),
        "note": "persisted to JSONL since P10 (2026-07-22)",
    }


@router.post("/route_setup")
async def gateway_route_setup(request: Request, payload: RouteSetupIn):
    """Manually route a trade setup through the gateway (for testing)."""
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        return {"error": "TradingGateway not initialized"}
    result = gw.route_setup(payload.dict(), payload.firing_system)
    return {"routed": result}
