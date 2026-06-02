"""D-RVX: VSA volume gate — S2 Reactive fires with flag ON, blocked with flag OFF.

Calls PRODUCTION FiveMinSystem._detect_reactive with real bar data.
Asserts on the consumer (returned direction), not on internal variables.

if reverted → RED because without the VSA gate, the 90% threshold
  blocks all bars (0 fires ever) even with the flag ON.
"""

import pytest
import backend.v9.shared.atr as atr_mod


def _set_flag(monkeypatch, on: bool):
    monkeypatch.setattr(atr_mod, "S2_VSA_VOLUME", on)


def _make_system():
    from backend.v9.systems.five_min.five_min_system import FiveMinSystem
    fs = FiveMinSystem.__new__(FiveMinSystem)
    # Minimal init for _detect_reactive
    fs._footprint_system = None
    fs._current_atr_5m = 2.0
    return fs


def _make_bars():
    """7 bars: 3 lookback + 4 pattern bars.

    Bar 1 (sellers): bearish close, high volume (800)
    Bar 2 (exhaustion): low volume (150) — 81% drop (passes VSA, fails 90%)
    Bar 3 (buyers): bullish close
    Bar 4 (confirm): bullish close above bar 3 high
    Lookback: moderate volume (200-300, all < 0.6 * 800 = 480)
    """
    return [
        # lookback bars (3)
        {"o": 100, "h": 101, "l": 99, "c": 100.5, "v": 250},
        {"o": 100.5, "h": 101, "l": 99.5, "c": 100, "v": 300},
        {"o": 100, "h": 101, "l": 99, "c": 100.5, "v": 200},
        # bar 1: sellers (bearish, high vol)
        {"o": 101, "h": 101.5, "l": 99, "c": 99.5, "v": 800},
        # bar 2: exhaustion (low vol — 150/800 = 0.1875 → fails 0.10 but passes VSA)
        {"o": 99.5, "h": 100, "l": 99, "c": 99.5, "v": 150},
        # bar 3: buyers (bullish)
        {"o": 99.5, "h": 101, "l": 99, "c": 100.5, "v": 500},
        # bar 4: confirm (bullish, close above bar 3 high)
        {"o": 100.5, "h": 102, "l": 100, "c": 101.5, "v": 600},
    ]


def test_vsa_flag_on_fires(monkeypatch):
    """D-RVX: Flag ON + VSA-qualifying bars → S2 fires LONG.

    if reverted → RED because without VSA gate, b2_drop uses 0.10 threshold
      and 150/800=0.1875 > 0.10 → b2_drop=False → no fire.
    """
    _set_flag(monkeypatch, True)
    fs = _make_system()
    # Mock COT/AMT so the COT>AMT gate passes
    fs._get_cot_from_footprint = lambda: 100.0
    fs._get_amt_from_footprint = lambda: 50.0
    fs._get_belly_from_footprint = lambda: True
    fs._get_belly_ratio_from_footprint = lambda d: 2.0
    fs._poc_vol_rising = lambda bars: True

    direction, conf, info = fs._detect_reactive(_make_bars())
    assert direction == "LONG", (
        f"VSA flag ON should fire LONG. Got direction={direction}, info={info}"
    )


def test_legacy_flag_off_blocked(monkeypatch):
    """D-RVX: Flag OFF + same bars → S2 does NOT fire (90% gate blocks).

    This is the golden test — proves legacy behavior unchanged.
    """
    _set_flag(monkeypatch, False)
    fs = _make_system()
    fs._get_cot_from_footprint = lambda: 100.0
    fs._get_amt_from_footprint = lambda: 50.0
    fs._get_belly_from_footprint = lambda: True
    fs._get_belly_ratio_from_footprint = lambda d: 2.0
    fs._poc_vol_rising = lambda bars: True

    direction, conf, info = fs._detect_reactive(_make_bars())
    assert direction is None, (
        f"Legacy 90% gate should block. Got direction={direction}"
    )
