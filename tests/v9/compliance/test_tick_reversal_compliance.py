"""R3 Spec Compliance Tests — System 3 (tick_reversal / footprint).

Validates every requirement from MEMS26_FOOTPRINT_TICK_SPEC_V3_STANDALONE.
"""
import pytest

from backend.v9.systems.tick_reversal.schemas import (
    BarInput, BarAnalysis, TickReversalConfig,
    ClusterResult, EmptyZoneResult, ContextResult,
    ZoharSignals, IndustrySignals, ConfluenceResult, PatternResult,
)
from backend.v9.systems.tick_reversal.detector import TickReversalDetector


# ── Helpers ──────────────────────────────────────────────────────

def _bar(c=5250.0, o=5248.0, h=5252.0, l=5247.0, vol=500,
         ask_vol=300, bid_vol=200, delta=100, tick_size=15):
    return BarInput(
        ts="1000000", o=o, h=h, l=l, c=c, vol=vol,
        ask_vol=ask_vol, bid_vol=bid_vol, delta=delta,
        tick_size=tick_size,
    )


def _make_bars(n=5, base=5250.0):
    bars = []
    for i in range(n):
        bars.append(_bar(
            c=base + i * 0.5, o=base + i * 0.5 - 1,
            h=base + i * 0.5 + 1, l=base + i * 0.5 - 2,
        ))
    return bars


# ── Step 1: Buffer ───────────────────────────────────────────────

class TestStep1Buffer:
    def test_step1_buffer(self):
        det = TickReversalDetector()
        assert det.BUFFER_SIZE == 30
        for b in _make_bars(5):
            det.process_bar(b)
        assert len(det.bars) == 5

    def test_buffer_bounded(self):
        det = TickReversalDetector()
        for b in _make_bars(35):
            det.process_bar(b)
        assert len(det.bars) == 30


# ── Step 2: Cluster Detection ───────────────────────────────────

class TestStep2Cluster:
    def test_step2_cluster(self):
        det = TickReversalDetector()
        result = det.process_bar(_bar())
        assert isinstance(result.cluster, ClusterResult)
        assert hasattr(result.cluster, "detected")
        assert hasattr(result.cluster, "yellow_poc")


# ── Step 3: Empty Zone ──────────────────────────────────────────

class TestStep3EmptyZone:
    def test_step3_empty_zone(self):
        det = TickReversalDetector()
        result = det.process_bar(_bar(o=5252, c=5250, h=5254, l=5248))
        assert isinstance(result.empty_zone, EmptyZoneResult)
        assert hasattr(result.empty_zone, "detected")


# ── Step 4: Context Analysis ────────────────────────────────────

class TestStep4Context:
    def test_step4_context(self):
        det = TickReversalDetector()
        for b in _make_bars(8):
            result = det.process_bar(b)
        assert isinstance(result.context, ContextResult)
        assert hasattr(result.context, "accumulation_active")
        assert hasattr(result.context, "jumps_count")
        assert hasattr(result.context, "otf_state")

    def test_otf_states(self):
        """OTF clarity has 4 states: 1=BOTH, 2=SELLERS, 3=BUYERS, 4=UNCLEAR."""
        det = TickReversalDetector()
        for b in _make_bars(5):
            result = det.process_bar(b)
        assert result.context.otf_state in (1, 2, 3, 4)


# ── Step 5: Pattern Detection ───────────────────────────────────

class TestStep5Patterns:
    def test_step5_patterns(self):
        det = TickReversalDetector()
        result = det.process_bar(_bar())
        assert isinstance(result.pattern, PatternResult)
        assert hasattr(result.pattern, "detected")
        assert hasattr(result.pattern, "completion")


# ── Step 6: Signals ──────────────────────────────────────────────

class TestStep6Zohar:
    def test_step6_zohar(self):
        """All 5 Zohar signals present in output."""
        det = TickReversalDetector()
        result = det.process_bar(_bar())
        z = result.signals_zohar
        assert isinstance(z, ZoharSignals)
        assert hasattr(z, "belly_comparison")
        assert hasattr(z, "volume_drop_90")
        assert hasattr(z, "cot_above_amt")
        assert hasattr(z, "tick_breach_ok")
        assert hasattr(z, "poc_jumping")


class TestStep6Industry:
    def test_step6_industry(self):
        """All 5 industry signals present in output."""
        det = TickReversalDetector()
        result = det.process_bar(_bar())
        ind = result.signals_industry
        assert isinstance(ind, IndustrySignals)
        assert hasattr(ind, "imbalance_250")
        assert hasattr(ind, "stacked_imbalance")
        assert hasattr(ind, "cumulative_delta_aligned")
        assert hasattr(ind, "exhaustion")
        assert hasattr(ind, "liquidity_sweep")


# ── Step 7: Confluence ───────────────────────────────────────────

