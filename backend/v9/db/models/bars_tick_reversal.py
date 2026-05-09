"""V9 model: Tick reversal bars (15-tick and 12-tick)."""

from sqlalchemy import Column, String, Float, Integer, SmallInteger, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9BarTickReversal(Base):
    __tablename__ = "v9_bars_tick_reversal"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, default="MES")
    tick_size = Column(Integer, nullable=False)  # 15 or 12
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False, default=0)
    ask_vol = Column(Integer)
    bid_vol = Column(Integer)
    delta = Column(Float)
    direction = Column(SmallInteger)
    footprint_json = Column(JsonColumn)
    cluster_data = Column(JsonColumn)
    empty_zones = Column(JsonColumn)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
