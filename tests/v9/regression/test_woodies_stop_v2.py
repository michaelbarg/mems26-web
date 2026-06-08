"""S4 woodies compute_stop_v2 — structural stop wins, ATR is a size gate.

Pins the core behavior change of stop-anchor V2 for S4. Flag-off / pure: legacy
compute_stop() is untouched (a separate test proves that). MES tick=0.25.
"""
from backend.v9.systems.woodies.atr_stop import (
    compute_stop_v2, compute_stop, StopResultV2, PatternGroup,
)


def test_structural_stop_is_not_moved_by_atr_on_big_bar():
    # LONG entry 7400, structural anchor (cluster low -3T) at 7388 = 12-tick risk.
    # ATR cap (CONT_TIGHT 1.0x) is only 8 ticks. Legacy would pull the stop to 8t.
    # V2 keeps the structural 12t stop and flags cap_exceeded for sizing.
    r = compute_stop_v2("LONG", 7400.0, 7388.0, PatternGroup.CONT_TIGHT, atr_14=8.0)
    assert r.stop_price == 7388.0          # NOT moved to entry-8t (7398)
    assert r.risk_ticks == 48              # 12 pts = 48 ticks
    assert r.atr_cap_ticks == 8
    assert r.cap_exceeded is True          # → fewer contracts downstream
    assert r.floor_applied is False


def test_floor_still_applies_on_tiny_structural():
    # structural only 1 tick away -> floor 4t wins
    r = compute_stop_v2("LONG", 7400.0, 7399.75, PatternGroup.CONT_TIGHT, atr_14=10.0)
    assert r.risk_ticks == 4
    assert r.stop_price == 7399.0          # entry - 4 ticks
    assert r.floor_applied is True


def test_short_direction_mirror():
    r = compute_stop_v2("SHORT", 7400.0, 7412.0, PatternGroup.REV, atr_14=8.0)
    assert r.stop_price == 7412.0
    assert r.risk_ticks == 48
    assert r.cap_exceeded is True          # REV cap 1.5*8=12 < 48


def test_cap_not_exceeded_normal_bar():
    # structural 6t risk, ATR cap 1.0*10=10t -> within cap -> full size
    r = compute_stop_v2("LONG", 7400.0, 7398.5, PatternGroup.CONT_TIGHT, atr_14=10.0)
    assert r.risk_ticks == 6
    assert r.cap_exceeded is False


def test_legacy_compute_stop_unchanged():
    """Anti-regression: legacy path must still behave exactly as before
    (this is what runs while STOP_ANCHORS_V2 is OFF)."""
    from backend.v9.systems.woodies.schemas import WoodiesBar
    bar = WoodiesBar(ts=1781000000.0, open=7400, high=7402,
                     low=7399, close=7401, cci_14=120.0)
    res = compute_stop("LONG", bar, swing_anchor=None,
                       pattern_group=PatternGroup.CONT_TIGHT, atr_14=8.0)
    # CONT primary 3t vs cap 8t -> min 3t -> floor 4t -> 4t below entry-bar low
    assert res.stop_ticks == 4
    assert res.layer_applied == "floor"
