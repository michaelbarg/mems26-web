"""§5 ELQ_LEG_FROM_BREAK_V1 — leg_base from broken IB edge, not session extreme.

Mutation guard: flag gates the IB-edge override. Removing the flag
check makes leg_base always use IB edge (even when no break exists).
"""
import subprocess
import unittest


class TestElqLegFromBreak(unittest.TestCase):

    def test_flag_read_site_exists(self):
        """ELQ_LEG_FROM_BREAK_V1 has a read site in trading_gateway.py."""
        out = subprocess.run(
            ["grep", "-c", "ELQ_LEG_FROM_BREAK_V1",
             "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertGreaterEqual(int(out.stdout.strip()), 1)

    def test_mutation_accepted_break_required(self):
        """The code checks accepted_break before changing leg_base."""
        out = subprocess.run(
            ["grep", "-A5", "ELQ_LEG_FROM_BREAK_V1",
             "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertIn("accepted_break", out.stdout,
                       "Must check accepted_break before overriding leg_base")

    def test_mutation_ib_edge_used(self):
        """The override reads ib_high or ib_low from TPO."""
        out = subprocess.run(
            ["grep", "-A15", "ELQ_LEG_FROM_BREAK_V1",
             "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertIn("ib_high", out.stdout)
        self.assertIn("ib_low", out.stdout)


if __name__ == "__main__":
    unittest.main()
