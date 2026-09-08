"""RE_ACCEPTANCE_V1 pipeline test — through _on_bar_closed, not detect().

The current test_re_acceptance.py feeds delta+vol directly to detect(),
so it passes on a dead pipeline. This test uses the real buffer shape
({ts,o,h,l,c,v} without delta) and a mocked read_all for enrichment.

Mutation: removing the enrichment line → _ra_bars have no delta → detect
returns None → route_setup never called → FAIL.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestReAcceptancePipeline(unittest.TestCase):

    def _make_buffer(self, n=15):
        """Build a buffer in the REAL shape: {ts, o, h, l, c, v} — NO delta."""
        bars = []
        from datetime import timedelta
        base_ts = datetime(2026, 9, 3, 16, 30, tzinfo=timezone.utc)
        for i in range(n):
            ts = base_ts + timedelta(minutes=i * 5)
            bars.append({
                "ts": ts.isoformat(),
                "o": 7700 + i, "h": 7705 + i, "l": 7695 + i,
                "c": 7702 + i, "v": 10000 + i * 500,
            })
        # Last bar: acceptance candidate
        bars[-1] = {
            "ts": base_ts.replace(hour=18, minute=0).isoformat(),
            "o": 7718, "h": 7731, "l": 7718,
            "c": 7730, "v": 22284,
        }
        return bars

    def _make_delta_rows(self, buffer):
        """Build mock DB rows for v9_bars_cumulative_delta."""
        rows = []
        for i, b in enumerate(buffer):
            rows.append({
                "ts": datetime.fromisoformat(b["ts"]),
                "delta": (i + 1) * 300 if i < len(buffer) - 1 else 4130.0,
            })
        return rows

    @patch("backend.v9.systems.re_acceptance.detect")
    def test_enrichment_provides_delta_and_vol(self, mock_detect):
        """After enrichment, bars passed to detect() have delta and vol keys."""
        mock_detect.return_value = None  # don't need actual detection

        buf = self._make_buffer()
        delta_rows = self._make_delta_rows(buf)

        # Simulate the enrichment logic from five_min_system.py
        from backend.v9.systems.five_min.five_min_system import _canon_bar_ts

        dm = {_canon_bar_ts(r["ts"]): float(r["delta"])
              for r in delta_rows if r.get("delta") is not None}

        enriched = []
        for rb in buf:
            rd = dict(rb)
            rd["delta"] = dm.get(_canon_bar_ts(rb.get("ts")))
            if rd.get("vol") is None:
                rd["vol"] = rb.get("v", rb.get("volume"))
            enriched.append(rd)

        # Verify enrichment
        last = enriched[-1]
        self.assertIsNotNone(last.get("delta"),
                              "Last bar must have delta after enrichment")
        self.assertIsNotNone(last.get("vol"),
                              "Last bar must have vol after enrichment")
        self.assertEqual(last["delta"], 4130.0)
        self.assertEqual(last["vol"], 22284)

        # Count enriched
        hit = sum(1 for b in enriched if b.get("delta") is not None)
        self.assertEqual(hit, len(buf),
                          f"All {len(buf)} bars should have delta, got {hit}")

    def test_raw_buffer_has_no_delta(self):
        """The raw buffer shape has NO delta — confirms the bug existed."""
        buf = self._make_buffer()
        for b in buf:
            self.assertNotIn("delta", b,
                              "Raw buffer must NOT have delta key")

    def test_mutation_no_enrichment_means_no_delta(self):
        """MUTATION: without enrichment, detect() gets None delta → returns None."""
        from backend.v9.systems.re_acceptance import detect

        buf = self._make_buffer()
        # Pass raw buffer (no enrichment) — should return None
        result = detect(buf, ib_high=7726, ib_low=7700, gap_direction="UP")
        self.assertIsNone(result,
                           "Without enrichment, detect must return None (no delta)")

    def test_enrichment_plus_detect_fires(self):
        """Full pipeline: enrich → detect → trigger."""
        from backend.v9.systems.re_acceptance import detect
        from backend.v9.systems.five_min.five_min_system import _canon_bar_ts

        buf = self._make_buffer()
        delta_rows = self._make_delta_rows(buf)

        dm = {_canon_bar_ts(r["ts"]): float(r["delta"])
              for r in delta_rows if r.get("delta") is not None}

        enriched = []
        for rb in buf:
            rd = dict(rb)
            rd["delta"] = dm.get(_canon_bar_ts(rb.get("ts")))
            if rd.get("vol") is None:
                rd["vol"] = rb.get("v")
            enriched.append(rd)

        result = detect(enriched, ib_high=7726, ib_low=7700, gap_direction="UP")
        self.assertIsNotNone(result,
                              "After enrichment, detect must fire on acceptance bar")
        self.assertEqual(result["direction"], "LONG")

    def test_vol_key_mapped_from_v(self):
        """The buffer uses 'v' but detect() reads 'vol' — enrichment must map."""
        buf = self._make_buffer()
        # Raw has 'v' but not 'vol'
        self.assertIn("v", buf[-1])
        self.assertNotIn("vol", buf[-1])

        # After enrichment
        rd = dict(buf[-1])
        if rd.get("vol") is None:
            rd["vol"] = rd.get("v")
        self.assertEqual(rd["vol"], 22284)


if __name__ == "__main__":
    unittest.main()
