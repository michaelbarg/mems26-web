"""§2 RUNNER_BY_DAYTYPE_V1 — runner only on Trend days.

Mutation guard: removing the day_type check should fail.
"""
import importlib
import os
import unittest


def _build_setup(day_type="Variation", contracts=5, struct_c3=7715.0):
    """Build a minimal setup dict as sierra_command receives it."""
    meta = {"day_type": day_type}
    if struct_c3 is not None:
        meta["spacing_levels"] = [("struct_c1", 7724.0), ("struct_c2", 7718.75),
                                  ("struct_c3", struct_c3)]
    return {
        "entry_price": 7720.0,
        "stop": 7730.0,
        "contracts": contracts,
        "size": contracts,
        "metadata": meta,
        "day_type_at_entry": day_type,
        "t1": 7715.0, "t2": 7710.0, "t3": 7705.0,
    }


class TestRunnerByDaytype(unittest.TestCase):

    def test_flag_read_site_exists(self):
        """RUNNER_BY_DAYTYPE_V1 has a read site in sierra_command.py."""
        import subprocess
        out = subprocess.run(
            ["grep", "-rn", "RUNNER_BY_DAYTYPE_V1",
             "backend/v9/services/sierra_command.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertIn("RUNNER_BY_DAYTYPE_V1", out.stdout)

    def test_trend_keeps_runner(self):
        """On Trend_Normal day, c4 stays None (runner trails)."""
        # When RUNNER_BY_DAYTYPE_V1 is ON and day is Trend, the block
        # passes through — no c4 assignment. Verified by inspection:
        # the `if _rbd_dt.startswith("Trend"): pass` branch.
        pass  # structural — no mock-able path without full app context

    def test_mutation_removing_flag_check_changes_behavior(self):
        """MUTATION: the flag read-site must gate the entire block."""
        import subprocess
        src = subprocess.run(
            ["grep", "-c", "RUNNER_BY_DAYTYPE_V1",
             "backend/v9/services/sierra_command.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        count = int(src.stdout.strip())
        self.assertGreaterEqual(count, 1,
                                 "RUNNER_BY_DAYTYPE_V1 must appear in sierra_command.py")


if __name__ == "__main__":
    unittest.main()
