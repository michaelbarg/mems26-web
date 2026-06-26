"""Anti-tautological regression tests for FEED_WATCHDOG (T2).

When ON + canonical streams stale → is_feed_alive() returns HALT.
When ON + streams fresh → alive. When OFF → always alive.
The gateway blocks fires when the watchdog halts.

if reverted → RED because: removing the FEED_WATCHDOG check from the gateway
or is_feed_alive() would break the halt assertion.
"""
import os
import time
import pytest
from unittest.mock import patch, MagicMock

from backend.v9.services.feed_watchdog import is_feed_alive, STALE_THRESHOLD_SECONDS
from datetime import datetime
from zoneinfo import ZoneInfo

# Mock RTH time (10:00 CT = inside RTH window)
_RTH_TIME = datetime(2026, 6, 25, 10, 0, 0, tzinfo=ZoneInfo("America/Chicago"))


def _mock_stream_health(streams_age):
    """Create a mock StreamHealthService with given stream ages (seconds since last push)."""
    import threading

    class FakeState:
        def __init__(self, name, age):
            self.name = name
            self.last_bridge_push_ts = time.time() - age if age >= 0 else 0.0
            self.push_count = 1 if age >= 0 else 0

    class FakeSHS:
        def __init__(self):
            self._lock = threading.Lock()
            self._streams = {name: FakeState(name, age) for name, age in streams_age.items()}

    return FakeSHS()


def _mock_app_with_shs(shs):
    mock_app = MagicMock()
    mock_app.state.stream_health_service = shs
    mock_mod = MagicMock()
    mock_mod.app = mock_app
    return mock_mod


# ── Flag OFF → always alive ──────────────────────────────────────────────

@patch.dict(os.environ, {"FEED_WATCHDOG": "0"})
def test_flag_off_always_alive():
    """FEED_WATCHDOG=0 → always alive regardless of stream state."""
    alive, reason = is_feed_alive()
    assert alive is True
    assert reason is None


# ── Flag ON + streams fresh → alive ──────────────────────────────────────

@patch.dict(os.environ, {"FEED_WATCHDOG": "1"})
@patch("backend.v9.services.feed_watchdog.datetime")
def test_fresh_streams_alive(mock_dt):
    """Both streams pushed recently → alive."""
    mock_dt.now.return_value = _RTH_TIME
    shs = _mock_stream_health({"5min": 10, "woodies_5min": 5})
    with patch("backend.v9.services.feed_watchdog.importlib.import_module",
               return_value=_mock_app_with_shs(shs)):
        alive, reason = is_feed_alive()
    assert alive is True


# ── Flag ON + ALL streams stale → HALT ───────────────────────────────────

@patch.dict(os.environ, {"FEED_WATCHDOG": "1"})
@patch("backend.v9.services.feed_watchdog.datetime")
def test_all_stale_halts(mock_dt):
    """Both canonical streams stale (>90s) → HALT.

    if reverted → RED because: removing is_feed_alive makes this always return True.
    """
    mock_dt.now.return_value = _RTH_TIME
    shs = _mock_stream_health({"5min": 200, "woodies_5min": 300})
    with patch("backend.v9.services.feed_watchdog.importlib.import_module",
               return_value=_mock_app_with_shs(shs)):
        alive, reason = is_feed_alive()
    assert alive is False
    assert "HALT" in reason
    assert "stale" in reason


# ── Flag ON + one stream fresh → alive (partial OK) ──────────────────────

@patch.dict(os.environ, {"FEED_WATCHDOG": "1"})
@patch("backend.v9.services.feed_watchdog.datetime")
def test_one_fresh_one_stale_alive(mock_dt):
    """Only one stream stale, other fresh → still alive (need ALL stale to halt)."""
    mock_dt.now.return_value = _RTH_TIME
    shs = _mock_stream_health({"5min": 200, "woodies_5min": 5})
    with patch("backend.v9.services.feed_watchdog.importlib.import_module",
               return_value=_mock_app_with_shs(shs)):
        alive, reason = is_feed_alive()
    assert alive is True


# ── Auto-resume: stale → fresh → alive again ────────────────────────────

@patch.dict(os.environ, {"FEED_WATCHDOG": "1"})
@patch("backend.v9.services.feed_watchdog.datetime")
def test_auto_resume_after_fresh(mock_dt):
    """After a halt, when streams become fresh again → auto-resume (alive)."""
    mock_dt.now.return_value = _RTH_TIME
    # First check: stale → halt
    shs_stale = _mock_stream_health({"5min": 200, "woodies_5min": 300})
    with patch("backend.v9.services.feed_watchdog.importlib.import_module",
               return_value=_mock_app_with_shs(shs_stale)):
        alive1, _ = is_feed_alive()
    assert alive1 is False

    # Second check: fresh → resume
    shs_fresh = _mock_stream_health({"5min": 5, "woodies_5min": 10})
    with patch("backend.v9.services.feed_watchdog.importlib.import_module",
               return_value=_mock_app_with_shs(shs_fresh)):
        alive2, _ = is_feed_alive()
    assert alive2 is True


# ── Gateway integration (source inspection) ─────────────────────────────

def test_gateway_has_feed_watchdog():
    """Gateway route_setup checks feed_watchdog.

    if reverted → RED because: removing the import makes this fail.
    """
    import inspect
    from backend.v9.gateway.trading_gateway import TradingGateway
    # Cowork refactored route_setup to delegate to _route_setup_inner
    source = inspect.getsource(TradingGateway._route_setup_inner)
    assert "feed_watchdog" in source
    assert "is_feed_alive" in source
    assert "blocked_by" in source
