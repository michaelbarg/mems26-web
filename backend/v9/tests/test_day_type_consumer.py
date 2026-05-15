"""Tests for DayTypeConsumer (3a-S4 REVISED C2).

Tests UPSERT pattern: insert new, update existing, handle nulls, multi-day.
Uses in-memory SQLite for isolation.
"""
import pytest
from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.v9.db.session import Base
from backend.v9.db.models.day_type_history import V9DayTypeHistory
from backend.v9.systems.day_type.consumer import DayTypeConsumer


@pytest.fixture
def db_session_factory():
    """In-memory SQLite session factory."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return factory


def _make_event(
    day_type="Trend_Normal",
    probability=0.7,
    timestamp="2026-05-15T14:30:00+00:00",
    **overrides,
):
    """Create a classification event dict."""
    event = {
        "timestamp": timestamp,
        "day_type": day_type,
        "probability": probability,
        "directional_certainty": "HIGH",
        "trading_confidence": "LOW",
        "ib_h": 5260.0,
        "ib_l": 5240.0,
        "ib_width": 20.0,
        "ib_width_class": "MEDIUM",
        "opening_type": "OPEN_DRIVE",
        "last_updated_at": timestamp,
        "reasoning_notes": "test event",
        "active_zohar_rules": ["delta"],
    }
    event.update(overrides)
    return event


def test_consume_inserts_new_row(db_session_factory):
    """First consume for a date inserts a new row."""
    consumer = DayTypeConsumer(db_session_factory)
    event = _make_event()

    consumer.consume(event)

    session = db_session_factory()
    row = session.query(V9DayTypeHistory).first()
    assert row is not None
    assert row.date == date(2026, 5, 15)
    assert row.day_type == "Trend_Normal"
    assert row.probability == 0.7
    assert row.directional_certainty == "HIGH"
    assert row.trading_confidence == "LOW"
    assert row.ib_high == 5260.0
    assert row.ib_low == 5240.0
    assert row.ib_width == 20.0
    assert row.ib_width_class == "MEDIUM"
    assert row.opening_type == "OPEN_DRIVE"
    assert row.reasoning_notes == "test event"
    assert row.active_zohar_rules == ["delta"]
    session.close()


def test_consume_upserts_existing_row(db_session_factory):
    """Second consume for same date updates the existing row."""
    consumer = DayTypeConsumer(db_session_factory)

    # First insert
    consumer.consume(_make_event(day_type="Normal", probability=0.5))

    # Second upsert — same date, different classification
    consumer.consume(_make_event(
        day_type="Variation",
        probability=0.8,
        reasoning_notes="updated classification",
    ))

    session = db_session_factory()
    rows = session.query(V9DayTypeHistory).all()
    assert len(rows) == 1  # UPSERT: still 1 row
    assert rows[0].day_type == "Variation"
    assert rows[0].probability == 0.8
    assert rows[0].reasoning_notes == "updated classification"
    session.close()


def test_consume_handles_optional_nulls(db_session_factory):
    """Consume with null optional fields succeeds."""
    consumer = DayTypeConsumer(db_session_factory)
    event = _make_event()
    event["ib_h"] = None
    event["ib_l"] = None
    event["ib_width"] = None
    event["ib_width_class"] = None
    event["opening_type"] = None
    event["active_zohar_rules"] = []

    consumer.consume(event)

    session = db_session_factory()
    row = session.query(V9DayTypeHistory).first()
    assert row is not None
    assert row.ib_high is None
    assert row.ib_low is None
    assert row.ib_width is None
    assert row.opening_type is None
    session.close()


def test_consume_multi_day(db_session_factory):
    """Different dates create separate rows."""
    consumer = DayTypeConsumer(db_session_factory)

    consumer.consume(_make_event(
        timestamp="2026-05-14T14:00:00+00:00",
        day_type="Normal",
    ))
    consumer.consume(_make_event(
        timestamp="2026-05-15T14:00:00+00:00",
        day_type="Variation",
    ))

    session = db_session_factory()
    rows = session.query(V9DayTypeHistory).order_by(V9DayTypeHistory.date).all()
    assert len(rows) == 2
    assert rows[0].date == date(2026, 5, 14)
    assert rows[0].day_type == "Normal"
    assert rows[1].date == date(2026, 5, 15)
    assert rows[1].day_type == "Variation"
    session.close()


def test_consume_accepts_datetime_object(db_session_factory):
    """Consume works with datetime objects (not just ISO strings)."""
    consumer = DayTypeConsumer(db_session_factory)
    event = _make_event()
    event["timestamp"] = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)
    event["last_updated_at"] = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)

    consumer.consume(event)

    session = db_session_factory()
    row = session.query(V9DayTypeHistory).first()
    assert row is not None
    assert row.date == date(2026, 5, 15)
    session.close()
