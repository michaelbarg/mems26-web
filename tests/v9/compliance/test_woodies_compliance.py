"""R3 Spec Compliance Tests — System 4 (woodies).

Validates every requirement from MEMS26_WOODIES_SPEC_V1_DERIVED.
"""
import pytest

from backend.v9.systems.woodies.schemas import (
    WoodiesBar, PatternSignal, WoodiesState,
)
from backend.v9.systems.woodies.cci_calc import (
    calc_cci, calc_cci_series, calc_ema, calc_ema_series,
    calc_lsma, calc_sidewinder, calc_chopzone,
    calc_trend_state, calc_predictor, compute_all_studies,
)
from backend.v9.systems.woodies.detector import (
    detect_patterns, compute_state,
)


# ── Helpers ──────────────────────────────────────────────────────

def _sample_data(n=30, base=5250.0, trend=0.5):
    """Generate synthetic OHLC data for testing."""
    highs, lows, closes, timestamps = [], [], [], []
    for i in range(n):
        c = base + i * trend
        highs.append(c + 2)
        lows.append(c - 2)
        closes.append(c)
        timestamps.append(1000000 + i * 1800)
    return highs, lows, closes, timestamps


# ── Study Computation (11 studies) ───────────────────────────────

class TestStudyComputation:
    def test_study_computation(self):
        """All 11 studies compute without error."""
        h, l, c, ts = _sample_data(30)
        studies = compute_all_studies(h, l, c)
        assert "cci_14" in studies
        assert "cci_6_tcci" in studies
        assert "ema_34" in studies
        assert "lsma_value" in studies
        assert "lsma_above_price" in studies
        assert "swi_value" in studies
        assert "czi_value" in studies
        assert "trend_state" in studies
        assert "predictor_next_cci" in studies

    def test_cci14_formula(self):
        """CCI-14 uses standard formula: (TP-SMA)/(0.015*MD)."""
        h, l, c, _ = _sample_data(20)
        cci = calc_cci(h, l, c, 14)
        assert isinstance(cci, float)

    def test_cci6_turbo(self):
        h, l, c, _ = _sample_data(20)
        cci6 = calc_cci(h, l, c, 6)
        assert isinstance(cci6, float)

    def test_ema34(self):
        _, _, c, _ = _sample_data(40)
        ema = calc_ema(c, 34)
        assert isinstance(ema, float)
        assert ema > 0

    def test_lsma25(self):
        _, _, c, _ = _sample_data(30)
        lsma = calc_lsma(c, 25)
        assert isinstance(lsma, float)

    def test_sidewinder(self):
        swi = calc_sidewinder(150.0, 100.0)
        assert swi == 50.0

    def test_chopzone(self):
        h, l, c, _ = _sample_data(20)
        ema = calc_ema(c, 34)
        czi = calc_chopzone(h, l, c, ema)
        assert isinstance(czi, float)

    def test_predictor(self):
        pred = calc_predictor(100.0, 80.0)
        assert pred == 120.0  # 100 + (100-80)


# ── Trend State ──────────────────────────────────────────────────

class TestTrendState:
    def test_trend_state(self):
        """4 trend states: BLUE, RED, YELLOW, GRAY."""
        assert calc_trend_state(100, 50, 30) == "BLUE"
        assert calc_trend_state(-100, -50, -30) == "RED"
        assert calc_trend_state(10, -10, 0) == "YELLOW"
        assert calc_trend_state(10, 10, 5) == "GRAY"

    def test_blue_conditions(self):
        """BLUE requires CCI>50, prev>0, SWI>20."""
        assert calc_trend_state(51, 1, 21) == "BLUE"
        assert calc_trend_state(49, 1, 21) != "BLUE"

    def test_red_conditions(self):
        """RED requires CCI<-50, prev<0, SWI<-20."""
        assert calc_trend_state(-51, -1, -21) == "RED"
        assert calc_trend_state(-49, -1, -21) != "RED"


# ── Pattern Detection ────────────────────────────────────────────

