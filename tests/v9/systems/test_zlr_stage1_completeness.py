"""Tests: ZLR Stage-1 completeness (W-6).

Verifies ZLR detection across CCI strength levels and direction mirroring.
"""

import pytest
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult
from backend.v9.systems.woodies.patterns import zlr


def make_bar(ts=1000.0, close=5250.0, high=5252.0, low=5248.0,
             open_=5249.0, volume=100, cci_14=0.0, cci_6_tcci=0.0,
             ema_34=5250.0, trend_state="GRAY", **kwargs) -> WoodiesBar:
    return WoodiesBar(
        ts=ts, open=open_, high=high, low=low, close=close,
        volume=volume, cci_14=cci_14, cci_6_tcci=cci_6_tcci,
        ema_34=ema_34, trend_state=trend_state, **kwargs,
    )


def make_bars_from_cci(cci_values, base_close=5250.0, step=0.5,
                       trend_state="GRAY", **kwargs):
    bars = []
    for i, cci in enumerate(cci_values):
        c = base_close + i * step
        bars.append(make_bar(
            ts=1000.0 + i * 1800,
            close=c, high=c + 1.5, low=c - 1.0, open_=c - 0.25,
            cci_14=cci, cci_6_tcci=cci * 1.1, trend_state=trend_state,
            **kwargs,
        ))
    return bars


class TestZLRStage1:
    def test_strong_trend_above_200_detects(self):
        """CCI > 200 in lookback should trigger ZLR when pullback+bounce present."""
        # Need >=13 bars (LOOKBACK=12), last 3 CCI range >= 50 for AP8
        cci = [0] * 5 + [220, 180, 60, 50, 40, 30, 55, 100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is True
        assert result.direction == "LONG"

    def test_moderate_trend_100_200_detects(self):
        """CCI 100-200 should trigger ZLR with correct pullback pattern."""
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is True
        assert result.direction == "LONG"

    def test_no_trend_below_100_no_detect(self):
        """CCI staying < 100 should NOT trigger ZLR (no extreme in lookback)."""
        cci = [0] * 5 + [50, 60, 70, 40, 30, 20, 35, 60]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is False

    def test_red_direction_mirror(self):
        """ZLR SHORT: CCI < -100 extreme, pullback to zero, bounce down."""
        cci = [0] * 5 + [-120, -130, -110, -60, -50, -20, -55, -100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is True
        assert result.direction == "SHORT"

    def test_13_bar_pullback_blocked_by_ap1(self):
        """AP1 blocks ZLR when pullback exceeds max bars (>12 bars in zone)."""
        # 15 bars of pullback within -100..+100 should be AP1-blocked
        cci = [150] + [50] * 14 + [80]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        # With 15-bar pullback, AP1 should block or the extreme is out of lookback
        # Either way, detection should fail
        assert result.detected is False
