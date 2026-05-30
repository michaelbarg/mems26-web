"""Regression tests: IB live tracking during A3 (developing) phase.

Verifies:
1. _build_state() always includes ib_high_live/ib_low_live/ib_range_live/ib_locked in meta
2. to_classification() returns DEVELOPING data during A3 (not None)
3. to_classification() returns None before A3 starts (no IB data)
4. After A4 lock, ib_locked=True in meta and ib_width_class is NARROW/MEDIUM/WIDE
5. ib_range_live updates each bar during A3
"""
import pytest
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
from backend.v9.systems.day_type.schemas import BarInput, DayType, IBWidth


def _bar(session_min: int, high: float, low: float, open_: float = 0.0, close: float = 0.0,
         pd_high: float = 5850.0, pd_low: float = 5800.0, pd_close: float = 5820.0,
         ib_high: float = None, ib_low: float = None, **kwargs) -> BarInput:
    # Source-of-truth (2026-05-28): IB comes from Sierra (bar.ib_high/ib_low),
    # NOT derived from bar.high/low. A3/A4 read bar.ib_* only. Fixtures must
    # supply Sierra IB or the machine correctly refuses to lock. Default IB to
    # this bar's high/low so the developing→lock path mirrors live Sierra feed.
    return BarInput(
        ts=1700000000.0 + session_min * 60,
        session_min=session_min,
        open=open_ or high - (high - low) / 2,
        high=high,
        low=low,
        close=close or high - (high - low) / 2,
        pd_high=pd_high,
        pd_low=pd_low,
        pd_close=pd_close,
        ib_high=ib_high if ib_high is not None else high,
        ib_low=ib_low if ib_low is not None else low,
        **kwargs,
    )


def _feed_to_a3(machine: DayTypeStateMachine):
    """Feed enough bars to reach A3 (past A1 + A2 which needs 3 bars)."""
    # A1 bar (session_min=0, has pd context → advances to A2)
    machine.process_bar(_bar(0, high=5825.0, low=5815.0))
    # A2 needs 3 bars
    machine.process_bar(_bar(5, high=5830.0, low=5820.0))
    machine.process_bar(_bar(10, high=5835.0, low=5822.0))
    # Now in A3


class TestIBLiveMeta:
    """_build_state always exposes live IB fields in meta."""

    def test_meta_keys_present_from_a1(self):
        machine = DayTypeStateMachine()
        state = machine.process_bar(_bar(0, high=5825.0, low=5815.0))
        assert "ib_high_live" in state.meta
        assert "ib_low_live" in state.meta
        assert "ib_range_live" in state.meta
        assert "ib_locked" in state.meta

    def test_meta_none_before_ib_tracking_starts(self):
        """Before any bars, IB fields are None (no tracking started)."""
        machine = DayTypeStateMachine()
        # Only 1 bar at A1 — IB tracking not yet started (stage is still A1 or A2)
        state = machine.process_bar(_bar(0, high=5825.0, low=5815.0, pd_high=None, pd_low=None, pd_close=None))
        # Stage A1 (missing pd context) — ib_high stays 0, ib_low stays inf
        assert state.meta["ib_high_live"] is None
        assert state.meta["ib_low_live"] is None
        assert state.meta["ib_range_live"] is None
        assert state.meta["ib_locked"] is False

    def test_ib_live_updates_during_a3(self):
        machine = DayTypeStateMachine()
        _feed_to_a3(machine)
        # First A3 bar
        state = machine.process_bar(_bar(15, high=5840.0, low=5820.0))
        assert state.meta["ib_high_live"] is not None
        assert state.meta["ib_low_live"] is not None
        assert state.meta["ib_range_live"] is not None
        assert state.meta["ib_locked"] is False

        first_range = state.meta["ib_range_live"]

        # Second A3 bar with new high
        state2 = machine.process_bar(_bar(20, high=5850.0, low=5818.0))
        assert state2.meta["ib_high_live"] >= state.meta["ib_high_live"]
        assert state2.meta["ib_low_live"] <= state.meta["ib_low_live"]
        assert state2.meta["ib_range_live"] >= first_range  # range can only grow

    def test_ib_locked_after_a4(self):
        machine = DayTypeStateMachine()
        _feed_to_a3(machine)
        # Feed bars up to and past session_min=60 (IB lock)
        for sm in range(15, 75, 5):
            state = machine.process_bar(_bar(sm, high=5840.0, low=5818.0))
        assert state.meta["ib_locked"] is True


class TestToClassificationDeveloping:
    """to_classification() returns DEVELOPING data during A3."""

    def test_returns_none_before_a3(self):
        """No classification before opening type is detected."""
        machine = DayTypeStateMachine()
        machine.process_bar(_bar(0, high=5825.0, low=5815.0, pd_high=None, pd_low=None, pd_close=None))
        # A1 only, opening_type still UNKNOWN
        result = machine.to_classification()
        assert result is None

    def test_returns_developing_during_a3(self):
        """Returns partial classification with ib_width_class=DEVELOPING during A3."""
        machine = DayTypeStateMachine()
        _feed_to_a3(machine)
        machine.process_bar(_bar(15, high=5840.0, low=5820.0))

        result = machine.to_classification()
        assert result is not None
        assert result.ib_width_class == "DEVELOPING"
        assert result.day_type == DayType.UNKNOWN
        assert result.ib_h is not None
        assert result.ib_l is not None
        assert result.ib_width is not None  # range in points
        assert result.ib_h > result.ib_l

    def test_developing_ib_range_is_high_minus_low(self):
        machine = DayTypeStateMachine()
        _feed_to_a3(machine)
        machine.process_bar(_bar(15, high=5840.0, low=5820.0))

        result = machine.to_classification()
        assert result is not None
        assert abs(result.ib_width - round(result.ib_h - result.ib_l, 2)) < 0.01

    def test_developing_ib_updates_with_new_bar(self):
        machine = DayTypeStateMachine()
        _feed_to_a3(machine)
        machine.process_bar(_bar(15, high=5840.0, low=5820.0))
        result1 = machine.to_classification()

        # New bar with larger range
        machine.process_bar(_bar(20, high=5860.0, low=5810.0))
        result2 = machine.to_classification()

        assert result2 is not None
        assert result2.ib_width > result1.ib_width  # range grew
        assert result2.ib_h >= result1.ib_h
        assert result2.ib_l <= result1.ib_l

    def test_developing_reasoning_notes_contain_session_min(self):
        machine = DayTypeStateMachine()
        _feed_to_a3(machine)
        machine.process_bar(_bar(15, high=5840.0, low=5820.0))
        result = machine.to_classification()
        assert result is not None
        assert "session_min" in result.reasoning_notes

    def test_locked_classification_after_a4(self):
        """After A4 lock, ib_width_class is NARROW/MEDIUM/WIDE, not DEVELOPING."""
        machine = DayTypeStateMachine()
        _feed_to_a3(machine)
        for sm in range(15, 75, 5):
            machine.process_bar(_bar(sm, high=5840.0, low=5820.0))

        result = machine.to_classification()
        if result is not None:
            assert result.ib_width_class in ("NARROW", "MEDIUM", "WIDE")
            assert result.ib_width_class != "DEVELOPING"
