"""V1 gap tests for System 3 (tick_reversal / footprint).

Each test asserts a specific spec requirement that is NOT met in code.
Failures are EXPECTED — they prove drift.
"""
import pytest
from backend.v9.systems.tick_reversal.detector import TickReversalDetector
from backend.v9.systems.tick_reversal.schemas import (
    TickReversalConfig, BarInput, BarAnalysis,
)


# ── GAP: EOD Analysis Hook (Output 3) ─────────────────────────

class TestEODAnalysisHook:
    """Spec Section 9: End-of-day analysis must be a separate module.
    Provides: setup count, hypothetical performance, per-pattern win rate.
    """

    def test_eod_analysis_module_exists(self):
        """Spec: tick_reversal must have an EOD analysis module."""
        try:
            from backend.v9.systems.tick_reversal import eod_analysis
            assert hasattr(eod_analysis, "compute_eod_report"), (
                "eod_analysis module must have compute_eod_report function"
            )
        except ImportError:
            pytest.fail(
                "Spec Section 9: tick_reversal must have eod_analysis module. "
                "Not found at backend.v9.systems.tick_reversal.eod_analysis"
            )


# ── GAP: 12-tick secondary bar support ─────────────────────────

class TestDualBarSizeSupport:
    """Spec Section 3 Input #2: 12-tick reversal bars (backup).
    Code only processes one bar size at a time.
    """

    def test_detector_accepts_12_tick_bars(self):
        """Spec: detector should process both 15-tick and 12-tick bars."""
        config = TickReversalConfig(tick_reversal_size=12)
        detector = TickReversalDetector(config=config)
        bar = BarInput(
            ts="1715270400", o=5246.5, h=5248.25, l=5246.0, c=5247.75,
            vol=1840, tick_size=12,
        )
        result = detector.process_bar(bar)
        assert result.tick_reversal_size == 12, (
            f"12-tick bar should be processed with tick_reversal_size=12, "
            f"got {result.tick_reversal_size}"
        )

    def test_dual_detector_for_both_sizes(self):
        """Spec: System 3 must monitor BOTH 15-tick and 12-tick simultaneously."""
        # The system should have a way to run dual detectors
        assert hasattr(TickReversalDetector, "process_dual_bars") or \
               hasattr(TickReversalDetector, "dual_mode"), (
            "Spec: System 3 must process both 15-tick primary AND "
            "12-tick secondary bars simultaneously. "
            "No dual-mode capability found."
        )


# ── GAP: OTF Clarity from tail+absorption analysis ────────────

class TestOTFClarityFromSpec:
    """Spec Section 7 — OTF Clarity 4 states from Zohar:
    State 1: both sides clear
    State 2: sellers clear -> LONG only
    State 3: buyers clear -> SHORT only
    State 4: unclear -> NO setup

    Code uses simplified 3-bar up/down count instead of
    tail + responsive activity + absorption analysis.
    """

    def test_otf_uses_tail_analysis(self):
        """Spec: OTF clarity should use buying/selling tail analysis."""
        detector = TickReversalDetector()
        # Create bars with specific footprint data showing clear buying tail
        bars = []
        for i in range(6):
            bar = BarInput(
                ts=str(i), o=5246.5 + i * 0.5, h=5248.0 + i * 0.5,
                l=5246.0 + i * 0.5, c=5247.5 + i * 0.5,
                vol=1000, ask_vol=700, bid_vol=300,
                tick_size=15,
            )
            bars.append(bar)

        # Process all bars
        for bar in bars:
            result = detector.process_bar(bar)

        # OTF should consider tail+responsive+absorption, not just bar direction
        # State 3 (buyers clear) requires tail analysis per Zohar
        assert result.context.otf_state in (1, 2, 3), (
            f"With 6 consecutive up bars and 70% ask volume, "
            f"OTF should be State 3 (buyers clear). Got state {result.context.otf_state}. "
            f"Implementation likely uses simplified bar-direction counting."
        )


# ── GAP: Confluence penalty for delta divergence ──────────────

class TestConfluenceDeltaDivergencePenalty:
    """Spec Section 6 Step 7: Delta divergence = -1 penalty.
    Also: Initiative + exhaustion = -1 penalty.
    These are listed as separate items in the spec.
    """

    def test_delta_divergence_penalty_separate(self):
        """Spec: delta divergence penalty is separate from exhaustion penalty."""
        detector = TickReversalDetector()
        bar = BarInput(
            ts="1", o=5250, h=5255, l=5245, c=5252,
            vol=2000, ask_vol=600, bid_vol=1400,
            delta=-800,  # negative delta = bearish
            tick_size=15,
        )
        result = detector.process_bar(bar)
        confluence = result.confluence

        # Verify penalties are tracked separately
        assert hasattr(confluence, "delta_divergence_penalty"), (
            "Spec: ConfluenceResult should track delta_divergence_penalty "
            "separately from exhaustion penalty. "
            f"Current fields: {list(confluence.model_fields.keys())}"
        )
