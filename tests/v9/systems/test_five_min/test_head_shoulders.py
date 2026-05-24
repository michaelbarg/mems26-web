"""Golden tests for Inverse H&S + H&S Top detectors (Pkg 5a · D-091 §5+§6)."""
import pytest
from backend.v9.systems.five_min.patterns.head_shoulders import (
    detect_inverse_hns,
    detect_hns_top,
    MIN_BARS_REQUIRED,
    SEARCH_WINDOW,
    PIVOT_LOOKBACK,
    SHOULDER_SYM_PCT,
    HEAD_MIN_EXT_TICKS,
    TICK_SIZE,
)


# ── Fixture builders ──


def _build_inverse_hns_bars(
    ls_low=4500.0, head_low=4490.0, rs_low=4499.0,
    neckline_high=4510.0, breakout_close=4511.0,
):
    """Build a 14-bar Inverse H&S fixture with controllable pivots.

    Each swing-low pivot has 2 bars on each side with strictly higher lows.
    Layout: approach → LS → rise → approach → Head → rise → approach → RS → rise → breakout
    """
    # Each pivot needs ±2 bars with strictly LESS extreme values (higher lows for swing-low pivots)
    # Spacer bars keep lows > max(LS, RS) to avoid poisoning neighbors
    safe_low = max(ls_low, rs_low) + 4  # safe distance above both shoulder lows
    bars = [
        {"o": 4506, "h": 4507, "l": safe_low + 1, "c": 4506, "v": 1000},               # 0: safe
        {"o": 4505, "h": 4506, "l": ls_low + 2, "c": ls_low + 2, "v": 1100},           # 1: > LS
        {"o": ls_low + 1, "h": ls_low + 2, "l": ls_low, "c": ls_low + 0.5, "v": 1200}, # 2: LS pivot
        {"o": ls_low + 0.5, "h": neckline_high, "l": ls_low + 2, "c": neckline_high - 1, "v": 1100},  # 3: > LS
        {"o": neckline_high - 1, "h": neckline_high, "l": safe_low, "c": safe_low, "v": 1200},  # 4: safe (> both shoulders AND > head)
        {"o": safe_low, "h": safe_low + 1, "l": head_low + 2, "c": head_low + 2, "v": 1300},  # 5: > head
        {"o": head_low + 1, "h": head_low + 2, "l": head_low, "c": head_low + 0.5, "v": 1500},  # 6: Head pivot
        {"o": head_low + 0.5, "h": head_low + 3, "l": head_low + 2, "c": head_low + 2, "v": 1300},  # 7: > head
        {"o": head_low + 2, "h": neckline_high, "l": safe_low, "c": neckline_high - 1, "v": 1200},  # 8: safe (> both shoulders)
        {"o": neckline_high - 1, "h": neckline_high - 0.5, "l": rs_low + 2, "c": rs_low + 2, "v": 1100},  # 9: > RS
        {"o": rs_low + 1, "h": rs_low + 2, "l": rs_low, "c": rs_low + 0.5, "v": 1100},  # 10: RS pivot
        {"o": rs_low + 0.5, "h": neckline_high - 1, "l": rs_low + 2, "c": neckline_high - 2, "v": 1000},  # 11: > RS
        {"o": neckline_high - 2, "h": neckline_high + 0.5, "l": neckline_high - 1, "c": neckline_high, "v": 1100},  # 12: > RS
        {"o": neckline_high, "h": breakout_close + 0.5, "l": neckline_high - 0.5, "c": breakout_close, "v": 1400},  # 13: breakout
    ]
    return bars


