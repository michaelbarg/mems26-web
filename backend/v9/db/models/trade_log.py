"""V9 model: Trade management log."""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9TradeManagementLog(Base):
    __tablename__ = "v9_trade_management_log"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    trade_id = Column(ForeignKey("v9_trades.id", ondelete="CASCADE"), nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    action = Column(String(30), nullable=False)
    value = Column(JsonColumn)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trade = relationship("V9Trade", back_populates="management_log")
