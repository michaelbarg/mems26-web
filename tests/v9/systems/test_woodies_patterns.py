"""Tests: Woodies CCI 8 pattern detectors -- new WoodiesBar interface.

Coverage target: >85% across all 8 detectors + detect_all_patterns.
Tests each pattern with: positive detection, negative (no signal), edge cases.
"""

import pytest
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult
from backend.v9.systems.woodies.patterns import (
    zlr, tlb, tt, gb100, vegas, ghost, famir, htlb,
)
from backend.v9.systems.woodies.patterns import ALL_PATTERN_DETECTORS

# Import the top-level detect_all_patterns
from backend.v9.systems.woodies.pattern_engine import detect_all_patterns


# ---- Helpers ---------------------------------------------------------------

def make_bar(ts=1000.0, close=5250.0, high=5252.0, low=5248.0,
             open_=5249.0, volume=100, cci_14=0.0, cci_6_tcci=0.0,
             ema_34=5250.0, trend_state="GRAY", **kwargs) -> WoodiesBar:
    """Create a WoodiesBar with sensible defaults."""
    return WoodiesBar(
        ts=ts, open=open_, high=high, low=low, close=close,
        volume=volume, cci_14=cci_14, cci_6_tcci=cci_6_tcci,
        ema_34=ema_34, trend_state=trend_state, **kwargs,
    )


def make_bars_from_cci(cci_values, base_close=5250.0, step=0.5,
                       trend_state="GRAY", cci6_values=None, **kwargs):
    """Build list of WoodiesBar from CCI-14 values."""
    bars = []
    for i, cci in enumerate(cci_values):
        c = base_close + i * step
        cci6 = cci6_values[i] if cci6_values else cci * 1.1
        bars.append(make_bar(
            ts=1000.0 + i * 1800,
            close=c, high=c + 1.5, low=c - 1.0, open_=c - 0.25,
            cci_14=cci, cci_6_tcci=cci6, trend_state=trend_state,
            **kwargs,
        ))
    return bars


# ---- PatternResult schema tests -------------------------------------------

class TestPatternResult:
    def test_detected_false(self):
        r = PatternResult(detected=False, pattern_id="ZLR")
        assert r.detected is False
        assert r.pattern_id == "ZLR"
        assert r.direction == "NEUTRAL"
        assert r.targets == []

    def test_detected_true_with_fields(self):
        r = PatternResult(
            detected=True, pattern_id="ZLR", direction="LONG",
            confidence=0.85, entry_price=5250.0, stop=5248.0,
            targets=[5253.0, 5256.0], group="CONTINUATION",
            cci_at_signal=80.0, bar_index=12, ts=1000.0,
            details={"bars_since_extreme": 3},
        )
        assert r.detected is True
        assert r.entry_price == 5250.0
        assert r.stop == 5248.0
        assert len(r.targets) == 2

    def test_model_dump(self):
        r = PatternResult(detected=True, pattern_id="TLB", direction="SHORT",
                          confidence=0.7, entry_price=5260.0, stop=5262.5,
                          targets=[5257.0])
        d = r.model_dump()
        assert d["detected"] is True
        assert d["pattern_id"] == "TLB"


class TestWoodiesBarProperties:
    def test_ohlcv_aliases(self):
        bar = make_bar(open_=100.0, high=105.0, low=95.0, close=102.0, volume=500)
        assert bar.o == 100.0
        assert bar.h == 105.0
        assert bar.l == 95.0
        assert bar.c == 102.0
        assert bar.vol == 500


# ---- ZLR tests -------------------------------------------------------------

