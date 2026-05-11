"""Base Pydantic Event model — all events inherit from this."""

import time
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event for the MEMS26 Event Bus.

    Every event on the bus carries these common fields.
    """

    event_type: str
    correlation_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    ts_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    source: str = "unknown"
    version: str = "1.0"
    payload: Dict[str, Any] = Field(default_factory=dict)

    def to_stream_dict(self) -> Dict[str, str]:
        """Serialize for Redis Streams XADD (all values must be strings)."""
        return {
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "ts_ms": str(self.ts_ms),
            "source": self.source,
            "version": self.version,
            "data": self.model_dump_json(),
        }

    @classmethod
    def from_stream_dict(cls, raw: Dict[str, str]) -> "BaseEvent":
        """Deserialize from Redis Streams XREAD entry."""
        return cls.model_validate_json(raw["data"])
