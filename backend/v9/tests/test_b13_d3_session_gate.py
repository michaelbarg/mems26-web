"""B-13 D3 regression: session gate blocks firing outside 08:30-15:00 CT.

if reverted → RED because is_within_firing_window returns True for
15:01 CT, allowing trades to fire after close.
"""

import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from backend.v9.gateway.session_gate import (
    is_within_firing_window,
    is_after_firing_close,
    FIRING_TZ,
)


CT = ZoneInfo("America/Chicago")


def _ct_to_utc(year, month, day, hour, minute) -> datetime:
    """Helper: create a CT datetime and convert to UTC."""
    ct = datetime(year, month, day, hour, minute, tzinfo=CT)
    return ct.astimezone(timezone.utc)


class TestSessionGate:
    """B-13 D3: no firing outside 08:30-15:00 CT."""

    def test_within_window_allowed(self):
        """10:00 CT on a Wednesday → firing allowed."""
        utc = _ct_to_utc(2026, 6, 4, 10, 0)  # Wed
        assert is_within_firing_window(utc) is True

    def test_after_close_blocked(self):
        """15:01 CT → firing blocked."""
        utc = _ct_to_utc(2026, 6, 4, 15, 1)  # Wed
        assert is_within_firing_window(utc) is False

    def test_before_open_blocked(self):
        """08:00 CT → firing blocked."""
        utc = _ct_to_utc(2026, 6, 4, 8, 0)
        assert is_within_firing_window(utc) is False

    def test_at_open_allowed(self):
        """08:30 CT → firing allowed."""
        utc = _ct_to_utc(2026, 6, 4, 8, 30)
        assert is_within_firing_window(utc) is True

    def test_at_close_blocked(self):
        """15:00 CT exactly → firing blocked (close is exclusive)."""
        utc = _ct_to_utc(2026, 6, 4, 15, 0)
        assert is_within_firing_window(utc) is False

    def test_weekend_blocked(self):
        """Saturday → firing blocked."""
        utc = _ct_to_utc(2026, 6, 6, 10, 0)  # Sat
        assert is_within_firing_window(utc) is False

    def test_phantom_fire_time_blocked(self):
        """B-13 exact regression: 16:18 CT (= 17:18 ET) → must be blocked."""
        utc = _ct_to_utc(2026, 6, 4, 16, 18)
        assert is_within_firing_window(utc) is False

    def test_is_after_firing_close(self):
        """15:01 CT → is_after_firing_close is True."""
        utc = _ct_to_utc(2026, 6, 4, 15, 1)
        assert is_after_firing_close(utc) is True

    def test_not_after_close_during_session(self):
        """14:00 CT → is_after_firing_close is False."""
        utc = _ct_to_utc(2026, 6, 4, 14, 0)
        assert is_after_firing_close(utc) is False
