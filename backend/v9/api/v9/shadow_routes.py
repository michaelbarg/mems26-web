"""W5.1 — Backend stubs for SSV / Shadow WR / System Health.

Closes Chrome audit bugs #14-16.
"""
import sqlite3
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request

router = APIRouter(tags=["shadow"])

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

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
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT outcome FROM v9_trades WHERE date(created_at) = date('now') AND outcome IS NOT NULL"
        ).fetchall()
        conn.close()
    except Exception:
        rows = []

    total = len(rows)
    wins = sum(1 for r in rows if r[0] == "WIN")
    losses = sum(1 for r in rows if r[0] in ("STOP", "LOSS"))
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
        status = "error"
        notes = f"{system_name} not running"
    elif bars > 0 and (age < 60 or age == -1):
        status = "healthy"
        notes = f"{system_name}: {bars} bars processed, data fresh"
    elif bars > 0 and age < 300:
        status = "warn"
        notes = f"{system_name}: data {age}s old"
    elif bars > 0:
        status = "error"
        notes = f"{system_name}: data stale ({age}s)"
    else:
        status = "warn"
        notes = f"{system_name}: running but no signals yet"

    return {
        "status": status,
        "last_signal_ts": str(last_update) if last_update else None,
        "data_age_seconds": age,
        "reasoning_notes": notes,
    }


@router.get("/api/v9/{system_name}/health")
async def system_health(system_name: str, request: Request):
    """Per-system health status for UI status dots."""
    if system_name not in SYSTEM_NAMES:
        return {"status": "error", "reasoning_notes": f"Unknown system: {system_name}"}
    return _get_system_health(system_name, request)
