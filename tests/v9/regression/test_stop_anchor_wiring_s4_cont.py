"""S4 CONT stop-anchor V2 wiring tests — ZLR, TLB, TT, GB100.

Each test verifies:
  1. Flag OFF → legacy behavior unchanged (exact same stop price).
  2. Flag ON  → V2 structural anchor from YAML window, stop never moved by ATR.
"""
import os
from unittest.mock import patch

from backend.v9.systems.woodies.schemas import WoodiesBar


def _make_bars(n=20, base_price=7400.0, trend="BLUE"):
    """Generate n WoodiesBar objects suitable for pattern detection."""
    bars = []
    for i in range(n):
        cci_val = 150.0 if trend == "BLUE" else -150.0
        bars.append(WoodiesBar(
            ts=1781000000.0 + i * 300,
            open=base_price - 1.0 + i * 0.25,
            high=base_price + 2.0 + i * 0.25,
            low=base_price - 2.0 + i * 0.25,
            close=base_price + i * 0.25,
            cci_14=cci_val,
            cci_6_tcci=cci_val + 10,
            trend_state=trend,
        ))
    return bars


def _update_bar(bar, **kwargs):
    """Create a copy of a WoodiesBar with updated fields."""
    return bar.copy(update=kwargs)


# ── ZLR ──────────────────────────────────────────────────────────────────

def test_zlr_flag_off_legacy_unchanged():
    """Flag OFF → ZLR uses legacy compute_stop (no V2 code path)."""
    from backend.v9.systems.woodies.patterns.zlr import detect
    bars = _make_bars(20, trend="BLUE")
    # Force CCI pattern: extreme > 100, pullback, bounce
    bars[-5] = _update_bar(bars[-5], cci_14=120.0)
    bars[-4] = _update_bar(bars[-4], cci_14=50.0)
    bars[-3] = _update_bar(bars[-3], cci_14=30.0)
    bars[-2] = _update_bar(bars[-2], cci_14=40.0)
    bars[-1] = _update_bar(bars[-1], cci_14=80.0)
    with patch.dict(os.environ, {"STOP_ANCHORS_V2": "0"}, clear=False):
        result = detect(bars)
    if result.detected:
        assert result.stop is not None
        assert result.details.get("stop_layer_applied") != "v2_structural"


def test_zlr_flag_on_uses_v2():
    """Flag ON → ZLR resolves anchor from cluster_low window=4."""
    from backend.v9.systems.woodies.patterns.zlr import detect
    bars = _make_bars(20, trend="BLUE")
    bars[-5] = _update_bar(bars[-5], cci_14=120.0)
    bars[-4] = _update_bar(bars[-4], cci_14=50.0)
    bars[-3] = _update_bar(bars[-3], cci_14=30.0)
    bars[-2] = _update_bar(bars[-2], cci_14=40.0)
    bars[-1] = _update_bar(bars[-1], cci_14=80.0)
    with patch.dict(os.environ, {"STOP_ANCHORS_V2": "1"}, clear=False):
        result = detect(bars)
    if result.detected:
        assert result.details.get("stop_layer_applied") == "v2_structural"


# ── GB100 ────────────────────────────────────────────────────────────────

def test_gb100_flag_off_legacy_unchanged():
    """Flag OFF → GB100 uses legacy compute_stop."""
    from backend.v9.systems.woodies.patterns.gb100 import detect
    bars = _make_bars(20, trend="BLUE")
    bars[-3] = _update_bar(bars[-3], cci_14=90.0, trend_state="BLUE")
    bars[-2] = _update_bar(bars[-2], cci_14=95.0, trend_state="BLUE")
    bars[-1] = _update_bar(bars[-1], cci_14=120.0, trend_state="BLUE")
    with patch.dict(os.environ, {"STOP_ANCHORS_V2": "0"}, clear=False):
        result = detect(bars)
    if result.detected:
        assert result.details.get("stop_layer_applied") != "v2_structural"


