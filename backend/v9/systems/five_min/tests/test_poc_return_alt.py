"""Tests for POC return alt (Initiative Bar -2 alternative path)."""
from unittest.mock import patch
from backend.v9.systems.five_min.five_min_system import FiveMinSystem


def _make_bar(o, h, l, c, v=600, poc_vol=None):
    bar = {"o": o, "h": h, "l": l, "c": c, "v": v}
    if poc_vol is not None:
        bar["poc_vol"] = poc_vol
    return bar


class TestPocReturnAlt:
    def setup_method(self):
        self.sys = FiveMinSystem()

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long_poc_return(self, _amt, _cot):
        """Bar -2 returns to POC_VOL (not HL) → still fires."""
        bars = [
            _make_bar(5246, 5246, 5246, 5246, v=200),           # Lookback 1
            _make_bar(5246, 5246, 5246, 5246, v=200),           # Lookback 2
            _make_bar(5246, 5246, 5246, 5246, v=200),           # Lookback 3
            _make_bar(5247, 5248.75, 5247, 5248.50, v=600),    # Bar 1: expansion 1.75pt
            # Bar 2: NOT higher low (5246.5 < 5247), but close returns to POC
            _make_bar(5248, 5248.50, 5246.5, 5247.0, v=400, poc_vol=5247.0),
            _make_bar(5247.0, 5249.50, 5247.0, 5249, v=700),   # Bar 3: joining
            _make_bar(5248, 5249.25, 5247.0, 5249, v=500),     # Bar 4: test
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction == "LONG"
        assert info.get("b2_alt") == "poc_return"

    @patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=80.0)
    @patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
    def test_initiative_long_no_hl_no_poc_fails(self, _amt, _cot):
        """Bar -2 neither HL nor POC return → no fire."""
        bars = [
            _make_bar(5246, 5246, 5246, 5246, v=200),           # Lookback 1
            _make_bar(5246, 5246, 5246, 5246, v=200),           # Lookback 2
            _make_bar(5246, 5246, 5246, 5246, v=200),           # Lookback 3
            _make_bar(5247, 5248.75, 5247, 5248.50, v=600),
            # Bar 2: low < b1 low AND close far from POC
            _make_bar(5248, 5248.50, 5245, 5246.0, v=400, poc_vol=5249.0),
            _make_bar(5246.0, 5249.50, 5246.0, 5249, v=700),
            _make_bar(5248, 5249.25, 5246.0, 5249, v=500),
        ]
        direction, conf, info = self.sys._detect_initiative(bars)
        assert direction is None
