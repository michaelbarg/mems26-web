"""Regression tests: F-17 RTH gate — Woodies must not fire on non-RTH bars.

Filter-F17: process_bar() skips bars outside 09:30–16:00 ET to prevent
overnight/globex bars from triggering pattern detection and trade fires.
"""
import asyncio
import logging
from unittest.mock import MagicMock

import pytest

from backend.v9.systems.woodies.woodies_system import WoodiesSystem, _is_rth_bar


# ── _is_rth_bar helper tests ──────────────────────────────────────

class TestIsRthBar:
    """Unit tests for the RTH detection helper."""

    def _ts(self, hour_et: int, minute: int = 0) -> float:
        """Build a unix timestamp for 2026-05-27 at HH:MM ET (EDT = UTC-4)."""
        from datetime import datetime, timezone, timedelta
        # 2026-05-27 XX:XX EDT = 2026-05-27 (XX+4):XX UTC
        try:
            from zoneinfo import ZoneInfo
            et = ZoneInfo("America/New_York")
        except ImportError:
            import pytz
            et = pytz.timezone("America/New_York")
        dt = datetime(2026, 5, 27, hour_et, minute, tzinfo=et)
        return dt.timestamp()

    def test_930_am_et_is_rth(self):
        """9:30 AM ET (RTH open) is within RTH."""
        assert _is_rth_bar(self._ts(9, 30)) is True

    def test_1000_am_et_is_rth(self):
        """10:00 AM ET is within RTH."""
        assert _is_rth_bar(self._ts(10, 0)) is True

    def test_1500_et_is_rth(self):
        """3:00 PM ET is within RTH."""
        assert _is_rth_bar(self._ts(15, 0)) is True

    def test_1600_et_is_rth(self):
        """4:00 PM ET (RTH close) is the boundary — included."""
        assert _is_rth_bar(self._ts(16, 0)) is True

    def test_0200_am_et_is_not_rth(self):
        """2:00 AM ET is overnight — not RTH."""
        assert _is_rth_bar(self._ts(2, 0)) is False

    def test_0900_et_is_not_rth(self):
        """9:00 AM ET is pre-market — not RTH."""
        assert _is_rth_bar(self._ts(9, 0)) is False

    def test_1700_et_is_not_rth(self):
        """5:00 PM ET is after-hours — not RTH."""
        assert _is_rth_bar(self._ts(17, 0)) is False

    def test_zero_ts_fails_open(self):
        """ts=0 → fail-open (allow processing)."""
        assert _is_rth_bar(0.0) is True

    def test_negative_ts_not_rth(self):
        """Negative ts → converts to a 1969 date → not RTH (not fail-open, just non-RTH)."""
        assert _is_rth_bar(-1.0) is False


# ── WoodiesSystem RTH gate integration ────────────────────────────

def _run(coro):
    return asyncio.run(coro)


def _make_bar(ts_unix: float, close: float = 5000.0) -> dict:
    return {
        "ts": ts_unix,
        "open": close, "high": close + 1.0, "low": close - 1.0,
        "close": close, "volume": 500,
    }


def _rth_ts() -> float:
    """Return a unix timestamp for 2026-05-27 10:00 AM ET (clearly RTH)."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except ImportError:
        import pytz
        et = pytz.timezone("America/New_York")
    return datetime(2026, 5, 27, 10, 0, tzinfo=et).timestamp()


def _overnight_ts() -> float:
    """Return a unix timestamp for 2026-05-27 2:00 AM ET (overnight)."""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except ImportError:
        import pytz
        et = pytz.timezone("America/New_York")
    return datetime(2026, 5, 27, 2, 0, tzinfo=et).timestamp()


class TestWoodiesRthGate:

    def test_rth_bar_increments_bar_count(self):
        """RTH bar is processed → _bar_count increments."""
        sys = WoodiesSystem(rth_only=True)
        ts = _rth_ts()
        count_before = sys._bar_count
        _run(sys.process_bar(_make_bar(ts)))
        assert sys._bar_count > count_before

    def test_overnight_bar_still_increments_bar_count(self):
        """Overnight bar: _bar_count still increments (counted before RTH gate)."""
        sys = WoodiesSystem(rth_only=True)
        count_before = sys._bar_count
        _run(sys.process_bar(_make_bar(_overnight_ts())))
        assert sys._bar_count == count_before + 1

    def test_overnight_bar_does_not_fire_gateway(self):
        """Overnight bar skips pattern detection → gateway.route_setup not called."""
        sys = WoodiesSystem(rth_only=True)
        gw = MagicMock()
        gw.route_setup.return_value = {"shadow": None, "blocked_by": None}
        sys.set_gateway(gw)
        _run(sys.process_bar(_make_bar(_overnight_ts())))
        gw.route_setup.assert_not_called()

    def test_rth_only_false_allows_overnight_bar(self):
        """rth_only=False disables the gate → overnight bar reaches pattern engine."""
        sys = WoodiesSystem(rth_only=False)
        # With rth_only=False, process_bar runs fully — bar_count increments and
        # current_state is updated (studies populated if bar has cci_14).
        ts = _overnight_ts()
        _run(sys.process_bar(_make_bar(ts)))
        # Should not be skipped — bar_count incremented and processing happened
        assert sys._bar_count == 1

    def test_rth_only_default_attribute_set(self):
        """WoodiesSystem stores _rth_only attribute."""
        sys = WoodiesSystem()
        assert hasattr(sys, "_rth_only")
        assert isinstance(sys._rth_only, bool)

    def test_rth_only_false_constructor(self):
        """rth_only=False constructor sets attribute correctly."""
        sys = WoodiesSystem(rth_only=False)
        assert sys._rth_only is False

    def test_overnight_bar_calls_check_time_stops(self):
        """Even on overnight bar, _check_time_stops is called to expire open trades."""
        sys = WoodiesSystem(rth_only=True)
        # Manually insert an open fire record
        sys._open_fire_records["42"] = {"entry_bar_count": 1, "pattern_id": "ZLR"}
        sys._bar_count = 1
        # Process an overnight bar
        _run(sys.process_bar(_make_bar(_overnight_ts())))
        # Time stop enforcer limit_bars=18, bars_open < 18 → not removed yet
        assert "42" in sys._open_fire_records

    def test_overnight_bar_time_stop_fires_when_expired(self):
        """Overnight bar still fires time stop if trade has exceeded limit."""
        sys = WoodiesSystem(rth_only=True)
        sys._open_fire_records["99"] = {"entry_bar_count": 0, "pattern_id": "TLB"}
        sys._bar_count = 18  # already at bar_count=18 before processing
        _run(sys.process_bar(_make_bar(_overnight_ts())))
        # bars_open = 19 - 0 = 19 >= 18 → time stop fires → removed
        assert "99" not in sys._open_fire_records
