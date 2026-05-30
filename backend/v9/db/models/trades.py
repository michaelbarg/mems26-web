"""V9 model: Trades — all 3 modes (shadow/demo/live).

Section 6 of 3-Mode Trading Spec V3 FINAL.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9Trade(Base):
    __tablename__ = "v9_trades"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    mode = Column(String(10), nullable=False)              # shadow / demo / live
    firing_system = Column(Integer, nullable=False)        # 1, 2, or 4
    direction = Column(String(10), nullable=False)         # LONG / SHORT
    state = Column(String(10), nullable=False, default="PENDING")  # PENDING/FILLED/PARTIAL/CLOSED

    # Entry
    entry_ts = Column(DateTime(timezone=True))
    entry_price = Column(Float)

    # Bracket levels
    stop = Column(Float)
    t1 = Column(Float)
    t2 = Column(Float)
    t3 = Column(Float)

    # Target/stop hit timestamps
    t1_hit_ts = Column(DateTime(timezone=True))
    t2_hit_ts = Column(DateTime(timezone=True))
    t3_hit_ts = Column(DateTime(timezone=True))
    stop_hit_ts = Column(DateTime(timezone=True))

    # Exit
    exit_ts = Column(DateTime(timezone=True))
    exit_price = Column(Float)
    exit_reason = Column(String(30))

    # PnL — per-contract (c1/c2/c3), NOT 3x
    pnl_usd = Column(Float)
    pnl_r = Column(Float)

    # Outcome
    outcome = Column(String(10))                           # WIN / LOSS / BE

    # Quality — nullable, set by W12 EOD agent
    quality = Column(JsonColumn, nullable=True)

    # Cross-system context at entry time
    cross_context = Column(JsonColumn)

    # Sierra bracket reference
    sierra_bracket_id = Column(String(50))

    # Synthetic/test data flag (migration 019)
    is_synthetic = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    management_log = relationship("V9TradeManagementLog", back_populates="trade", cascade="all, delete-orphan")
