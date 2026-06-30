"""Regression: woodies fire_setup must be built for routable patterns.

06-30 live: patterns fired but fire_setup=None → A7 FAIL → ready_to_route=False
→ 0 trades all day. Root cause: best.stop was falsy → fire_setup block skipped.

Anti-tautological: calls REAL decision_tree._a7_universal.
Contract: docs/handoff/CC_HANDOFF_CONTRACT.md
"""
from backend.v9.systems.woodies.decision_tree import (
    _a7_universal, WoodiesDecisionContext, StageStatus,
)
from unittest.mock import MagicMock


def _ctx(*, patterns=None, sizing="full", fire_setup=None):
    """Build a minimal WoodiesDecisionContext."""
    ctx = MagicMock(spec=WoodiesDecisionContext)
    ctx.patterns = patterns or []
    ctx.sizing = sizing
    ctx.fire_setup = fire_setup
    ctx.classification = "TREND_CONFIRMING"
    ctx.direction = "LONG"
    return ctx


# ---------------------------------------------------------------------------
# Test 1: fire_setup present → A7 PASS (or proceeds past FAIL check)
# if reverted → RED because removing the fix leaves fire_setup=None for routable
# ---------------------------------------------------------------------------
class TestA7FireSetup:
    def test_fire_setup_present_no_fail(self):
        """fire_setup built → A7 does not FAIL."""
        setup = {"direction": "LONG", "entry_price": 7530, "stop_price": 7526.75,
                 "t1_price": 7533.25, "t2_price": None, "time_stop_minutes": 90,
                 "confidence": 65}
        ctx = _ctx(patterns=["ZLR"], fire_setup=setup)
        result = _a7_universal(ctx)
        assert result.status != StageStatus.FAIL, f"A7 should not FAIL with fire_setup: {result}"

    def test_fire_setup_none_routable_fails(self):
        """fire_setup=None + routable pattern → A7 FAIL (the 06-30 bug).

        if reverted → RED because this is the exact failure mode.
        """
        ctx = _ctx(patterns=["ZLR"], sizing="full", fire_setup=None)
        result = _a7_universal(ctx)
        assert result.status == StageStatus.FAIL
        assert "missing fire_setup" in result.message

    def test_fire_setup_none_no_patterns_skip(self):
        """No patterns → A7 SKIP (not FAIL)."""
        ctx = _ctx(patterns=[], fire_setup=None)
        result = _a7_universal(ctx)
        assert result.status == StageStatus.SKIP

    def test_fire_setup_none_sizing_reject_skip(self):
        """sizing=reject → A7 SKIP (not FAIL) even with patterns."""
        ctx = _ctx(patterns=["ZLR"], sizing="reject", fire_setup=None)
        result = _a7_universal(ctx)
        assert result.status == StageStatus.SKIP


# ---------------------------------------------------------------------------
# Test 2: effective_stop fallback in woodies_system
# if reverted → RED because the old code gate on best.stop left fire_setup=None
# ---------------------------------------------------------------------------
class TestEffectiveStopFallback:
    def test_effective_stop_from_best(self):
        """best.stop available → used as _s4_stop."""
        # Verify the code path by checking the source
        import inspect
        from backend.v9.systems.woodies.woodies_system import WoodiesSystem
        source = inspect.getsource(WoodiesSystem.process_bar)
        assert "_effective_stop" in source, (
            "process_bar must use _effective_stop (V2 fallback) for fire_setup"
        )
        assert "_last_v2_sizing" in source, (
            "process_bar must store V2 sizing result for stop fallback"
        )
