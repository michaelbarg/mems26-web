"""Tests for time_stop_mapper (S1 Day Type → time_stop_minutes)."""
from backend.v9.systems.five_min.time_stop_mapper import get_time_stop


def test_trend_normal_no_time_stop():
    # Trend_Normal has no time stop (None in targets_table)
    ts = get_time_stop("Trend_Normal")
    assert ts == 60  # falls back to DEFAULT since None


def test_variation_60min():
    ts = get_time_stop("Variation")
    assert ts == 60


def test_nontrend_20min():
    ts = get_time_stop("Nontrend")
    assert ts == 20
