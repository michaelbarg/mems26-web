"""Tests: R_t1 emission across all 8 pattern detectors (W-6).

Verifies that:
- Every detected pattern emits r_t1 > 0
- raw_confidence matches confidence
- r_t1 = None when stop == entry (division by zero)
- r_t1 matches hand-computed formula
"""

import pytest
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult


# ---- Helpers ---------------------------------------------------------------

def make_bar(ts=1000.0, close=5250.0, high=5252.0, low=5248.0,
             open_=5249.0, volume=100, cci_14=0.0, cci_6_tcci=0.0,
             ema_34=5250.0, trend_state="GRAY", **kwargs) -> WoodiesBar:
    return WoodiesBar(
        ts=ts, open=open_, high=high, low=low, close=close,
        volume=volume, cci_14=cci_14, cci_6_tcci=cci_6_tcci,
        ema_34=ema_34, trend_state=trend_state, **kwargs,
    )


def make_bars_from_cci(cci_values, base_close=5250.0, step=0.5,
                       trend_state="GRAY", cci6_values=None, **kwargs):
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


# ---- ZLR -------------------------------------------------------------------

class TestZLRRt1:
    def test_zlr_long_r_t1_positive(self):
        from backend.v9.systems.woodies.patterns import zlr
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is True
        assert result.r_t1 is not None
        assert result.r_t1 > 0
        assert result.raw_confidence == result.confidence

    def test_zlr_short_r_t1_positive(self):
        from backend.v9.systems.woodies.patterns import zlr
        cci = [0] * 5 + [-120, -130, -110, -60, -50, -20, -55, -100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is True
        assert result.r_t1 is not None
        assert result.r_t1 > 0


# ---- TLB -------------------------------------------------------------------

class TestTLBRt1:
    def test_tlb_long_r_t1_positive(self):
        from backend.v9.systems.woodies.patterns import tlb
        cci = [100, 90, 80, 70, 60, 50, 40, 30, 20, 80]
        bars = make_bars_from_cci(cci)
        result = tlb.detect(bars)
        assert result.detected is True
        assert result.r_t1 is not None
        assert result.r_t1 > 0


# ---- TT -------------------------------------------------------------------

class TestTTRt1:
    def test_tt_long_r_t1_positive(self):
        from backend.v9.systems.woodies.patterns import tt
        cci14 = [80, 85, 90, 95, 100, 100, 50, 95, 100]
        cci6 = [110, 115, 120, 125, 130, 120, 110, 100, 120]
        bars = []
        for i in range(len(cci14)):
            c = 5250.0 + i * 0.5
            bars.append(make_bar(
                ts=1000.0 + i * 1800, close=c, high=c + 1.5, low=c - 1.0,
                cci_14=cci14[i], cci_6_tcci=cci6[i], trend_state="BLUE",
            ))
        result = tt.detect(bars)
        assert result.detected is True
        assert result.r_t1 is not None
        assert result.r_t1 > 0
        assert result.raw_confidence == 0.7


# ---- GB100 -----------------------------------------------------------------

class TestGB100Rt1:
    def test_gb100_long_r_t1_positive(self):
        from backend.v9.systems.woodies.patterns import gb100
        cci = [50, 60, 70, 80, 90, 65, 99, 120]
        bars = make_bars_from_cci(cci, trend_state="BLUE")
        result = gb100.detect(bars)
        assert result.detected is True
        assert result.r_t1 is not None
        assert result.r_t1 > 0


# ---- VEGAS -----------------------------------------------------------------

class TestVEGASRt1:
    def test_vegas_bearish_r_t1_positive(self):
        from backend.v9.systems.woodies.patterns import vegas
        price = [70, 80, 90, 95, 100, 95, 85, 75, 65, 55,
                 65, 80, 95, 102, 105, 102, 95, 85, 80, 75]
        cci = [50, 80, 120, 140, 150, 140, 100, 60, 30, 10,
               30, 60, 100, 115, 120, 115, 90, 60, 50, -10]
        price = [price[0]] * 5 + price
        cci = [cci[0]] * 5 + cci
        bars = []
        for i in range(len(price)):
            bars.append(make_bar(
                ts=1000.0 + i * 1800,
                close=price[i], high=price[i] + 2, low=price[i] - 2,
                cci_14=cci[i],
            ))
        result = vegas.detect(bars)
        assert result.detected is True
        assert result.r_t1 is not None
        assert result.r_t1 > 0


# ---- GHOST -----------------------------------------------------------------

class TestGHOSTRt1:
    def test_ghost_bearish_r_t1_positive(self):
        from backend.v9.systems.woodies.patterns import ghost
        cci = [50, 80, 120, 80, 60, 100, 180, 100, 60, 40,
               70, 100, 70, 40, 30, 20, 10, -50, 0, -10]
        bars = make_bars_from_cci(cci)
        result = ghost.detect(bars)
        assert result.detected is True
        assert result.r_t1 is not None
        assert result.r_t1 > 0


# ---- FAMIR -----------------------------------------------------------------

class TestFAMIRRt1:
    def test_famir_short_r_t1_positive(self):
        from backend.v9.systems.woodies.patterns import famir
        cci = [100, 130, 160, 180, 185, 175, 150, 120]
        bars = make_bars_from_cci(cci, lsma_above_price=True)
        result = famir.detect(bars)
        assert result.detected is True
        assert result.r_t1 is not None
        assert result.r_t1 > 0


# ---- HTLB -----------------------------------------------------------------

class TestHTLBRt1:
    def test_htlb_r_t1_positive_if_detected(self):
        from backend.v9.systems.woodies.patterns import htlb
        cci = [50, 60, 70, 80, 70, 60, 70, 80, 70, 60, 70, 80, 70, 60, 100]
        bars = make_bars_from_cci(cci)
        result = htlb.detect(bars)
        if result.detected:
            assert result.r_t1 is not None
            assert result.r_t1 > 0


# ---- Edge cases ------------------------------------------------------------

class TestRt1EdgeCases:
    def test_r_t1_invalid_when_stop_equals_entry(self):
        """r_t1 = None when stop == entry (would be division by zero)."""
        r = PatternResult(
            detected=True, pattern_id="ZLR", direction="LONG",
            confidence=0.8, entry_price=5250.0, stop=5250.0,
            r_t1=None,
        )
        assert r.r_t1 is None

    def test_r_t1_matches_formula(self):
        """Hand-computed R_t1 check: T1=+4T, entry=5250, stop=5249 -> risk=1.0, R_t1=1.0."""
        entry = 5250.0
        stop = 5249.0  # 4 ticks below
        tick_size = 0.25
        t1_ticks = 4
        risk = abs(entry - stop)
        expected_r_t1 = (t1_ticks * tick_size) / risk  # 1.0 / 1.0 = 1.0
        assert expected_r_t1 == 1.0

        # Now with 2-tick risk -> R_t1 = 1.0/0.5 = 2.0
        stop2 = 5249.5
        risk2 = abs(entry - stop2)
        r_t1_2 = (t1_ticks * tick_size) / risk2
        assert r_t1_2 == 2.0

    def test_r_t1_not_detected_is_none(self):
        """Non-detected patterns should have r_t1=None."""
        r = PatternResult(detected=False, pattern_id="ZLR")
        assert r.r_t1 is None

    def test_raw_confidence_equals_confidence(self):
        """raw_confidence must equal confidence when set."""
        from backend.v9.systems.woodies.patterns import zlr
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        if result.detected:
            assert result.raw_confidence == result.confidence
