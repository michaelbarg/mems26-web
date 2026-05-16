"""Tests for A6 Entry Classification (PROMPT 3 · 3.2).

Acceptance: REACTIVE for HFE/FAMIR, INITIATIVE for VEGAS/GHOST/TLB,
pattern-wins-conflict test.
"""

import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")

import pytest
from backend.v9.systems.woodies.stages.a6_entry_classification import (
    A6EntryClassification,
    A6Output,
    REACTIVE_PATTERNS,
    INITIATIVE_PATTERNS,
)


@pytest.fixture
def classifier():
    return A6EntryClassification()


class TestReactiveClassification:
    def test_hfe_is_reactive(self, classifier):
        result = classifier.evaluate(pattern_matched="HFE")
        assert result.entry_classification == "REACTIVE"
        assert result.position_size == 2
        assert result.management_profile == "TIGHT"

    def test_famir_is_reactive(self, classifier):
        result = classifier.evaluate(pattern_matched="FAMIR")
        assert result.entry_classification == "REACTIVE"

    def test_tt_is_reactive(self, classifier):
        result = classifier.evaluate(pattern_matched="TT")
        assert result.entry_classification == "REACTIVE"


class TestInitiativeClassification:
    def test_vegas_is_initiative(self, classifier):
        result = classifier.evaluate(pattern_matched="VEGAS")
        assert result.entry_classification == "INITIATIVE"
        assert result.position_size == 3
        assert result.management_profile == "WIDE"

    def test_ghost_is_initiative(self, classifier):
        result = classifier.evaluate(pattern_matched="GHOST")
        assert result.entry_classification == "INITIATIVE"

    def test_tlb_is_initiative(self, classifier):
        result = classifier.evaluate(pattern_matched="TLB")
        assert result.entry_classification == "INITIATIVE"

    def test_htlb_is_initiative(self, classifier):
        result = classifier.evaluate(pattern_matched="HTLB")
        assert result.entry_classification == "INITIATIVE"

    def test_zlr_is_initiative(self, classifier):
        result = classifier.evaluate(pattern_matched="ZLR")
        assert result.entry_classification == "INITIATIVE"

    def test_gb100_is_initiative(self, classifier):
        result = classifier.evaluate(pattern_matched="GB100")
        assert result.entry_classification == "INITIATIVE"


class TestPatternWinsConflict:
    def test_pattern_hfe_overrides_initiative_hint(self, classifier):
        """Pattern=HFE → REACTIVE, even when A4 hint says INITIATIVE."""
        result = classifier.evaluate(
            pattern_matched="HFE",
            entry_classification_hint="INITIATIVE",
        )
        assert result.entry_classification == "REACTIVE"

    def test_pattern_vegas_overrides_reactive_hint(self, classifier):
        """Pattern=VEGAS → INITIATIVE, even when A4 hint says REACTIVE."""
        result = classifier.evaluate(
            pattern_matched="VEGAS",
            entry_classification_hint="REACTIVE",
        )
        assert result.entry_classification == "INITIATIVE"


class TestNoPattern:
    def test_none_pattern_defaults_initiative(self, classifier):
        result = classifier.evaluate(pattern_matched="NONE")
        assert result.entry_classification == "INITIATIVE"

    def test_empty_pattern_defaults_initiative(self, classifier):
        result = classifier.evaluate(pattern_matched="")
        assert result.entry_classification == "INITIATIVE"


class TestPositionSizing:
    def test_reactive_size_2(self, classifier):
        result = classifier.evaluate(pattern_matched="HFE")
        assert result.position_size == 2

    def test_initiative_size_3(self, classifier):
        result = classifier.evaluate(pattern_matched="VEGAS")
        assert result.position_size == 3


class TestAllPatternsCovered:
    def test_all_reactive_patterns(self):
        assert REACTIVE_PATTERNS == {"HFE", "FAMIR", "TT"}

    def test_all_initiative_patterns(self):
        assert INITIATIVE_PATTERNS == {"VEGAS", "GHOST", "TLB", "HTLB", "ZLR", "GB100"}

    def test_all_9_patterns_classified(self):
        """All 9 patterns should be in either REACTIVE or INITIATIVE."""
        all_patterns = REACTIVE_PATTERNS | INITIATIVE_PATTERNS
        assert len(all_patterns) == 9
