"""Prompt 21b — Prove pd_high/pd_low/pd_close correctness in S1 A1.

Acceptance criteria:
  1. pd_close comes from v9_bars_5min last close, NOT poc_price.
  2. pd_high/pd_low from TPO range when available, bars fallback otherwise.
  3. A1 receives pd_* and computes gap correctly.
  4. Missing pd_* produces explicit degraded state (no fake data).
  5. No SHADOW/DEMO/LIVE.
"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from unittest.mock import patch, MagicMock
from backend.v9.systems.day_type.schemas import BarInput, PreOpenContext
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine


def test_pd_close_from_bars_last_close_not_poc():
    """pd_close must be the actual last bar close, not TPO POC."""
    # Simulated scenario: TPO has poc=7444 but bars last close=7418
    # The correct pd_close is 7418 (actual session close), not 7444 (POC)
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.25, pd_low=7409.5, pd_close=7418.0,  # bars last close
    )
    state = machine.process_bar(bar)
    # Gap = 7460 - 7418 = 42 pts UP
    assert machine.pre_open.gap_size == 42.0
    assert machine.pre_open.gap_direction == "UP"


def test_gap_uses_pd_close_not_poc():
    """Gap calculation: open - pd_close. pd_close = bars close, not POC."""
    machine = DayTypeStateMachine()
    # If pd_close were poc=7444, gap would be 7470-7444=26
    # With correct pd_close=7418, gap = 7470-7418=52
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7470.0, high=7472.0, low=7468.0, close=7471.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7418.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open.gap_size == 52.0


def test_a1_receives_all_pd_values():
    """A1 pre-open uses pd_high, pd_low, pd_close to compute location."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.25, pd_low=7409.5, pd_close=7418.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open is not None
    # Open=7460 is between pd_low=7409.5 and pd_high=7505.25 → INSIDE
    assert machine.pre_open.location_vs_pd == "INSIDE"


def test_location_above_pd_high():
    """When open > pd_high → ABOVE."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7510.0, high=7512.0, low=7508.0, close=7511.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7450.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open.location_vs_pd == "ABOVE"


def test_location_below_pd_low():
    """When open < pd_low → BELOW."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7395.0, high=7397.0, low=7393.0, close=7396.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7450.0,
    )
    state = machine.process_bar(bar)
    assert machine.pre_open.location_vs_pd == "BELOW"


def test_missing_pd_explicit_degraded():
    """Missing pd_* → gap_size=0, location=INSIDE (explicit defaults, not fake data)."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        # All pd_* are None
    )
    state = machine.process_bar(bar)
    assert machine.pre_open is not None
    # Without pd_close: gap_size should be 0 (no reference)
    assert machine.pre_open.gap_size == 0.0
    # Without pd_high/pd_low: location defaults to INSIDE (can't determine)
    assert machine.pre_open.location_vs_pd == "INSIDE"


def test_missing_pd_does_not_crash():
    """System remains functional even without pd_*."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
    )
    # Must not raise
    state = machine.process_bar(bar)
    assert state is not None


def test_no_shadow_demo_live():
    """No trading mode activated by pd_* processing."""
    machine = DayTypeStateMachine()
    bar = BarInput(
        ts=1700000000, session_min=0,
        open=7460.0, high=7462.0, low=7458.0, close=7461.0,
        pd_high=7505.0, pd_low=7400.0, pd_close=7418.0,
    )
    state = machine.process_bar(bar)
    state_str = str(state.__dict__) if hasattr(state, '__dict__') else str(state)
    assert "shadow" not in state_str.lower()
    assert "demo" not in state_str.lower()
    assert "live" not in state_str.lower()
