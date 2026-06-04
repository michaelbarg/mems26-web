"""V9 model: 5-min continuous bars from Sierra chart#5 (24h coverage)."""

from sqlalchemy import Column, String, Float, Integer, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9Bar5MinContinuous(Base):
    __tablename__ = "v9_bars_5min_continuous"
    __table_args__ = (
        UniqueConstraint("ts", "symbol", name="uq_v9_bars_5min_cont_ts_symbol"),
    )

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, default="MES")
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False, default=0)
    delta = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
