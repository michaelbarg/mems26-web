"""V9 model: 5-Min pattern setups (System 2)."""

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9FiveMinSetup(Base):
    __tablename__ = "v9_five_min_setups"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    pattern = Column(String(32), nullable=False)
    direction = Column(String(8), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_price = Column(Float, nullable=False)
    t1_price = Column(Float, nullable=True)
    t2_price = Column(Float, nullable=True)
    time_stop_min = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=False)
    day_type_at_fire = Column(String(32), nullable=True)
    killzone_at_fire = Column(String(32), nullable=True)
    pattern_type = Column(String(48), nullable=True)
    setup_kind = Column(String(16), nullable=True)  # REACTIVE or INITIATIVE
    bar_stage = Column(Integer, nullable=True)       # which bar in pattern (1-4)
    cot_at_fire = Column(Float, nullable=True)
    amt_at_fire = Column(Float, nullable=True)
    variant_tag = Column(String(16), nullable=True)      # primary variant: A_VSA / B_RVOL / C_STRICT
    variants_passed = Column(String(64), nullable=True)   # comma-joined list of passing variants
    created_at = Column(DateTime(timezone=True), server_default=func.now())
