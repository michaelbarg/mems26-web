"""DALTON_PLAYBOOK_V1 — session-phase decision tree tests.

Each row in the tree is a test. Mutation: flipping bias → fails.
"""
import os
import unittest
from backend.v9.services.dalton_playbook import intent, evaluate_gate, entry_kind_for, Intent


class TestPhaseA(unittest.TestCase):

    def test_open_drive_phase_a(self):
        it = intent(opening_type="OPEN_DRIVE", now_il_hhmm="16:35",
                     direction_hint="LONG")
        self.assertEqual(it.bias, "LONG")
        self.assertIn("WITH_DRIVE", it.entry_kinds)
        self.assertEqual(it.size_frac, 0.5)
        self.assertTrue(it.runner)

    def test_no_drive_phase_a(self):
        it = intent(opening_type="UNKNOWN", now_il_hhmm="16:35")
        self.assertEqual(it.bias, "NONE")
        self.assertEqual(it.size_frac, 0.0)


class TestPhaseB(unittest.TestCase):

    def test_open_drive_phase_b(self):
        it = intent(opening_type="OPEN_DRIVE", now_il_hhmm="17:00",
                     direction_hint="SHORT")
        self.assertEqual(it.bias, "SHORT")
        self.assertIn("WITH_DRIVE", it.entry_kinds)
        self.assertIn("PULLBACK", it.entry_kinds)
        self.assertEqual(it.size_frac, 1.0)

    def test_otd_phase_b(self):
        it = intent(opening_type="OPEN_TEST_DRIVE", now_il_hhmm="17:00",
                     direction_hint="LONG")
        self.assertEqual(it.bias, "LONG")
        self.assertTrue(it.runner)

    def test_orr_phase_b(self):
        it = intent(opening_type="OPEN_REJECTION_REVERSE", now_il_hhmm="17:00",
                     direction_hint="LONG")
        # Reversal = opposite direction
        self.assertEqual(it.bias, "SHORT")
        self.assertIn("REVERSAL", it.entry_kinds)
        self.assertFalse(it.runner)

    def test_auction_in_phase_b(self):
        it = intent(opening_type="OPEN_AUCTION_IN", now_il_hhmm="17:00")
        self.assertEqual(it.bias, "BOTH")
        self.assertIn("EDGE_FADE", it.entry_kinds)
        self.assertEqual(it.size_frac, 0.5)

    def test_unknown_phase_b(self):
        it = intent(opening_type="UNKNOWN", now_il_hhmm="17:00")
        self.assertEqual(it.bias, "NONE")
        self.assertEqual(it.size_frac, 0.0)


class TestPhaseC(unittest.TestCase):

    def test_trend_normal(self):
        it = intent(day_type="Trend_Normal", now_il_hhmm="18:00",
                     direction_hint="LONG")
        self.assertEqual(it.bias, "LONG")
        self.assertIn("PULLBACK", it.entry_kinds)
        self.assertIn("BREAK", it.entry_kinds)
        self.assertTrue(it.runner)

    def test_trend_dd(self):
        it = intent(day_type="Trend_DD", now_il_hhmm="18:00",
                     direction_hint="SHORT")
        self.assertEqual(it.bias, "SHORT")
        self.assertTrue(it.runner)

    def test_variation(self):
        it = intent(day_type="Variation", now_il_hhmm="18:00",
                     direction_hint="LONG")
        self.assertIn(it.bias, ("LONG", "BOTH"))
        self.assertFalse(it.runner)

    def test_normal(self):
        it = intent(day_type="Normal", now_il_hhmm="18:00")
        self.assertEqual(it.bias, "BOTH")
        self.assertIn("EDGE_FADE", it.entry_kinds)

    def test_neutral_center(self):
        it = intent(day_type="Neutral_Center", now_il_hhmm="18:00")
        self.assertEqual(it.bias, "BOTH")
        self.assertEqual(it.target_rule, "CENTER")

    def test_nontrend(self):
        it = intent(day_type="Nontrend", now_il_hhmm="18:00")
        self.assertEqual(it.bias, "NONE")
        self.assertEqual(it.size_frac, 0.0)

    def test_none_daytype_after_lock(self):
        it = intent(day_type="", now_il_hhmm="18:00")
        self.assertEqual(it.bias, "NONE")
        self.assertEqual(it.size_frac, 0.0)


class TestPhaseD(unittest.TestCase):

    def test_management_only(self):
        it = intent(day_type="Trend_Normal", now_il_hhmm="21:30",
                     direction_hint="LONG")
        self.assertEqual(it.size_frac, 0.0)


class TestGate(unittest.TestCase):

    def test_bias_blocks_wrong_direction(self):
        it = Intent(bias="LONG", entry_kinds=frozenset({"BREAK"}),
                    stop_rule="X", target_rule="X", size_frac=1.0,
                    runner=False, reason="test")
        block = evaluate_gate({"direction": "SHORT", "classification": "GB100"}, it)
        self.assertIsNotNone(block)
        self.assertIn("bias", block["blocked_by"])

    def test_bias_allows_correct_direction(self):
        it = Intent(bias="LONG", entry_kinds=frozenset({"BREAK"}),
                    stop_rule="X", target_rule="X", size_frac=1.0,
                    runner=False, reason="test")
        block = evaluate_gate({"direction": "LONG", "classification": "GB100"}, it)
        self.assertIsNone(block)

    def test_stand_down_blocks(self):
        it = Intent(bias="NONE", entry_kinds=frozenset(),
                    stop_rule=None, target_rule=None, size_frac=0.0,
                    runner=False, reason="stand-down")
        block = evaluate_gate({"direction": "LONG", "classification": "GB100"}, it)
        self.assertIsNotNone(block)
        self.assertIn("stand_down", block["blocked_by"])

    def test_kind_blocks_wrong_entry(self):
        it = Intent(bias="BOTH", entry_kinds=frozenset({"EDGE_FADE"}),
                    stop_rule="X", target_rule="X", size_frac=1.0,
                    runner=False, reason="test")
        block = evaluate_gate({"direction": "LONG", "classification": "GB100"}, it)
        self.assertIsNotNone(block)
        self.assertIn("kind", block["blocked_by"])


class TestEntryKindMap(unittest.TestCase):

    def test_zlr_maps_to_break(self):
        self.assertEqual(entry_kind_for("ZLR"), "BREAK")

    def test_trend_step_maps_to_pullback(self):
        self.assertEqual(entry_kind_for("TREND_STEP"), "PULLBACK")

    def test_reactive_maps_to_edge_fade(self):
        self.assertEqual(entry_kind_for("REACTIVE_LONG"), "EDGE_FADE")


class TestMutation(unittest.TestCase):

    def test_flipping_trend_bias_fails(self):
        """MUTATION: if Trend gives BOTH instead of trend_direction, wrong trades pass."""
        it = intent(day_type="Trend_Normal", now_il_hhmm="18:00",
                     direction_hint="LONG")
        # A SHORT should be blocked on a Trend_Normal LONG day
        block = evaluate_gate({"direction": "SHORT", "classification": "GB100"}, it)
        self.assertIsNotNone(block, "SHORT must be blocked on Trend LONG day")


if __name__ == "__main__":
    unittest.main()
