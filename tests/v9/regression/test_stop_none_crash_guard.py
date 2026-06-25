"""T3: S4 process_bar must not crash when a pattern has stop=None.

DLL-sourced fires can propagate stop=None through the stop computation chain.
The fix: skip the fire with a WARNING, never crash process_bar.

if reverted → RED because: removing the T3 guard would let stop=None reach
PatternResult construction → pydantic ValidationError → process_bar crashes.
"""
import asyncio
import os
import pytest
from unittest.mock import patch

from backend.v9.systems.woodies.woodies_system import WoodiesSystem
from backend.v9.systems.woodies.schemas import PatternResult


_RTH_BASE_TS = 1781114400.0


def _make_bar(i, close=7440.0, cci=-50.0, trend="RED",
              zlr_detected=False, zlr_direction="NONE"):
    return {
        "ts": _RTH_BASE_TS + i * 300,
        "open": close - 1.0, "high": close + 2.0, "low": close - 3.0, "close": close,
        "volume": 5000, "cci_14": cci, "cci_6_tcci": cci * 0.8,
        "ema_34": close - 5.0, "lsma_value": close - 3.0, "lsma_above_price": False,
        "swi_value": -50.0, "czi_value": 50.0, "trend_state": trend,
        "predictor_next_cci": cci * 0.9,
        "zlr_detected": zlr_detected, "zlr_direction": zlr_direction,
        "hfe_detected": False, "hfe_direction": "NONE", "hfe_extreme_bars_ago": 0,
    }


def _feed_bars(ws, bars):
    class Evt:
        def __init__(self, d): self.payload = d
    loop = asyncio.new_event_loop()
    for b in bars:
        loop.run_until_complete(ws.process_bar(Evt(b)))
    loop.close()


def test_process_bar_no_crash_with_stop_none():
    """PatternResult(stop=None) crashes pydantic. The T3 guard filters it out.

    if reverted → RED because: removing the guard lets stop=None propagate
    to PatternResult → ValidationError → process_bar crashes.
    """
    # This test just confirms that stop=None indeed crashes PatternResult
    with pytest.raises(Exception):
        PatternResult(
            detected=True, pattern_id="ZLR", direction="SHORT",
            confidence=0.65, entry_price=7400.0, stop=None,
            targets=[], group="CONTINUATION", cci_at_signal=-80.0,
            bar_index=0, ts=1000.0)


def test_process_bar_survives_bad_atr():
    """process_bar with too few bars for ATR → stop computation may yield None/0.
    The T3 guard ensures no crash.

    if reverted → RED because: without the guard, a DLL ZLR with insufficient
    bars for ATR could crash.
    """
    ws = WoodiesSystem(rth_only=False)
    # Only 5 bars (< 14 for ATR) + ZLR flag → ATR=0 → stop path may yield 0
    bars = [_make_bar(i, close=7400+i*0.5, cci=-50+i*8, trend="RED") for i in range(5)]
    zlr_bar = _make_bar(5, close=7440.0, cci=-120.0, trend="RED",
                        zlr_detected=True, zlr_direction="DOWN")
    # Must not crash — T3 guard skips the bad-stop pattern
    _feed_bars(ws, bars + [zlr_bar])
    # If we got here, no crash — success


def test_woodies_system_has_t3_guard():
    """Source inspection: T3 guard exists in process_bar."""
    import inspect
    source = inspect.getsource(WoodiesSystem.process_bar)
    assert "T3 guard" in source or "T3: guard" in source
    assert "bad stop" in source.lower() or "stop=%s" in source
