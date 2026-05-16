"""Tests for A2 Day Type Query (PROMPT 3 · 3.3).

Acceptance: correct preferences for all 6 day types + degraded mode.
RULE 14: advisory only — NEVER vetoes entry.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.a2_day_type_query import A2DayTypeQuery, A2Output


@pytest.fixture
def stage():
    return A2DayTypeQuery()


class TestDayTypePreferences:
    def test_trend_day(self, stage):
        result = stage.evaluate(day_type="TREND")
        assert "ZLR" in result.pattern_preference
        assert result.color_volatility_expectation == "LOW"

    def test_range_day(self, stage):
        result = stage.evaluate(day_type="RANGE")
        assert "HFE" in result.pattern_preference
        assert result.color_volatility_expectation == "HIGH"

    def test_reversal_day(self, stage):
        result = stage.evaluate(day_type="REVERSAL")
        assert "VEGAS" in result.pattern_preference
        assert "GHOST" in result.pattern_preference

    def test_gap_fill(self, stage):
        result = stage.evaluate(day_type="GAP_FILL")
        assert result.pattern_preference == []  # bias handled in A6

    def test_broad_channel(self, stage):
        result = stage.evaluate(day_type="BROAD_CHANNEL")
        assert "HFE" in result.pattern_preference

    def test_neutral(self, stage):
        result = stage.evaluate(day_type="NEUTRAL")
        assert result.pattern_preference == []
        assert result.color_volatility_expectation == "MEDIUM"


class TestDegradedMode:
    def test_none_day_type_returns_no_preference(self, stage):
        result = stage.evaluate(day_type=None)
        assert result.pattern_preference == []
        assert result.color_volatility_expectation == "MEDIUM"


class TestAdvisoryOnly:
    def test_output_is_advisory_no_blocking(self, stage):
        """RULE 14: A2 output has NO blocking/veto field."""
        result = stage.evaluate(day_type="TREND")
        assert isinstance(result, A2Output)
        assert not hasattr(result, "veto")
        assert not hasattr(result, "block")
