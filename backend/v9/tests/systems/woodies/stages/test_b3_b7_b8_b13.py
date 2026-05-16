"""Tests for B3+B7+B8+B13 (PROMPT 3 · 3.5).

B3: Color flip both directions + degradation
B7: Time stop at 60min without T1 + skip if T1 hit
B8: Counter-pattern tightening per stage
B13: EMA-169 trail trigger both directions
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.b3_color_flip import B3ColorFlip, B3Output
from backend.v9.systems.woodies.stages.b7_time_stop import B7TimeStop, B7Output
from backend.v9.systems.woodies.stages.b8_counter_pattern import B8CounterPattern, B8Output
from backend.v9.systems.woodies.stages.b13_trail_check import B13TrailCheck, B13Output


# ── B3 Color Flip ────────────────────────────────────────────────

class TestB3ColorFlip:
    def test_long_blue_to_red_flips(self):
        result = B3ColorFlip().evaluate(current_color="RED", entry_color="BLUE", direction="LONG")
        assert result.flip_detected is True
        assert result.action == "CLOSE_ALL"

    def test_short_red_to_blue_flips(self):
        result = B3ColorFlip().evaluate(current_color="BLUE", entry_color="RED", direction="SHORT")
        assert result.flip_detected is True
        assert result.action == "CLOSE_ALL"

    def test_no_flip_same_color(self):
        result = B3ColorFlip().evaluate(current_color="BLUE", entry_color="BLUE", direction="LONG")
        assert result.flip_detected is False
        assert result.action == "HOLD"

    def test_yellow_degradation_default_tighten(self):
        result = B3ColorFlip().evaluate(current_color="YELLOW", entry_color="BLUE", direction="LONG")
        assert result.action == "TIGHTEN"

    def test_grey_degradation(self):
        result = B3ColorFlip().evaluate(current_color="GREY", entry_color="BLUE", direction="LONG")
        assert result.action == "TIGHTEN"

    def test_degradation_configurable_exit(self):
        result = B3ColorFlip().evaluate(
            current_color="YELLOW", entry_color="BLUE", direction="LONG",
            degradation_action="EXIT",
        )
        assert result.action == "CLOSE_ALL"

    def test_priority_class(self):
        assert B3ColorFlip().priority_class == "STRATEGIC_EXIT"


# ── B7 Time Stop ─────────────────────────────────────────────────

class TestB7TimeStop:
    def test_60min_no_t1_triggers(self):
        result = B7TimeStop().evaluate(elapsed_minutes=60, t1_hit=False)
        assert result.time_stop_hit is True
        assert result.action == "CLOSE_ALL"

    def test_59min_no_trigger(self):
        result = B7TimeStop().evaluate(elapsed_minutes=59, t1_hit=False)
        assert result.time_stop_hit is False
        assert result.action == "HOLD"

    def test_60min_with_t1_no_trigger(self):
        """T1 hit → no time stop regardless of elapsed."""
        result = B7TimeStop().evaluate(elapsed_minutes=120, t1_hit=True)
        assert result.time_stop_hit is False
        assert result.action == "HOLD"

    def test_priority_class(self):
        assert B7TimeStop().priority_class == "TIME_EXIT"


# ── B8 Counter-Pattern ───────────────────────────────────────────

class TestB8CounterPattern:
    def test_no_bars_no_detection(self):
        result = B8CounterPattern().evaluate(bars=None, direction="LONG")
        assert result.counter_detected is False
        assert result.action == "HOLD"

    def test_tighten_pre_t1(self):
        """Pre-T1: tighten to 50% of T1 distance."""
        stage = B8CounterPattern()
        output = stage._tighten(t1_hit=False, t2_hit=False)
        assert output.tighten_destination == "50PCT_T1_DISTANCE"

    def test_tighten_post_t1(self):
        """Post-T1: tighten to entry."""
        stage = B8CounterPattern()
        output = stage._tighten(t1_hit=True, t2_hit=False)
        assert output.tighten_destination == "ENTRY"

    def test_tighten_post_t2(self):
        """Post-T2: tighten to T1 level."""
        stage = B8CounterPattern()
        output = stage._tighten(t1_hit=True, t2_hit=True)
        assert output.tighten_destination == "T1_LEVEL"

    def test_priority_class(self):
        assert B8CounterPattern().priority_class == "TIGHTEN"


# ── B13 Trail Check ──────────────────────────────────────────────

class TestB13TrailCheck:
    def test_long_below_ema_exits(self):
        result = B13TrailCheck().evaluate(
            vegas_ema_169=7400.0,
            current_price=7395.0,
            direction="LONG",
            t2_already_hit=True,
            trail_mode_active=True,
        )
        assert result.trail_exit is True
        assert result.action == "CLOSE_C3"

    def test_short_above_ema_exits(self):
        result = B13TrailCheck().evaluate(
            vegas_ema_169=7400.0,
            current_price=7405.0,
            direction="SHORT",
            t2_already_hit=True,
            trail_mode_active=True,
        )
        assert result.trail_exit is True
        assert result.action == "CLOSE_C3"

    def test_long_above_ema_holds(self):
        result = B13TrailCheck().evaluate(
            vegas_ema_169=7400.0,
            current_price=7410.0,
            direction="LONG",
            t2_already_hit=True,
            trail_mode_active=True,
        )
        assert result.trail_exit is False
        assert result.action == "HOLD"

    def test_not_trail_mode_holds(self):
        result = B13TrailCheck().evaluate(
            vegas_ema_169=7400.0,
            current_price=7395.0,
            direction="LONG",
            t2_already_hit=True,
            trail_mode_active=False,
        )
        assert result.trail_exit is False

    def test_no_t2_holds(self):
        result = B13TrailCheck().evaluate(
            vegas_ema_169=7400.0,
            current_price=7395.0,
            direction="LONG",
            t2_already_hit=False,
        )
        assert result.trail_exit is False

    def test_priority_class(self):
        assert B13TrailCheck().priority_class == "TRAIL"
