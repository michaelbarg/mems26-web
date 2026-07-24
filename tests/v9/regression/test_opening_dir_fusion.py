"""OPENING_DIR_FUSION_V1 — volume-confirmed opening-direction gate.

The recipe (docs/reports/OPENING_SIGNAL_EDGE_2026-07-24.md): on the days it fires it
called the day direction 73% vs the classifier's 53%. These tests pin the LOGIC of the
pure function; the 73% is the empirical aggregate, not asserted per-fixture.

Rules: opening volume below the trailing median → None (auction/low-conviction);
direction = 30-min momentum (>2 pt); an accepted level-break that conflicts → None.
"""
from backend.v9.systems.opening_entry import opening_dir_fusion


def B(o, h, l, c, v):
    return {"o": o, "h": h, "l": l, "c": c, "v": v}


def _bars(open_p, close6, hi=None, lo=None):
    hi = hi if hi is not None else max(open_p, close6) + 1
    lo = lo if lo is not None else min(open_p, close6) - 1
    mid = [B(open_p, hi, lo, open_p, 50) for _ in range(5)]
    return mid + [B(open_p, hi, lo, close6, 50)]


def test_hi_vol_up_momentum_fires_up():
    r = opening_dir_fusion(_bars(100.0, 105.0), 100.0, opening_vol=300, median_open_vol=200)
    assert r == "UP"


def test_hi_vol_down_momentum_fires_down():
    r = opening_dir_fusion(_bars(100.0, 95.0), 100.0, opening_vol=300, median_open_vol=200)
    assert r == "DOWN"


def test_low_volume_is_auction_none():
    # same up move, but opening volume below the trailing median → skip
    r = opening_dir_fusion(_bars(100.0, 105.0), 100.0, opening_vol=150, median_open_vol=200)
    assert r is None


def test_flat_momentum_none():
    # |close - open| <= 2pt → no directional momentum → None
    r = opening_dir_fusion(_bars(100.0, 101.5), 100.0, opening_vol=300, median_open_vol=200)
    assert r is None


def test_accepted_break_agrees_fires():
    # up momentum + close accepted above PDH (agree) → UP
    bars = _bars(100.0, 106.0, hi=107.0, lo=103.0)
    r = opening_dir_fusion(bars, 100.0, 300, 200, pdh=104.0)
    assert r == "UP"


def test_accepted_break_conflict_none():
    # up momentum (close 103 > open 100) but close is BELOW yesterday's low 105
    # (accepted DOWN) → conflict → None
    bars = _bars(100.0, 103.0, hi=104.0, lo=99.0)
    r = opening_dir_fusion(bars, 100.0, 300, 200, pdl=105.0)
    assert r is None


def test_missing_inputs_fail_closed():
    assert opening_dir_fusion([], 100.0, 300, 200) is None
    assert opening_dir_fusion(_bars(100.0, 105.0), 100.0, None, 200) is None
    assert opening_dir_fusion(_bars(100.0, 105.0), 100.0, 300, None) is None
