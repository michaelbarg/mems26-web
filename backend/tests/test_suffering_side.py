"""Tests for Suffering Side Veto gate (D-049, D-065)."""

import os
import sys
from pathlib import Path

# Add backend to path so gates package imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from gates.suffering_side import check_suffering_side, NO_TRADE_ZONE_PT, GateResult


class TestSufferingSideVeto:
    """Test all decision branches per D-065 logic."""

    def test_long_clearly_above_poc_passes(self):
        """LONG well above POC should PASS."""
        result = check_suffering_side(
            direction="LONG", price=5740.00, day_poc=5730.00,
        )
        assert result.result == "PASS"
        assert result.reason == "clear_of_poc_zone"

    def test_short_clearly_below_poc_passes(self):
        """SHORT well below POC should PASS."""
        result = check_suffering_side(
            direction="SHORT", price=5720.00, day_poc=5730.00,
        )
        assert result.result == "PASS"
        assert result.reason == "clear_of_poc_zone"

    def test_long_below_poc_blocks(self):
        """LONG below POC = buyers suffer = BLOCK."""
        result = check_suffering_side(
            direction="LONG", price=5725.00, day_poc=5730.00,
        )
        assert result.result == "BLOCK"
        assert result.reason == "below_poc_buyers_suffer"

    def test_short_above_poc_blocks(self):
        """SHORT above POC = sellers suffer = BLOCK."""
        result = check_suffering_side(
            direction="SHORT", price=5735.00, day_poc=5730.00,
        )
        assert result.result == "BLOCK"
        assert result.reason == "above_poc_sellers_suffer"

    def test_inside_zone_long_blocks(self):
        """LONG inside ±2pt zone = BLOCK."""
        result = check_suffering_side(
            direction="LONG", price=5731.00, day_poc=5730.00,
        )
        assert result.result == "BLOCK"
        assert result.reason == "inside_no_trade_zone"

    def test_inside_zone_short_blocks(self):
        """SHORT inside ±2pt zone = BLOCK."""
        result = check_suffering_side(
            direction="SHORT", price=5729.00, day_poc=5730.00,
        )
        assert result.result == "BLOCK"
        assert result.reason == "inside_no_trade_zone"

    def test_exactly_2pt_above_blocks(self):
        """Exactly at zone edge (2pt) = BLOCK (inclusive)."""
        result = check_suffering_side(
            direction="LONG", price=5732.00, day_poc=5730.00,
        )
        assert result.result == "BLOCK"
        assert result.reason == "inside_no_trade_zone"

    def test_just_past_zone_passes(self):
        """LONG just past 2pt zone = PASS."""
        result = check_suffering_side(
            direction="LONG", price=5732.25, day_poc=5730.00,
        )
        assert result.result == "PASS"

    def test_missing_poc_fail_open(self):
        """Missing day_poc in fail-open mode = WARNING (passes)."""
        result = check_suffering_side(
            direction="LONG", price=5732.25, day_poc=None, mode="open",
        )
        assert result.result == "WARNING"
        assert result.reason == "day_poc_unavailable_fail_open"

    def test_missing_poc_fail_closed(self):
        """Missing day_poc in fail-closed mode = BLOCK."""
        result = check_suffering_side(
            direction="LONG", price=5732.25, day_poc=None, mode="closed",
        )
        assert result.result == "BLOCK"
        assert result.reason == "day_poc_unavailable_fail_closed"

    def test_invalid_direction_warning(self):
        """Invalid direction = WARNING."""
        result = check_suffering_side(
            direction="INVALID", price=5732.25, day_poc=5730.00,
        )
        assert result.result == "WARNING"
        assert result.reason == "invalid_direction"

    def test_lowercase_direction_normalized(self):
        """Lowercase direction should be normalized to upper."""
        result = check_suffering_side(
            direction="long", price=5740.00, day_poc=5730.00,
        )
        assert result.result == "PASS"

    def test_result_includes_source_attribution(self):
        """Every result must reference D-049, D-065 and Hebrew quote."""
        result = check_suffering_side(
            direction="LONG", price=5740.00, day_poc=5730.00,
        )
        assert "D-049" in result.source_decision
        assert "D-065" in result.source_decision
        assert "סובל" in result.source_quote

    def test_to_dict_returns_all_fields(self):
        """to_dict must include all GateResult fields."""
        result = check_suffering_side(
            direction="LONG", price=5740.00, day_poc=5730.00,
        )
        d = result.to_dict()
        assert "gate" in d
        assert "result" in d
        assert "reason" in d
        assert "details" in d
        assert "source_decision" in d
        assert "source_quote" in d
        assert "timestamp" in d

    def test_short_just_past_zone_below_passes(self):
        """SHORT just past 2pt zone below POC = PASS."""
        result = check_suffering_side(
            direction="SHORT", price=5727.75, day_poc=5730.00,
        )
        assert result.result == "PASS"

    def test_zero_poc_treated_as_missing(self):
        """day_poc of 0 should be treated as missing."""
        result = check_suffering_side(
            direction="LONG", price=5740.00, day_poc=0, mode="open",
        )
        assert result.result == "WARNING"
        assert "unavailable" in result.reason
