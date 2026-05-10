"""System 2 API: GET /v9/chart_5min/signals, GET /v9/chart_5min/state."""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from backend.v9.db.models import V9SystemSignal
from backend.v9.api.v9.auth import verify_bridge_token

router = APIRouter(prefix="/api/v9/chart_5min", tags=["v9-chart-5min"])


@router.get("/signals")
def get_signals(
    limit: int = Query(50, le=200),
    direction: Optional[str] = None,
    classification: Optional[str] = None,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    """Get System 2 signals (pattern detections + setups)."""
    q = db.query(V9SystemSignal).filter(V9SystemSignal.system_id == 2)
    if direction:
        q = q.filter(V9SystemSignal.direction == direction)
    if classification:
        q = q.filter(V9SystemSignal.classification == classification)
    rows = q.order_by(V9SystemSignal.ts.desc()).limit(limit).all()
    return {"signals": [
        {
            "id": r.id,
            "ts": r.ts.isoformat(),
            "system_id": r.system_id,
            "classification": r.classification,
            "direction": r.direction,
            "confidence": r.confidence,
            "payload": r.payload,
        }
        for r in rows
    ]}


@router.get("/state")
def get_state(
    _token: str = Depends(verify_bridge_token),
):
    """Get current System 2 engine state.

    Note: The detector runs in-process (bridge or worker). This endpoint
    returns the last known state snapshot, stored via the detector's
    periodic state dump. For real-time state, use WS /ws/v9/signals/2.
    """
    # In production, this reads from Redis or a state table.
    # For now, return the schema shape so the frontend can integrate.
    return {
        "bar_count": 0,
        "is_first_hour": True,
        "day_type": None,
        "day_type_locked": False,
        "opening_type": None,
        "active_patterns": [],
        "chop": {"micro": 0, "session": 0, "macro": 0, "composite": 0},
        "last_setup": None,
        "killzone_blocked": False,
    }


@router.get("/patterns")
def get_pattern_library(
    _token: str = Depends(verify_bridge_token),
):
    """Return the pattern library metadata (12 patterns, 3 groups)."""
    return {"patterns": [
        {"id": "reactive_buyer", "group": "A", "bars": "4", "potential": "2-4R", "method": "OFA", "direction": "LONG"},
        {"id": "reactive_seller", "group": "A", "bars": "4", "potential": "2-4R", "method": "OFA", "direction": "SHORT"},
        {"id": "initiative_buyer", "group": "A", "bars": "4", "potential": "4-8R", "method": "OFA", "direction": "LONG"},
        {"id": "initiative_seller", "group": "A", "bars": "4", "potential": "4-8R", "method": "OFA", "direction": "SHORT"},
        {"id": "double_bottom", "group": "B", "bars": "8-15", "potential": "3-5R", "method": "Geometric", "direction": "LONG"},
        {"id": "double_top", "group": "B", "bars": "8-15", "potential": "3-5R", "method": "Geometric", "direction": "SHORT"},
        {"id": "bull_flag", "group": "B", "bars": "5-10", "potential": "3-6R", "method": "Hybrid", "direction": "LONG"},
        {"id": "bear_flag", "group": "B", "bars": "5-10", "potential": "3-6R", "method": "Hybrid", "direction": "SHORT"},
        {"id": "bull_pennant", "group": "B", "bars": "5-10", "potential": "3-5R", "method": "Geometric", "direction": "LONG"},
        {"id": "bear_pennant", "group": "B", "bars": "5-10", "potential": "3-5R", "method": "Geometric", "direction": "SHORT"},
        {"id": "ascending_triangle", "group": "B", "bars": "10-20", "potential": "4-7R", "method": "Geometric", "direction": "LONG"},
        {"id": "descending_triangle", "group": "B", "bars": "10-20", "potential": "4-7R", "method": "Geometric", "direction": "SHORT"},
        {"id": "head_shoulders", "group": "C", "bars": "15-25", "potential": "5-10R", "method": "Geometric", "direction": "SHORT"},
        {"id": "inverse_head_shoulders", "group": "C", "bars": "15-25", "potential": "5-10R", "method": "Geometric", "direction": "LONG"},
        {"id": "symmetrical_triangle", "group": "C", "bars": "10-25", "potential": "4-7R", "method": "Geometric", "direction": "BOTH"},
        {"id": "falling_wedge", "group": "C", "bars": "15-30", "potential": "5-8R", "method": "Geometric", "direction": "LONG"},
        {"id": "rising_wedge", "group": "C", "bars": "15-30", "potential": "5-8R", "method": "Geometric", "direction": "SHORT"},
        {"id": "cup_handle", "group": "C", "bars": "20-40", "potential": "6-12R", "method": "Geometric", "direction": "LONG"},
        {"id": "inverse_cup_handle", "group": "C", "bars": "20-40", "potential": "6-12R", "method": "Geometric", "direction": "SHORT"},
    ]}
