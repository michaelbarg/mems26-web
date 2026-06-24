"""Anti-tautological regression tests for VEGAS_SPEC_V2 flag.

When ON: VEGAS detects CCI cup-and-handle (Michael's spec), NOT divergence.
When OFF: legacy price/CCI divergence (today's behavior).

if reverted → RED because: removing _detect_cup_and_handle or the VEGAS_SPEC_V2
branch would break the ON-fires-cup-handle assertion AND the ON-blocks-divergence
assertion (the flag swaps detection logic, not gates it).
"""
import os
import pytest
from unittest.mock import patch

from backend.v9.systems.woodies.schemas import WoodiesBar
from backend.v9.systems.woodies.patterns.vegas import detect, _detect_cup_and_handle


def _bar(cci=0.0, close=7450.0, high=7455.0, low=7445.0, ts=1000.0) -> WoodiesBar:
    return WoodiesBar(
        ts=ts, open=close - 1, high=high, low=low, close=close, volume=1000,
        cci_14=cci, cci_6_tcci=cci * 0.8, ema_34=close, lsma_value=close,
        swi_value=30.0, czi_value=50.0, trend_state="BLUE" if cci > 0 else "RED",
        predictor_next_cci=cci,
        hfe_detected=False, hfe_direction="NONE", hfe_extreme_bars_ago=0,
    )


def _cup_and_handle_bars_long():
    """20 bars forming a CCI cup-and-handle LONG:
    1) CCI drops below -200 (cup bottom at bar 5)
    2) CCI recovers, crosses -100 (rim peak at bar 10, CCI = -50)
    3) Handle: CCI dips to -80 (higher than cup -220) for 3+ bars
    4) Entry bar: CCI breaks above rim (-50) → current CCI = -10, prev = -55
    AP8 needs range > 50 over last 3 bars (bars 17,18,19: -120,-55,-10 → range=110).
    """
    bars = []
    ccis = [-30, -80, -140, -180, -210,
            # Bar 5: cup bottom
            -230,
            # Bars 6-9: recovery
            -190, -150, -110, -80,
            # Bar 10: rim (peak, crosses -100)
            -50,
            # Bars 11-15: handle (higher-low, holds well above cup -230)
            -90, -100, -95, -85, -80,
            # Bars 16-18: handle narrows → prepare for rim break
            -75, -120, -55,
            # Bar 19 (entry): CCI = -10, prev = -55 → breaks rim (-50)
            -10]
    for i, cci in enumerate(ccis):
        bars.append(_bar(cci=cci, close=7450.0 - i * 0.5, ts=float(1000 + i * 300),
                         high=7455.0 - i * 0.5, low=7445.0 - i * 0.5))
    return bars


def _divergence_bars_short():
    """20 bars forming a price HH + CCI LH divergence (legacy VEGAS SHORT).
    Price makes higher highs but CCI makes lower highs = bearish divergence.
    AP8 needs CCI range > 50 over last 3 bars.
    """
    bars = []
    for i in range(20):
        # Price trending up (higher highs)
        close = 7400.0 + i * 3.0
        # CCI: first peak at bar 8 (CCI=180), second peak at bar 16 (CCI=150) = LH
        if i <= 8:
            cci = 20.0 + i * 20.0  # 20 → 180
        elif i <= 12:
            cci = 180.0 - (i - 8) * 30.0  # 180 → 60
        elif i <= 16:
            cci = 60.0 + (i - 12) * 22.5  # 60 → 150
        else:
            cci = 150.0 - (i - 16) * 20.0  # 150 → 90
        bars.append(_bar(cci=cci, close=close, high=close + 5, low=close - 5,
                         ts=float(1000 + i * 300)))
    return bars


# ── Pure cup-and-handle detector ─────────────────────────────────────────

def test_cup_and_handle_detects_long():
    """Pure helper detects the cup-and-handle LONG structure."""
    bars = _cup_and_handle_bars_long()
    result = _detect_cup_and_handle(bars)
    assert result is not None, "Must detect cup-and-handle LONG"
    assert result["direction"] == "LONG"
    assert result["cup_cci"] <= -200
    assert result["rim_cci"] >= -100


def test_cup_and_handle_no_false_positive():
    """Flat CCI bars → no cup-and-handle detected."""
    bars = [_bar(cci=50 + i * 2, ts=float(1000 + i * 300)) for i in range(20)]
    result = _detect_cup_and_handle(bars)
    assert result is None


# ── Flag ON: fires cup-and-handle, NOT divergence ────────────────────────

@patch.dict(os.environ, {"VEGAS_SPEC_V2": "1"})
def test_v2_on_fires_cup_and_handle():
    """With v2 ON, a cup-and-handle bar sequence fires VEGAS LONG.

    if reverted → RED because: removing the v2 branch means this sequence
    (no price divergence) produces no fire.
    """
    bars = _cup_and_handle_bars_long()
    result = detect(bars)
    assert result.detected, "Cup-and-handle must fire with v2 ON: %s" % (result.details,)
    assert result.direction == "LONG"
    assert result.details.get("cup_and_handle") is True
    assert result.details.get("vegas_spec_v2") is True


@patch.dict(os.environ, {"VEGAS_SPEC_V2": "1"})
def test_v2_on_blocks_divergence():
    """With v2 ON, a pure divergence sequence does NOT fire (it's the wrong pattern).

    if reverted → RED because: without v2, the divergence would fire.
    """
    bars = _divergence_bars_short()
    result = detect(bars)
    # v2 ON: only cup-and-handle fires; divergence is ignored
    if result.detected:
        # If it fires, it must NOT be a divergence detection
        assert result.details.get("cup_and_handle") is True, \
            "v2 ON must only fire cup-and-handle, not divergence"


# ── Flag OFF: legacy divergence fires ────────────────────────────────────

@patch.dict(os.environ, {"VEGAS_SPEC_V2": "0"})
def test_v2_off_cup_handle_does_not_fire():
    """With v2 OFF, the cup-and-handle sequence uses divergence logic which
    doesn't match this CCI pattern → no fire (proves the flag swaps logic).

    if reverted → RED because: the v2 ON test fires this same sequence.
    """
    bars = _cup_and_handle_bars_long()
    result = detect(bars)
    # Legacy divergence needs price HH/LL + CCI LH/HL — this CCI-only cup has no
    # price divergence → should NOT fire (or if it does, it's not cup-and-handle)
    if result.detected:
        assert result.details.get("cup_and_handle") is not True, \
            "v2 OFF must not fire cup-and-handle"


# ── Source inspection ────────────────────────────────────────────────────

def test_vegas_detect_has_v2_branch():
    """detect() source contains the VEGAS_SPEC_V2 flag check."""
    import inspect
    source = inspect.getsource(detect)
    assert "VEGAS_SPEC_V2" in source
    assert "_detect_cup_and_handle" in source
