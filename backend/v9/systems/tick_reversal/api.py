"""Tick Reversal observer — read-only API.

GET /v9/tick_reversal/signals — returns recent S3 signals from DB.
OBSERVER ONLY: no POST endpoints that create trades.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from backend.v9.db.models import V9SystemSignal
from backend.v9.api.v9.auth import verify_bridge_token

router = APIRouter(prefix="/v9/tick_reversal", tags=["v9-tick-reversal"])

SYSTEM_ID = 3


@router.get("/signals")
def get_tick_reversal_signals(
    limit: int = Query(50, le=500),
    classification: Optional[str] = None,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    """Read-only: fetch recent System 3 signals."""
    q = db.query(V9SystemSignal).filter(V9SystemSignal.system_id == SYSTEM_ID)

    if classification:
        q = q.filter(V9SystemSignal.classification == classification)

    rows = q.order_by(V9SystemSignal.ts.desc()).limit(limit).all()

    return {"signals": [
        {
            "id": r.id,
            "ts": r.ts.isoformat() if r.ts else None,
            "system_id": r.system_id,
            "classification": r.classification,
            "direction": r.direction,
            "confidence": r.confidence,
            "confluence_total": r.payload.get("confluence", {}).get("total") if r.payload else None,
            "pattern": r.payload.get("pattern", {}).get("detected") if r.payload else None,
            "payload": r.payload,
        }
        for r in rows
    ]}


@router.get("/signals/summary")
def get_tick_reversal_summary(
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    """Read-only: today's setup count by classification."""
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    rows = (
        db.query(V9SystemSignal.classification, func.count())
        .filter(
            V9SystemSignal.system_id == SYSTEM_ID,
            V9SystemSignal.ts >= today_start,
        )
        .group_by(V9SystemSignal.classification)
        .all()
    )

    return {
        "system_id": SYSTEM_ID,
        "date": today_start.date().isoformat(),
        "counts": {cls: cnt for cls, cnt in rows},
    }
