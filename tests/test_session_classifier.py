"""Tests for SessionClassifier (D-083)."""

from datetime import datetime
import pytz
from backend.v9.common.session_classifier import SessionClassifier, Session

ET = pytz.timezone('America/New_York')
sc = SessionClassifier()


def _dt(year, month, day, hour, minute):
    return ET.localize(datetime(year, month, day, hour, minute))


class TestSessionClassifier:
    def test_friday_evening_is_weekend(self):
        info = sc.classify(_dt(2026, 5, 8, 18, 0))  # Friday 18:00
        assert info.session == Session.WEEKEND

    def test_saturday_is_weekend(self):
        info = sc.classify(_dt(2026, 5, 9, 12, 0))  # Saturday
        assert info.session == Session.WEEKEND

    def test_sunday_before_open_is_weekend(self):
        info = sc.classify(_dt(2026, 5, 10, 15, 0))  # Sunday 15:00
        assert info.session == Session.WEEKEND

    def test_sunday_after_open_is_overnight(self):
        info = sc.classify(_dt(2026, 5, 10, 19, 0))  # Sunday 19:00
        assert info.session == Session.OVERNIGHT

    def test_tuesday_6am_is_overnight(self):
        info = sc.classify(_dt(2026, 5, 12, 6, 0))  # Tuesday 06:00
        assert info.session == Session.OVERNIGHT

    def test_tuesday_8am_is_premarket(self):
        info = sc.classify(_dt(2026, 5, 12, 8, 30))  # Tuesday 08:30
        assert info.session == Session.PRE_MARKET

    def test_tuesday_930_is_cash_open(self):
        info = sc.classify(_dt(2026, 5, 12, 9, 30))  # Tuesday 09:30
        assert info.session == Session.CASH_OPEN

    def test_tuesday_940_is_first_hour(self):
        info = sc.classify(_dt(2026, 5, 12, 9, 40))  # Tuesday 09:40
        assert info.session == Session.FIRST_HOUR

    def test_tuesday_1100_is_cash_hours(self):
        info = sc.classify(_dt(2026, 5, 12, 11, 0))  # Tuesday 11:00
        assert info.session == Session.CASH_HOURS

    def test_tuesday_1600_is_after_hours(self):
        info = sc.classify(_dt(2026, 5, 12, 16, 30))  # Tuesday 16:30
        assert info.session == Session.AFTER_HOURS

    def test_tuesday_1730_is_maintenance(self):
        info = sc.classify(_dt(2026, 5, 12, 17, 30))  # Tuesday 17:30
        assert info.session == Session.MAINTENANCE

    def test_maintenance_not_active(self):
        info = sc.classify(_dt(2026, 5, 12, 17, 30))
        assert not info.is_trading_active

    def test_weekend_not_active(self):
        info = sc.classify(_dt(2026, 5, 9, 12, 0))
        assert not info.is_trading_active

    def test_overnight_is_active(self):
        info = sc.classify(_dt(2026, 5, 12, 3, 0))
        assert info.is_trading_active

    def test_cash_hours_is_active(self):
        info = sc.classify(_dt(2026, 5, 12, 14, 0))
        assert info.is_trading_active


class TestIsGlobexIsCash:
    def test_overnight_is_globex(self):
        assert sc.is_globex(Session.OVERNIGHT)

    def test_pre_market_is_globex(self):
        assert sc.is_globex(Session.PRE_MARKET)

    def test_cash_hours_is_cash(self):
        assert sc.is_cash(Session.CASH_HOURS)

    def test_first_hour_is_cash(self):
        assert sc.is_cash(Session.FIRST_HOUR)

    def test_overnight_not_cash(self):
        assert not sc.is_cash(Session.OVERNIGHT)

    def test_cash_not_globex(self):
        assert not sc.is_globex(Session.CASH_HOURS)


class TestCurrentTime:
    def test_classify_now_returns_valid(self):
        """Calling with no args uses current time — should not crash."""
        info = sc.classify()
        assert info.session in list(Session)
        assert isinstance(info.is_trading_active, bool)