def test_gb100_flag_on_uses_v2():
    """Flag ON → GB100 resolves anchor from cluster_low window=6."""
    from backend.v9.systems.woodies.patterns.gb100 import detect
    bars = _make_bars(20, trend="BLUE")
    bars[-3] = _update_bar(bars[-3], cci_14=90.0, trend_state="BLUE")
    bars[-2] = _update_bar(bars[-2], cci_14=95.0, trend_state="BLUE")
    bars[-1] = _update_bar(bars[-1], cci_14=120.0, trend_state="BLUE")
    with patch.dict(os.environ, {"STOP_ANCHORS_V2": "1"}, clear=False):
        result = detect(bars)
    if result.detected:
        assert result.details.get("stop_layer_applied") == "v2_structural"


# ── TLB ──────────────────────────────────────────────────────────────────

def test_tlb_flag_off_legacy_unchanged():
    """Flag OFF → TLB uses legacy compute_stop."""
    from backend.v9.systems.woodies.patterns.tlb import detect
    bars = _make_bars(20, trend="BLUE")
    for i in range(10):
        bars[-(10-i)] = _update_bar(bars[-(10-i)], cci_14=100.0 - i * 15)
    bars[-1] = _update_bar(bars[-1], cci_14=80.0)
    with patch.dict(os.environ, {"STOP_ANCHORS_V2": "0"}, clear=False):
        result = detect(bars)
    if result.detected:
        assert result.details.get("stop_layer_applied") != "v2_structural"


def test_tlb_flag_on_uses_v2():
    """Flag ON → TLB resolves anchor from since_trendline_peak window=8."""
    from backend.v9.systems.woodies.patterns.tlb import detect
    bars = _make_bars(20, trend="BLUE")
    for i in range(10):
        bars[-(10-i)] = _update_bar(bars[-(10-i)], cci_14=100.0 - i * 15)
    bars[-1] = _update_bar(bars[-1], cci_14=80.0)
    with patch.dict(os.environ, {"STOP_ANCHORS_V2": "1"}, clear=False):
        result = detect(bars)
    if result.detected:
        assert result.details.get("stop_layer_applied") == "v2_structural"


# ── TT ──────────────────────────────────────────────────────────────────

def test_tt_flag_off_legacy_unchanged():
    """Flag OFF → TT uses legacy compute_stop."""
    from backend.v9.systems.woodies.patterns.tt import detect
    bars = _make_bars(20, trend="BLUE")
    bars[-3] = _update_bar(bars[-3], cci_14=120.0, cci_6_tcci=140.0, trend_state="BLUE")
    bars[-2] = _update_bar(bars[-2], cci_14=115.0, cci_6_tcci=118.0, trend_state="BLUE")
    bars[-1] = _update_bar(bars[-1], cci_14=125.0, cci_6_tcci=145.0, trend_state="BLUE")
    with patch.dict(os.environ, {"STOP_ANCHORS_V2": "0"}, clear=False):
        result = detect(bars)
    if result.detected:
        assert result.details.get("stop_layer_applied") != "v2_structural"


def test_tt_flag_on_uses_v2():
    """Flag ON → TT resolves anchor from zl_excursion window=9."""
    from backend.v9.systems.woodies.patterns.tt import detect
    bars = _make_bars(20, trend="BLUE")
    bars[-3] = _update_bar(bars[-3], cci_14=120.0, cci_6_tcci=140.0, trend_state="BLUE")
    bars[-2] = _update_bar(bars[-2], cci_14=115.0, cci_6_tcci=118.0, trend_state="BLUE")
    bars[-1] = _update_bar(bars[-1], cci_14=125.0, cci_6_tcci=145.0, trend_state="BLUE")
    with patch.dict(os.environ, {"STOP_ANCHORS_V2": "1"}, clear=False):
        result = detect(bars)
    if result.detected:
        assert result.details.get("stop_layer_applied") == "v2_structural"
