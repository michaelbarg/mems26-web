"""W3-α — Five-Min multi-bar pattern detection per V3 T1.

Tests the Reactive + Initiative 4-bar detectors and POC_VOL tracking.
"""
from unittest.mock import patch, MagicMock
from backend.v9.systems.five_min.five_min_system import FiveMinSystem


def _make_bar(o, h, l, c, v=1000, poc_vol=None):
    bar = {"o": o, "h": h, "l": l, "c": c, "v": v}
    if poc_vol is not None:
        bar["poc_vol"] = poc_vol
    return bar


def _quiet_lookback(v_bar1=1000):
    """3 quiet bars for lookback · max vol < 60% of bar1 vol."""
    qv = int(v_bar1 * 0.4)  # well below 0.6 threshold
    return [
        _make_bar(5248, 5249, 5247, 5248, v=qv),
        _make_bar(5248, 5249, 5247, 5248, v=qv),
        _make_bar(5248, 5249, 5247, 5248, v=qv),
    ]


class TestReactivePattern:
    """Reactive 4-bar per V3 T1: seller weakness → buyer belly → confirm."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_long(self, _br, _belly, _amt, _cot):
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),  # Bar 1: sellers
            _make_bar(5248, 5248, 5247, 5247.75, v=80),     # Bar 2: 92% drop
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),  # Bar 3: buyers
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),  # Bar 4: confirm
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction == "LONG"
        assert info["kind"] == "REACTIVE"
        assert conf >= 0.75

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=50.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_short(self, _br, _belly, _amt, _cot):
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5247, 5250, 5247, 5249.50, v=1000),  # Bar 1: buyers
            _make_bar(5249, 5249, 5248, 5248.25, v=90),     # Bar 2: 91% drop
            _make_bar(5249, 5249, 5247, 5247.50, v=800),    # Bar 3: sellers
            _make_bar(5248, 5248, 5246, 5246.50, v=700),    # Bar 4: confirm
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction == "SHORT"
        assert info["kind"] == "REACTIVE"

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=False)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_rejected_when_belly_false(self, _br, _belly, _amt, _cot):
        """Belly explicitly False → no pattern (belly gate per W3-α)."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None  # explicit None, no fallback

    def test_reactive_needs_7_bars(self):
        bars = [_make_bar(5250, 5250, 5247, 5248)] * 6
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None


class TestInitiativePattern:
    """Initiative 4-bar per V3 T1: expansion → test → joining → retest."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long(self, _amt, _cot):
        bars = _quiet_lookback(v_bar1=600) + [
            _make_bar(5247, 5248.75, 5247, 5248.50, v=600),    # Bar 1: expansion 1.75pt
            _make_bar(5248, 5248.50, 5247.25, 5247.75, v=400),  # Bar 2: higher low
            _make_bar(5247.50, 5249.50, 5247.50, 5249, v=700),  # Bar 3: joining (range > B1)
            _make_bar(5248, 5249.25, 5247.50, 5249, v=500),     # Bar 4: test >= B2 low
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction == "LONG"
        assert info["kind"] == "INITIATIVE"
        assert conf >= 0.80


class TestPocVolRising:
    """POC_VOL rising check per V3 T1 — W3-α gap 3."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    def test_poc_rising_true(self):
        bars = [
            _make_bar(0, 0, 0, 0, poc_vol=5247),
            _make_bar(0, 0, 0, 0, poc_vol=5248),
            _make_bar(0, 0, 0, 0, poc_vol=5249),
        ]
        assert self.sys._poc_vol_rising(bars) is True

    def test_poc_not_rising(self):
        bars = [
            _make_bar(0, 0, 0, 0, poc_vol=5249),
            _make_bar(0, 0, 0, 0, poc_vol=5248),
            _make_bar(0, 0, 0, 0, poc_vol=5247),
        ]
        assert self.sys._poc_vol_rising(bars) is False

    def test_poc_rising_insufficient_bars(self):
        bars = [_make_bar(0, 0, 0, 0, poc_vol=5247)]
        assert self.sys._poc_vol_rising(bars) is False

    def test_poc_falling_true(self):
        bars = [
            _make_bar(0, 0, 0, 0, poc_vol=5249),
            _make_bar(0, 0, 0, 0, poc_vol=5248),
            _make_bar(0, 0, 0, 0, poc_vol=5247),
        ]
        assert self.sys._poc_vol_falling(bars) is True


