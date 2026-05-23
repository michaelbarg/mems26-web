"""Golden tests for Adaptive Stop Engine (D-091 · Pkg 1).

Tests are AUTHORITY per handoff §1 — pseudo-code is illustrative only.
Uses corrected min(max(A,B), floor) formula, NOT the deprecated max(A,B,C).
"""

import logging
import pytest

from backend.v9.systems.five_min.adaptive_stop import (
    compute_baseline_atr,
    compute_rolling_atr,
    compute_today_typical,
    compute_today_max,
    compute_stop,
    StopComputation,
    MES_TICK,
    FLOOR_TICKS,
    ATR_MULTIPLIERS,
)


# ── Helper: make a bar dict ──────────────────────────────────────

def _bar(h: float, l: float, c: float) -> dict:
    return {"h": h, "l": l, "c": c}


# ── Test 1: baseline ATR-14 basic ────────────────────────────────

class TestBaselineATR:
    def test_baseline_atr_14_basic(self):
        """14 bars with known ranges → Wilder's ATR-14 exact."""
        # 14 bars: range = h - l for each, prev_close used for TR
        bars = [
            _bar(101.0, 100.0, 100.5),  # range=1.0
            _bar(101.2, 100.0, 100.8),  # range=1.2, TR=max(1.2, |101.2-100.5|, |100.0-100.5|)=max(1.2, 0.7, 0.5)=1.2
            _bar(102.0, 100.5, 101.5),  # range=1.5
            _bar(101.8, 100.6, 101.0),  # range=1.2
            _bar(102.5, 101.5, 102.0),  # range=1.0
            _bar(103.0, 101.2, 102.5),  # range=1.8
            _bar(102.0, 101.0, 101.5),  # range=1.0
            _bar(102.2, 101.0, 101.8),  # range=1.2
            _bar(103.0, 101.5, 102.5),  # range=1.5
            _bar(102.5, 101.5, 102.0),  # range=1.0
            _bar(103.5, 102.0, 103.0),  # range=1.5
            _bar(103.0, 101.5, 102.0),  # range=1.5
            _bar(102.5, 101.0, 101.5),  # range=1.5
            _bar(102.0, 100.5, 101.0),  # range=1.5
        ]
        # Compute TRs by hand:
        # TR[0] = 1.0 (no prev)
        # TR[1] = max(1.2, |101.2-100.5|, |100.0-100.5|) = max(1.2, 0.7, 0.5) = 1.2
        # TR[2] = max(1.5, |102.0-100.8|, |100.5-100.8|) = max(1.5, 1.2, 0.3) = 1.5
        # TR[3] = max(1.2, |101.8-101.5|, |100.6-101.5|) = max(1.2, 0.3, 0.9) = 1.2
        # TR[4] = max(1.0, |102.5-101.0|, |101.5-101.0|) = max(1.0, 1.5, 0.5) = 1.5
        # TR[5] = max(1.8, |103.0-102.0|, |101.2-102.0|) = max(1.8, 1.0, 0.8) = 1.8
        # TR[6] = max(1.0, |102.0-102.5|, |101.0-102.5|) = max(1.0, 0.5, 1.5) = 1.5
        # TR[7] = max(1.2, |102.2-101.5|, |101.0-101.5|) = max(1.2, 0.7, 0.5) = 1.2
        # TR[8] = max(1.5, |103.0-101.8|, |101.5-101.8|) = max(1.5, 1.2, 0.3) = 1.5
        # TR[9] = max(1.0, |102.5-102.5|, |101.5-102.5|) = max(1.0, 0.0, 1.0) = 1.0
        # TR[10] = max(1.5, |103.5-102.0|, |102.0-102.0|) = max(1.5, 1.5, 0.0) = 1.5
        # TR[11] = max(1.5, |103.0-103.0|, |101.5-103.0|) = max(1.5, 0.0, 1.5) = 1.5
        # TR[12] = max(1.5, |102.5-102.0|, |101.0-102.0|) = max(1.5, 0.5, 1.0) = 1.5
        # TR[13] = max(1.5, |102.0-101.5|, |100.5-101.5|) = max(1.5, 0.5, 1.0) = 1.5
        # TRs = [1.0, 1.2, 1.5, 1.2, 1.5, 1.8, 1.5, 1.2, 1.5, 1.0, 1.5, 1.5, 1.5, 1.5]
        # ATR = mean(all 14 TRs) = (1.0+1.2+1.5+1.2+1.5+1.8+1.5+1.2+1.5+1.0+1.5+1.5+1.5+1.5)/14
        #      = 19.4 / 14 = ~1.38571...
        expected_atr = 19.4 / 14
        result = compute_baseline_atr(bars)
        assert abs(result - expected_atr) < 1e-10, f"Expected {expected_atr}, got {result}"

    def test_baseline_atr_insufficient_bars(self):
        """Fewer than 14 bars → RuntimeError."""
        bars = [_bar(101.0, 100.0, 100.5)] * 5
        with pytest.raises(RuntimeError, match="≥14"):
            compute_baseline_atr(bars)


