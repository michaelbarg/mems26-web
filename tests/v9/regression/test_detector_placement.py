"""Detector placement guard — a detector must not be nested under a gate that
its own evidence lives outside of.

Written by cowork-dev 2026-09-08 after the third dead-on-landing detector in
one week. RE_ACCEPTANCE_V1 and FAILED_RE_IB_V1 were built from
docs/reports/DALTON_EARLY_ENTRY_2026-09-07.md, whose whole finding is that the
money bar is the *resolution* bar 20-90 minutes after the open — and both were
placed inside

    if self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:      # ends 10:30 ET
        if _oe_mode in ("shadow", "1", "true"):           # OPENING_ENTRY_V1

so the live path can only ever evaluate 16:30-17:30 IL bars. Measured against
11 days of v9_bars_5min_woodies: RE_ACCEPTANCE's single fire is at 18:00 and
FAILED_RE_IB's earliest of 14 is at 17:40 — **zero** fall inside the window.
Both detectors were structurally incapable of firing on the evidence that
justified them, and every unit test stayed green because unit tests call
detect() directly and never see the nest.

five_min_system.py:1396-1406 already documents this exact trap for
DALTON_EDGE_V1 ("deliberately NOT inside the FIRST_HOUR_TACTICAL /
OPENING_ENTRY_V1 nest where EDGE_FADE/VA_FADE/FAILED_BREAK live"). This guard
turns that comment into a test.

AST, not grep: the check walks the real enclosing-statement chain, so it fails
when the code is nested and passes when it is not — a substring search over the
file cannot tell those apart.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "backend" / "v9" / "systems" / "five_min" / "five_min_system.py"

# Detectors whose evidence lies outside the opening hour, with the marker that
# identifies their call site in the source.
ALL_SESSION_DETECTORS = {
    "RE_ACCEPTANCE_V1": "re_acceptance",
    "FAILED_RE_IB_V1": "FAILED_RE_IB_V1",
}

# Gate tests a detector above must NOT be nested under.
FORBIDDEN_GATES = ("FIRST_HOUR_TACTICAL", "OPENING_ENTRY_V1", "_oe_mode")


def _enclosing_gates(tree: ast.AST, needle: str):
    """Return the `if` tests enclosing every occurrence of `needle`.

    Walks parent links built on the fly; for each node whose source segment
    mentions the needle, collect the test source of every ancestor `If`.
    """
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node  # type: ignore[attr-defined]

    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Call, ast.ImportFrom, ast.Name, ast.Constant)):
            continue
        seg = ast.dump(node)
        if needle not in seg:
            continue
        gates, cur = [], getattr(node, "parent", None)
        while cur is not None:
            if isinstance(cur, ast.If):
                try:
                    gates.append(ast.unparse(cur.test))
                except Exception:
                    pass
            cur = getattr(cur, "parent", None)
        hits.append((getattr(node, "lineno", -1), gates))
    return hits


class TestDetectorPlacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(SRC.read_text(encoding="utf-8"))

    def test_all_session_detectors_are_not_nested_in_the_opening_gate(self):
        for flag, needle in ALL_SESSION_DETECTORS.items():
            hits = _enclosing_gates(self.tree, needle)
            self.assertTrue(
                hits, f"{flag}: no call site found for marker {needle!r} — "
                      f"the detector is not wired at all")
            for lineno, gates in hits:
                joined = " | ".join(gates)
                for bad in FORBIDDEN_GATES:
                    self.assertNotIn(
                        bad, joined,
                        f"{flag} at {SRC.name}:{lineno} is nested under {bad!r}. "
                        f"Its evidence (DALTON_EARLY_ENTRY: the resolution bar, "
                        f"20-90 min after the open) lies outside that window, so "
                        f"the live path can never see it. Move the block beside "
                        f"_maybe_dalton_edge() — all-session, after the FIRST_HOUR "
                        f"block — exactly as five_min_system.py:1396-1406 "
                        f"prescribes. Enclosing gates: {joined}")

    def test_the_guard_itself_detects_nesting(self):
        """Mutation control: the walker must SEE a gate when one is there."""
        sample = ast.parse(
            "if self.mode == FiveMinMode.FIRST_HOUR_TACTICAL:\n"
            "    if _oe_mode in ('shadow',):\n"
            "        from x import re_acceptance\n")
        hits = _enclosing_gates(sample, "re_acceptance")
        self.assertTrue(hits, "walker found no call site in the control sample")
        joined = " | ".join(g for _, gs in hits for g in gs)
        self.assertIn("FIRST_HOUR_TACTICAL", joined,
                      "the walker failed to report a gate that is present — "
                      "a green run above would prove nothing")


if __name__ == "__main__":
    unittest.main()
