"""W2b.2 — Empty zone detection"""
from backend.v9.layer3.cluster import PriceLevel
from backend.v9.layer3.empty_zone import identify_empty_zones

def test_empty_zone_below_cluster_for_long():
    levels = [
        PriceLevel(price=5246.00, bid_vol=5, ask_vol=5),
        PriceLevel(price=5246.25, bid_vol=3, ask_vol=2),
        PriceLevel(price=5246.50, bid_vol=8, ask_vol=5),
        PriceLevel(price=5246.75, bid_vol=100, ask_vol=80),
        PriceLevel(price=5247.00, bid_vol=200, ask_vol=150),
        PriceLevel(price=5247.25, bid_vol=400, ask_vol=300),
        PriceLevel(price=5247.50, bid_vol=250, ask_vol=180),
    ]
    zones = identify_empty_zones(levels)
    assert len(zones) >= 1
    assert zones[0].zone_low <= 5246.25
