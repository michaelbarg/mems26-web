"""Tests for Layer 3: Cluster, Empty Zone, Entry Executor."""

import pytest
from backend.v9.layer3.cluster import PriceLevel, identify_cluster
from backend.v9.layer3.empty_zone import identify_empty_zones
from backend.v9.layer3.entry_executor import compute_entry_plan, DAY_TYPE_TARGETS


# ── Fixtures ──────────────────────────────────────────────

def make_levels(prices_and_vols):
    """Helper: [(price, bid, ask), ...] -> [PriceLevel, ...]"""
    return [PriceLevel(price=p, bid_vol=b, ask_vol=a) for p, b, a in prices_and_vols]


SAMPLE_BAR = make_levels([
    (5246.00, 10, 5),    # low volume
    (5246.25, 8, 3),     # low volume
    (5246.50, 15, 20),   # moderate
    (5246.75, 50, 80),   # HIGH — cluster
    (5247.00, 60, 90),   # HIGH — cluster (POC candidate)
    (5247.25, 55, 70),   # HIGH — cluster
    (5247.50, 20, 15),   # moderate
    (5247.75, 5, 8),     # low volume
    (5248.00, 2, 1),     # empty zone
    (5248.25, 1, 1),     # empty zone
])

TOTAL_VOL = sum(lv.total_vol for lv in SAMPLE_BAR)


# ══════════════════════════════════════════════════════════
# CLUSTER TESTS
# ══════════════════════════════════════════════════════════

class TestCluster:
    def test_identifies_poc(self):
        c = identify_cluster(SAMPLE_BAR, TOTAL_VOL)
        assert c is not None
        assert c.yellow_poc == 5247.00  # highest volume level

    def test_cluster_three_levels(self):
        c = identify_cluster(SAMPLE_BAR, TOTAL_VOL)
        assert c.cluster_low == 5246.75
        assert c.cluster_high == 5247.25
        assert len(c.levels) == 3

    def test_cluster_density(self):
        c = identify_cluster(SAMPLE_BAR, TOTAL_VOL)
        assert 0.4 < c.density < 0.9  # cluster should be 40-90% of volume

    def test_dominant_side_buy(self):
        c = identify_cluster(SAMPLE_BAR, TOTAL_VOL)
        assert c.dominant_side == "BUY"  # ask > bid in cluster

    def test_dominant_side_sell(self):
        sell_levels = make_levels([
            (100.0, 80, 20),
            (100.25, 90, 10),
            (100.50, 70, 15),
        ])
        c = identify_cluster(sell_levels, 285)
        assert c.dominant_side == "SELL"

    def test_empty_returns_none(self):
        assert identify_cluster([], 0) is None

    def test_single_level(self):
        levels = make_levels([(100.0, 50, 50)])
        c = identify_cluster(levels, 100)
        assert c is not None
        assert c.yellow_poc == 100.0
        assert c.density == 1.0

    def test_two_levels(self):
        levels = make_levels([(100.0, 30, 40), (100.25, 20, 10)])
        c = identify_cluster(levels, 100)
        assert c is not None
        assert len(c.levels) == 2


# ══════════════════════════════════════════════════════════
# EMPTY ZONE TESTS
# ══════════════════════════════════════════════════════════

class TestEmptyZone:
    def test_finds_empty_zone(self):
        # Use 10% threshold — levels with 3 vol vs avg ~49 = 6% → below 10%
        zones = identify_empty_zones(SAMPLE_BAR, TOTAL_VOL, threshold_pct=0.10, min_consecutive=2)
        assert len(zones) >= 1
        # The 5248.00/5248.25 levels should be empty
        top_zone = zones[-1]
        assert top_zone.zone_high >= 5248.00

    def test_no_zones_in_full_bar(self):
        full = make_levels([(p, 50, 50) for p in [100.0, 100.25, 100.50, 100.75, 101.0]])
        zones = identify_empty_zones(full, 500, threshold_pct=0.05)
        assert len(zones) == 0

    def test_empty_input(self):
        assert identify_empty_zones([], 0) == []

    def test_min_consecutive(self):
        # Only 1 empty level — should not form zone with min_consecutive=2
        levels = make_levels([
            (100.0, 50, 50),
            (100.25, 0, 0),    # single empty
            (100.50, 50, 50),
        ])
        zones = identify_empty_zones(levels, 200, threshold_pct=0.05, min_consecutive=2)
        assert len(zones) == 0

    def test_zone_width(self):
        zones = identify_empty_zones(SAMPLE_BAR, TOTAL_VOL, threshold_pct=0.05, min_consecutive=2)
        if zones:
            for z in zones:
                assert z.zone_width_pt >= 0
                assert z.zone_high >= z.zone_low


# ══════════════════════════════════════════════════════════
# ENTRY EXECUTOR TESTS
# ══════════════════════════════════════════════════════════

class TestEntryExecutor:
    def test_long_entry_above_cluster(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL, "Variation")
        assert plan is not None
        assert plan.direction == "LONG"
        assert plan.entry_price > 5247.00  # above cluster

    def test_short_entry_below_cluster(self):
        plan = compute_entry_plan("SHORT", SAMPLE_BAR, TOTAL_VOL, "Variation")
        assert plan is not None
        assert plan.direction == "SHORT"
        assert plan.entry_price < 5247.00  # below cluster

    def test_stop_distance_within_bounds(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL, "Normal")
        assert plan is not None
        assert 1.0 <= plan.stop_distance_pt <= 3.75  # 4-15 ticks * 0.25

    def test_targets_per_day_type_variation(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL, "Variation")
        assert plan is not None
        assert plan.t1_r == 1.0
        assert plan.t2_r == 2.5
        assert plan.t3_r is None  # Variation has no T3
        assert plan.t1_price is not None
        assert plan.t2_price is not None

    def test_targets_per_day_type_trend_normal(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL, "Trend_Normal")
        assert plan is not None
        assert plan.t3_r == 4.0  # Trend Normal has T3
        assert plan.t3_price is not None
        assert plan.contracts == 2

    def test_targets_per_day_type_nontrend(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL, "Nontrend")
        assert plan is not None
        assert plan.t1_r == 0.5  # tiny target
        assert plan.t2_r is None
        assert plan.sizing_label == "MIN"
        assert plan.contracts == 1

    def test_all_6_day_types_have_config(self):
        for dt in ["Trend_Normal", "Trend_DD", "Variation", "Normal", "Neutral", "Nontrend"]:
            assert dt in DAY_TYPE_TARGETS

    def test_invalid_direction(self):
        plan = compute_entry_plan("SIDEWAYS", SAMPLE_BAR, TOTAL_VOL)
        assert plan is None

    def test_empty_levels(self):
        plan = compute_entry_plan("LONG", [], 0)
        assert plan is None

    def test_long_stop_below_entry(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL)
        assert plan is not None
        assert plan.stop_price < plan.entry_price

    def test_short_stop_above_entry(self):
        plan = compute_entry_plan("SHORT", SAMPLE_BAR, TOTAL_VOL)
        assert plan is not None
        assert plan.stop_price > plan.entry_price

    def test_t1_between_entry_and_t2(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL, "Variation")
        assert plan is not None
        if plan.t1_price and plan.t2_price:
            assert plan.entry_price < plan.t1_price < plan.t2_price

    def test_cluster_poc_in_plan(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL)
        assert plan is not None
        assert plan.cluster_poc == 5247.00

    def test_confidence_from_density(self):
        plan = compute_entry_plan("LONG", SAMPLE_BAR, TOTAL_VOL)
        assert plan is not None
        assert 0.0 < plan.confidence <= 1.0