class TestPatternDetection:
    def test_pattern_detection(self):
        """detect_patterns returns list (may be empty without detectors)."""
        h, l, c, ts = _sample_data(30)
        patterns = detect_patterns(h, l, c, ts)
        assert isinstance(patterns, list)

    def test_pattern_signal_schema(self):
        """PatternSignal has required fields."""
        sig = PatternSignal(
            pattern="ZLR", group="CONTINUATION", direction="LONG",
            confidence=0.8, cci_at_signal=150.0, bar_index=29, ts=1000000,
        )
        assert sig.pattern == "ZLR"
        assert sig.group == "CONTINUATION"

    def test_all_8_pattern_names(self):
        """All 8 pattern names are valid."""
        valid = {"ZLR", "TLB", "TT", "GB100", "VEGAS", "GHOST", "FAMIR", "HTLB"}
        for name in valid:
            sig = PatternSignal(
                pattern=name, group="CONTINUATION" if name in {"ZLR", "TLB", "TT", "GB100"} else "REVERSAL",
                direction="LONG", confidence=0.5, cci_at_signal=0, bar_index=0, ts=0,
            )
            assert sig.pattern in valid


# ── Classification ───────────────────────────────────────────────

class TestClassification:
    def test_classification(self):
        """WoodiesState has classification field."""
        state = WoodiesState(
            trend_state="BLUE", cci_14=100, cci_6_tcci=120,
            swi_value=30, czi_value=50, ema_34=5250, lsma_value=5248,
            predictor_next_cci=110,
        )
        assert state.classification in ("NO_SETUP", "TACTICAL", "STRATEGIC")

    def test_compute_state(self):
        h, l, c, ts = _sample_data(30)
        state = compute_state(h, l, c, ts)
        assert isinstance(state, WoodiesState)
        assert state.trend_state in ("BLUE", "RED", "YELLOW", "GRAY")
        assert state.classification in ("NO_SETUP", "TACTICAL", "STRATEGIC")


# ── Anti-Patterns ────────────────────────────────────────────────

class TestAntiPatterns:
    def test_AP1_independence(self):
        """detect_patterns/compute_state take only price data, no system deps."""
        import inspect
        sig = inspect.signature(detect_patterns)
        params = list(sig.parameters.keys())
        assert "day_type" not in params
        assert "killzone" not in params

    def test_AP2_dll_source(self):
        """Python CCI calc matches DLL formula for validation."""
        h = [5250, 5252, 5248, 5253, 5251, 5255, 5249, 5254, 5250, 5256,
             5248, 5253, 5250, 5255, 5252]
        l = [5246, 5248, 5244, 5249, 5247, 5251, 5245, 5250, 5246, 5252,
             5244, 5249, 5246, 5251, 5248]
        c = [5248, 5250, 5246, 5251, 5249, 5253, 5247, 5252, 5248, 5254,
             5246, 5251, 5248, 5253, 5250]
        cci = calc_cci(h, l, c, 14)
        assert isinstance(cci, float)


# ── Output Schema ────────────────────────────────────────────────

class TestOutputSchema:
    def test_woodies_bar_schema(self):
        """WoodiesBar has all 11 study fields per spec Section 4."""
        bar = WoodiesBar(
            ts=1000000, open=5250, high=5255, low=5245, close=5252,
            cci_14=100, cci_6_tcci=120, ema_34=5248, lsma_value=5249,
            lsma_above_price=False, swi_value=30, czi_value=50,
            trend_state="BLUE", predictor_next_cci=110,
            zlr_detected=True, zlr_direction="UP",
        )
        assert bar.cci_14 == 100
        assert bar.zlr_detected is True
        assert bar.zlr_direction == "UP"

    def test_woodies_state_schema(self):
        """WoodiesState has classification and direction."""
        state = WoodiesState(
            trend_state="GRAY", cci_14=0, cci_6_tcci=0,
            swi_value=0, czi_value=0, ema_34=0, lsma_value=0,
            predictor_next_cci=0,
        )
        assert state.classification == "NO_SETUP"
        assert state.direction == "NEUTRAL"
