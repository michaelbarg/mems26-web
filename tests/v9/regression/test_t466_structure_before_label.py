# -*- coding: utf-8 -*-
"""T-466 — structure before label: the pure predicate behind STRUCTURE_BEFORE_LABEL_V1.

24.09 18:05: IB 7730–7758.25, session low 7725.25 (5 pts below the IB low, high never above the IB
high) while the label still said Normal ⇒ the tree must see Variation, bias SHORT. Trend labels are
never overridden; a two-sided session is not one-sided; a tick-poke is noise.
"""
import unittest

from backend.v9.systems.structure_before_label import effective_day_type, one_sided_extension


class TestOneSidedExtension(unittest.TestCase):
    def test_24_09_18_05_is_a_short_extension(self):
        self.assertEqual(one_sided_extension(7758.25, 7730.0, 7758.25, 7725.25), "SHORT")

    def test_up_extension(self):
        self.assertEqual(one_sided_extension(7758.25, 7730.0, 7783.0, 7730.0), "LONG")

    def test_two_sided_is_not_one_sided(self):
        # 24.09 after 19:15: low 7725.25 AND high 7783 ⇒ neutral, no override
        self.assertIsNone(one_sided_extension(7758.25, 7730.0, 7783.0, 7725.25))

    def test_tick_poke_is_noise(self):
        self.assertIsNone(one_sided_extension(7758.25, 7730.0, 7758.5, 7729.0))   # 1 pt < max(2, 2.8)
        self.assertEqual(one_sided_extension(7758.25, 7730.0, 7758.5, 7727.0), "SHORT")  # 3 pts, other side +0.25 only

    def test_needs_a_complete_ib(self):
        self.assertIsNone(one_sided_extension(0, 0, 7783.0, 7725.25))
        self.assertIsNone(one_sided_extension(None, None, None, None))


class TestEffectiveDayType(unittest.TestCase):
    def test_non_trend_labels_become_variation(self):
        for lab in ("", "UNKNOWN", "Normal", "Neutral_Center", "Neutral_Extreme", "Nontrend"):
            self.assertEqual(effective_day_type(lab, "SHORT"), "Variation")

    def test_trend_and_variation_labels_untouched(self):
        for lab in ("Trend_Normal", "Trend_DD", "Variation", "Normal_Variation"):
            self.assertEqual(effective_day_type(lab, "LONG"), lab)

    def test_no_extension_keeps_label(self):
        self.assertEqual(effective_day_type("Normal", None), "Normal")


if __name__ == "__main__":
    unittest.main()
