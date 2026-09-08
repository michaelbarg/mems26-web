"""RE_ACCEPTANCE_V1 — the real pipeline test: calls production, captures what
production actually hands the detector.

Written by cowork-dev 2026-09-08. The existing backend/v9/tests/
test_re_acceptance_pipeline.py says "through _on_bar_closed" in its docstring
and then, at its line 55, "# Simulate the enrichment logic from
five_min_system.py" — it rebuilds the delta map inside the test body and never
calls production. Deleting the 25 enrichment lines from five_min_system.py
leaves it green, so it cannot be the acceptance evidence for an enrichment fix.

This one patches `re_acceptance.detect`, drives the real
`FiveMinSystem._maybe_re_acceptance()` with a buffer in the REAL shape
({ts,o,h,l,c,v} — no delta, no vol) and a stubbed `read_all`, then asserts on
the bars production passed down. Remove the enrichment from production and
this fails, which is the whole point.

Guards the class that has now landed five times (§2 · §4 · §5 · §7 · §3):
green unit tests over a pipeline that never carries the keys the detector reads.
"""
import os
import unittest
from unittest.mock import patch


BUFFER_TS = [
    "2026-09-03 17:30:00+03:00", "2026-09-03 17:35:00+03:00",
    "2026-09-03 17:40:00+03:00", "2026-09-03 17:45:00+03:00",
    "2026-09-03 17:50:00+03:00", "2026-09-03 17:55:00+03:00",
]


def _real_shape_buffer():
    """Exactly what five_min_system.py:466-473 puts in _bar_buffer."""
    out = []
    for i, ts in enumerate(BUFFER_TS):
        base = 7700.0 + i
        out.append({"ts": ts, "o": base, "h": base + 3.0,
                    "l": base - 1.0, "c": base + 2.5, "v": 1000 + i * 100})
    return out


def _delta_rows():
    from datetime import datetime
    return [{"ts": datetime.fromisoformat(ts), "delta": 300.0 * (i + 1)}
            for i, ts in enumerate(BUFFER_TS)]


class TestReAcceptanceProductionPath(unittest.TestCase):
    def setUp(self):
        self._prev = os.environ.get("RE_ACCEPTANCE_V1")
        os.environ["RE_ACCEPTANCE_V1"] = "shadow"

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("RE_ACCEPTANCE_V1", None)
        else:
            os.environ["RE_ACCEPTANCE_V1"] = self._prev

    def _run_production(self, delta_rows):
        """Drive the real method; return the bars it handed to detect()."""
        from backend.v9.systems.five_min.five_min_system import FiveMinSystem

        sys_ = FiveMinSystem.__new__(FiveMinSystem)   # no __init__: no DB, no clock
        sys_._bar_buffer = _real_shape_buffer()
        sys_._gateway = type("G", (), {"route_setup": lambda self, s, i: None})()

        captured = {}

        def _capture(bars, **kw):
            captured["bars"] = bars
            return None      # never build a setup — this test is about the input

        with patch("backend.v9.systems.re_acceptance.detect", side_effect=_capture), \
             patch("backend.v9.db.read.read_all", return_value=delta_rows), \
             patch("backend.v9.api.v9.tpo_routes._load_sierra_tpo",
                   return_value={"ib_high": 7726, "ib_low": 7700}):
            sys_._maybe_re_acceptance()

        return captured.get("bars")

    def test_production_hands_the_detector_delta_and_vol(self):
        bars = self._run_production(_delta_rows())
        self.assertIsNotNone(
            bars, "production never called detect() — the detector is unreachable")
        last = bars[-1]
        self.assertIsNotNone(
            last.get("delta"),
            "production handed the detector a bar with no delta. re_acceptance.py:71 "
            "returns None on that (Rule 1), so the detector is inert. The buffer "
            "carries {ts,o,h,l,c,v} — the enrichment in _maybe_re_acceptance must "
            "attach delta from v9_bars_cumulative_delta.")
        self.assertIsNotNone(
            last.get("vol"),
            "production handed the detector a bar with no 'vol'. The buffer key is "
            "'v'; re_acceptance.py:70 reads 'vol'/'volume' → 0 → max_vol<=0 → None.")
        self.assertEqual(last["delta"], 300.0 * len(BUFFER_TS))
        self.assertEqual(last["vol"], last["v"])

    def test_every_bar_is_enriched_not_only_the_last(self):
        bars = self._run_production(_delta_rows())
        hit = sum(1 for b in bars if b.get("delta") is not None)
        self.assertEqual(
            hit, len(BUFFER_TS),
            f"only {hit}/{len(BUFFER_TS)} bars carry delta — the session-max "
            f"comparison in re_acceptance.detect() is computed over the PRIOR "
            f"bars, so a partially enriched buffer silently changes the threshold")

    def test_empty_delta_map_is_survivable_and_loud(self):
        """DB returns nothing → no crash, and detect still gets called (with
        delta=None) so the 'detector inert' warning is what surfaces it."""
        bars = self._run_production([])
        self.assertIsNotNone(bars, "an empty delta map must not abort the path")
        self.assertIsNone(bars[-1].get("delta"))

    def test_ts_key_uses_the_canonicaliser_not_str(self):
        """The buffer's ts is 'YYYY-MM-DD HH:MM:SS+03:00' while the aggregator
        path emits ISO with 'T'. Matching on str() works for one and breaks for
        the other — the F2 class (12.08). Feed ISO-T rows and require a match.
        """
        from datetime import datetime
        rows = [{"ts": datetime.fromisoformat(ts).isoformat(), "delta": 300.0 * (i + 1)}
                for i, ts in enumerate(BUFFER_TS)]
        bars = self._run_production(rows)
        self.assertIsNotNone(bars[-1].get("delta"),
                             "ISO-'T' delta rows did not match the buffer's "
                             "space-separated ts — the map key is not going "
                             "through _canon_bar_ts")


if __name__ == "__main__":
    unittest.main()
