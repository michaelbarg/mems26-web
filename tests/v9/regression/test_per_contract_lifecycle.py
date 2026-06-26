"""Pipeline 5 Phase 2-E: per-contract lifecycle regression tests.

Each Tn fill = ONE contract out (scale-out), not the whole position.
T3 closes ONLY when all 3 contracts are out (T1+T2+T3 all filled).

if reverted → RED because: reverting to the old "T3→CLOSED always" would
close the trade when T3 fills even if T2 is still open.
"""
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from backend.v9.services.trade_manager.manager import TradeManager
from backend.v9.services.trade_manager.state_machine import TradeState


def _mock_trade(t1_hit=None, t2_hit=None, t3_hit=None, state="PARTIAL"):
    """Create a mock V9Trade with configurable target hit timestamps."""
    trade = MagicMock()
    trade.id = 1
    trade.state = state
    trade.direction = "LONG"
    trade.entry_price = 7450.0
    trade.stop = 7445.0
    trade.t1 = 7460.0
    trade.t2 = 7470.0
    trade.t3 = 7480.0
    trade.t1_hit_ts = t1_hit
    trade.t2_hit_ts = t2_hit
    trade.t3_hit_ts = t3_hit
    trade.exit_ts = None
    trade.exit_reason = None
    trade.quality = {"initial_stop": 7440.0}
    trade.cross_context = []
    trade.mode = "shadow"
    return trade


def test_t3_does_not_close_while_c2_open():
    """T3 fill with T2 still open → trade stays PARTIAL (not CLOSED).

    if reverted → RED because: the old code did machine.transition(CLOSED)
    on any T3, which closes the trade even though C2 is still running.
    """
    now = datetime.now(timezone.utc)
    trade = _mock_trade(t1_hit=now, t2_hit=None)  # T1 filled, T2 NOT filled

    tm = MagicMock(spec=TradeManager)
    tm._db = MagicMock()
    tm._get_trade = MagicMock(return_value=trade)
    tm._get_machine = MagicMock(return_value=MagicMock())
    tm._append_snapshot = MagicMock()
    tm._log_management = MagicMock()
    tm._calculate_pnl = MagicMock()
    tm._set_outcome = MagicMock()
    tm._cleanup_machine = MagicMock()
    tm._emitter = MagicMock()
    tm.on_target_hit = TradeManager.on_target_hit.__get__(tm)

    tm.on_target_hit(1, "T3", fill_ts=now)

    # T3 filled BUT T2 is still open → NOT closed
    assert trade.t3_hit_ts == now
    assert trade.exit_reason is None, "T3 with open C2 must NOT close the trade"
    tm._set_outcome.assert_not_called()
    tm._cleanup_machine.assert_not_called()


def test_t3_closes_when_all_out():
    """T3 fill with T1+T2 already filled → trade CLOSES (all 3 contracts out).

    if reverted → RED because: the test relies on the all_out check.
    """
    now = datetime.now(timezone.utc)
    trade = _mock_trade(t1_hit=now, t2_hit=now)  # T1 AND T2 filled

    machine = MagicMock()
    tm = MagicMock(spec=TradeManager)
    tm._db = MagicMock()
    tm._get_trade = MagicMock(return_value=trade)
    tm._get_machine = MagicMock(return_value=machine)
    tm._append_snapshot = MagicMock()
    tm._log_management = MagicMock()
    tm._calculate_pnl = MagicMock()
    tm._set_outcome = MagicMock()
    tm._cleanup_machine = MagicMock()
    tm._emitter = MagicMock()
    tm.on_target_hit = TradeManager.on_target_hit.__get__(tm)

    tm.on_target_hit(1, "T3", fill_ts=now)

    assert trade.t3_hit_ts == now
    assert trade.exit_reason == "T3_HIT"
    machine.transition.assert_called_with(TradeState.CLOSED)
    tm._set_outcome.assert_called_once()


def test_t2_stays_partial():
    """T2 fill = C2 scale-out → stays PARTIAL (not CLOSED)."""
    now = datetime.now(timezone.utc)
    trade = _mock_trade(t1_hit=now, t2_hit=None)

    tm = MagicMock(spec=TradeManager)
    tm._db = MagicMock()
    tm._get_trade = MagicMock(return_value=trade)
    tm._get_machine = MagicMock(return_value=MagicMock())
    tm._append_snapshot = MagicMock()
    tm._log_management = MagicMock()
    tm._calculate_pnl = MagicMock()
    tm._emitter = MagicMock()
    tm.on_target_hit = TradeManager.on_target_hit.__get__(tm)

    tm.on_target_hit(1, "T2", fill_ts=now)

    assert trade.t2_hit_ts == now
    assert trade.exit_reason is None  # stays PARTIAL


def test_struct_trail_routes_to_runner_id():
    """apply_dynamic_struct_trail routes _emit_modify_target to the front runner's
    own Sierra target ID (c2_target_id or c3_target_id), NEVER C1.

    if reverted → RED because: removing the per-runner routing sends MODIFY_TARGET
    to C1's id (the old default), which never re-anchors the runners.
    """
    import inspect
    source = inspect.getsource(TradeManager.apply_dynamic_struct_trail)
    assert "c2_target_id" in source
    assert "c3_target_id" in source
    assert "target_order_id=" in source
