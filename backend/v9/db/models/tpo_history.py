"""V9 model: TPO profile history (System 5)."""

from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9TpoHistory(Base):
    __tablename__ = "v9_tpo_history"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    poc = Column(Float, nullable=False)
    vah = Column(Float, nullable=False)
    val = Column(Float, nullable=False)
    ib_high = Column(Float, nullable=True)
    ib_low = Column(Float, nullable=True)
    profile_shape = Column(String(4), nullable=True)
    poc_migration_direction = Column(String(8), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
