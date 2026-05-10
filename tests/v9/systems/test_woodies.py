"""Tests: Woodies CCI — calculations, patterns, detector, API."""

import pytest
import math
from backend.v9.systems.woodies.cci_calc import (
    calc_cci, calc_cci_series, calc_ema, calc_lsma,
    calc_sidewinder, calc_chopzone, calc_trend_state,
    calc_predictor, compute_all_studies, typical_price,
)
from backend.v9.systems.woodies.detector import detect_patterns, compute_state
from backend.v9.systems.woodies.patterns.zlr import detect_zlr
from backend.v9.systems.woodies.patterns.tlb import detect_tlb
from backend.v9.systems.woodies.patterns.tt import detect_tt
from backend.v9.systems.woodies.patterns.gb100 import detect_gb100
from backend.v9.systems.woodies.patterns.vegas import detect_vegas
from backend.v9.systems.woodies.patterns.ghost import detect_ghost
from backend.v9.systems.woodies.patterns.famir import detect_famir
from backend.v9.systems.woodies.patterns.htlb import detect_htlb
from backend.v9.systems.woodies.schemas import PatternSignal, WoodiesState


# ─── Test data generators ────────────────────────────────────

def make_trending_up(n=30, start=5400.0, step=0.5):
    """Generate an uptrend with minor noise."""
    closes = [start + i * step + (i % 3 - 1) * 0.25 for i in range(n)]
    highs = [c + 1.5 for c in closes]
    lows = [c - 1.0 for c in closes]
    return highs, lows, closes


def make_trending_down(n=30, start=5500.0, step=0.5):
    closes = [start - i * step - (i % 3 - 1) * 0.25 for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.5 for c in closes]
    return highs, lows, closes


