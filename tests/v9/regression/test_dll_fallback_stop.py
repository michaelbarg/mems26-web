"""Bug #1: DLL-flagged ZLR/HFE must compute real stop via process_bar.

Feeds a bar with zlr_detected=True through the REAL WoodiesSystem.process_bar.
Verifies: no crash, ZLR in active_patterns, stop>0, R:R sanity.

RED-on-revert: reverting woodies_system.py DLL-fallback to stop=None
→ PatternResult ValidationError → process_bar crashes → no active_patterns.
"""
import asyncio
import os
import pydantic
import pytest
from unittest.mock import patch
from backend.v9.systems.woodies.woodies_system import WoodiesSystem
from backend.v9.systems.woodies.schemas import PatternResult


# RTH timestamp: 2026-06-09 10:00 ET = 14:00 UTC
_RTH_BASE_TS = 1781114400.0  # epoch for 2026-06-09 14:00:00 UTC


def _make_bar(i, close=7440.0, cci=-50.0, trend="RED",
              zlr_detected=False, zlr_direction="NONE",
              hfe_detected=False, hfe_direction="NONE"):
    return {
        "ts": _RTH_BASE_TS + i * 300,
        "open": close - 1.0, "high": close + 2.0, "low": close - 3.0, "close": close,
        "volume": 5000, "cci_14": cci, "cci_6_tcci": cci * 0.8,
        "ema_34": close - 5.0, "lsma_value": close - 3.0, "lsma_above_price": False,
        "swi_value": -50.0, "czi_value": 50.0, "trend_state": trend,
        "predictor_next_cci": cci * 0.9,
        "zlr_detected": zlr_detected, "zlr_direction": zlr_direction,
        "hfe_detected": hfe_detected, "hfe_direction": hfe_direction,
        "hfe_extreme_bars_ago": 3 if hfe_detected else 0,
        "proj_hi": close + 100, "proj_lo": close - 100,
    }


def _feed_bars(ws, bars):
    class Evt:
        def __init__(self, d): self.payload = d
    loop = asyncio.new_event_loop()
    for b in bars:
        loop.run_until_complete(ws.process_bar(Evt(b)))
    loop.close()


def test_dll_zlr_through_process_bar():
    """Feed zlr_detected=True through real process_bar → no crash, ZLR with stop>0."""
    ws = WoodiesSystem(rth_only=False)

    # 20 bars of history (ATR needs 14+)
    history = [_make_bar(i, close=7400+i*0.5, cci=-50+i*5) for i in range(20)]
    # ZLR bar
    zlr = _make_bar(20, close=7440.0, cci=-120.0, trend="RED",
                    zlr_detected=True, zlr_direction="DOWN")
    _feed_bars(ws, history + [zlr])

    patterns = ws._active_patterns
    zlr_pats = [p for p in patterns if p.pattern_id == "ZLR"]
    assert len(zlr_pats) >= 1, \
        f"Expected ZLR in active_patterns, got: {[p.pattern_id for p in patterns]}"

    z = zlr_pats[0]
    assert z.stop is not None, "stop must not be None"
    assert z.stop > 0, f"stop must be > 0, got {z.stop}"
    assert z.stop != 0.0, "stop=0.0 is wrong (R:R garbage)"
    assert z.direction == "SHORT"
    assert z.stop > z.entry_price, \
        f"SHORT stop ({z.stop}) must be above entry ({z.entry_price})"


@patch.dict(os.environ, {"HFE_DISABLED": "0"})
def test_dll_hfe_through_process_bar():
    """Feed hfe_detected=True through real process_bar → stop>0 (HFE enabled)."""
    ws = WoodiesSystem(rth_only=False)

    history = [_make_bar(i, close=7400+i*0.5, cci=50+i*5, trend="BLUE") for i in range(20)]
    hfe = _make_bar(20, close=7440.0, cci=210.0, trend="BLUE",
                    hfe_detected=True, hfe_direction="DOWN")
    _feed_bars(ws, history + [hfe])

    patterns = ws._active_patterns
    hfe_pats = [p for p in patterns if p.pattern_id == "HFE"]
    assert len(hfe_pats) >= 1, \
        f"Expected HFE in active_patterns, got: {[p.pattern_id for p in patterns]}"

    h = hfe_pats[0]
    assert h.stop is not None
    assert h.stop > 0


@patch.dict(os.environ, {"HFE_DISABLED": "1"})
def test_dll_hfe_disabled_no_fire():
    """With HFE_DISABLED=1, hfe_detected=True bar produces NO HFE fire.

    if reverted → RED because: removing the HFE_DISABLED filter would let HFE through.
    """
    ws = WoodiesSystem(rth_only=False)

    history = [_make_bar(i, close=7400+i*0.5, cci=50+i*5, trend="BLUE") for i in range(20)]
    hfe = _make_bar(20, close=7440.0, cci=210.0, trend="BLUE",
                    hfe_detected=True, hfe_direction="DOWN")
    _feed_bars(ws, history + [hfe])

    patterns = ws._active_patterns
    hfe_pats = [p for p in patterns if p.pattern_id == "HFE"]
    assert len(hfe_pats) == 0, \
        f"HFE_DISABLED=1 but HFE still fired: {[p.pattern_id for p in patterns]}"


def test_dll_zlr_stop_none_crashes():
    """Prove stop=None crashes PatternResult — the bug we fixed."""
    with pytest.raises(pydantic.ValidationError):
        PatternResult(
            detected=True, pattern_id="ZLR", direction="SHORT",
            confidence=0.65, raw_confidence=0.65,
            entry_price=7400.0, stop=None, targets=[],
            group="CONTINUATION", cci_at_signal=-80.0,
            bar_index=0, ts=1781000000.0,
        )
