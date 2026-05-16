"""Tests for Quality Tier (S5 TPO location-based sizing)."""
from backend.v9.systems.five_min.quality_tier import get_quality_tier


def test_high_at_poc():
    tpo = {"poc": 5250.0, "vah": 5260.0, "val": 5240.0}
    tier, contracts = get_quality_tier(5250.5, tpo_data=tpo)
    assert tier == 'HIGH'
    assert contracts == 3


def test_medium_in_value_area():
    tpo = {"poc": 5250.0, "vah": 5260.0, "val": 5240.0}
    tier, contracts = get_quality_tier(5255.0, tpo_data=tpo)
    assert tier == 'MEDIUM'
    assert contracts == 2


def test_low_outside_value():
    tpo = {"poc": 5250.0, "vah": 5260.0, "val": 5240.0}
    tier, contracts = get_quality_tier(5275.0, tpo_data=tpo)
    assert tier == 'LOW'
    assert contracts == 0
