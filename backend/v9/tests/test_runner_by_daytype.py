"""§A RUNNER_BY_DAYTYPE_V1 — runner ONLY on Trend days.

Behavioral tests through command_from_setup with stubs.
The key fix: day_type=None also gets NO runner (was the hole —
14/39 live trades had None and got stop-only runner).
"""
import os
import unittest
from unittest.mock import patch


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


def _get_t4(mock_write):
    """Extract t4 from the write_trade_command call."""
    call_args = mock_write.call_args
    if call_args[0]:
        cmd = call_args[0][0]
    else:
        cmd = call_args[1]
    return cmd.get("context", {}).get("t4")


class TestRunnerByDaytypeBehavioral(unittest.TestCase):

    def setUp(self):
        os.environ["RUNNER_BY_DAYTYPE_V1"] = "1"
        os.environ["RUNNER_TRAIL_V2"] = "1"
        os.environ["C4_RULING6_V1"] = "0"
        os.environ["T0_TARGET_PTS"] = "0"
        # The subject of these tests is the c4 leg: "day_type=None must get a
        # TARGET on c4, not a stop-only runner". That leg only exists at 4+
        # contracts, so the size ruling has to be pinned here — otherwise the
        # test silently measures the ruling instead of the runner logic.
        # Michael 15.09 17:25 moved the standing size to 3 (ladder 1,1,1,0),
        # `ruled_contracts()` then overrides the setup's `contracts=5`, c4 is
        # correctly None, and both tests failed for the wrong reason
        # (guard_tests RED → fire_drill NO-GO, 15.09 17:29). Pinning 5 here
        # restores what the tests were written to prove; it does not touch
        # production sizing, which stays whatever `.env` rules.
        self._size_saved = {k: os.environ.get(k)
                            for k in ("FIXED_CONTRACTS_1", "FIXED_CONTRACTS_3", "FIXED_CONTRACTS_5")}
        os.environ["FIXED_CONTRACTS_1"] = "0"  # 18.09 one-contract ruling — pinned off, same reason
        os.environ["FIXED_CONTRACTS_3"] = "0"
        os.environ["FIXED_CONTRACTS_5"] = "1"

    def tearDown(self):
        for k in ("RUNNER_BY_DAYTYPE_V1", "RUNNER_TRAIL_V2",
                   "C4_RULING6_V1", "T0_TARGET_PTS"):
            os.environ.pop(k, None)
        for k, v in self._size_saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    @patch("backend.v9.services.sierra_command.write_trade_command")
    @patch("backend.v9.services.trade_context.get_live_day_type")
    def test_none_daytype_gets_target_not_runner(self, mock_dt, mock_write):
        """§A: day_type=None → c4 must NOT be None (no runner)."""
        mock_dt.return_value = None
        mock_write.return_value = {"ok": True}

        from backend.v9.services.sierra_command import command_from_setup
        setup = _make_setup("Variation", contracts=5, struct_c3=7715.0)
        command_from_setup(setup, trade_id="test", account="SIM", mode="shadow")

        t4 = _get_t4(mock_write)
        self.assertIsNotNone(t4,
                              "day_type=None: c4 must be struct_c3/t3, NOT None (runner)")

    @patch("backend.v9.services.sierra_command.write_trade_command")
    @patch("backend.v9.services.trade_context.get_live_day_type")
    def test_variation_gets_struct_c3(self, mock_dt, mock_write):
        """Variation → c4 = struct_c3."""
        mock_dt.return_value = "Variation"
        mock_write.return_value = {"ok": True}

        from backend.v9.services.sierra_command import command_from_setup
        setup = _make_setup("Variation", contracts=5, struct_c3=7715.0)
        command_from_setup(setup, trade_id="test", account="SIM", mode="shadow")

        t4 = _get_t4(mock_write)
        self.assertIsNotNone(t4)
        self.assertAlmostEqual(float(t4), 7715.0, places=1)

    @patch("backend.v9.services.sierra_command.write_trade_command")
    @patch("backend.v9.services.trade_context.get_live_day_type")
    def test_trend_normal_gets_runner(self, mock_dt, mock_write):
        """Trend_Normal → c4 = None (runner, RUNNER_TRAIL_V2 fires)."""
        mock_dt.return_value = "Trend_Normal"
        mock_write.return_value = {"ok": True}

        from backend.v9.services.sierra_command import command_from_setup
        setup = _make_setup("Trend_Normal", contracts=5)
        command_from_setup(setup, trade_id="test", account="SIM", mode="shadow")

        t4 = _get_t4(mock_write)
        self.assertIsNone(t4, "Trend day: c4 must be None (runner)")

    @patch("backend.v9.services.sierra_command.write_trade_command")
    @patch("backend.v9.services.trade_context.get_live_day_type")
    def test_trend_dd_gets_runner(self, mock_dt, mock_write):
        """Trend_DD → c4 = None (runner)."""
        mock_dt.return_value = "Trend_DD"
        mock_write.return_value = {"ok": True}

        from backend.v9.services.sierra_command import command_from_setup
        setup = _make_setup("Trend_DD", contracts=5)
        command_from_setup(setup, trade_id="test", account="SIM", mode="shadow")

        t4 = _get_t4(mock_write)
        self.assertIsNone(t4, "Trend_DD: c4 must be None (runner)")


class TestRunnerByDaytypeMutation(unittest.TestCase):

    def test_runner_by_daytype_skip_exists(self):
        """runner_by_daytype must appear as a skip in RUNNER_TRAIL_V2."""
        import subprocess
        out = subprocess.run(
            ["grep", "-n", "runner_by_daytype",
             "backend/v9/services/sierra_command.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        lines = [l for l in out.stdout.strip().split("\n") if l]
        self.assertGreaterEqual(len(lines), 2)

    def test_none_branch_exists(self):
        """MUTATION: the else branch must handle None (not just non-Trend)."""
        import subprocess
        out = subprocess.run(
            ["grep", "-A3", "startswith.*Trend",
             "backend/v9/services/sierra_command.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertIn("else", out.stdout,
                       "Must have else branch after Trend check (handles None)")


if __name__ == "__main__":
    unittest.main()
