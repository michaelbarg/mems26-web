"""T-426 — provisional OPEN_DRIVE for a confirmed opening drive while the T-314
label lags (Michael 20.09 "תתקן את הענף"). 18.09: the opening engine confirmed
DRIVE SHORT at 16:45:03 @7705 (close beyond the OR, 3 closed bars, 16:40
closed 7705.0 < 7705.25) while the label was still OPEN_AUCTION_IN, so the
phase-B row (EDGE_FADE only) blocked it — `dalton_intent:kind`. The live
entry came at 17:00 @7691.25, after 25 of the drive's 26 points."""
import unittest

from backend.v9.systems.opening_provisional import provisional_opening_type


class TestOpeningProvisional(unittest.TestCase):

    def test_18_09_confirmed_drive_under_auction_in_label(self):
        ot, d, applied = provisional_opening_type(
            "OPEN_AUCTION_IN", locked=False, classification="OPENING_DRIVE", direction="SHORT")
        self.assertTrue(applied)
        self.assertEqual(ot, "OPEN_DRIVE")
        self.assertEqual(d, "SHORT")

    def test_test_drive_maps_to_open_test_drive(self):
        ot, d, applied = provisional_opening_type(
            "OPEN_AUCTION_OUT", locked=False, classification="OPENING_TEST_DRIVE", direction="LONG")
        self.assertTrue(applied)
        self.assertEqual((ot, d), ("OPEN_TEST_DRIVE", "LONG"))

    def test_unknown_label_is_lagging_too(self):
        ot, d, applied = provisional_opening_type(
            "UNKNOWN", locked=False, classification="OPENING_DRIVE", direction="LONG")
        self.assertTrue(applied)
        self.assertEqual(ot, "OPEN_DRIVE")

    def test_locked_label_is_a_ruling_and_stays(self):
        ot, d, applied = provisional_opening_type(
            "OPEN_AUCTION_IN", locked=True, classification="OPENING_DRIVE", direction="SHORT")
        self.assertFalse(applied)
        self.assertEqual(ot, "OPEN_AUCTION_IN")
        self.assertIsNone(d)

    def test_non_lagging_label_unchanged(self):
        for lab in ("OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE"):
            ot, d, applied = provisional_opening_type(
                lab, locked=False, classification="OPENING_DRIVE", direction="SHORT")
            self.assertFalse(applied, lab)
            self.assertEqual(ot, lab)

    def test_other_producers_never_promoted(self):
        for cls in ("OPENING_ORR", "OPENING_PULLBACK_CONT", "OPENING_EXTREME_REJECT",
                    "REACTIVE_SHORT", "ZLR", "INITIATIVE_LONG", "", None):
            ot, d, applied = provisional_opening_type(
                "OPEN_AUCTION_IN", locked=False, classification=cls, direction="SHORT")
            self.assertFalse(applied, cls)
            self.assertEqual(ot, "OPEN_AUCTION_IN")

    def test_missing_direction_unchanged(self):
        ot, d, applied = provisional_opening_type(
            "OPEN_AUCTION_IN", locked=False, classification="OPENING_DRIVE", direction=None)
        self.assertFalse(applied)


if __name__ == "__main__":
    unittest.main()
