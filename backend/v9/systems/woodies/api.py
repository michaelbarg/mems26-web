"""Woodies CCI API — GET endpoints for signals and state.

NOTE: These are self-contained routes. Registration snippet provided
at end for inclusion in app.py when ready.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from backend.v9.db.models import V9Bar30MinWoodies, V9SystemSignal
from backend.v9.systems.woodies.detector import compute_state, detect_patterns
from backend.v9.systems.woodies import SYSTEM_ID

router = APIRouter(prefix="/api/v9/woodies", tags=["v9-woodies"])


def _load_bar_history(db: Session, limit: int = 60):
    """Load recent Woodies bars from DB, return as parallel lists."""
    rows = db.query(V9Bar30MinWoodies).order_by(
        V9Bar30MinWoodies.ts.desc()
    ).limit(limit).all()
    rows = list(reversed(rows))

    highs = [r.high for r in rows]
    lows = [r.low for r in rows]
    closes = [r.close for r in rows]
    timestamps = [r.ts.timestamp() for r in rows]
    return highs, lows, closes, timestamps


@router.get("/state")
def get_woodies_state(
    db: Session = Depends(get_db),
):
    """Current Woodies system state: all studies + active patterns."""
    highs, lows, closes, timestamps = _load_bar_history(db)
    if not closes:
        return {
            "trend_state": "GRAY", "cci_14": 0, "cci_6_tcci": 0,
            "classification": "NO_SETUP", "direction": "NEUTRAL",
            "active_patterns": [],
        }

    state = compute_state(highs, lows, closes, timestamps)
    return state.model_dump()


@router.get("/signals")
def get_woodies_signals(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """Recent Woodies signals from v9_system_signals where system_id=4."""
    rows = db.query(V9SystemSignal).filter(
        V9SystemSignal.system_id == SYSTEM_ID
    ).order_by(V9SystemSignal.ts.desc()).limit(limit).all()

    return {"signals": [
        {"id": r.id, "ts": r.ts.isoformat(), "system_id": r.system_id,
         "classification": r.classification, "direction": r.direction,
         "confidence": r.confidence, "payload": r.payload}
        for r in rows
    ]}


@router.get("/patterns")
def get_woodies_patterns(
    db: Session = Depends(get_db),
):
    """Run pattern detection on current bar history and return results."""
    highs, lows, closes, timestamps = _load_bar_history(db)
    if not closes:
        return {"patterns": []}

    patterns = detect_patterns(highs, lows, closes, timestamps)
    return {"patterns": [p.model_dump() for p in patterns]}


@router.post("/process")
def process_woodies_bar(
    db: Session = Depends(get_db),
):
    """Process latest bar: detect patterns → persist signals to DB.

    Called by the bridge on each new 30-min bar. This enables SHADOW mode
    by ensuring signals are logged to v9_system_signals.
    """
    from datetime import datetime, timezone

    highs, lows, closes, timestamps = _load_bar_history(db)
    if not closes:
        return {"signals_written": 0, "state": None}

    state = compute_state(highs, lows, closes, timestamps)

    # Persist signals if classification is not NO_SETUP
    signals_written = 0
    if state.classification != "NO_SETUP" and state.active_patterns:
        for p in state.active_patterns:
            signal = V9SystemSignal(
                ts=datetime.fromtimestamp(p.ts, tz=timezone.utc),
                system_id=SYSTEM_ID,
                classification=state.classification,
                direction=p.direction,
                confidence=p.confidence,
                payload={
                    "pattern": p.pattern,
                    "group": p.group,
                    "cci_at_signal": p.cci_at_signal,
                    "bar_index": p.bar_index,
                    "details": p.details,
                    "sizing": "STANDARD" if state.classification == "TACTICAL" else "AGGRESSIVE",
                },
            )
            db.add(signal)
            signals_written += 1
        db.commit()

    return {"signals_written": signals_written, "state": state.model_dump()}
