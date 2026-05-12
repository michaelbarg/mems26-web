"""V9 model: 5-min system state for crash recovery (Section 3, D-077)."""

from sqlalchemy import Column, String, Float, Integer, Date, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn


class V9FiveMinState(Base):
    __tablename__ = "v9_five_min_state"

    session_date = Column(Date, primary_key=True)
    mode = Column(String(50), nullable=False, default="WAITING_OPEN")
    first_hour_buffer = Column(JsonColumn, nullable=True)
    opening_type = Column(String(50), nullable=True)
    choppiness_score = Column(Integer, nullable=True)
    last_processed_ts = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
