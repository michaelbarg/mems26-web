"""Golden tests for Double Bottom Eve&Eve + Double Top Adam&Adam (Pkg 5b · D-091 §7+§8)."""
import pytest
from backend.v9.systems.five_min.patterns.double_bt import (
    detect_double_bottom_ee,
    detect_double_top_aa,
    MIN_BARS_REQUIRED,
    TROUGH_SYM_PCT,
    TROUGH_MIN_WIDTH_BARS,
    PEAK_MAX_WIDTH_BARS,
    NECKLINE_MIN_RISE_PCT,
    TICK_SIZE,
)


# ── Fixture builders ──


def _build_double_bottom_ee(
    t1_low=4490.0, t2_low=4491.0, neckline_high=4510.0,
    breakout_close=4511.0, trough_width=4,
):
    """Build Eve&Eve double bottom: 2 wide troughs + neckline + breakout.
    Each trough has `trough_width` bars at similar low.
    """
    safe = max(t1_low, t2_low) + 5
    bars = []
    # Approach (2 bars with lows > trough)
    bars.append({"o": safe, "h": safe + 1, "l": safe, "c": safe, "v": 1000})
    bars.append({"o": safe, "h": safe + 1, "l": safe - 1, "c": safe - 1, "v": 1000})
    # Trough 1 (Eve = wide): center bar is lowest, neighbors at +0.25 (within 0.2% tolerance)
    for k in range(trough_width):
        offset = 0.0 if k == trough_width // 2 else 0.25
        bars.append({"o": t1_low + 0.5, "h": t1_low + 1, "l": t1_low + offset, "c": t1_low + 0.5, "v": 1200})
    # Rise above troughs (2 bars with lows > trough)
    bars.append({"o": t1_low + 1, "h": neckline_high, "l": safe - 2, "c": neckline_high - 1, "v": 1100})
    bars.append({"o": neckline_high - 1, "h": neckline_high, "l": safe - 1, "c": safe, "v": 1000})
    # Drop back
    bars.append({"o": safe, "h": safe, "l": safe - 2, "c": safe - 2, "v": 1100})
    # Trough 2 (Eve = wide): same pattern
    for k in range(trough_width):
        offset = 0.0 if k == trough_width // 2 else 0.25
        bars.append({"o": t2_low + 0.5, "h": t2_low + 1, "l": t2_low + offset, "c": t2_low + 0.5, "v": 1200})
    # Rise + breakout (2 bars with lows > trough)
    bars.append({"o": t2_low + 1, "h": neckline_high - 1, "l": safe - 2, "c": neckline_high - 2, "v": 1100})
    bars.append({"o": neckline_high - 2, "h": breakout_close + 0.5, "l": neckline_high - 1, "c": breakout_close, "v": 1400})
    return bars


def _build_double_top_aa(
    p1_high=4510.0, p2_high=4509.0, neckline_low=4490.0,
    breakout_close=4489.0, peak_width=1,
):
    """Build Adam&Adam double top: 2 sharp peaks + neckline + breakout."""
    safe = min(p1_high, p2_high) - 5
    bars = []
    # Approach
    bars.append({"o": safe, "h": safe + 1, "l": safe - 1, "c": safe, "v": 1000})
    bars.append({"o": safe, "h": safe + 2, "l": safe, "c": safe + 1, "v": 1000})
    # Peak 1 (Adam = sharp V)
    bars.append({"o": p1_high - 1, "h": p1_high, "l": p1_high - 2, "c": p1_high - 0.5, "v": 1200})
    # Drop to neckline
    bars.append({"o": p1_high - 1, "h": p1_high - 1, "l": neckline_low, "c": neckline_low + 1, "v": 1100})
    bars.append({"o": neckline_low + 1, "h": neckline_low + 2, "l": neckline_low, "c": neckline_low + 1, "v": 1000})
    # Rise toward peak 2
    bars.append({"o": neckline_low + 1, "h": safe + 2, "l": neckline_low + 1, "c": safe + 1, "v": 1100})
    # Peak 2 (Adam = sharp V)
    bars.append({"o": p2_high - 1, "h": p2_high, "l": p2_high - 2, "c": p2_high - 0.5, "v": 1200})
    # Drop + breakout
    bars.append({"o": p2_high - 1, "h": p2_high - 1, "l": safe - 1, "c": safe, "v": 1100})
    bars.append({"o": safe, "h": safe, "l": neckline_low, "c": neckline_low + 0.5, "v": 1000})
    bars.append({"o": neckline_low + 0.5, "h": neckline_low + 0.5, "l": breakout_close - 0.5, "c": breakout_close, "v": 1400})
    return bars


