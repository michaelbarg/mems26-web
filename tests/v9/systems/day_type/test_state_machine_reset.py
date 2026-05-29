"""Test DayTypeStateMachine.reset() method.

P31-B: After reset(), the machine must return to __init__ defaults.
to_classification() must return None after reset.
"""

import pytest

from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
from backend.v9.systems.day_type.schemas import (
    BarInput, DayType, Stage, Behavior, RangeCategory, FailedExtensionType,
)


class TestStateMachineReset:

    def _make_bar(self, **overrides) -> BarInput:
        defaults = dict(
            ts=1716900000, session_min=0, open=7500.0, high=7510.0,
            low=7490.0, close=7505.0, volume=100, is_rth=True,
            pd_high=7520.0, pd_low=7480.0, pd_close=7500.0,
        )
        defaults.update(overrides)
        return BarInput(**defaults)

    def test_reset_restores_initial_stage(self):
        machine = DayTypeStateMachine()
        bar = self._make_bar(session_min=0)
        machine.process_bar(bar)
        # Should have advanced from A1
        assert machine.bar_count > 0

        machine.reset()

        assert machine.stage == Stage.A1
        assert machine.day_type == DayType.UNKNOWN
        assert machine.confidence == 0.0
        assert machine.lock_state == "PENDING"
        assert machine.bar_count == 0

    def test_reset_clears_ib(self):
        machine = DayTypeStateMachine()
        machine.ib_high = 7550.0
        machine.ib_low = 7500.0
        machine.ib_locked = True

        machine.reset()

        assert machine.ib_high == 0.0
        assert machine.ib_low == float("inf")
        assert machine.ib_locked is False
        assert machine.ib_class is None

    def test_to_classification_returns_none_after_reset(self):
        machine = DayTypeStateMachine()
        # Process enough bars to get a classification
        bar = self._make_bar(session_min=0)
        machine.process_bar(bar)

        machine.reset()

        result = machine.to_classification()
        assert result is None, "to_classification() must return None after reset()"

    def test_reset_clears_vote_history(self):
        machine = DayTypeStateMachine()
        bar = self._make_bar(session_min=0)
        machine.process_bar(bar)

        machine.reset()

        assert machine.vote_history == []
        assert machine.behavior == Behavior.DEVELOPING
        assert machine.range_category == RangeCategory.NORMAL
        assert machine.failed_extension == FailedExtensionType.NONE

    def test_reset_clears_session_tracking(self):
        machine = DayTypeStateMachine()
        machine.session_high = 7600.0
        machine.session_low = 7400.0
        machine.globex_h = 7550.0
        machine.rth_session_h = 7580.0

        machine.reset()

        assert machine.session_high == 0.0
        assert machine.session_low == float("inf")
        assert machine.globex_h == 0.0
        assert machine.globex_l == float("inf")
        assert machine.rth_session_h == 0.0
        assert machine.rth_session_l == float("inf")

    def test_reset_clears_v9_state(self):
        machine = DayTypeStateMachine()
        machine._latest_cvd_state = "BULLISH"
        machine._max_tpo_row_width = 12
        machine._active_zohar_rules = ["delta", "width"]

        machine.reset()

        assert machine._latest_cvd_state is None
        assert machine._max_tpo_row_width == 0
        assert machine._active_zohar_rules == []
        assert machine._last_state is None

    def test_reset_preserves_config_and_collaborators(self):
        """reset() must NOT clear config or injected collaborators."""
        from unittest.mock import MagicMock
        mock_zohar = MagicMock()
        mock_ext = MagicMock()
        machine = DayTypeStateMachine(
            zohar_engine=mock_zohar,
            extension_tracker=mock_ext,
        )

        machine.reset()

        assert machine._zohar_engine is mock_zohar
        assert machine._extension_tracker is mock_ext
        assert machine.config is not None
