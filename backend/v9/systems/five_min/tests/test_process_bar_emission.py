"""Tests for process_bar → emit_t1_setup wire (Phase 5.5 final auto-fire)."""
import asyncio
from unittest.mock import patch, MagicMock

from backend.v9.systems.five_min.five_min_system import FiveMinSystem


def _reactive_long_bars():
    """4 bars matching Reactive LONG criteria."""
    return [
        {"o": 5250, "h": 5250, "l": 5247, "c": 5247.5, "v": 1000},
        {"o": 5248, "h": 5248, "l": 5247, "c": 5247.75, "v": 80},
        {"o": 5247.25, "h": 5249, "l": 5247.25, "c": 5248.75, "v": 800},
        {"o": 5248.5, "h": 5250, "l": 5248.5, "c": 5249.75, "v": 700},
    ]


def _make_sys():
    """Create FiveMinSystem with required state initialized."""
    sys = FiveMinSystem()
    sys._hydrated = True
    sys.current_state = {"last_reasoning_notes": ""}
    sys.last_pattern = None
    sys.last_classification = None
    sys.last_confluence = 0
    sys.opening_type = None
    return sys


@patch('backend.v9.systems.five_min.five_min_system.emit_t1_setup')
@patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
@patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
@patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
def test_process_bar_emits_setup_on_pattern_match(_belly, _amt, _cot, mock_emit):
    """When pattern fires → emit_t1_setup called."""
    mock_emit.return_value = MagicMock(pattern_name='REACTIVE_LONG')
    sys = _make_sys()
    sys._bar_buffer = _reactive_long_bars()[:-1]  # pre-load 3 bars

    asyncio.run(sys.process_bar(_reactive_long_bars()[-1]))
    assert mock_emit.called


@patch('backend.v9.systems.five_min.five_min_system.emit_t1_setup')
def test_process_bar_no_emit_on_no_pattern(mock_emit):
    """Neutral bars → no pattern → no emit."""
    sys = _make_sys()
    asyncio.run(sys.process_bar({"o": 5250, "h": 5251, "l": 5249, "c": 5250, "v": 500}))
    assert not mock_emit.called


@patch('backend.v9.systems.five_min.five_min_system.emit_t1_setup', side_effect=Exception("emitter crash"))
@patch.object(FiveMinSystem, '_get_cot_from_footprint', return_value=150.0)
@patch.object(FiveMinSystem, '_get_amt_from_footprint', return_value=100.0)
@patch.object(FiveMinSystem, '_get_belly_from_footprint', return_value=True)
def test_process_bar_handles_emitter_exception(_belly, _amt, _cot, mock_emit):
    """Emitter raises → process_bar doesn't crash."""
    sys = _make_sys()
    sys._bar_buffer = _reactive_long_bars()[:-1]

    # Should NOT raise despite emitter crashing
    asyncio.run(sys.process_bar(_reactive_long_bars()[-1]))
