"""Test: day_type hydrate runs BEFORE overnight early-return (P31-F).

Verifies that FiveMinSystem.hydrate() populates current_day_type even when
the session classifier reports OVERNIGHT, and that UNKNOWN day_type is skipped.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from backend.v9.systems.five_min.five_min_system import FiveMinSystem, FiveMinMode
from backend.v9.common.session_classifier import Session


class _FakeSessionInfo:
    def __init__(self, session):
        self.session = session


def _make_fake_dt_state(day_type: str):
    """Create a mock V9DayTypeState row."""
    obj = MagicMock()
    obj.day_type = day_type
    obj.ts = datetime.now(timezone.utc)
    obj.id = 1
    return obj


@patch("backend.v9.systems.five_min.five_min_system.SessionLocal")
@patch("backend.v9.systems.five_min.five_min_system.SessionClassifier")
def test_hydrate_populates_day_type_during_overnight(mock_sc_cls, mock_session_local):
    """current_day_type is set even when hydrate returns OVERNIGHT_MODE."""
    # SessionClassifier returns OVERNIGHT
    mock_sc = MagicMock()
    mock_sc.classify.return_value = _FakeSessionInfo(Session.OVERNIGHT)
    mock_sc_cls.return_value = mock_sc

    # DB returns a day_type row
    fake_row = _make_fake_dt_state("Neutral_Center")
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = fake_row
    mock_session_local.return_value = mock_db

    system = FiveMinSystem()
    result = system.hydrate()

    assert result.reached_state == FiveMinMode.OVERNIGHT_MODE
    assert system.current_day_type == "Neutral_Center"


@patch("backend.v9.systems.five_min.five_min_system.SessionLocal")
@patch("backend.v9.systems.five_min.five_min_system.SessionClassifier")
def test_hydrate_skips_unknown_day_type(mock_sc_cls, mock_session_local):
    """UNKNOWN day_type is not stored in current_day_type."""
    mock_sc = MagicMock()
    mock_sc.classify.return_value = _FakeSessionInfo(Session.OVERNIGHT)
    mock_sc_cls.return_value = mock_sc

    fake_row = _make_fake_dt_state("UNKNOWN")
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = fake_row
    mock_session_local.return_value = mock_db

    system = FiveMinSystem()
    result = system.hydrate()

    assert result.reached_state == FiveMinMode.OVERNIGHT_MODE
    assert system.current_day_type is None, "UNKNOWN should not be stored"
