"""Tests for A1 Strategic Gate (PROMPT 3 · 3.2).

Acceptance: 5 color scenarios (BLUE/RED/GREY/YELLOW/INDETERMINATE).
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.a1_strategic_gate import A1StrategicGate, StrategicGateResult as A1Output


@pytest.fixture
def gate():
    return A1StrategicGate()


class TestBlueColor:
    def test_6_bars_above_zero_is_blue(self, gate):
        history = [10, 20, 15, 25, 30, 12, 18]  # 7 bars > 0
        result = gate.evaluate(cci_14_value=18, cci_14_history=history)
        assert result.color == "BLUE"
        assert result.direction_allowed == "LONG"

    def test_exactly_6_bars_above(self, gate):
        history = [-5, 10, 20, 15, 25, 30, 12]  # 6 above after -5
        result = gate.evaluate(cci_14_value=12, cci_14_history=history)
        assert result.color == "BLUE"
        assert result.direction_allowed == "LONG"


class TestRedColor:
    def test_6_bars_below_zero_is_red(self, gate):
        history = [-10, -20, -15, -25, -30, -12, -18]
        result = gate.evaluate(cci_14_value=-18, cci_14_history=history)
        assert result.color == "RED"
        assert result.direction_allowed == "SHORT"

    def test_exactly_6_bars_below(self, gate):
        history = [5, -10, -20, -15, -25, -30, -12]
        result = gate.evaluate(cci_14_value=-12, cci_14_history=history)
        assert result.color == "RED"
        assert result.direction_allowed == "SHORT"


class TestGreyColor:
    def test_frequent_crosses_is_grey(self, gate):
        # 4 crosses in 10 bars (above threshold of 3)
        history = [10, -5, 10, -5, 10, -5, 10, -5, 10, 5]
        result = gate.evaluate(cci_14_value=5, cci_14_history=history)
        assert result.color == "GREY"
        assert result.direction_allowed == "NONE"


class TestYellowColor:
    def test_trend_change_blue_after_red_is_yellow(self, gate):
        # 6+ bars below zero, then 6+ bars above zero = YELLOW (transition)
        history = [-10, -20, -15, -25, -30, -12, -8, 5, 10, 15, 20, 25, 30, 12]
        result = gate.evaluate(cci_14_value=12, cci_14_history=history)
        assert result.color == "YELLOW"
        assert result.direction_allowed == "NONE"

    def test_trend_change_red_after_blue_is_yellow(self, gate):
        history = [10, 20, 15, 25, 30, 12, 8, -5, -10, -15, -20, -25, -30, -12]
        result = gate.evaluate(cci_14_value=-12, cci_14_history=history)
        assert result.color == "YELLOW"
        assert result.direction_allowed == "NONE"


class TestIndeterminateColor:
    def test_insufficient_bars_indeterminate(self, gate):
        history = [10, 20, 15]  # only 3 bars above, < 6
        result = gate.evaluate(cci_14_value=15, cci_14_history=history)
        assert result.color == "INDETERMINATE"
        assert result.direction_allowed == "NONE"

    def test_empty_history(self, gate):
        result = gate.evaluate(cci_14_value=0, cci_14_history=[])
        assert result.color == "INDETERMINATE"
        assert result.direction_allowed == "NONE"


class TestTerminalStates:
    def test_grey_is_skip(self, gate):
        """GREY → direction NONE (causes SKIP in entry engine)."""
        history = [10, -5, 10, -5, 10, -5, 10, -5, 10, 5]
        result = gate.evaluate(cci_14_value=5, cci_14_history=history)
        assert result.direction_allowed == "NONE"

    def test_yellow_is_skip(self, gate):
        """YELLOW → direction NONE (causes SKIP)."""
        history = [-10, -20, -15, -25, -30, -12, -8, 5, 10, 15, 20, 25, 30, 12]
        result = gate.evaluate(cci_14_value=12, cci_14_history=history)
        assert result.direction_allowed == "NONE"

    def test_indeterminate_is_skip(self, gate):
        """INDETERMINATE → direction NONE."""
        result = gate.evaluate(cci_14_value=10, cci_14_history=[10, 20])
        assert result.direction_allowed == "NONE"
