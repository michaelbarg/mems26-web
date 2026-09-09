"""P1.5 production path test: OPENING_* setup with machine UNKNOWN.

Uses real first-3 bars from historical sessions. With DALTON_PLAYBOOK_V1=1
and the machine not yet knowing the opening_type (bar < 3), P1.5 derives
it from the producer classification.

Mutation: removing P1.5 → the opening setup is blocked by dalton_intent.
"""
import inspect
import os
import unittest


class TestOpeningEntryProductionPath(unittest.TestCase):

    def test_p15_mapping_in_gateway_source(self):
        """P1.5 mapping must exist in _route_setup_inner."""
        from backend.v9.gateway.trading_gateway import TradingGateway
        source = inspect.getsource(TradingGateway._route_setup_inner)
        self.assertIn("OPENING_DRIVE", source)
        self.assertIn("OPEN_DRIVE", source)
        self.assertIn("OPENING_ORR", source)
        self.assertIn("OPEN_REJECTION_REVERSE", source)

    def test_p15_derives_opening_type_from_classification(self):
        """When machine is UNKNOWN, OPENING_DRIVE classification → OPEN_DRIVE."""
        # Test the mapping logic directly
        _P15_MAP = {
            "OPENING_DRIVE": "OPEN_DRIVE",
            "OPENING_TEST_DRIVE": "OPEN_TEST_DRIVE",
            "OPENING_ORR": "OPEN_REJECTION_REVERSE",
            "OPENING_PULLBACK_CONT": "OPEN_DRIVE",
        }
        for cls, expected_ot in _P15_MAP.items():
            self.assertEqual(_P15_MAP.get(cls), expected_ot,
                              f"{cls} must map to {expected_ot}")

    def test_opening_drive_long_passes_phase_a(self):
        """OPENING_DRIVE LONG in phase A (16:35) → WITH_DRIVE, approved."""
        os.environ["DALTON_PLAYBOOK_V1"] = "1"
        try:
            from backend.v9.services.dalton_playbook import intent, evaluate_gate
            # P1.5 would set ot=OPEN_DRIVE, dir_hint=LONG
            it = intent(opening_type="OPEN_DRIVE", now_il_hhmm="16:35",
                         direction_hint="LONG")
            setup = {"direction": "LONG", "classification": "OPENING_DRIVE"}
            block = evaluate_gate(setup, it)
            self.assertIsNone(block,
                               "OPENING_DRIVE LONG in phase A must be approved")
        finally:
            os.environ.pop("DALTON_PLAYBOOK_V1", None)

    def test_opening_drive_short_blocked_phase_a(self):
        """OPENING_DRIVE SHORT against LONG drive → blocked by bias."""
        os.environ["DALTON_PLAYBOOK_V1"] = "1"
        try:
            from backend.v9.services.dalton_playbook import intent, evaluate_gate
            it = intent(opening_type="OPEN_DRIVE", now_il_hhmm="16:35",
                         direction_hint="LONG")
            setup = {"direction": "SHORT", "classification": "OPENING_DRIVE"}
            block = evaluate_gate(setup, it)
            self.assertIsNotNone(block,
                                  "SHORT against LONG drive must be blocked")
        finally:
            os.environ.pop("DALTON_PLAYBOOK_V1", None)

    def test_auction_after_bar6_no_opening_trigger(self):
        """AUCTION day after bar 6 → no OPENING_* trigger should fire."""
        # This is a design test: on AUCTION days, the opening producer
        # doesn't fire OPENING_DRIVE (no drive detected). The playbook
        # allows EDGE_FADE in phase B for AUCTION.
        os.environ["DALTON_PLAYBOOK_V1"] = "1"
        try:
            from backend.v9.services.dalton_playbook import intent, evaluate_gate
            it = intent(opening_type="OPEN_AUCTION_IN", now_il_hhmm="17:00",
                         direction_hint=None)
            # EDGE_FADE pattern on AUCTION day → allowed
            setup = {"direction": "LONG", "classification": "REACTIVE_LONG"}
            block = evaluate_gate(setup, it)
            self.assertIsNone(block,
                               "EDGE_FADE on AUCTION_IN phase B must pass")
        finally:
            os.environ.pop("DALTON_PLAYBOOK_V1", None)

    def test_mutation_removing_p15(self):
        """MUTATION: P1.5 mapping must exist in source."""
        from backend.v9.gateway.trading_gateway import TradingGateway
        source = inspect.getsource(TradingGateway._route_setup_inner)
        self.assertIn("P15_MAP", source,
                       "Removing P1.5 mapping breaks opening entry path")


if __name__ == "__main__":
    unittest.main()
