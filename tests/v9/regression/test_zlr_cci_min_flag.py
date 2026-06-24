"""ZLR_CCI_MIN flag — require a stronger CCI extreme for ZLR (Liran spec ±200).

Default (unset) = 100 = current behavior. Set ZLR_CCI_MIN=200 → a ZLR whose
extreme only reached ±150 is rejected. Anti-tautological: reverting the threshold
edit (back to hardcoded ±100) makes test_zlr_blocked_at_200 fire → RED.
"""
import pytest

from backend.v9.systems.woodies.patterns.zlr import detect, _zlr_cci_min
from backend.v9.systems.woodies.schemas import WoodiesBar

# CCI sequence: a DOWN move whose extreme reaches only -150 (between -100 and -200),
# then pulls back toward zero, then the last bar drops (reject) → a ZLR DOWN.
_CCI_PEAK_150_DOWN = [0, 50, 30, 10, -10, -30, -20, 40, 60, -150, -70, -40, -30, -90]


def _bars(cci_list):
    bars, px = [], 7410.0
    for k, c in enumerate(cci_list):
        px -= 1.0
        bars.append(WoodiesBar(ts=float(k), open=px + 0.5, high=px + 2.0,
                               low=px - 2.0, close=px, volume=100, cci_14=c))
    return bars


def test_zlr_cci_min_default(monkeypatch):
    monkeypatch.delenv("ZLR_CCI_MIN", raising=False)
    assert _zlr_cci_min() == 100.0


def test_zlr_cci_min_200(monkeypatch):
    monkeypatch.setenv("ZLR_CCI_MIN", "200")
    assert _zlr_cci_min() == 200.0


def test_zlr_cci_min_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("ZLR_CCI_MIN", "junk")
    assert _zlr_cci_min() == 100.0


def test_zlr_fires_at_default_threshold(monkeypatch):
    # extreme -150 passes the default ±100 gate → ZLR detected.
    # ZLR_SPEC_V2=0: this test checks CCI_MIN only, not the spec-v2 gates.
    monkeypatch.delenv("ZLR_CCI_MIN", raising=False)
    monkeypatch.setenv("ZLR_SPEC_V2", "0")
    r = detect(_bars(_CCI_PEAK_150_DOWN))
    assert r.detected


def test_zlr_blocked_at_200(monkeypatch):
    # extreme only -150, spec needs ±200 → rejected.  reverting the edit → RED
    monkeypatch.setenv("ZLR_CCI_MIN", "200")
    monkeypatch.setenv("ZLR_SPEC_V2", "0")
    r = detect(_bars(_CCI_PEAK_150_DOWN))
    assert not r.detected
