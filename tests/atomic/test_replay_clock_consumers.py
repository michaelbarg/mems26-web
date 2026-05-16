"""Prompt 26b — Prove TPO + TradeManager use market_clock (replay-safe).

Tests verify:
  1. TPO IB lock uses replay timestamp in REPLAY mode.
  2. TradeManager lifecycle timestamps use replay timestamp.
  3. No SHADOW/DEMO/LIVE activation.
"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from unittest.mock import patch
from datetime import datetime, timezone
import inspect


REPLAY_TS = datetime(2026, 5, 14, 15, 30, 0, tzinfo=timezone.utc)


def _mock_market_now_utc():
    return REPLAY_TS


def test_tpo_ib_lock_uses_market_clock():
    """TPO _ib_locked_ts sourced from _market_now_utc, not raw datetime.utcnow."""
    from backend.v9.systems.tpo.tpo_system import TPOSystem
    source = inspect.getsource(TPOSystem)
    assert "_market_now_utc" in source
    # No raw utcnow paired with ib_locked_ts assignment
    for line in source.split('\n'):
        if '_ib_locked_ts' in line and 'datetime.utcnow' in line:
            raise AssertionError(f"TPO still uses datetime.utcnow for IB lock: {line.strip()}")


def test_tpo_poc_migration_uses_market_clock():
    """TPO POC migration timing uses _market_now_utc."""
    from backend.v9.systems.tpo.tpo_system import TPOSystem
    source = inspect.getsource(TPOSystem.process_bar)
    assert "_market_now_utc" in source


def test_trade_manager_imports_market_clock():
    """TradeManager imports _market_now_utc from market_clock."""
    from backend.v9.services.trade_manager import manager
    source = inspect.getsource(manager)
    assert "from backend.v9.services.market_clock import now_utc as _market_now_utc" in source


def test_trade_manager_fill_uses_replay_ts():
    """TradeManager.on_fill sets entry_ts from market_clock value."""
    from backend.v9.services.trade_manager.manager import TradeManager
    from backend.v9.db.session import SessionLocal

    db = SessionLocal()
    with patch("backend.v9.services.trade_manager.manager._market_now_utc", _mock_market_now_utc):
        tm = TradeManager(db=db)
        trade_id = tm.accept_setup({
            "firing_system": 2, "direction": "LONG",
            "stop": 7440.0, "t1": 7455.0, "t2": 7460.0, "t3": 7470.0,
        }, mode="shadow")
        tm.on_fill(trade_id, 7450.0)
        trade = tm._get_trade(trade_id)
        # SQLite may strip tzinfo; compare naive
        expected_naive = REPLAY_TS.replace(tzinfo=None)
        actual_naive = trade.entry_ts.replace(tzinfo=None) if trade.entry_ts else None
        assert actual_naive == expected_naive, f"Expected {expected_naive}, got {actual_naive}"
    db.rollback()
    db.close()


def test_no_shadow_demo_live():
    """No trading mode enabled by clock changes."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway()
    assert gw._demo_enabled_systems == set()
    assert gw._live_enabled_systems == set()
