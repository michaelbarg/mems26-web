"""Tests for cvd_features.compute_cvd_features — grounded in REAL 2026-06-19 data."""
from backend.v9.systems.day_type.cvd_features import compute_cvd_features

# Real cumulative-delta series from /api/v9/cumulative_delta/current on 2026-06-19.
TODAY_CUM = [261, 397, 146, 210, 191, 446, -267, -190, -85, 40, -235, -174, -402,
             260, 549, 459, 930, 1066, 1315, 1658, 1250, 845, 861, 1017, 88, -706,
             -1170, -461, -400, -574, -778, -849, -867, -658, -386, -370, -101,
             -273, -124, 31, -370, -564]


def test_today_is_flat_not_trend():
    """cvd_pos≈0.21 (low) BUT the -1170 low is 15 bars old → direction FLAT, not short.
    Matches the spec's own read: today swung two-sided and returned = balance."""
    f = compute_cvd_features(TODAY_CUM, k=5)
    assert abs(f["cvd_pos"] - 0.214) < 0.01, f
    assert f["recent_new_low"] is False, f
    assert f["direction"] == "flat", f


def test_monotonic_up_supports_long():
    f = compute_cvd_features([0, 50, 120, 240, 400, 600], k=5)
    assert f["cvd_pos"] == 1.0, f
    assert f["recent_new_high"] is True, f
    assert f["direction"] == "support_long", f


def test_monotonic_down_supports_short():
    f = compute_cvd_features([0, -40, -90, -200, -350, -560], k=5)
    assert f["cvd_pos"] == 0.0, f
    assert f["direction"] == "support_short", f


def test_midband_is_flat():
    f = compute_cvd_features([0, 100, -100, 80, -60, 30], k=5)
    assert 0.25 < f["cvd_pos"] < 0.75, f
    assert f["direction"] == "flat", f


def test_empty_is_safe():
    f = compute_cvd_features([])
    assert f["cvd_pos"] is None and f["direction"] == "flat"
