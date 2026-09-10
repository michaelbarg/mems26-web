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

    def test_kind_blocks_counter_direction_wrong_entry(self):
        """Counter-direction → blocked by bias (kind never reached)."""
        it = Intent(bias="LONG", entry_kinds=frozenset({"EDGE_FADE"}),
                    stop_rule="X", target_rule="X", size_frac=1.0,
                    runner=False, reason="test")
        # SHORT (counter to LONG bias) → blocked by bias
        block = evaluate_gate({"direction": "SHORT", "classification": "GB100"}, it)
        self.assertIsNotNone(block)
        self.assertIn("bias", block["blocked_by"])


class TestEntryKindMap(unittest.TestCase):

    def test_zlr_maps_to_break(self):
        self.assertEqual(entry_kind_for("ZLR"), "BREAK")

    def test_trend_step_maps_to_pullback(self):
        self.assertEqual(entry_kind_for("TREND_STEP"), "PULLBACK")

    def test_reactive_maps_to_edge_fade(self):
        self.assertEqual(entry_kind_for("REACTIVE_LONG"), "EDGE_FADE")


class TestPolicyKeys(unittest.TestCase):

    def test_counter_bias_only_allows_with_direction(self):
        """kinds_apply_to=counter_bias_only: WITH-bias direction passes any kind."""
        # Trend LONG, EDGE_FADE (not in [PULLBACK, BREAK]) but WITH bias → passes
        it = intent(day_type="Trend_Normal", now_il_hhmm="18:00",
                     direction_hint="LONG")
        # REACTIVE_LONG maps to EDGE_FADE, not in Trend's [PULLBACK, BREAK]
        block = evaluate_gate({"direction": "LONG", "classification": "REACTIVE_LONG"}, it)
        # With counter_bias_only: LONG WITH Trend LONG → any kind allowed
        self.assertIsNone(block,
                           "WITH-bias direction should pass any kind under counter_bias_only")

    def test_counter_bias_only_still_applies_kinds_under_both(self):
        """cowork 09.09: under bias=BOTH the kinds list MUST still veto.

        Normal day (bias BOTH, kinds [EDGE_FADE, VALUE_RETURN]): a BREAK (ZLR)
        must be blocked. The 11:35 build let it through (`bias in ("BOTH",
        direction)`), which is the kinds-advisory variant — replay Σ +60 instead
        of +607.50 and losers-rejected 31% instead of 57%.
        """
        it = intent(day_type="Normal", now_il_hhmm="18:00")
        self.assertEqual(it.bias, "BOTH")
        block = evaluate_gate({"direction": "SHORT", "classification": "ZLR"}, it)
        self.assertIsNotNone(block, "BREAK under bias=BOTH must still be vetoed by the kinds list")
        self.assertEqual(block["blocked_by"], "dalton_intent:kind")

    def test_counter_bias_only_blocks_counter_wrong_kind(self):
        """Counter-direction + wrong kind → blocked."""
        it = intent(day_type="Trend_Normal", now_il_hhmm="18:00",
                     direction_hint="LONG")
        # SHORT (counter) + EDGE_FADE (not in kinds) → blocked
        block = evaluate_gate({"direction": "SHORT", "classification": "REACTIVE_SHORT"}, it)
        self.assertIsNotNone(block)

    def test_phase_d_manage_only(self):
        """phase_d=manage_only: 21:30 → stand-down."""
        it = intent(day_type="Trend_Normal", now_il_hhmm="21:30",
                     direction_hint="LONG")
        self.assertEqual(it.size_frac, 0.0)

    def test_phase_d_as_phase_c(self):
        """If phase_d were as_phase_c, 21:30 Trend would still be active."""
        # This tests the YAML key behavior — currently manage_only
        # so this is a negative test (size_frac=0)
        it = intent(day_type="Trend_Normal", now_il_hhmm="21:30",
                     direction_hint="LONG")
        self.assertEqual(it.size_frac, 0.0,
                          "phase_d=manage_only: no new entries after 21:00")


class TestHintLayering(unittest.TestCase):
    """Direction hint layering: opening first, extension overrides in C only."""

    def test_phase_b_drive_gets_opening_hint(self):
        """Phase B with OPEN_DRIVE: hint = drive direction (from opening)."""
        it = intent(opening_type="OPEN_DRIVE", now_il_hhmm="17:00",
                     direction_hint="LONG")
        self.assertEqual(it.bias, "LONG",
                          "Phase B OPEN_DRIVE with LONG hint must give bias=LONG")

    def test_phase_c_with_extension_overrides(self):
        """Phase C with extension: hint overrides to extension direction."""
        # Variation with extension DOWN (hint=SHORT from 5b)
        it = intent(day_type="Variation", now_il_hhmm="18:00",
                     direction_hint="SHORT")
        # bias should be SHORT (extension direction)
        self.assertEqual(it.bias, "SHORT",
                          "Phase C Variation with SHORT hint must give bias=SHORT")

    def test_phase_c_no_extension_keeps_opening_hint(self):
        """Phase C without extension: hint = opening direction (Layer 1)."""
        # If no extension happened, direction_hint stays from opening
        it = intent(day_type="Variation", now_il_hhmm="18:00",
                     direction_hint="LONG")
        # bias should be LONG (from opening, no extension override)
        self.assertIn(it.bias, ("LONG", "BOTH"),
                       "Phase C Variation with LONG hint must preserve opening direction")


class TestMutation(unittest.TestCase):

    def test_flipping_trend_bias_fails(self):
        """MUTATION: if Trend gives BOTH instead of trend_direction, wrong trades pass."""
        it = intent(day_type="Trend_Normal", now_il_hhmm="18:00",
                     direction_hint="LONG")
        block = evaluate_gate({"direction": "SHORT", "classification": "GB100"}, it)
        self.assertIsNotNone(block, "SHORT must be blocked on Trend LONG day")

    def test_mutation_ext_zero_does_not_override(self):
        """MUTATION: ext_up=ext_dn=0 must NOT override the opening hint."""
        # When extension = 0, the hint should stay as the opening direction
        # This tests the gateway logic indirectly via intent():
        # With direction_hint="LONG" (from opening) and no extension,
        # Phase C Variation should keep LONG bias
        it = intent(day_type="Variation", now_il_hhmm="18:00",
                     direction_hint="LONG")
        # If ext override wrongly set hint=None → bias would be BOTH
        # instead of LONG. The test catches the old reset-to-None bug.
        block = evaluate_gate(
            {"direction": "SHORT", "classification": "ZLR"}, it)
        # Under counter_bias_only: SHORT against LONG bias + BREAK kind
        # → should be blocked by bias (not by kind under BOTH)
        self.assertIsNotNone(block,
                              "SHORT against LONG hint must be blocked — "
                              "ext=0 must not erase the opening hint")


if __name__ == "__main__":
    unittest.main()
