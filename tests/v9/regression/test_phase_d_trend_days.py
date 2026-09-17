"""Phase D opened for trend days — Michael ruling 2026-09-17 14:05.

16.09: 100 of the day's 124 points came after 21:00 IL (FOMC), the system fired
five correct SHORT setups (incl. INITIATIVE_SHORT 21:30 @7678) and every one was
blocked by "phase D = manage only". Ruling: Trend_* and Neutral_Extreme trade
WITH the trend/extension in phase D (PULLBACK/BREAK, no runner); all other day
types stay manage-only.
"""
import unittest

from backend.v9.services.dalton_playbook import intent, evaluate_gate


class TestPhaseDTrendDays(unittest.TestCase):

    def test_trend_normal_short_allowed_in_phase_d(self):
        it = intent(opening_type="OPEN_REJECTION_REVERSE", day_type="Trend_Normal",
                    now_il_hhmm="21:47", direction_hint="SHORT")
        self.assertEqual(it.bias, "SHORT")
        self.assertIn("BREAK", it.entry_kinds)
        self.assertIn("PULLBACK", it.entry_kinds)
        self.assertFalse(it.runner)
        self.assertGreater(it.size_frac, 0)
        # GHOST is a BREAK-kind producer → passes with the bias
        self.assertIsNone(evaluate_gate(
            {"direction": "SHORT", "classification": "GHOST"}, it))

    def test_trend_counter_direction_blocked_in_phase_d(self):
        it = intent(opening_type="OPEN_REJECTION_REVERSE", day_type="Trend_DD",
                    now_il_hhmm="21:47", direction_hint="SHORT")
        blk = evaluate_gate({"direction": "LONG", "classification": "GHOST"}, it)
        self.assertIsNotNone(blk)
        self.assertEqual(blk["blocked_by"], "dalton_intent:bias")

    def test_neutral_extreme_follows_extension_in_phase_d(self):
        # bias=extension_direction resolves to the gateway dir_hint, which the
        # gateway overrides with the dominant IB-extension direction.
        it = intent(opening_type="OPEN_REJECTION_REVERSE", day_type="Neutral_Extreme",
                    now_il_hhmm="21:55", direction_hint="SHORT")
        self.assertEqual(it.bias, "SHORT")
        self.assertIsNone(evaluate_gate(
            {"direction": "SHORT", "classification": "GHOST"}, it))

    def test_other_day_types_stay_manage_only_in_phase_d(self):
        for dt in ("Normal", "Neutral_Center", "Variation", "Nontrend", ""):
            it = intent(opening_type="OPEN_AUCTION_IN", day_type=dt,
                        now_il_hhmm="21:30", direction_hint="SHORT")
            blk = evaluate_gate({"direction": "SHORT", "classification": "INITIATIVE_SHORT"}, it)
            self.assertIsNotNone(blk, dt)
            self.assertEqual(blk["blocked_by"], "dalton_intent:stand_down", dt)

    def test_phase_c_unchanged(self):
        it = intent(opening_type="OPEN_AUCTION_IN", day_type="Normal",
                    now_il_hhmm="18:00", direction_hint=None)
        self.assertEqual(it.bias, "BOTH")
        self.assertEqual(set(it.entry_kinds), {"EDGE_FADE", "VALUE_RETURN"})


if __name__ == "__main__":
    unittest.main()
