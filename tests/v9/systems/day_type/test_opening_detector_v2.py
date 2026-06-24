"""Tests for opening_detector_v2 — the 5 measured opening types + the over-DRIVE fix.
Includes REAL 2026-06-19 early bars (from v9_bars_5min_woodies) which must NOT be DRIVE."""
from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type


def B(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


FAR = dict(prior_vah=110, prior_val=90, pdh=112, pdl=88)  # refs far → no poke


def test_open_drive_up():
    bars = [B(100, 100.6, 100.0, 100.5), B(100.5, 101.1, 100.4, 101.0),
            B(101.0, 102.1, 100.9, 102.0), B(102.0, 103.2, 101.9, 103.0)]
    r = detect_opening_type(bars, 100.0, **FAR)
    assert r["opening_type"] == "OPEN_DRIVE" and r["direction"] == "UP", r


def test_open_drive_down():
    bars = [B(100, 100.0, 99.4, 99.5), B(99.5, 99.6, 98.9, 99.0),
            B(99.0, 99.1, 97.9, 98.0), B(98.0, 98.1, 96.9, 97.0)]
    r = detect_opening_type(bars, 100.0, **FAR)
    assert r["opening_type"] == "OPEN_DRIVE" and r["direction"] == "DOWN", r


def test_drive_reverted_by_return_through_open():
    """ANTI-TAUTOLOGY: same up-shape but bar-2 dips below the open → NOT a drive."""
    bars = [B(100, 100.6, 100.0, 100.5), B(100.5, 101.1, 99.5, 101.0),  # low 99.5 < open
            B(101.0, 102.1, 100.9, 102.0), B(102.0, 103.2, 101.9, 103.0)]
    r = detect_opening_type(bars, 100.0, **FAR)
    assert r["opening_type"] != "OPEN_DRIVE", r


def test_auction_in_rangey():
    bars = [B(100, 100.7, 99.2, 100.5), B(100.5, 100.8, 99.0, 99.4),
            B(99.4, 100.6, 99.0, 100.6), B(100.6, 100.9, 99.1, 99.3), B(99.3, 100.5, 99.0, 100.4)]
    r = detect_opening_type(bars, 100.0, prior_vah=104, prior_val=96, pdh=106, pdl=94)
    assert r["opening_type"] == "OPEN_AUCTION_IN", r


def test_auction_out_of_range():
    bars = [B(107, 107.6, 106.4, 107.4), B(107.4, 107.7, 106.3, 106.6),
            B(106.6, 107.8, 106.4, 107.5), B(107.5, 107.9, 106.3, 106.5)]
    r = detect_opening_type(bars, 107.0, prior_vah=104, prior_val=96, pdh=106, pdl=94)
    assert r["opening_type"] == "OPEN_AUCTION_OUT", r


def test_rejection_reverse():
    bars = [B(100, 101.7, 99.9, 101.5), B(101.5, 101.6, 100.5, 100.8),
            B(100.8, 100.9, 99.0, 99.2), B(99.2, 99.3, 97.9, 98.0)]
    r = detect_opening_type(bars, 100.0, **FAR)
    assert r["opening_type"] == "OPEN_REJECTION_REVERSE" and r["direction"] == "DOWN", r


def test_test_drive_poke_fail():
    bars = [B(100, 101.8, 99.9, 100.2), B(100.2, 100.3, 99.0, 99.3),
            B(99.3, 99.4, 98.0, 98.2), B(98.2, 98.3, 97.0, 97.2)]
    r = detect_opening_type(bars, 100.0, prior_vah=101, prior_val=90, pdh=112, pdl=88)
    assert r["opening_type"] == "OPEN_TEST_DRIVE", r


def test_real_0619_is_not_drive():
    """REAL 2026-06-19 early bars: rangey, crosses the open → AUCTION, NOT the
    OPEN_DRIVE the old detector produced. This is the over-DRIVE fix on real data."""
    bars = [B(7545.5, 7545.75, 7541.25, 7543), B(7542.75, 7544.25, 7537.75, 7538.75),
            B(7538.25, 7543.5, 7538.25, 7542.25), B(7542.5, 7546.25, 7540, 7543.5),
            B(7543.5, 7547.25, 7543.5, 7544.5), B(7544.25, 7545, 7543, 7543.5),
            B(7543.5, 7543.75, 7540, 7542.5), B(7542.25, 7543.5, 7537.5, 7541.75)]
    r = detect_opening_type(bars, 7545.5, prior_vah=7576.0, prior_val=7542.5, pdh=7583.0, pdl=7535.5)
    assert r["opening_type"] != "OPEN_DRIVE", r
    assert r["opening_type"].startswith("OPEN_AUCTION"), r
