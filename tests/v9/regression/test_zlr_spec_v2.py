"""Anti-tautological regression tests for ZLR_SPEC_V2 flag.

When ON, the ZLR detector gates fires on Michael's source characterization:
Stage 1 (trend): 6+ bars blue, SWI yellow/green, 3 bars above EMA-34
Stage 3 (entry): CCI diff >=15, entry CCI <=120, SWI yellow/green, CZI cyan 3 bars

if reverted → RED because: removing _zlr_spec_v2_check or the ZLR_SPEC_V2 gate
would let the bare CCI-geometry fires through, failing the flag-ON block assertions.
"""
import os
import pytest
from unittest.mock import patch

from backend.v9.systems.woodies.schemas import WoodiesBar
from backend.v9.systems.woodies.patterns.zlr import (
    detect, _swi_color, _czi_cyan_for_direction, _zlr_spec_v2_check,
)


def _bar(cci=50.0, tcci=40.0, close=7450.0, ema=7440.0, swi=30.0, czi=50.0,
         trend="BLUE", ts=1000.0, high=7455.0, low=7445.0) -> WoodiesBar:
    return WoodiesBar(
        ts=ts, open=close - 1, high=high, low=low, close=close, volume=1000,
        cci_14=cci, cci_6_tcci=tcci, ema_34=ema, lsma_value=close,
        swi_value=swi, czi_value=czi, trend_state=trend,
        predictor_next_cci=cci,
        hfe_detected=False, hfe_direction="NONE", hfe_extreme_bars_ago=0,
    )


def _full_spec_bars_long():
    """Build a bar buffer that satisfies ALL spec conditions for ZLR UP.
    13 bars: 6+ BLUE, CCI>100 extreme, pullback, bounce with CCI diff >=15,
    entry <=120, SWI yellow, CZI cyan, close > EMA-34.
    AP8 requires CCI range > 50 over last 3 bars.
    """
    bars = []
    # Bars 0-7: trend phase (BLUE, CCI above 0, 2 bars >100, SWI yellow=30, CZI=50, close>EMA)
    for i in range(8):
        cci = 150.0 if i in (3, 4) else 80.0  # bars 3,4 have CCI>100 (Stage 1.2)
        bars.append(_bar(cci=cci, tcci=cci*0.8, close=7450+i, ema=7440.0,
                         swi=30.0, czi=50.0, trend="BLUE", ts=float(1000+i*300)))
    # Bar 8: start pullback — CCI drops to 40 (below 100, above -100)
    bars.append(_bar(cci=40.0, tcci=35.0, close=7452, ema=7440, swi=30, czi=40,
                     trend="BLUE", ts=3400.0))
    # Bar 9: deeper pullback — CCI at 10 (needs to be low enough for AP8 range >50)
    bars.append(_bar(cci=10.0, tcci=8.0, close=7448, ema=7440, swi=30, czi=30,
                     trend="BLUE", ts=3700.0))
    # Bar 10: start bounce — CCI at 50
    bars.append(_bar(cci=50.0, tcci=55.0, close=7451, ema=7440, swi=30, czi=40,
                     trend="BLUE", ts=4000.0))
    # Bar 11: CZI cyan filler — CCI at 30 (range across 10,50,30,90 > 50 for AP8)
    bars.append(_bar(cci=30.0, tcci=35.0, close=7453, ema=7440, swi=35, czi=50,
                     trend="BLUE", ts=4300.0))
    # Bar 12 (entry): CCI=90 (<=120), prev=30 → diff=60 >=15, SWI=35 (yellow),
    # CZI=55 (>0=cyan), close=7455>EMA=7440. AP8 range: max(30,90)-min(30,90)=60>50 ✓
    bars.append(_bar(cci=90.0, tcci=95.0, close=7455, ema=7440, swi=35, czi=55,
                     trend="BLUE", ts=4600.0))
    return bars


def _no_swi_bars_long():
    """Like full spec but SWI is RED (=10, |10|<20) everywhere → fails S1.3."""
    bars = _full_spec_bars_long()
    for b in bars:
        b.swi_value = 10.0  # red
    return bars


def _high_cci_entry_bars_long():
    """Like full spec but entry CCI=140 (>120) → fails S3.7."""
    bars = _full_spec_bars_long()
    bars[-1].cci_14 = 140.0
    return bars


