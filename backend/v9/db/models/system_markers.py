"""V9 model: System visual markers for chart overlay."""

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class V9SystemMarker(Base):
    __tablename__ = "v9_system_markers"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    system_id = Column(Integer, nullable=False)
    marker_type = Column(String(30), nullable=False)
    price = Column(Float)
    color = Column(String(20))
    label = Column(String(100))
    border_style = Column(String(20))
    payload = Column(JsonColumn)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
