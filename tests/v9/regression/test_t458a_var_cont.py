# -*- coding: utf-8 -*-
"""T-458א — VAR_CONT_V1, the with-extension pullback-continuation producer (one contract).

Parity pin: on the 23.09 RTH bars the producer must fire exactly where the measured model rule
CONT_1S fired (scripts/variation_playbook_test.py, 24.09): 18:45 SHORT @7779.50 stop 7789.52 ·
20:20 SHORT @7766.00 stop 7774.25 · 21:00 SHORT @7776.25 stop 7785.50 — and nothing from 22:00
(measured: 22:xx entries n=14 Σ−$183, 21% — the EOD cuts them). Flag off ⇒ enabled() is False and
the five_min hook returns before touching anything.
"""
import json
import os
import unittest
from unittest import mock

if not os.getenv("BRIDGE_TOKEN"):
    os.environ["BRIDGE_TOKEN"] = "test-token-for-isolation"

from backend.v9.systems import var_cont as vc

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "rth_bars_2026-09-23.json")


def _bars():
    with open(FIX, encoding="utf-8") as fh:
        return json.load(fh)


class TestVarContParity(unittest.TestCase):
    def test_fires_exactly_where_the_measured_model_fired(self):
        bs = _bars()
        hits = {}
        with mock.patch.dict(os.environ, {"T1_BANK_R": "1.5", "VAR_CONT_CUTOFF_IL": "22:00"}, clear=False):
            for i in range(12, len(bs)):
                tr = vc.detect(bs[:i + 1])
                if tr:
                    hits[bs[i]["t"][:5]] = tr
        self.assertEqual(sorted(hits), ["18:45", "20:20", "21:00"])
        self.assertEqual((hits["18:45"]["direction"], hits["18:45"]["entry"], hits["18:45"]["stop"]), ("SHORT", 7779.5, 7789.52))
        self.assertEqual((hits["20:20"]["direction"], hits["20:20"]["entry"], hits["20:20"]["stop"]), ("SHORT", 7766.0, 7774.25))
        self.assertEqual((hits["21:00"]["direction"], hits["21:00"]["entry"], hits["21:00"]["stop"]), ("SHORT", 7776.25, 7785.5))
        self.assertEqual(hits["18:45"]["via"], "opening_drive")
        self.assertEqual(hits["20:20"]["via"], "ib_extension")
        # t1 = 1.5R below entry for a short
        for h in hits.values():
            r = abs(h["entry"] - h["stop"])
            self.assertAlmostEqual(h["entry"] - h["t1"], 1.5 * r, delta=0.02)

    def test_cutoff_keeps_the_late_entries_out(self):
        bs = _bars()
        late = []
        with mock.patch.dict(os.environ, {"VAR_CONT_CUTOFF_IL": "23:00"}, clear=False):
            for i in range(12, len(bs)):
                tr = vc.detect(bs[:i + 1])
                if tr and tr["bar_il"] >= "22:00":
                    late.append(tr["bar_il"])
        self.assertTrue(late, "with the cutoff lifted the 22:xx bars do trigger")
        with mock.patch.dict(os.environ, {"VAR_CONT_CUTOFF_IL": "22:00"}, clear=False):
            for i in range(12, len(bs)):
                tr = vc.detect(bs[:i + 1])
                if tr:
                    self.assertLess(tr["bar_il"], "22:00")

    def test_needs_the_ib_and_a_one_sided_day(self):
        bs = _bars()
        self.assertIsNone(vc.detect(bs[:12]))            # IB not locked yet
        # both IB edges exceeded ⇒ not one-sided ⇒ no trigger anywhere
        two_sided = [dict(b) for b in bs]
        two_sided[13]["h"] = max(x["h"] for x in bs[:12]) + 5.0   # poke above the IB high early
        with mock.patch.dict(os.environ, {"VAR_CONT_CUTOFF_IL": "23:00"}, clear=False):
            for i in range(14, len(two_sided)):
                tr = vc.detect(two_sided[:i + 1])
                if tr:
                    self.assertNotEqual(tr["via"], "ib_extension")

    def test_flag_and_setup(self):
        with mock.patch.dict(os.environ, {"VAR_CONT_V1": "0"}, clear=False):
            self.assertFalse(vc.enabled())
        with mock.patch.dict(os.environ, {"VAR_CONT_V1": "shadow"}, clear=False):
            self.assertTrue(vc.enabled()); self.assertTrue(vc.is_shadow())
        with mock.patch.dict(os.environ, {"VAR_CONT_V1": "1"}, clear=False):
            self.assertTrue(vc.enabled()); self.assertFalse(vc.is_shadow())
        trig = {"direction": "SHORT", "entry": 7766.0, "stop": 7774.25, "t1": 7753.62, "via": "ib_extension", "ext": "down"}
        s = vc.build_setup(trig, shadow=True)
        self.assertEqual((s["classification"], s["direction"], s["entry_price"], s["stop"], s["t1"]), ("VAR_CONT", "SHORT", 7766.0, 7774.25, 7753.62))
        self.assertTrue(s["metadata"]["shadow_only"]); self.assertEqual(s["metadata"]["entry_kind"], "PULLBACK")
        self.assertFalse(vc.build_setup(trig, shadow=False)["metadata"]["shadow_only"])


if __name__ == "__main__":
    unittest.main()
