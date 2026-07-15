"""V9 model: Trades — all 3 modes (shadow/demo/live).

Section 6 of 3-Mode Trading Spec V3 FINAL.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship, validates
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
    t4 = Column(Float)  # Michael 07-15: 4th contract runner (T0 ladder)

    # Target/stop hit timestamps
    t1_hit_ts = Column(DateTime(timezone=True))
    t2_hit_ts = Column(DateTime(timezone=True))
    t3_hit_ts = Column(DateTime(timezone=True))
    t4_hit_ts = Column(DateTime(timezone=True))  # Michael 07-15
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

    # G1: queryable calibration cuts (promoted from cross_context JSON)
    # Source: same snapshot as cross_context, populated at entry time.
    # Silent/missing → NULL (Rule 1: honest failure > synthetic value).
    day_type_at_entry = Column(String(20), nullable=True, index=True)
    pattern_id_at_entry = Column(String(40), nullable=True, index=True)
    session_at_entry = Column(String(20), nullable=True, index=True)

    # Synthetic/test data flag (migration 019)
    is_synthetic = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @validates("exit_reason")
    def _truncate_exit_reason(self, _key, value):
        """Guard: truncate to varchar(30) — trade 303 crash (ea868cc)."""
        if value and len(value) > 30:
            value = value[:30]
        return value

    @validates("outcome")
    def _truncate_outcome(self, _key, value):
        """Guard: truncate to varchar(10) — trade 329/331 crash (D2, 07-09 18:45)."""
        if value and len(value) > 10:
            value = value[:10]
        return value

    management_log = relationship("V9TradeManagementLog", back_populates="trade", cascade="all, delete-orphan")
