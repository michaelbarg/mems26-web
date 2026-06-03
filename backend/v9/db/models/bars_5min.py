"""V9 model: 5-minute OHLCV bars."""

from sqlalchemy import Column, String, Float, Integer, DateTime, UniqueConstraint, SmallInteger
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9Bar5Min(Base):
    __tablename__ = "v9_bars_5min"
    # P30 G8 (2026-05-20): enforce per-bar uniqueness so the bridge can't
    # race two concurrent POSTs into duplicate rows. Backing migration in
    # `backend/v9/db/migrations/versions/V9_011_bars_5min_unique_ts_symbol.sql`.
    __table_args__ = (
        UniqueConstraint("ts", "symbol", name="ux_v9_bars_5min_ts_symbol"),
    )

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
    is_synthetic = Column(SmallInteger, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
