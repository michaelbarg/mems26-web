"""W5.1 — Backend stubs for SSV / Shadow WR / System Health.

Closes Chrome audit bugs #14-16.
"""
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request

from backend.v9.common.trading_date import et_today
from backend.v9.db.read import read_all

router = APIRouter(tags=["shadow"])

# ── W5.1.A: /api/v9/veto/state (Suffering Side) ──

@router.get("/api/v9/veto/state")
async def veto_state(request: Request):
    """Suffering Side Veto state — reads from gateway SSV module."""
    gw = getattr(request.app.state, "trading_gateway", None)
    if gw and hasattr(gw, "ssv"):
        return gw.ssv.get_state()
    return {
        "suffering_side": "NONE",
        "recent_outcomes": 0,
        "veto_active": False,
        "reasoning_notes": "SSV not initialized — no losses tracked yet (INFRA-SHADOW)",
    }


# ── W5.1.B: /api/v9/shadow/today_wr (Win Rate) ──

@router.get("/api/v9/shadow/today_wr")
async def shadow_today_wr():
    """Today's shadow trade win rate from v9_trades."""
    rows = read_all(
        "SELECT outcome FROM v9_trades WHERE date(created_at) = :today AND outcome IS NOT NULL",
        {"today": et_today().isoformat()},
    )

    total = len(rows)
    wins = sum(1 for r in rows if r["outcome"] == "WIN")
    losses = sum(1 for r in rows if r["outcome"] in ("STOP", "LOSS"))
    wr = round(wins / total * 100, 1) if total > 0 else 0.0

    return {
        "today_wr_pct": wr,
        "total_trades_today": total,
        "wins": wins,
        "losses": losses,
        "reasoning_notes": f"Shadow WR today: {wins}/{total} = {wr}%" if total > 0
                           else "No trades closed today — INFRA-SHADOW",
    }


# ── W5.1.C: /api/v9/<system>/health (per-system status dots) ──

@router.get("/api/v9/shadow/soak_progress")
async def shadow_soak_progress():
    """Shadow soak progress — Day N/30 + WR stats."""
    from datetime import date
    # SHADOW start date — first day mode was set to shadow
    start_date = date(2026, 5, 14)  # hard-coded for now
    today = et_today()
    day_n = max(1, (today - start_date).days + 1)
    return {
        "day": min(day_n, 30),
        "total_days": 30,
        "wr_7d": 0.0,
        "wr_30d": 0.0,
        "trades_today": 0,
        "reasoning_notes": f"Shadow soak Day {min(day_n, 30)}/30",
    }


SYSTEM_NAMES = {
    "day_type": 1, "five_min": 2, "footprint": 3,
    "woodies": 4, "tpo": 5, "killzone": 6,
}

def _get_system_health(system_name: str, request: Request) -> dict:
    """Compute health status for a single system."""
    sys_attr_map = {
        "day_type": "day_type_machine",
        "five_min": "five_min_system",
        "footprint": "footprint_system",
        "woodies": "woodies_system",
        "tpo": "tpo_system",
        "killzone": "killzone_system",
    }
    attr = sys_attr_map.get(system_name)
    sys_obj = getattr(request.app.state, attr, None) if attr else None

    if sys_obj is None:
        return {
            "status": "error",
            "last_signal_ts": None,
            "data_age_seconds": -1,
            "reasoning_notes": f"{system_name} not initialized",
        }

    # Support both get_current() (systems) and get_state() (state machines)
    if hasattr(sys_obj, "get_current"):
        state = sys_obj.get_current()
    elif hasattr(sys_obj, "current_state"):
        state = dict(sys_obj.current_state) if isinstance(sys_obj.current_state, dict) else {}
    else:
        state = {"running": True}  # assume running if object exists
    running = state.get("running", False) or state.get("hydrated", False)
    bars = state.get("bars_processed_today", state.get("buffer_size", 0))

    # Estimate data age from last update
    last_update = state.get("last_update_ts") or state.get("ib_locked_ts")
    if last_update:
        try:
            if isinstance(last_update, str):
                dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
            else:
                dt = datetime.fromtimestamp(last_update, tz=timezone.utc)
            age = int((datetime.now(timezone.utc) - dt).total_seconds())
        except Exception:
            age = -1
    else:
        age = -1

    if not running:
        status = "warn"
        notes = f"{system_name} idle (not running — may be outside session)"
    elif bars > 0 and (age < 120 or age == -1):
        status = "healthy"
        notes = f"{system_name}: {bars} bars processed, data fresh"
    elif bars > 0 and age < 600:
        status = "warn"
        notes = f"{system_name}: data {age}s old"
    elif bars > 0:
        status = "warn"
        notes = f"{system_name}: data stale ({age}s) — outside session?"
    else:
        status = "healthy"
        notes = f"{system_name}: running, awaiting first signal"

    return {
        "status": status,
        "last_signal_ts": str(last_update) if last_update else None,
        "data_age_seconds": age,
        "reasoning_notes": notes,
    }


@router.get("/api/v9/five_min/nt_skip_stats")
def get_nt_skip_stats(request: Request):
    """Return cumulative count of NT NO_TRADE skips (D-091.Q2 SHADOW counter)."""
    fm = getattr(request.app.state, "five_min_system", None)
    if fm is None:
        return {"available": False, "reason": "five_min_system not on app.state"}
    return {
        "available": True,
        "nt_skip_count": getattr(fm, "_nt_skip_count", 0),
        "current_day_type": getattr(fm, "current_day_type", None),
    }


@router.get("/api/v9/{system_name}/health")
async def system_health(system_name: str, request: Request):
    """Per-system health status for UI status dots."""
    if system_name not in SYSTEM_NAMES:
        return {"status": "error", "reasoning_notes": f"Unknown system: {system_name}"}
    return _get_system_health(system_name, request)
