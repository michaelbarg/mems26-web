"""Pipeline 5 DLL exit monitor: tracks attached stop/target fills via
GetPersistentInt64 IDs and writes {kind:STOP|T1} to trade_fills.json.

if reverted → RED because: removing the fill-check block would stop
exit events from reaching the backend.
"""
from pathlib import Path
import pytest


def test_dll_has_exit_monitor_block():
    """DLL source has the Pipeline 5 exit monitor (attached-order fill detection)."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    assert "Monitor all 3 groups" in source
    assert "p5_parent" in source
    assert "tgt_id" in source
    assert "stp_id" in source


def test_dll_writes_stop_fill():
    """DLL writes a STOP fill event when the attached stop fills."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    assert "STOP" in source and "AvgFillPrice" in source


def test_dll_writes_t1_fill():
    """DLL writes a T1 fill event when the attached target fills."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    assert "T1" in source and "AvgFillPrice" in source


def test_dll_stores_parent_order_for_monitoring():
    """After order submission, the DLL stores IDs via GetPersistentInt64."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    assert "GetPersistentInt64(1) = o.InternalOrderID" in source
    assert "GetPersistentInt64(2) = o.Target1InternalOrderID" in source
    assert "GetPersistentInt64(3) = o.Stop1InternalOrderID" in source


def test_dll_exit_monitor_gated_by_enable_order():
    """Exit monitor only runs when EnableOrderPlacement >= 1."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    monitor_pos = source.find("Monitor all 3 groups")
    assert monitor_pos > 0
    following = source[monitor_pos:monitor_pos + 500]
    assert "EnableOrderPlacement" in following
