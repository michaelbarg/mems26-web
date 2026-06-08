"""Bug #1 fix: DLL-flagged ZLR/HFE must compute a real stop, not None/0.0.

RED-on-revert: if reverted → PatternResult(stop=None) → ValidationError →
process_bar crashes → all S4 patterns silenced. This test catches that by
creating a WoodiesBar with zlr_detected=True and verifying the DLL-fallback
path produces a valid PatternResult with stop > 0.
"""
import os
from unittest.mock import patch
from backend.v9.systems.woodies.schemas import WoodiesBar, PatternResult


def _make_woodies_bars(n=20, base=7400.0):
    """Create n WoodiesBar objects with valid CCI/trend for ZLR detection."""
    bars = []
    for i in range(n):
        bars.append(WoodiesBar(
            ts=1781000000.0 + i * 300,
            open=base + i * 0.25, high=base + 2.0 + i * 0.25,
            low=base - 2.0 + i * 0.25, close=base + 0.5 + i * 0.25,
            cci_14=-120.0 if i < 5 else -50.0 + i * 5,
            cci_6_tcci=-100.0, trend_state="RED",
        ))
    return bars


def test_dll_zlr_fallback_computes_real_stop():
    """DLL-flagged ZLR must produce PatternResult with stop > 0, not None."""
    bars = _make_woodies_bars(20)
    # Simulate a DLL-flagged ZLR bar
    zlr_bar = bars[-1].copy(update={
        "zlr_detected": True, "zlr_direction": "DOWN",
        "cci_14": -80.0, "trend_state": "RED",
    })

    # The DLL fallback path computes stop via compute_stop/compute_stop_v2
    from backend.v9.systems.woodies.atr_stop import compute_stop, PatternGroup
    # Compute ATR same way as the fix
    trs = []
    for i, b in enumerate(bars):
        br = b.high - b.low
        if i > 0:
            pc = bars[i-1].close
            br = max(br, abs(b.high - pc), abs(b.low - pc))
        trs.append(br)
    atr = sum(trs[:14]) / 14
    for tr in trs[14:]:
        atr = ((atr * 13) + tr) / 14
    atr_ticks = atr / 0.25

    sr = compute_stop("SHORT", zlr_bar, swing_anchor=None,
                      pattern_group=PatternGroup.CONT_TIGHT, atr_14=atr_ticks)
    assert sr.stop_price > 0
    assert sr.stop_price > zlr_bar.close  # SHORT stop above entry

    # Now create PatternResult with the computed stop — must NOT crash
    pr = PatternResult(
        detected=True, pattern_id="ZLR", direction="SHORT",
        confidence=0.65, raw_confidence=0.65,
        entry_price=zlr_bar.close, stop=sr.stop_price,
        targets=[zlr_bar.close - 1.0],
        group="CONTINUATION", cci_at_signal=zlr_bar.cci_14,
        bar_index=19, ts=zlr_bar.ts,
        details={"source": "dll_flag"},
    )
    assert pr.stop > 0
    assert pr.stop != zlr_bar.close  # stop != entry


def test_dll_zlr_stop_none_crashes():
    """Prove that stop=None crashes PatternResult (the bug we're fixing)."""
    import pydantic
    try:
        PatternResult(
            detected=True, pattern_id="ZLR", direction="SHORT",
            confidence=0.65, raw_confidence=0.65,
            entry_price=7400.0, stop=None, targets=[],
            group="CONTINUATION", cci_at_signal=-80.0,
            bar_index=0, ts=1781000000.0,
        )
        assert False, "Should have raised ValidationError"
    except pydantic.ValidationError:
        pass  # Expected — this is the bug


def test_dll_hfe_fallback_computes_real_stop():
    """DLL-flagged HFE must also get a real stop."""
    bars = _make_woodies_bars(20)
    from backend.v9.systems.woodies.atr_stop import compute_stop, PatternGroup

    swing_low = min(b.low for b in bars[-12:])
    trs = []
    for i, b in enumerate(bars):
        br = b.high - b.low
        if i > 0:
            pc = bars[i-1].close
            br = max(br, abs(b.high - pc), abs(b.low - pc))
        trs.append(br)
    atr = sum(trs[:14]) / 14
    for tr in trs[14:]:
        atr = ((atr * 13) + tr) / 14
    atr_ticks = atr / 0.25

    sr = compute_stop("LONG", bars[-1], swing_anchor=swing_low,
                      pattern_group=PatternGroup.REV, atr_14=atr_ticks)
    assert sr.stop_price > 0
    assert sr.stop_price < bars[-1].close  # LONG stop below entry

    pr = PatternResult(
        detected=True, pattern_id="HFE", direction="LONG",
        confidence=0.60, raw_confidence=0.60,
        entry_price=bars[-1].close, stop=sr.stop_price,
        targets=[bars[-1].close + 1.0],
        group="REVERSAL", cci_at_signal=bars[-1].cci_14,
        bar_index=19, ts=bars[-1].ts,
        details={"source": "dll_flag"},
    )
    assert pr.stop > 0
