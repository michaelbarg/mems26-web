"""T7 — anti-tautology: each CONT detector picks the correct LONG/SHORT side.

If a detector's direction branch is inverted, these fail.
Negative cases: wrong-side trend paint → no fire (or opposite not claimed).
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from backend.v9.systems.woodies.schemas import WoodiesBar


def _bar(**kw) -> WoodiesBar:
    close = kw.pop("close", 7500.0)
    return WoodiesBar(
        ts=kw.pop("ts", 1000.0),
        open=kw.pop("open", close - 1),
        high=kw.pop("high", close + 5),
        low=kw.pop("low", close - 5),
        close=close,
        volume=kw.pop("volume", 1000),
        cci_14=kw.pop("cci", 50.0),
        cci_6_tcci=kw.pop("tcci", 40.0),
        ema_34=kw.pop("ema", close - 10),
        lsma_value=kw.pop("lsma", close),
        swi_value=kw.pop("swi", 30.0),
        czi_value=kw.pop("czi", 50.0),
        trend_state=kw.pop("trend", "BLUE"),
        predictor_next_cci=kw.pop("pred", 50.0),
        hfe_detected=False,
        hfe_direction="NONE",
        hfe_extreme_bars_ago=0,
    )


def _tt_long_bars():
    # need ≥3 bars; BLUE; TCCI touch CCI from above then bounce; CCI range≥50 (AP flat)
    b0 = _bar(ts=1, cci=40, tcci=100, trend="BLUE", close=7500)  # was above
    b1 = _bar(ts=2, cci=70, tcci=72, trend="BLUE", close=7501)   # touch
    b2 = _bar(ts=3, cci=100, tcci=120, trend="BLUE", close=7502)  # bounce; range 60
    return [b0, b1, b2]


def _tt_short_bars():
    b0 = _bar(ts=1, cci=-40, tcci=-100, trend="RED", close=7500)
    b1 = _bar(ts=2, cci=-70, tcci=-72, trend="RED", close=7499)
    b2 = _bar(ts=3, cci=-100, tcci=-120, trend="RED", close=7498)
    return [b0, b1, b2]


def _gb100_long_bars():
    # BLUE, fresh +100 cross; CCI range≥50
    return [
        _bar(ts=1, cci=40, trend="BLUE", close=7500),
        _bar(ts=2, cci=100, trend="BLUE", close=7501),
        _bar(ts=3, cci=130, trend="BLUE", close=7502),
    ]


def _gb100_short_bars():
    return [
        _bar(ts=1, cci=-40, trend="RED", close=7500),
        _bar(ts=2, cci=-100, trend="RED", close=7499),
        _bar(ts=3, cci=-130, trend="RED", close=7498),
    ]


def test_tt_long_not_short():
    from backend.v9.systems.woodies.patterns.tt import detect
    with patch.dict(os.environ, {"ZLR_SPEC_V2": "0"}, clear=False):
        r = detect(_tt_long_bars())
    assert r is not None and r.detected
    assert r.direction == "LONG"


def test_tt_short_not_long():
    from backend.v9.systems.woodies.patterns.tt import detect
    r = detect(_tt_short_bars())
    assert r is not None and r.detected
    assert r.direction == "SHORT"


def test_tt_no_fire_on_gray():
    from backend.v9.systems.woodies.patterns.tt import detect
    bars = _tt_long_bars()
    for b in bars:
        b.trend_state = "GRAY"
    r = detect(bars)
    assert r is None or not r.detected


def test_gb100_long_not_short():
    from backend.v9.systems.woodies.patterns.gb100 import detect
    r = detect(_gb100_long_bars())
    assert r is not None and r.detected
    assert r.direction == "LONG"


def test_gb100_short_not_long():
    from backend.v9.systems.woodies.patterns.gb100 import detect
    r = detect(_gb100_short_bars())
    assert r is not None and r.detected
    assert r.direction == "SHORT"


def test_gb100_no_fire_wrong_paint():
    """BLUE paint but bearish cross geometry → must not claim LONG."""
    from backend.v9.systems.woodies.patterns.gb100 import detect
    bars = _gb100_short_bars()
    for b in bars:
        b.trend_state = "BLUE"
    r = detect(bars)
    assert r is None or not r.detected or r.direction != "LONG"


def test_zlr_spec_v2_long_direction():
    """Reuse the proven full-spec LONG fixture; assert direction == LONG (not SHORT)."""
    from tests.v9.regression.test_zlr_spec_v2 import _full_spec_bars_long
    from backend.v9.systems.woodies.patterns.zlr import detect
    with patch.dict(os.environ, {"ZLR_SPEC_V2": "1"}, clear=False):
        r = detect(_full_spec_bars_long())
    assert r is not None and r.detected
    assert r.direction == "LONG"


def test_zlr_no_fire_when_red_paint_on_long_geometry():
    from tests.v9.regression.test_zlr_spec_v2 import _full_spec_bars_long
    from backend.v9.systems.woodies.patterns.zlr import detect
    bars = _full_spec_bars_long()
    for b in bars:
        b.trend_state = "RED"
    with patch.dict(os.environ, {"ZLR_SPEC_V2": "1"}, clear=False):
        r = detect(bars)
    # Must not fire LONG under RED stairs
    assert r is None or not r.detected or r.direction != "LONG"
