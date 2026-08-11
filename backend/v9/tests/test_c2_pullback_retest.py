"""C2 — RE_PULLBACK_ENTRY_V1 tests (2026-08-11).

Tests the pullback-retest pattern detector: after IB breaks, price extends,
pulls back to the broken edge, and a rejection bar closes with the break.
"""
import pytest

from backend.v9.systems.five_min.patterns.pullback_retest import (
    detect_pullback_retest,
    IB_BREAK_MIN_FRAC,
    RETEST_TOL_PT,
    TICK_SIZE,
)


def _bar(o, h, l, c, ts=0):
    return {"o": o, "h": h, "l": l, "c": c, "ts": ts}


# ── LONG retest ────────────────────────────────────────────────────────────

class TestLongRetest:
    """IB-high broken upward → pullback to ib_high → rejection bar → LONG."""

    def test_basic_long_retest(self):
        """Classic: IB breaks up, extends, pulls back, rejection bar."""
        ib_h, ib_l = 7790.0, 7770.0  # ib_width=20
        # Bar 0-2: break above IB-high
        bars = [
            _bar(7788, 7795, 7786, 7794),   # breaks ib_high by 5pt (>0.15*20=3)
            _bar(7794, 7800, 7792, 7799),   # extends further
            _bar(7799, 7805, 7797, 7803),   # more extension
            _bar(7803, 7804, 7795, 7796),   # starts pulling back
            # Rejection bar: low touches ib_high area, closes above it bullishly
            _bar(7793, 7797, 7789, 7796),   # low=7789 near ib_h=7790, close=7796>7790, bullish
        ]
        d, conf, info = detect_pullback_retest(
            bars, ib_high=ib_h, ib_low=ib_l, ib_locked=True, session_min=90)
        assert d == "LONG"
        assert conf > 0.5
        assert info["kind"] == "RE_PULLBACK"
        assert info["pattern_name"] == "RE_PULLBACK_LONG"
        assert info["ib_high"] == ib_h

    def test_no_break_no_pattern(self):
        """No IB break → no pattern."""
        ib_h, ib_l = 7790.0, 7770.0
        bars = [
            _bar(7780, 7785, 7778, 7783),
            _bar(7783, 7788, 7780, 7786),
            _bar(7786, 7789, 7784, 7787),
            _bar(7787, 7788, 7785, 7786),
            _bar(7786, 7789, 7784, 7788),
        ]
        d, _, _ = detect_pullback_retest(
            bars, ib_high=ib_h, ib_low=ib_l, ib_locked=True, session_min=90)
        assert d is None

    def test_no_pullback_no_pattern(self):
        """IB breaks but no pullback → no pattern."""
        ib_h, ib_l = 7790.0, 7770.0
        bars = [
            _bar(7788, 7795, 7786, 7794),
            _bar(7794, 7800, 7792, 7799),
            _bar(7799, 7810, 7798, 7808),
            _bar(7808, 7815, 7806, 7813),
            _bar(7813, 7820, 7811, 7818),  # no pullback to 7790
        ]
        d, _, _ = detect_pullback_retest(
            bars, ib_high=ib_h, ib_low=ib_l, ib_locked=True, session_min=90)
        assert d is None

    def test_failed_retest_no_pattern(self):
        """Pullback to edge but close below (failed retest) → no pattern."""
        ib_h, ib_l = 7790.0, 7770.0
        bars = [
            _bar(7788, 7795, 7786, 7794),
            _bar(7794, 7800, 7792, 7799),
            _bar(7799, 7803, 7795, 7796),
            _bar(7796, 7797, 7788, 7789),
            # Close BELOW ib_high — failed retest
            _bar(7789, 7791, 7785, 7788),
        ]
        d, _, _ = detect_pullback_retest(
            bars, ib_high=ib_h, ib_low=ib_l, ib_locked=True, session_min=90)
        assert d is None


# ── SHORT retest ───────────────────────────────────────────────────────────

