"""V9 API: System signals CRUD."""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.v9.db.session import get_db
from backend.v9.db.models import V9SystemSignal
from backend.v9.api.v9.auth import verify_bridge_token

router = APIRouter(prefix="/api/v9/signals", tags=["v9-signals"])


class SignalIn(BaseModel):
    ts: Optional[float] = None
    system_id: int
    classification: Optional[str] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    payload: Optional[dict] = None


class SignalBatchIn(BaseModel):
    signals: List[SignalIn]


def _ts(unix_ts) -> datetime:
    if unix_ts is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(float(unix_ts), tz=timezone.utc)


@router.post("")
def post_signals(
    batch: SignalBatchIn,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    created = 0
    for s in batch.signals:
        row = V9SystemSignal(
            ts=_ts(s.ts),
            system_id=s.system_id,
            classification=s.classification,
            direction=s.direction,
            confidence=s.confidence,
            payload=s.payload,
        )
        db.add(row)
        created += 1
    db.commit()
    return {"ok": True, "inserted": created}


@router.get("")
def get_signals(
    system_id: Optional[int] = None,
    classification: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    q = db.query(V9SystemSignal)
    if system_id is not None:
        q = q.filter(V9SystemSignal.system_id == system_id)
    if classification:
        q = q.filter(V9SystemSignal.classification == classification)
    rows = q.order_by(V9SystemSignal.ts.desc()).limit(limit).all()
    return {"signals": [
        {"id": r.id, "ts": r.ts.isoformat(), "system_id": r.system_id,
         "classification": r.classification, "direction": r.direction,
         "confidence": r.confidence, "payload": r.payload}
        for r in rows
    ]}
