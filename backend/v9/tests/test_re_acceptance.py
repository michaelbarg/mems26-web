"""RE_ACCEPTANCE_V1 — bar-of-acceptance detector tests.

Behavioral: bar meeting all conditions → trigger with shadow_only.
Almost-bar (delta 0.6×) → None. Mutations for each condition.
"""
import os
import unittest
from backend.v9.systems.re_acceptance import detect, build_setup


def _bars(n=15, last_delta=4130, last_vol=22284, last_close=7730, last_high=7731, last_low=7718):
    """Build bars ending with a candidate acceptance bar."""
    bars = []
    for i in range(n - 1):
        bars.append({
            "o": 7700 + i, "h": 7705 + i, "l": 7695 + i,
            "c": 7702 + i, "vol": 10000 + i * 500,
            "delta": (i + 1) * 300,  # max prior delta ~4200
        })
    # Last bar: the acceptance bar
    bars.append({
        "o": 7718, "h": last_high, "l": last_low, "c": last_close,
        "vol": last_vol, "delta": last_delta,
    })
    return bars


class TestReAcceptanceDetect(unittest.TestCase):

    def test_acceptance_bar_fires(self):
        """Bar with delta ≥ 0.7× max, vol ≥ 0.7× max, close extreme, crosses edge → trigger."""
        bars = _bars(last_delta=4130, last_vol=22284, last_close=7730, last_high=7731, last_low=7718)
        t = detect(bars, ib_high=7726, ib_low=7700, gap_direction="UP")
        self.assertIsNotNone(t)
        self.assertEqual(t["direction"], "LONG")
        self.assertIn("IBH", t["edge"])

    def test_almost_bar_delta_too_low(self):
        """Delta at 0.6× max → None."""
        bars = _bars(last_delta=2500, last_vol=22284, last_close=7730, last_high=7731, last_low=7718)
        # Max prior delta ~4200, 2500/4200 ≈ 0.60 < 0.7
        t = detect(bars, ib_high=7726, ib_low=7700, gap_direction="UP")
        self.assertIsNone(t)

    def test_mutation_remove_delta_check(self):
        """Without delta, should return None (Rule 1)."""
        bars = _bars()
        bars[-1]["delta"] = None
        t = detect(bars, ib_high=7726, ib_low=7700, gap_direction="UP")
        self.assertIsNone(t)

    def test_mutation_remove_volume_check(self):
        """Low volume → None."""
        bars = _bars(last_vol=100)  # tiny volume
        t = detect(bars, ib_high=7726, ib_low=7700, gap_direction="UP")
        self.assertIsNone(t)

    def test_mutation_remove_close_position(self):
        """Close in the middle of the bar → None."""
        bars = _bars(last_close=7724, last_high=7731, last_low=7718)
        # cpos = (7724-7718)/(7731-7718) = 6/13 ≈ 0.46 < 0.75
        t = detect(bars, ib_high=7720, ib_low=7700, gap_direction="UP")
        self.assertIsNone(t)

    def test_mutation_remove_edge_crossing(self):
        """Close doesn't cross any edge → None."""
        bars = _bars(last_close=7720, last_high=7721, last_low=7718)
        # Close 7720 < ib_high 7726
        t = detect(bars, ib_high=7726, ib_low=7700, gap_direction="UP")
        self.assertIsNone(t)

    def test_mutation_wrong_gap_direction(self):
        """Gap DOWN but delta LONG → None."""
        bars = _bars(last_delta=4130, last_vol=22284, last_close=7730, last_high=7731, last_low=7718)
        t = detect(bars, ib_high=7726, ib_low=7700, gap_direction="DOWN")
        self.assertIsNone(t)

    def test_build_setup_has_shadow_only(self):
        """Setup must have shadow_only=True."""
        trigger = {
            "type": "RE_ACCEPTANCE", "direction": "LONG",
            "entry": 7730, "stop": 7716, "t1": 7744,
            "edge": "IBH", "delta_frac": 0.98, "vol_frac": 0.87,
        }
        setup = build_setup(trigger)
        self.assertTrue(setup["metadata"]["shadow_only"])
        self.assertEqual(setup["classification"], "RE_ACCEPTANCE")

    def test_short_direction(self):
        """SHORT acceptance bar: delta negative, close low, crosses IBL."""
        bars = []
        for i in range(14):
            bars.append({
                "o": 7730 - i, "h": 7735 - i, "l": 7725 - i,
                "c": 7728 - i, "vol": 10000 + i * 500,
                "delta": -(i + 1) * 300,
            })
        bars.append({
            "o": 7725, "h": 7726, "l": 7710, "c": 7712,
            "vol": 22000, "delta": -4200,
        })
        t = detect(bars, ib_high=7730, ib_low=7720, gap_direction="DOWN")
        self.assertIsNotNone(t)
        self.assertEqual(t["direction"], "SHORT")


if __name__ == "__main__":
    unittest.main()
