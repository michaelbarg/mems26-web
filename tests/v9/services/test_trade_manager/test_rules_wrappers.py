"""18 tests for the 5 RiskRule wrapper modules + 3 skip-log rate-limit tests."""
from __future__ import annotations

import pytest

from backend.v9.services.trade_manager.rules.base import (
    Layer4Context,
    PRE_TIGHTEN,
    POST_TIGHTEN,
    _skip_limiter,
)
from backend.v9.services.trade_manager.rules.mfe_peak import MFETightenRule
from backend.v9.services.trade_manager.rules.cci_flat import CCIFlatRule
from backend.v9.services.trade_manager.rules.tcci_cross import TCCIExitRule
from backend.v9.services.trade_manager.rules.swi import SWITightenRule
from backend.v9.services.trade_manager.rules.day_type_targets import DayTypeTargetsVerifyRule


# ---------------------------------------------------------------------------
# Fixture: reset skip limiter before and after each test
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_skip_limiter():
    _skip_limiter.reset()
    yield
    _skip_limiter.reset()


# ---------------------------------------------------------------------------
# Shared trade dicts
# ---------------------------------------------------------------------------
_LONG_TRADE = {
    "direction": "LONG",
    "entry": 5000.0,
    "stop": 4990.0,
    "stop_price": 4990.0,
    "t2": 5020.0,
    "mfe": 5016.5,
    "current_price": 5015.0,
    "day_type_at_entry": "TREND",
}

_SHORT_TRADE = {
    "direction": "SHORT",
    "entry": 5000.0,
    "stop": 5010.0,
    "stop_price": 5010.0,
    "t2": 4980.0,
    "mfe": 4983.5,
    "current_price": 4985.0,
    "day_type_at_entry": "TREND",
}


# ---------------------------------------------------------------------------
# MFETightenRule (order=1, PRE_TIGHTEN)
# ---------------------------------------------------------------------------
class TestMFETightenRule:
    def setup_method(self):
        self.rule = MFETightenRule()

    def test_phase_and_name(self):
        assert self.rule.name == "MFE_PEAK"
        assert self.rule.phase == PRE_TIGHTEN

    def test_returns_tighten_when_mfe_above_threshold(self):
        ctx = Layer4Context()
        result = self.rule.evaluate(_LONG_TRADE, ctx)
        # MFE = 5016.5, T2 = 5020, distance = 20, mfe_distance = 16.5 → 82.5% > 80%
        assert result is not None
        assert result["action"] == "TIGHTEN_STOP"
        assert result["new_stop"] > _LONG_TRADE["stop"]

    def test_returns_none_when_mfe_below_threshold(self):
        trade = {**_LONG_TRADE, "mfe": 5001.0}  # only 5% of T2 distance
        ctx = Layer4Context()
        assert self.rule.evaluate(trade, ctx) is None


# ---------------------------------------------------------------------------
# CCIFlatRule (order=2, PRE_TIGHTEN)
# ---------------------------------------------------------------------------
class TestCCIFlatRule:
    def setup_method(self):
        self.rule = CCIFlatRule()

    def test_phase_and_name(self):
        assert self.rule.name == "CCI_FLAT"
        assert self.rule.phase == PRE_TIGHTEN

    def test_returns_tighten_when_cci_flat(self):
        cci_history = [5.0, 6.0, 7.0, 5.5]  # all within ±10 of each other
        ctx = Layer4Context(cci_history=cci_history)
        result = self.rule.evaluate(_LONG_TRADE, ctx)
        assert result is not None
        assert result["action"] == "TIGHTEN_STOP"

    def test_skip_log_when_cci_history_none(self):
        ctx = Layer4Context(cci_history=None)
        # First call: should log (limiter allows), returns None
        result = self.rule.evaluate(_LONG_TRADE, ctx)
        assert result is None

    def test_returns_none_when_cci_not_flat(self):
        cci_history = [5.0, 50.0, 5.0]  # large swings
        ctx = Layer4Context(cci_history=cci_history)
        assert self.rule.evaluate(_LONG_TRADE, ctx) is None


