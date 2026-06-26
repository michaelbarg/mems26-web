"""Pipeline 5 Phase 2: dynamic manager drives Sierra (DEMO mode).

Tests the command protocol (MODIFY_STOP/MODIFY_TARGET/EXIT/CANCEL),
the manager's emit wiring, and the DLL order-ops source.

if reverted → RED because: removing the command functions or the
emit wiring would break the assertions.
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.v9.services.sierra_command import (
    write_modify_stop, write_modify_target, write_exit, write_cancel,
    command_from_setup,
)


# ── A. Command protocol ─────────────────────────────────────────────────

def test_modify_stop_command():
    """write_modify_stop writes correct JSON with op=MODIFY_STOP."""
    with tempfile.TemporaryDirectory() as td:
        with patch.dict(os.environ, {"MEMS26_SIGNALS_DIR": td}):
            result = write_modify_stop(trade_id="t-1", order_id=42, new_stop=7440.0)
            assert result["op"] == "MODIFY_STOP"
            assert result["order_id"] == 42
            assert result["new_stop"] == 7440.0
            # Verify file written
            content = json.loads((Path(td) / "trade_command.json").read_text())
            assert content["op"] == "MODIFY_STOP"


def test_modify_target_command():
    with tempfile.TemporaryDirectory() as td:
        with patch.dict(os.environ, {"MEMS26_SIGNALS_DIR": td}):
            result = write_modify_target(trade_id="t-2", order_id=43, new_target=7470.0)
            assert result["op"] == "MODIFY_TARGET"
            assert result["new_target"] == 7470.0


def test_exit_command():
    with tempfile.TemporaryDirectory() as td:
        with patch.dict(os.environ, {"MEMS26_SIGNALS_DIR": td}):
            result = write_exit(trade_id="t-3", order_id=44, contracts=1)
            assert result["op"] == "EXIT"
            assert result["contracts"] == 1


def test_cancel_command():
    with tempfile.TemporaryDirectory() as td:
        with patch.dict(os.environ, {"MEMS26_SIGNALS_DIR": td}):
            result = write_cancel(trade_id="t-4", order_id=45)
            assert result["op"] == "CANCEL"


def test_place_command_has_op_field():
    """PLACE commands now include op=PLACE for dispatch."""
    with tempfile.TemporaryDirectory() as td:
        with patch.dict(os.environ, {"MEMS26_SIGNALS_DIR": td}):
            setup = {"direction": "LONG", "entry_price": 7450.0, "stop": 7440.0,
                     "t1": 7460.0, "contracts": 3}
            result = command_from_setup(setup, trade_id="t-5", account="SIM", mode="demo")
            assert result["op"] == "PLACE"
            assert result["action"] == "BUY"


# ── C. Manager emit wiring — BEHAVIORAL tests ──────────────────────────

@patch.dict(os.environ, {"DEMO_EXECUTION_ENABLED": "1"})
def test_manager_emits_modify_stop_in_demo():
    """In DEMO mode, a stop move emits a MODIFY_STOP command.

    if reverted → RED because: removing _emit_modify_stop makes the mock
    never called → assertion fails.
    """
    from backend.v9.services.trade_manager.manager import TradeManager

    mock_trade = MagicMock()
    mock_trade.mode = "demo"
    mock_trade.quality = {"sierra_order_id": 42}

    tm = MagicMock(spec=TradeManager)
    tm._is_demo_mode = TradeManager._is_demo_mode.__get__(tm)
    tm._get_sierra_order_id = TradeManager._get_sierra_order_id.__get__(tm)
    tm._emit_modify_stop = TradeManager._emit_modify_stop.__get__(tm)

    with patch("backend.v9.services.sierra_command.write_modify_stop") as mock_write:
        tm._emit_modify_stop(mock_trade, 7445.0)
        mock_write.assert_called_once_with(
            trade_id=str(mock_trade.id), order_id=42, new_stop=7445.0)


@patch.dict(os.environ, {"DEMO_EXECUTION_ENABLED": "0"})
def test_manager_does_not_emit_in_shadow():
    """In SHADOW mode (flag OFF), no Sierra command emitted.

    if reverted → RED because: removing the mode gate makes this always emit.
    """
    from backend.v9.services.trade_manager.manager import TradeManager

    mock_trade = MagicMock()
    mock_trade.mode = "shadow"
    mock_trade.quality = {"sierra_order_id": 42}

    tm = MagicMock(spec=TradeManager)
    tm._is_demo_mode = TradeManager._is_demo_mode.__get__(tm)
    tm._get_sierra_order_id = TradeManager._get_sierra_order_id.__get__(tm)
    tm._emit_modify_stop = TradeManager._emit_modify_stop.__get__(tm)

    with patch("backend.v9.services.sierra_command.write_modify_stop") as mock_write:
        tm._emit_modify_stop(mock_trade, 7445.0)
        mock_write.assert_not_called()


@patch.dict(os.environ, {"DEMO_EXECUTION_ENABLED": "1"})
def test_manager_emits_modify_target_in_demo():
    """In DEMO mode, a target re-anchor emits MODIFY_TARGET."""
    from backend.v9.services.trade_manager.manager import TradeManager

    mock_trade = MagicMock()
    mock_trade.mode = "demo"
    mock_trade.quality = {"sierra_order_id": 42}

    tm = MagicMock(spec=TradeManager)
    tm._is_demo_mode = TradeManager._is_demo_mode.__get__(tm)
    tm._get_sierra_order_id = TradeManager._get_sierra_order_id.__get__(tm)
    tm._emit_modify_target = TradeManager._emit_modify_target.__get__(tm)

    with patch("backend.v9.services.sierra_command.write_modify_target") as mock_write:
        tm._emit_modify_target(mock_trade, 7470.0)
        mock_write.assert_called_once()


# ── B. DLL order-ops ─────────────────────────────────────────────────────

def test_dll_has_modify_stop_op():
    """DLL dispatches MODIFY_STOP via sc.ModifyOrder."""
    dll = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll.exists():
        pytest.skip("DLL not found")
    source = dll.read_text()
    assert "MODIFY_STOP" in source
    assert "ModifyOrder" in source


def test_dll_has_modify_target_op():
    dll = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll.exists():
        pytest.skip("DLL not found")
    source = dll.read_text()
    assert "MODIFY_TARGET" in source


def test_dll_has_exit_op():
    dll = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll.exists():
        pytest.skip("DLL not found")
    source = dll.read_text()
    assert "FlattenAndCancelOrders" in source
    assert "EXIT" in source


def test_dll_has_cancel_op():
    dll = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll.exists():
        pytest.skip("DLL not found")
    source = dll.read_text()
    assert "CANCEL" in source


def test_dll_3_contracts_default():
    """Phase 2: entry bracket defaults to 3 contracts."""
    dll = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll.exists():
        pytest.skip("DLL not found")
    source = dll.read_text()
    assert "contracts = 3" in source


def test_dll_oco_group1_partial_target():
    """PLACE uses OCOGroup1Quantity=1 for C1 partial target (not all-out).

    if reverted → RED because: removing OCOGroup1Quantity makes the target
    cover all contracts (the bug this follow-up fixes).
    """
    dll = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll.exists():
        pytest.skip("DLL not found")
    source = dll.read_text()
    assert "OCOGroup1Quantity = 1" in source
    assert "OCOGroup2Quantity" in source


def test_dll_exit_uses_partial_not_flatten():
    """EXIT uses sc.SellExit/BuyExit (partial), NOT FlattenAndCancelOrders.

    if reverted → RED because: using Flatten for EXIT closes all contracts.
    """
    dll = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll.exists():
        pytest.skip("DLL not found")
    source = dll.read_text()
    # Find the EXIT block and verify it uses SellExit/BuyExit
    exit_pos = source.find("OP: EXIT")
    assert exit_pos > 0
    exit_block = source[exit_pos:exit_pos + 1000]
    assert "SellExit" in exit_block
    assert "BuyExit" in exit_block
    # FlattenAndCancelOrders may appear in a comment but must NOT be called
    # The actual call would be "sc.FlattenAndCancelOrders()" — check that's absent
    assert "sc.FlattenAndCancelOrders()" not in exit_block


def test_dll_runner_stop_tracked():
    """DLL tracks the G2 (runner) stop in persistent int 104."""
    dll = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll.exists():
        pytest.skip("DLL not found")
    source = dll.read_text()
    assert "p5_runner_stop_id" in source
    assert "GetPersistentInt(104)" in source
