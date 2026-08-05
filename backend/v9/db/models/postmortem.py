"""V9 model: Post-mortem summary for losing trades (POST_MORTEM_V1).

Pure observability — written on every LOSS close (live + shadow).
One row per trade_id. Weekly aggregate feeds calibration.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9Postmortem(Base):
    __tablename__ = "v9_postmortem"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, nullable=False, unique=True, index=True)
    mode = Column(String(10), nullable=False)               # shadow / demo / live
    firing_system = Column(Integer)

    # Context at entry vs EOD truth
    day_type_at_entry = Column(String(30), nullable=True)
    day_type_eod = Column(String(30), nullable=True)
    day_type_mismatch = Column(Integer, default=0)           # 1 if entry != eod

    pattern_id = Column(String(40), nullable=True)
    session_at_entry = Column(String(20), nullable=True)
    direction = Column(String(10), nullable=True)

    # Trade metrics
    entry_price = Column(Float)
    exit_price = Column(Float)
    stop = Column(Float)
    exit_reason = Column(String(30))
    pnl_usd = Column(Float)
    pnl_r = Column(Float)
    mae_pts = Column(Float)
    mfe_pts = Column(Float)

    # Range position at entry (0.0=low, 1.0=high)
    range_position = Column(Float, nullable=True)

    # S7 score (computed even when flag OFF)
    s7_score = Column(Float, nullable=True)
    s7_sizing = Column(Integer, nullable=True)
    s7_components = Column(JsonColumn, nullable=True)

    # Gates that passed / near-blocked
    gates_passed = Column(JsonColumn, nullable=True)

    # Exit mechanism
    exit_mechanism = Column(String(30), nullable=True)       # STOP_HIT / MAE_SCRATCH / etc.

    # Root verdict (closed taxonomy)
    root_verdict = Column(String(30), nullable=True)
    # One of: WRONG_CLASS / LATE_ENTRY / TIGHT_STOP / MANAGEMENT / NORMAL_NOISE
    root_detail = Column(Text, nullable=True)

    # Report path
    report_path = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
