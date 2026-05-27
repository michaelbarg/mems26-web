"""Tests for W-7 anti-pattern gate (anti_patterns.py).

Coverage:
  - 2 tests per AP (positive=blocked, negative=allowed) = 16 tests
  - 4 integration tests:
      AP8 blocks ZLR on flat CCI
      AP3 blocks VEGAS on close swings
      AP9 blocks FAMIR LONG on LSMA mismatch
      HFE AP5 still works after W-7
"""

import pytest
from backend.v9.systems.woodies.anti_patterns import AntiPatternChecker, AntiPatternResult
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult


# ── Helpers ──────────────────────────────────────────────────────────

def _bar(cci_14=0.0, cci_6_tcci=0.0, trend_state="GRAY",
         lsma_above_price=False, ts=0.0, **kw):
    """Shorthand WoodiesBar factory."""
    return WoodiesBar(
        ts=ts, open=5800, high=5805, low=5795, close=5800,
        cci_14=cci_14, cci_6_tcci=cci_6_tcci, trend_state=trend_state,
        lsma_above_price=lsma_above_price, **kw,
    )


def _bars_with_cci(cci_values, **kw):
    """Build a list of WoodiesBar with given CCI-14 values."""
    return [_bar(cci_14=v, ts=float(i), **kw) for i, v in enumerate(cci_values)]


# ═══════════════════════════════════════════════════════════════════
# AP1: ZLR pullback too long
# ═══════════════════════════════════════════════════════════════════

class TestAP1:
    def test_ap1_blocked_long_pullback(self):
        """Pullback >12 bars from extreme -> blocked."""
        # Extreme at index 0 (150 CCI), then 14 bars of low CCI
        cci = [150] + [10] * 14
        bars = _bars_with_cci(cci)
        result = AntiPatternChecker.check_ap1_zlr_pullback(bars)
        assert result.blocked
        assert result.ap_id == "AP1"
        assert result.metadata["bars_since_extreme"] == 14

    def test_ap1_allowed_recent_extreme(self):
        """Extreme within 12 bars -> allowed."""
        cci = [10] * 5 + [120] + [30] * 5
        bars = _bars_with_cci(cci)
        result = AntiPatternChecker.check_ap1_zlr_pullback(bars)
        assert not result.blocked


# ═══════════════════════════════════════════════════════════════════
# AP2: GB100 YELLOW trend
# ═══════════════════════════════════════════════════════════════════

class TestAP2:
    def test_ap2_blocked_yellow(self):
        bars = [_bar(trend_state="YELLOW")]
        result = AntiPatternChecker.check_ap2_gb100_yellow(bars)
        assert result.blocked
        assert result.ap_id == "AP2"

    def test_ap2_allowed_blue(self):
        bars = [_bar(trend_state="BLUE")]
        result = AntiPatternChecker.check_ap2_gb100_yellow(bars)
        assert not result.blocked


# ═══════════════════════════════════════════════════════════════════
# AP3: VEGAS swings too close
# ═══════════════════════════════════════════════════════════════════

class TestAP3:
    def test_ap3_blocked_close_swings(self):
        bars = _bars_with_cci([50] * 10)
        result = AntiPatternChecker.check_ap3_vegas_swings(bars, swing_low_idx=10, swing_high_idx=13)
        assert result.blocked
        assert result.metadata["swing_gap"] == 3

    def test_ap3_allowed_far_swings(self):
        bars = _bars_with_cci([50] * 10)
        result = AntiPatternChecker.check_ap3_vegas_swings(bars, swing_low_idx=2, swing_high_idx=12)
        assert not result.blocked


# ═══════════════════════════════════════════════════════════════════
# AP4: HTLB insufficient touches
# ═══════════════════════════════════════════════════════════════════

class TestAP4:
    def test_ap4_blocked_one_touch(self):
        bars = _bars_with_cci([50] * 5)
        result = AntiPatternChecker.check_ap4_htlb_touches(bars, touches=1)
        assert result.blocked
        assert result.ap_id == "AP4"

    def test_ap4_allowed_two_touches(self):
        bars = _bars_with_cci([50] * 5)
        result = AntiPatternChecker.check_ap4_htlb_touches(bars, touches=2)
        assert not result.blocked


# ═══════════════════════════════════════════════════════════════════
# AP6: GB100 pullback depth
# ═══════════════════════════════════════════════════════════════════

class TestAP6:
    def test_ap6_blocked_deep_pullback(self):
        bars = _bars_with_cci([50] * 5)
        result = AntiPatternChecker.check_ap6_gb100_pullback_depth(bars, pullback_bars_opposite=7)
        assert result.blocked
        assert result.ap_id == "AP6"

    def test_ap6_allowed_shallow_pullback(self):
        bars = _bars_with_cci([50] * 5)
        result = AntiPatternChecker.check_ap6_gb100_pullback_depth(bars, pullback_bars_opposite=4)
        assert not result.blocked


