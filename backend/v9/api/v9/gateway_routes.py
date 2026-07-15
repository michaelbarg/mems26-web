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
    out = []
    for d in buf[-max(1, min(int(limit), 200)):][::-1]:  # newest first
        e = dict(d)
        try:
            e["t_il"] = _dt.fromisoformat(d["ts"]).astimezone(_il).strftime("%H:%M:%S")
        except Exception:
            e["t_il"] = None
        out.append(e)
    return {
        "decisions": out,
        "today": {"fired": fired, "blocked": blocked,
                  "shadow_only": shadow_only, "by_gate": by_gate},
        "buffer_len": len(buf),
        "note": "in-memory since backend start",
    }


@router.post("/route_setup")
async def gateway_route_setup(request: Request, payload: RouteSetupIn):
    """Manually route a trade setup through the gateway (for testing)."""
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        return {"error": "TradingGateway not initialized"}
    result = gw.route_setup(payload.dict(), payload.firing_system)
    return {"routed": result}
