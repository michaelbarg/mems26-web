"""Tests for day_type_targets.compute_targets_for_day_type (Pkg 3a Stream 2)."""
import pytest
from backend.v9.systems.day_type.day_type_targets import compute_targets_for_day_type


def test_returns_none_for_none_input():
    assert compute_targets_for_day_type(
        day_type=None, entry_price=4500, stop_price=4490, direction="LONG"
    ) is None


def test_returns_none_for_unknown_day_type():
    assert compute_targets_for_day_type(
        day_type="Banana", entry_price=4500, stop_price=4490, direction="LONG"
    ) is None


def test_returns_none_for_zero_risk():
    assert compute_targets_for_day_type(
        day_type="Trend_Normal", entry_price=4500, stop_price=4500, direction="LONG"
    ) is None


def test_trend_normal_long_no_time_stop():
    r = compute_targets_for_day_type(
        day_type="Trend_Normal", entry_price=4500, stop_price=4490, direction="LONG"
    )
    assert r is not None
    assert r["time_stop_minutes"] is None
    assert r["t1_price"] == 4510              # 1R = 10
    assert r["t3_price"] == 4540              # 4R = 40
    assert r["trail_after_t2"] is True
    assert r["no_trade"] is False


def test_trend_dd_short_90min_time_stop():
    r = compute_targets_for_day_type(
        day_type="Trend_DD", entry_price=4500, stop_price=4508, direction="SHORT"
    )
    assert r is not None
    assert r["time_stop_minutes"] == 90
    assert r["t1_price"] == 4492              # entry - 1R (R=8)
    # t2_r is None (open-ended) per targets_table → t2_price is None
    assert r["t2_price"] is None
    assert r["t3_price"] == 4468              # entry - 4R = entry - 32


def test_neutral_extreme_45min_no_t3():
    r = compute_targets_for_day_type(
        day_type="Neutral_Extreme", entry_price=4500, stop_price=4490, direction="LONG"
    )
    assert r is not None
    assert r["time_stop_minutes"] == 45
    assert r["t3_price"] is None
    assert r["t2_price"] is None


def test_neutral_center_30min():
    r = compute_targets_for_day_type(
        day_type="Neutral_Center", entry_price=4500, stop_price=4490, direction="LONG"
    )
    assert r is not None
    assert r["time_stop_minutes"] == 30
    assert r["t2_price"] is None
    assert r["no_trade"] is False


def test_nontrend_no_trade_true():
    r = compute_targets_for_day_type(
        day_type="Nontrend", entry_price=4500, stop_price=4490, direction="LONG"
    )
    assert r is not None
    assert r["no_trade"] is True
    assert r["time_stop_minutes"] is None
    assert r["sizing_contracts"] == 0


def test_legacy_neutral_maps_to_neuc():
    r = compute_targets_for_day_type(
        day_type="Neutral", entry_price=4500, stop_price=4490, direction="LONG"
    )
    assert r is not None
    assert r["day_type_canonical"] == "Neutral_Center"
    assert r["time_stop_minutes"] == 30


def test_short_direction_sign_correct():
    r = compute_targets_for_day_type(
        day_type="Trend_Normal", entry_price=4500, stop_price=4510, direction="SHORT"
    )
    assert r is not None
    assert r["t1_price"] == 4490
