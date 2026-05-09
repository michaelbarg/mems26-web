"""V9 model: System configs."""

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9SystemConfig(Base):
    __tablename__ = "v9_system_configs"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    system_id = Column(Integer, nullable=False)
    mode = Column(String(10), nullable=False)
    params = Column(JsonColumn, nullable=False, default={})
    locked_at = Column(DateTime(timezone=True))
    locked_by = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
