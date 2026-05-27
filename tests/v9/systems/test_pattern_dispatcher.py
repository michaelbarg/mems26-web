"""Tests for W-8 Two-tier R_t1 Pattern Dispatcher.

Covers:
  - Single / empty pattern edge cases
  - YELLOW raises ValueError
  - Within-family max(r_t1) selection (CONT and REV)
  - BLUE/RED prefers CONT over higher-R_t1 REV
  - GRAY uses max(r_t1) across all families
  - No CONT in BLUE falls back cross-family
  - HTLB groups with REV
  - r_t1 missing fallback to confidence
  - Tie-breaker: same r_t1, different confidence
  - YAML config: missing, valid, invalid
  - woodies_system integration (PatternDispatcher wired in)
  - raw_confidence still emitted (W-6 intact)
"""

import os
import tempfile
import pytest
import logging

from backend.v9.systems.woodies.pattern_dispatcher import (
    PatternDispatcher,
    Family,
    FAMILY_MAP,
    DispatchResult,
)
from backend.v9.systems.woodies.schemas import PatternResult, PatternId
from backend.v9.systems.woodies.stages.a1_strategic_gate import TrendState


def _make_pattern(
    pattern_id: str = "ZLR",
    direction: str = "LONG",
    confidence: float = 0.7,
    r_t1: float = 1.5,
    group: str = "CONTINUATION",
    detected: bool = True,
    raw_confidence: float = None,
) -> PatternResult:
    """Helper to build a PatternResult for testing."""
    return PatternResult(
        detected=detected,
        pattern_id=pattern_id,
        direction=direction,
        confidence=confidence,
        raw_confidence=raw_confidence if raw_confidence is not None else confidence,
        r_t1=r_t1,
        entry_price=100.0,
        stop=99.0,
        targets=[101.0, 102.0],
        group=group,
        cci_at_signal=50.0,
        bar_index=10,
        ts=1000.0,
    )


class TestPatternDispatcherEdgeCases:
    """Tests 1-3: edge cases."""

    def test_single_pattern_wins(self):
        """Test 1: single pattern returns that pattern."""
        d = PatternDispatcher()
        p = _make_pattern("ZLR", r_t1=2.0)
        result = d.select_winner([p], TrendState.BLUE)
        assert result.winner is p
        assert result.selection_path == "single_pattern"
        assert result.winning_family == Family.CONT
        assert result.rejected_candidates == []

    def test_empty_patterns_returns_none(self):
        """Test 2: empty list returns None winner."""
        d = PatternDispatcher()
        result = d.select_winner([], TrendState.BLUE)
        assert result.winner is None
        assert result.selection_path == "no_patterns"

    def test_yellow_raises_value_error(self):
        """Test 3: YELLOW trend state raises ValueError."""
        d = PatternDispatcher()
        p1 = _make_pattern("ZLR", r_t1=2.0)
        p2 = _make_pattern("VEGAS", r_t1=3.0, group="REVERSAL")
        with pytest.raises(ValueError, match="YELLOW"):
            d.select_winner([p1, p2], TrendState.YELLOW)


class TestWithinFamilySelection:
    """Tests 4-5: within-family max(r_t1)."""

    def test_cont_family_max_r_t1(self):
        """Test 4: within CONT, higher r_t1 wins."""
        d = PatternDispatcher()
        zlr = _make_pattern("ZLR", r_t1=1.0)
        tlb = _make_pattern("TLB", r_t1=3.0)
        gb100 = _make_pattern("GB100", r_t1=2.0)
        result = d.select_winner([zlr, tlb, gb100], TrendState.BLUE)
        assert result.winner.pattern_id == "TLB"
        assert result.selection_path == "within_family_max_r_t1"

    def test_rev_family_max_r_t1(self):
        """Test 5: within REV (only REV candidates), higher r_t1 wins."""
        d = PatternDispatcher()
        vegas = _make_pattern("VEGAS", r_t1=4.0, group="REVERSAL")
        ghost = _make_pattern("GHOST", r_t1=2.0, group="REVERSAL")
        # No CONT candidates, so BLUE falls back to cross-family
        result = d.select_winner([vegas, ghost], TrendState.BLUE)
        assert result.winner.pattern_id == "VEGAS"
        assert result.selection_path == "cross_family_trend_preferred"


