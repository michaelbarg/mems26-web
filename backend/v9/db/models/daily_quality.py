"""V9 model: Daily quality reports."""

from sqlalchemy import Column, String, Float, Integer, Date, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9DailyQualityReport(Base):
    __tablename__ = "v9_daily_quality_reports"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    mode = Column(String(10), nullable=False)
    system_id = Column(Integer, nullable=False)
    trade_count = Column(Integer, default=0)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    max_dd = Column(Float)
    recommendations = Column(JsonColumn)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
