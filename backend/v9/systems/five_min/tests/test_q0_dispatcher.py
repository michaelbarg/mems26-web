"""Tests for Q0 Dispatcher (Pre/Post-Lock branching)."""
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.v9.systems.five_min.q0_dispatcher import get_current_mode, is_transition_bar, S2Mode

ET = ZoneInfo("America/New_York")


def test_pre_lock_mode():
    dt = datetime(2026, 5, 16, 9, 45, tzinfo=ET)
    assert get_current_mode(dt) == S2Mode.PRE_LOCK


def test_post_lock_mode():
    dt = datetime(2026, 5, 16, 11, 0, tzinfo=ET)
    assert get_current_mode(dt) == S2Mode.POST_LOCK


def test_closed_before_rth():
    dt = datetime(2026, 5, 16, 8, 0, tzinfo=ET)
    assert get_current_mode(dt) == S2Mode.CLOSED


def test_transition_bar_at_1030():
    dt = datetime(2026, 5, 16, 10, 32, tzinfo=ET)
    assert is_transition_bar(dt) is True
    dt2 = datetime(2026, 5, 16, 10, 36, tzinfo=ET)
    assert is_transition_bar(dt2) is False