# ---------------------------------------------------------------------------
# TCCIExitRule (order=3, PRE_TIGHTEN)
# ---------------------------------------------------------------------------
class TestTCCIExitRule:
    def setup_method(self):
        self.rule = TCCIExitRule()

    def test_phase_and_name(self):
        assert self.rule.name == "TCCI_CROSS"
        assert self.rule.phase == PRE_TIGHTEN

    def test_returns_exit_on_direction_change_against_trade(self):
        dce = {"type": "DIRECTION_CHANGE", "direction": "BEARISH", "reasoning_notes": "cross"}
        ctx = Layer4Context(direction_change_event=dce)
        result = self.rule.evaluate(_LONG_TRADE, ctx)
        assert result is not None
        assert result["action"] == "EXIT"

    def test_returns_none_when_no_direction_change(self):
        ctx = Layer4Context(direction_change_event=None)
        assert self.rule.evaluate(_LONG_TRADE, ctx) is None

    def test_returns_none_when_direction_change_aligned_with_trade(self):
        dce = {"type": "DIRECTION_CHANGE", "direction": "BULLISH", "reasoning_notes": "cross"}
        ctx = Layer4Context(direction_change_event=dce)
        # Bullish cross with a LONG trade — no exit
        assert self.rule.evaluate(_LONG_TRADE, ctx) is None


# ---------------------------------------------------------------------------
# SWITightenRule (order=4, PRE_TIGHTEN)
# ---------------------------------------------------------------------------
class TestSWITightenRule:
    def setup_method(self):
        self.rule = SWITightenRule()

    def test_phase_and_name(self):
        assert self.rule.name == "SWI"
        assert self.rule.phase == PRE_TIGHTEN

    def test_returns_tighten_when_swi_red(self):
        swi = {"value": -0.5, "color": "red"}
        ctx = Layer4Context(swi=swi)
        result = self.rule.evaluate(_LONG_TRADE, ctx)
        assert result is not None
        assert result["action"] == "TIGHTEN_STOP"

    def test_skip_log_when_swi_none(self):
        ctx = Layer4Context(swi=None)
        result = self.rule.evaluate(_LONG_TRADE, ctx)
        assert result is None

    def test_returns_none_when_swi_not_red(self):
        swi = {"value": 0.5, "color": "green"}
        ctx = Layer4Context(swi=swi)
        assert self.rule.evaluate(_LONG_TRADE, ctx) is None


# ---------------------------------------------------------------------------
# DayTypeTargetsVerifyRule (order=5, POST_TIGHTEN)
# ---------------------------------------------------------------------------
class TestDayTypeTargetsVerifyRule:
    def setup_method(self):
        self.rule = DayTypeTargetsVerifyRule()

    def test_phase_and_name(self):
        assert self.rule.name == "DAY_TYPE_TARGETS"
        assert self.rule.phase == POST_TIGHTEN

    def test_skip_log_when_current_day_type_none(self):
        ctx = Layer4Context(current_day_type=None)
        result = self.rule.evaluate(_LONG_TRADE, ctx)
        assert result is None

    def test_returns_none_when_day_type_consistent(self):
        # entry day type == current day type → no action
        ctx = Layer4Context(current_day_type="TREND")
        result = self.rule.evaluate(_LONG_TRADE, ctx)
        assert result is None


# ---------------------------------------------------------------------------
# Skip-log rate-limit tests (3 tests)
# ---------------------------------------------------------------------------
def test_skip_limiter_emits_first_call():
    """should_log returns True on first call for a new rule name."""
    _skip_limiter.reset("TEST_RULE")
    assert _skip_limiter.should_log("TEST_RULE") is True


def test_skip_limiter_suppresses_second_immediate_call():
    """should_log returns False on the second consecutive call within the cooldown."""
    _skip_limiter.reset("TEST_RULE2")
    _skip_limiter.should_log("TEST_RULE2")  # first — True
    assert _skip_limiter.should_log("TEST_RULE2") is False  # second — suppressed


def test_skip_limiter_reset_clears_state():
    """After reset(), should_log returns True again."""
    _skip_limiter.should_log("TEST_RULE3")
    _skip_limiter.reset("TEST_RULE3")
    assert _skip_limiter.should_log("TEST_RULE3") is True
