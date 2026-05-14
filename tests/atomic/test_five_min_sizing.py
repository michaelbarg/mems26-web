"""W3-α — Five-Min calculate_size per Cockpit V5 LOCKED.

CORR-23: per-system internal only. No cross-system inputs.
"""
from backend.v9.systems.five_min.five_min_system import FiveMinSystem


class TestCalculateSize:

    def setup_method(self):
        self.sys = FiveMinSystem()

    def test_full_size_pristine_setup(self):
        """4 bars + strong COT + at POC → full (3 contracts)."""
        result = self.sys.calculate_size({
            "bars_formed": 4,
            "direction": "LONG",
            "cot": 150,
            "amt": 100,
            "location_vs_poc_vol": "at",
        })
        assert result == "full"

    def test_half_size_solid_setup(self):
        """3 bars + COT ok + near POC → half (2 contracts)."""
        result = self.sys.calculate_size({
            "bars_formed": 3,
            "direction": "LONG",
            "cot": 110,
            "amt": 100,
            "location_vs_poc_vol": "near",
        })
        assert result == "half"

    def test_reject_no_flow_support(self):
        """COT below AMT for LONG → reject."""
        result = self.sys.calculate_size({
            "bars_formed": 4,
            "direction": "LONG",
            "cot": 80,
            "amt": 100,
            "location_vs_poc_vol": "at",
        })
        assert result == "reject"

    def test_reject_immature_pattern(self):
        """< 3 bars → reject."""
        result = self.sys.calculate_size({
            "bars_formed": 2,
            "direction": "LONG",
            "cot": 150,
            "amt": 100,
            "location_vs_poc_vol": "at",
        })
        assert result == "reject"

    def test_reject_far_from_poc(self):
        """Far from POC → reject."""
        result = self.sys.calculate_size({
            "bars_formed": 3,
            "direction": "LONG",
            "cot": 110,
            "amt": 100,
            "location_vs_poc_vol": "far",
        })
        assert result == "reject"