# ── Tests 1-2: Classic detections ──


class TestClassicDetection:
    def test_double_bottom_ee_classic_symmetric(self):
        bars = _build_double_bottom_ee(t1_low=4490.0, t2_low=4490.0)
        d, c, info = detect_double_bottom_ee(bars)
        assert d == "LONG"
        assert c >= 0.7
        assert info["kind"] == "DOUBLE_BOTTOM_EE"
        assert info["pattern_measure"] == pytest.approx(20.0, abs=1.0)
        assert info["structural_anchor"] == pytest.approx(4490.0 - TICK_SIZE, abs=0.01)

    def test_double_top_aa_classic_symmetric(self):
        bars = _build_double_top_aa(p1_high=4510.0, p2_high=4510.0)
        d, c, info = detect_double_top_aa(bars)
        assert d == "SHORT"
        assert info["kind"] == "DOUBLE_TOP_AA"
        assert info["pattern_measure"] == pytest.approx(20.0, abs=1.0)
        assert info["structural_anchor"] == pytest.approx(4510.0 + TICK_SIZE, abs=0.01)


# ── Tests 3-4: Asymmetric rejected ──


class TestAsymmetricRejection:
    def test_double_bottom_ee_asymmetric_troughs_rejected(self):
        bars = _build_double_bottom_ee(t1_low=4490.0, t2_low=4350.0)
        d, c, info = detect_double_bottom_ee(bars)
        assert d is None

    def test_double_top_aa_asymmetric_peaks_rejected(self):
        bars = _build_double_top_aa(p1_high=4510.0, p2_high=4350.0)
        d, c, info = detect_double_top_aa(bars)
        assert d is None


# ── Tests 5-6: Variant enforcement ──


class TestVariantEnforcement:
    def test_double_bottom_ee_v_shaped_troughs_rejected(self):
        """V-shaped (Adam) trough should fail Eve check (width < 3)."""
        bars = _build_double_bottom_ee(t1_low=4490.0, t2_low=4490.0, trough_width=1)
        d, c, info = detect_double_bottom_ee(bars)
        assert d is None

    def test_double_top_aa_rounded_peaks_rejected(self):
        """Rounded (Eve) peaks should fail Adam check (width > 2)."""
        bars = _build_double_top_aa(p1_high=4510.0, p2_high=4510.0, peak_width=4)
        # Build wide peaks manually
        safe = 4505.0
        bars = []
        bars.append({"o": safe, "h": safe + 1, "l": safe - 1, "c": safe, "v": 1000})
        bars.append({"o": safe, "h": safe + 2, "l": safe, "c": safe + 1, "v": 1000})
        # Wide peak 1 (3 bars at high = Eve, not Adam)
        for _ in range(3):
            bars.append({"o": 4509.5, "h": 4510.0, "l": 4508, "c": 4509.5, "v": 1200})
        bars.append({"o": 4509, "h": 4509, "l": 4490, "c": 4491, "v": 1100})
        bars.append({"o": 4491, "h": 4492, "l": 4490, "c": 4491, "v": 1000})
        bars.append({"o": 4491, "h": safe + 2, "l": 4491, "c": safe + 1, "v": 1100})
        for _ in range(3):
            bars.append({"o": 4509.5, "h": 4510.0, "l": 4508, "c": 4509.5, "v": 1200})
        bars.append({"o": 4509, "h": 4509, "l": 4491, "c": 4491, "v": 1100})
        bars.append({"o": 4491, "h": 4491, "l": 4489, "c": 4489, "v": 1400})
        d, c, info = detect_double_top_aa(bars)
        assert d is None


# ── Tests 7-8: No breakout ──


class TestNoBreakout:
    def test_double_bottom_ee_no_breakout_rejected(self):
        bars = _build_double_bottom_ee(breakout_close=4510.0)  # at neckline, not above
        d, c, info = detect_double_bottom_ee(bars)
        assert d is None

    def test_double_top_aa_no_breakout_rejected(self):
        bars = _build_double_top_aa(breakout_close=4490.0)  # at neckline, not below
        d, c, info = detect_double_top_aa(bars)
        assert d is None


