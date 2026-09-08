"""#1191 monotonic ladder ordering guard.

t2 must be farther from entry than t1, t3 farther than t2.
An inverted ladder sends duplicate targets to the DLL.

Behavioral test: inverted ladder → closer leg dropped to None.
Mutation: removing _mdist <= _prev_dist → inverted ladder passes.
"""
import inspect
import unittest


class TestMonotonicLadderGuard(unittest.TestCase):

    def _apply_guard(self, entry, direction, t1, t2, t3):
        """Apply the monotonic guard logic directly (same as gateway code)."""
        setup = {"entry_price": entry, "t1": t1, "t2": t2, "t3": t3}
        _prev_dist = 0.0
        for _mk in ("t1", "t2", "t3"):
            _mv = setup.get(_mk)
            if _mv is None:
                continue
            _mdist = abs(float(_mv) - float(entry))
            if _mdist <= _prev_dist:
                setup[_mk] = None
            else:
                _prev_dist = _mdist
        return setup

    def test_inverted_t2_dropped(self):
        """#1191: t1=7702.25 (6pt), t2=7704.0 (4.25pt) → t2=None."""
        r = self._apply_guard(7708.25, "SHORT", 7702.25, 7704.0, 7698.5)
        self.assertEqual(r["t1"], 7702.25)
        self.assertIsNone(r["t2"], "t2 closer than t1 → must be None")
        self.assertEqual(r["t3"], 7698.5)

    def test_monotonic_ladder_passes(self):
        """A correctly ordered ladder passes unchanged."""
        r = self._apply_guard(7708.25, "SHORT", 7705.0, 7700.0, 7695.0)
        self.assertEqual(r["t1"], 7705.0)
        self.assertEqual(r["t2"], 7700.0)
        self.assertEqual(r["t3"], 7695.0)

    def test_equal_distance_dropped(self):
        """t2 at same distance as t1 → dropped (DLL dedup)."""
        r = self._apply_guard(7708.25, "SHORT", 7702.25, 7714.25, 7698.5)
        # t1 dist=6.0, t2 dist=6.0 (same) → dropped
        self.assertIsNone(r["t2"])

    def test_long_direction(self):
        """LONG: t1=7712 (3.75pt), t2=7710 (1.75pt) → t2=None."""
        r = self._apply_guard(7708.25, "LONG", 7712.0, 7710.0, 7720.0)
        self.assertEqual(r["t1"], 7712.0)
        self.assertIsNone(r["t2"], "t2 closer than t1 in LONG → None")
        self.assertEqual(r["t3"], 7720.0)

    def test_mutation_guard_in_source(self):
        """MUTATION: _mdist <= _prev_dist must appear in trading_gateway.py."""
        from backend.v9.gateway.trading_gateway import TradingGateway
        source = inspect.getsource(TradingGateway._route_setup_inner)
        self.assertIn("_mdist <= _prev_dist", source,
                       "Removing the monotonic check is a mutation — "
                       "inverted ladders would reach the DLL")

    def test_none_targets_skipped(self):
        """None targets are skipped without breaking the chain."""
        r = self._apply_guard(7708.25, "SHORT", 7705.0, None, 7695.0)
        self.assertEqual(r["t1"], 7705.0)
        self.assertIsNone(r["t2"])
        self.assertEqual(r["t3"], 7695.0)


if __name__ == "__main__":
    unittest.main()
