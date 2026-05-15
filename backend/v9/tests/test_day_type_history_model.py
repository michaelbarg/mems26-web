"""Tests for V9DayTypeHistory model (3a-S4 REVISED).

Tests V9 columns added via Hybrid enhancement.
Uses in-memory SQLite for isolation.
"""
import pytest
from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.v9.db.session import Base
from backend.v9.db.models.day_type_history import V9DayTypeHistory


@pytest.fixture
def db_session():
    """In-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_insert_full_v9_row(db_session):
    """Insert a row with all V9 columns populated."""
    row = V9DayTypeHistory(
        date=date(2026, 5, 15),
        day_type="Trend_Normal",
        probability=0.7,
        directional_certainty="HIGH",
        trading_confidence="LOW",
        ib_high=5260.0,
        ib_low=5240.0,
        ib_width=20.0,
        ib_width_class="MEDIUM",
        opening_type="OPEN_DRIVE",
        last_updated_at=datetime.now(timezone.utc),
        reasoning_notes="Opening=OPEN_DRIVE Width=MEDIUM winner=trend_normal (0.70)",
        active_zohar_rules=["delta", "timing_bias"],
    )
    db_session.add(row)
    db_session.commit()

    fetched = db_session.query(V9DayTypeHistory).first()
    assert fetched is not None
    assert fetched.day_type == "Trend_Normal"
    assert fetched.probability == 0.7
    assert fetched.directional_certainty == "HIGH"
    assert fetched.trading_confidence == "LOW"
    assert fetched.ib_width == 20.0
    assert fetched.ib_width_class == "MEDIUM"
    assert fetched.active_zohar_rules == ["delta", "timing_bias"]


def test_unique_session_date(db_session):
    """Duplicate date raises IntegrityError (UNIQUE constraint)."""
    row1 = V9DayTypeHistory(
        date=date(2026, 5, 15),
        day_type="Normal",
        reasoning_notes="first",
    )
    row2 = V9DayTypeHistory(
        date=date(2026, 5, 15),
        day_type="Variation",
        reasoning_notes="duplicate",
    )
    db_session.add(row1)
    db_session.commit()

    db_session.add(row2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_default_active_zohar_rules(db_session):
    """active_zohar_rules defaults to empty list (or None in SQLite)."""
    row = V9DayTypeHistory(
        date=date(2026, 5, 15),
        day_type="Neutral",
        reasoning_notes="test defaults",
    )
    db_session.add(row)
    db_session.commit()

    fetched = db_session.query(V9DayTypeHistory).first()
    # SQLite JSON default: may be None or [] depending on driver
    assert fetched.active_zohar_rules is None or fetched.active_zohar_rules == []


def test_v1_columns_still_work(db_session):
    """V1 columns (status, confidence, locked_at) still writable."""
    row = V9DayTypeHistory(
        date=date(2026, 5, 14),
        day_type="Normal",
        status="LOCKED",
        confidence=65.0,
        ib_high=5260.0,
        ib_low=5240.0,
        ib_width_ticks=80,
        reasoning_notes="V1 path",
    )
    db_session.add(row)
    db_session.commit()

    fetched = db_session.query(V9DayTypeHistory).first()
    assert fetched.status == "LOCKED"
    assert fetched.confidence == 65.0
    assert fetched.ib_width_ticks == 80
