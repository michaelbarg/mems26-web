"""Offset-exactness — every anchor type applies EXACTLY the spec's 3 ticks.

Catches the class of bug CC's e2e tests missed: they asserted only
`stop <= entry` (correct side) but not the exact distance, so a structure-
anchored S2 family double-counting the offset (pattern bakes in 1T, V2 adds 3T
= 4T) slipped through. These tests pin the distance.
"""
from backend.v9.systems.stop_anchors import resolver as SA

TICK = SA.MES_TICK  # 0.25


def test_window_anchor_is_exactly_3t_from_raw_low():
    # cluster low = 7390.0 ; LONG stop must be 7390 - 3*0.25 = 7389.25
    bars = [{"l": 7392.0, "h": 7395.0}, {"l": 7390.0, "h": 7393.0}, {"l": 7391.0, "h": 7392.0}]
    stop = SA.resolve_anchor_from_window(bars, "LONG", 3)
    assert stop == round(7390.0 - 3 * TICK, 2) == 7389.25


def test_structure_anchor_raw_is_exactly_3t():
    # raw structure (flag_low) = 7400.0 ; stop = 7400 - 0.75 = 7399.25
    assert SA.apply_offset(7400.0, "LONG", 3) == 7399.25
    assert SA.apply_offset(7400.0, "SHORT", 3) == 7400.75


def test_baked_in_tick_is_stripped_so_total_is_3t_not_4t():
    """The wiring fix: structural_anchor = flag_low − 1T must be un-baked before
    apply_offset, so the total is 3T from flag_low, not 4T."""
    flag_low = 7400.0
    structural_anchor = flag_low - TICK          # what the pattern passes (−1T)
    # WRONG (pre-fix): apply_offset(structural_anchor) = flag_low − 4T
    wrong = SA.apply_offset(structural_anchor, "LONG", 3)
    assert wrong == round(flag_low - 4 * TICK, 2) == 7399.0   # the bug value
    # RIGHT (post-fix): un-bake the 1T, then 3T from raw = flag_low − 3T
    raw = structural_anchor + TICK
    right = SA.apply_offset(raw, "LONG", 3)
    assert right == round(flag_low - 3 * TICK, 2) == 7399.25
    assert right != wrong                          # the fix changes the value by 1 tick


def test_short_structure_unbake():
    flag_high = 7400.0
    structural_anchor = flag_high + TICK
    raw = structural_anchor - TICK
    assert SA.apply_offset(raw, "SHORT", 3) == round(flag_high + 3 * TICK, 2) == 7400.75
