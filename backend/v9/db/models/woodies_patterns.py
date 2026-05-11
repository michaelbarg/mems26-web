"""V9 model: Woodies CCI patterns (System 4)."""

from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9WoodiesPattern(Base):
    __tablename__ = "v9_woodies_patterns"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    pattern = Column(String(16), nullable=False)
    group = Column(String(16), nullable=False)
    direction = Column(String(8), nullable=False)
    confidence = Column(Float, nullable=False)
    cci_value = Column(Float, nullable=True)
    trend_state = Column(String(32), nullable=True)
    entry_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
