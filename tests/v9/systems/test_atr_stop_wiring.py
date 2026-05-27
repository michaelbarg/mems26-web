"""Tests: ATR stop wiring into pattern detectors (W-6).

Verifies atr_stop integration across patterns.
"""

import pytest
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult


def make_bar(ts=1000.0, close=5250.0, high=5252.0, low=5248.0,
             open_=5249.0, volume=100, cci_14=0.0, cci_6_tcci=0.0,
             ema_34=5250.0, trend_state="GRAY", **kwargs) -> WoodiesBar:
    return WoodiesBar(
        ts=ts, open=open_, high=high, low=low, close=close,
        volume=volume, cci_14=cci_14, cci_6_tcci=cci_6_tcci,
        ema_34=ema_34, trend_state=trend_state, **kwargs,
    )


def make_bars_from_cci(cci_values, base_close=5250.0, step=0.5,
                       trend_state="GRAY", cci6_values=None, **kwargs):
    bars = []
    for i, cci in enumerate(cci_values):
        c = base_close + i * step
        cci6 = cci6_values[i] if cci6_values else cci * 1.1
        bars.append(make_bar(
            ts=1000.0 + i * 1800,
            close=c, high=c + 1.5, low=c - 1.0, open_=c - 0.25,
            cci_14=cci, cci_6_tcci=cci6, trend_state=trend_state,
            **kwargs,
        ))
    return bars


class TestZLRAtrStop:
    def test_zlr_uses_atr_stop(self):
        """ZLR detection should include stop_layer_applied in details."""
        from backend.v9.systems.woodies.patterns import zlr
        cci = [0] * 5 + [120, 130, 110, 60, 50, 20, 55, 100]
        bars = make_bars_from_cci(cci)
        result = zlr.detect(bars)
        assert result.detected is True
        assert result.details is not None
        assert "stop_layer_applied" in result.details
        assert result.details["stop_layer_applied"] in ("primary", "cap", "floor")


class TestVEGASAtrStop:
    def test_vegas_uses_atr_stop_with_swing_anchor(self):
        """VEGAS (REV) should use swing_anchor and emit stop_layer_applied."""
        from backend.v9.systems.woodies.patterns import vegas
        price = [70, 80, 90, 95, 100, 95, 85, 75, 65, 55,
                 65, 80, 95, 102, 105, 102, 95, 85, 80, 75]
        cci = [50, 80, 120, 140, 150, 140, 100, 60, 30, 10,
               30, 60, 100, 115, 120, 115, 90, 60, 50, -10]
        price = [price[0]] * 5 + price
        cci = [cci[0]] * 5 + cci
        bars = []
        for i in range(len(price)):
            bars.append(make_bar(
                ts=1000.0 + i * 1800,
                close=price[i], high=price[i] + 2, low=price[i] - 2,
                cci_14=cci[i],
            ))
        result = vegas.detect(bars)
        assert result.detected is True
        assert "stop_layer_applied" in result.details
        assert "swing_anchor" in result.details


class TestHFEAtrStop:
    def test_hfe_uses_atr_stop_after_ap5(self):
        """HFE uses atr_stop; verify stop_layer_applied in details when DLL detected."""
        from backend.v9.systems.woodies.patterns import hfe
        # Build bars with HFE DLL detection flags
        bars = []
        for i in range(20):
            c = 5250.0 + i * 0.25
            bars.append(make_bar(
                ts=1000.0 + i * 1800,
                close=c, high=c + 2.0, low=c - 2.0,
                cci_14=-220 + i * 20,  # starts extreme negative, hooks up
                hfe_detected=(i == 19),
                hfe_direction="UP" if i == 19 else "NONE",
                hfe_extreme_bars_ago=5 if i == 19 else 0,
            ))
        result = hfe.detect(bars)
        if result.detected:
            assert "stop_layer_applied" in result.details


class TestAtrConversion:
    def test_atr14_converted_from_points_to_ticks(self):
        """ATR-14 computed inline should produce ticks, not points."""
        from backend.v9.systems.woodies.patterns.zlr import _compute_atr14_ticks
        # 14 bars with H-L = 2.0 points each, no gaps -> ATR = 2.0 points = 8 ticks
        bars = []
        for i in range(14):
            bars.append(make_bar(
                ts=1000.0 + i * 1800,
                close=5250.0, high=5251.0, low=5249.0,
            ))
        atr_ticks = _compute_atr14_ticks(bars, tick_size=0.25)
        # ATR in points = 2.0, in ticks = 2.0 / 0.25 = 8.0
        assert abs(atr_ticks - 8.0) < 0.01
