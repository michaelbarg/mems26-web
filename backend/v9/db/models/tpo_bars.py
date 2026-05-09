"""V9 model: TPO (Time Price Opportunity) bars."""

from sqlalchemy import Column, String, Float, Integer, DateTime, CHAR
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9TpoBar(Base):
    __tablename__ = "v9_tpo_bars"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, default="MES")
    letter = Column(CHAR(1), nullable=False)
    price = Column(Float, nullable=False)
    level = Column(Integer, nullable=False)
    period_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
