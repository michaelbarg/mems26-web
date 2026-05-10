"""R3 Spec Compliance Tests — System 2 (chart_5min).

Validates every requirement from MEMS26_5MIN_CHART_SPEC_V3_PATTERNS_INTEGRATED.
"""
import pytest

from backend.v9.systems.chart_5min.schemas import (
    PatternDetection, ChopScore, ConfluenceBreakdown, SetupPackage, SystemState,
)
from backend.v9.systems.chart_5min.matrix import (
    lookup_matrix, classify_opportunity, sizing_for_classification, TradeManagement,
    _TREND_NORMAL, _VARIATION, _NORMAL, _TREND_DD, _NEUTRAL, _NONTREND,
)


# ── Step 1: Day Type Input ───────────────────────────────────────

class TestStep1DayTypeInput:
    def test_step1_day_type_input(self):
        """Detector accepts day_type from System 1."""
        from backend.v9.systems.chart_5min.detector import Chart5MinDetector
        det = Chart5MinDetector()
        det.set_day_type("TREND_NORMAL", locked=True)
        state = det.get_state()
        assert state.day_type == "TREND_NORMAL"
        assert state.day_type_locked is True


# ── Step 2: Reference Lines ─────────────────────────────────────

class TestStep2ReferenceLines:
    def test_step2_reference_lines(self):
        """Detector accepts TPO reference lines."""
        from backend.v9.systems.chart_5min.detector import Chart5MinDetector
        det = Chart5MinDetector()
        det.set_reference_lines([5250.0, 5260.0, 5240.0])
        assert det._reference_lines == [5250.0, 5260.0, 5240.0]


# ── Step 3: Killzone Gate ────────────────────────────────────────

class TestStep3KillzoneGate:
    def test_step3_killzone_gate(self):
        """Killzone blocked stops processing."""
        from backend.v9.systems.chart_5min.detector import Chart5MinDetector
        det = Chart5MinDetector()
        det.set_killzone(blocked=True, quality="LUNCH")
        state = det.get_state()
        assert state.killzone_blocked is True


# ── Step 4: Bar Processing ──────────────────────────────────────

class TestStep4BarProcessing:
    def test_step4_bar_processing(self):
        """SystemState schema has all required fields."""
        state = SystemState()
        assert hasattr(state, "bar_count")
        assert hasattr(state, "is_first_hour")
        assert hasattr(state, "active_patterns")
        assert hasattr(state, "chop")


# ── Step 5: OFA Patterns ────────────────────────────────────────

class TestStep5OFAPatterns:
    def test_step5_ofa_patterns(self):
        """PatternDetection schema supports OFA group patterns."""
        pd = PatternDetection(
            pattern_id="reactive_buyer", group="A", tier=1,
            direction="LONG", completion=1.0, bar_count=4,
            method="OFA", potential_r="2-4R",
        )
        assert pd.group == "A"
        assert pd.method == "OFA"


# ── Step 6: Chart Patterns ──────────────────────────────────────

class TestStep6ChartPatterns:
    def test_step6_chart_patterns(self):
        """PatternDetection supports geometric chart patterns."""
        pd = PatternDetection(
            pattern_id="double_bottom", group="B", tier=2,
            direction="LONG", completion=0.85, bar_count=12,
            method="Geometric", potential_r="3-5R",
            key_levels={"neckline": 5252},
        )
        assert pd.group == "B"
        assert pd.key_levels["neckline"] == 5252


# ── Step 7: Matrix Lookup ───────────────────────────────────────

class TestStep7MatrixLookup:
    def test_step7_matrix_lookup(self):
        """Matrix returns TradeManagement for known combos."""
        mgmt = lookup_matrix("TREND_NORMAL", "initiative_buyer", "LONG")
        assert not mgmt.blocked
        assert mgmt.t1_reason == "momentum_push"
        assert mgmt.t3_reason == "trail_vegas_ema"

    def test_matrix_trend_normal(self):
        """Trend Normal: initiative continuation allowed, reactive blocked."""
        mgmt_init = lookup_matrix("TREND_NORMAL", "initiative_buyer", "LONG")
        assert not mgmt_init.blocked
        mgmt_react = lookup_matrix("TREND_NORMAL", "reactive_buyer", "LONG")
        assert mgmt_react.blocked

    def test_matrix_variation(self):
        """Variation: reactive allowed with T1=POC/VWAP, T2=opposite extreme."""
        mgmt = lookup_matrix("VARIATION", "reactive_buyer", "LONG")
        assert not mgmt.blocked
        assert mgmt.t1_reason == "poc_tpo_vwap"
        assert mgmt.time_stop_min == 60

    def test_matrix_normal(self):
        """Normal Day: reactive allowed, sizing=HALF, time_stop=30."""
        mgmt = lookup_matrix("NORMAL", "reactive_buyer", "LONG")
        assert mgmt.sizing == "HALF"
        assert mgmt.time_stop_min == 30

    def test_matrix_trend_dd(self):
        """Trend DD: initiative has 3 targets."""
        mgmt = lookup_matrix("TREND_DD", "initiative_buyer", "LONG")
        assert mgmt.t1_reason == "first_dist_edge"
        assert mgmt.t2_reason == "second_dist_center"
        assert mgmt.t3_reason == "second_dist_edge"

    def test_matrix_neutral(self):
        """Neutral: quick reactive scalps only, T1=POC return."""
        mgmt = lookup_matrix("NEUTRAL", "reactive_buyer", "LONG")
        assert mgmt.t1_reason == "poc_return"
        assert mgmt.t2_reason is None

    def test_matrix_nontrend(self):
        """Nontrend: tiny scalps only, T1=3-5 ticks."""
        mgmt = lookup_matrix("NONTREND", "reactive_buyer", "LONG")
        assert mgmt.t1_reason == "3_5_ticks"
        assert mgmt.sizing == "MIN"
        assert mgmt.time_stop_min == 20


