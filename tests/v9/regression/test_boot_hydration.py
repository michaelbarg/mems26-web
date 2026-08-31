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



# ═══ T-186 (2026-08-31): UNPRICED rows must not kill the hydration ═══
#
# On the 21:07 restart, BOOT_HYDRATION died on `float(None)` and the daily-loss
# cap silently restarted from $0.00 instead of -$148.75 — effective cap
# -$598.75 instead of the ruled -$450. The NULL is CORRECT: T-160 /
# PNL_REQUIRES_EXIT_PRICE_V1 writes pnl_usd=NULL rather than inventing an exit
# price (CLAUDE.md Rule 1), so every reader of pnl_usd must handle NULL.
#
# The tests above all passed while the bug was live, because none of them fed a
# NULL row — the same gap as T-177. These assert the COUNTERS after hydration,
# not the SQL.

def test_hydrate_survives_unpriced_row_and_keeps_counters():
    """THE REGRESSION: a pnl_usd=NULL row must not zero the daily-loss cap."""
    gw = _make_gateway()
    # #877 closed by phantom_reconcile with no exit price → pnl_usd NULL, and
    # it is the MOST RECENT row, i.e. the first one the streak walk touches.
    mock_rows = [
        {"id": 877, "pnl_usd": None},
        {"id": 885, "pnl_usd": -60.0},
        {"id": 875, "pnl_usd": -100.0},
        {"id": 873, "pnl_usd": 11.25},
    ]
    with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
         patch("backend.v9.db.read.read_scalar", side_effect=[-148.75, 5]), \
         patch("backend.v9.db.read.read_all", return_value=mock_rows):
        gw.hydrate_live_pnl()

    assert gw._daily_pnl == -148.75, "daily-loss cap silently restarted from $0"
    assert gw._daily_trades == 5
    # UNPRICED is skipped, not counted and not a streak-breaker: the two real
    # losses behind it still count (breaking would UNDERSTATE the streak).
    assert gw._consecutive_losses == 2


def test_unpriced_row_does_not_break_the_streak():
    """Skip (not break) is the safe direction — pin it explicitly."""
    gw = _make_gateway()
    mock_rows = [
        {"id": 3, "pnl_usd": -10.0},
        {"id": 2, "pnl_usd": None},   # unpriced in the MIDDLE of the streak
        {"id": 1, "pnl_usd": -20.0},
    ]
    with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
         patch("backend.v9.db.read.read_scalar", side_effect=[-30.0, 3]), \
         patch("backend.v9.db.read.read_all", return_value=mock_rows):
        gw.hydrate_live_pnl()
    assert gw._consecutive_losses == 2, "unpriced row broke the loss streak"


def test_unpriced_rows_are_reported_not_silent(caplog):
    """daily_pnl EXCLUDES unpriced trades — the operator must be told."""
    import logging
    gw = _make_gateway()
    mock_rows = [{"id": 877, "pnl_usd": None}, {"id": 873, "pnl_usd": -20.0}]
    with caplog.at_level(logging.WARNING):
        with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
             patch("backend.v9.db.read.read_scalar", side_effect=[-20.0, 2]), \
             patch("backend.v9.db.read.read_all", return_value=mock_rows):
            gw.hydrate_live_pnl()
    assert any("UNPRICED" in r.message or "UNPRICED" in str(r.msg)
               for r in caplog.records), "unpriced rows were skipped silently"


def test_all_priced_path_is_unchanged(caplog):
    """Control: with no NULLs, nothing is reported and numbers are identical."""
    import logging
    gw = _make_gateway()
    mock_rows = [{"id": 2, "pnl_usd": -75.0}, {"id": 1, "pnl_usd": 100.0}]
    with caplog.at_level(logging.WARNING):
        with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
             patch("backend.v9.db.read.read_scalar", side_effect=[25.0, 2]), \
             patch("backend.v9.db.read.read_all", return_value=mock_rows):
            gw.hydrate_live_pnl()
    assert gw._daily_pnl == 25.0
    assert gw._consecutive_losses == 1
    assert not any("UNPRICED" in str(r.msg) for r in caplog.records)


def test_hydration_failure_is_logged_as_error_not_warning(caplog):
    """A risk gate that fails OPEN may not read like noise (CLAUDE.md)."""
    import logging
    gw = _make_gateway()
    with caplog.at_level(logging.WARNING):
        with patch("backend.v9.services.market_clock.now_et", return_value=_mock_now_post_rth()), \
             patch("backend.v9.db.read.read_scalar", side_effect=Exception("DB down")):
            gw.hydrate_live_pnl()  # still non-fatal
    hits = [r for r in caplog.records if "BOOT_HYDRATION" in str(r.msg)]
    assert hits, "hydration failure was not logged at all"
    assert any(r.levelno >= logging.ERROR for r in hits), (
        "hydration failure still logged below ERROR — this is exactly how the "
        "zeroed daily-loss cap hid for a whole session")