# ═══════════════════════════════════════════════════════════════════
# AP7: TT TCCI divergence gap
# ═══════════════════════════════════════════════════════════════════

class TestAP7:
    def test_ap7_blocked_small_gap(self):
        bar = _bar(cci_14=100, cci_6_tcci=102)
        result = AntiPatternChecker.check_ap7_tt_divergence_gap(bar)
        assert result.blocked
        assert result.ap_id == "AP7"

    def test_ap7_allowed_large_gap(self):
        bar = _bar(cci_14=100, cci_6_tcci=120)
        result = AntiPatternChecker.check_ap7_tt_divergence_gap(bar)
        assert not result.blocked


# ═══════════════════════════════════════════════════════════════════
# AP8: CCI flat (universal)
# ═══════════════════════════════════════════════════════════════════

class TestAP8:
    def test_ap8_blocked_flat_cci(self):
        bars = _bars_with_cci([20, 21, 22])
        result = AntiPatternChecker.check_ap8_cci_flat(bars)
        assert result.blocked
        assert result.ap_id == "AP8"

    def test_ap8_allowed_volatile_cci(self):
        bars = _bars_with_cci([20, 100, 30])
        result = AntiPatternChecker.check_ap8_cci_flat(bars)
        assert not result.blocked


# ═══════════════════════════════════════════════════════════════════
# AP9: FAMIR LSMA mismatch
# ═══════════════════════════════════════════════════════════════════

class TestAP9:
    def test_ap9_blocked_long_lsma_above(self):
        bars = [_bar(lsma_above_price=True)]
        result = AntiPatternChecker.check_ap9_famir_lsma(bars, direction="LONG")
        assert result.blocked
        assert result.ap_id == "AP9"

    def test_ap9_allowed_long_lsma_below(self):
        bars = [_bar(lsma_above_price=False)]
        result = AntiPatternChecker.check_ap9_famir_lsma(bars, direction="LONG")
        assert not result.blocked


# ═══════════════════════════════════════════════════════════════════
# Integration tests
# ═══════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_ap8_blocks_zlr_on_flat_cci(self):
        """AP8 universal check blocks ZLR when CCI is flat."""
        from backend.v9.systems.woodies.patterns.zlr import detect as detect_zlr

        # Build bars that would trigger a ZLR UP but with flat CCI
        # Extreme at bar 5, pullback, then bounce -- but all within 2 points
        cci_values = [10] * 5 + [110] + [50, 40, 30, 25, 24, 23, 24]
        bars = _bars_with_cci(cci_values)
        result = detect_zlr(bars)
        # With AP8 in zlr.py, flat CCI (last 3 bars: 23, 24 -> range=1) blocks
        assert not result.detected or (result.details and result.details.get("reject_reason"))

    def test_ap3_blocks_vegas_on_close_swings(self):
        """AP3 blocks VEGAS when swing indices are too close together."""
        bars = _bars_with_cci([50] * 10)
        ap3 = AntiPatternChecker.check_ap3_vegas_swings(bars, swing_low_idx=10, swing_high_idx=12)
        assert ap3.blocked
        assert "too close" in ap3.reason

    def test_ap9_blocks_famir_long_lsma_mismatch(self):
        """AP9 blocks FAMIR LONG when LSMA is above price."""
        bars = [_bar(cci_14=50, lsma_above_price=True) for _ in range(5)]
        ap9 = AntiPatternChecker.check_ap9_famir_lsma(bars, direction="LONG")
        assert ap9.blocked
        assert "LSMA above price" in ap9.reason

    def test_hfe_ap5_still_works(self):
        """HFE AP5 enforcement in hfe.py still works after W-7 changes.

        AP5 blocks when bars_ago is outside [2, 12]. We test with
        hfe_extreme_bars_ago=0 (outside range).
        CCI values must vary enough to pass AP8 (range >= 50).
        """
        from backend.v9.systems.woodies.patterns.hfe import detect as detect_hfe

        # Varied CCI so AP8 doesn't fire, but AP5 does (bars_ago=0)
        cci_vals = [-250, -200, -180, -150, -100]
        bars = [
            _bar(cci_14=c, ts=float(i), hfe_detected=True, hfe_direction="UP",
                 hfe_extreme_bars_ago=0)
            for i, c in enumerate(cci_vals)
        ]
        result = detect_hfe(bars)
        # AP5 should block because bars_ago=0 is outside [2, 12]
        assert not result.detected
        assert result.details.get("ap5_blocked") is True