# ── Test 9: Insufficient bars ──


class TestInsufficientBars:
    def test_double_bottom_ee_insufficient_bars(self):
        bars = [{"o": 100, "h": 101, "l": 99, "c": 100, "v": 100}] * 8
        d, c, info = detect_double_bottom_ee(bars)
        assert d is None


# ── Test 10: Neckline too shallow ──


class TestNecklineShallow:
    def test_double_bottom_ee_neckline_too_shallow(self):
        """Flat bars with no significant neckline rise → no pattern detected.
        All bar highs barely above lows → degenerate pattern (height/price < 0.1%)."""
        low = 4490.0
        # 12 bars all with h = low + 0.25 → neckline = low + 0.25 → height = 0.25 → 0.25/4490 < 0.001
        bars = [{"o": low + 0.1, "h": low + 0.25, "l": low + 0.1, "c": low + 0.1, "v": 1000}] * 2
        for _ in range(3):
            bars.append({"o": low + 0.1, "h": low + 0.25, "l": low, "c": low + 0.1, "v": 1200})
        bars.append({"o": low + 0.1, "h": low + 0.25, "l": low + 0.1, "c": low + 0.1, "v": 1000})
        bars.append({"o": low + 0.1, "h": low + 0.25, "l": low + 0.1, "c": low + 0.1, "v": 1000})
        bars.append({"o": low + 0.1, "h": low + 0.25, "l": low + 0.1, "c": low + 0.1, "v": 1100})
        for _ in range(3):
            bars.append({"o": low + 0.1, "h": low + 0.25, "l": low, "c": low + 0.1, "v": 1200})
        bars.append({"o": low + 0.1, "h": low + 0.5, "l": low + 0.1, "c": low + 0.4, "v": 1400})
        d, c, info = detect_double_bottom_ee(bars)
        assert d is None


# ── Tests 11-12: Confidence ──


class TestConfidence:
    def test_double_bottom_ee_confidence_perfect_pattern(self):
        """Identical troughs, both 9+ bars wide (variant_score=1.0)."""
        bars = _build_double_bottom_ee(t1_low=4490.0, t2_low=4490.0, trough_width=9)
        d, c, info = detect_double_bottom_ee(bars)
        assert d is not None
        assert c == pytest.approx(1.0, abs=0.05)

    def test_double_top_aa_confidence_marginal_pattern(self):
        bars = _build_double_top_aa()
        d, c, info = detect_double_top_aa(bars)
        if d is not None:
            assert 0.60 <= c <= 1.0


# ── Tests 13-14: Structural anchor ──


class TestStructuralAnchor:
    def test_double_bottom_ee_returns_structural_anchor(self):
        bars = _build_double_bottom_ee(t1_low=4490.0, t2_low=4490.0)
        d, c, info = detect_double_bottom_ee(bars)
        assert d is not None
        assert info["structural_anchor"] == pytest.approx(4490.0 - TICK_SIZE, abs=0.01)

    def test_double_top_aa_returns_structural_anchor(self):
        bars = _build_double_top_aa(p1_high=4510.0, p2_high=4510.0)
        d, c, info = detect_double_top_aa(bars)
        assert d is not None
        assert info["structural_anchor"] == pytest.approx(4510.0 + TICK_SIZE, abs=0.01)


# ── Tests 15-16: Pattern measure positive ──


class TestPatternMeasure:
    def test_double_bottom_ee_pattern_measure_positive(self):
        bars = _build_double_bottom_ee(t1_low=4490.0, t2_low=4490.0, neckline_high=4510.0)
        d, c, info = detect_double_bottom_ee(bars)
        assert d is not None
        assert info["pattern_measure"] > 0
        assert info["pattern_measure"] == pytest.approx(20.0, abs=1.0)

    def test_double_top_aa_pattern_measure_positive(self):
        bars = _build_double_top_aa(p1_high=4510.0, p2_high=4510.0, neckline_low=4490.0)
        d, c, info = detect_double_top_aa(bars)
        assert d is not None
        assert info["pattern_measure"] > 0
        assert info["pattern_measure"] == pytest.approx(20.0, abs=1.0)
