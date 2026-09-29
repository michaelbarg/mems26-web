# -*- coding: utf-8 -*-
"""T-515 (29.09): the real-time turn state — a double top/bottom at the session extreme from CLOSED bars.
Built from 28.09 (Michael: "היה תקרה כפולה … המערכת צריכה לדעת לבצע את השורט בזמן, ובסוף היא קנתה בהיפוך"):
tops 16:30 7775.25 · 16:50 7774.75 with a 16.5-pt pullback ⇒ down from 16:55; the IB low retested at 17:10 ⇒ range
(17:25 VEGAS LONG @7766.5 is mid-range); the 17:35 breakdown ⇒ down again."""
import os
import unittest

from backend.v9.services.turn_state import detect_turn, turn_rel

# 28.09 RTH 5-min bars (IL time) — high, low, close — from v9_bars_5min_woodies
B = [("16:30", 7775.25, 7763.75, 7766.5), ("16:35", 7766.5, 7758.75, 7764.0), ("16:40", 7766.75, 7759.25, 7765.25),
     ("16:45", 7772.75, 7762.5, 7769.5), ("16:50", 7774.75, 7764.5, 7772.0), ("16:55", 7773.5, 7765.5, 7773.0),
     ("17:00", 7773.75, 7765.75, 7766.25), ("17:05", 7770.0, 7763.5, 7767.0), ("17:10", 7767.75, 7759.25, 7762.0),
     ("17:15", 7766.5, 7760.0, 7764.5), ("17:20", 7768.75, 7761.25, 7766.25), ("17:25", 7767.75, 7762.75, 7764.0),
     ("17:30", 7764.25, 7760.0, 7761.5), ("17:35", 7762.25, 7753.0, 7753.75), ("17:40", 7755.0, 7741.25, 7741.5)]
BARS = [dict(t=t, h=h, l=l, c=c) for t, h, l, c in B]


def upto(hhmm):
    """closed bars at decision time hhmm: bars whose start + 5 min <= hhmm"""
    m = int(hhmm[:2]) * 60 + int(hhmm[3:])
    return [b for b in BARS if int(b["t"][:2]) * 60 + int(b["t"][3:]) + 5 <= m]


class TestTurnState(unittest.TestCase):
    def test_no_turn_before_the_second_top_closes(self):
        self.assertEqual(detect_turn(upto("16:50"))["turn"], "none")        # the 16:50 live long: nothing yet

    def test_double_top_is_down_at_1655(self):
        st = detect_turn(upto("16:55"))
        self.assertEqual((st["turn"], st["level"]), ("down", 7775.25))
        self.assertEqual(turn_rel(st, "SHORT", 7772.0), "with")           # TOUCH2 SHORT at the double top
        self.assertEqual(turn_rel(st, "LONG", 7771.0), "against")

    def test_range_when_both_extremes_are_defended(self):
        st = detect_turn(upto("17:25"))
        self.assertEqual(st["turn"], "range")
        self.assertEqual(turn_rel(st, "LONG", 7766.5), "mid")              # the 17:25 live VEGAS long
        self.assertEqual(turn_rel(st, "SHORT", 7774.0), "edge")
        self.assertEqual(turn_rel(st, "LONG", 7759.5), "edge")

    def test_breakdown_resets_the_bottom(self):
        self.assertEqual(detect_turn(upto("17:45"))["turn"], "down")      # new low 7741.25 ⇒ the double bottom is gone

    def test_too_few_bars(self):
        self.assertEqual(detect_turn(BARS[:2])["turn"], "none")
        self.assertEqual(turn_rel({"turn": "none"}, "LONG", 1.0), "none")

    def test_gateway_reads_closed_bars_only_and_feeds_the_vector(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "v9", "gateway",
                                "trading_gateway.py"), encoding="utf-8").read()
        i = src.index("_t3_turn = {\"turn\": \"none\"}")
        blk = src[i:i + 1800]
        self.assertIn("ts + interval '5 minutes' <= now()", blk)
        self.assertIn('_t3_vec["turn_rel"] = _t3_ts.turn_rel(', blk)
        from backend.v9.services import decision_tree as dt3
        self.assertIn("turn", dt3.FEATURES)
        self.assertIn("turn_rel", dt3.FEATURES)


if __name__ == "__main__":
    unittest.main()
