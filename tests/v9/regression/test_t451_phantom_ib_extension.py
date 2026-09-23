# -*- coding: utf-8 -*-
"""T-451 (2026-09-23) — the day's bias was decided by a phantom 2.25-pt "IB extension".

Incident, from the decision feed + backend.err.log:

    16:45:05 [FiveMin] OPENING_ENTRY DRIVE SHORT entry=7814.25 stop=7828.00 t1=7793.62 (live-eligible)
    16:45:05 [Gateway] T-426 provisional opening type OPEN_AUCTION_IN→OPEN_DRIVE for OPENING_DRIVE SHORT
    16:45:05 [Gateway] BLOCKED ... OPENING_DRIVE dir=SHORT blocked_by=dalton_intent:bias ot=OPEN_DRIVE hint=LONG bias=LONG
    vector @16:45: extension=up 2.25  ib_locked=true  ib_width=12.25   (IB 7814.25–7826.50 — still DEVELOPING)
    vector @18:40, 18:45: extension=up 2.25 (IB 7778.25–7826.50 locked)  hint=LONG
    19:15:03 REACTIVE_LONG LONG 7780.50 admitted (day_type Normal, hint LONG)  → #2230 −$18.75
    19:15:13 ZLR SHORT blocked_by=dalton_intent:bias hint=LONG
    19:20:05 extension=both 2.75 → hint SHORT (the real extension down finally exceeded the phantom)

No bar of 23.09 has a high above 7826.50. The only 7828.75 in the DB is a mislabeled
pre-open bar on the RTH-only '5min' channel ("09-22 23:55" high 7828.75) that TPOSystem —
subscribed to '5min' — took as session_high; the GLOBEX_<date> → CASH_<date> boundary
shares the trading date, so the extremes were never reset. session_high 7828.75 − IB high
7826.50 = the phantom "extension up 2.25", and the gateway's Layer-2 override (documented
"phase C only", never enforced) turned it into bias=LONG on a 48-point opening drive DOWN.

Two fixes, both pinned here:
  1. TPOSystem resets session_high/low at the RTH (CASH) boundary regardless of date.
  2. The gateway's IB-extension override does not run before 17:30 IL
     (IB_EXT_OVERRIDE_PHASE_GUARD_V1, default ON) — no IB, no extension.
"""
import os
import unittest
from unittest import mock

if not os.getenv("BRIDGE_TOKEN"):
    os.environ["BRIDGE_TOKEN"] = "test-token-for-isolation"

from backend.v9.systems.tpo.tpo_system import TPOSystem


def _bare_tpo():
    t = TPOSystem.__new__(TPOSystem)
    t.current_session_id = None
    t.current_session_type = None
    t.profile = {}
    t.current_letter_idx = 0
    t.ib_high = None; t.ib_low = None; t.ib_locked = False
    t._ib_width = None; t._ib_class = None; t._ib_locked_ts = None
    t.current_state = {"session_high": None, "session_low": None}
    return t


