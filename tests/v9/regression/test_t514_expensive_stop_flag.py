# -*- coding: utf-8 -*-
"""T-514 (29.09): ELQ_EXPENSIVE_STOP_V1 — the expensive-stop arm of ELQ blocks only when the flag is on.
Default (unset/0) keeps the 10.09 shadow (compute + log, never block). 28.09 #2483 OPENING_EXTREME_REJECT:
stop 13.2 vs ATR 5.6 ⇒ rr 2.37 > 1.5 — the shadow said "would block", the trade lost 61.25$ at the broker."""
import os
import unittest

from backend.v9.systems.entry_location_quality import assess_entry_quality

KW = dict(entry_price=7771.5, direction="LONG", leg_base=None, leg_extreme=None, stop_distance=13.25, atr=5.6,
          vah=None, val=None)


class TestExpensiveStopFlag(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("ELQ_EXPENSIVE_STOP_V1", None)

    def test_default_is_shadow(self):
        os.environ.pop("ELQ_EXPENSIVE_STOP_V1", None)
        r = assess_entry_quality(**KW)
        self.assertTrue(r["pass"])
        self.assertFalse(any("expensive_stop" in x for x in r["reasons"]))

    def test_flag_on_blocks_a_wide_stop(self):
        os.environ["ELQ_EXPENSIVE_STOP_V1"] = "1"
        r = assess_entry_quality(**KW)
        self.assertFalse(r["pass"])
        self.assertTrue(any(x.startswith("expensive_stop") for x in r["reasons"]))

    def test_flag_on_passes_a_normal_stop(self):
        os.environ["ELQ_EXPENSIVE_STOP_V1"] = "1"
        r = assess_entry_quality(**dict(KW, stop_distance=6.0))
        self.assertTrue(r["pass"])


if __name__ == "__main__":
    unittest.main()
