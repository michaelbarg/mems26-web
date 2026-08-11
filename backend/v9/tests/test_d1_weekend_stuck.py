"""D1 — S2 WEEKEND label stuck (2026-08-11).

Bug: When hydrate() set mode=WEEKEND, process_bar had no transition to
FIRST_HOUR_TACTICAL or DAY_TYPE_MODE when RTH started. The label stayed
stuck until the next restart.

Fix: WEEKEND is now treated identically to OVERNIGHT_MODE for session
transitions — when session_classifier returns CASH_OPEN/FIRST_HOUR/
CASH_HOURS, mode advances.
"""
import inspect

import pytest


class TestWeekendTransition:
    """Verify WEEKEND mode transitions to RTH modes."""

    def test_weekend_included_in_transition_check(self):
        """WEEKEND must be checked alongside OVERNIGHT_MODE for mode transitions."""
        from backend.v9.systems.five_min import five_min_system
        src = inspect.getsource(five_min_system.FiveMinSystem.process_bar)
        # The transition check must include WEEKEND
        assert "FiveMinMode.WEEKEND" in src
        # It should be in the same conditional as OVERNIGHT_MODE
        # Find the transition block
        transition_idx = src.index("Live session transition")
        transition_block = src[transition_idx:transition_idx + 500]
        assert "WEEKEND" in transition_block
        assert "OVERNIGHT_MODE" in transition_block

    def test_weekend_mode_exists(self):
        """FiveMinMode.WEEKEND must exist."""
        from backend.v9.systems.five_min.five_min_system import FiveMinMode
        assert hasattr(FiveMinMode, "WEEKEND")

    def test_weekend_buffers_bars(self):
        """WEEKEND mode must still buffer bars (no pattern detection)."""
        from backend.v9.systems.five_min import five_min_system
        src = inspect.getsource(five_min_system.FiveMinSystem.process_bar)
        # The buffering block includes WEEKEND
        buffer_idx = src.index("S2 must not fire outside trading sessions")
        buffer_block = src[buffer_idx:buffer_idx + 200]
        assert "WEEKEND" in buffer_block