class TestShortRetest:
    """IB-low broken downward → pullback to ib_low → rejection bar → SHORT."""

    def test_basic_short_retest(self):
        """Classic: IB breaks down, extends, pulls back, rejection bar."""
        ib_h, ib_l = 7790.0, 7770.0
        bars = [
            _bar(7772, 7773, 7765, 7766),   # breaks ib_low by 5pt
            _bar(7766, 7768, 7760, 7761),   # extends
            _bar(7761, 7763, 7755, 7757),   # more extension
            _bar(7757, 7765, 7756, 7764),   # pulls back toward ib_low
            # Rejection: high near ib_low, close below, bearish (open > close)
            _bar(7769, 7771, 7763, 7765),   # open=7769, high=7771 near ib_l=7770, close=7765<7770
        ]
        d, conf, info = detect_pullback_retest(
            bars, ib_high=ib_h, ib_low=ib_l, ib_locked=True, session_min=90)
        assert d == "SHORT"
        assert conf > 0.5
        assert info["kind"] == "RE_PULLBACK"
        assert info["pattern_name"] == "RE_PULLBACK_SHORT"


# ── Gate checks ────────────────────────────────────────────────────────────

class TestGates:
    """Verify the pattern respects its gates."""

    def test_ib_not_locked_no_pattern(self):
        """Before IB lock → no pattern."""
        bars = [_bar(7780, 7795, 7778, 7794)] * 5
        d, _, _ = detect_pullback_retest(
            bars, ib_high=7790, ib_low=7770, ib_locked=False, session_min=90)
        assert d is None

    def test_before_period_c_no_pattern(self):
        """session_min < 60 (before period C) → no pattern."""
        bars = [_bar(7780, 7795, 7778, 7794)] * 5
        d, _, _ = detect_pullback_retest(
            bars, ib_high=7790, ib_low=7770, ib_locked=True, session_min=30)
        assert d is None

    def test_missing_ib_no_pattern(self):
        """Missing IB data → no pattern."""
        bars = [_bar(7780, 7795, 7778, 7794)] * 5
        d, _, _ = detect_pullback_retest(
            bars, ib_high=None, ib_low=7770, ib_locked=True, session_min=90)
        assert d is None

    def test_too_few_bars_no_pattern(self):
        """< 5 bars → no pattern."""
        bars = [_bar(7780, 7795, 7778, 7794)] * 3
        d, _, _ = detect_pullback_retest(
            bars, ib_high=7790, ib_low=7770, ib_locked=True, session_min=90)
        assert d is None


# ── Target verification ───────────────────────────────────────────────────

class TestTargets:
    """Verify targets are structurally correct."""

    def test_long_targets_above_ib(self):
        """LONG targets: edge + 0.5/1.0/2.0 × ib_width."""
        ib_h, ib_l = 7790.0, 7770.0  # width=20
        bars = [
            _bar(7788, 7795, 7786, 7794),
            _bar(7794, 7800, 7792, 7799),
            _bar(7799, 7805, 7797, 7803),
            _bar(7803, 7804, 7795, 7796),
            _bar(7793, 7797, 7789, 7796),
        ]
        d, _, info = detect_pullback_retest(
            bars, ib_high=ib_h, ib_low=ib_l, ib_locked=True, session_min=90)
        if d == "LONG":
            assert info["t1"] == 7800.0  # 7790 + 0.5*20
            assert info["t2"] == 7810.0  # 7790 + 1.0*20
            assert info["t3"] == 7830.0  # 7790 + 2.0*20

    def test_long_stop_below_retest(self):
        """LONG stop: below the retest low + buffer."""
        ib_h, ib_l = 7790.0, 7770.0
        bars = [
            _bar(7788, 7795, 7786, 7794),
            _bar(7794, 7800, 7792, 7799),
            _bar(7799, 7805, 7797, 7803),
            _bar(7803, 7804, 7795, 7796),
            _bar(7793, 7797, 7789, 7796),
        ]
        d, _, info = detect_pullback_retest(
            bars, ib_high=ib_h, ib_low=ib_l, ib_locked=True, session_min=90)
        if d == "LONG":
            assert info["stop"] < info["retest_low"]


# ── Code path in five_min_system ──────────────────────────────────────────

class TestWiring:
    def test_flag_exists_in_five_min(self):
        """RE_PULLBACK_ENTRY_V1 must appear in five_min_system."""
        import inspect
        from backend.v9.systems.five_min import five_min_system
        src = inspect.getsource(five_min_system.FiveMinSystem.process_bar)
        assert "RE_PULLBACK_ENTRY_V1" in src
        assert "detect_pullback_retest" in src

    def test_pattern_name_in_schema(self):
        """RE_PULLBACK_LONG/SHORT must be valid PatternName."""
        from backend.v9.systems.five_min.output_schema import PatternName
        # Literal type — check the args
        assert "RE_PULLBACK_LONG" in PatternName.__args__
        assert "RE_PULLBACK_SHORT" in PatternName.__args__
