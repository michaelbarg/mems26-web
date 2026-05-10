"""V1 gap tests for System 2 (chart_5min).

Each test asserts a specific spec requirement that is NOT met in code.
Failures are EXPECTED — they prove drift.
"""
import pytest
from backend.v9.systems.chart_5min.detector import Chart5MinDetector
from backend.v9.systems.chart_5min.matrix import (
    classify_opportunity, lookup_matrix, TradeManagement,
)
from backend.v9.systems.chart_5min.schemas import (
    ConfluenceBreakdown, ChopScore,
)


# ── GAP: First Hour confluence capped at MAX 4 ─────────────────

class TestFirstHourConfluenceMax4:
    """V3.3 Q6: Confluence Count MAX 4 in first hour.
    Code does not enforce this cap.
    """

    def test_first_hour_confluence_capped_at_4(self):
        """Spec: In first hour, confluence score must not exceed 4."""
        confluence = ConfluenceBreakdown(
            base=1,
            day_type_aligned=1,
            killzone_high=1,
            reference_lines=1,
            woodies_cci=1,
            tier_34_confirms=2,
            chop_penalty=0,
            total=7,
        )
        # In first hour, total should be capped at 4
        is_first_hour = True
        if is_first_hour:
            capped_total = min(confluence.total, 4)
        else:
            capped_total = confluence.total
        assert confluence.total <= 4, (
            f"V3.3: First hour confluence MAX 4, but total={confluence.total}. "
            f"ConfluenceBreakdown should enforce cap when is_first_hour=True."
        )


# ── GAP: No STRATEGIC classification in first hour ─────────────

class TestFirstHourNoStrategic:
    """V3.3: First hour = never STRATEGIC. Code should return TACTICAL_PLUS max."""

    def test_first_hour_high_confluence_not_strategic(self):
        """Spec: Even with confluence=6, first hour must not return STRATEGIC."""
        result = classify_opportunity(6, is_first_hour=True)
        assert result != "STRATEGIC", (
            f"V3.3: First hour must NEVER return STRATEGIC, got {result}"
        )

    def test_first_hour_returns_tactical_plus_max(self):
        """Spec: Best classification in first hour is TACTICAL_PLUS."""
        result = classify_opportunity(10, is_first_hour=True)
        assert result == "TACTICAL_PLUS", (
            f"V3.3: Max first-hour classification is TACTICAL_PLUS, got {result}"
        )


# ── GAP: Nontrend day blocks strategic trades entirely ─────────

class TestNontrendBlocksStrategic:
    """V3.0 Section 3: NONTREND DAY — Strategic trades: NO TRADES.
    Code returns TradeManagement with t1=3_5_ticks for unknown patterns.
    """

    def test_nontrend_strategic_pattern_blocked(self):
        """Spec: On Nontrend day, head_shoulders pattern must be BLOCKED."""
        mgmt = lookup_matrix(
            day_type="NONTREND",
            pattern_id="head_shoulders",
            direction="LONG",
        )
        assert mgmt.blocked is True, (
            f"Spec: NONTREND day blocks strategic patterns. "
            f"head_shoulders should be blocked, got blocked={mgmt.blocked}, "
            f"t1={mgmt.t1_reason}"
        )


# ── GAP: Test phase (Step 8) not implemented ──────────────────

class TestPhaseValidation:
    """V3.0 Section 5 Step 8: Wait for test phase — pullback to key level,
    validate test. Not implemented in detector.
    """

    def test_detector_has_test_phase_method(self):
        """Spec: Chart5MinDetector must implement test phase validation."""
        detector = Chart5MinDetector()
        assert hasattr(detector, "_validate_test_phase") or \
               hasattr(detector, "validate_test_phase"), (
            "V3.0 Step 8: Detector must have test phase validation method. "
            "Currently only has _validate_structure (Q5)."
        )


# ── GAP: T-levels computed from actual structure ──────────────

class TestTLevelComputation:
    """V3.0 Section 4: T-levels are determined by market structure
    (POC, VWAP, pattern projection), not static strings.
    """

    def test_t1_has_price_value(self):
        """Spec: T1 output must include computed price, not just reason string."""
        mgmt = lookup_matrix(
            day_type="NORMAL",
            pattern_id="reactive_buyer",
            direction="LONG",
        )
        assert hasattr(mgmt, "t1_price") or hasattr(mgmt, "t1_level"), (
            f"Spec: TradeManagement must include t1_price computed from "
            f"POC/VWAP/pattern. Got only t1_reason='{mgmt.t1_reason}'"
        )


# ── GAP: Opening Choppiness uses 3-6 bar window ──────────────

class TestOpeningChoppinessWindow:
    """V3.3 Q4: Opening Choppiness indicator uses 3-6 bars.
    Code uses 15-bar micro window for chop calculation.
    """

    def test_chop_score_has_opening_field(self):
        """Spec: ChopScore should have an 'opening' field for 3-6 bar window."""
        score = ChopScore()
        assert hasattr(score, "opening"), (
            "V3.3: ChopScore must include 'opening' field for "
            "3-6 bar choppiness indicator. "
            f"Current fields: micro, session, macro, composite"
        )


# ── GAP: Pattern bar count enforcement ─────────────────────────

class TestPatternBarCountEnforcement:
    """V3.0 Section 2: Each pattern has min/max bar count.
    Double Bottom = 8-15 bars, H&S = 15-25 bars, etc.
    """

    def test_double_bottom_min_bars(self):
        """Spec: Double Bottom requires minimum 8 bars."""
        from backend.v9.systems.chart_5min.models import ALL_TIERS
        # Find double_bottom in tier patterns
        for tier in ALL_TIERS:
            if "double_bottom" in tier.patterns:
                assert tier.buffer_size >= 8, (
                    f"Double Bottom requires min 8 bars, "
                    f"tier buffer_size={tier.buffer_size}"
                )
                break


# ── GAP: First hour pattern eligibility excludes large patterns ─

class TestFirstHourPatternExclusion:
    """V3.3: First hour must NOT detect Triangles, H&S, Cup&Handle, Wedges."""

    def test_head_shoulders_excluded_first_hour(self):
        """Spec: head_shoulders must not be in first hour eligibility."""
        from backend.v9.systems.chart_5min.models import FIRST_HOUR_ELIGIBILITY
        for bar_count, patterns in FIRST_HOUR_ELIGIBILITY.items():
            assert "head_shoulders" not in patterns, (
                f"V3.3: head_shoulders must NOT be eligible in first hour "
                f"(found at bar_count={bar_count})"
            )
            assert "inverse_head_shoulders" not in patterns, (
                f"V3.3: inverse_head_shoulders must NOT be eligible in first hour"
            )

    def test_cup_handle_excluded_first_hour(self):
        """Spec: cup_handle must not be in first hour eligibility."""
        from backend.v9.systems.chart_5min.models import FIRST_HOUR_ELIGIBILITY
        for bar_count, patterns in FIRST_HOUR_ELIGIBILITY.items():
            assert "cup_handle" not in patterns, (
                f"V3.3: cup_handle must NOT be eligible in first hour"
            )

    def test_ascending_triangle_excluded_first_hour(self):
        """Spec: ascending_triangle must not be in first hour eligibility."""
        from backend.v9.systems.chart_5min.models import FIRST_HOUR_ELIGIBILITY
        for bar_count, patterns in FIRST_HOUR_ELIGIBILITY.items():
            assert "ascending_triangle" not in patterns, (
                f"V3.3: ascending_triangle must NOT be eligible in first hour"
            )
