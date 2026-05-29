"""W-10 TimeStopEnforcer enabled regression test.

After 2026-05-28 evening decision (Option B REVERSED), W-10 (Registry #11)
is the sole TIME_STOP authority. The Woodies-side enforcer is enabled via YAML
(time_stop_minutes: 90). Layer 4 TIME_STOP code removed from bar_level_detector.

Bug A fixed: _bar_count increments only when bar.ts changes.
Bug D fixed: exit_price = self._closes[-1] set before close_trade().
"""

from backend.v9.systems.woodies.time_stop import (
    TimeStopEnforcer,
    load_time_stop_config,
)


def test_dispatcher_yaml_has_90_time_stop_minutes():
    """YAML config must have time_stop_minutes=90 (W-10 enabled)."""
    cfg = load_time_stop_config()
    assert cfg["time_stop_minutes"] == 90, (
        "dispatcher_config.yaml::time_stop.time_stop_minutes must be 90. "
        "W-10 is the sole TIME_STOP authority per 2026-05-28 evening decision."
    )


def test_enforcer_with_90_minutes_fires_at_18_bars():
    """W-10 fires at 18 bars (90 min / 5 min = 18)."""
    enf = TimeStopEnforcer(time_stop_minutes=90, tick_minutes=5)
    assert enf.limit_bars == 18
    res_17 = enf.check(bars_open=17, pattern_id="ZLR", trade_id="t1")
    assert res_17.fired is False
    res_18 = enf.check(bars_open=18, pattern_id="ZLR", trade_id="t1")
    assert res_18.fired is True


def test_woodies_system_time_stop_fires_and_removes():
    """End-to-end: WoodiesSystem with real YAML fires TIME_STOP at limit."""
    from unittest.mock import MagicMock

    from backend.v9.systems.woodies.woodies_system import WoodiesSystem

    system = WoodiesSystem(db_path=":memory:")
    mock_trade = MagicMock()
    mock_trade.exit_price = None
    mock_tm = MagicMock()
    mock_tm._get_trade.return_value = mock_trade
    mock_gateway = MagicMock()
    mock_gateway._trade_manager = mock_tm
    system._gateway = mock_gateway
    system._closes = [5500.0]

    system._open_fire_records["42"] = {
        "entry_bar_count": 1,
        "pattern_id": "GB100",
    }
    system._bar_count = 20  # bars_open = 19 >= 18

    system._check_time_stops()

    # W-10 fires: close_trade called, record removed
    mock_tm.close_trade.assert_called_once_with(42, "TIME_STOP")
    assert "42" not in system._open_fire_records
    # Bug D fix: exit_price was set before close_trade
    assert mock_trade.exit_price == 5500.0
