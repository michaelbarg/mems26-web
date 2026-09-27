# -*- coding: utf-8 -*-
"""T-495 (27.09): live bar events carry `ts` as epoch seconds; the TPO system's timestamptz casts rejected it
(`DatetimeFieldOverflow`, every restart), so the T-330 restart seed of the session extremes never ran and the
decision tree read a post-boot session low after a mid-session restart (25.09 19:17: 7804.25 vs 7752.75)."""
import os
import unittest

from backend.v9.systems.tpo.tpo_system import _norm_bar_ts


class TestNormBarTs(unittest.TestCase):
    def test_epoch_seconds_become_iso_utc(self):
        self.assertEqual(_norm_bar_ts(1790352900), "2026-09-25T16:15:00+00:00")
        self.assertEqual(_norm_bar_ts("1790352900"), "2026-09-25T16:15:00+00:00")
        self.assertEqual(_norm_bar_ts(1790352900.0), "2026-09-25T16:15:00+00:00")

    def test_epoch_millis(self):
        self.assertEqual(_norm_bar_ts(1790352900000), "2026-09-25T16:15:00+00:00")

    def test_iso_and_empty_pass_through(self):
        self.assertEqual(_norm_bar_ts("2026-09-25T16:15:00+00:00"), "2026-09-25T16:15:00+00:00")
        self.assertEqual(_norm_bar_ts(""), "")
        self.assertIsNone(_norm_bar_ts(None))
        self.assertEqual(_norm_bar_ts(True), True)

    def test_process_bar_normalises_at_the_source(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "v9", "systems", "tpo",
                                "tpo_system.py"), encoding="utf-8").read()
        self.assertIn("ts_str = _norm_bar_ts(getattr(event, 'ts', '') or bar.get('ts', ''))", src)


if __name__ == "__main__":
    unittest.main()
