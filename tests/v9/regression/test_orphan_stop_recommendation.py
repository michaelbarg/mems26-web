"""P3: an untracked (orphan) Sierra position must never sit naked — the
reconciler computes an exact protective stop to surface in the CRITICAL alert.
"""
from backend.v9.services.sierra_position_reconciler import recommend_orphan_stop


def test_long_orphan_stop_below_entry():
    r = recommend_orphan_stop(3, 7600.0)
    assert r == {"side": "LONG", "qty": 3, "entry": 7600.0, "stop": 7590.0, "points": 10.0}


def test_short_orphan_stop_above_entry():
    r = recommend_orphan_stop(-4, 7600.0)
    assert r["side"] == "SHORT" and r["qty"] == 4 and r["stop"] == 7610.0


def test_tick_snapped():
    # entry 7600.10 → LONG stop 7590.10 → snapped to nearest 0.25 = 7590.0
    r = recommend_orphan_stop(1, 7600.10)
    assert r["stop"] == 7590.0


def test_none_avg_price_returns_none():
    assert recommend_orphan_stop(3, None) is None


def test_zero_qty_returns_none():
    assert recommend_orphan_stop(0, 7600.0) is None


def test_nonpositive_avg_returns_none():
    assert recommend_orphan_stop(2, 0) is None


def test_points_env_override(monkeypatch):
    monkeypatch.setenv("ORPHAN_STOP_POINTS", "6")
    r = recommend_orphan_stop(2, 7600.0)
    assert r["stop"] == 7594.0 and r["points"] == 6.0