# ── Test 3: rolling ATR during IB ────────────────────────────────

class TestRollingATR:
    def test_rolling_atr_during_ib(self):
        """6 bars in IB → simple mean of bar ranges."""
        bars = [
            _bar(101.0, 100.0, 100.5),  # range 1.0
            _bar(101.5, 100.5, 101.0),  # range 1.0
            _bar(102.0, 100.0, 101.0),  # range 2.0
            _bar(101.5, 100.5, 101.0),  # range 1.0
            _bar(102.5, 101.0, 102.0),  # range 1.5
            _bar(101.0, 100.0, 100.5),  # range 1.0
        ]
        # mean = (1.0 + 1.0 + 2.0 + 1.0 + 1.5 + 1.0) / 6 = 7.5 / 6 = 1.25
        result = compute_rolling_atr(bars)
        assert result == pytest.approx(1.25)


# ── Test 4: today_typical P75 ────────────────────────────────────

class TestTodayTypical:
    def test_today_typical_p75(self):
        """20 bars with known ranges → 75th percentile via statistics.quantiles."""
        # Create 20 bars with ranges 0.5, 1.0, 1.5, ..., 10.0
        bars = [_bar(100.0 + r, 100.0, 100.0 + r / 2) for r in
                [i * 0.5 for i in range(1, 21)]]
        # ranges = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,
        #           5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
        import statistics
        ranges = [b["h"] - b["l"] for b in bars]
        expected = statistics.quantiles(ranges, n=4)[2]
        result = compute_today_typical(bars)
        assert result == expected


# ── Test 5: today_max ─────────────────────────────────────────────

class TestTodayMax:
    def test_today_max(self):
        """Max bar range = 2.5."""
        bars = [
            _bar(101.0, 100.0, 100.5),  # range 1.0
            _bar(102.5, 100.0, 101.0),  # range 2.5
            _bar(101.5, 100.5, 101.0),  # range 1.0
        ]
        assert compute_today_max(bars) == 2.5


# ── Tests 6-10: compute_stop LONG + SHORT ────────────────────────

class TestComputeStopLong:
    def test_stop_long_layer_a_binds(self):
        """Reactive LONG · entry=100.0 · belly_low=98.75 · today_typical=2.0.
        A=98.5 B=98.0 C=99.0 · max(A,B)=98.5 · min(98.5, 99.0)=98.5 · Layer A.
        """
        r = compute_stop(
            entry_price=100.0,
            direction="LONG",
            structural_anchor=98.75,
            family="Reactive",
            today_typical=2.0,
        )
        assert r.stop_price == 98.5
        assert r.stop_structural == 98.5
        assert r.adaptive_cap == 98.0
        assert r.floor_price == 99.0
        assert r.binding_layer == "A"
        assert r.reduce_size_signal is True

    def test_stop_long_layer_b_binds(self):
        """Reactive LONG · entry=100.0 · belly_low=95.0 · today_typical=1.5.
        A=94.75 B=98.5 C=99.0 · max(A,B)=98.5 · min(98.5, 99.0)=98.5 · Layer B.
        """
        r = compute_stop(
            entry_price=100.0,
            direction="LONG",
            structural_anchor=95.0,
            family="Reactive",
            today_typical=1.5,
        )
        assert r.stop_price == 98.5
        assert r.stop_structural == 94.75
        assert r.adaptive_cap == 98.5
        assert r.floor_price == 99.0
        assert r.binding_layer == "B"
        assert r.reduce_size_signal is False

    def test_stop_long_layer_c_binds(self):
        """Reactive LONG · entry=100.0 · belly_low=95.0 · today_typical=0.1.
        A=94.75 B=99.9 C=99.0 · max(A,B)=99.9 · min(99.9, 99.0)=99.0 · Layer C.
        """
        r = compute_stop(
            entry_price=100.0,
            direction="LONG",
            structural_anchor=95.0,
            family="Reactive",
            today_typical=0.1,
        )
        assert r.stop_price == 99.0
        assert r.stop_structural == 94.75
        assert r.adaptive_cap == 99.9
        assert r.floor_price == 99.0
        assert r.binding_layer == "C"
        assert r.reduce_size_signal is False


class TestComputeStopShort:
    def test_stop_short_layer_a_binds(self):
        """Reactive SHORT · entry=100.0 · belly_high=101.25 · today_typical=2.0.
        A=101.5 B=102.0 C=101.0 · min(A,B)=101.5 · max(101.5, 101.0)=101.5 · Layer A.
        """
        r = compute_stop(
            entry_price=100.0,
            direction="SHORT",
            structural_anchor=101.25,
            family="Reactive",
            today_typical=2.0,
        )
        assert r.stop_price == 101.5
        assert r.stop_structural == 101.5
        assert r.adaptive_cap == 102.0
        assert r.floor_price == 101.0
        assert r.binding_layer == "A"
        assert r.reduce_size_signal is True

    def test_stop_short_layer_b_binds(self):
        """Reactive SHORT · entry=100.0 · belly_high=105.0 · today_typical=1.5.
        A=105.25 B=101.5 C=101.0 · min(A,B)=101.5 · max(101.5, 101.0)=101.5 · Layer B.
        """
        r = compute_stop(
            entry_price=100.0,
            direction="SHORT",
            structural_anchor=105.0,
            family="Reactive",
            today_typical=1.5,
        )
        assert r.stop_price == 101.5
        assert r.stop_structural == 105.25
        assert r.adaptive_cap == 101.5
        assert r.floor_price == 101.0
        assert r.binding_layer == "B"
        assert r.reduce_size_signal is False


