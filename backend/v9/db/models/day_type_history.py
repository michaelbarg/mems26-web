"""V9 model: Day Type classification history (System 1)."""

from sqlalchemy import Column, String, Float, Integer, Date, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9DayTypeHistory(Base):
    __tablename__ = "v9_day_type_history"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    day_type = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False)
    confidence = Column(Float, nullable=False)
    ib_high = Column(Float, nullable=True)
    ib_low = Column(Float, nullable=True)
    ib_width_ticks = Column(Integer, nullable=True)
    opening_type = Column(String(16), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    reasoning_notes = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