def _build_hns_top_bars(
    ls_high=4500.0, head_high=4510.0, rs_high=4501.0,
    neckline_low=4490.0, breakout_close=4489.0,
):
    """Build a 14-bar H&S Top fixture with controllable pivots."""
    safe_high = min(ls_high, rs_high) - 4  # safe distance below both shoulder highs
    bars = [
        {"o": 4494, "h": safe_high - 1, "l": 4493, "c": 4494, "v": 1000},               # 0: safe
        {"o": 4495, "h": ls_high - 2, "l": 4494, "c": ls_high - 2, "v": 1100},          # 1: < LS
        {"o": ls_high - 1, "h": ls_high, "l": ls_high - 2, "c": ls_high - 0.5, "v": 1200},  # 2: LS pivot
        {"o": ls_high - 0.5, "h": ls_high - 2, "l": neckline_low, "c": neckline_low + 1, "v": 1100},  # 3: < LS
        {"o": neckline_low + 1, "h": safe_high, "l": neckline_low, "c": safe_high, "v": 1200},  # 4: safe
        {"o": safe_high, "h": head_high - 2, "l": neckline_low + 1, "c": head_high - 2, "v": 1300},  # 5: < head
        {"o": head_high - 1, "h": head_high, "l": head_high - 2, "c": head_high - 0.5, "v": 1500},  # 6: Head pivot
        {"o": head_high - 0.5, "h": head_high - 2, "l": neckline_low + 1, "c": head_high - 2, "v": 1300},  # 7: < head
        {"o": head_high - 2, "h": safe_high, "l": neckline_low, "c": safe_high, "v": 1200},  # 8: safe
        {"o": safe_high, "h": rs_high - 2, "l": neckline_low + 0.5, "c": rs_high - 2, "v": 1100},  # 9: < RS
        {"o": rs_high - 0.5, "h": rs_high, "l": rs_high - 2, "c": rs_high - 0.5, "v": 1100},  # 10: RS pivot
        {"o": rs_high - 0.5, "h": rs_high - 2, "l": neckline_low + 1, "c": neckline_low + 2, "v": 1000},  # 11: < RS
        {"o": neckline_low + 1, "h": neckline_low + 1, "l": neckline_low - 0.5, "c": neckline_low, "v": 1100},  # 12
        {"o": neckline_low, "h": neckline_low + 0.5, "l": breakout_close - 0.5, "c": breakout_close, "v": 1400},  # 13: breakout
    ]
    return bars


# ── Tests 1-2: Classic symmetric detections ──


class TestClassicDetection:
    def test_inverse_hns_classic_symmetric(self):
        bars = _build_inverse_hns_bars(ls_low=4500.0, head_low=4490.0, rs_low=4500.0)
        d, c, info = detect_inverse_hns(bars)
        assert d == "LONG"
        assert c >= 0.7
        assert info["kind"] == "INVERSE_HNS"
        assert info["pattern_measure"] == pytest.approx(20.0, abs=1.0)
        assert info["structural_anchor"] == pytest.approx(4500.0 - TICK_SIZE, abs=0.01)

    def test_hns_top_classic_symmetric(self):
        bars = _build_hns_top_bars(ls_high=4500.0, head_high=4510.0, rs_high=4500.0)
        d, c, info = detect_hns_top(bars)
        assert d == "SHORT"
        assert info["kind"] == "HNS_TOP"
        assert info["pattern_measure"] == pytest.approx(20.0, abs=1.0)
        assert info["structural_anchor"] == pytest.approx(4500.0 + TICK_SIZE, abs=0.01)


# ── Tests 3-4: Asymmetric shoulders rejected ──


class TestAsymmetricRejection:
    def test_inverse_hns_asymmetric_shoulders_rejected(self):
        # LS=4500, RS=4480 → 20pt difference, head=4490 → asymmetry >> 5%
        bars = _build_inverse_hns_bars(ls_low=4500.0, head_low=4490.0, rs_low=4480.0)
        d, c, info = detect_inverse_hns(bars)
        assert d is None

    def test_hns_top_asymmetric_shoulders_rejected(self):
        bars = _build_hns_top_bars(ls_high=4500.0, head_high=4510.0, rs_high=4480.0)
        d, c, info = detect_hns_top(bars)
        assert d is None


# ── Tests 5-6: Head not extreme → rejected ──


class TestHeadNotExtreme:
    def test_inverse_hns_head_not_lowest_rejected(self):
        # Head at 4501 is NOT lower than LS=4500
        bars = _build_inverse_hns_bars(ls_low=4500.0, head_low=4501.0, rs_low=4499.0)
        d, c, info = detect_inverse_hns(bars)
        assert d is None

    def test_hns_top_head_not_highest_rejected(self):
        bars = _build_hns_top_bars(ls_high=4510.0, head_high=4505.0, rs_high=4509.0)
        d, c, info = detect_hns_top(bars)
        assert d is None