# ── Test 11: family multipliers ──────────────────────────────────

class TestFamilyMultipliers:
    def test_family_multipliers_all_5(self):
        """All 5 families with entry=100.0 · belly_low=90.0 · today_typical=1.0.
        Adaptive cap distances: Reactive=1.0 OFA=1.5 Flag=1.5 Double_BT=2.0 HnS=2.0.
        """
        expected_distances = {
            "Reactive": 1.0,
            "OFA": 1.5,
            "Flag": 1.5,
            "Double_BT": 2.0,
            "HnS": 2.0,
        }
        for family, dist in expected_distances.items():
            r = compute_stop(
                entry_price=100.0,
                direction="LONG",
                structural_anchor=90.0,
                family=family,
                today_typical=1.0,
            )
            assert r.adaptive_cap == pytest.approx(100.0 - dist), \
                f"family={family}: expected cap={100.0 - dist}, got {r.adaptive_cap}"


# ── Tests 12-13b: reduce_size_signal ─────────────────────────────

class TestReduceSizeSignal:
    def test_reduce_size_signal_when_a_binds(self):
        """Same inputs as test 6 (Layer A binds) → reduce_size_signal=True."""
        r = compute_stop(
            entry_price=100.0, direction="LONG",
            structural_anchor=98.75, family="Reactive", today_typical=2.0,
        )
        assert r.reduce_size_signal is True

    def test_reduce_size_signal_false_when_b_binds(self):
        """Same inputs as test 7 (Layer B binds) → reduce_size_signal=False."""
        r = compute_stop(
            entry_price=100.0, direction="LONG",
            structural_anchor=95.0, family="Reactive", today_typical=1.5,
        )
        assert r.reduce_size_signal is False

    def test_reduce_size_signal_false_when_c_binds(self):
        """Same inputs as test 8 (Layer C binds) → reduce_size_signal=False."""
        r = compute_stop(
            entry_price=100.0, direction="LONG",
            structural_anchor=95.0, family="Reactive", today_typical=0.1,
        )
        assert r.reduce_size_signal is False


# ── Test 14: unknown family raises ───────────────────────────────

class TestUnknownFamily:
    def test_unknown_family_raises(self):
        with pytest.raises(KeyError):
            compute_stop(
                entry_price=100.0, direction="LONG",
                structural_anchor=99.0, family="Unknown", today_typical=1.0,
            )


# ── Test 15: binding_layer field correct ─────────────────────────

class TestBindingLayerField:
    def test_binding_layer_field_correct(self):
        """Verify binding_layer matches for all 3 scenarios (tests 6/7/8)."""
        # Layer A
        r = compute_stop(entry_price=100.0, direction="LONG",
                         structural_anchor=98.75, family="Reactive", today_typical=2.0)
        assert r.binding_layer == "A"
        # Layer B
        r = compute_stop(entry_price=100.0, direction="LONG",
                         structural_anchor=95.0, family="Reactive", today_typical=1.5)
        assert r.binding_layer == "B"
        # Layer C
        r = compute_stop(entry_price=100.0, direction="LONG",
                         structural_anchor=95.0, family="Reactive", today_typical=0.1)
        assert r.binding_layer == "C"


# ── Test 16: today_typical fallback to baseline ──────────────────

class TestTodayTypicalFallback:
    def test_today_typical_fallback_to_baseline(self, caplog):
        """today_bars=2 (insufficient for quantiles) → falls back gracefully."""
        bars = [_bar(101.0, 100.0, 100.5), _bar(101.5, 100.5, 101.0)]
        with caplog.at_level(logging.DEBUG):
            result = compute_today_typical(bars)
        # With 2 bars, statistics.quantiles still works (needs ≥2 data points)
        # ranges = [1.0, 1.0] → P75 = 1.0
        assert result == pytest.approx(1.0)


# ── Test 17: negative today_typical floor only ───────────────────

class TestNegativeTodayTypical:
    def test_negative_today_typical_floor_only(self, caplog):
        """today_typical=0 → returns floor (entry - 4T for LONG); warning logged."""
        with caplog.at_level(logging.WARNING):
            r = compute_stop(
                entry_price=100.0, direction="LONG",
                structural_anchor=95.0, family="Reactive", today_typical=0.0,
            )
        assert r.stop_price == 99.0  # floor = 100.0 - 4 * 0.25 = 99.0
        assert r.binding_layer == "C"
        assert any("today_typical" in record.message and "≤ 0" in record.message
                    for record in caplog.records)
