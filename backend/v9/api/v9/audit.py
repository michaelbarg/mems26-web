"""Audit query endpoints — read from v9_audit_events table."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from backend.v9.db.models.audit import AuditEvent

router = APIRouter(tags=["v9-audit"])


@router.get("/api/v9/audit/events")
def list_events(
    event_type: str = Query(None),
    start_ms: int = Query(None),
    end_ms: int = Query(None),
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    """List audit events with optional filters."""
    q = db.query(AuditEvent).order_by(AuditEvent.ts_ms.desc())
    if event_type:
        q = q.filter(AuditEvent.event_type == event_type)
    if start_ms:
        q = q.filter(AuditEvent.ts_ms >= start_ms)
    if end_ms:
        q = q.filter(AuditEvent.ts_ms <= end_ms)
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id,
            "ts_ms": r.ts_ms,
            "event_type": r.event_type,
            "correlation_id": r.correlation_id,
            "source": r.source,
            "price": r.price,
            "stream_id": r.stream_id,
        }
        for r in rows
    ]


@router.get("/api/v9/audit/replay")
def replay_chain(
    correlation_id: str = Query(...),
    db: Session = Depends(get_db),
):
    """Replay full causal chain by correlation_id."""
    rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.correlation_id == correlation_id)
        .order_by(AuditEvent.ts_ms.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "ts_ms": r.ts_ms,
            "event_type": r.event_type,
            "source": r.source,
            "price": r.price,
            "payload": r.payload,
        }
        for r in rows
    ]


@router.get("/api/v9/audit/stats")
def audit_stats(db: Session = Depends(get_db)):
    """Counts per event_type."""
    rows = (
        db.query(AuditEvent.event_type, func.count(AuditEvent.id))
        .group_by(AuditEvent.event_type)
        .all()
    )
    total = db.query(func.count(AuditEvent.id)).scalar() or 0
    return {
        "total": total,
        "by_type": {event_type: count for event_type, count in rows},
    }
