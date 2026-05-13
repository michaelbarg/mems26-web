"""Tests for System 2: Chart 5-Min Detector + Matrix + Chop."""

import pytest
from backend.v9.systems.chart_5min.models import Bar, FIRST_HOUR_ELIGIBILITY, ALL_TIERS
from backend.v9.systems.chart_5min.detector import Chart5MinDetector
from backend.v9.systems.chart_5min.matrix import (
    lookup_matrix, classify_opportunity, sizing_for_classification,
)
from backend.v9.systems.chart_5min.schemas import ChopScore


# ─── Helpers ────────────────────────────────────────────────

def make_bar(o=100, h=101, c=100.5, l=99.5, vol=100, **kw) -> Bar:
    return Bar(o=o, h=h, l=l, c=c, vol=vol, **kw)


def make_bars(n, start=100, trend=0.5) -> list:
    """Generate n bars with optional trend."""
    bars = []
    for i in range(n):
        base = start + i * trend
        bars.append(make_bar(o=base, h=base + 1, l=base - 0.5, c=base + 0.3))
    return bars


# ─── Detector State ─────────────────────────────────────────

class TestDetectorState:
    def test_initial_state(self):
        d = Chart5MinDetector()
        state = d.get_state()
        assert state.bar_count == 0
        assert state.is_first_hour is True
        assert state.day_type is None

    def test_first_hour_flag(self):
        d = Chart5MinDetector()
        for _ in range(5):
            d.process_bar(make_bar())
        assert d.is_first_hour is True

        d.set_day_type("TREND_NORMAL", locked=True)
        assert d.is_first_hour is False

    def test_bar_count_increments(self):
        d = Chart5MinDetector()
        d.process_bar(make_bar())
        d.process_bar(make_bar())
        assert d.get_state().bar_count == 2

    def test_killzone_blocks(self):
        d = Chart5MinDetector()
        d.set_killzone(blocked=True)
        result = d.process_bar(make_bar())
        assert result is None

    def test_set_day_type(self):
        d = Chart5MinDetector()
        d.set_day_type("VARIATION", locked=True)
        assert d.get_state().day_type == "VARIATION"
        assert d.get_state().day_type_locked is True


# ─── Matrix Lookup ──────────────────────────────────────────

class TestMatrixLookup:
    def test_trend_normal_initiative_long(self):
        m = lookup_matrix("TREND_NORMAL", "initiative_buyer", "LONG")
        assert not m.blocked
        assert m.t1_reason == "momentum_push"
        assert m.t3_reason == "trail_vegas_ema"
        assert m.sizing == "FULL"

    def test_trend_normal_reactive_blocked(self):
        m = lookup_matrix("TREND_NORMAL", "reactive_buyer", "LONG")
        assert m.blocked
        assert "Suffering Side" in m.block_reason

    def test_variation_reactive(self):
        m = lookup_matrix("VARIATION", "reactive_buyer", "LONG")
        assert not m.blocked
        assert m.t1_reason == "poc_tpo_vwap"
        assert m.t2_contracts == 2
        assert m.time_stop_min == 60

    def test_variation_double_bottom(self):
        m = lookup_matrix("VARIATION", "double_bottom", "LONG")
        assert m.t1_reason == "neckline"

    def test_normal_reactive(self):
        m = lookup_matrix("NORMAL", "reactive_buyer", "LONG")
        assert m.t1_reason == "poc"
        assert m.sizing == "HALF"

    def test_trend_dd_initiative(self):
        m = lookup_matrix("TREND_DD", "initiative_buyer", "LONG")
        assert m.t3_reason == "second_dist_edge"
        assert m.sizing == "FULL"

    def test_neutral_scalps(self):
        m = lookup_matrix("NEUTRAL", "reactive_buyer", "LONG")
        assert m.t1_reason == "poc_return"
        assert m.sizing == "HALF"

    def test_nontrend_tiny(self):
        m = lookup_matrix("NONTREND", "reactive_buyer", "LONG")
        assert m.t1_reason == "3_5_ticks"
        assert m.sizing == "MIN"

    def test_first_hour_open_drive(self):
        m = lookup_matrix(
            "TREND_NORMAL", "initiative_buyer", "LONG",
            is_first_hour=True, opening_type="OPEN_DRIVE",
        )
        assert not m.blocked
        assert m.t3_reason is None  # no T3 in first hour

    def test_first_hour_no_strategic(self):
        m = lookup_matrix(
            "TREND_NORMAL", "bull_flag", "LONG",
            is_first_hour=True, opening_type="OPEN_DRIVE",
        )
        assert m.t3_reason is None

    def test_first_hour_blocked_combo(self):
        m = lookup_matrix(
            "TREND_NORMAL", "head_shoulders", "SHORT",
            is_first_hour=True, opening_type="OPEN_DRIVE",
        )
        assert m.blocked


# ─── Classification ─────────────────────────────────────────

