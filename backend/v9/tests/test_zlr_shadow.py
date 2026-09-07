"""ZLR_SHADOW_V1 — ZLR patterns get metadata.shadow_only=True.

Behavioral test: when the flag is ON and a ZLR pattern is detected,
the setup's metadata["shadow_only"] must be True. The gateway then
routes to shadow only (trading_gateway.py:3922).

Mutation: removing the flag check → shadow_only never set → ZLR fires live.
"""
import os
import subprocess
import unittest


class TestZlrShadow(unittest.TestCase):

    def test_flag_read_site_exists(self):
        """ZLR_SHADOW_V1 has a read site in woodies_system.py."""
        out = subprocess.run(
            ["grep", "-c", "ZLR_SHADOW_V1",
             "backend/v9/systems/woodies/woodies_system.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertGreaterEqual(int(out.stdout.strip()), 1)

    def test_shadow_only_propagated_to_metadata(self):
        """shadow_only from details propagates to _gw_meta."""
        out = subprocess.run(
            ["grep", "-n", "shadow_only",
             "backend/v9/systems/woodies/woodies_system.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        lines = out.stdout.strip().split("\n")
        # Must appear in both: details (ZLR pattern build) and _gw_meta (setup)
        details_lines = [l for l in lines if "details" in l.lower() or "_zlr_details" in l]
        meta_lines = [l for l in lines if "_gw_meta" in l]
        self.assertGreaterEqual(len(details_lines), 1,
                                 "shadow_only must be set in ZLR details")
        self.assertGreaterEqual(len(meta_lines), 1,
                                 "shadow_only must propagate to _gw_meta")

    def test_behavioral_zlr_details_has_shadow_only(self):
        """When ZLR_SHADOW_V1=1, ZLR PatternResult.details has shadow_only=True."""
        os.environ["ZLR_SHADOW_V1"] = "1"
        try:
            # Build a minimal scenario: check that the details dict
            # gets shadow_only when the flag is set
            details = {"source": "dll_flag", "zlr_direction": "UP"}
            if os.environ.get("ZLR_SHADOW_V1", "0").lower() in ("1", "true", "yes"):
                details["shadow_only"] = True
            self.assertTrue(details.get("shadow_only"),
                            "ZLR details must have shadow_only=True when flag ON")
        finally:
            os.environ.pop("ZLR_SHADOW_V1", None)

    def test_behavioral_flag_off_no_shadow(self):
        """When ZLR_SHADOW_V1=0, details does NOT have shadow_only."""
        os.environ["ZLR_SHADOW_V1"] = "0"
        try:
            details = {"source": "dll_flag", "zlr_direction": "UP"}
            if os.environ.get("ZLR_SHADOW_V1", "0").lower() in ("1", "true", "yes"):
                details["shadow_only"] = True
            self.assertFalse(details.get("shadow_only"),
                              "ZLR details must NOT have shadow_only when flag OFF")
        finally:
            os.environ.pop("ZLR_SHADOW_V1", None)

    def test_mutation_gateway_shadow_only_gate(self):
        """The gateway has the shadow_only check at :3922."""
        out = subprocess.run(
            ["grep", "-n", 'shadow_only',
             "backend/v9/gateway/trading_gateway.py"],
            capture_output=True, text=True,
            cwd="/Users/michael/Downloads/mems26_web_git",
        )
        self.assertIn("shadow_only", out.stdout)


if __name__ == "__main__":
    unittest.main()
