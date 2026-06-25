"""Pipeline 5 DLL exit monitor: the DLL monitors OCO bracket exits and writes
fill events (T1/STOP) to trade_fills.json when Sierra fills stop/target orders.

if reverted → RED because: removing the exit monitor block from the DLL
would remove the persistent-int tracking and fill-write logic.
"""
from pathlib import Path
import pytest


def test_dll_has_exit_monitor_block():
    """DLL source has the Pipeline 5 exit monitor (stop/target fill detection)."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    # Exit monitor block markers
    assert "Pipeline 5: Monitor OCO bracket exits" in source
    assert "p5_parent_order_id" in source
    assert "p5_stop_order_id" in source
    assert "p5_target_order_id" in source
    assert "p5_exit_written" in source


def test_dll_writes_stop_fill():
    """DLL writes a STOP fill event when the stop order fills."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    assert '"kind":"STOP"' in source.replace("\\", "").replace(" ", "").\
        replace('\\"', '"') or '"kind\\":\\"STOP\\"' in source or \
        '\"kind\":\"STOP\"' in source


def test_dll_writes_t1_fill():
    """DLL writes a T1 fill event when the target order fills."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    # In C source: "kind":"T1" appears as \\\"kind\\\":\\\"T1\\\" or "kind\":\"T1\"
    assert "T1" in source and "kind" in source and "target_info.AvgFillPrice" in source


def test_dll_stores_parent_order_for_monitoring():
    """After order submission, the DLL stores the parent order ID for exit monitoring."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    assert "GetPersistentInt(100) = submit_result" in source


def test_dll_exit_monitor_gated_by_enable_order():
    """Exit monitor only runs when EnableOrderPlacement >= 1."""
    dll_path = Path("sc_study/MES_AI_DataExport.cpp")
    if not dll_path.exists():
        pytest.skip("DLL source not found")
    source = dll_path.read_text()
    monitor_pos = source.find("Pipeline 5: Monitor OCO bracket exits")
    assert monitor_pos > 0
    # The if(EnableOrderPlacement) gate is right after the comment block
    following = source[monitor_pos:monitor_pos + 500]
    assert "EnableOrderPlacement" in following, \
        "Exit monitor must be gated by EnableOrderPlacement"
