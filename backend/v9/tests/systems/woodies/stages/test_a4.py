"""Tests for A4 POC + Suffering Side Query (PROMPT 3 · 3.3).

Acceptance: REACTIVE/INITIATIVE classification, suffering warning, UFL/UFH bypass.
RULE 14: advisory only — suffering warning does NOT block entry.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.a4_poc_suffering_query import A4PocSufferingQuery, A4Output


@pytest.fixture
def stage():
    return A4PocSufferingQuery()


class TestClassificationHint:
    def test_near_ib_edge_is_reactive(self, stage):
        result = stage.evaluate(
            entry_direction="LONG",
            current_price=7472.0,
            poc_location=7400.0,
            ib_high=7473.0,
            ib_low=7200.0,
        )
        assert result.entry_classification_hint == "REACTIVE"

    def test_near_middle_poc_migrating_is_initiative(self, stage):
        result = stage.evaluate(
            entry_direction="LONG",
            current_price=7410.0,
            poc_location=7400.0,
            ib_high=7473.0,
            ib_low=7200.0,
        )
        assert result.entry_classification_hint == "INITIATIVE"


class TestSufferingWarning:
    def test_buyers_suffering_long_warns(self, stage):
        result = stage.evaluate(
            entry_direction="LONG",
            current_price=7400.0,
            poc_location=7400.0,
            suffering_side="BUYERS",
        )
        assert result.suffering_warning == "SUFFERING_SIDE"

    def test_sellers_suffering_short_warns(self, stage):
        result = stage.evaluate(
            entry_direction="SHORT",
            current_price=7400.0,
            poc_location=7400.0,
            suffering_side="SELLERS",
        )
        assert result.suffering_warning == "SUFFERING_SIDE"

    def test_no_suffering_match_no_warning(self, stage):
        result = stage.evaluate(
            entry_direction="LONG",
            current_price=7400.0,
            poc_location=7400.0,
            suffering_side="SELLERS",  # sellers suffering, we're LONG → safe
        )
        assert result.suffering_warning == "NONE"


class TestUflUfhBypass:
    def test_in_ufl_bypasses_suffering(self, stage):
        result = stage.evaluate(
            entry_direction="LONG",
            current_price=7170.0,
            poc_location=7400.0,
            suffering_side="BUYERS",
            ufl_ufh={"ufl": 7172.0, "ufh": 7475.0},
        )
        assert result.bypass_active == "UFL"
        assert result.suffering_warning == "NONE"

    def test_in_ufh_bypasses_suffering(self, stage):
        result = stage.evaluate(
            entry_direction="SHORT",
            current_price=7476.0,
            poc_location=7400.0,
            suffering_side="SELLERS",
            ufl_ufh={"ufl": 7172.0, "ufh": 7475.0},
        )
        assert result.bypass_active == "UFH"


class TestDegradedMode:
    def test_no_data_returns_initiative(self, stage):
        result = stage.evaluate()
        assert result.entry_classification_hint == "INITIATIVE"
        assert result.suffering_warning == "NONE"

    def test_no_poc_returns_degraded(self, stage):
        result = stage.evaluate(current_price=7400.0, poc_location=None)
        assert result.entry_classification_hint == "INITIATIVE"


class TestAdvisoryNoVeto:
    def test_suffering_warning_is_advisory_not_block(self, stage):
        """RULE 14: suffering warning → advisory output, NOT a block."""
        result = stage.evaluate(
            entry_direction="LONG",
            current_price=7400.0,
            poc_location=7400.0,
            suffering_side="BUYERS",
        )
        # Warning fires but NO veto/block field exists
        assert result.suffering_warning == "SUFFERING_SIDE"
        assert not hasattr(result, "veto")
        assert not hasattr(result, "entry_blocked")
