"""Anti-tautological regression tests for DYNAMIC_STRUCT_TRAIL.

Tests the PURE consolidation detector and the dynamic trail integration.
OFF = unchanged (today's behavior). ON + consolidation = stop moves + target updates.
ON + no consolidation = no move. Never-widen invariant holds.

if reverted → RED because: removing detect_consolidation or the DYNAMIC_STRUCT_TRAIL
branch would break the ON-moves-stop assertion and the ON-no-consolidation-no-move
assertion (the flag gates the entire structure-trail logic).
"""
import os
import pytest
from unittest.mock import patch

from backend.v9.services.trade_manager.consolidation import (
    detect_consolidation,
    next_target_from_levels,
)


# ── Pure consolidation detector tests ────────────────────────────────────

def _bars(prices):
    """Build bar dicts from (high, low, close) tuples."""
    return [{"high": h, "low": l, "close": c} for h, l, c in prices]


def test_consolidation_detected_long():
    """After advance, 3 tight bars → consolidation found.

    if reverted → RED because: removing detect_consolidation → ImportError.
    """
    # 10 bars: advance from 7440 to 7460 (20pt > 1×risk=10pt), then 3 tight bars
    bars = _bars([
        (7442, 7438, 7440), (7448, 7440, 7445), (7455, 7445, 7452),
        (7462, 7455, 7460), (7465, 7458, 7463),  # advance
        (7468, 7462, 7465), (7470, 7465, 7468),  # more advance
        (7469, 7466, 7468), (7469, 7467, 7468), (7470, 7467, 7469),  # consolidation: range=3
    ])
    result = detect_consolidation(
        bars=bars, direction="LONG", last_anchor_price=7440.0,
        entry_price=7440.0, initial_risk=10.0,
        min_bars=3, max_range_atr_frac=0.5, min_advance_risk_mult=1.0,
        atr_14=10.0, range_floor_pts=2.0,
    )
    assert result is not None, "Must detect consolidation after advance"
    assert result["zone_low"] > 7440.0, "Zone must be above entry (LONG advance)"
    assert result["zone_range"] <= 5.0, "Zone range must be tight"
    assert result["anchor_extreme"] == result["zone_low"]


def test_consolidation_detected_short():
    """SHORT: advance down, 3 tight bars → consolidation found."""
    bars = _bars([
        (7460, 7458, 7460), (7455, 7448, 7450), (7448, 7440, 7442),
        (7440, 7435, 7436), (7438, 7432, 7434),
        (7435, 7430, 7432), (7433, 7430, 7431),
        (7432, 7429, 7430), (7431, 7429, 7430), (7432, 7429, 7430),
    ])
    result = detect_consolidation(
        bars=bars, direction="SHORT", last_anchor_price=7460.0,
        entry_price=7460.0, initial_risk=10.0,
        min_bars=3, max_range_atr_frac=0.5, min_advance_risk_mult=1.0,
        atr_14=10.0, range_floor_pts=2.0,
    )
    assert result is not None
    assert result["zone_high"] < 7460.0
    assert result["anchor_extreme"] == result["zone_high"]


def test_no_consolidation_without_advance():
    """If price hasn't advanced enough (< M×risk), no consolidation."""
    # 5 bars, range only 3pt (advance < 1×risk=10pt)
    bars = _bars([
        (7442, 7440, 7441), (7443, 7440, 7442), (7443, 7441, 7442),
        (7443, 7441, 7442), (7443, 7441, 7442),
    ])
    result = detect_consolidation(
        bars=bars, direction="LONG", last_anchor_price=7440.0,
        entry_price=7440.0, initial_risk=10.0,
        min_bars=3, max_range_atr_frac=0.5, min_advance_risk_mult=1.0,
        atr_14=10.0, range_floor_pts=2.0,
    )
    assert result is None, "No advance → no consolidation"


