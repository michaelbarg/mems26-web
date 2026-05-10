"""Day Type Engine API — GET state, GET history, POST process."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from .models import V9DayTypeState
from .schemas import (
    BarInput, DayTypeState, DayTypeStateResponse,
    DayTypeHistoryResponse, ProcessBarResponse,
)
from .state_machine import DayTypeStateMachine

router = APIRouter(prefix="/v9/day_type", tags=["v9-day-type"])

# Module-level state machine instance (reset daily by bridge)
_engine: Optional[DayTypeStateMachine] = None


def _get_engine() -> DayTypeStateMachine:
    global _engine
    if _engine is None:
        _engine = DayTypeStateMachine()
    return _engine


def reset_engine():
    """Reset the state machine (called at session start)."""
    global _engine
    _engine = DayTypeStateMachine()


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("/state", response_model=DayTypeStateResponse)
def get_state():
    """Return current Day Type Engine state."""
    engine = _get_engine()
    state = engine._build_state(
        BarInput(ts=0, session_min=0, open=0, high=0, low=0, close=0)
    )
    return DayTypeStateResponse(state=state)


@router.get("/history", response_model=DayTypeHistoryResponse)
def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return recent day type state history from DB."""
    rows = (
        db.query(V9DayTypeState)
        .order_by(V9DayTypeState.ts.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for row in rows:
        items.append(DayTypeState(
            stage=row.stage,
            day_type=row.day_type or "UNKNOWN",
            confidence=row.confidence or 0.0,
            lock_state=row.lock_state or "PENDING",
            opening_type=row.opening_type or "UNKNOWN",
            ib_width=row.ib_width_class or "UNKNOWN",
            behavior=row.behavior or "DEVELOPING",
            meta=row.meta or {},
        ))

    return DayTypeHistoryResponse(items=items, count=len(items))


@router.post("/process", response_model=ProcessBarResponse)
def process_bar(bar: BarInput, db: Session = Depends(get_db)):
    """Process a single bar through the Day Type Engine.

    Used by the bridge to feed bars into the state machine.
    """
    engine = _get_engine()
    prev_stage = engine.stage

    state = engine.process_bar(bar)
    stage_changed = state.stage != prev_stage

    # Persist to DB
    record = V9DayTypeState(
        ts=datetime.fromtimestamp(bar.ts, tz=timezone.utc),
        stage=state.stage.value,
        day_type=state.day_type.value,
        classification=state.day_type.value if state.lock_state == "LOCKED" else None,
        confidence=state.confidence,
        ib_width_class=state.ib_width.value if state.ib_width else None,
        opening_type=state.opening_type.value if state.opening_type else None,
        behavior=state.behavior.value if state.behavior else None,
        lock_state=state.lock_state.value if state.lock_state else None,
        meta=state.meta,
    )
    db.add(record)
    db.commit()

    return ProcessBarResponse(state=state, stage_changed=stage_changed)
