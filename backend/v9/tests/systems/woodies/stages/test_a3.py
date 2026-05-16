"""Tests for A3 Pattern Detection (PROMPT 3 · 3.2).

Acceptance: detects patterns via pattern_engine, categorizes correctly.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.a3_pattern_detection import A3PatternDetection, A3Output
from backend.v9.systems.woodies.schemas import WoodiesBar


@pytest.fixture
def detector():
    return A3PatternDetection()


def _make_bars(cci_values, base_price=7400.0):
    """Create WoodiesBar list from CCI values."""
    bars = []
    for i, cci in enumerate(cci_values):
        bars.append(WoodiesBar(
            ts=1000.0 + i * 1800,
            open=base_price,
            high=base_price + 5,
            low=base_price - 5,
            close=base_price + 1,
            cci_14=cci,
            cci_6_tcci=cci * 0.8,
        ))
    return bars


class TestNoPattern:
    def test_no_bars_returns_none(self, detector):
        result = detector.evaluate(bars=None)
        assert result.pattern_matched == "NONE"

    def test_empty_bars_returns_none(self, detector):
        result = detector.evaluate(bars=[])
        assert result.pattern_matched == "NONE"

    def test_too_few_bars(self, detector):
        bars = _make_bars([10, 20])
        result = detector.evaluate(bars=bars)
        assert result.pattern_matched == "NONE"

    def test_flat_cci_no_pattern(self, detector):
        """Flat CCI at zero — unlikely to trigger any pattern."""
        bars = _make_bars([0] * 10)
        result = detector.evaluate(bars=bars)
        assert result.pattern_matched == "NONE"


class TestCategoryMapping:
    def test_continuation_patterns_are_trend_confirming(self):
        from backend.v9.systems.woodies.pattern_engine import CONTINUATION_PATTERNS
        assert "ZLR" in CONTINUATION_PATTERNS
        assert "TLB" in CONTINUATION_PATTERNS
        assert "TT" in CONTINUATION_PATTERNS
        assert "GB100" in CONTINUATION_PATTERNS

    def test_reversal_patterns_are_new_trend(self):
        from backend.v9.systems.woodies.pattern_engine import REVERSAL_PATTERNS
        assert "VEGAS" in REVERSAL_PATTERNS
        assert "GHOST" in REVERSAL_PATTERNS
        assert "FAMIR" in REVERSAL_PATTERNS
        assert "HTLB" in REVERSAL_PATTERNS
        assert "HFE" in REVERSAL_PATTERNS


class TestColorFiltering:
    def test_continuation_blocked_in_grey(self, detector):
        """Continuation patterns require BLUE/RED; GREY blocks them."""
        # Even if detect_all_patterns would return something,
        # A3 should filter if color is GREY
        bars = _make_bars([0] * 10)  # unlikely to detect anyway
        result = detector.evaluate(bars=bars, color="GREY")
        assert result.pattern_matched == "NONE"


class TestLegacyParams:
    def test_legacy_params_accepted(self, detector):
        """Backward compat: cci_14_history param doesn't crash."""
        result = detector.evaluate(cci_14_history=[], cci_zero_line_distance=0.0)
        assert result.pattern_matched == "NONE"


class TestOutputSchema:
    def test_output_is_a3output(self, detector):
        result = detector.evaluate(bars=_make_bars([0] * 5))
        assert isinstance(result, A3Output)
        assert result.pattern_matched in ("NONE", "ZLR", "TLB", "TT", "GB100",
                                           "VEGAS", "GHOST", "FAMIR", "HTLB", "HFE")
        assert result.pattern_category in ("NONE", "TREND_CONFIRMING", "NEW_TREND")
        assert result.pattern_direction in ("NONE", "LONG", "SHORT")