def _weak_bounce_bars_long():
    """Like full spec but CCI diff only 5 (<15) → fails S3.3.
    Keep AP8 range > 50 by keeping bar[-3] CCI low enough."""
    bars = _full_spec_bars_long()
    bars[-3].cci_14 = 10.0  # ensure AP8 range: max(10,37,42)-min(10,37,42) = 32... need more
    bars[-2].cci_14 = 37.0  # prev
    bars[-1].cci_14 = 42.0  # current: diff = 5 < 15; AP8 range = 42-10 = 32 < 50... still fails
    # Need range > 50 over last 3 bars: set bar[-3] very low
    bars[-3].cci_14 = -15.0  # AP8 range: max(-15,37,42)-min(-15,37,42) = 42-(-15) = 57 > 50 ✓
    return bars


# ── SWI/CZI color mapping tests ─────────────────────────────────────────

def test_swi_color_green():
    assert _swi_color(45.0) == "green"
    assert _swi_color(-50.0) == "green"

def test_swi_color_yellow():
    assert _swi_color(30.0) == "yellow"
    assert _swi_color(-25.0) == "yellow"

def test_swi_color_red():
    assert _swi_color(15.0) == "red"
    assert _swi_color(-10.0) == "red"
    assert _swi_color(0.0) == "red"

def test_czi_cyan_long():
    assert _czi_cyan_for_direction(50.0, "LONG") is True
    assert _czi_cyan_for_direction(-10.0, "LONG") is False

def test_czi_cyan_short():
    assert _czi_cyan_for_direction(-50.0, "SHORT") is True
    assert _czi_cyan_for_direction(10.0, "SHORT") is False


# ── Flag ON: full-spec case fires ────────────────────────────────────────

@patch.dict(os.environ, {"ZLR_SPEC_V2": "1", "ZLR_CCI_MIN": "100"})
def test_full_spec_fires_with_v2():
    """A ZLR that satisfies all spec conditions fires even with v2 ON.

    if reverted → RED because: this test uses bars crafted for the v2 checks;
    reverting the gate doesn't break this test, but the rejection tests below do.
    """
    bars = _full_spec_bars_long()
    result = detect(bars)
    assert result.detected, "Full-spec ZLR must fire with v2 ON: %s" % (result.details,)
    assert result.direction == "LONG"


# ── Flag ON: spec violations blocked ────────────────────────────────────

@patch.dict(os.environ, {"ZLR_SPEC_V2": "1", "ZLR_CCI_MIN": "100"})
def test_no_swi_blocked_with_v2():
    """SWI red everywhere → blocked by S1.3 (no SWI yellow/green).

    if reverted → RED because: removing the v2 gate lets this fire (CCI geometry is valid).
    """
    bars = _no_swi_bars_long()
    result = detect(bars)
    assert not result.detected, "No-SWI ZLR must be blocked by v2"
    assert "S1.3" in result.details.get("reject_reason", "")


@patch.dict(os.environ, {"ZLR_SPEC_V2": "1", "ZLR_CCI_MIN": "100"})
def test_high_cci_entry_blocked_with_v2():
    """Entry CCI=140 (>120) → blocked by S3.7.

    if reverted → RED because: without v2, CCI<200 passes (the old gate).
    """
    bars = _high_cci_entry_bars_long()
    result = detect(bars)
    assert not result.detected, "CCI-140 entry must be blocked by v2 (<=120)"
    assert "S3.7" in result.details.get("reject_reason", "")


@patch.dict(os.environ, {"ZLR_SPEC_V2": "1", "ZLR_CCI_MIN": "100"})
def test_weak_bounce_blocked_with_v2():
    """CCI diff only 3 (<15) → blocked by S3.3 (not sharp enough).

    if reverted → RED because: without v2, any current>prev passes.
    """
    bars = _weak_bounce_bars_long()
    result = detect(bars)
    assert not result.detected, "Weak-bounce ZLR must be blocked by v2 (diff<15)"
    assert "S3.3" in result.details.get("reject_reason", "")


# ── Flag OFF → identical to today (anti-tautology) ──────────────────────

@patch.dict(os.environ, {"ZLR_SPEC_V2": "0", "ZLR_CCI_MIN": "100"})
def test_flag_off_no_swi_fires():
    """With v2 OFF, a no-SWI setup fires (today's CCI-only behavior).

    if reverted → RED because: the flag-ON test above blocks this case,
    proving the flag gates the spec enforcement.
    """
    bars = _no_swi_bars_long()
    result = detect(bars)
    assert result.detected, "Flag OFF: CCI-geometry ZLR must fire regardless of SWI"


@patch.dict(os.environ, {"ZLR_SPEC_V2": "0", "ZLR_CCI_MIN": "100"})
def test_flag_off_high_cci_fires():
    """With v2 OFF, CCI=140 entry fires (today allows <200)."""
    bars = _high_cci_entry_bars_long()
    result = detect(bars)
    assert result.detected, "Flag OFF: CCI-140 entry must fire (old gate is <200)"
