"""W2b.1 — Cluster detection from footprint cells"""
from backend.v9.layer3.cluster import identify_cluster, PriceLevel

def test_cluster_at_poc():
    levels = [
        PriceLevel(price=5247.00, bid_vol=50, ask_vol=50),
        PriceLevel(price=5247.25, bid_vol=200, ask_vol=150),
        PriceLevel(price=5247.50, bid_vol=400, ask_vol=300),
        PriceLevel(price=5247.75, bid_vol=150, ask_vol=100),
    ]
    result = identify_cluster(levels)
    assert result is not None
    assert result.yellow_poc == 5247.50
    assert result.cluster_low >= 5247.25
    assert result.cluster_high <= 5247.75
    assert result.density > 0.5

def test_cluster_returns_none_when_no_cells():
    result = identify_cluster([])
    assert result is None
