"""Forward gate — golden session assertions.

Runs forward_gate.py on all golden sessions and fails on any deviation.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestForwardGate(unittest.TestCase):

    def test_golden_sessions_pass(self):
        """All golden session assertions must pass."""
        import yaml
        golden_path = ROOT / "config" / "forward_gate_golden.yaml"
        self.assertTrue(golden_path.exists(), f"Golden file not found: {golden_path}")

        with open(golden_path) as f:
            golden = yaml.safe_load(f) or {}

        sessions = golden.get("sessions", {})
        self.assertGreater(len(sessions), 0, "No golden sessions defined")

        sys.path.insert(0, str(ROOT))
        from scripts.forward_gate import run_session

        failures = []
        for day, entry in sessions.items():
            ok, line = run_session(day, entry)
            if not ok:
                failures.append(line)

        self.assertEqual(len(failures), 0,
                          f"Forward gate failures:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