class TestStep7Confluence:
    def test_step7_confluence(self):
        det = TickReversalDetector()
        result = det.process_bar(_bar())
        c = result.confluence
        assert isinstance(c, ConfluenceResult)
        assert hasattr(c, "zohar_count")
        assert hasattr(c, "industry_count")
        assert hasattr(c, "boosters")
        assert hasattr(c, "total")

    def test_confluence_weights(self):
        """Stacked imbalance = +2, liquidity sweep = +2 per spec."""
        det = TickReversalDetector()
        # Test via the internal method
        zohar = ZoharSignals()
        industry = IndustrySignals(stacked_imbalance=True, liquidity_sweep=True)
        c = det._calc_confluence(zohar, industry)
        assert c.boosters == 4


# ── Step 8: Classification ──────────────────────────────────────

class TestStep8Classification:
    def test_step8_classification(self):
        det = TickReversalDetector()
        assert det._classify(3) == "NO_SETUP"
        assert det._classify(4) == "TACTICAL"
        assert det._classify(6) == "STRATEGIC"

    def test_classification_thresholds(self):
        cfg = TickReversalConfig()
        assert cfg.confluence_tactical_min == 4
        assert cfg.confluence_strategic_min == 6


# ── Step 9: Visual Markers ──────────────────────────────────────

class TestStep9Markers:
    def test_step9_markers(self):
        det = TickReversalDetector()
        result = det.process_bar(_bar())
        assert hasattr(result, "visual_marker_drawn")
        if result.classification == "NO_SETUP":
            assert result.visual_marker_drawn is False


# ── Step 10: Journal Logging ────────────────────────────────────

class TestStep10Logging:
    def test_step10_logging(self):
        """Every bar produces a BarAnalysis regardless of classification."""
        det = TickReversalDetector()
        result = det.process_bar(_bar())
        assert isinstance(result, BarAnalysis)
        assert result.bar_id is not None
        assert result.ts is not None


# ── Anti-Patterns ────────────────────────────────────────────────

class TestAntiPatterns:
    def test_AP1_no_trade_execution(self):
        """Detector class has no execute/order/trade methods."""
        det = TickReversalDetector()
        assert not hasattr(det, "execute_trade")
        assert not hasattr(det, "place_order")
        assert not hasattr(det, "send_order")

    def test_AP2_no_external_input(self):
        """Detector __init__ takes no system dependencies."""
        det = TickReversalDetector()
        assert not hasattr(det, "day_type")
        assert not hasattr(det, "killzone")

    def test_AP3_log_every_bar(self):
        """Every call to process_bar returns a BarAnalysis."""
        det = TickReversalDetector()
        for b in _make_bars(10):
            result = det.process_bar(b)
            assert isinstance(result, BarAnalysis)

    def test_AP4_no_orders(self):
        """No order-related attributes in detector."""
        det = TickReversalDetector()
        assert not hasattr(det, "order")
        assert not hasattr(det, "bracket")

    def test_AP5_no_killzone_gate(self):
        """No killzone reference in detector."""
        det = TickReversalDetector()
        assert not hasattr(det, "_killzone")
        assert not hasattr(det, "killzone_blocked")


# ── Config Params (12 per spec Section 5) ────────────────────────

class TestConfigParams:
    def test_all_12_params(self):
        cfg = TickReversalConfig()
        assert cfg.tick_reversal_size == 15
        assert cfg.accumulation_min_bars == 5
        assert cfg.accumulation_range_ticks == 15
        assert cfg.jumps_required == 3
        assert cfg.cluster_poc_threshold_pct == 30
        assert cfg.empty_zone_threshold_pct == 5
        assert cfg.imbalance_ratio == 250
        assert cfg.stacked_imbalance_count == 3
        assert cfg.volume_drop_pct == 90
        assert cfg.belly_dominance_ratio == 1.5
        assert cfg.confluence_tactical_min == 4
        assert cfg.confluence_strategic_min == 6


# ── Output Schema ────────────────────────────────────────────────

class TestOutputSchema:
    def test_output_fields(self):
        """BarAnalysis has all fields from spec Section 8."""
        det = TickReversalDetector()
        result = det.process_bar(_bar())
        assert hasattr(result, "ts")
        assert hasattr(result, "bar_id")
        assert hasattr(result, "tick_reversal_size")
        assert hasattr(result, "bar")
        assert hasattr(result, "cluster")
        assert hasattr(result, "empty_zone")
        assert hasattr(result, "context")
        assert hasattr(result, "pattern")
        assert hasattr(result, "signals_zohar")
        assert hasattr(result, "signals_industry")
        assert hasattr(result, "confluence")
        assert hasattr(result, "classification")
        assert hasattr(result, "direction_inferred")
        assert hasattr(result, "would_be_entry_price")
        assert hasattr(result, "would_be_stop_price")
        assert hasattr(result, "stop_distance_ticks")
        assert hasattr(result, "visual_marker_drawn")
