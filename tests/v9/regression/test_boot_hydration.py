"""BOOT_HYDRATION_V1: verify daily PnL restoration from DB on restart.
Task F (2026-07-22): pre-09:30 restart → counters=0; post-09:30 → today's trades only."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")


def _make_gateway():
    from backend.v9.gateway.trading_gateway import TradingGateway
    return TradingGateway()


def _mock_now_post_rth():
    """Return a datetime at 10:30 ET (after 09:30 — session active)."""
    return datetime(2026, 7, 22, 10, 30, 0, tzinfo=_ET)


def _mock_now_pre_rth():
    """Return a datetime at 08:00 ET (before 09:30 — no session yet)."""
    return datetime(2026, 7, 22, 8, 0, 0, tzinfo=_ET)


def test_hydrate_live_pnl_restores_counters():
    """After hydration (post-09:30), gateway counters match DB state."""
    gw = _make_gateway()
    assert gw._daily_pnl == 0.0
    assert gw._daily_trades == 0
    assert gw._consecutive_losses == 0

    # Mock: 3 closed trades today: +100, -50, -75 (most recent first)
    mock_rows = [
        {"pnl_usd": -75.0},   # most recent — loss
        {"pnl_usd": -50.0},   # loss
        {"pnl_usd": 100.0},   # oldest — win
    ]
    with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
         patch("backend.v9.db.read.read_scalar", side_effect=[-25.0, 3]), \
         patch("backend.v9.db.read.read_all", return_value=mock_rows):
        gw.hydrate_live_pnl()

    assert gw._daily_pnl == -25.0
    assert gw._daily_trades == 3
    assert gw._consecutive_losses == 2  # last 2 were losses


def test_hydrate_live_pnl_no_trades():
    """Hydration with no trades (post-09:30) keeps counters at 0."""
    gw = _make_gateway()
    with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
         patch("backend.v9.db.read.read_scalar", side_effect=[0.0, 0]), \
         patch("backend.v9.db.read.read_all", return_value=[]):
        gw.hydrate_live_pnl()

    assert gw._daily_pnl == 0.0
    assert gw._daily_trades == 0
    assert gw._consecutive_losses == 0


def test_hydrate_live_pnl_db_error_is_nonfatal():
    """DB failure during hydration logs warning but doesn't crash."""
    gw = _make_gateway()
    with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
         patch("backend.v9.db.read.read_scalar", side_effect=Exception("DB down")):
        gw.hydrate_live_pnl()  # should not raise
    assert gw._daily_pnl == 0.0  # stays at default


def test_hydrate_all_wins_zero_consecutive_losses():
    """When all trades are wins, consecutive_losses stays 0."""
    gw = _make_gateway()
    mock_rows = [
        {"pnl_usd": 50.0},
        {"pnl_usd": 100.0},
    ]
    with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
         patch("backend.v9.db.read.read_scalar", side_effect=[150.0, 2]), \
         patch("backend.v9.db.read.read_all", return_value=mock_rows):
        gw.hydrate_live_pnl()

    assert gw._daily_pnl == 150.0
    assert gw._daily_trades == 2
    assert gw._consecutive_losses == 0


# ═══ Task F (2026-07-22): pre-09:30 reset ═══

def test_hydrate_pre_0930_counters_zero():
    """Pre-09:30 restart: counters stay 0 (no session yet). Fixes $675 cap bug."""
    gw = _make_gateway()
    # Even if previous day had trades, pre-09:30 should NOT load them
    with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_pre_rth()):
        gw.hydrate_live_pnl()

    assert gw._daily_pnl == 0.0
    assert gw._daily_trades == 0
    assert gw._consecutive_losses == 0


def test_hydrate_post_0930_loads_today_only():
    """Post-09:30 restart: loads today's trades, not yesterday's."""
    gw = _make_gateway()
    # Inject -125 to simulate yesterday's trades leaking in (the old bug)
    gw._daily_pnl = -125.0

    mock_rows = [{"pnl_usd": -50.0}]
    with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
         patch("backend.v9.db.read.read_scalar", side_effect=[-50.0, 1]), \
         patch("backend.v9.db.read.read_all", return_value=mock_rows):
        gw.hydrate_live_pnl()

    # Should be -50 (today only), not -125 (yesterday's leak)
    assert gw._daily_pnl == -50.0
    assert gw._daily_trades == 1
    assert gw._consecutive_losses == 1