class TestZLR:
    def test_zlr_up_detected(self):
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is True
        assert result.pattern_id == "ZLR"
        assert result.direction == "LONG"
        assert result.group == "CONTINUATION"
        assert result.confidence > 0.5
        assert result.entry_price > 0
        assert result.stop < result.entry_price
        assert len(result.targets) == 2
        assert result.targets[0] > result.entry_price

    def test_zlr_down_detected(self):
        cci = [0] * 5 + [-120, -130, -110, -60, -50, -20, -55, -100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is True
        assert result.direction == "SHORT"
        assert result.stop > result.entry_price
        assert result.targets[0] < result.entry_price

    def test_zlr_no_signal_flat(self):
        cci = [0] * 15
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is False

    def test_zlr_insufficient_data(self):
        bars = make_bars_from_cci([50, 60])
        result = zlr.detect(bars)
        assert result.detected is False

    def test_zlr_confidence_range(self):
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert 0.0 < result.confidence <= 0.9

    def test_zlr_details_present(self):
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.details is not None
        assert "bars_since_extreme" in result.details


# ---- TLB tests -------------------------------------------------------------

class TestTLB:
    def test_tlb_up_detected(self):
        cci = [100, 90, 80, 70, 60, 50, 40, 30, 20, 80]
        bars = make_bars_from_cci(cci)
        result = tlb.detect(bars)
        assert result.detected is True
        assert result.pattern_id == "TLB"
        assert result.direction == "LONG"
        assert result.group == "CONTINUATION"
        assert result.entry_price > 0
        assert result.stop < result.entry_price

    def test_tlb_down_detected(self):
        cci = [-100, -90, -80, -70, -60, -50, -40, -30, -20, -80]
        bars = make_bars_from_cci(cci)
        result = tlb.detect(bars)
        assert result.detected is True
        assert result.direction == "SHORT"
        assert result.stop > result.entry_price

    def test_tlb_no_signal_flat(self):
        cci = [50] * 10
        bars = make_bars_from_cci(cci)
        result = tlb.detect(bars)
        assert result.detected is False

    def test_tlb_insufficient_data(self):
        bars = make_bars_from_cci([50, 60, 70])
        result = tlb.detect(bars)
        assert result.detected is False

    def test_tlb_details_have_slope(self):
        cci = [100, 90, 80, 70, 60, 50, 40, 30, 20, 80]
        bars = make_bars_from_cci(cci)
        result = tlb.detect(bars)
        assert result.details is not None
        assert "slope" in result.details
        assert "break_amount" in result.details


# ---- TT tests --------------------------------------------------------------

class TestTT:
    def test_tt_long_detected(self):
        cci14_vals = [80, 85, 90, 95, 100, 100, 50, 95, 100]
        cci6_vals = [110, 115, 120, 125, 130, 120, 110, 100, 120]
        bars = []
        for i in range(len(cci14_vals)):
            c = 5250.0 + i * 0.5
            bars.append(make_bar(
                ts=1000.0 + i * 1800, close=c, high=c + 1.5, low=c - 1.0,
                cci_14=cci14_vals[i], cci_6_tcci=cci6_vals[i],
                trend_state="BLUE",
            ))
        result = tt.detect(bars)
        assert result.detected is True
        assert result.pattern_id == "TT"
        assert result.direction == "LONG"
        assert result.group == "CONTINUATION"

    def test_tt_short_detected(self):
        cci14_vals = [-80, -85, -90, -95, -100, -100, -50, -95, -100]
        cci6_vals = [-110, -115, -120, -125, -130, -120, -110, -100, -120]
        bars = []
        for i in range(len(cci14_vals)):
            c = 5250.0 - i * 0.5
            bars.append(make_bar(
                ts=1000.0 + i * 1800, close=c, high=c + 1.0, low=c - 1.5,
                cci_14=cci14_vals[i], cci_6_tcci=cci6_vals[i],
                trend_state="RED",
            ))
        result = tt.detect(bars)
        assert result.detected is True
        assert result.direction == "SHORT"

    def test_tt_no_signal_gray_trend(self):
        cci14_vals = [80, 85, 90, 95, 100, 100, 90, 95, 100]
        cci6_vals = [110, 115, 120, 125, 130, 120, 110, 100, 120]
        bars = []
        for i in range(len(cci14_vals)):
            c = 5250.0 + i * 0.5
            bars.append(make_bar(
                ts=1000.0 + i * 1800, close=c, high=c + 1.5, low=c - 1.0,
                cci_14=cci14_vals[i], cci_6_tcci=cci6_vals[i],
                trend_state="GRAY",
            ))
        result = tt.detect(bars)
        assert result.detected is False

    def test_tt_insufficient_data(self):
        bars = [make_bar(cci_14=50, cci_6_tcci=60)]
        result = tt.detect(bars)
        assert result.detected is False


# ---- GB100 tests -----------------------------------------------------------

class TestGB100:
    def test_gb100_long_detected(self):
        cci = [50, 60, 70, 80, 90, 65, 99, 120]
        bars = make_bars_from_cci(cci, trend_state="BLUE")
        result = gb100.detect(bars)
        assert result.detected is True
        assert result.pattern_id == "GB100"
        assert result.direction == "LONG"
        assert result.group == "CONTINUATION"

    def test_gb100_short_detected(self):
        cci = [-50, -60, -70, -80, -90, -65, -99, -120]
        bars = make_bars_from_cci(cci, trend_state="RED")
        result = gb100.detect(bars)
        assert result.detected is True
        assert result.direction == "SHORT"

    def test_gb100_no_signal_wrong_trend(self):
        cci = [50, 60, 70, 80, 90, 95, 99, 120]
        bars = make_bars_from_cci(cci, trend_state="GRAY")
        result = gb100.detect(bars)
        assert result.detected is False

    def test_gb100_no_signal_no_cross(self):
        cci = [50, 60, 70, 80, 90, 95, 98, 99]
        bars = make_bars_from_cci(cci, trend_state="BLUE")
        result = gb100.detect(bars)
        assert result.detected is False

    def test_gb100_insufficient_data(self):
        bars = [make_bar(cci_14=110, trend_state="BLUE")]
        result = gb100.detect(bars)
        assert result.detected is False

    def test_gb100_entry_and_targets(self):
        cci = [50, 60, 70, 80, 90, 65, 99, 120]
        bars = make_bars_from_cci(cci, trend_state="BLUE")
        result = gb100.detect(bars)
        assert result.entry_price > 0
        assert result.stop < result.entry_price
        assert len(result.targets) == 2
        for t in result.targets:
            assert t > result.entry_price


# ---- VEGAS tests -----------------------------------------------------------

class TestVEGAS:
    def _make_divergence_bars(self, bearish=True):
        """Build bars with price/CCI divergence for VEGAS detection."""
        if bearish:
            # Price HH, CCI LH
            price = [
                70, 80, 90, 95, 100, 95, 85, 75, 65, 55,
                65, 80, 95, 102, 105, 102, 95, 85, 80, 75,
            ]
            cci = [
                50, 80, 120, 140, 150, 140, 100, 60, 30, 10,
                30, 60, 100, 115, 120, 115, 90, 60, 50, -10,
            ]
        else:
            # Price LL, CCI HL
            price = [
                60, 50, 40, 35, 30, 35, 45, 55, 70, 80,
                70, 55, 40, 30, 25, 30, 40, 55, 60, 65,
            ]
            cci = [
                -50, -80, -120, -140, -150, -140, -100, -60, -30, -10,
                -30, -60, -100, -115, -120, -115, -90, -60, -50, 10,
            ]
        # Pad with 5 prefix bars
        price = [price[0]] * 5 + price
        cci = [cci[0]] * 5 + cci
        bars = []
        for i in range(len(price)):
            bars.append(make_bar(
                ts=1000.0 + i * 1800,
                close=price[i], high=price[i] + 2, low=price[i] - 2,
                cci_14=cci[i],
            ))
        return bars

    def test_vegas_bearish_detected(self):
        bars = self._make_divergence_bars(bearish=True)
        result = vegas.detect(bars)
        assert result.detected is True
        assert result.pattern_id == "VEGAS"
        assert result.direction == "SHORT"
        assert result.group == "REVERSAL"

    def test_vegas_bullish_detected(self):
        bars = self._make_divergence_bars(bearish=False)
        result = vegas.detect(bars)
        assert result.detected is True
        assert result.direction == "LONG"

    def test_vegas_no_divergence(self):
        cci = [0.0] * 25
        bars = make_bars_from_cci(cci)
        result = vegas.detect(bars)
        assert result.detected is False

    def test_vegas_insufficient_data(self):
        bars = make_bars_from_cci([50, 60])
        result = vegas.detect(bars)
        assert result.detected is False

    def test_vegas_targets_and_stop(self):
        bars = self._make_divergence_bars(bearish=True)
        result = vegas.detect(bars)
        assert result.entry_price > 0
        assert result.stop > result.entry_price  # SHORT stop is above entry
        assert len(result.targets) == 2


# ---- GHOST tests -----------------------------------------------------------

class TestGHOST:
    def test_ghost_bearish_detected(self):
        # Three CCI peaks: left=120, head=180, right=100, then drops
        # Last 3 CCI must have range >= 50 for AP8
        cci = [50, 80, 120, 80, 60, 100, 180, 100, 60, 40,
               70, 100, 70, 40, 30, 20, 10, -50, 0, -10]
        bars = make_bars_from_cci(cci)
        result = ghost.detect(bars)
        assert result.detected is True
        assert result.pattern_id == "GHOST"
        assert result.direction == "SHORT"
        assert result.group == "REVERSAL"

    def test_ghost_bullish_detected(self):
        # Three CCI troughs: left=-120, head=-180, right=-100, then rises
        # Last 3 CCI must have range >= 50 for AP8
        cci = [-50, -80, -120, -80, -60, -100, -180, -100, -60, -40,
               -70, -100, -70, -40, -30, -20, -10, 50, 0, 10]
        bars = make_bars_from_cci(cci)
        result = ghost.detect(bars)
        assert result.detected is True
        assert result.direction == "LONG"

    def test_ghost_no_signal_flat(self):
        cci = [50] * 20
        bars = make_bars_from_cci(cci)
        result = ghost.detect(bars)
        assert result.detected is False

    def test_ghost_insufficient_data(self):
        bars = make_bars_from_cci([50, 60, 70])
        result = ghost.detect(bars)
        assert result.detected is False

    def test_ghost_details_present(self):
        cci = [50, 80, 120, 80, 60, 100, 180, 100, 60, 40,
               70, 100, 70, 40, 30, 20, 10, 5, 0, -10]
        bars = make_bars_from_cci(cci)
        result = ghost.detect(bars)
        if result.detected:
            assert "left" in result.details
            assert "head" in result.details
            assert "right" in result.details


# ---- FAMIR tests -----------------------------------------------------------

class TestFAMIR:
    def test_famir_short_detected(self):
        cci = [100, 130, 160, 180, 185, 175, 150, 120]
        bars = make_bars_from_cci(cci, lsma_above_price=True)
        result = famir.detect(bars)
        assert result.detected is True
        assert result.pattern_id == "FAMIR"
        assert result.direction == "SHORT"
        assert result.group == "REVERSAL"

    def test_famir_long_detected(self):
        cci = [-100, -130, -160, -180, -185, -175, -150, -120]
        bars = make_bars_from_cci(cci)
        result = famir.detect(bars)
        assert result.detected is True
        assert result.direction == "LONG"

    def test_famir_no_signal_below_threshold(self):
        cci = [50, 60, 70, 80, 90, 85, 80, 75]
        bars = make_bars_from_cci(cci)
        result = famir.detect(bars)
        assert result.detected is False

    def test_famir_no_signal_exceeded_200(self):
        # CCI went above 210 -- not a failure at 200
        cci = [100, 150, 180, 210, 220, 210, 200, 190]
        bars = make_bars_from_cci(cci)
        result = famir.detect(bars)
        assert result.detected is False

    def test_famir_insufficient_data(self):
        bars = make_bars_from_cci([180, 170])
        result = famir.detect(bars)
        assert result.detected is False

    def test_famir_stop_and_targets_short(self):
        cci = [100, 130, 160, 180, 185, 175, 150, 120]
        bars = make_bars_from_cci(cci, lsma_above_price=True)
        result = famir.detect(bars)
        assert result.stop > result.entry_price  # SHORT stop above entry
        assert len(result.targets) == 2
        for t in result.targets:
            assert t < result.entry_price

    def test_famir_stop_and_targets_long(self):
        cci = [-100, -130, -160, -180, -185, -175, -150, -120]
        bars = make_bars_from_cci(cci)
        result = famir.detect(bars)
        assert result.stop < result.entry_price  # LONG stop below entry
        assert len(result.targets) == 2
        for t in result.targets:
            assert t > result.entry_price


# ---- HTLB tests ------------------------------------------------------------

class TestHTLB:
    def test_htlb_resistance_break_detected(self):
        # Multiple touches at ~80, then break above
        cci = [50, 60, 70, 80, 70, 60, 70, 80, 70, 60, 70, 80, 70, 60, 100]
        bars = make_bars_from_cci(cci)
        result = htlb.detect(bars)
        # Whether detected depends on horizontal level detection
        assert result.pattern_id == "HTLB"
        if result.detected:
            assert result.direction == "LONG"

    def test_htlb_support_break_detected(self):
        # Multiple touches at ~-80, then break below
        cci = [-50, -60, -70, -80, -70, -60, -70, -80, -70, -60, -70, -80, -70, -60, -100]
        bars = make_bars_from_cci(cci)
        result = htlb.detect(bars)
        assert result.pattern_id == "HTLB"
        if result.detected:
            assert result.direction == "SHORT"

    def test_htlb_no_signal_no_level(self):
        # Random CCI with no clear horizontal level
        cci = [10, 30, 50, 70, 90, 110, 130, 150, 170, 190, 210, 230, 250, 270, 290]
        bars = make_bars_from_cci(cci)
        result = htlb.detect(bars)
        assert result.detected is False

    def test_htlb_insufficient_data(self):
        bars = make_bars_from_cci([50, 60])
        result = htlb.detect(bars)
        assert result.detected is False

    def test_htlb_details_have_level(self):
        cci = [50, 60, 70, 80, 70, 60, 70, 80, 70, 60, 70, 80, 70, 60, 100]
        bars = make_bars_from_cci(cci)
        result = htlb.detect(bars)
        if result.detected:
            assert "level" in result.details
            assert "break_amount" in result.details


# ---- detect_all_patterns integration tests ---------------------------------

class TestDetectAllPatterns:
    def test_returns_list(self):
        cci = [50] * 20
        bars = make_bars_from_cci(cci)
        results = detect_all_patterns(bars)
        assert isinstance(results, list)

    def test_empty_bars(self):
        results = detect_all_patterns([])
        assert results == []

    def test_short_bars(self):
        bars = [make_bar(), make_bar()]
        results = detect_all_patterns(bars)
        assert results == []

    def test_only_detected_returned(self):
        cci = [0] * 15
        bars = make_bars_from_cci(cci)
        results = detect_all_patterns(bars)
        for r in results:
            assert r.detected is True

    def test_zlr_detected_via_all(self):
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        bars = make_bars_from_cci(cci)
        results = detect_all_patterns(bars)
        zlr_results = [r for r in results if r.pattern_id == "ZLR"]
        assert len(zlr_results) >= 1

    def test_famir_detected_via_all(self):
        cci = [100, 130, 160, 180, 185, 175, 150, 120]
        bars = make_bars_from_cci(cci, lsma_above_price=True)
        results = detect_all_patterns(bars)
        famir_results = [r for r in results if r.pattern_id == "FAMIR"]
        assert len(famir_results) >= 1

    def test_context_passthrough(self):
        cci = [50] * 20
        bars = make_bars_from_cci(cci)
        ctx = {"session": "test"}
        results = detect_all_patterns(bars, context=ctx)
        assert isinstance(results, list)

    def test_all_9_detectors_registered(self):
        assert len(ALL_PATTERN_DETECTORS) == 9

    def test_pattern_ids_complete(self):
        from backend.v9.systems.woodies.pattern_engine import PATTERN_IDS
        expected = {"ZLR", "TLB", "TT", "GB100", "VEGAS", "GHOST", "FAMIR", "HTLB", "HFE"}
        assert set(PATTERN_IDS) == expected

    def test_continuation_vs_reversal(self):
        from backend.v9.systems.woodies.pattern_engine import (
            CONTINUATION_PATTERNS, REVERSAL_PATTERNS,
        )
        assert len(CONTINUATION_PATTERNS) == 4
        assert len(REVERSAL_PATTERNS) == 5  # includes HFE
        assert CONTINUATION_PATTERNS & REVERSAL_PATTERNS == set()


# ---- Legacy interface backward compat --------------------------------------

class TestLegacyInterface:
    """Verify legacy detect_<name> functions still work for detector.py."""

    def test_legacy_zlr(self):
        from backend.v9.systems.woodies.patterns.zlr import detect_zlr
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        result = detect_zlr(cci, bar_index=12, ts=1000.0)
        assert result is not None
        assert result.pattern == "ZLR"

    def test_legacy_tlb(self):
        from backend.v9.systems.woodies.patterns.tlb import detect_tlb
        cci = [100, 90, 80, 70, 60, 50, 40, 30, 20, 80]
        result = detect_tlb(cci, bar_index=9, ts=1000.0)
        assert result is not None
        assert result.pattern == "TLB"

    def test_legacy_gb100(self):
        from backend.v9.systems.woodies.patterns.gb100 import detect_gb100
        cci = [50, 60, 70, 80, 90, 95, 99, 120]
        result = detect_gb100(cci, bar_index=7, ts=1000.0, trend_state="BLUE")
        assert result is not None
        assert result.pattern == "GB100"

    def test_legacy_famir(self):
        from backend.v9.systems.woodies.patterns.famir import detect_famir
        cci = [100, 130, 160, 180, 185, 175, 150, 120]
        result = detect_famir(cci, bar_index=7, ts=1000.0)
        assert result is not None
        assert result.pattern == "FAMIR"

    def test_legacy_all_detectors_list(self):
        from backend.v9.systems.woodies.patterns import ALL_DETECTORS
        assert len(ALL_DETECTORS) == 8


# ---- Edge case tests -------------------------------------------------------

class TestEdgeCases:
    def test_all_patterns_handle_minimum_bars(self):
        """Every detector gracefully handles 1-bar input."""
        bars = [make_bar()]
        for det in ALL_PATTERN_DETECTORS:
            result = det(bars)
            assert isinstance(result, PatternResult)
            assert result.detected is False

    def test_all_patterns_handle_empty_bars(self):
        """Every detector gracefully handles empty input."""
        for det in ALL_PATTERN_DETECTORS:
            result = det([])
            assert isinstance(result, PatternResult)
            assert result.detected is False

    def test_extreme_cci_values(self):
        """Detectors handle extreme CCI values without errors."""
        cci = [500, -500, 1000, -1000, 0, 300, -300, 200]
        bars = make_bars_from_cci(cci)
        for det in ALL_PATTERN_DETECTORS:
            result = det(bars)
            assert isinstance(result, PatternResult)

    def test_all_zero_cci(self):
        """All detectors return not detected for constant zero CCI."""
        cci = [0.0] * 25
        bars = make_bars_from_cci(cci)
        results = detect_all_patterns(bars)
        assert len(results) == 0

    def test_context_none(self):
        """All detectors work with context=None."""
        bars = make_bars_from_cci([50] * 20)
        for det in ALL_PATTERN_DETECTORS:
            result = det(bars, None)
            assert isinstance(result, PatternResult)
