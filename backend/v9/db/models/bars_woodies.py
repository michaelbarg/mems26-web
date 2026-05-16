"""V9 model: Woodies CCI bars (D-074: 5-min primary, 30-min legacy)."""

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9Bar5MinWoodies(Base):
    """D-074: primary S4 table — 5-min Woodies bars."""
    __tablename__ = "v9_bars_5min_woodies"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, default="MES")
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False, default=0)
    cci_14 = Column(Float)
    cci_6_tcci = Column(Float)
    lsma_value = Column(Float)
    swi_value = Column(Float)
    czi_value = Column(Float)
    ema_34 = Column(Float)
    trend_state = Column(String(10))
    predictor_next_cci = Column(Float)
    zlr_detected = Column(Boolean, default=False)
    zlr_direction = Column(String(10))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class V9Bar30MinWoodies(Base):
    """Legacy 30-min Woodies bars — kept for historical replay only."""
    __tablename__ = "v9_bars_30min_woodies"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, default="MES")
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False, default=0)
    cci_14 = Column(Float)
    cci_6_tcci = Column(Float)
    lsma_value = Column(Float)
    swi_value = Column(Float)
    czi_value = Column(Float)
    ema_34 = Column(Float)
    trend_state = Column(String(10))
    predictor_next_cci = Column(Float)
    zlr_detected = Column(Boolean, default=False)
    zlr_direction = Column(String(10))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
