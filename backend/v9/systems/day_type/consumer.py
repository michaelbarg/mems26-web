"""DayTypeConsumer — subscribes to day_type.classification events.

LOCKED 15/5 (Hybrid, option D): UPSERT by session_date.
Source: PROMPT 3a-S4 REVISED Section B.

Persistence strategy:
- ONE ROW per session_date (UNIQUE constraint on date column)
- UPSERT pattern: continuously updates same row throughout the day
- Latest classification wins per day
- Final state at 16:00 ET = closing classification

Uses SQLAlchemy merge pattern for cross-database compatibility
(SQLite local dev, PostgreSQL production).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.v9.db.models.day_type_history import V9DayTypeHistory

logger = logging.getLogger(__name__)


class DayTypeConsumer:
    """Consumes DayTypeClassification events and persists to v9_day_type_history.

    Usage:
        consumer = DayTypeConsumer(db_session_factory=SessionLocal)
        consumer.consume(classification_dict)
    """

    EVENT_STREAM = "mems26:events:day_type.classification"

    def __init__(self, db_session_factory):
        self._db_session_factory = db_session_factory

    def consume(self, classification_event: dict) -> None:
        """UPSERT into v9_day_type_history keyed by session_date.

        Input: dict matching day_type_classification.yaml schema fields:
            timestamp, day_type, probability, directional_certainty,
            trading_confidence, ib_h, ib_l, ib_width, ib_width_class,
            opening_type, last_updated_at, reasoning_notes, active_zohar_rules

        Optional V1-legacy fields (also accepted to avoid NOT NULL drift between
        the SQLAlchemy model and the production SQLite schema — see migration
        014 comment): ``lock_state`` ("LOCKED" / "LOCKED_LOW_CONF" / "PENDING").
        """
        session_date = self._extract_session_date(
            classification_event["timestamp"]
        )

        # P31 §C fix: the production v9_day_type_history schema still carries
        # `status NOT NULL` and `confidence NOT NULL` (migration 014 noted that
        # SQLite cannot ALTER COLUMN to drop NOT NULL — see header comment).
        # The SQLAlchemy model marks both as nullable=True, so the in-memory
        # test DB created via Base.metadata.create_all() lets nulls through,
        # but the live SQLite DB rejects them with IntegrityError. The error
        # was being swallowed by `_logger.debug` in main._day_type_on_bar,
        # so v9_day_type_history stayed empty and the V9 day_type API endpoint
        # always returned `classified: false` → V1 demoted. Always populate
        # both legacy columns so the live UPSERT cannot drift again.
        legacy_status = self._map_legacy_status(classification_event)
        legacy_confidence = self._map_legacy_confidence(classification_event)

        session: Session = self._db_session_factory()
        try:
            existing: Optional[V9DayTypeHistory] = (
                session.query(V9DayTypeHistory)
                .filter(V9DayTypeHistory.date == session_date)
                .first()
            )

            if existing is not None:
                # UPDATE existing row
                existing.day_type = classification_event["day_type"]
                existing.status = legacy_status
                existing.confidence = legacy_confidence
                existing.probability = classification_event["probability"]
                existing.directional_certainty = classification_event["directional_certainty"]
                existing.trading_confidence = classification_event["trading_confidence"]
                existing.ib_high = classification_event.get("ib_h")
                existing.ib_low = classification_event.get("ib_l")
                existing.ib_width = classification_event.get("ib_width")
                existing.ib_width_class = classification_event.get("ib_width_class")
                existing.opening_type = classification_event.get("opening_type")
                existing.last_updated_at = self._parse_datetime(
                    classification_event["last_updated_at"]
                )
                existing.reasoning_notes = classification_event["reasoning_notes"]
                existing.active_zohar_rules = classification_event.get(
                    "active_zohar_rules", []
                )
                existing.updated_at = datetime.now(timezone.utc)
            else:
                # INSERT new row
                row = V9DayTypeHistory(
                    date=session_date,
                    day_type=classification_event["day_type"],
                    status=legacy_status,
                    confidence=legacy_confidence,
                    probability=classification_event["probability"],
                    directional_certainty=classification_event["directional_certainty"],
                    trading_confidence=classification_event["trading_confidence"],
                    ib_high=classification_event.get("ib_h"),
                    ib_low=classification_event.get("ib_l"),
                    ib_width=classification_event.get("ib_width"),
                    ib_width_class=classification_event.get("ib_width_class"),
                    opening_type=classification_event.get("opening_type"),
                    last_updated_at=self._parse_datetime(
                        classification_event["last_updated_at"]
                    ),
                    reasoning_notes=classification_event["reasoning_notes"],
                    active_zohar_rules=classification_event.get(
                        "active_zohar_rules", []
                    ),
                )
                session.add(row)

            session.commit()

            logger.info(
                "DayTypeConsumer upserted: date=%s type=%s prob=%.2f",
                session_date,
                classification_event["day_type"],
                classification_event["probability"],
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _extract_session_date(timestamp):
        """Extract date from timestamp (ISO string or datetime)."""
        if isinstance(timestamp, str):
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif isinstance(timestamp, datetime):
            ts = timestamp
        else:
            raise ValueError(f"Unsupported timestamp type: {type(timestamp)}")
        return ts.date()

    @staticmethod
    def _parse_datetime(value):
        """Parse datetime from ISO string or pass through datetime."""
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @staticmethod
    def _map_legacy_status(classification_event: dict) -> str:
        """Map V9 classification to V1-legacy ``status`` (NOT NULL in prod DB).

        Accepts an optional ``lock_state`` key in the event (``"LOCKED"`` /
        ``"LOCKED_LOW_CONF"`` / ``"PENDING"``) and falls back to ``"LOCKED"``
        because ``to_classification()`` only returns a non-None value once the
        state machine has produced a usable classification — at that point the
        row is publishable to the V9 API even if the internal lock has not yet
        fired (the API treats row-existence as ``classified=True``).
        """
        lock_state = classification_event.get("lock_state")
        if lock_state in ("LOCKED", "LOCKED_LOW_CONF", "PENDING"):
            return str(lock_state)
        return "LOCKED"

    @staticmethod
    def _map_legacy_confidence(classification_event: dict) -> float:
        """Map V9 ``probability`` (0..1) to V1-legacy ``confidence`` (0..100).

        Mirrors the reverse mapping in ``day_type_v9_routes._row_to_v9_dict``
        which converts V1 ``confidence`` back to V9 ``probability``. Defaults
        to ``0.0`` if probability is missing; never returns ``None`` because
        the production schema declares ``confidence FLOAT NOT NULL``.
        """
        probability = classification_event.get("probability")
        if probability is None:
            return 0.0
        try:
            return round(float(probability) * 100.0, 2)
        except (TypeError, ValueError):
            return 0.0