class TestTrendFamilyPreference:
    """Tests 6-9: trend-state family preference."""

    def test_blue_prefers_cont_over_higher_r_t1_rev(self):
        """Test 6: BLUE prefers CONT even when REV has higher R_t1."""
        d = PatternDispatcher()
        zlr = _make_pattern("ZLR", r_t1=1.0)
        vegas = _make_pattern("VEGAS", r_t1=5.0, group="REVERSAL")
        result = d.select_winner([zlr, vegas], TrendState.BLUE)
        assert result.winner.pattern_id == "ZLR"
        assert result.selection_path == "within_family_max_r_t1"

    def test_red_prefers_cont_over_higher_r_t1_rev(self):
        """Test 7: RED prefers CONT even when REV has higher R_t1."""
        d = PatternDispatcher()
        tt = _make_pattern("TT", r_t1=1.5)
        ghost = _make_pattern("GHOST", r_t1=6.0, group="REVERSAL")
        result = d.select_winner([tt, ghost], TrendState.RED)
        assert result.winner.pattern_id == "TT"
        assert result.selection_path == "within_family_max_r_t1"

    def test_gray_uses_max_r_t1_across_all(self):
        """Test 8: GRAY uses max R_t1 across all families."""
        d = PatternDispatcher()
        zlr = _make_pattern("ZLR", r_t1=1.0)
        vegas = _make_pattern("VEGAS", r_t1=5.0, group="REVERSAL")
        result = d.select_winner([zlr, vegas], TrendState.GRAY)
        assert result.winner.pattern_id == "VEGAS"
        assert result.selection_path == "gray_fallback_max_r_t1"

    def test_no_cont_in_blue_falls_back_cross_family(self):
        """Test 9: BLUE with no CONT patterns falls back to max R_t1 across all."""
        d = PatternDispatcher()
        vegas = _make_pattern("VEGAS", r_t1=3.0, group="REVERSAL")
        famir = _make_pattern("FAMIR", r_t1=2.0, group="REVERSAL")
        result = d.select_winner([vegas, famir], TrendState.BLUE)
        assert result.winner.pattern_id == "VEGAS"
        assert result.selection_path == "cross_family_trend_preferred"


class TestFamilyMapping:
    """Test 10-11: family mapping edge cases."""

    def test_htlb_groups_with_rev(self):
        """Test 10: HTLB is classified as REV, not CONT."""
        assert FAMILY_MAP[PatternId.HTLB] == Family.REV
        d = PatternDispatcher()
        # HTLB should NOT be picked by CONT preference in BLUE
        zlr = _make_pattern("ZLR", r_t1=1.0)
        htlb = _make_pattern("HTLB", r_t1=5.0, group="REVERSAL")
        result = d.select_winner([zlr, htlb], TrendState.BLUE)
        # BLUE prefers CONT → ZLR wins despite lower R_t1
        assert result.winner.pattern_id == "ZLR"

    def test_r_t1_missing_fallback(self):
        """Test 11: missing r_t1 falls back to max(confidence)."""
        d = PatternDispatcher()
        zlr = _make_pattern("ZLR", confidence=0.8, r_t1=None)
        vegas = _make_pattern("VEGAS", confidence=0.6, r_t1=None, group="REVERSAL")
        result = d.select_winner([zlr, vegas], TrendState.BLUE)
        assert result.winner.pattern_id == "ZLR"
        assert result.selection_path == "r_t1_missing_fallback"


