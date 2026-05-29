"""Tests for backend.v9.common.trading_date.et_today()."""

from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from backend.v9.common.trading_date import et_today, _ET


def test_et_today_returns_date():
    """et_today() returns a datetime.date instance."""
    result = et_today()
    assert isinstance(result, date)


def test_et_today_uses_et_timezone():
    """et_today() returns ET date, not UTC — verified by mocking datetime.now."""
    # 2026-01-15 02:00 UTC = 2026-01-14 21:00 ET (EST, UTC-5)
    fake_utc = datetime(2026, 1, 15, 2, 0, 0, tzinfo=ZoneInfo("UTC"))
    with patch("backend.v9.common.trading_date.datetime") as mock_dt:
        mock_dt.now.return_value = fake_utc.astimezone(_ET)
        result = et_today()
    assert result == date(2026, 1, 14), f"Expected 2026-01-14 (ET), got {result}"


def test_et_today_same_date_during_rth():
    """During RTH hours (e.g. 14:00 UTC = 10:00 ET summer), ET and UTC agree on date."""
    fake_utc = datetime(2026, 6, 10, 14, 0, 0, tzinfo=ZoneInfo("UTC"))
    with patch("backend.v9.common.trading_date.datetime") as mock_dt:
        mock_dt.now.return_value = fake_utc.astimezone(_ET)
        result = et_today()
    assert result == date(2026, 6, 10)
