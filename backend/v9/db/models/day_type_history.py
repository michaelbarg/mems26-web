"""V9 model: Day Type classification history (System 1).

V9 Hybrid Enhancement (3a-S4 REVISED):
- Original V1 columns retained for backward compat (date, status, confidence, etc.)
- V9 columns added to match DayTypeClassification dataclass (13 fields)
- session_date is an alias for date (V9 naming convention)
- UPSERT pattern: one row per session_date, continuously updated
"""

from sqlalchemy import Column, String, Float, Integer, Date, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK, JsonColumn


class V9DayTypeHistory(Base):
    __tablename__ = "v9_day_type_history"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)

    # V1 columns (retained for backward compat with existing api.py writes)
    date = Column(Date, nullable=False, unique=True, index=True)
    day_type = Column(String(32), nullable=False)
    status = Column(String(16), nullable=True)  # V1 legacy, nullable for V9 rows
    confidence = Column(Float, nullable=True)    # V1 legacy, V9 uses probability
    ib_high = Column(Float, nullable=True)
    ib_low = Column(Float, nullable=True)
    ib_width_ticks = Column(Integer, nullable=True)
    opening_type = Column(String(32), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    reasoning_notes = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # V9 columns (from DayTypeClassification dataclass, 3a-S4 REVISED)
    probability = Column(Float, nullable=True)
    directional_certainty = Column(String(8), nullable=True)  # HIGH/MEDIUM/LOW
    trading_confidence = Column(String(8), nullable=True)      # HIGH/MEDIUM/LOW
    ib_width = Column(Float, nullable=True)                    # IB range in points
    ib_width_class = Column(String(8), nullable=True)          # NARROW/MEDIUM/WIDE
    active_zohar_rules = Column(JsonColumn, nullable=True, default=list)
    last_updated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