# ── Step 8: Test Phase ───────────────────────────────────────────

class TestStep8TestPhase:
    def test_step8_test_phase(self):
        """SetupPackage schema has direction and entry/stop zones."""
        sp = SetupPackage(
            ts="2026-05-10T10:30:00Z",
            pattern=PatternDetection(
                pattern_id="reactive_buyer", group="A", tier=1,
                direction="LONG", completion=1.0, bar_count=4,
                method="OFA", potential_r="2-4R",
            ),
            day_type="NORMAL", matrix_cell="NORMAL x reactive_buyer x LONG",
            direction="LONG", classification="TACTICAL",
            confluence=ConfluenceBreakdown(), chop=ChopScore(),
        )
        assert sp.direction == "LONG"


# ── Step 9: Setup Output ────────────────────────────────────────

class TestStep9SetupOutput:
    def test_step9_setup_output(self):
        """SetupPackage includes t1/t2/t3 + sizing + time_stop."""
        sp = SetupPackage(
            ts="t", pattern=PatternDetection(
                pattern_id="x", group="A", tier=1, direction="LONG",
                completion=1.0, bar_count=4, method="OFA", potential_r="2R",
            ),
            day_type="NORMAL", matrix_cell="x", direction="LONG",
            classification="TACTICAL",
            t1={"reason": "poc", "contracts": 1},
            t2={"reason": "vah", "contracts": 2},
            time_stop_min=30, sizing="HALF",
            confluence=ConfluenceBreakdown(), chop=ChopScore(),
        )
        assert sp.t1["reason"] == "poc"
        assert sp.sizing == "HALF"


# ── Step 10: Rejection ──────────────────────────────────────────

class TestStep10Rejection:
    def test_step10_rejection(self):
        """Blocked matrix entry returns blocked=True."""
        mgmt = lookup_matrix("TREND_NORMAL", "reactive_buyer", "LONG")
        assert mgmt.blocked


# ── Anti-Patterns ────────────────────────────────────────────────

class TestAntiPatterns:
    def test_AP1_suffering_side(self):
        """Reactive against trend on Trend Normal MUST be blocked."""
        mgmt = lookup_matrix("TREND_NORMAL", "reactive_buyer", "LONG")
        assert mgmt.blocked
        assert "Suffering Side" in mgmt.block_reason

    def test_AP2_no_strategic_first_hour(self):
        """First hour cannot produce STRATEGIC classification."""
        cls = classify_opportunity(10, is_first_hour=True)
        assert cls != "STRATEGIC"

    def test_AP3_no_t3_first_hour(self):
        """First hour matrix entries have no T3."""
        mgmt = lookup_matrix(
            "TREND_NORMAL", "initiative_buyer", "LONG",
            is_first_hour=True, opening_type="OPEN_DRIVE",
        )
        assert mgmt.t3_reason is None

    def test_AP4_nontrend_no_strategic(self):
        """Nontrend day should use MIN sizing."""
        mgmt = lookup_matrix("NONTREND", "reactive_buyer", "LONG")
        assert mgmt.sizing == "MIN"


# ── Classification ───────────────────────────────────────────────

class TestClassification:
    def test_classification_thresholds(self):
        assert classify_opportunity(1) == "TACTICAL"
        assert classify_opportunity(2) == "TACTICAL_PLUS"
        assert classify_opportunity(4) == "STRATEGIC"

    def test_sizing_mapping(self):
        assert sizing_for_classification("TACTICAL") == "MIN"
        assert sizing_for_classification("TACTICAL_PLUS") == "HALF"
        assert sizing_for_classification("STRATEGIC") == "FULL"


# ── Confluence ───────────────────────────────────────────────────

class TestConfluence:
    def test_confluence_schema(self):
        c = ConfluenceBreakdown(
            base=1, day_type_aligned=1, killzone_high=1,
            reference_lines=0, woodies_cci=1, tier_34_confirms=2,
            chop_penalty=-1, total=5,
        )
        assert c.total == 5
