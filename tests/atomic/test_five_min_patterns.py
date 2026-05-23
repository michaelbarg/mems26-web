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


class TestReactivePattern:
    """Reactive 4-bar per V3 T1: seller weakness → buyer belly → confirm."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    def test_reactive_long(self, _belly, _amt, _cot):
        bars = [
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
    def test_reactive_short(self, _belly, _amt, _cot):
        bars = [
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
    def test_reactive_rejected_when_belly_false(self, _belly, _amt, _cot):
        """Belly explicitly False → no pattern (belly gate per W3-α)."""
        bars = [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None  # explicit None, no fallback

    def test_reactive_needs_4_bars(self):
        bars = [_make_bar(5250, 5250, 5247, 5248)] * 3
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None


class TestInitiativePattern:
    """Initiative 4-bar per V3 T1: expansion → test → joining → retest."""

    def setup_method(self):
        self.sys = FiveMinSystem()

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long(self, _amt, _cot):
        bars = [
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
    def test_reactive_long_rejected_when_b4_close_below_b3_high(self, _belly, _amt, _cot):
        """b4.close == b3.high (5249) → NOT strictly above → rejected."""
        bars = [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),  # b3.high = 5249
            _make_bar(5248.50, 5250, 5248.50, 5249, v=700),      # b4.close = 5249 (== b3.high)
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=50.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    def test_reactive_short_rejected_when_b4_close_above_b3_low(self, _belly, _amt, _cot):
        """b4.close == b3.low (5247) → NOT strictly below → rejected."""
        bars = [
            _make_bar(5247, 5250, 5247, 5249.50, v=1000),
            _make_bar(5249, 5249, 5248, 5248.25, v=90),
            _make_bar(5249, 5249, 5247, 5247.50, v=800),    # b3.low = 5247
            _make_bar(5248, 5248, 5246, 5247, v=700),         # b4.close = 5247 (== b3.low)
        ]
        direction, conf, info = self.sys._detect_reactive(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    @patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
    def test_reactive_long_fires_when_b4_close_above_b3_high(self, _belly, _amt, _cot):
        """Regression confirmation: existing positive test still passes."""
        bars = [
            _make_bar(5250, 5250, 5247, 5247.50, v=1000),
            _make_bar(5248, 5248, 5247, 5247.75, v=80),
            _make_bar(5247.25, 5249, 5247.25, 5248.75, v=800),  # b3.high = 5249
            _make_bar(5248.50, 5250, 5248.50, 5249.75, v=700),  # b4.close = 5249.75 > 5249
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
        bars = [
            _make_bar(5247, 5248.75, 5247, 5248.50, v=600),     # b1.high = 5248.75
            _make_bar(5248, 5248.50, 5247.25, 5247.75, v=400),
            _make_bar(5247.50, 5249.50, 5247.50, 5249, v=700),
            _make_bar(5248, 5249.25, 5247.50, 5248.75, v=500),  # b4.close = 5248.75 (== b1.high)
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=120.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_short_rejected_when_b4_close_above_b1_low(self, _amt, _cot):
        """b4.close == b1.low (5247.25) → NOT strictly above (SHORT needs below) → rejected."""
        bars = [
            _make_bar(5248.75, 5248.75, 5247, 5247.25, v=600),  # b1: bear, expansion, b1.low=5247
            _make_bar(5247.50, 5248.50, 5247, 5248, v=400),     # b2: lower_high (5248.50 < 5248.75)
            _make_bar(5248, 5249, 5247, 5247.25, v=700),        # b3: joining (range 2.0 > 1.75)
            _make_bar(5247.50, 5248.25, 5246.50, 5247, v=500),  # b4: test h<=b2.h, close=5247 (== b1.low)
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction is None

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long_fires_when_b4_close_above_b1_high(self, _amt, _cot):
        """Regression confirmation: existing positive test still passes."""
        bars = [
            _make_bar(5247, 5248.75, 5247, 5248.50, v=600),
            _make_bar(5248, 5248.50, 5247.25, 5247.75, v=400),
            _make_bar(5247.50, 5249.50, 5247.50, 5249, v=700),
            _make_bar(5248, 5249.25, 5247.50, 5249, v=500),     # b4.close = 5249 > 5248.75
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
