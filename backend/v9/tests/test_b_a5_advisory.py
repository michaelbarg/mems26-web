"""B: A5 is advisory-only — never blocks entry.

if reverted → RED because _a5_auxiliary returns FAIL when sizing=reject,
which puts A5 in failed_stages and blocks ready_to_route.
"""

import pytest
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.v9.systems.woodies.decision_tree import (
    WoodiesDecisionTree,
    WoodiesDecisionContext,
    StageStatus,
    _a5_auxiliary,
)


def _make_ctx(sizing="reject", patterns=None, direction=None, classification="NO_SETUP", fire_setup=None):
    """Build a minimal WoodiesDecisionContext for testing."""
    return WoodiesDecisionContext(
        bars=[],
        studies={"trend_state": "GREEN", "swi_value": 50.0},
        patterns=patterns or [],
        classification=classification,
        direction=direction,
        sizing=sizing,
        current_state={},
        fire_setup=fire_setup,
        touchpoints={},
    )


class TestA5Advisory:
    """A5 must never appear in failed_stages."""

    def test_a5_sizing_reject_is_pass(self):
        """A5 with sizing=reject returns PASS (advisory), not FAIL."""
        ctx = _make_ctx(sizing="reject")
        result = _a5_auxiliary(ctx)
        assert result.status == StageStatus.PASS, (
            f"A5 must be PASS (advisory), got {result.status}"
        )
        assert "advisory" in result.message

    def test_a5_sizing_ok_is_pass(self):
        """A5 with valid sizing returns PASS."""
        ctx = _make_ctx(sizing="2")
        result = _a5_auxiliary(ctx)
        assert result.status == StageStatus.PASS

    def test_a5_never_in_failed_stages(self):
        """Full decision tree: A5 never in failed_stages even when sizing=reject."""
        ctx = _make_ctx(sizing="reject")
        tree = WoodiesDecisionTree()
        result = tree.evaluate_bar(ctx)
        assert "A5" not in result["failed_stages"], (
            f"A5 must NOT block — failed_stages={result['failed_stages']}"
        )

    def test_real_blocker_is_not_a5(self):
        """When sizing=reject, the blocker is A2/A3/A7 — never A5."""
        ctx = _make_ctx(sizing="reject")
        tree = WoodiesDecisionTree()
        result = tree.evaluate_bar(ctx)
        failed = result["failed_stages"]
        assert "A5" not in failed, f"A5 must NOT be in failed_stages, got {failed}"
        # At least one real blocker exists (A2 study validity or A3 no pattern)
        assert len(failed) > 0, "Expected at least one real blocker"
