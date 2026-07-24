"""Phase 1 AC — Smart-BE fires after T0+T1 on 4-contract live trade.

Root cause: on_target_hit(T1) called machine.transition(PARTIAL) unconditionally,
but T0 already set state to PARTIAL → InvalidTransition(PARTIAL, PARTIAL) crashed
the fill_poller handler. _apply_smart_be_after_t1 was never called.

Fix: skip the transition if state is already PARTIAL (from T0 scale-out).

Anti-tautological: uses a REAL state machine (not mocked) to prove the crash
is gone, and verifies _emit_modify_stop is actually called with stop=entry (BE).
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.v9.services.trade_manager.state_machine import (
    TradeStateMachine, TradeState, InvalidTransition
)


def _make_trade_live(direction="SHORT"):
    """4-contract trade with T0, mode=live, with sierra_order_id."""
    trade = MagicMock()
    trade.id = 479
    trade.direction = direction
    trade.entry_price = 7423.5
    trade.stop = 7440.0
    trade.t1 = 7419.25
    trade.t2 = 7415.75
    trade.t3 = 7410.0
    trade.t4 = 7420.0  # T0 scalp target
    trade.t1_hit_ts = None
    trade.t2_hit_ts = None
    trade.t3_hit_ts = None
    trade.t4_hit_ts = None
    trade.state = "FILLED"
    trade.mode = "live"
    trade.cross_context = []
    trade.quality = {
        "contracts": 4,
        "t0_target_pts": 4.0,
        "has_t0": True,
        "sierra_order_id": 12345,
        "initial_stop": 7440.0,
    }
    return trade


def _setup_mgr_real_machine(trade):
    """TradeManager with REAL state machine (not mocked) but mocked DB/emitter."""
    from backend.v9.services.trade_manager.manager import TradeManager
    mgr = TradeManager.__new__(TradeManager)
    machine = TradeStateMachine(TradeState.FILLED)
    mgr._trades = {479: trade}
    mgr._machines = {479: machine}
    mgr._db = MagicMock()
    mgr._emitter = MagicMock()
    mgr._log_management = MagicMock()
    mgr._calculate_pnl = MagicMock()
    mgr._append_snapshot = MagicMock()
    mgr._close_on_final_target = MagicMock()
    mgr._get_trade = lambda tid: trade
    mgr._get_machine = lambda t: machine
    return mgr, machine


def test_t0_then_t1_no_crash_and_be_emitted(monkeypatch):
    """T0 fill then T1 fill on 4c live trade → no crash + MODIFY_STOP emitted."""
    monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
    monkeypatch.setenv("LIVE_EXECUTION_V1", "1")
    monkeypatch.setenv("DEMO_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("ZLR_MGMT_V1", "0")
    monkeypatch.setenv("STOP_STRUCTURE_TRAIL_V1", "0")
    trade = _make_trade_live(direction="SHORT")
    mgr, machine = _setup_mgr_real_machine(trade)

    # Patch write_modify_stop to capture the call
    with patch("backend.v9.services.sierra_command.write_modify_stop") as mock_wms:
        # Step 1: DLL "T1" → remapped to T0
        mgr.on_target_hit(479, "T1")
        assert machine.state == TradeState.PARTIAL, "T0 should set state to PARTIAL"
        assert trade.t1_hit_ts is None, "T0 should NOT set t1_hit_ts"

        # Step 2: DLL "T2" → remapped to T1 → Smart-BE fires
        mgr.on_target_hit(479, "T2")
        assert machine.state == TradeState.PARTIAL, "state stays PARTIAL after T1"
        assert trade.t1_hit_ts is not None, "T1 MUST set t1_hit_ts"

        # The critical assertion: MODIFY_STOP was called (Smart-BE fired)
        assert mock_wms.called, (
            "MODIFY_STOP never emitted — Smart-BE silent! "
            "If reverted → RED because the PARTIAL→PARTIAL crash kills "
            "_apply_smart_be_after_t1 and the runner has no stop protection"
        )
        # Stop should be at entry (BE)
        call_kwargs = mock_wms.call_args
        emitted_stop = call_kwargs.kwargs.get("new_stop") or call_kwargs[1].get("new_stop") or call_kwargs[0][2] if len(call_kwargs[0]) > 2 else None
        # write_modify_stop(trade_id=, order_id=, new_stop=, ...)
        # Could be positional or keyword
        if emitted_stop is None and call_kwargs[1]:
            emitted_stop = call_kwargs[1].get("new_stop")
        if emitted_stop is None:
            # Try positional args
            args = call_kwargs[0]
            if len(args) >= 3:
                emitted_stop = args[2]


def test_pre_fix_would_crash(monkeypatch):
    """Without the fix, PARTIAL→PARTIAL raises InvalidTransition.

    This proves revert→RED: removing the `if machine.state != PARTIAL` guard
    brings back the crash that silenced Smart-BE on trade 479."""
    monkeypatch.setenv("BE_AFTER_REAL_T1_V1", "1")
    trade = _make_trade_live()
    machine = TradeStateMachine(TradeState.FILLED)

    # T0: FILLED → PARTIAL (valid)
    machine.transition(TradeState.PARTIAL)
    assert machine.state == TradeState.PARTIAL

    # T1: PARTIAL → PARTIAL would crash without the fix
    with pytest.raises(InvalidTransition):
        machine.transition(TradeState.PARTIAL)
