"""P1-7 — DD neck-refill invalidation (Dalton p.27, doctrine contradiction-5).

A Double-Distribution day is defined by single prints separating two value
areas. When later bars DOUBLE-PRINT that neck (>=2 recent closes inside the
zone), the second distribution is rejected — "something has changed" — and
the Trend_DD classification must fall.

Layers: dd_features exposes neck_lo/neck_hi + neck_refilled(); the classifier
drops Trend_DD under S1_DD_INVALIDATION_V1. Anti-tautological: flag OFF →
the same refilled day still classifies Trend_DD (old behavior).
"""
from backend.v9.systems.day_type.dd_features import (
    detect_double_distribution, neck_refilled,
)
from backend.v9.systems.day_type.daytype_classifier import classify, load_plan


def _bar(px, v=100, spread=1.0):
    return {"o": px, "h": px + spread, "l": px - spread, "c": px, "v": v}


def _dd_day():
    """Narrow IB at 7500, drive up through a thin neck to a 2nd distribution at 7530."""
    bars = []
    for _ in range(14):
        bars.append(_bar(7500, v=200))          # 1st distribution (heavy)
    for px in (7508, 7516, 7524):
        bars.append(_bar(px, v=15, spread=0.5))  # the neck — single prints
    for _ in range(14):
        bars.append(_bar(7530, v=190))          # 2nd distribution — substantial (>=45% of 1st)
    bars.append(_bar(7532, v=180))              # close at extreme
    return bars


def test_zone_exposed_and_dd_detected():
    d = detect_double_distribution(_dd_day(), ib_width=5.0, ib_median=10.0)
    assert d["detected"], d
    assert d["neck_lo"] is not None and d["neck_hi"] is not None, d
    assert 7500 < d["neck_lo"] < d["neck_hi"] < 7532, d


def test_neck_refilled_detector():
    bars = _dd_day()
    d = detect_double_distribution(bars, 5.0, 10.0)
    assert not neck_refilled(bars, d["neck_lo"], d["neck_hi"]), "holding high — no refill"
    refill = bars + [_bar(7516, v=120), _bar(7515, v=130)]  # two closes back in the neck
    assert neck_refilled(refill, d["neck_lo"], d["neck_hi"])


def _feat(refilled):
    return {
        "n_bars": 32, "sides": 1, "rib": 3.0, "one_tf": "UP", "cvd_pos": 0.8,
        "close_pos": 0.5, "vol_ratio": 1.0, "opening_type": "OPEN_AUCTION_OUT",
        "open_location": "out_value_in_range", "ext_up_bars": 6, "ext_dn_bars": 0,
        "ib_width": 5.0, "ib_pctile": 10, "dd_second_dist": True,
        "dd_neck_refilled": refilled, "returned_through_open": False,
        "stair_steps_up": 0, "stair_steps_dn": 0,
    }


def test_flag_on_refill_drops_trend_dd(monkeypatch):
    monkeypatch.setenv("S1_DD_INVALIDATION_V1", "1")
    r = classify(_feat(refilled=True), load_plan(), is_eod=False)
    assert r["day_type"] != "Trend_DD", r


def test_flag_on_no_refill_keeps_trend_dd(monkeypatch):
    monkeypatch.setenv("S1_DD_INVALIDATION_V1", "1")
    r = classify(_feat(refilled=False), load_plan(), is_eod=False)
    assert r["day_type"] == "Trend_DD", r


def test_flag_off_old_behavior(monkeypatch):
    monkeypatch.delenv("S1_DD_INVALIDATION_V1", raising=False)
    r = classify(_feat(refilled=True), load_plan(), is_eod=False)
    assert r["day_type"] == "Trend_DD", r
