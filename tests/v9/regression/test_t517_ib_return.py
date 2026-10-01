# -*- coding: utf-8 -*-
"""T-517 (29.09): the IB-return state — the IB broke down, the price is taking the extension back (returning) or is
back inside the IB (failed). Built from 28.09 (Michael "כן" to: the 19:15 return, +43 pts, while every long died on
tree:bias): IB 7758.75-7775.25 · breakdown 17:35 · low 7726.0 at 17:55 · 19:20 closed 7768.25 back inside."""
import os
import unittest

from backend.v9.services.ib_return import (bucket_start, extension_extreme_epoch, flow_ok, ib_return_rel,
                                           ib_return_state, release_modes)

# 28.09 RTH 5-min bars (IL time) — high, low, close — from v9_bars_5min_woodies
B = [("16:30", 7775.25, 7763.75, 7766.5), ("16:35", 7766.5, 7758.75, 7764.0), ("16:40", 7766.75, 7759.25, 7765.25),
     ("16:45", 7772.75, 7762.5, 7769.5), ("16:50", 7774.75, 7764.5, 7772.0), ("16:55", 7773.5, 7765.5, 7773.0),
     ("17:00", 7773.75, 7765.75, 7766.25), ("17:05", 7770.0, 7763.5, 7767.0), ("17:10", 7767.75, 7759.25, 7762.0),
     ("17:15", 7766.5, 7760.0, 7764.5), ("17:20", 7768.75, 7761.25, 7766.25), ("17:25", 7767.75, 7762.75, 7764.0),
     ("17:30", 7764.25, 7760.0, 7761.5), ("17:35", 7762.25, 7753.0, 7753.75), ("17:40", 7755.0, 7741.25, 7741.5),
     ("17:45", 7742.5, 7727.75, 7731.5), ("17:50", 7737.5, 7728.0, 7728.25), ("17:55", 7734.0, 7726.0, 7730.75),
     ("18:00", 7736.75, 7730.5, 7735.0), ("18:05", 7746.25, 7732.75, 7746.0), ("18:10", 7747.5, 7740.0, 7741.0),
     ("18:15", 7742.25, 7737.0, 7740.5), ("18:20", 7740.5, 7735.5, 7738.0), ("18:25", 7742.25, 7735.75, 7740.25),
     ("18:30", 7741.5, 7736.5, 7740.25), ("18:35", 7746.75, 7738.75, 7746.5), ("18:40", 7746.75, 7736.0, 7739.0),
     ("18:45", 7740.25, 7736.5, 7738.5), ("18:50", 7741.75, 7737.5, 7741.5), ("18:55", 7745.25, 7741.25, 7744.5),
     ("19:00", 7745.75, 7740.75, 7742.25), ("19:05", 7746.5, 7740.75, 7745.5), ("19:10", 7748.0, 7742.5, 7743.5),
     ("19:15", 7758.5, 7742.75, 7755.5), ("19:20", 7769.5, 7753.5, 7768.25), ("19:25", 7786.0, 7767.5, 7777.25)]
BARS = [dict(t=t, h=h, l=l, c=c) for t, h, l, c in B]


def upto(hhmm):
    """closed bars at decision time hhmm: bars whose start + 5 min <= hhmm"""
    m = int(hhmm[:2]) * 60 + int(hhmm[3:])
    return [b for b in BARS if int(b["t"][:2]) * 60 + int(b["t"][3:]) + 5 <= m]


