# -*- coding: utf-8 -*-
"""T-497 (27.09): the candidate ledger dropped every DETECTED event whose signal_bar_ts arrived as an epoch STRING
('1790353200.000000') — `_as_utc` parsed int/float epochs but sent strings to fromisoformat, which raised, and
record() swallowed it (live log 23.09 20:20 · 24.09 17:45 · 25.09 19:25). Same class as T-495."""
import unittest

from backend.v9.services.candidate_ledger import floor_bar_ts, make_candidate_id


class TestLedgerEpochString(unittest.TestCase):
    def test_epoch_string_floors_like_the_number(self):
        self.assertEqual(floor_bar_ts("1790353200.000000"), "2026-09-25T16:20:00+00:00")
        self.assertEqual(floor_bar_ts("1790353200.000000"), floor_bar_ts(1790353200))
        self.assertEqual(floor_bar_ts("1790353200000"), floor_bar_ts(1790353200))

    def test_iso_and_z_still_parse(self):
        self.assertEqual(floor_bar_ts("2026-09-25T16:23:10Z"), "2026-09-25T16:20:00+00:00")
        self.assertEqual(floor_bar_ts("2026-09-25T16:23:10+00:00"), "2026-09-25T16:20:00+00:00")

    def test_same_candidate_id_for_string_and_number(self):
        a = make_candidate_id(system_id=2, pattern="DOUBLE_BOTTOM_EE_LONG", direction="LONG",
                              signal_bar_ts="1790353200.000000")
        b = make_candidate_id(system_id=2, pattern="DOUBLE_BOTTOM_EE_LONG", direction="LONG",
                              signal_bar_ts=1790353200)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
