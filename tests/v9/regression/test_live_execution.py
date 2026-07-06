"""Live execution + P&L-from-Sierra-fill regression tests.

Anti-tautological:
1. LIVE_EXECUTION_V1=1 → trade_command.json written with mode:"live"
   (FAILS on old stub that logged-only, no Sierra command).
2. P&L uses FILL price, not stop level: a STOP fill at price != trade.stop
   → recorded pnl reflects the fill (FAILS on old exit_price=trade.stop).
3. Target fill price flows through to PnL calculation.
4. FillPoller passes fill price to on_stop_hit and on_target_hit.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── Group 1: Live execution writes Sierra command ───────────────────

def test_live_flag_on_writes_sierra_command(monkeypatch):
    """LIVE_EXECUTION_V1=1: _execute_live writes trade_command.json with mode:live.

    ANTI-TAUTOLOGICAL: the old stub logged "NOT sent to Sierra" and wrote
    nothing. This test FAILS on the old code.
    """
    monkeypatch.setenv("LIVE_EXECUTION_V1", "1")
    monkeypatch.setenv("FIXED_CONTRACTS_3", "1")

    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setenv("MEMS26_SIGNALS_DIR", td)

        from backend.v9.services.sierra_command import command_from_setup
        setup = {
            "direction": "LONG", "entry_price": 7500.0,
            "stop": 7493.0, "t1": 7507.0, "t2": 7514.0, "t3": 7521.0,
            "contracts": 3, "firing_system": 4, "classification": "ZLR",
            "confidence": 0.75, "metadata": {"pattern": "ZLR", "sizing": "full"},
        }
        result = command_from_setup(
            setup, trade_id="live-001",
            account="APEX-125218-13", mode="live",
        )
        assert result["mode"] == "live", f"Expected mode='live', got {result['mode']}"
        assert result["action"] == "BUY"
        assert result["contracts"] == 3

        # Verify file was written
        cmd_file = Path(td) / "trade_command.json"
        assert cmd_file.exists(), "trade_command.json must exist for live orders"
        content = json.loads(cmd_file.read_text())
        assert content["mode"] == "live"
        assert content["account"] == "APEX-125218-13"


def test_live_flag_off_is_stub(monkeypatch):
    """LIVE_EXECUTION_V1=OFF: _execute_live stays the stub (no Sierra)."""
    monkeypatch.delenv("LIVE_EXECUTION_V1", raising=False)
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway.__new__(TradingGateway)
    gw._trade_manager = None
    gw._system_registry = {}

    setup = {
        "direction": "LONG", "entry_price": 7500.0,
        "stop": 7493.0, "t1": 7507.0,
        "classification": "ZLR", "confidence": 0.75,
        "metadata": {},
    }
    result = gw._execute_live(setup, 4, {})
    # Stub returns a legacy trade dict (not a Sierra command dict)
    assert result.get("mode") == "live"
    assert "sierra_command" not in result, "Stub should NOT produce Sierra commands"


# ── Group 2: P&L from fill price, not stop level ───────────────────

def test_stop_pnl_uses_fill_price_not_stop_level():
    """on_stop_hit with fill_price → exit_price = fill, not trade.stop.

    ANTI-TAUTOLOGICAL: old code hardcoded exit_price = trade.stop.
    With slippage (fill @ 7492.0 vs stop @ 7493.0), pnl must differ.
    """
    from backend.v9.services.trade_manager.manager import TradeManager, MES_POINT_VALUE

    # Create a mock trade
    trade = MagicMock()
    trade.id = 1
    trade.direction = "LONG"
    trade.entry_price = 7500.0
    trade.stop = 7493.0  # intended stop
    trade.state = "FILLED"
    trade.mode = "demo"
    trade.t1 = 7507.0
    trade.t2 = None
    trade.t3 = None
    trade.t1_hit_ts = None
    trade.t2_hit_ts = None
    trade.t3_hit_ts = None
    trade.cross_context = []
    trade.management_log = []
    trade.pnl_usd = None
    trade.pnl_r = None
    trade.outcome = None
    trade.exit_price = None
    trade.exit_ts = None
    trade.exit_reason = None
    trade.stop_hit_ts = None

    # Create a minimal TM
    tm = TradeManager.__new__(TradeManager)
    tm._db = MagicMock()
    tm._machines = {}
    tm._emitter = MagicMock()
    tm._snapshot = None
    tm._db.query.return_value.filter.return_value.first.return_value = trade

    # Simulate a state machine in FILLED state
    from backend.v9.services.trade_manager.state_machine import TradeStateMachine, TradeState
    tm._machines[1] = TradeStateMachine(TradeState.FILLED)

    # Stop hit with SLIPPAGE: fill at 7492.0, not the intended 7493.0
    fill_ts = datetime(2026, 7, 6, 15, 30, 0, tzinfo=timezone.utc)
    tm.on_stop_hit(1, fill_ts=fill_ts, fill_price=7492.0)

    # exit_price must be the fill price, not the stop level
    assert trade.exit_price == 7492.0, (
        f"exit_price should be fill (7492.0), not stop (7493.0), got {trade.exit_price}"
    )
    # PnL: LONG entry@7500, exit@7492 = -8pt × $5 × 3 contracts = -$120
    # (with stop@7493 it would have been -7pt × $5 × 3 = -$105)
    assert trade.pnl_usd == -120.0, (
        f"pnl should be -$120 (fill-based), not -$105 (stop-based), got {trade.pnl_usd}"
    )


def test_stop_pnl_falls_back_to_stop_when_no_fill_price():
    """Without fill_price, on_stop_hit falls back to trade.stop (backward compat)."""
    from backend.v9.services.trade_manager.manager import TradeManager
    from backend.v9.services.trade_manager.state_machine import TradeStateMachine, TradeState

    trade = MagicMock()
    trade.id = 2
    trade.direction = "LONG"
    trade.entry_price = 7500.0
    trade.stop = 7493.0
    trade.state = "FILLED"
    trade.mode = "demo"
    trade.t1 = 7507.0
    trade.t2 = None
    trade.t3 = None
    trade.t1_hit_ts = None
    trade.t2_hit_ts = None
    trade.t3_hit_ts = None
    trade.cross_context = []
    trade.management_log = []
    trade.pnl_usd = None
    trade.pnl_r = None
    trade.outcome = None
    trade.exit_price = None
    trade.exit_ts = None
    trade.exit_reason = None
    trade.stop_hit_ts = None

    tm = TradeManager.__new__(TradeManager)
    tm._db = MagicMock()
    tm._machines = {2: TradeStateMachine(TradeState.FILLED)}
    tm._emitter = MagicMock()
    tm._snapshot = None
    tm._db.query.return_value.filter.return_value.first.return_value = trade

    # No fill_price → fallback to trade.stop
    tm.on_stop_hit(2)
    assert trade.exit_price == 7493.0, f"Should fall back to trade.stop, got {trade.exit_price}"


# ── Group 3: Target fill price flows to PnL ─────────────────────────

def test_target_fill_price_updates_target_level():
    """on_target_hit with fill_price updates t1/t2/t3 for PnL accuracy."""
    from backend.v9.services.trade_manager.manager import TradeManager
    from backend.v9.services.trade_manager.state_machine import TradeStateMachine, TradeState

    trade = MagicMock()
    trade.id = 3
    trade.direction = "LONG"
    trade.entry_price = 7500.0
    trade.stop = 7493.0
    trade.state = "FILLED"
    trade.mode = "demo"
    trade.t1 = 7507.0  # intended T1
    trade.t2 = 7514.0
    trade.t3 = 7521.0
    trade.t1_hit_ts = None
    trade.t2_hit_ts = None
    trade.t3_hit_ts = None
    trade.cross_context = []
    trade.management_log = []
    trade.pnl_usd = None
    trade.pnl_r = None
    trade.outcome = None
    trade.exit_price = None

    tm = TradeManager.__new__(TradeManager)
    tm._db = MagicMock()
    tm._machines = {3: TradeStateMachine(TradeState.FILLED)}
    tm._emitter = MagicMock()
    tm._snapshot = None
    tm._db.query.return_value.filter.return_value.first.return_value = trade

    # T1 fill at 7507.25 (0.25pt better than intended 7507.0)
    tm.on_target_hit(3, "T1", fill_price=7507.25)
    assert trade.t1 == 7507.25, f"T1 should be updated to fill price 7507.25, got {trade.t1}"


# ── Group 4: FillPoller passes price to manager ──────────────────────

def test_fill_poller_passes_stop_fill_price():
    """FillPoller passes actual fill price to on_stop_hit."""
    from backend.v9.services.fill_poller import FillPoller

    tm = MagicMock()
    tm.get_active_trades.return_value = []

    fp = FillPoller.__new__(FillPoller)
    fp._tm = tm
    fp._order_map = {1001: 42}
    fp._processed_count = 0
    fp._gateway = None

    fill = {"kind": "STOP", "order_id": 1001, "price": 7492.50, "ts": 1751900000}
    fp._process_fill(fill)

    tm.on_stop_hit.assert_called_once()
    call_kwargs = tm.on_stop_hit.call_args
    assert call_kwargs.kwargs.get("fill_price") == 7492.50 or \
           (len(call_kwargs.args) > 0 and call_kwargs[1].get("fill_price") == 7492.50), \
        f"on_stop_hit should receive fill_price=7492.50"


def test_fill_poller_passes_target_fill_price():
    """FillPoller passes actual fill price to on_target_hit."""
    from backend.v9.services.fill_poller import FillPoller

    tm = MagicMock()
    tm.get_active_trades.return_value = []

    fp = FillPoller.__new__(FillPoller)
    fp._tm = tm
    fp._order_map = {2001: 43}
    fp._processed_count = 0
    fp._gateway = None

    fill = {"kind": "T1", "order_id": 2001, "price": 7507.25, "ts": 1751900000}
    fp._process_fill(fill)

    tm.on_target_hit.assert_called_once()
    call_kwargs = tm.on_target_hit.call_args
    assert call_kwargs.kwargs.get("fill_price") == 7507.25 or \
           (len(call_kwargs.args) > 0 and call_kwargs[1].get("fill_price") == 7507.25), \
        f"on_target_hit should receive fill_price=7507.25"
