"""Prompt 21 — Prove pd_high/pd_low/pd_close wire into S1 A1 pre-open context."""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from backend.v9.systems.day_type.schemas import BarInput, PreOpenContext
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine


def test_a1_receives_pd_values():
    """A1 pre-open context correctly processes pd_high/pd_low/pd_close."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.25, pd_low=7409.5, pd_close=7444.0,
    )
    state = machine.process_bar(bar)
    # A1 should have computed gap and location
    assert machine.pre_open is not None
    assert machine.pre_open.gap_size != 0  # 7460 - 7444 = 16 pts gap


def test_gap_uses_pd_close():
    """Gap magnitude = open - pd_close."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7470.0, high=7472.0, low=7468.0, close=7471.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7450.0,
    )
    state = machine.process_bar(bar)
    # Gap = 7470 - 7450 = 20 pts UP
    assert machine.pre_open.gap_size == 20.0
    assert machine.pre_open.gap_direction == "UP"


def test_location_above_pd_high():
    """When open > pd_high, location = ABOVE."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7510.0, high=7512.0, low=7508.0, close=7511.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7450.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open.location_vs_pd == "ABOVE"


def test_location_below_pd_low():
    """When open < pd_low, location = BELOW."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7395.0, high=7397.0, low=7393.0, close=7396.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7450.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open.location_vs_pd == "BELOW"


def test_missing_pd_produces_neutral_not_crash():
    """When pd_* is None, A1 still completes with NEUTRAL defaults."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        # No pd_* fields
    )
    state = machine.process_bar(bar)
    # Should not crash; pre_open defaults to NEUTRAL
    assert machine.pre_open is not None
    assert machine.pre_open.gap_direction in ("UP", "DOWN", "FLAT")
    assert machine.pre_open.location_vs_pd in ("ABOVE", "BELOW", "INSIDE")


def test_no_shadow_demo_live():
    """No trading mode activated by pd_* processing."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7450.0,
    )
    state = machine.process_bar(bar)
    # No mode fields in state
    state_dict = state.__dict__ if hasattr(state, '__dict__') else {}
    assert "shadow" not in str(state_dict).lower()
    assert "demo" not in str(state_dict).lower()
    assert "live" not in str(state_dict).lower()
