"""S2 adaptive_stop compute_stop_v2 — structural stop wins, ATR is a size gate.

Mirrors test_woodies_stop_v2.py for S2. Legacy compute_stop() is unchanged
(anti-regression test at the bottom).
"""
from backend.v9.systems.five_min.adaptive_stop import (
    compute_stop, compute_stop_v2, StopComputation, StopComputationV2,
)


# ── V2 core behavior ────────────────────────────────────────────────────

def test_structural_stop_not_moved_by_atr():
    """Big structural anchor (12 ticks) beyond ATR cap — V2 keeps it."""
    r = compute_stop_v2(
        entry_price=7400.0,
        direction="LONG",
        structural_stop_price=7397.0,  # 12 ticks below entry
        family="Reactive",             # multiplier 1.0
        today_typical=1.5,             # cap = 1.0 * 1.5 / 0.25 = 6 ticks
    )
    assert r.stop_price == 7397.0       # NOT moved to entry - 6t
    assert r.risk_ticks == 12
    assert r.atr_cap_ticks == 6
    assert r.cap_exceeded is True       # → fewer contracts downstream
    assert r.floor_applied is False


def test_floor_applies_on_tiny_structural():
    """Structural only 1 tick away → floor 4T wins."""
    r = compute_stop_v2(
        entry_price=7400.0,
        direction="LONG",
        structural_stop_price=7399.75,  # 1 tick below entry
        family="Reactive",
        today_typical=2.0,
    )
    assert r.risk_ticks == 4
    assert r.stop_price == 7399.0       # entry - 4 ticks
    assert r.floor_applied is True


def test_short_direction_mirror():
    """SHORT structural stop above entry."""
    r = compute_stop_v2(
        entry_price=7400.0,
        direction="SHORT",
        structural_stop_price=7403.0,   # 12 ticks above
        family="Double_BT",            # multiplier 2.0
        today_typical=1.0,             # cap = 2.0 * 1.0 / 0.25 = 8 ticks
    )
    assert r.stop_price == 7403.0
    assert r.risk_ticks == 12
    assert r.atr_cap_ticks == 8
    assert r.cap_exceeded is True


def test_cap_not_exceeded_normal():
    """Structural risk within ATR cap → full size OK."""
    r = compute_stop_v2(
        entry_price=7400.0,
        direction="LONG",
        structural_stop_price=7398.5,  # 6 ticks
        family="OFA",                  # multiplier 1.5
        today_typical=2.0,             # cap = 1.5 * 2.0 / 0.25 = 12 ticks
    )
    assert r.risk_ticks == 6
    assert r.cap_exceeded is False
    assert r.floor_applied is False


def test_short_floor_applied():
    """SHORT with tiny structural → floor pushes stop further from entry."""
    r = compute_stop_v2(
        entry_price=7400.0,
        direction="SHORT",
        structural_stop_price=7400.25,  # 1 tick above
        family="Flag",
        today_typical=2.0,
    )
    assert r.risk_ticks == 4
    assert r.stop_price == 7401.0       # entry + 4 ticks
    assert r.floor_applied is True


def test_today_typical_zero_no_crash():
    """today_typical=0 → cap degenerates to floor, no division error."""
    r = compute_stop_v2(
        entry_price=7400.0,
        direction="LONG",
        structural_stop_price=7398.0,  # 8 ticks
        family="Reactive",
        today_typical=0.0,
    )
    assert r.risk_ticks == 8
    assert r.atr_cap_ticks == 4         # falls to floor
    assert r.cap_exceeded is True       # 8 > 4


def test_family_multiplier_affects_cap():
    """HnS (2.0×) gives double the cap vs Reactive (1.0×)."""
    common = dict(entry_price=7400.0, direction="LONG",
                  structural_stop_price=7397.0, today_typical=1.5)
    r_reactive = compute_stop_v2(family="Reactive", **common)  # cap=6
    r_hns = compute_stop_v2(family="HnS", **common)            # cap=12
    assert r_reactive.atr_cap_ticks == 6
    assert r_hns.atr_cap_ticks == 12
    # Same structural → same risk, but different cap_exceeded
    assert r_reactive.cap_exceeded is True   # 12 > 6
    assert r_hns.cap_exceeded is False       # 12 <= 12


# ── Anti-regression: legacy compute_stop unchanged ──────────────────────

def test_legacy_compute_stop_unchanged():
    """Legacy path must still behave exactly as before.
    This is what runs while STOP_ANCHORS_V2 is OFF."""
    r = compute_stop(
        entry_price=7400.0,
        direction="LONG",
        structural_anchor=7398.5,   # anchor
        family="Reactive",          # mult 1.0
        today_typical=2.0,          # cap = 1.0 * 2.0 = 2.0; cap_price = 7398.0
    )
    assert isinstance(r, StopComputation)
    # Layer A: 7398.5 - 0.25 = 7398.25
    # Layer B: 7400 - 1.0*2.0 = 7398.0
    # candidate = max(7398.25, 7398.0) = 7398.25 → A wins
    # Layer C: 7400 - 4*0.25 = 7399.0
    # final = min(7398.25, 7399.0) = 7398.25 (A tighter than floor)
    assert r.stop_price == 7398.25
    assert r.binding_layer == "A"


def test_legacy_floor_still_binding():
    """Legacy: when structural and cap are both above floor, floor wins."""
    r = compute_stop(
        entry_price=7400.0,
        direction="LONG",
        structural_anchor=7400.0,   # at entry → structural = 7399.75
        family="Reactive",
        today_typical=0.5,          # cap = 7400 - 0.5 = 7399.5
    )
    # A = 7399.75, B = 7399.5, candidate = max(7399.75, 7399.5) = 7399.75
    # C = 7399.0, final = min(7399.75, 7399.0) = 7399.0 → floor
    assert r.stop_price == 7399.0
    assert r.binding_layer == "C"
