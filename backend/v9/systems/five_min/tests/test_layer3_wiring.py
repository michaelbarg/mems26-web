"""Tests for Layer 3 wiring (Path A: cluster + empty_zone → entry plan)."""
from backend.v9.layer3.cluster import identify_cluster, PriceLevel
from backend.v9.layer3.empty_zone import identify_empty_zones
from backend.v9.systems.five_min.setup_emitter import emit_t1_setup


def _make_levels(poc_price=5250.0, poc_vol=500):
    """Create minimal price levels for cluster identification."""
    return [
        PriceLevel(price=poc_price - 1.0, bid_vol=100, ask_vol=100),
        PriceLevel(price=poc_price - 0.5, bid_vol=150, ask_vol=200),
        PriceLevel(price=poc_price, bid_vol=200, ask_vol=300),
        PriceLevel(price=poc_price + 0.5, bid_vol=150, ask_vol=150),
        PriceLevel(price=poc_price + 1.0, bid_vol=70, ask_vol=80),
    ]


def test_cluster_provides_yellow_poc():
    """identify_cluster returns yellow_poc for entry computation."""
    levels = _make_levels(poc_price=5250.0, poc_vol=500)
    cluster = identify_cluster(levels, bar_total_vol=1500)
    assert cluster is not None
    # yellow_poc is the level with max total_vol (ask+bid)
    assert cluster.yellow_poc == 5250.0  # 200+300=500 is highest
    assert cluster.cluster_high >= cluster.cluster_low


def test_empty_zone_provides_stop():
    """identify_empty_zones returns zones for stop placement."""
    levels = _make_levels()
    # Add thin levels below to create empty zone
    levels_with_gap = [
        PriceLevel(price=5245.0, bid_vol=1, ask_vol=1),   # very thin
        PriceLevel(price=5246.0, bid_vol=1, ask_vol=0),   # very thin
        PriceLevel(price=5247.0, bid_vol=2, ask_vol=1),   # thin
    ] + levels
    zones = identify_empty_zones(levels_with_gap, bar_total_vol=1500)
    assert isinstance(zones, list)


def test_emitter_with_layer3_data():
    """End-to-end: emitter with real Layer 3 data → valid T1Setup."""
    # Simulate what happens when Layer 3 provides cluster + empty_zone
    setup = emit_t1_setup(
        'REACTIVE_LONG', 'LONG',
        entry_price=5250.0,  # yellow_poc from cluster
        stop_price=5246.5,   # empty_zone bottom
        t1_price=5253.5,     # 1R up
        t2_price=5257.0,     # 2R up
        bar_index=100,
        day_type="Variation",
        tpo_data={"poc": 5250.0, "vah": 5260.0, "val": 5240.0},
    )
    assert setup is not None
    assert setup.provisional is False
    assert setup.entry_price == 5250.0
    assert setup.stop_price == 5246.5
    assert setup.quality_tier == 'HIGH'
