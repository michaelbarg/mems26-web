"""Item-22 — TARGET_ZONES_V1 level-confluence clustering + C2/C3 selection."""
from backend.v9.systems.target_zones import (
    cluster_levels, select_target_zones, zone_tol_pts, Zone,
)


def test_cluster_merges_nearby_levels():
    """Three levels within 1.5pt collapse to one zone; a far one stays separate."""
    levels = [(7550.0, "poc"), (7551.0, "val"), (7551.5, "pd_poc"), (7580.0, "vah")]
    zones = cluster_levels(levels, tol_pts=1.5)
    assert len(zones) == 2
    strong = zones[0]
    assert strong.strength == 3 and strong.low == 7550.0 and strong.high == 7551.5


def test_cluster_strength_counts_confluence():
    levels = [(7600.0, "ibh"), (7600.5, "sh"), (7600.25, "swing")]
    z = cluster_levels(levels, tol_pts=1.0)[0]
    assert z.strength == 3
    assert set(z.members) == {"ibh", "sh", "swing"}


def test_select_short_zones_below_t1_near_edge():
    """SHORT: C2/C3 are the nearest zones below T1; target = zone HIGH (near edge)."""
    zones = cluster_levels(
        [(7520.0, "poc"), (7520.5, "val"), (7505.0, "pdl"), (7490.0, "swing")],
        tol_pts=1.5)
    sel = select_target_zones(direction="SHORT", entry_price=7540.0,
                              t1_price=7532.0, zones=zones)
    # nearest zone below 7532 is the 7520/7520.5 cluster → near edge = high 7520.5
    assert sel["c2"] == 7520.5
    assert sel["c3"] == 7505.0
    assert sel["c2_zone"].strength == 2


def test_select_long_zones_above_t1():
    zones = cluster_levels(
        [(7560.0, "vah"), (7560.5, "pdh"), (7575.0, "ext")], tol_pts=1.5)
    sel = select_target_zones(direction="LONG", entry_price=7545.0,
                              t1_price=7552.0, zones=zones)
    # nearest zone above 7552 → near edge = low 7560.0
    assert sel["c2"] == 7560.0
    assert sel["c3"] == 7575.0


def test_no_zone_beyond_t1_returns_none():
    zones = cluster_levels([(7500.0, "poc")], tol_pts=1.5)
    sel = select_target_zones(direction="SHORT", entry_price=7540.0,
                              t1_price=7495.0, zones=zones)  # t1 already below the only level
    assert sel["c2"] is None and sel["c3"] is None


def test_min_strength_filter_drops_lonely_levels():
    zones = cluster_levels([(7520.0, "poc"), (7519.5, "val"), (7500.0, "lonely")],
                           tol_pts=1.5)
    sel = select_target_zones(direction="SHORT", entry_price=7540.0, t1_price=7532.0,
                              zones=zones, min_strength=2)
    assert sel["c2"] == 7520.0     # the 2-member confluence
    assert sel["c3"] is None       # lonely single-level zone filtered out


def test_targets_snap_to_grid():
    zones = cluster_levels([(7560.13, "vah")], tol_pts=1.0)
    sel = select_target_zones(direction="LONG", entry_price=7545.0, t1_price=7552.0,
                              zones=zones)
    px = sel["c2"]
    assert abs((px / 0.25) - round(px / 0.25)) < 1e-9


def test_tol_defaults_to_half_atr():
    assert zone_tol_pts(16.0) == 8.0
    assert zone_tol_pts(1.0) == 1.5   # floor
    assert zone_tol_pts(None) == 1.5
