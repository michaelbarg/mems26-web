"""V9 API: System markers CRUD."""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.v9.db.session import get_db
from backend.v9.db.models import V9SystemMarker
from backend.v9.api.v9.auth import verify_bridge_token
from backend.v9.api.v9.ws_manager import publish_event, CHANNEL_MARKERS

router = APIRouter(prefix="/api/v9/markers", tags=["v9-markers"])


class MarkerIn(BaseModel):
    ts: Optional[float] = None
    system_id: int
    marker_type: str
    price: Optional[float] = None
    color: Optional[str] = None
    label: Optional[str] = None
    border_style: Optional[str] = None
    payload: Optional[dict] = None


class MarkerBatchIn(BaseModel):
    markers: List[MarkerIn]


def _ts(unix_ts) -> datetime:
    if unix_ts is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(float(unix_ts), tz=timezone.utc)


@router.post("")
def post_markers(
    batch: MarkerBatchIn,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    created = 0
    for m in batch.markers:
        row = V9SystemMarker(
            ts=_ts(m.ts),
            system_id=m.system_id,
            marker_type=m.marker_type,
            price=m.price,
            color=m.color,
            label=m.label,
            border_style=m.border_style,
            payload=m.payload,
        )
        db.add(row)
        created += 1
    db.commit()
    system_ids = set(m.system_id for m in batch.markers)
    for sid in system_ids:
        publish_event(CHANNEL_MARKERS.format(system_id=sid), {"count": created})
    return {"ok": True, "inserted": created}


@router.get("")
def get_markers(
    system_id: Optional[int] = None,
    marker_type: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    q = db.query(V9SystemMarker)
    if system_id is not None:
        q = q.filter(V9SystemMarker.system_id == system_id)
    if marker_type:
        q = q.filter(V9SystemMarker.marker_type == marker_type)
    rows = q.order_by(V9SystemMarker.ts.desc()).limit(limit).all()
    return {"markers": [
        {"id": r.id, "ts": r.ts.isoformat(), "system_id": r.system_id,
         "type": r.marker_type, "price": r.price, "color": r.color,
         "label": r.label, "border_style": r.border_style, "payload": r.payload}
        for r in rows
    ]}