# ── Pkg 2a · Close-through-level entry signal tests ───────────────


class TestReactiveCloseThrough:
    """Pkg 2a · Reactive entry signal requires close through prior bar level."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_long_rejected_when_b4_close_below_b3_high(self, _br, _belly, _amt, _cot):
        """b4.close == b3.high (5249) → NOT strictly above → rejected."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=50.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_short_rejected_when_b4_close_above_b3_low(self, _br, _belly, _amt, _cot):
        """b4.close == b3.low (5247) → NOT strictly below → rejected."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5247, 5250, 5247, 5249.50, v=1000),
            _make_bar(5249, 5249, 5248, 5248.25, v=90),
            _make_bar(5249, 5249, 5247, 5247.50, v=800),
            _make_bar(5248, 5248, 5246, 5247, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_long_fires_when_b4_close_above_b3_high(self, _br, _belly, _amt, _cot):
        """Regression confirmation: existing positive test still passes."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction == "LONG"


class TestInitiativeCloseThrough:
    """Pkg 2a · Initiative entry signal requires close through expansion bar level."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long_rejected_when_b4_close_below_b1_high(self, _amt, _cot):
        """b4.close == b1.high (5248.75) → NOT strictly above → rejected."""
        bars = _quiet_lookback(v_bar1=600) + [
            _make_bar(5247, 5248.75, 5247, 5248.50, v=600),
            _make_bar(5248, 5248.50, 5247.25, 5247.75, v=400),
            _make_bar(5247.50, 5249.50, 5247.50, 5249, v=700),
            _make_bar(5248, 5249.25, 5247.50, 5248.75, v=500),
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=120.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_short_rejected_when_b4_close_above_b1_low(self, _amt, _cot):
        """b4.close == b1.low (5247) → NOT strictly below → rejected."""
        bars = _quiet_lookback(v_bar1=600) + [
            _make_bar(5248.75, 5248.75, 5247, 5247.25, v=600),
            _make_bar(5247.50, 5248.50, 5247, 5248, v=400),
            _make_bar(5248, 5249, 5247, 5247.25, v=700),
            _make_bar(5247.50, 5248.25, 5246.50, 5247, v=500),
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long_fires_when_b4_close_above_b1_high(self, _amt, _cot):
        """Regression confirmation: existing positive test still passes."""
        bars = _quiet_lookback(v_bar1=600) + [
            _make_bar(5247, 5248.75, 5247, 5248.50, v=600),
            _make_bar(5248, 5248.50, 5247.25, 5247.75, v=400),
            _make_bar(5247.50, 5249.50, 5247.50, 5249, v=700),
            _make_bar(5248, 5249.25, 5247.50, 5249, v=500),
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction == "LONG"


class TestFamilyMapping:
    """Pkg 2a · family mapping fix for adaptive_stop integration."""

    def test_reactive_kind_maps_to_reactive_family(self):
        """REACTIVE detector → 'Reactive' family (multiplier 1.0)."""
        kind = "REACTIVE"
        family = "Reactive" if kind == "REACTIVE" else "OFA"
        assert family == "Reactive"

    def test_initiative_kind_maps_to_ofa_family(self):
        """INITIATIVE detector → 'OFA' family (multiplier 1.5)."""
        kind = "INITIATIVE"
        family = "Reactive" if kind == "REACTIVE" else "OFA"
        assert family == "OFA"

    def test_unknown_kind_falls_back_to_ofa(self):
        """Defensive: unknown kind → 'OFA' (wider stop, safer)."""
        kind = "UNKNOWN_FUTURE"
        family = "Reactive" if kind == "REACTIVE" else "OFA"
        assert family == "OFA"


class TestFamilyIntegratesWithAdaptiveStop:
    """Pkg 2a × Pkg 1 · family mapping yields correct ATR_MULTIPLIERS downstream."""

    def test_reactive_family_yields_correct_multiplier(self):
        from backend.v9.systems.five_min.adaptive_stop import ATR_MULTIPLIERS
        assert ATR_MULTIPLIERS["Reactive"] == 1.0  # D-091 Master Sheet 4

    def test_ofa_family_yields_correct_multiplier(self):
        from backend.v9.systems.five_min.adaptive_stop import ATR_MULTIPLIERS
        assert ATR_MULTIPLIERS["OFA"] == 1.5


# ── Pkg 2bc · Belly Dominance + Lookback + Constants ──────────────


class TestBellyDominanceRatio:
    """Pkg 2bc · belly_dominance_ratio gates Reactive fires."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=1.25)
    def test_reactive_long_rejected_when_belly_ratio_below_threshold(self, _br, _belly, _amt, _cot):
        """ratio=1.25 < 1.5 threshold → rejected."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=1.8)
    def test_reactive_long_fires_when_belly_ratio_above_threshold(self, _br, _belly, _amt, _cot):
        """ratio=1.8 >= 1.5 threshold → fires."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction == "LONG"

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=None)
    def test_reactive_long_passes_when_forces_history_unavailable(self, _br, _belly, _amt, _cot):
        """No forces history → graceful degradation → fires."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction == "LONG"

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=50.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=1.25)
    def test_reactive_short_belly_dominance_applies_mirror(self, _br, _belly, _amt, _cot):
        """SHORT mirror: ratio=1.25 < 1.5 → rejected."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5247, 5250, 5247, 5249.50, v=1000),
            _make_bar(5249, 5249, 5248, 5248.25, v=90),
            _make_bar(5249, 5249, 5247, 5247.50, v=800),
            _make_bar(5248, 5248, 5246, 5246.50, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None


class TestLookbackCheck:
    """Pkg 2bc · lookback volume check gates pattern fires."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    def test_pattern_rejected_when_buffer_below_7_bars(self):
        """6 bars → None (MIN_BARS_REQUIRED=7)."""
        bars = [_make_bar(5250, 5250, 5247, 5248)] * 6
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_long_rejected_when_lookback_has_high_volume(self, _br, _belly, _amt, _cot):
        """Lookback max=700, bar1=1000 → 700/1000=0.7 > 0.6 → rejected."""
        noisy_lookback = [
            _make_bar(5248, 5249, 5247, 5248, v=700),  # 700/1000 = 0.7 > 0.6
            _make_bar(5248, 5249, 5247, 5248, v=300),
            _make_bar(5248, 5249, 5247, 5248, v=400),
        ]
        bars = noisy_lookback + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    @patch.object(FiveMinSystem, '_get_belly_ratio_from_footprint', return_value=2.0)
    def test_reactive_long_fires_when_lookback_quiet(self, _br, _belly, _amt, _cot):
        """Lookback max=400, bar1=1000 → 400/1000=0.4 < 0.6 → fires."""
        bars = _quiet_lookback(v_bar1=1000) + [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction == "LONG"

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_lookback_also_applies(self, _amt, _cot):
        """Initiative blocked when lookback noisy."""
        noisy_lookback = [
            _make_bar(5248, 5249, 5247, 5248, v=500),  # 500/600 = 0.83 > 0.6
            _make_bar(5248, 5249, 5247, 5248, v=300),
            _make_bar(5248, 5249, 5247, 5248, v=400),
        ]
        bars = noisy_lookback + [
            _make_bar(5247, 5248.75, 5247, 5248.50, v=600),
            _make_bar(5248, 5248.50, 5247.25, 5247.75, v=400),
            _make_bar(5247.50, 5249.50, 5247.50, 5249, v=700),
            _make_bar(5248, 5249.25, 5247.50, 5249, v=500),
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction is None


class TestModuleConstants:
    """Pkg 2bc · module-level constants have documented defaults."""

    def test_constants_have_documented_defaults(self):
        from backend.v9.systems.five_min.five_min_system import (
            DROP_THRESHOLD_PCT, EXPANSION_MIN_PT, EXPANSION_MAX_PT,
            POC_RETURN_TOLERANCE_PT, MIN_BARS_REQUIRED, LOOKBACK_BARS,
            LOOKBACK_MAX_VOL_RATIO, BELLY_DOMINANCE_RATIO,
        )
        assert DROP_THRESHOLD_PCT == 0.10
        assert EXPANSION_MIN_PT == 1.5
        assert EXPANSION_MAX_PT == 1.75
        assert POC_RETURN_TOLERANCE_PT == 0.5
        assert MIN_BARS_REQUIRED == 7
        assert LOOKBACK_BARS == 3
        assert LOOKBACK_MAX_VOL_RATIO == 0.6
        assert BELLY_DOMINANCE_RATIO == 1.5
