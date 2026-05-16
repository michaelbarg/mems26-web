"""Tests for A5 OTF Clarity Query (PROMPT 3 · 3.3).

Acceptance: 4 OTF states mapped correctly.
RULE 14: advisory only — NO_CLARITY → warning, NOT veto.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.a5_otf_clarity_query import A5OtfClarityQuery, A5Output


@pytest.fixture
def stage():
    return A5OtfClarityQuery()


class TestOtfStateMapping:
    def test_both_clear_safe(self, stage):
        result = stage.evaluate(otf_clarity="BOTH_CLEAR", entry_direction="LONG")
        assert result.clarity_warning == "NONE"
        assert result.otf_state_value == "BOTH_CLEAR"

    def test_sellers_clear_long_safe(self, stage):
        result = stage.evaluate(otf_clarity="SELLERS_CLEAR", entry_direction="LONG")
        assert result.clarity_warning == "NONE"

    def test_buyers_clear_short_safe(self, stage):
        result = stage.evaluate(otf_clarity="BUYERS_CLEAR", entry_direction="SHORT")
        assert result.clarity_warning == "NONE"

    def test_unclear_warns(self, stage):
        result = stage.evaluate(otf_clarity="UNCLEAR", entry_direction="LONG")
        assert result.clarity_warning == "NO_CLARITY"

    def test_sellers_clear_short_mismatch(self, stage):
        result = stage.evaluate(otf_clarity="SELLERS_CLEAR", entry_direction="SHORT")
        assert result.clarity_warning == "DIRECTION_MISMATCH"

    def test_buyers_clear_long_mismatch(self, stage):
        result = stage.evaluate(otf_clarity="BUYERS_CLEAR", entry_direction="LONG")
        assert result.clarity_warning == "DIRECTION_MISMATCH"


class TestDegradedMode:
    def test_none_clarity_returns_unavailable(self, stage):
        result = stage.evaluate(otf_clarity=None)
        assert result.clarity_warning == "NONE"
        assert result.otf_state_value == "UNAVAILABLE"


class TestAdvisoryNoVeto:
    def test_no_clarity_is_warning_not_block(self, stage):
        """RULE 14: UNCLEAR → NO_CLARITY warning, NOT a veto."""
        result = stage.evaluate(otf_clarity="UNCLEAR", entry_direction="LONG")
        assert result.clarity_warning == "NO_CLARITY"
        assert not hasattr(result, "veto")
        assert not hasattr(result, "entry_blocked")

    def test_mismatch_is_warning_not_block(self, stage):
        result = stage.evaluate(otf_clarity="SELLERS_CLEAR", entry_direction="SHORT")
        assert result.clarity_warning == "DIRECTION_MISMATCH"
        assert not hasattr(result, "veto")
