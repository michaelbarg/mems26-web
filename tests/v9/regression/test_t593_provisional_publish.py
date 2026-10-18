# -*- coding: utf-8 -*-
"""T-593 (18.10, cowork): S1_PROVISIONAL_PUBLISH_V1 — the canonical classifier runs from the 30-minute mark so its
P0-2 provisional-from-the-open is what gets published before the IB lock.

Finding (fwd_harness S1 timelines): the first published day-type label was "Trend_Normal" in 154/166 reconstructed
sessions and 67/70 live-era sessions — the legacy state machine's TRENDING behaviour at 30 min — demoted to
Variation 10-25 min later and replaced by the canonical label only at the lock (main.py ran classify_session only
when `day_type_machine.ib_locked`). A fixed sequence independent of the market, and the tree's phase-B `day_type`.
"""
import os
import unittest
from unittest import mock

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")


def _src(rel):
    return open(os.path.join(ROOT, rel), encoding="utf-8").read()


class TestGateStrings(unittest.TestCase):
    def test_main_runs_the_classifier_from_30_minutes_under_the_flag(self):
        s = _src("backend/main.py")
        self.assertIn('_S1_PROV_PUB = _os.environ.get("S1_PROVISIONAL_PUBLISH_V1", "0")', s)
        self.assertIn("if _S1_NEW_CLS and (day_type_machine.ib_locked or (_S1_PROV_PUB and len(_cls_rth_bars) >= 6)):", s)
        self.assertIn("if len(_cls_rth_bars) >= (12 if day_type_machine.ib_locked else 6):", s)
        self.assertIn('if not _stab_st.get("_first_lock_done") and day_type_machine.ib_locked:', s)

    def test_harness_mirrors_main(self):
        s = _src("scripts/fwd_harness.py")
        self.assertIn("if _S1_NEW_CLS and (dtm.ib_locked or (_S1_PROV_PUB and len(_cls_rth_bars) >= 6)):", s)
        self.assertIn("if len(_cls_rth_bars) >= (12 if dtm.ib_locked else 6):", s)
        self.assertIn('if not _stab_st.get("_first_lock_done") and dtm.ib_locked:', s)


def _bars(n, o=7500.0, step=1.0):
    return [{"o": o + i * step, "h": o + i * step + 2, "l": o + i * step - 1, "c": o + (i + 1) * step, "v": 1000} for i in range(n)]


class TestClassifierBeforeLock(unittest.TestCase):
    """With 6 bars and the running extremes as the IB stand-in, classify_session never raises and, with the P0-2
    provisional on, never answers bare FORMING — the published label before the lock comes from the open."""
    def test_six_bars_running_extremes_provisional(self):
        from backend.v9.systems.day_type.classifier_core import classify_session
        bars = _bars(6)
        with mock.patch.dict(os.environ, {"S1_COMMITTED_PROVISIONAL_V1": "1", "S1_ACCEPTANCE_RECLASS_V1": "0"}):
            r = classify_session(bars=bars, ib_high=max(b["h"] for b in bars), ib_low=min(b["l"] for b in bars),
                                 open_price=bars[0]["o"], prior_vah=7520.0, prior_val=7480.0, pdh=7540.0, pdl=7460.0)
        self.assertNotEqual(r.get("day_type"), "FORMING")
        self.assertIn(r.get("status"), ("PROVISIONAL", "CLASSIFIED"))

    def test_six_bars_without_the_provisional_flag_is_forming(self):
        from backend.v9.systems.day_type.classifier_core import classify_session
        bars = _bars(6)
        with mock.patch.dict(os.environ, {"S1_COMMITTED_PROVISIONAL_V1": "0", "S1_ACCEPTANCE_RECLASS_V1": "0"}):
            r = classify_session(bars=bars, ib_high=max(b["h"] for b in bars), ib_low=min(b["l"] for b in bars),
                                 open_price=bars[0]["o"], prior_vah=7520.0, prior_val=7480.0, pdh=7540.0, pdl=7460.0)
        self.assertEqual(r.get("day_type"), "FORMING")


if __name__ == "__main__":
    unittest.main()
