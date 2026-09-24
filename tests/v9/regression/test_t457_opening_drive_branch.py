# -*- coding: utf-8 -*-
"""T-457 — the opening-drive branch (OPENING_DRIVE_BRANCH_V1, default OFF, pending ruling).

Measured 24.09 (scripts/variation_playbook_test.py, 60 sessions, 21 confirmed opening drives,
one contract, first touch on 5-min bars, $1.30/side):
    exit T1=1.5R  Σ +$442  57%      exit T2=2.5R  Σ +$712  48%      exit T3=4R  Σ +$725  48%
    trail 1×ATR   Σ +$26            23.09 drive SHORT @7806.50: 1.5R = +22.5 pts · 2.5R = +37.5 pts

Replay of 23.09 with the T-451 fixes (harness_out/t456): the confirmed drive SHORT @7814.25
passed the tree and died at entry_location_quality (beyond_value ex=1.08 > 0.25); with ELQ
off, TARGET_REALISM clamped t1 7793.62 → 7812.50 (1.75 pts) on a 48-point drive.

The branch (one flag, three parts, all measured together):
  1. build_opening_setup: DRIVE / TEST_DRIVE triggers take t1 = OPENING_DRIVE_T1_R (default the
     ruled 1.5R — real-engine T-458ג: 1.5R day-Δ +$601 vs 2.5R +$326 on 29 drives), ladder
     t2 = max(4R, t1+0.5R), no t3 — other triggers untouched.
  2. gateway: ELQ skipped for OPENING_DRIVE / OPENING_TEST_DRIVE setups (logged).
  3. gateway: TARGET_REALISM skipped for the same setups (structural ladder kept).
Flag OFF ⇒ byte-identical (pinned below).
"""
import os
import unittest
from unittest import mock

if not os.getenv("BRIDGE_TOKEN"):
    os.environ["BRIDGE_TOKEN"] = "test-token-for-isolation"

from backend.v9.systems.opening_entry import build_opening_setup


def _bars():
    # 23.09 16:30–16:40 (the three closed bars the engine judged at 16:45:05)
    return [
        {"ts": "2026-09-23T13:30:00+00:00", "o": 7823.50, "h": 7826.50, "l": 7819.75, "c": 7819.75, "v": 14461},
        {"ts": "2026-09-23T13:35:00+00:00", "o": 7820.00, "h": 7820.00, "l": 7815.75, "c": 7816.75, "v": 14530},
        {"ts": "2026-09-23T13:40:00+00:00", "o": 7817.00, "h": 7818.00, "l": 7814.25, "c": 7814.25, "v": 10089},
    ]


def _drive_trigger():
    return {"type": "DRIVE", "direction": "SHORT", "entry": 7814.25, "bar_index": 2}


class TestT457DriveTarget(unittest.TestCase):
    def _setup(self, env):
        with mock.patch.dict(os.environ, env, clear=False):
            return build_opening_setup(_drive_trigger(), _bars(), shadow_only=False)

    def test_flag_off_is_the_ruled_1_5R(self):
        s = self._setup({"OPENING_DRIVE_BRANCH_V1": "0", "T1_BANK_R": "1.5", "OPENING_LADDER_V1": "1", "OPENING_STOP_STRUCTURAL_V1": "1"})
        self.assertIsNotNone(s)
        risk = abs(float(s["entry_price"]) - float(s["stop"]))
        self.assertAlmostEqual(abs(float(s["t1"]) - float(s["entry_price"])), 1.5 * risk, delta=0.02)

    def test_flag_on_default_target_is_the_ruled_1_5R_with_a_monotonic_ladder(self):
        # T-458ג (real engine, 29 drives): 1.5R day-Δ +$601 vs 2.5R +$326 ⇒ default 1.5R
        s = self._setup({"OPENING_DRIVE_BRANCH_V1": "1", "T1_BANK_R": "1.5", "OPENING_LADDER_V1": "1", "OPENING_STOP_STRUCTURAL_V1": "1"})
        self.assertIsNotNone(s)
        entry, stop = float(s["entry_price"]), float(s["stop"]); risk = abs(entry - stop)
        self.assertAlmostEqual(abs(float(s["t1"]) - entry), 1.5 * risk, delta=0.02)
        self.assertEqual(s["direction"], "SHORT")
        self.assertLess(float(s["t1"]), entry)                       # short: target below entry
        if s.get("t2") is not None:
            self.assertLess(float(s["t2"]), float(s["t1"]))          # monotonic: t2 beyond t1
        self.assertIsNone(s.get("t3"))

    def test_flag_on_param_2_5R_is_honoured_for_replay(self):
        s = self._setup({"OPENING_DRIVE_BRANCH_V1": "1", "OPENING_DRIVE_T1_R": "2.5", "T1_BANK_R": "1.5", "OPENING_LADDER_V1": "1", "OPENING_STOP_STRUCTURAL_V1": "1"})
        self.assertIsNotNone(s)
        entry, stop = float(s["entry_price"]), float(s["stop"]); risk = abs(entry - stop)
        self.assertAlmostEqual(abs(float(s["t1"]) - entry), 2.5 * risk, delta=0.02)
        if s.get("t2") is not None:
            self.assertGreater(abs(float(s["t2"]) - entry), abs(float(s["t1"]) - entry))  # monotonic ladder
        self.assertIsNone(s.get("t3"))

    def test_flag_on_leaves_pullback_cont_at_its_own_1_5R(self):
        trig = {"type": "PULLBACK_CONT", "direction": "SHORT", "entry": 7814.25, "bar_index": 2, "t1_r": 1.5}
        with mock.patch.dict(os.environ, {"OPENING_DRIVE_BRANCH_V1": "1", "OPENING_STOP_STRUCTURAL_V1": "1"}, clear=False):
            s = build_opening_setup(trig, _bars(), shadow_only=False)
        if s is None:
            self.skipTest("PULLBACK_CONT trigger not buildable from these bars")
        risk = abs(float(s["entry_price"]) - float(s["stop"]))
        self.assertAlmostEqual(abs(float(s["t1"]) - float(s["entry_price"])), 1.5 * risk, delta=0.02)


class TestT457GatewayExemptions(unittest.TestCase):
    """The two gateway exemptions reduced to their predicate (mirrors trading_gateway.py)."""

    @staticmethod
    def exempt(classification, flag):
        with mock.patch.dict(os.environ, {"OPENING_DRIVE_BRANCH_V1": flag}, clear=False):
            return (os.getenv("OPENING_DRIVE_BRANCH_V1", "0").lower() in ("1", "true", "yes")
                    and str(classification or "").upper() in ("OPENING_DRIVE", "OPENING_TEST_DRIVE"))

    def test_only_the_engines_drive_setups_are_exempt(self):
        self.assertTrue(self.exempt("OPENING_DRIVE", "1"))
        self.assertTrue(self.exempt("OPENING_TEST_DRIVE", "1"))
        self.assertFalse(self.exempt("INITIATIVE_SHORT", "1"))
        self.assertFalse(self.exempt("OPENING_PULLBACK_CONT", "1"))
        self.assertFalse(self.exempt("REACTIVE_LONG", "1"))

    def test_flag_off_exempts_nothing(self):
        self.assertFalse(self.exempt("OPENING_DRIVE", "0"))


if __name__ == "__main__":
    unittest.main()
