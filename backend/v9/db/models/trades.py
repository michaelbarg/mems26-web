"""V9 model: Trades — all 3 modes."""

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9Trade(Base):
    __tablename__ = "v9_trades"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    mode = Column(String(10), nullable=False)
    dominant_system = Column(Integer, nullable=False)
    direction = Column(String(10), nullable=False)
    entry_ts = Column(DateTime(timezone=True))
    entry_price = Column(Float)
    stop_initial = Column(Float)
    stop_final = Column(Float)
    t1_price = Column(Float)
    t1_filled_at = Column(DateTime(timezone=True))
    t2_price = Column(Float)
    t2_filled_at = Column(DateTime(timezone=True))
    t3_price = Column(Float)
    exit_ts = Column(DateTime(timezone=True))
    exit_price = Column(Float)
    exit_reason = Column(String(30))
    pnl_usd = Column(Float)
    pnl_r = Column(Float)
    outcome = Column(String(10))
    quality_review = Column(JsonColumn)
    sierra_bracket_id = Column(String(50))
    context_json = Column(JsonColumn)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    management_log = relationship("V9TradeManagementLog", back_populates="trade", cascade="all, delete-orphan")
