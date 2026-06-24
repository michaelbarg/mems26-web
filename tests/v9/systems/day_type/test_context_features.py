"""Tests for context_features — IB percentile, open_location, poc_drift.
open_location uses REAL 2026-06-19 references (full-session VA + PDH/PDL).
(second_distribution removed 2026-06-20 — dead POC-jump proxy, superseded by dd_features.)"""
from backend.v9.systems.day_type.context_features import (
    ib_width_percentile, open_location, poc_drift,
)


def test_ib_percentile_narrow_normal_wide():
    hist = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
    assert ib_width_percentile(9, hist)["klass"] == "NARROW"    # below all
    assert ib_width_percentile(29, hist)["klass"] == "WIDE"     # above all
    assert ib_width_percentile(19, hist)["klass"] == "NORMAL"   # middle


def test_ib_percentile_insufficient_history():
    assert ib_width_percentile(10, [11, 12])["klass"] == "UNKNOWN"


def test_open_location_real_0619():
    # 2026-06-19: prior FULL-session VA 7542.5–7576, PDH/PDL 7583/7535.5.
    assert open_location(7560.0, 7576.0, 7542.5, 7583.0, 7535.5) == "in_value"      # inside VA
    assert open_location(7580.0, 7576.0, 7542.5, 7583.0, 7535.5) == "out_value_in_range"  # above VA, in range
    assert open_location(7590.0, 7576.0, 7542.5, 7583.0, 7535.5) == "out_of_range"  # above PDH


def test_poc_drift_relative():
    assert poc_drift(108.0, 100.0, 5.0) == 1.6     # value migrated up 1.6 IB-widths
    assert poc_drift(100.0, 100.0, 5.0) == 0.0
    assert poc_drift(None, 100.0, 5.0) is None
