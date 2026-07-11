"""Ladder collapse guard — trade 337: t1=t2=t3=7583.75.

When target producers converge on a single level, the bracket degenerates
into a point. The ladder-dedup guard nudges t2/t3 farther so each contract
has a distinct target.

If reverted → RED because without the guard, t1=t2=t3 stay identical,
and the bracket has no runner differentiation.
"""
from backend.v9.systems.structural_targets import _build_result


def test_build_result_deduplicates_collapsed_targets():
    """_build_result's monotonicity should separate identical c1/c2/c3."""
    result = _build_result(
        direction="SHORT",
        entry=7591.25,
        stop=7597.5,
        c1=7583.75,
        c2=7583.75,
        c3=7583.75,
        contracts=3,
        time_stop_minutes=90,
        trail_after_c2=True,
        day_type="Normal",
    )
    t1 = result["t1_price"]
    t2 = result["t2_price"]
    t3 = result["t3_price"]
    # All three must be distinct
    assert t1 != t2, f"t1 ({t1}) == t2 ({t2}) — ladder collapsed"
    assert t2 != t3, f"t2 ({t2}) == t3 ({t3}) — ladder collapsed"
    # All must be below entry (SHORT)
    assert t1 < 7591.25
    assert t2 < 7591.25
    assert t3 < 7591.25
    # Monotonicity: |t1-entry| < |t2-entry| < |t3-entry|
    assert abs(t1 - 7591.25) < abs(t2 - 7591.25) < abs(t3 - 7591.25)


def test_build_result_normal_targets_unchanged():
    """Distinct targets should not be affected by monotonicity fix."""
    result = _build_result(
        direction="LONG",
        entry=7600.0,
        stop=7594.0,
        c1=7606.0,
        c2=7612.0,
        c3=7618.0,
        contracts=3,
        time_stop_minutes=90,
        trail_after_c2=True,
        day_type="Normal",
    )
    assert result["t1_price"] == 7606.0
    assert result["t2_price"] == 7612.0
    assert result["t3_price"] == 7618.0
