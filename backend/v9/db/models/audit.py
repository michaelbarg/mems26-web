"""V9 model: Audit events — append-only log of all Event Bus events (AP-DB02)."""

from sqlalchemy import Column, String, Float, BigInteger, Index
from sqlalchemy.sql import func
from backend.v9.db.session import Base
from backend.v9.db.models._types import JsonColumn, BigIntPK


class AuditEvent(Base):
    __tablename__ = "v9_audit_events"

    id = Column(BigIntPK, primary_key=True, autoincrement=True)
    ts_ms = Column(BigInteger, nullable=False)
    event_type = Column(String(64), nullable=False)
    correlation_id = Column(String(24), nullable=False)
    source = Column(String(64), nullable=False, default="unknown")
    price = Column(Float, nullable=True)
    payload = Column(JsonColumn, nullable=True)
    stream_id = Column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_audit_event_type_ts", "event_type", ts_ms.desc()),
        Index("ix_audit_correlation", "correlation_id"),
        Index("ix_audit_dedup", "stream_id", unique=True),
    )
