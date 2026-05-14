"""Behavior Phase detector — 4 phase scenarios."""
import pytest
from backend.v9.systems.behavior_phase.phase_detector import detect_phase, BehaviorPhase


def _make_bars(n, base_price=7500, trend=0, vol_trend=0):
    """Generate synthetic bars for testing."""
    bars = []
    for i in range(n):
        p = base_price + i * trend
        v = 100 + i * vol_trend
        bars.append({"o": p, "h": p + 2, "l": p - 1, "c": p + 1, "v": max(10, v)})
    return bars


def test_development_phase_flat_range():
    """Flat range, near POC, no volume increase → DEVELOPMENT."""
    bars = _make_bars(15, base_price=7500, trend=0, vol_trend=0)
    result = detect_phase(bars, ib_high=7510, ib_low=7490, poc=7501)
    assert result.phase == BehaviorPhase.DEVELOPMENT
    assert result.confidence > 0
    assert "reasoning_notes" in result.__dict__


def test_mature_phase_trending():
    """Strong uptrend with volume increase → MATURE."""
    bars = _make_bars(15, base_price=7500, trend=2, vol_trend=10)
    result = detect_phase(bars, ib_high=7505, ib_low=7495, poc=7500)
    assert result.phase == BehaviorPhase.MATURE
    assert result.confidence >= 0.6


def test_reversal_phase_exhaustion():
    """Range expanding (new high) but volume declining → REVERSAL."""
    bars = []
    for i in range(15):
        # Oscillating price (no clear HH/HL trend) but range gets wider
        p = 7500 + (i % 3 - 1) * 2
        v = 500 - i * 30  # volume declining
        h = p + 2 + (i * 0.5 if i == 14 else 0)  # last bar makes new high = range expansion
        bars.append({"o": p, "h": h, "l": p - 2 - (i * 0.5 if i == 13 else 0), "c": p + 1, "v": max(10, v)})
    result = detect_phase(bars, ib_high=7510, ib_low=7490, poc=7500)
    assert result.phase == BehaviorPhase.REVERSAL
    assert result.confidence > 0


def test_insufficient_bars_returns_development():
    """< 5 bars → DEVELOPMENT with 0 confidence."""
    result = detect_phase([{"o": 7500, "h": 7502, "l": 7498, "c": 7501, "v": 100}])
    assert result.phase == BehaviorPhase.DEVELOPMENT
    assert result.confidence == 0.0
