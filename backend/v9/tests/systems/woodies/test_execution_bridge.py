"""Tests for Woodies Execution Bridge (PROMPT 4 · 4.2).

Acceptance: 4 public methods, each maps 1:1 to trade_manager.
RULE 15: NO modifications to trade_manager files, NO duplicate exec mechanics.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from unittest.mock import MagicMock, patch

from backend.v9.systems.woodies.execution_bridge import (
    WoodiesExecutionBridge,
    WoodiesIntent,
    IntentType,
    ExecutionResult,
)


@pytest.fixture
def bridge():
    """Bridge with no trade_manager (test mode)."""
    return WoodiesExecutionBridge()


@pytest.fixture
def mock_tm():
    """Mock trade_manager for integration tests."""
    tm = MagicMock()
    tm.accept_setup.return_value = 42  # trade_id
    tm.get_active_trades.return_value = []
    return tm


@pytest.fixture
def bridge_with_tm(mock_tm):
    return WoodiesExecutionBridge(trade_manager=mock_tm, mode="shadow")


# ── Test: 4 public methods exist ──────────────────────────────────

class TestPublicMethods:
    def test_has_submit_bracket(self, bridge):
        assert hasattr(bridge, "submit_bracket")

    def test_has_close_all(self, bridge):
        assert hasattr(bridge, "close_all")

    def test_has_close_contracts(self, bridge):
        assert hasattr(bridge, "close_contracts")

    def test_has_move_stop(self, bridge):
        assert hasattr(bridge, "move_stop")


# ── Test: submit_bracket ──────────────────────────────────────────

class TestSubmitBracket:
    def test_submit_returns_success(self, bridge):
        intent = WoodiesIntent(
            intent_type=IntentType.SUBMIT_BRACKET,
            reason="A7_approved",
            direction="LONG",
            stop_price=7395.0,
            t1_price=7405.0,
            t2_price=7415.0,
            t3_price=7435.0,
        )
        result = bridge.execute_intent(intent)
        assert result.success is True
        assert result.intent_type == "SUBMIT_BRACKET"

    def test_submit_calls_tm_accept_setup(self, bridge_with_tm, mock_tm):
        intent = WoodiesIntent(
            intent_type=IntentType.SUBMIT_BRACKET,
            reason="BUY",
            direction="LONG",
            stop_price=7395.0,
            t1_price=7405.0,
            t2_price=7415.0,
            t3_price=7435.0,
        )
        result = bridge_with_tm.execute_intent(intent)
        mock_tm.accept_setup.assert_called_once()
        setup = mock_tm.accept_setup.call_args[0][0]
        assert setup["firing_system"] == 4
        assert setup["direction"] == "LONG"
        assert setup["stop"] == 7395.0
        assert result.trade_id == 42


# ── Test: close_all ───────────────────────────────────────────────

class TestCloseAll:
    def test_close_all_returns_success(self, bridge):
        result = bridge.close_all(reason="STOP_LOSS")
        assert result.success is True
        assert result.intent_type == "CLOSE_ALL"

    def test_close_all_calls_tm_for_s4_trades(self, bridge_with_tm, mock_tm):
        """Only close S4 Woodies trades, not other systems."""
        trade_s4 = MagicMock()
        trade_s4.firing_system = 4
        trade_s4.id = 100
        trade_other = MagicMock()
        trade_other.firing_system = 2
        mock_tm.get_active_trades.return_value = [trade_s4, trade_other]

        result = bridge_with_tm.close_all(reason="EOD_FORCE")
        mock_tm.close_trade.assert_called_once_with(100, "EOD_FORCE")


# ── Test: close_contracts ─────────────────────────────────────────

class TestCloseContracts:
    def test_close_contracts_returns_success(self, bridge):
        result = bridge.close_contracts(count=1, reason="T1_HIT", target_level="T1")
        assert result.success is True

    def test_close_contracts_calls_tm_on_target_hit(self, bridge_with_tm, mock_tm):
        trade = MagicMock()
        trade.firing_system = 4
        trade.id = 200
        mock_tm.get_active_trades.return_value = [trade]

        result = bridge_with_tm.close_contracts(count=1, reason="T1", target_level="T1")
        mock_tm.on_target_hit.assert_called_once_with(200, "T1")


# ── Test: move_stop ───────────────────────────────────────────────

class TestMoveStop:
    def test_move_stop_returns_success(self, bridge):
        result = bridge.move_stop(new_price=7400.0, reason="Smart_BE")
        assert result.success is True
        assert result.details["new_stop_price"] == 7400.0

    def test_move_stop_no_price_fails(self, bridge):
        result = bridge.move_stop(new_price=None, reason="test")
        assert result.success is False


# ── Test: execute_intent dispatch ─────────────────────────────────

class TestExecuteIntentDispatch:
    def test_dispatch_submit(self, bridge):
        intent = WoodiesIntent(intent_type=IntentType.SUBMIT_BRACKET,
                               reason="test", direction="LONG")
        result = bridge.execute_intent(intent)
        assert result.intent_type == "SUBMIT_BRACKET"

    def test_dispatch_close_all(self, bridge):
        intent = WoodiesIntent(intent_type=IntentType.CLOSE_ALL, reason="B1")
        result = bridge.execute_intent(intent)
        assert result.intent_type == "CLOSE_ALL"

    def test_dispatch_close_contracts(self, bridge):
        intent = WoodiesIntent(intent_type=IntentType.CLOSE_CONTRACTS,
                               reason="T2", target_level="T2", contract_count=1)
        result = bridge.execute_intent(intent)
        assert result.intent_type == "CLOSE_CONTRACTS"

    def test_dispatch_move_stop(self, bridge):
        intent = WoodiesIntent(intent_type=IntentType.MOVE_STOP,
                               reason="tighten", new_stop_price=7400.0)
        result = bridge.execute_intent(intent)
        assert result.intent_type == "MOVE_STOP"


# ── Test: Intent log ──────────────────────────────────────────────

class TestIntentLog:
    def test_intents_logged(self, bridge):
        for i in range(3):
            intent = WoodiesIntent(intent_type=IntentType.CLOSE_ALL, reason=f"test-{i}")
            bridge.execute_intent(intent)
        assert len(bridge.get_intent_log()) == 3


# ── Test: RULE 15 D-067 boundary ─────────────────────────────────

class TestD067Boundary:
    def test_no_close_position_method(self, bridge):
        """RULE 15: Woodies module must NOT have close_position."""
        assert not hasattr(bridge, "close_position")

    def test_no_submit_order_method(self, bridge):
        """RULE 15: Woodies module must NOT have submit_order."""
        assert not hasattr(bridge, "submit_order")

    def test_no_cancel_order_method(self, bridge):
        assert not hasattr(bridge, "cancel_order")

    def test_bridge_only_calls_tm_public_api(self):
        """Verify bridge only references trade_manager's public methods."""
        import inspect
        from backend.v9.systems.woodies.execution_bridge import WoodiesExecutionBridge
        source = inspect.getsource(WoodiesExecutionBridge)
        # Should reference tm methods, NOT duplicate them
        assert "accept_setup" in source
        assert "close_trade" in source
        assert "on_target_hit" in source
        # Should NOT have raw order placement
        assert "submit_order" not in source
        assert "cancel_order" not in source
