"""System 6 — active-trade diagnosis endpoint (read-only).

GET /api/v9/system6/diagnose → the live manager view: the 9 management checks
(supervisor), the HOLD gate (pattern-continuation), and the exit signals
(stall / opposite / counter-flow), for whatever trade the gateway currently
holds. Returns {"active": false} when flat. Diagnoses only — never executes.
Fail-safe: any source that errors is omitted, never crashes the endpoint.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v9/system6", tags=["system6"])


def _atr(bars):
    if not bars:
        return 0.0
    trs, prev = [], None
    for b in bars[-14:]:
        h, l, c = b["high"], b["low"], b["close"]
        trs.append(h - l if prev is None else max(h - l, abs(h - prev), abs(l - prev)))
        prev = c
    return sum(trs) / len(trs) if trs else 0.0


@router.get("/diagnose")
async def diagnose(request: Request):
    gw = getattr(request.app.state, "trading_gateway", None)
    slot = (getattr(gw, "demo_slot", None) or getattr(gw, "live_slot", None)) if gw else None
    if not slot:
        return {"active": False}

    from backend.v9.db.read import read_one, read_all
    out = {"active": True, "trade": None, "hold": None,
           "supervisor": None, "exit_signals": [], "recommendation": "hold"}

    # active trade
    try:
        tr = read_one(
            "SELECT id, direction, entry_price, stop, t1_hit_ts "
            "FROM v9_trades WHERE id = :id", {"id": int(slot)})
    except Exception as e:
        logger.warning("[System6API] trade read failed: %s", e)
        tr = None
    if not tr:
        return {"active": True, "trade": None, "note": f"slot {slot} not found in DB"}
    direction = str(tr["direction"])
    entry = float(tr["entry_price"]) if tr["entry_price"] is not None else None
    stop = float(tr["stop"]) if tr["stop"] is not None else None
    t1_hit = tr["t1_hit_ts"] is not None
    out["trade"] = {"id": tr["id"], "direction": direction, "entry": entry,
                    "stop": stop, "t1_hit": t1_hit, "contracts": 3}

    # recent bars (oldest→newest)
    try:
        rows = read_all(
            "SELECT open, high, low, close FROM v9_bars_5min_woodies "
            "ORDER BY ts DESC LIMIT 10", {})
        bars = [{"o": float(r["open"]), "h": float(r["high"]),
                 "l": float(r["low"]), "c": float(r["close"]),
                 "high": float(r["high"]), "low": float(r["low"]),
                 "close": float(r["close"])} for r in rows][::-1]
    except Exception as e:
        logger.warning("[System6API] bars read failed: %s", e)
        bars = []
    atr = _atr(bars)

    # supervisor (9 management checks)
    try:
        from backend.v9.systems.system6_supervisor import diagnose_trade
        rep = diagnose_trade(
            trade={"direction": direction, "entry_price": entry, "stop": stop,
                   "contracts": 3}, atr=atr, t1_hit=t1_hit, expected_contracts=3)
        out["supervisor"] = {
            "healthy": rep.healthy,
            "issues": [{"code": i.code, "severity": i.severity,
                        "action": i.action, "detail": i.detail} for i in rep.issues],
        }
    except Exception as e:
        logger.warning("[System6API] supervisor failed: %s", e)

    # HOLD gate + exit signals
    try:
        from backend.v9.systems.system6_exit_signals import (
            hold_confirmation, price_stall, opposite_patterns, counter_flow_wins,
        )
        if bars and entry is not None:
            h = hold_confirmation(direction=direction, invalidation_level=stop, bars=bars)
            out["hold"] = {"intact": h.intact, "continuing": h.continuing,
                           "broke": h.broke, "score": h.score, "reason": h.reason}
            sigs = [price_stall(direction=direction, bars=bars)]
            # recent counter-direction fires
            try:
                fr = read_all(
                    "SELECT direction FROM v9_trades WHERE entry_ts >= "
                    "(now() - interval '30 minutes') ORDER BY entry_ts", {})
                dirs = [str(r["direction"]) for r in fr]
            except Exception:
                dirs = []
            sigs.append(opposite_patterns(trade_direction=direction, recent_fire_directions=dirs))
            # counter-flow (CVD)
            try:
                cv = read_all(
                    "SELECT cumulative FROM v9_bars_cumulative_delta "
                    "ORDER BY ts::timestamptz DESC LIMIT 4", {})
                cvd = [float(r["cumulative"]) for r in cv if r["cumulative"] is not None][::-1]
                if len(cvd) >= 3:
                    sigs.append(counter_flow_wins(direction=direction, cvd_series=cvd))
            except Exception:
                pass
            out["exit_signals"] = [{"kind": s.kind, "score": s.score, "fired": s.fired,
                                    "reason": s.reason, "action": s.action} for s in sigs]
            fired = [s for s in sigs if s.fired]
            if h.broke:
                out["recommendation"] = "exit"
            elif h.continuing:
                out["recommendation"] = "hold"
            elif fired:
                out["recommendation"] = "consider_exit"
            # Learning journal — record fired signals (gated SYSTEM6_EXIT_JOURNAL)
            try:
                from backend.v9.systems.system6_journal import record, build_record, enabled as _je
                if _je():
                    for s in fired:
                        record(build_record(
                            trade_id=int(tr["id"]), signal_kind=s.kind, score=s.score,
                            fired=True, recommendation=out["recommendation"],
                            context={"reason": s.reason, "entry": entry, "stop": stop,
                                     "hold": out.get("hold")}))
            except Exception as _je_err:
                logger.warning("[System6API] journal record failed: %s", _je_err)
    except Exception as e:
        logger.warning("[System6API] exit engine failed: %s", e)

    # per-signal hit-rates (advisory, from the journal)
    try:
        from backend.v9.systems.system6_journal import get_hit_rates
        out["hit_rates"] = get_hit_rates()
    except Exception:
        pass

    return out
