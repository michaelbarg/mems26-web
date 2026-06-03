from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
import sqlite3

from backend.v9.shared.pre_fire_validator import FireRequest, validate_fire

router = APIRouter(prefix="/api/v9/woodies", tags=["woodies"])


class WoodiesFireRequest(BaseModel):
    """Manual/automation fire request for S4 Woodies.

    If prices are omitted, the route tries to use the best active pattern from
    WoodiesSystem.current_state.
    """

    direction: Optional[str] = None
    entry_price: Optional[float] = Field(default=None, gt=0)
    stop_price: Optional[float] = Field(default=None, gt=0)
    t1_price: Optional[float] = Field(default=None, gt=0)
    t2_price: Optional[float] = Field(default=None, gt=0)
    t3_price: Optional[float] = Field(default=None, gt=0)
    time_stop_minutes: int = Field(default=90, ge=1, le=180)
    confidence: Optional[int] = Field(default=None, ge=0, le=100)
    dry_run: bool = False


@router.get("/current")
async def woodies_current(request: Request):
    sys = getattr(request.app.state, "woodies_system", None)
    if sys is None:
        return {"running": False, "error": "WoodiesSystem not initialized"}
    return sys.get_current()


@router.get("/signals")
async def woodies_signals(request: Request, limit: int = 20):
    db_path = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM v9_woodies_signals ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return {"entries": [dict(r) for r in rows]}
    except Exception as e:
        return {"entries": [], "error": str(e)}


@router.get("/patterns")
async def woodies_patterns(request: Request):
    """Return currently active patterns from the 8-pattern engine."""
    sys = getattr(request.app.state, "woodies_system", None)
    if sys is None:
        return {"patterns": [], "error": "WoodiesSystem not initialized"}
    state = sys.get_current()
    return {
        "patterns": state.get("active_patterns", []),
        "trend_state": state.get("trend_state", "GRAY"),
        "cci_14": state.get("cci_14"),
        "classification": state.get("classification", "NO_SETUP"),
    }


@router.get("/fire")
async def woodies_fire_state(request: Request):
    """Return latest Woodies fire readiness without routing a trade."""
    sys = getattr(request.app.state, "woodies_system", None)
    if sys is None:
        return {"fired": False, "error": "WoodiesSystem not initialized"}
    state = sys.get_current()
    return {
        "fired": bool(state.get("ready_to_route")),
        "ready_to_route": bool(state.get("ready_to_route")),
        "classification": state.get("classification", "NO_SETUP"),
        "direction": state.get("direction"),
        "entry_classification_spec": state.get("entry_classification_spec"),
        "decision_tree": state.get("decision_tree", {}),
        "active_patterns": state.get("active_patterns", []),
    }


@router.post("/fire")
async def woodies_fire(request: Request, payload: WoodiesFireRequest):
    """Validate and route a Woodies setup through TradingGateway.

    This endpoint does not send orders directly to Sierra. It creates a Woodies
    setup, gates it with pre_fire_validator, then delegates to TradingGateway,
    which owns SHADOW/DEMO/LIVE slot behavior.
    """
    sys = getattr(request.app.state, "woodies_system", None)
    if sys is None:
        raise HTTPException(status_code=503, detail="WoodiesSystem not initialized")

    state = sys.get_current()
    setup = _build_fire_setup_from_state(state, payload)

    pre_fire_req = FireRequest(
        system_id="T2_WOODIES",
        direction=setup["direction"],
        entry_price=setup["entry_price"],
        stop_price=setup["stop_price"],
        t1_price=setup["t1_price"],
        t2_price=setup["t2_price"],
        time_stop_minutes=payload.time_stop_minutes,
        confidence=setup["confidence"],
    )
    pre_fire = validate_fire(pre_fire_req)
    if not pre_fire.valid:
        return {
            "routed": False,
            "blocked_by": "pre_fire_validator",
            "reason": pre_fire.fail_reason,
            "setup": setup,
        }

    gateway_payload = {
        "firing_system": 4,
        "direction": setup["direction"],
        "classification": state.get("classification", "NO_SETUP"),
        "confidence": setup["confidence"] / 100.0,
        "entry_price": setup["entry_price"],
        "stop": setup["stop_price"],
        "t1": setup["t1_price"],
        "t2": setup["t2_price"],
        "t3": setup.get("t3_price", 0.0),
        "metadata": {
            "source": "woodies_fire_endpoint",
            "entry_classification_spec": state.get("entry_classification_spec"),
            "decision_tree": state.get("decision_tree", {}),
        },
    }

    if payload.dry_run:
        return {"routed": False, "dry_run": True, "pre_fire": pre_fire.model_dump(), "setup": gateway_payload}

    gw = getattr(request.app.state, "trading_gateway", None)
    if gw is None:
        raise HTTPException(status_code=503, detail="TradingGateway not initialized")

    result = gw.route_setup(gateway_payload, 4)
    return {"routed": True, "pre_fire": pre_fire.model_dump(), "gateway": result, "setup": gateway_payload}


def _build_fire_setup_from_state(state: dict, payload: WoodiesFireRequest) -> dict:
    pattern = _best_active_pattern(state)

    direction = payload.direction or state.get("direction") or (pattern or {}).get("direction")
    entry_price = payload.entry_price or (pattern or {}).get("entry_price")
    stop_price = payload.stop_price or (pattern or {}).get("stop")
    targets = (pattern or {}).get("targets") or []
    t1_price = payload.t1_price or (targets[0] if len(targets) > 0 else None)
    t2_price = payload.t2_price or (targets[1] if len(targets) > 1 else None)
    t3_price = payload.t3_price or (targets[2] if len(targets) > 2 else 0.0)
    confidence = payload.confidence
    if confidence is None:
        confidence = int(float((pattern or {}).get("confidence", 0.0)) * 100)

    missing = [
        name for name, value in {
            "direction": direction,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "t1_price": t1_price,
            "t2_price": t2_price,
        }.items()
        if value in (None, "", 0)
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Woodies fire setup incomplete: missing {', '.join(missing)}",
        )

    return {
        "direction": direction,
        "entry_price": float(entry_price),
        "stop_price": float(stop_price),
        "t1_price": float(t1_price),
        "t2_price": float(t2_price),
        "t3_price": float(t3_price or 0.0),
        "confidence": int(confidence),
    }


def _best_active_pattern(state: dict) -> Optional[dict]:
    patterns = state.get("active_patterns") or []
    if not patterns:
        return None
    return max(patterns, key=lambda p: float(p.get("confidence", 0.0)))
