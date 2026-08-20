"""Pipeline 5: DEMO execution round-trip regression tests.

Phase A: DLL order placement gated by Enable Order Placement Input
Phase B: FillPoller reads trade_fills.json → TradeManager
Phase C: bar_level_detector skips DEMO/LIVE trades (mode-gate)
Phase D: DEMO_EXECUTION_ENABLED gates the gateway DEMO branch

if reverted → RED because: removing the mode-gate, fill-poller, or
DEMO_EXECUTION_ENABLED check would break these assertions.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.v9.services.fill_poller import FillPoller
from backend.v9.services.sierra_command import command_from_setup


# ── Phase A: command_from_setup writes correct bracket ───────────────────

def test_command_writes_bracket():
    """command_from_setup writes a full bracket command JSON."""
    with tempfile.TemporaryDirectory() as td:
        with patch.dict(os.environ, {"MEMS26_SIGNALS_DIR": td}):
            setup = {
                "direction": "LONG", "entry_price": 7450.0,
                "stop": 7440.0, "t1": 7460.0, "t2": 7470.0, "t3": 7480.0,
                "contracts": 3, "firing_system": 4, "classification": "ZLR",
                "confidence": 0.65,
            }
            result = command_from_setup(setup, trade_id="test-123",
                                        account="PA-APEX-SIM", mode="demo")
            assert result["action"] == "BUY"
            assert result["price"] == 7450.0
            assert result["stop_price"] == 7440.0
            assert result["mode"] == "demo"
            # Verify file was written
            cmd_file = Path(td) / "trade_command.json"
            assert cmd_file.exists()
            content = json.loads(cmd_file.read_text())
            assert content["action"] == "BUY"


# ── Phase B: FillPoller processes fill events ────────────────────────────

def test_fill_poller_processes_entry_fill():
    """FillPoller reads an ENTRY fill and calls TradeManager.

    if reverted → RED because: removing FillPoller → ImportError.
    """
    mock_tm = MagicMock()
    mock_trade = MagicMock()
    mock_tm._get_trade.return_value = mock_trade
    mock_tm.get_active_trades.return_value = [mock_trade]
    mock_trade.id = 42

    poller = FillPoller(trade_manager=mock_tm)
    poller.register_order(1001, 42)

    fill = {
        "kind": "ENTRY", "ts": 1719300000, "order_id": 1001,
        "price": 7450.25, "contracts": 3, "direction": "LONG",
    }
    poller._process_fill(fill)
    # ENTRY now drives on_fill (PENDING->FILLED transition + records the Sierra fill
    # price), not a direct entry_price set (Cowork fix 2026-06-25: the old path left
    # the trade un-transitioned -> it would never be managed/exited).
    mock_tm.on_fill.assert_called_with(42, 7450.25)


def test_fill_poller_processes_stop_fill():
    """FillPoller reads a STOP fill → on_stop_hit."""
    mock_tm = MagicMock()
    mock_tm.get_active_trades.return_value = []
    poller = FillPoller(trade_manager=mock_tm)
    poller.register_order(1002, 55)
    poller._process_fill({"kind": "STOP", "ts": 1719300100, "order_id": 1002, "price": 7440.0})
    mock_tm.on_stop_hit.assert_called_once()


def test_fill_poller_processes_target_fill():
    """FillPoller reads T1 fill → on_target_hit."""
    mock_tm = MagicMock()
    poller = FillPoller(trade_manager=mock_tm)
    poller.register_order(1003, 60)
    poller._process_fill({"kind": "T1", "ts": 1719300200, "order_id": 1003, "price": 7460.0})
    mock_tm.on_target_hit.assert_called_once_with(60, "T1", fill_ts=pytest.approx(
        datetime.fromtimestamp(1719300200, tz=timezone.utc), abs=1),
        fill_price=7460.0, fill_qty=None, order_id=1003)


def test_fill_poller_forwards_the_per_leg_quantity():
    """T-62: `contracts` from the DLL must reach the manager — without it a
    ladder's legs cannot be booked at their own prices (#749 = $52.50 error)."""
    mock_tm = MagicMock()
    poller = FillPoller(trade_manager=mock_tm)
    poller.register_order(1004, 61)
    poller._process_fill({"kind": "T1", "ts": 1719300300, "order_id": 1004,
                          "price": 7460.0, "contracts": 2})
    assert mock_tm.on_target_hit.call_args.kwargs["fill_qty"] == 2


# ── Phase C: bar_level_detector mode-gate ────────────────────────────────

def test_bar_level_detector_skips_demo_trades():
    """bar_level_detector skips DEMO trades (managed by fill poller).

    if reverted → RED because: removing the mode-gate makes source inspection fail.
    """
    import inspect
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    source = inspect.getsource(BarLevelDetector.on_bar)
    assert "demo" in source.lower()
    assert "live" in source.lower()
    assert "continue" in source  # the skip


# ── Phase D: DEMO_EXECUTION_ENABLED gates gateway ───────────────────────

@patch.dict(os.environ, {"DEMO_EXECUTION_ENABLED": "0"})
def test_demo_disabled_by_default():
    """With DEMO_EXECUTION_ENABLED=0, gateway DEMO branch is gated off."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway()
    gw.enable_demo(2)
    gw.enable_demo(4)
    # Even though systems are "enabled", the flag gates it
    assert gw._is_demo_enabled(2) is False
    assert gw._is_demo_enabled(4) is False


@patch.dict(os.environ, {"DEMO_EXECUTION_ENABLED": "1"})
def test_demo_enabled_with_flag():
    """With DEMO_EXECUTION_ENABLED=1, gateway DEMO branch is active."""
    from backend.v9.gateway.trading_gateway import TradingGateway
    gw = TradingGateway()
    gw.enable_demo(4)
    assert gw._is_demo_enabled(4) is True
    assert gw._is_demo_enabled(2) is False  # not enabled for S2


# ── DLL: Enable Order Placement Input exists ─────────────────────────────

def test_dll_has_order_placement_input():
    """DLL source has Enable Order Placement Input (default OFF).

    if reverted → RED because: removing the Input makes source inspection fail.
    """
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    assert "EnableOrderPlacement" in source
    assert "Enable Order Placement" in source
    assert "SetInt(0)" in source  # default OFF


def test_dll_has_trade_fills_path():
    """DLL source has TradeFillsPath Input for trade_fills.json."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    assert "TradeFillsPath" in source
    assert "trade_fills.json" in source
