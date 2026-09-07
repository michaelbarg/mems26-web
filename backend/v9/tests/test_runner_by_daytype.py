"""§2 RUNNER_BY_DAYTYPE_V1 — runner only on Trend days.

Behavioral test: through command_from_setup with stubs for
write_trade_command and get_live_day_type.
Mutation: removing runner_by_daytype skip → RUNNER_TRAIL_V2 overwrites → FAIL.
"""
import importlib
import os
import unittest
from unittest.mock import patch, MagicMock


def _make_setup(day_type="Variation", contracts=5, struct_c3=7715.0):
    meta = {"day_type": day_type}
    if struct_c3 is not None:
        meta["spacing_levels"] = [("struct_c1", 7724.0), ("struct_c2", 7718.75),
                                  ("struct_c3", struct_c3)]
    return {
        "entry_price": 7720.0,
        "stop": 7730.0,
        "direction": "SHORT",
        "contracts": contracts,
        "size": contracts,
        "metadata": meta,
        "day_type_at_entry": day_type,
        "t1": 7715.0, "t2": 7710.0, "t3": 7705.0,
    }


class TestRunnerByDaytypeBehavioral(unittest.TestCase):

    def setUp(self):
        os.environ["RUNNER_BY_DAYTYPE_V1"] = "1"
        os.environ["RUNNER_TRAIL_V2"] = "1"
        os.environ["C4_RULING6_V1"] = "0"
        os.environ["T0_TARGET_PTS"] = "0"

    def tearDown(self):
        for k in ("RUNNER_BY_DAYTYPE_V1", "RUNNER_TRAIL_V2",
                   "C4_RULING6_V1", "T0_TARGET_PTS"):
            os.environ.pop(k, None)

    @patch("backend.v9.services.sierra_command.write_trade_command")
    @patch("backend.v9.services.trade_context.get_live_day_type")
    def test_variation_gets_struct_c3_not_none(self, mock_dt, mock_write):
        """On Variation, c4 = struct_c3, NOT None (RUNNER_TRAIL_V2 must skip)."""
        mock_dt.return_value = "Variation"
        mock_write.return_value = {"ok": True}

        from backend.v9.services.sierra_command import command_from_setup
        setup = _make_setup("Variation", contracts=5, struct_c3=7715.0)
        command_from_setup(setup, trade_id="test", account="SIM", mode="shadow")

        # Check what was passed to write_trade_command
        call_args = mock_write.call_args
        # c4 is passed as context.t4 — find it in the call
        kwargs = call_args[1] if call_args[1] else {}
        args = call_args[0] if call_args[0] else ()
        # write_trade_command receives a dict; check t4 key
        if args:
            cmd = args[0]
        else:
            cmd = kwargs
        # The command dict should have context.t4 set to struct_c3
        ctx = cmd.get("context", {})
        t4 = ctx.get("t4")
        self.assertIsNotNone(t4,
                              "Variation day: c4 must be struct_c3 (7715.0), not None")
        self.assertAlmostEqual(float(t4), 7715.0, places=1,
                                msg="c4 should be struct_c3=7715.0")

    @patch("backend.v9.services.sierra_command.write_trade_command")
    @patch("backend.v9.services.trade_context.get_live_day_type")
    def test_trend_normal_gets_none(self, mock_dt, mock_write):
        """On Trend_Normal, c4 = None (runner trails via RUNNER_TRAIL_V2)."""
        mock_dt.return_value = "Trend_Normal"
        mock_write.return_value = {"ok": True}

        from backend.v9.services.sierra_command import command_from_setup
        setup = _make_setup("Trend_Normal", contracts=5)
        command_from_setup(setup, trade_id="test", account="SIM", mode="shadow")

        call_args = mock_write.call_args
        if call_args[0]:
            cmd = call_args[0][0]
        else:
            cmd = call_args[1]
        ctx = cmd.get("context", {})
        t4 = ctx.get("t4")
        # Trend: RUNNER_TRAIL_V2 sets c4=None (stop-only runner)
        self.assertIsNone(t4,
                           "Trend day: c4 must be None (runner trails)")


class TestRunnerByDaytypeMutation(unittest.TestCase):

    def test_runner_by_daytype_skip_exists(self):
        """MUTATION: runner_by_daytype must appear as a skip condition
        in the RUNNER_TRAIL_V2 block."""
        import subprocess
        out = subprocess.run(
            ["grep", "-n", "runner_by_daytype",
             "backend/v9/services/sierra_command.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        lines = [l for l in out.stdout.strip().split("\n") if l]
        # Must appear at least 3 times: 2 writes + 1 skip check
        self.assertGreaterEqual(len(lines), 3,
                                 f"runner_by_daytype must appear >=3 times "
                                 f"(2 writes + 1 skip), got {len(lines)}")


if __name__ == "__main__":
    unittest.main()