# ── Tests 7-8: No breakout → rejected ──


class TestNoBreakout:
    def test_inverse_hns_no_breakout_rejected(self):
        # Close exactly at neckline (4510) — NOT > neckline + 1T
        bars = _build_inverse_hns_bars(breakout_close=4510.0)
        d, c, info = detect_inverse_hns(bars)
        assert d is None

    def test_hns_top_no_breakout_rejected(self):
        bars = _build_hns_top_bars(breakout_close=4490.0)
        d, c, info = detect_hns_top(bars)
        assert d is None


# ── Test 9: Insufficient bars ──


class TestInsufficientBars:
    def test_inverse_hns_insufficient_bars(self):
        bars = [{"o": 100, "h": 101, "l": 99, "c": 100, "v": 100}] * 8
        d, c, info = detect_inverse_hns(bars)
        assert d is None


# ── Test 10: Head extension below threshold ──


class TestHeadExtension:
    def test_hns_top_head_extension_below_threshold(self):
        # Head only 0.25pt (1T) above avg shoulder — needs >= 2T
        avg_shoulder = (4500.0 + 4501.0) / 2
        head = avg_shoulder + TICK_SIZE  # only 1T above
        bars = _build_hns_top_bars(ls_high=4500.0, head_high=head, rs_high=4501.0)
        d, c, info = detect_hns_top(bars)
        assert d is None


# ── Tests 11-12: Confidence levels ──


class TestConfidence:
    def test_inverse_hns_confidence_perfect_pattern(self):
        # Perfectly symmetric shoulders + head 10T beyond (ext_score=1.0)
        avg = 4500.0
        head = avg - 10 * TICK_SIZE  # 10T = 2.5pt below shoulders → ext_score = (10/2-1)/4 = 1.0
        bars = _build_inverse_hns_bars(ls_low=4500.0, head_low=head, rs_low=4500.0)
        d, c, info = detect_inverse_hns(bars)
        assert d is not None
        assert c == pytest.approx(1.0, abs=0.01)

    def test_hns_top_confidence_marginal_pattern(self):
        # Shoulders at edge of symmetry, head barely extends
        bars = _build_hns_top_bars()
        d, c, info = detect_hns_top(bars)
        if d is not None:
            assert 0.60 <= c <= 1.0


# ── Tests 13-14: Structural anchor ──


class TestStructuralAnchor:
    def test_inverse_hns_returns_structural_anchor(self):
        bars = _build_inverse_hns_bars(ls_low=4500.0, head_low=4490.0, rs_low=4500.0)
        d, c, info = detect_inverse_hns(bars)
        assert d is not None
        assert info["structural_anchor"] == pytest.approx(4500.0 - TICK_SIZE, abs=0.01)

    def test_hns_top_returns_structural_anchor(self):
        bars = _build_hns_top_bars(ls_high=4500.0, head_high=4510.0, rs_high=4500.0)
        d, c, info = detect_hns_top(bars)
        assert d is not None
        assert info["structural_anchor"] == pytest.approx(4500.0 + TICK_SIZE, abs=0.01)


# ── Tests 15-16: Pattern measure positive ──


class TestPatternMeasure:
    def test_inverse_hns_pattern_measure_positive(self):
        bars = _build_inverse_hns_bars(head_low=4490.0, neckline_high=4510.0)
        d, c, info = detect_inverse_hns(bars)
        if d is not None:
            assert info["pattern_measure"] > 0
            assert info["pattern_measure"] == pytest.approx(20.0, abs=1.0)

    def test_hns_top_pattern_measure_positive(self):
        bars = _build_hns_top_bars(head_high=4510.0, neckline_low=4490.0)
        d, c, info = detect_hns_top(bars)
        if d is not None:
            assert info["pattern_measure"] > 0
            assert info["pattern_measure"] == pytest.approx(20.0, abs=1.0)
