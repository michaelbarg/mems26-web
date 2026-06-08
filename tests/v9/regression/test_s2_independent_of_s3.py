"""S2 is INDEPENDENT of S3 (footprint COT/AMT) by default — Michael 2026-06-08.

S3 (footprint) is muted/broken at this stage (S3_MUTE / I-11). S2 must fire on
price-geometry + volume alone, NOT gated on footprint COT/AMT order-flow. The
order-flow confirmation is restorable ONLY via env S2_REQUIRE_COT_AMT=1.

Litmus: if the COT/AMT hard-dependency is restored as default → these go RED.
Tests the REAL _detect_reactive (Reactive LONG geometry, COT/AMT unavailable).
"""
import os

import pytest

from backend.v9.systems.five_min.five_min_system import FiveMinSystem, MIN_BARS_REQUIRED


def _reactive_long_bars():
    """3 quiet lookback bars + a valid Reactive-LONG 4-bar setup (7 total)."""
    pad = [{"o": 5250, "h": 5251, "l": 5249, "c": 5250, "v": 50} for _ in range(3)]
    setup = [
        {"o": 5250, "h": 5250, "l": 5247, "c": 5247.5, "v": 1000},   # b1 sellers
        {"o": 5248, "h": 5248, "l": 5247, "c": 5247.75, "v": 80},    # b2 90% vol drop
        {"o": 5247.25, "h": 5249, "l": 5247.25, "c": 5248.75, "v": 800},  # b3 buyers
        {"o": 5248.5, "h": 5250, "l": 5248.5, "c": 5249.75, "v": 700},    # b4 confirm
    ]
    return pad + setup


def _sys_no_footprint():
    """FiveMinSystem with footprint (S3) fully unavailable — COT/AMT/belly None."""
    s = FiveMinSystem()
    s._get_cot_from_footprint = lambda: None
    s._get_amt_from_footprint = lambda: None
    s._get_belly_from_footprint = lambda: None
    s._get_belly_ratio_from_footprint = lambda d: None
    s._poc_vol_rising = lambda b: False
    s._poc_vol_falling = lambda b: False
    return s


def test_s2_fires_without_footprint_when_independent_default(monkeypatch):
    """Default (flag unset): Reactive fires on geometry alone, COT/AMT=None."""
    monkeypatch.delenv("S2_REQUIRE_COT_AMT", raising=False)
    monkeypatch.delenv("S2_VSA_VOLUME", raising=False)
    direction, conf, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars())
    assert direction == "LONG", (
        "S2 must fire independent of S3: with COT/AMT unavailable and the gate "
        "disabled by default, a valid Reactive-LONG geometry should still fire"
    )


def test_s2_requires_cot_amt_only_when_flag_set(monkeypatch):
    """Flag=1 restores the S3 order-flow dependency: COT/AMT=None → no fire."""
    monkeypatch.setenv("S2_REQUIRE_COT_AMT", "1")
    monkeypatch.delenv("S2_VSA_VOLUME", raising=False)
    direction, conf, _ = _sys_no_footprint()._detect_reactive(_reactive_long_bars())
    assert direction is None, (
        "With S2_REQUIRE_COT_AMT=1 and COT/AMT unavailable, the guard must "
        "block the fire (original S3-dependent behavior)"
    )