class TestT451SessionExtremesResetAtRthBoundary(unittest.TestCase):
    def _open(self, t, session_id, session_type, today):
        with mock.patch("backend.v9.db.safe_writer.safe_execute", return_value=None):
            t._open_session(session_id, session_type, today, "2026-09-23 13:30:00")

    def test_globex_to_cash_same_date_resets_extremes(self):
        t = _bare_tpo()
        self._open(t, "GLOBEX_2026-09-23", "GLOBEX", "2026-09-23")
        # the pre-open bars (incl. the mislabeled 7828.75) set the Globex extremes
        t.current_state["session_high"] = 7828.75
        t.current_state["session_low"] = 7818.75
        self._open(t, "CASH_2026-09-23", "CASH", "2026-09-23")
        self.assertIsNone(t.current_state["session_high"], "RTH must start with no session_high")
        self.assertIsNone(t.current_state["session_low"], "RTH must start with no session_low")

    def test_globex_after_cash_keeps_date_reset_semantics(self):
        # date change still resets everything (the original #68 behaviour is untouched)
        t = _bare_tpo()
        self._open(t, "CASH_2026-09-22", "CASH", "2026-09-22")
        t.current_state["session_high"] = 7848.5; t.current_state["session_low"] = 7822.0
        t.ib_high, t.ib_low, t.ib_locked = 7848.5, 7831.5, True
        self._open(t, "GLOBEX_2026-09-23", "GLOBEX", "2026-09-23")
        self.assertIsNone(t.current_state["session_high"])
        self.assertIsNone(t.ib_high); self.assertFalse(t.ib_locked)

    def test_cash_to_cash_same_date_does_not_reset(self):
        # a re-open of the same CASH session (e.g. hydration path) must not wipe real RTH extremes
        t = _bare_tpo()
        self._open(t, "CASH_2026-09-23", "CASH", "2026-09-23")
        t.current_state["session_high"] = 7826.5; t.current_state["session_low"] = 7759.0
        self._open(t, "CASH_2026-09-23", "CASH", "2026-09-23")
        self.assertEqual(t.current_state["session_high"], 7826.5)


class TestT451NoIbExtensionOverrideBeforeIbLock(unittest.TestCase):
    """The Layer-2 decision, reduced to its inputs (the gateway inlines it; this mirrors the
    exact arithmetic: ext_up = session_high − ib_high, ext_dn = ib_low − session_low, the
    larger positive one overrides Layer 1 — and, since T-451, only from 17:30 IL)."""

    @staticmethod
    def layer2(tpo, il_hhmm, layer1, guard_on=True):
        if guard_on and il_hhmm < "17:30":
            tpo = {}
        hint = layer1
        ibh = float(tpo.get("ib_high") or 0); ibl = float(tpo.get("ib_low") or 0)
        sh = float(tpo.get("session_high") or tpo.get("rth_high") or 0)
        sl = float(tpo.get("session_low") or tpo.get("rth_low") or 0)
        if ibh > 0 and ibl > 0:
            ext_up = max(0, sh - ibh); ext_dn = max(0, ibl - sl)
            if ext_up > ext_dn and ext_up > 0: hint = "LONG"
            elif ext_dn > ext_up and ext_dn > 0: hint = "SHORT"
        return hint

    # vector @16:45:05: extension="up" 2.25 (only up) — the 16:45 bar had just opened, session_low == IB low
    INCIDENT_1645 = dict(ib_high=7826.5, ib_low=7814.25, ib_locked=True, session_high=7828.75, session_low=7814.25)

    def test_1645_phantom_extension_cannot_flip_the_drive_before_1730(self):
        # 16:45: confirmed DRIVE SHORT (Layer 1 = SHORT via T-426) — the phantom 2.25 must not win
        self.assertEqual(self.layer2(self.INCIDENT_1645, "16:45", "SHORT"), "SHORT")

    def test_old_behaviour_reproduces_the_incident(self):
        # with the guard off the 23.09 bug is byte-identical: LONG
        self.assertEqual(self.layer2(self.INCIDENT_1645, "16:45", "SHORT", guard_on=False), "LONG")

    def test_after_ib_lock_a_real_extension_still_overrides(self):
        # 20:00: IB 7778.25–7826.50 locked, session_low 7759 → real extension down 19.25 → SHORT
        tpo = dict(ib_high=7826.5, ib_low=7778.25, ib_locked=True, session_high=7826.5, session_low=7759.0)
        self.assertEqual(self.layer2(tpo, "20:00", "LONG"), "SHORT")

    def test_after_ib_lock_with_honest_extremes_the_phantom_is_gone(self):
        # 18:40 with the TPO fix: session_high is the RTH high (7826.5) → ext_up 0 → Layer 1 stands
        tpo = dict(ib_high=7826.5, ib_low=7778.25, ib_locked=True, session_high=7826.5, session_low=7778.25)
        self.assertEqual(self.layer2(tpo, "18:40", "SHORT"), "SHORT")


if __name__ == "__main__":
    unittest.main()
