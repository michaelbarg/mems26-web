"""V9 API: trade review marks (read/write to v9_trades.quality.review).

Lets the in-dashboard marker SUBMIT the user's marks + notes to the DB so they
persist across browsers / origins (replacing the fragile per-origin localStorage
that lost marks between localhost / 127.0.0.1 / file://), and become a queryable
calibration asset for deriving lessons. POST writes one trade's review; GET
returns all reviews so the marker hydrates from the DB on load.

Additive and isolated — does not change any existing trade route (§7a).
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.v9.db.session import get_db
from backend.v9.db.models.trades import V9Trade
from backend.v9.api.v9.auth import verify_bridge_token

router = APIRouter(tags=["v9-trade-review"])


class ReviewIn(BaseModel):
    # entry / stop1-3 / t1-3 (numbers) + no_entry (bool) + note (str) + pat/day_type/dir
    marks: Dict[str, Any] = {}


@router.post("/api/v9/trades/{trade_id}/review")
def post_review(
    trade_id: int,
    body: ReviewIn,
    db: Session = Depends(get_db),
    _token: str = Depends(verify_bridge_token),
):
    t = db.query(V9Trade).filter(V9Trade.id == trade_id).first()
    if not t:
        raise HTTPException(status_code=404, detail=f"trade {trade_id} not found")
    q = dict(t.quality or {})
    q["review"] = {**body.marks, "by": "michael", "ts": datetime.now(timezone.utc).isoformat()}
    t.quality = q  # reassign so SQLAlchemy detects the JSON mutation
    db.commit()
    return {"ok": True, "id": trade_id}


@router.get("/api/v9/trade_reviews")
def get_reviews(db: Session = Depends(get_db), _token: str = Depends(verify_bridge_token)):
    rows = db.query(V9Trade.id, V9Trade.quality).filter(V9Trade.quality.isnot(None)).all()
    out: Dict[str, Any] = {}
    for tid, q in rows:
        if isinstance(q, dict) and isinstance(q.get("review"), dict):
            out[str(tid)] = q["review"]
    return {"reviews": out}
