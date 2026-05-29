"""W-10 TIME_STOP must set exit_price before close_trade.

Anti-regression for Bug D (pnl=0 because manager._calculate_pnl falls
back to entry_price when exit_price is NULL).
"""

from unittest.mock import MagicMock, call

from backend.v9.systems.woodies.woodies_system import WoodiesSystem


def test_time_stop_sets_exit_price_before_close():
    """exit_price = self._closes[-1] is set on the trade BEFORE close_trade."""
    system = WoodiesSystem(db_path=":memory:")

    mock_trade = MagicMock()
    mock_trade.exit_price = None

    mock_tm = MagicMock()
    mock_tm._get_trade.return_value = mock_trade

    mock_gateway = MagicMock()
    mock_gateway._trade_manager = mock_tm
    system._gateway = mock_gateway
    system._closes = [5600.25]

    # Force enforcer to fire
    system._time_stop_enforcer = MagicMock()
    system._time_stop_enforcer.check.return_value = MagicMock(fired=True)

    system._open_fire_records["99"] = {
        "entry_bar_count": 1,
        "pattern_id": "ZLR",
    }
    system._bar_count = 20

    system._check_time_stops()

    # Verify exit_price was set
    assert mock_trade.exit_price == 5600.25
    # Verify close_trade was called
    mock_tm.close_trade.assert_called_once_with(99, "TIME_STOP")


def test_time_stop_skipped_when_closes_empty():
    """If _closes is empty, close_trade is NOT called and trade is removed."""
    system = WoodiesSystem(db_path=":memory:")

    mock_tm = MagicMock()
    mock_gateway = MagicMock()
    mock_gateway._trade_manager = mock_tm
    system._gateway = mock_gateway
    system._closes = []  # empty

    system._time_stop_enforcer = MagicMock()
    system._time_stop_enforcer.check.return_value = MagicMock(fired=True)

    system._open_fire_records["99"] = {
        "entry_bar_count": 1,
        "pattern_id": "ZLR",
    }
    system._bar_count = 20

    system._check_time_stops()

    # close_trade NOT called (no exit_price available)
    mock_tm.close_trade.assert_not_called()
    # But record is still removed to avoid infinite loop
    assert "99" not in system._open_fire_records
