"""V9 model: Account status."""

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9AccountStatus(Base):
    __tablename__ = "v9_account_status"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    mode = Column(String(10), nullable=False)
    daily_pnl = Column(Float, default=0)
    trade_count = Column(Integer, default=0)
    margin_used_pct = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
