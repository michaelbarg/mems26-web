"""§4 STOP_MOVE_TARGET_RESTORE_V1 — restore drifted targets after MODIFY_STOP.

Mutation guard: the flag must gate the Timer creation, and the check
must compare actual vs expected target prices.
"""
import subprocess
import unittest


class TestStopMoveTargetRestore(unittest.TestCase):

    def test_flag_read_site_exists(self):
        """STOP_MOVE_TARGET_RESTORE_V1 has a read site in manager.py."""
        out = subprocess.run(
            ["grep", "-c", "STOP_MOVE_TARGET_RESTORE_V1",
             "backend/v9/services/trade_manager/manager.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertGreaterEqual(int(out.stdout.strip()), 1)

    def test_mutation_timer_gated_by_flag(self):
        """The Timer is created inside a flag-check block."""
        out = subprocess.run(
            ["grep", "-A2", "STOP_MOVE_TARGET_RESTORE_V1",
             "backend/v9/services/trade_manager/manager.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertIn("Timer", out.stdout,
                       "Timer must be inside the flag-check block")

    def test_drift_check_method_exists(self):
        """_check_target_drift_after_stop method exists in manager."""
        out = subprocess.run(
            ["grep", "-c", "_check_target_drift_after_stop",
             "backend/v9/services/trade_manager/manager.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertGreaterEqual(int(out.stdout.strip()), 2,
                                 "def + call site")

    def test_mutation_compares_expected_vs_actual(self):
        """The drift check compares target prices, not just exists-check."""
        out = subprocess.run(
            ["grep", "-n", "_expected.*_actual\\|abs.*_actual.*_expected",
             "backend/v9/services/trade_manager/manager.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertTrue(len(out.stdout.strip()) > 0,
                        "Must compare expected vs actual target prices")


if __name__ == "__main__":
    unittest.main()
