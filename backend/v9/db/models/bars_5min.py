"""V9 model: 5-minute OHLCV bars."""

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9Bar5Min(Base):
    __tablename__ = "v9_bars_5min"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, default="MES")
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False, default=0)
    poc_vol = Column(Integer)
    vah = Column(Float)
    val = Column(Float)
    cumulative_delta = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
