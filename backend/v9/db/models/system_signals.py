"""V9 model: System signals."""

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9SystemSignal(Base):
    __tablename__ = "v9_system_signals"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    system_id = Column(Integer, nullable=False)
    classification = Column(String(30))
    direction = Column(String(10))
    confidence = Column(Float)
    payload = Column(JsonColumn)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
