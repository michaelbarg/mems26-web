"""T-390: V9 model for the decision-vectors log table."""

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from backend.v9.db.models._types import BigIntPK, JsonColumn
from backend.v9.db.session import Base


class V9DecisionVector(Base):
    __tablename__ = "v9_decision_vectors"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False)
    kind = Column(String(20), nullable=False)   # 'DECISION' or 'BAR'
    system = Column(Integer, nullable=True)
    classification = Column(String(100), nullable=True)
    direction = Column(String(10), nullable=True)
    entry = Column(Numeric, nullable=True)
    phase = Column(String(5), nullable=True)
    blocked_by = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    mode_result = Column(JsonColumn, nullable=True)
    vector = Column(JsonColumn, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