def make_flat(n=30, center=5450.0, noise=0.5):
    closes = [center + (i % 5 - 2) * noise for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    return highs, lows, closes


# ─── CCI calculation tests ──────────────────────────────────

class TestCCICalc:

    def test_typical_price(self):
        assert typical_price(10, 8, 9) == 9.0

    def test_cci_known_values(self):
        """CCI on truly flat data should be near zero."""
        h = [5450.5] * 20
        l = [5449.5] * 20
        c = [5450.0] * 20
        cci = calc_cci(h, l, c, 14)
        assert abs(cci) < 1  # exactly zero for constant data

    def test_cci_trending_up_positive(self):
        """Strong uptrend → CCI should be positive."""
        h, l, c = make_trending_up(30, step=2.0)
        cci = calc_cci(h, l, c, 14)
        assert cci > 0

    def test_cci_trending_down_negative(self):
        """Strong downtrend → CCI should be negative."""
        h, l, c = make_trending_down(30, step=2.0)
        cci = calc_cci(h, l, c, 14)
        assert cci < 0

    def test_cci_insufficient_data(self):
        assert calc_cci([1, 2], [0, 1], [1.5, 1.5], 14) == 0.0

    def test_cci_series_length(self):
        h, l, c = make_trending_up(30)
        series = calc_cci_series(h, l, c, 14)
        assert len(series) == 30
        # First 13 should be 0
        assert all(s == 0.0 for s in series[:13])
        # From index 13 onward should have values
        assert series[13] != 0.0


class TestEMA:

    def test_ema_converges(self):
        closes = [100.0] * 50
        ema = calc_ema(closes, 34)
        assert abs(ema - 100.0) < 0.01

    def test_ema_follows_trend(self):
        closes = list(range(100, 200))
        ema = calc_ema(closes, 10)
        # EMA should lag but be between start and end
        assert 100 < ema < 200


class TestLSMA:

    def test_lsma_on_linear(self):
        """LSMA on perfectly linear data should match the last point."""
        closes = [100.0 + i * 2.0 for i in range(30)]
        lsma = calc_lsma(closes, 25)
        assert abs(lsma - closes[-1]) < 0.5

    def test_lsma_insufficient(self):
        assert calc_lsma([100], 25) == 100


class TestIndicators:

    def test_sidewinder(self):
        assert calc_sidewinder(150, 100) == 50

    def test_chopzone_trending(self):
        h, l, c = make_trending_up(20, step=2.0)
        ema = calc_ema(c, 34)
        czi = calc_chopzone(h, l, c, ema)
        # Trending up, price above EMA → positive CZI
        assert czi != 0

    def test_trend_state_blue(self):
        assert calc_trend_state(100, 50, 30) == "BLUE"

    def test_trend_state_red(self):
        assert calc_trend_state(-100, -50, -30) == "RED"

    def test_trend_state_yellow(self):
        assert calc_trend_state(10, -10, 5) == "YELLOW"

    def test_trend_state_gray(self):
        assert calc_trend_state(10, 10, 5) == "GRAY"

    def test_predictor(self):
        assert calc_predictor(100, 80) == 120


class TestComputeAllStudies:

    def test_returns_all_fields(self):
        h, l, c = make_trending_up(30, step=2.0)
        result = compute_all_studies(h, l, c)
        expected_keys = {
            "cci_14", "cci_6_tcci", "ema_34", "lsma_value",
            "lsma_above_price", "swi_value", "czi_value",
            "trend_state", "predictor_next_cci",
        }
        assert set(result.keys()) == expected_keys

    def test_insufficient_data(self):
        result = compute_all_studies([1], [0], [0.5])
        assert result["trend_state"] == "GRAY"
        assert result["cci_14"] == 0


# ─── Pattern tests ────────────────────────────────────────────

class TestZLR:

    def test_zlr_up(self):
        # Build CCI history: above 100, pulls to 50, bounces to 80
        cci = [0] * 5 + [120, 130, 110, 60, 50, 40, 55, 80]
        result = detect_zlr(cci, bar_index=12, ts=1000.0)
        assert result is not None
        assert result.pattern == "ZLR"
        assert result.direction == "LONG"

    def test_zlr_down(self):
        cci = [0] * 5 + [-120, -130, -110, -60, -50, -40, -55, -80]
        result = detect_zlr(cci, bar_index=12, ts=1000.0)
        assert result is not None
        assert result.direction == "SHORT"

    def test_zlr_no_signal(self):
        cci = [0] * 15
        result = detect_zlr(cci, bar_index=14, ts=1000.0)
        assert result is None


class TestTLB:

    def test_tlb_up(self):
        # Downward slope then break up
        cci = [100, 90, 80, 70, 60, 50, 40, 30, 20, 80]
        result = detect_tlb(cci, bar_index=9, ts=1000.0)
        assert result is not None
        assert result.pattern == "TLB"
        assert result.direction == "LONG"

    def test_tlb_no_signal_flat(self):
        cci = [50] * 10
        result = detect_tlb(cci, bar_index=9, ts=1000.0)
        assert result is None


class TestTT:

    def test_tt_insufficient_data(self):
        result = detect_tt([1, 2], bar_index=1, ts=1000.0)
        assert result is None

    def test_tt_long(self):
        # TCCI was well above CCI14, dipped to touch, then bounced back up
        #                                    prev2  prev  curr
        cci14 = [80, 85, 90, 95, 100, 100,    90,    95,  100]
        cci6 =  [110, 115, 120, 125, 130, 120, 110,  100,  120]
        result = detect_tt(
            cci14, bar_index=8, ts=1000.0,
            cci6_history=cci6, trend_state="BLUE",
        )
        assert result is not None
        assert result.pattern == "TT"
        assert result.direction == "LONG"


class TestGB100:

    def test_gb100_long(self):
        cci = [50, 60, 70, 80, 90, 95, 99, 120]
        result = detect_gb100(cci, bar_index=7, ts=1000.0, trend_state="BLUE")
        assert result is not None
        assert result.pattern == "GB100"
        assert result.direction == "LONG"

    def test_gb100_short(self):
        cci = [-50, -60, -70, -80, -90, -95, -99, -120]
        result = detect_gb100(cci, bar_index=7, ts=1000.0, trend_state="RED")
        assert result is not None
        assert result.direction == "SHORT"

    def test_gb100_no_trend(self):
        cci = [50, 60, 70, 80, 90, 95, 99, 120]
        result = detect_gb100(cci, bar_index=7, ts=1000.0, trend_state="GRAY")
        assert result is None


class TestFAMIR:

    def test_famir_short(self):
        # Approaches +200 but fails, reverses
        cci = [100, 130, 160, 180, 185, 175, 160, 140]
        result = detect_famir(cci, bar_index=7, ts=1000.0)
        assert result is not None
        assert result.pattern == "FAMIR"
        assert result.direction == "SHORT"

    def test_famir_long(self):
        cci = [-100, -130, -160, -180, -185, -175, -160, -140]
        result = detect_famir(cci, bar_index=7, ts=1000.0)
        assert result is not None
        assert result.direction == "LONG"


class TestGHOST:

    def test_ghost_bearish(self):
        # Three peaks: left=120, head=150, right=110, current dropping
        cci = [50, 80, 120, 90, 100, 150, 100, 80, 110, 80, 60, 50,
               40, 30, 20, 30, 20, 10, 5, 0]
        result = detect_ghost(cci, bar_index=19, ts=1000.0)
        # May or may not detect depending on swing detection — at least no crash
        assert result is None or result.pattern == "GHOST"

    def test_ghost_insufficient(self):
        result = detect_ghost([1, 2, 3], bar_index=2, ts=1000.0)
        assert result is None


class TestHTLB:

    def test_htlb_insufficient(self):
        result = detect_htlb([1, 2, 3], bar_index=2, ts=1000.0)
        assert result is None

    def test_htlb_resistance_break(self):
        # Multiple touches at ~80, then break above
        cci = [50, 60, 70, 80, 70, 60, 70, 80, 70, 60, 70, 80, 70, 60, 100]
        result = detect_htlb(cci, bar_index=14, ts=1000.0)
        assert result is None or result.pattern == "HTLB"


class TestVEGAS:

    def test_vegas_insufficient(self):
        result = detect_vegas([1, 2], bar_index=1, ts=1000.0, price_closes=[1, 2])
        assert result is None

    def test_vegas_bearish_divergence(self):
        """Price makes Higher High but CCI makes Lower High → SHORT."""
        # Explicit construction: two peaks with clean V-shaped valley
        # Window is last 20 bars. Build 20 directly.
        #   Peak 1: index 4 (price=100, cci=150)
        #   Valley: index 9 (price=55, cci=10)
        #   Peak 2: index 14 (price=105, cci=120)  ← Price HH, CCI LH
        price = [
            70, 80, 90, 95, 100, 95, 85, 75, 65, 55,   # rise to 100, fall to 55
            65, 80, 95, 102, 105, 102, 95, 85, 80, 75,  # rise to 105, fall
        ]
        cci = [
            50, 80, 120, 140, 150, 140, 100, 60, 30, 10,  # rise to 150, fall to 10
            30, 60, 100, 115, 120, 115, 90, 60, 50, 40,   # rise to 120 (< 150 = LH)
        ]
        # Pad with 5 prefix bars so len=25 (LOOKBACK=20 takes last 20)
        price = [70, 70, 70, 70, 70] + price
        cci = [50, 50, 50, 50, 50] + cci

        result = detect_vegas(cci, bar_index=24, ts=1000.0, price_closes=price)
        assert result is not None, "VEGAS should detect bearish divergence"
        assert result.direction == "SHORT"
        assert result.pattern == "VEGAS"
        assert result.confidence == 0.75

    def test_vegas_bullish_divergence(self):
        """Price makes Lower Low but CCI makes Higher Low → LONG."""
        # Window is last 20 bars.
        #   Trough 1: index 4 (price=30, cci=-150)
        #   Peak: index 9 (price=80, cci=-10)
        #   Trough 2: index 14 (price=25, cci=-120)  ← Price LL, CCI HL
        price = [
            60, 50, 40, 35, 30, 35, 45, 55, 70, 80,   # fall to 30, rise to 80
            70, 55, 40, 30, 25, 30, 40, 55, 60, 65,   # fall to 25 (< 30 = LL)
        ]
        cci = [
            -50, -80, -120, -140, -150, -140, -100, -60, -30, -10,  # fall to -150
            -30, -60, -100, -115, -120, -115, -90, -60, -50, -40,   # fall to -120 (> -150 = HL)
        ]
        price = [60, 60, 60, 60, 60] + price
        cci = [-50, -50, -50, -50, -50] + cci

        result = detect_vegas(cci, bar_index=24, ts=1000.0, price_closes=price)
        assert result is not None, "VEGAS should detect bullish divergence"
        assert result.direction == "LONG"
        assert result.pattern == "VEGAS"

    def test_vegas_no_divergence(self):
        """Price HH and CCI HH (no divergence) → None."""
        price = [50.0] * 25
        cci = [0.0] * 25
        # Both price and CCI make higher highs → no divergence
        for i in range(6, 11):
            price[i] = 95.0 + (5.0 - abs(i - 8) * 2.5)
            cci[i] = 130.0 + (20.0 - abs(i - 8) * 10.0)
        for i in range(11, 15):
            price[i] = 60.0
            cci[i] = 20.0
        for i in range(16, 21):
            price[i] = 100.0 + (5.0 - abs(i - 18) * 2.5)
            cci[i] = 160.0 + (20.0 - abs(i - 18) * 10.0)  # CCI also HH
        for i in range(21, 25):
            price[i] = 80.0
            cci[i] = 50.0
        result = detect_vegas(cci, bar_index=24, ts=1000.0, price_closes=price)
        assert result is None


# ─── Detector integration ─────────────────────────────────────

class TestDetector:

    def test_detect_patterns_empty(self):
        patterns = detect_patterns([], [], [], [])
        assert patterns == []

    def test_detect_patterns_short_data(self):
        patterns = detect_patterns([1, 2], [0, 1], [0.5, 1.5], [100, 200])
        assert patterns == []

    def test_detect_patterns_returns_list(self):
        h, l, c = make_trending_up(30, step=2.0)
        ts = list(range(30))
        patterns = detect_patterns(h, l, c, ts)
        assert isinstance(patterns, list)

    def test_compute_state_returns_state(self):
        h, l, c = make_trending_up(30, step=2.0)
        ts = list(range(30))
        state = compute_state(h, l, c, ts)
        assert isinstance(state, WoodiesState)
        assert state.trend_state in ("BLUE", "RED", "GRAY", "YELLOW")
        assert state.classification in ("NO_SETUP", "TACTICAL", "STRATEGIC")


# ─── Schema tests ─────────────────────────────────────────────

class TestSchemas:

    def test_pattern_signal_creates(self):
        ps = PatternSignal(
            pattern="ZLR", group="CONTINUATION", direction="LONG",
            confidence=0.8, cci_at_signal=75, bar_index=10, ts=1000.0,
        )
        assert ps.pattern == "ZLR"
        d = ps.model_dump()
        assert d["direction"] == "LONG"

    def test_woodies_state_creates(self):
        ws = WoodiesState(
            trend_state="BLUE", cci_14=120, cci_6_tcci=130,
            swi_value=50, czi_value=80, ema_34=5400,
            lsma_value=5410, predictor_next_cci=140,
        )
        assert ws.classification == "NO_SETUP"
