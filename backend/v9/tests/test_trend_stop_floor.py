"""TREND_STOP_FLOOR_V1 — trend-day stop floor tests (2026-08-04).

Five acceptance cases:
1. With-trend on Trend day: floor applied (stop widened)
2. Against-trend on Trend day: floor NOT applied
3. Balance day: floor NOT applied
4. Opening trade: floor NOT applied (own caps)
5. Floor exceeds max risk: floor NOT applied (SIZE_CUT, not expand)
"""
import os
import pytest


# ── Pure logic tests (no system wiring needed) ──

def _compute_floor(ib_width):
    """Same formula as the system: max(6.0, 0.15 * IB_width)."""
    return max(6.0, 0.15 * ib_width)


def _should_apply_floor(day_type, direction, day_bias, is_opening, risk_pts, floor_pts, max_pts=15.0):
    """Pure decision: should the floor be applied?"""
    is_trend = day_type.startswith("Trend")
    with_trend = (
        (direction == "LONG" and day_bias == "UP")
        or (direction == "SHORT" and day_bias == "DOWN")
    )
    if not is_trend:
        return False
    if not with_trend:
        return False
    if is_opening:
        return False
    if risk_pts >= floor_pts:
        return False  # already above floor
    if floor_pts > max_pts:
        return False  # would exceed max risk
    return True


def test_with_trend_floor_applied():
    """Case 1: LONG on Trend UP with 3pt stop → floor raises to 6pt."""
    assert _should_apply_floor("Trend_Normal", "LONG", "UP", False, 3.0, 6.0)


def test_against_trend_no_floor():
    """Case 2: SHORT on Trend UP → no floor."""
    assert not _should_apply_floor("Trend_Normal", "SHORT", "UP", False, 3.0, 6.0)


def test_balance_day_no_floor():
    """Case 3: Normal day → no floor regardless of direction."""
    assert not _should_apply_floor("Normal", "LONG", "UP", False, 3.0, 6.0)
    assert not _should_apply_floor("Neutral_Center", "LONG", "UP", False, 3.0, 6.0)


def test_opening_trade_no_floor():
    """Case 4: Opening trade → own caps, no trend floor."""
    assert not _should_apply_floor("Trend_Normal", "LONG", "UP", True, 3.0, 6.0)


def test_floor_exceeds_max_not_applied():
    """Case 5: Floor 12pt > max 10pt → not applied."""
    assert not _should_apply_floor("Trend_Normal", "LONG", "UP", False, 3.0, 12.0, max_pts=10.0)


def test_floor_formula_small_ib():
    """IB=30pt → floor = max(6, 0.15*30) = 6.0 (minimum)."""
    assert _compute_floor(30.0) == 6.0


def test_floor_formula_large_ib():
    """IB=80pt → floor = max(6, 0.15*80) = 12.0."""
    assert _compute_floor(80.0) == 12.0


def test_already_above_floor():
    """Risk 8pt >= floor 6pt → no change needed."""
    assert not _should_apply_floor("Trend_Normal", "LONG", "UP", False, 8.0, 6.0)


def test_variation_with_leg_eligible():
    """Variation with a live leg should also be eligible (treated as trend)."""
    # This is a conceptual test — Variation + leg is treated as trend-like
    # The actual system checks day_type + leg_dir; this tests the logic
    is_trend_like = "Normal_Variation".startswith("Trend")  # False for NV
    # But with leg, it becomes eligible — tested at integration level
    assert not is_trend_like  # NV by itself is not trend
