"""§7 DELTA_BREAKOUT_RELEASE_V1 — delta-based release path in release_gate.

Mutation guards:
  - Removing delta condition → releases without delta → FAIL
  - Removing volume condition → releases on low volume → FAIL
  - Removing accepted_break check → fires without IB break → FAIL
"""
import os
import unittest

from backend.v9.systems.release_gate import (
    Bar, _delta_breakout_release, ReleaseVerdict,
)


class TestDeltaBreakoutRelease(unittest.TestCase):

    def _bars(self, n=10, delta_last=4130, vol_last=22284):
        """Build bars with delta growing to max on last bar."""
        bars = []
        for i in range(n):
            d = (i + 1) * 100 if i < n - 1 else delta_last
            v = 10000 + i * 1000 if i < n - 1 else vol_last
            bars.append(Bar(high=7730 + i, low=7720 - i, close=7725 + i,
                            volume=v, delta=d))
        return bars

    def setUp(self):
        os.environ["DELTA_BREAKOUT_RELEASE_V1"] = "1"

    def tearDown(self):
        os.environ.pop("DELTA_BREAKOUT_RELEASE_V1", None)

    def test_releases_on_max_delta_and_volume(self):
        """With session-max delta and sufficient volume → released."""
        bars = self._bars(delta_last=4130, vol_last=22284)
        v = _delta_breakout_release(bars, "LONG", "UP")
        self.assertIsNotNone(v)
        self.assertTrue(v.released)
        self.assertIn("delta-breakout", v.reason)

    def test_no_release_without_accepted_break(self):
        """Without accepted_break → None (no decision)."""
        bars = self._bars()
        v = _delta_breakout_release(bars, "LONG", None)
        self.assertIsNone(v)

    def test_no_release_wrong_direction(self):
        """Break=DOWN but direction=LONG → None."""
        bars = self._bars()
        v = _delta_breakout_release(bars, "LONG", "DOWN")
        self.assertIsNone(v)

    def test_no_release_when_flag_off(self):
        """Flag OFF → None always."""
        os.environ["DELTA_BREAKOUT_RELEASE_V1"] = "0"
        bars = self._bars()
        v = _delta_breakout_release(bars, "LONG", "UP")
        self.assertIsNone(v)

    def test_mutation_removing_delta_check(self):
        """MUTATION: if delta is not session-max, should NOT release."""
        bars = self._bars(delta_last=50, vol_last=22284)  # tiny delta
        v = _delta_breakout_release(bars, "LONG", "UP")
        # delta=50 is not the session max (max is 900 from bar 9)
        self.assertTrue(v is None or not v.released)

    def test_mutation_removing_volume_check(self):
        """MUTATION: low volume should NOT release."""
        bars = self._bars(delta_last=4130, vol_last=100)  # tiny volume
        v = _delta_breakout_release(bars, "LONG", "UP")
        # vol=100 < 0.7 * max_vol (max is ~19000)
        self.assertTrue(v is None or not v.released)

    def test_shadow_logs_but_does_not_release(self):
        """Shadow mode: returns None (no decision), only logs."""
        os.environ["DELTA_BREAKOUT_RELEASE_V1"] = "shadow"
        bars = self._bars()
        v = _delta_breakout_release(bars, "LONG", "UP")
        self.assertIsNone(v)  # shadow = no release

    def test_no_delta_data_returns_none(self):
        """Bars without delta → None (Rule 1: honest failure)."""
        bars = [Bar(7730, 7720, 7725, 10000, delta=None) for _ in range(10)]
        v = _delta_breakout_release(bars, "LONG", "UP")
        self.assertIsNone(v)


if __name__ == "__main__":
    unittest.main()
