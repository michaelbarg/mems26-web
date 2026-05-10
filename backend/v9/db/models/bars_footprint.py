"""V9 model: Footprint bars — separate from tick reversal bars."""

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9BarFootprint(Base):
    __tablename__ = "v9_bars_footprint"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, default="MES")
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False, default=0)
    delta = Column(Float)
    poc_price = Column(Float)
    poc_vol = Column(Integer)
    levels = Column(JsonColumn)
    stacked_buy = Column(Integer)
    stacked_sell = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
