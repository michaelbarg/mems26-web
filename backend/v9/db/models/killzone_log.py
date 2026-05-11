"""V9 model: Killzone session log (System 6)."""

from sqlalchemy import Column, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import BigIntPK


class V9KillzoneLog(Base):
    __tablename__ = "v9_killzone_log"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    current_killzone = Column(String(32), nullable=False)
    quality = Column(String(4), nullable=False)
    sizing_modifier = Column(Float, nullable=False)
    is_blocked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
