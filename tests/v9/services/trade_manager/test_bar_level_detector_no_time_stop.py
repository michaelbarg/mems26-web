"""BarLevelDetector — Layer 4 TIME_STOP removed (2026-05-28 evening).

W-10 is sole TIME_STOP authority. BarLevelDetector handles only
stop/target hit detection. This test verifies the TIME_STOP code
is fully removed.
"""

import inspect

from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


def test_no_time_stop_by_day_type_constant():
    """TIME_STOP_BY_DAY_TYPE constant must not exist in bar_level_detector."""
    import backend.v9.services.trade_manager.bar_level_detector as mod
    assert not hasattr(mod, "TIME_STOP_BY_DAY_TYPE"), (
        "TIME_STOP_BY_DAY_TYPE should be deleted — W-10 is sole TIME_STOP authority."
    )


def test_no_check_time_stop_method():
    """_check_time_stop method must not exist on BarLevelDetector."""
    assert not hasattr(BarLevelDetector, "_check_time_stop"), (
        "_check_time_stop should be deleted — W-10 is sole TIME_STOP authority."
    )


def test_on_bar_does_not_reference_time_stop():
    """on_bar source should not contain TIME_STOP or _check_time_stop calls."""
    src = inspect.getsource(BarLevelDetector.on_bar)
    assert "_check_time_stop" not in src
    assert "TIME_STOP" not in src


def test_parse_ts_preserved():
    """_parse_ts is kept for stop/target hit logic."""
    from datetime import datetime, timezone
    det = BarLevelDetector.__new__(BarLevelDetector)
    # int timestamp
    result = det._parse_ts(1716900000)
    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc
    # None
    assert det._parse_ts(None) is None