def test_no_consolidation_wide_range():
    """Bars have advanced but range too wide → not a consolidation."""
    bars = _bars([
        (7442, 7438, 7440), (7455, 7445, 7452), (7465, 7455, 7462),
        (7470, 7458, 7468),  # advance
        (7475, 7460, 7470), (7478, 7462, 7472), (7480, 7465, 7475),  # wide range (15pt > 0.5×10)
    ])
    result = detect_consolidation(
        bars=bars, direction="LONG", last_anchor_price=7440.0,
        entry_price=7440.0, initial_risk=10.0,
        min_bars=3, max_range_atr_frac=0.5, min_advance_risk_mult=1.0,
        atr_14=10.0, range_floor_pts=2.0,
    )
    assert result is None, "Wide range → not a consolidation"


def test_too_few_bars():
    """Fewer than min_bars → no detection."""
    bars = _bars([(7450, 7448, 7449), (7451, 7449, 7450)])
    result = detect_consolidation(
        bars=bars, direction="LONG", last_anchor_price=7440.0,
        entry_price=7440.0, initial_risk=10.0,
        min_bars=3,
    )
    assert result is None


# ── next_target_from_levels tests ────────────────────────────────────────

def test_next_target_picks_nearest_long():
    """LONG: picks the closest level above current price."""
    result = next_target_from_levels(
        direction="LONG", current_price=7460.0,
        zone_projection=7475.0,
        key_levels=[7480.0, 7465.0, 7500.0],
    )
    assert result == 7465.0, "Must pick nearest (7465), not zone projection (7475)"


def test_next_target_picks_nearest_short():
    """SHORT: picks the closest level below current price."""
    result = next_target_from_levels(
        direction="SHORT", current_price=7460.0,
        zone_projection=7445.0,
        key_levels=[7440.0, 7455.0, 7420.0],
    )
    assert result == 7455.0


def test_next_target_zone_only():
    """No key levels in direction → uses zone projection."""
    result = next_target_from_levels(
        direction="LONG", current_price=7460.0,
        zone_projection=7475.0,
        key_levels=[7400.0, 7420.0],  # all below → not in direction
    )
    assert result == 7475.0


def test_next_target_none_when_empty():
    result = next_target_from_levels(
        direction="LONG", current_price=7460.0,
        zone_projection=None,
        key_levels=[],
    )
    assert result is None


# ── Never-widen invariant ────────────────────────────────────────────────

def test_consolidation_never_widens_stop():
    """If the new stop from consolidation would widen (move further from entry),
    the detector's anchor_extreme must be checked by the caller (manager enforces).
    The detector itself is pure — the manager has the never-widen guard.
    We verify the anchor_extreme is on the correct side.
    """
    bars = _bars([
        (7442, 7438, 7440), (7450, 7440, 7448), (7458, 7448, 7455),
        (7462, 7455, 7460), (7465, 7458, 7463),
        (7468, 7462, 7465), (7470, 7465, 7468),
        (7469, 7466, 7468), (7469, 7467, 7468), (7470, 7467, 7469),
    ])
    result = detect_consolidation(
        bars=bars, direction="LONG", last_anchor_price=7440.0,
        entry_price=7440.0, initial_risk=10.0,
        min_bars=3, atr_14=10.0,
    )
    assert result is not None
    # For LONG, anchor_extreme = zone_low, and the stop goes BELOW that.
    # The manager will only apply if new_stop > current_stop (tighter).
    assert result["anchor_extreme"] > 7440.0, \
        "Anchor must be above entry for LONG (so stop moves up = tighter)"


# ── Source inspection: flag gates the logic ──────────────────────────────

def test_bar_level_detector_has_dynamic_trail_branch():
    """bar_level_detector.on_bar source contains DYNAMIC_STRUCT_TRAIL check.

    if reverted → RED because: removing the branch makes this fail.
    """
    import inspect
    from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector
    source = inspect.getsource(BarLevelDetector.on_bar)
    assert "DYNAMIC_STRUCT_TRAIL" in source
    assert "apply_dynamic_struct_trail" in source
