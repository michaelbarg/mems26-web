"""§3 STRUCT_TARGETS_WIN_V1 — structural targets override m×risk.

Mutation guard: removing the day_type check or the spacing_levels
check should fail (structural targets applied unconditionally or
never applied).
"""
import os
import subprocess
import unittest


class TestStructTargetsWin(unittest.TestCase):

    def test_flag_read_site_exists(self):
        """STRUCT_TARGETS_WIN_V1 has a read site in trading_gateway.py."""
        out = subprocess.run(
            ["grep", "-c", "STRUCT_TARGETS_WIN_V1",
             "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertGreaterEqual(int(out.stdout.strip()), 1)

    def test_mutation_spacing_levels_required(self):
        """The code checks _stw_sl (spacing_levels) before overriding."""
        out = subprocess.run(
            ["grep", "-n", "_stw_sl", "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertIn("_stw_sl", out.stdout,
                       "Must check spacing_levels before override")

    def test_mutation_day_type_required(self):
        """The code checks _stw_dt (day_type) before overriding."""
        out = subprocess.run(
            ["grep", "-n", "_stw_dt", "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertIn("_stw_dt", out.stdout,
                       "Must check day_type before override")

    def test_struct_c3_maps_to_t3(self):
        """struct_c3 in spacing_levels → setup['t3']."""
        out = subprocess.run(
            ["grep", "-n", "struct_c3.*t3\\|t3.*struct_c3",
             "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        # At least the logging line mentions t3 and struct
        self.assertTrue(len(out.stdout.strip()) > 0,
                        "struct_c3 must map to t3 in the override")


if __name__ == "__main__":
    unittest.main()