class TestClassification:
    def test_tactical(self):
        assert classify_opportunity(1) == "TACTICAL"

    def test_tactical_plus(self):
        assert classify_opportunity(2) == "TACTICAL_PLUS"
        assert classify_opportunity(3) == "TACTICAL_PLUS"

    def test_strategic(self):
        assert classify_opportunity(4) == "STRATEGIC"
        assert classify_opportunity(5) == "STRATEGIC"

    def test_first_hour_no_strategic(self):
        assert classify_opportunity(4, is_first_hour=True) == "TACTICAL_PLUS"
        assert classify_opportunity(5, is_first_hour=True) == "TACTICAL_PLUS"

    def test_sizing(self):
        assert sizing_for_classification("TACTICAL") == "MIN"
        assert sizing_for_classification("TACTICAL_PLUS") == "HALF"
        assert sizing_for_classification("STRATEGIC") == "FULL"


# ─── Chop Detection ─────────────────────────────────────────

class TestChopDetection:
    def test_chop_needs_bars(self):
        d = Chart5MinDetector()
        for _ in range(3):
            d.process_bar(make_bar())
        chop = d.get_state().chop
        assert chop.composite == 0.0

    def test_choppy_market(self):
        """Alternating bullish/bearish bars = high chop."""
        d = Chart5MinDetector()
        for i in range(20):
            if i % 2 == 0:
                d.process_bar(make_bar(o=100, c=101, h=101.5, l=99.5))
            else:
                d.process_bar(make_bar(o=101, c=100, h=101.5, l=99.5))
        chop = d.get_state().chop
        assert chop.micro > 30  # should show choppiness


# ─── First Hour Eligibility ────────────────────────────────

class TestFirstHourEligibility:
    def test_bars_lt_4_empty(self):
        d = Chart5MinDetector()
        for _ in range(3):
            d.process_bar(make_bar())
        eligible = d._first_hour_eligible()
        assert eligible == []

    def test_bars_4_ofa_only(self):
        d = Chart5MinDetector()
        for _ in range(4):
            d.process_bar(make_bar())
        eligible = d._first_hour_eligible()
        assert "reactive_buyer" in eligible
        assert "bull_flag" not in eligible

    def test_bars_6_flags(self):
        d = Chart5MinDetector()
        for _ in range(6):
            d.process_bar(make_bar())
        eligible = d._first_hour_eligible()
        assert "bull_flag" in eligible
        assert "double_bottom" not in eligible

    def test_bars_10_double(self):
        d = Chart5MinDetector()
        for _ in range(10):
            d.process_bar(make_bar())
        eligible = d._first_hour_eligible()
        assert "double_bottom" in eligible


# ─── Tier Config ────────────────────────────────────────────

class TestTierConfig:
    def test_tier_1_patterns(self):
        assert "reactive_buyer" in ALL_TIERS[0].patterns
        assert "bull_flag" in ALL_TIERS[0].patterns

    def test_tier_2_patterns(self):
        assert "double_bottom" in ALL_TIERS[1].patterns
        assert "head_shoulders" in ALL_TIERS[1].patterns

    def test_tier_3_patterns(self):
        assert "cup_handle" in ALL_TIERS[2].patterns

    def test_tier_buffer_sizes(self):
        assert ALL_TIERS[0].buffer_size == 30
        assert ALL_TIERS[1].buffer_size == 80
        assert ALL_TIERS[2].buffer_size == 200
        assert ALL_TIERS[3].buffer_size == 500


# ─── Pattern Registry ──────────────────────────────────────

class TestPatternRegistry:
    def test_all_19_registered(self):
        from backend.v9.systems.chart_5min.patterns import PATTERN_REGISTRY
        assert len(PATTERN_REGISTRY) == 19  # 12 spec entries = 19 variants

    def test_all_callable(self):
        from backend.v9.systems.chart_5min.patterns import PATTERN_REGISTRY
        for name, fn in PATTERN_REGISTRY.items():
            assert callable(fn), f"{name} is not callable"

    def test_group_a_patterns(self):
        from backend.v9.systems.chart_5min.patterns import PATTERN_REGISTRY
        group_a = ["reactive_buyer", "reactive_seller",
                    "initiative_buyer", "initiative_seller"]
        for p in group_a:
            assert p in PATTERN_REGISTRY

    def test_group_b_patterns(self):
        from backend.v9.systems.chart_5min.patterns import PATTERN_REGISTRY
        group_b = ["double_bottom", "double_top", "bull_flag", "bear_flag",
                    "bull_pennant", "bear_pennant",
                    "ascending_triangle", "descending_triangle"]
        for p in group_b:
            assert p in PATTERN_REGISTRY

    def test_group_c_patterns(self):
        from backend.v9.systems.chart_5min.patterns import PATTERN_REGISTRY
        group_c = ["head_shoulders", "inverse_head_shoulders",
                    "symmetrical_triangle", "falling_wedge", "rising_wedge",
                    "cup_handle", "inverse_cup_handle"]
        for p in group_c:
            assert p in PATTERN_REGISTRY
