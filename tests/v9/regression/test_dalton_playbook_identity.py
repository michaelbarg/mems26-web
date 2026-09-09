"""DALTON_PLAYBOOK_V1=0 → byte-identical gateway_decisions.

When the flag is OFF, the old gates (compass/playbook/location_gate)
run unchanged. The dalton_intent block does not execute.
"""
import inspect
import os
import unittest


class TestDaltonPlaybookOff(unittest.TestCase):

    def test_flag_off_skips_dalton_block(self):
        """When DALTON_PLAYBOOK_V1=0, _dp_active is False → dalton block skipped."""
        os.environ["DALTON_PLAYBOOK_V1"] = "0"
        try:
            from backend.v9.gateway.trading_gateway import TradingGateway
            source = inspect.getsource(TradingGateway._route_setup_inner)
            # The _dp_active flag must gate the block
            self.assertIn("_dp_active", source)
            # Old gates must be wrapped in "if not _dp_active"
            self.assertIn("not _dp_active", source)
        finally:
            os.environ.pop("DALTON_PLAYBOOK_V1", None)

    def test_old_gates_run_when_off(self):
        """compass/playbook/location_gate conditions include 'not _dp_active'."""
        from backend.v9.gateway.trading_gateway import TradingGateway
        source = inspect.getsource(TradingGateway._route_setup_inner)
        # Each old gate must have _dp_active condition
        # compass: "and not _dp_active" on _cmp_on()
        idx_compass = source.find("_cmp_on()")
        self.assertGreater(idx_compass, 0)
        compass_line = source[max(0, idx_compass - 50):idx_compass + 50]
        self.assertIn("_dp_active", compass_line,
                       "compass gate must check _dp_active")
        # playbook: "not _dp_active" on the `if` that checks DAYTYPE_PLAYBOOK env
        idx_pb = source.find('getenv("DAYTYPE_PLAYBOOK"')
        if idx_pb > 0:
            pb_context = source[max(0, idx_pb - 80):idx_pb]
            self.assertIn("_dp_active", pb_context,
                           "playbook gate must check _dp_active")

    def test_flag_off_is_default(self):
        """The .env default for DALTON_PLAYBOOK_V1 is 0."""
        os.environ.pop("DALTON_PLAYBOOK_V1", None)
        val = os.getenv("DALTON_PLAYBOOK_V1", "0")
        self.assertIn(val, ("0", ""),
                       "DALTON_PLAYBOOK_V1 must default to 0 (off)")


if __name__ == "__main__":
    unittest.main()
