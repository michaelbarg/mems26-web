"""V9 model: Footprint markers (System 3)."""

from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK, JsonColumn


class V9FootprintMarker(Base):
    __tablename__ = "v9_footprint_markers"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    classification = Column(String(32), nullable=False)
    cluster_top = Column(Float, nullable=True)
    cluster_bottom = Column(Float, nullable=True)
    empty_zone_top = Column(Float, nullable=True)
    empty_zone_bottom = Column(Float, nullable=True)
    pattern = Column(String(64), nullable=True)
    zohar_signals_json = Column(JsonColumn, nullable=True)
    industry_signals_json = Column(JsonColumn, nullable=True)
    confluence_total = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
