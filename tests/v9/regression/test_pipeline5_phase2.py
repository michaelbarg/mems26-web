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


# ── C. Manager emit wiring ──────────────────────────────────────────────

def test_manager_has_emit_modify_stop():
    """Manager has _emit_modify_stop method."""
    import inspect
    from backend.v9.services.trade_manager.manager import TradeManager
    assert hasattr(TradeManager, '_emit_modify_stop')
    source = inspect.getsource(TradeManager._emit_modify_stop)
    assert "write_modify_stop" in source


def test_manager_has_emit_modify_target():
    """Manager has _emit_modify_target method."""
    import inspect
    from backend.v9.services.trade_manager.manager import TradeManager
    assert hasattr(TradeManager, '_emit_modify_target')
    source = inspect.getsource(TradeManager._emit_modify_target)
    assert "write_modify_target" in source


def test_smart_be_emits_modify_stop():
    """_apply_smart_be_after_t1 calls _emit_modify_stop.

    if reverted → RED because: removing the emit call from smart_be
    removes MODIFY_STOP from the Sierra command sequence.
    """
    import inspect
    from backend.v9.services.trade_manager.manager import TradeManager
    source = inspect.getsource(TradeManager._apply_smart_be_after_t1)
    assert "_emit_modify_stop" in source


def test_trail_emits_modify_stop():
    """apply_trail_after_t1 calls _emit_modify_stop."""
    import inspect
    from backend.v9.services.trade_manager.manager import TradeManager
    source = inspect.getsource(TradeManager.apply_trail_after_t1)
    assert "_emit_modify_stop" in source


def test_struct_trail_emits_both():
    """apply_dynamic_struct_trail calls both _emit_modify_stop and _emit_modify_target."""
    import inspect
    from backend.v9.services.trade_manager.manager import TradeManager
    source = inspect.getsource(TradeManager.apply_dynamic_struct_trail)
    assert "_emit_modify_stop" in source
    assert "_emit_modify_target" in source


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