class TestTieBreaker:
    """Test 12: tie-breaking on confidence."""

    def test_same_r_t1_higher_confidence_wins(self):
        """Test 12: same r_t1, different confidence -> higher confidence wins."""
        d = PatternDispatcher()
        zlr = _make_pattern("ZLR", r_t1=2.0, confidence=0.9)
        tlb = _make_pattern("TLB", r_t1=2.0, confidence=0.7)
        result = d.select_winner([zlr, tlb], TrendState.BLUE)
        assert result.winner.pattern_id == "ZLR"


class TestYAMLConfig:
    """Tests 13-15: YAML config handling."""

    def test_yaml_missing_uses_defaults_warns(self, caplog):
        """Test 13: missing YAML file uses defaults with warning."""
        with caplog.at_level(logging.WARNING, logger="woodies.pattern_dispatcher"):
            d = PatternDispatcher(config_yaml_path="/nonexistent/path.yaml")
        assert d.config_source == "python_default"
        assert "not found" in caplog.text

    def test_yaml_valid_overrides_defaults(self):
        """Test 14: valid YAML overrides defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                "pattern_dispatcher:\n"
                "  min_r_t1_threshold: 0.5\n"
                "  log_dispatch_decisions: true\n"
            )
            f.flush()
            try:
                d = PatternDispatcher(config_yaml_path=f.name)
                assert d.config_source == "yaml_override"
                assert d.config["min_r_t1_threshold"] == 0.5
                assert d.config["log_dispatch_decisions"] is True
                # Non-overridden defaults still present
                assert d.config["tie_breaker"] == "raw_confidence"
            finally:
                os.unlink(f.name)

    def test_yaml_invalid_uses_defaults_warns(self, caplog):
        """Test 15: invalid YAML uses defaults with warning."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("not: a: valid: yaml: [[[")
            f.flush()
            try:
                with caplog.at_level(logging.WARNING, logger="woodies.pattern_dispatcher"):
                    d = PatternDispatcher(config_yaml_path=f.name)
                assert d.config_source == "python_default"
            finally:
                os.unlink(f.name)


class TestWoodiesSystemIntegration:
    """Test 16: verify PatternDispatcher is wired into woodies_system."""

    def test_pattern_dispatcher_imported_and_instantiated(self):
        """Test 16: woodies_system imports and uses PatternDispatcher."""
        import backend.v9.systems.woodies.woodies_system as ws
        assert hasattr(ws, '_pattern_dispatcher')
        assert isinstance(ws._pattern_dispatcher, PatternDispatcher)


class TestRawConfidenceIntact:
    """Test 17: verify raw_confidence field still exists on PatternResult (W-6)."""

    def test_raw_confidence_field_exists(self):
        """Test 17: PatternResult has raw_confidence field."""
        p = _make_pattern("ZLR", confidence=0.75, raw_confidence=0.75)
        assert p.raw_confidence == 0.75

    def test_raw_confidence_in_dispatch_winner(self):
        """Ensure dispatcher winner retains raw_confidence."""
        d = PatternDispatcher()
        p = _make_pattern("ZLR", confidence=0.8, raw_confidence=0.8, r_t1=2.0)
        result = d.select_winner([p], TrendState.BLUE)
        assert result.winner.raw_confidence == 0.8


class TestNonDetectedFiltered:
    """Extra: non-detected patterns should be filtered out."""

    def test_non_detected_ignored(self):
        """Non-detected patterns are excluded from dispatch."""
        d = PatternDispatcher()
        p1 = _make_pattern("ZLR", r_t1=2.0, detected=True)
        p2 = _make_pattern("VEGAS", r_t1=5.0, detected=False, group="REVERSAL")
        result = d.select_winner([p1, p2], TrendState.GRAY)
        assert result.winner.pattern_id == "ZLR"
        assert result.selection_path == "single_pattern"

    def test_all_non_detected_returns_none(self):
        """All non-detected patterns -> no_patterns."""
        d = PatternDispatcher()
        p1 = _make_pattern("ZLR", detected=False)
        result = d.select_winner([p1], TrendState.BLUE)
        assert result.winner is None
        assert result.selection_path == "no_patterns"