class TestIbReturn(unittest.TestCase):
    def test_ib_forming_then_inside(self):
        self.assertEqual(ib_return_state(upto("17:30"))["state"], "forming")      # 12 bars = the IB itself
        self.assertEqual(ib_return_state(upto("17:35"))["state"], "inside")

    def test_breakdown_is_extended(self):
        st = ib_return_state(upto("17:40"))
        self.assertEqual((st["state"], st["ib_lo"], st["ib_hi"]), ("extended_down", 7758.75, 7775.25))

    def test_half_of_the_extension_taken_back_is_returning(self):
        self.assertEqual(ib_return_state(upto("19:00"))["state"], "returning_down")   # 18:55 closed 7744.5 ≥ 7742.375
        self.assertEqual(ib_return_state(upto("19:05"))["state"], "extended_down")    # 19:00 closed 7742.25 < 7742.375
        self.assertEqual(ib_return_rel(ib_return_state(upto("19:00")), "LONG"), "with_returning")

    def test_back_inside_the_ib_is_failed(self):
        st = ib_return_state(upto("19:25"))                                            # 19:20 closed 7768.25
        self.assertEqual(st["state"], "failed_down")
        self.assertEqual(ib_return_rel(st, "LONG"), "with_failed")
        self.assertEqual(ib_return_rel(st, "SHORT"), "against_return")

    def test_both_sides_extended_is_two_sided(self):
        self.assertEqual(ib_return_state(upto("19:30"))["state"], "two_sided")        # 19:25 high 7786 > IB high
        self.assertEqual(ib_return_rel(ib_return_state(upto("19:30")), "LONG"), "none")

    def test_release_modes_default_off(self):
        self.assertEqual(release_modes(None), ())
        self.assertEqual(release_modes("0"), ())
        self.assertEqual(release_modes("returning"), ("with_returning",))
        self.assertEqual(release_modes("both"), ("with_returning", "with_failed"))

    def test_order_flow_of_the_return(self):
        # 28.09 (v9_bars_5min_continuous, 15-min Sierra bars): the extreme 7726.0 is the 17:55 bar ⇒ bucket 17:45;
        # Σ delta of the buckets closed by 19:00 = 425 + 1421 + 1133 + 128 + 749 = +3,856 — buyers took it back
        bars_e = [dict(b, e=float(int(b["t"][:2]) * 60 + int(b["t"][3:])) * 60.0) for b in BARS]
        st = ib_return_state(upto("19:00"))
        closed_e = [b for b in bars_e if b["e"] / 60.0 + 5 <= 19 * 60]
        xe = extension_extreme_epoch(closed_e, st)
        self.assertEqual(xe, (17 * 60 + 55) * 60.0)
        self.assertEqual(bucket_start(xe, (16 * 60 + 30) * 60.0), (17 * 60 + 45) * 60.0)
        self.assertTrue(flow_ok(st, 3856.0))
        self.assertFalse(flow_ok(st, -10.0))
        self.assertTrue(flow_ok({"state": "returning_up"}, -5.0))
        self.assertFalse(flow_ok({"state": "inside"}, 100.0))
        self.assertIsNone(extension_extreme_epoch(closed_e, {"state": "inside"}))

    def test_gateway_releases_only_against_and_only_when_the_flag_is_set(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "v9", "gateway",
                                "trading_gateway.py"), encoding="utf-8").read()
        i = src.index("T-517 IB-return state")
        blk = src[i:i + 2200]
        self.assertIn('os.getenv("IB_RETURN_HINT_RELEASE_V1", "0")', blk)
        self.assertIn('_t3_vec.get("rel_bias") == "against"', blk)
        blk2 = src[i:i + 4200]
        self.assertIn('os.getenv("IB_RETURN_RELEASE_FLOW", "0")', blk2)
        self.assertIn("ts + interval '15 minutes' <= now()", blk2)          # the 15-min flow bucket is CLOSED
        self.assertLess(i, src.index("_tree_leaf, _t3_path = _dt3.walk(_dt3.load_tree(), _t3_vec)"))


if __name__ == "__main__":
    unittest.main()


class TestT523Acceptance(unittest.TestCase):
    """T-523 (01.10): release after a failed extension only once value accepts the return."""

    def _failed_down(self, last):
        # IB 7682.25-7740.25 (mid 7711.25), extended to 7672.75, last close back inside
        ib = [{"h": 7740.25, "l": 7682.25, "c": 7700.0}] * 12
        post = [{"h": 7690.0, "l": 7672.75, "c": 7677.75}, {"h": max(last, 7690.0), "l": 7685.0, "c": last}]
        return ib_return_state(ib + post)

    def test_labels_follow_acceptance(self):
        from backend.v9.services.ib_return import ib_return_rels
        st = self._failed_down(7692.5)                      # 18:15 close — inside, below mid, below POC
        self.assertEqual(st["state"], "failed_down"); self.assertEqual(st["ib_mid"], 7711.25)
        self.assertEqual(ib_return_rels(st, "LONG", "below"), ("with_failed",))
        self.assertEqual(ib_return_rels(st, "LONG", "above"), ("with_failed", "with_failed_poc"))   # 19:00 POC crossed
        st2 = self._failed_down(7721.75)                    # 20:20 close above the IB midpoint
        self.assertEqual(ib_return_rels(st2, "LONG", "above"), ("with_failed", "with_failed_mid", "with_failed_poc"))
        self.assertEqual(ib_return_rels(st2, "SHORT", "above"), ("against_return",))
        self.assertEqual(ib_return_rels({"state": "returning_down"}, "LONG"), ("with_returning",))
        self.assertEqual(ib_return_rels({"state": "inside"}, "LONG"), ())

    def test_modes(self):
        self.assertEqual(release_modes("accepted_mid"), ("with_returning", "with_failed_mid"))
        self.assertEqual(release_modes("accepted_poc"), ("with_returning", "with_failed_poc"))
        self.assertEqual(release_modes("accepted_any"), ("with_returning", "with_failed_mid", "with_failed_poc"))
        # the live mode is unchanged
        self.assertEqual(release_modes("returning"), ("with_returning",))
