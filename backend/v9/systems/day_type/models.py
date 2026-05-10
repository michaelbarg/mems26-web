"""Day Type Engine — SQLAlchemy model for persisting state."""

from sqlalchemy import Column, String, Float, DateTime, func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9DayTypeState(Base):
    """Persisted state snapshot from the Day Type Engine."""

    __tablename__ = "v9_day_type_state"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    stage = Column(String(20), nullable=False)          # A1, A2, ..., C3
    day_type = Column(String(20))                       # one of 6 types or UNKNOWN
    classification = Column(String(30))                 # same as day_type when locked
    confidence = Column(Float, default=0.0)
    ib_width_class = Column(String(10))                 # NARROW, MEDIUM, WIDE
    opening_type = Column(String(30))                   # OPEN_DRIVE, etc.
    behavior = Column(String(30))                       # TRENDING_UP, etc.
    lock_state = Column(String(20))                     # PENDING, LOCKED, LOCKED_LOW_CONF
    meta = Column(JsonColumn)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
