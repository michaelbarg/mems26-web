"""Tests for shared ATR utilities."""

from backend.v9.shared.atr import atr_5min, atr_daily, _wilder_atr


def _make_bars(ranges, close_start=5000.0):
    """Generate bar dicts from a list of (high-low) ranges."""
    bars = []
    c = close_start
    for r in ranges:
        h = c + r / 2
        l = c - r / 2
        bars.append({"h": h, "l": l, "c": h - 0.1})
        c = h - 0.1
    return bars


def test_returns_none_below_period():
    bars = _make_bars([1.0] * 10)
    assert atr_5min(bars, period=14) is None


def test_returns_value_at_exactly_period():
    bars = _make_bars([1.0] * 14)
    result = atr_5min(bars, period=14)
    assert result is not None
    assert result > 0


def test_constant_range_equals_range():
    """With constant bar ranges and no gaps, ATR should converge to range."""
    bars = _make_bars([2.0] * 30)
    result = atr_5min(bars, period=14)
    assert result is not None
    # With constant ranges and small prev_close gaps, ATR ≈ 2.0
    assert abs(result - 2.0) < 0.5


def test_daily_same_as_5min_algorithm():
    bars = _make_bars([3.0] * 20)
    assert atr_5min(bars) == atr_daily(bars)


def test_wilder_smoothing_applied():
    """Increasing ranges should produce ATR between min and max range."""
    bars = _make_bars([1.0] * 14 + [5.0] * 10)
    result = _wilder_atr(bars, 14)
    assert result is not None
    assert 1.0 < result < 5.0


def test_flags_default_off():
    """Feature flags default to False (OFF)."""
    from backend.v9.shared.atr import (
        S2_ATR_RELATIVE, S3_RELATIVE, S1_CVD_OPENING,
        S1_DAYTYPE_STAGING, S1_IB_WIDTH_ATR,
    )
    assert S2_ATR_RELATIVE is False
    assert S3_RELATIVE is False
    assert S1_CVD_OPENING is False
    assert S1_DAYTYPE_STAGING is False
    assert S1_IB_WIDTH_ATR is False
