"""Stream 1.5 · _rescore_from_behavior returns NeuE/NeuC via classify_neutral_subtype."""
import pytest
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
from backend.v9.systems.day_type.schemas import (
    DayType, BarInput, Behavior, RangeCategory, FailedExtensionType,
)


def _bar(open_price=4490.0):
    """Minimal BarInput for driving _rescore_from_behavior."""
    return BarInput(
        ts=1716480000.0, session_min=30,
        open=open_price, high=open_price + 1, low=open_price - 1, close=open_price,
        volume=100,
    )


class TestConstructorBackwardCompat:
    def test_constructor_backward_compat_no_args(self):
        m = DayTypeStateMachine()
        assert m.prev_vah is None
        assert m.prev_val is None
        assert m.session_date is None
        assert m.session_open_price is None

    def test_constructor_accepts_prev_day_summary(self):
        m = DayTypeStateMachine(prev_day_summary={"vah": 4500, "val": 4480, "session_date": "2026-05-23"})
        assert m.prev_vah == 4500
        assert m.prev_val == 4480
        assert m.session_date == "2026-05-23"
        assert m.session_open_price is None  # captured in _stage_a1, not constructor


class TestStageA1CapturesOpen:
    def test_stage_a1_captures_session_open_price(self):
        m = DayTypeStateMachine()
        bar = _bar(open_price=4490.0)
        m._stage_a1(bar)
        assert m.session_open_price == 4490.0

    def test_stage_a1_does_not_overwrite_session_open(self):
        m = DayTypeStateMachine()
        m._stage_a1(_bar(open_price=4490.0))
        m._stage_a1(_bar(open_price=4495.0))
        assert m.session_open_price == 4490.0


class TestRescoreNeutralSubtype:
    def _setup_compressed_normal(self, m):
        m.behavior = Behavior.COMPRESSED
        m.range_category = RangeCategory.NORMAL
        m.failed_extension = FailedExtensionType.NONE

    def test_rescore_returns_neue_when_open_at_vah(self):
        m = DayTypeStateMachine(prev_day_summary={"vah": 4500, "val": 4480, "session_date": "2026-05-23"})
        m.session_open_price = 4500.0
        self._setup_compressed_normal(m)
        result = m._rescore_from_behavior(_bar())
        assert result == DayType.Neutral_Extreme

    def test_rescore_returns_neue_when_open_at_val(self):
        m = DayTypeStateMachine(prev_day_summary={"vah": 4500, "val": 4480, "session_date": "2026-05-23"})
        m.session_open_price = 4480.0
        self._setup_compressed_normal(m)
        result = m._rescore_from_behavior(_bar())
        assert result == DayType.Neutral_Extreme

    def test_rescore_returns_neuc_when_open_inside_va(self):
        m = DayTypeStateMachine(prev_day_summary={"vah": 4500, "val": 4480, "session_date": "2026-05-23"})
        m.session_open_price = 4490.0
        self._setup_compressed_normal(m)
        result = m._rescore_from_behavior(_bar())
        assert result == DayType.Neutral_Center

    def test_rescore_falls_back_to_neuc_without_prev_day_summary(self):
        m = DayTypeStateMachine(prev_day_summary=None)
        m.session_open_price = 4490.0
        self._setup_compressed_normal(m)
        result = m._rescore_from_behavior(_bar())
        assert result == DayType.Neutral_Center

    def test_rescore_falls_back_with_only_vah_missing(self):
        m = DayTypeStateMachine(prev_day_summary={"val": 4480, "session_date": "2026-05-23"})
        m.session_open_price = 4490.0
        self._setup_compressed_normal(m)
        result = m._rescore_from_behavior(_bar())
        assert result == DayType.Neutral_Center
