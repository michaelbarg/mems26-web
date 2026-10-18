# -*- coding: utf-8 -*-
"""T-594 (18.10, cowork): the opening lock (T-314, opening_lock.py) called detect_opening_type WITHOUT the prior-day
references, so the detector's open-location axis (Dalton pp.74-88) was always UNKNOWN: OPEN_AUCTION_OUT and
OPEN_TEST_DRIVE could never be locked (0 of 235 harness sessions; with references the detector reads OUT in 34 and
TEST_DRIVE in 14). OPENING_LOCK_PRIOR_REFS_V1 (default OFF) passes machine.prev_vah/prev_val and the prior high/low."""
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from backend.v9.systems.day_type.opening_lock import update_opening_lock, _prior_refs


def _rotational_open_outside_prior_range():
    """six closed bars rotating around an open of 7600, prior day 7500-7560 (open OUT of range), + a developing bar"""
    o = 7600.0
    bars = [{"o": o, "h": o + 3, "l": o - 3, "c": o + 1, "v": 1000},
            {"o": o + 1, "h": o + 4, "l": o - 2, "c": o - 1, "v": 900},
            {"o": o - 1, "h": o + 2, "l": o - 4, "c": o + 1, "v": 900},
            {"o": o + 1, "h": o + 3, "l": o - 3, "c": o - 1, "v": 900},
            {"o": o - 1, "h": o + 2, "l": o - 3, "c": o + 0.5, "v": 900},
            {"o": o + 0.5, "h": o + 3, "l": o - 2, "c": o - 0.5, "v": 900},
            {"o": o - 0.5, "h": o + 1, "l": o - 1, "c": o, "v": 300}]
    return bars


def _machine():
    return SimpleNamespace(prev_vah=7550.0, prev_val=7520.0, opening_bars=[SimpleNamespace(pd_high=7560.0, pd_low=7500.0)])


class TestPriorRefs(unittest.TestCase):
    def test_refs_only_under_the_flag(self):
        m = _machine()
        with mock.patch.dict(os.environ, {"OPENING_LOCK_PRIOR_REFS_V1": "0"}):
            self.assertEqual(_prior_refs(m), {})
        with mock.patch.dict(os.environ, {"OPENING_LOCK_PRIOR_REFS_V1": "1"}):
            self.assertEqual(_prior_refs(m), {"prior_vah": 7550.0, "prior_val": 7520.0, "pdh": 7560.0, "pdl": 7500.0})

    def test_refs_fail_open(self):
        with mock.patch.dict(os.environ, {"OPENING_LOCK_PRIOR_REFS_V1": "1"}):
            self.assertEqual(_prior_refs(SimpleNamespace()), {})

    def test_lock_reads_auction_out_only_with_references(self):
        bars = _rotational_open_outside_prior_range()
        with mock.patch.dict(os.environ, {"OPENING_LOCK_PRIOR_REFS_V1": "0", "OPENING_DALTON_GAPS_V1": "1"}):
            m = _machine(); update_opening_lock(machine=m, rth_bars=bars, ib_locked=True, now_iso="2026-10-18T10:30:00-04:00")
            self.assertEqual(getattr(m, "_opening_locked_val", None), "OPEN_AUCTION_IN")      # legacy: location unknown → IN
        with mock.patch.dict(os.environ, {"OPENING_LOCK_PRIOR_REFS_V1": "1", "OPENING_DALTON_GAPS_V1": "1"}):
            m = _machine(); update_opening_lock(machine=m, rth_bars=bars, ib_locked=True, now_iso="2026-10-18T10:30:00-04:00")
            self.assertEqual(getattr(m, "_opening_locked_val", None), "OPEN_AUCTION_OUT")


if __name__ == "__main__":
    unittest.main()
