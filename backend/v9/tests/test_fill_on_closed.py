"""Tests for P0-2: fill-based accounting on already-CLOSED trades.

Key invariant: when a Sierra fill arrives for a trade already closed
(by MAE_SCRATCH or bar-level detector), the P&L must still be updated
from the real fill price. Trade #640: $0 → -$131.25.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


def _make_closed_trade(trade_id=640, entry=7735.5, stop=7744.0, direction="SHORT"):
    return SimpleNamespace(
        id=trade_id, mode="live", direction=direction, state="CLOSED",
        entry_price=entry, exit_price=None, stop=stop,
        t1=7720.0, t2=7710.0, t3=7700.0,
        t1_hit_ts=None, t2_hit_ts=None, t3_hit_ts=None, t4_hit_ts=None,
        stop_hit_ts=None, exit_ts=datetime(2026, 8, 6, 15, 0, tzinfo=timezone.utc),
        exit_reason="MAE_SCRATCH", pnl_usd=0.0, pnl_r=0.0,
        outcome="BE", quality={"contracts": 3}, cross_context=None,
        sierra_bracket_id=None, is_synthetic=0,
        created_at=None, updated_at=None,
    )


def test_update_closed_trade_pnl_sets_correct_values():
    """update_closed_trade_pnl fixes P&L on a CLOSED trade."""
    from backend.v9.services.trade_manager.manager import TradeManager

    trade = _make_closed_trade()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = trade

    tm = TradeManager.__new__(TradeManager)
    tm._db = db
    tm._machines = {}
    tm._mgmt_log = []

    def mock_log(tid, action, val):
        tm._mgmt_log.append((tid, action, val))
    tm._log_management = mock_log

    result = tm.update_closed_trade_pnl(640, exit_price=7744.25)
    assert result is True
    assert trade.exit_price == 7744.25
    assert trade.pnl_usd is not None
    assert trade.pnl_usd < 0  # SHORT entry 7735.5, exit 7744.25 = loss


def test_update_closed_trade_pnl_skips_non_closed():
    """Only applies to CLOSED trades."""
    from backend.v9.services.trade_manager.manager import TradeManager

    trade = _make_closed_trade()
    trade.state = "FILLED"  # not closed
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = trade

    tm = TradeManager.__new__(TradeManager)
    tm._db = db
    tm._machines = {}

    result = tm.update_closed_trade_pnl(640, exit_price=7744.25)
    assert result is False  # should skip


def test_fill_poller_routes_closed_to_update():
    """FillPoller routes STOP fill on CLOSED trade to update_closed_trade_pnl."""
    # This is an integration-level test of the routing logic
    from backend.v9.services.fill_poller import FillPoller

    fp = FillPoller.__new__(FillPoller)
    fp._tm = MagicMock()
    fp._order_map = {5001: 640}
    fp._processed_count = 0
    fp._orphan_count = 0
    fp._orphan_fills = []

    # Simulate a CLOSED trade
    closed_trade = _make_closed_trade()
    fp._tm._get_trade.return_value = closed_trade
    fp._tm.update_closed_trade_pnl.return_value = True

    fill = {"kind": "STOP", "order_id": 5001, "price": 7744.25, "ts": 1722960000}
    fp._process_fill(fill)

    # Should have called update_closed_trade_pnl
    fp._tm.update_closed_trade_pnl.assert_called_once_with(
        640, 7744.25, exit_reason="STOP_FILL"
    )
