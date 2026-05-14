"""W2a — 15-tick reversal bar + VAP math validation"""

TICK_SIZE = 0.25  # MES
REVERSAL_TICKS = 15
THRESHOLD = REVERSAL_TICKS * TICK_SIZE  # 3.75 points

def test_reversal_threshold_math():
    """15 ticks * 0.25 = 3.75 points threshold"""
    assert THRESHOLD == 3.75

def test_vap_poc_max_volume_level():
    """POC = price level with maximum total volume"""
    from backend.v9.services.footprint.vap_recompute import compute_bar_vap
    cells = [
        {"price": 5247.00, "bid_volume": 100, "ask_volume": 150},  # 250
        {"price": 5247.25, "bid_volume": 200, "ask_volume": 100},  # 300 ← POC
        {"price": 5247.50, "bid_volume": 300, "ask_volume": 200},  # 500 ← POC
        {"price": 5247.75, "bid_volume": 80, "ask_volume": 70},    # 150
    ]
    vap = compute_bar_vap(cells)
    assert vap["poc"] == 5247.50  # highest total volume (500)
    assert vap["total_volume"] == 1200

def test_vap_70_percent_value_area():
    """VAH/VAL expand from POC until cumulative >= 70% total"""
    from backend.v9.services.footprint.vap_recompute import compute_bar_vap
    cells = [
        {"price": 5246.50, "bid_volume": 10, "ask_volume": 10},    # 20
        {"price": 5246.75, "bid_volume": 50, "ask_volume": 50},    # 100
        {"price": 5247.00, "bid_volume": 100, "ask_volume": 150},  # 250
        {"price": 5247.25, "bid_volume": 200, "ask_volume": 100},  # 300
        {"price": 5247.50, "bid_volume": 300, "ask_volume": 200},  # 500 ← POC
        {"price": 5247.75, "bid_volume": 80, "ask_volume": 70},    # 150
        {"price": 5248.00, "bid_volume": 10, "ask_volume": 10},    # 20
    ]
    vap = compute_bar_vap(cells)
    assert vap["poc"] == 5247.50
    # 70% of 1340 = 938. POC=500, +5247.25(300)=800, +5247.00(250)=1050 >= 938
    assert vap["val"] <= 5247.00
    assert vap["vah"] >= 5247.50

def test_existing_reversal_15_in_dll():
    """DLL already exports tick_reversal_15.json"""
    import os
    export_dir = "/Users/michael/SierraChart_Data/v9_export"
    path = os.path.join(export_dir, "tick_reversal_15.json")
    assert os.path.exists(path), f"tick_reversal_15.json not found at {path}"
    import json
    with open(path) as f:
        d = json.load(f)
    assert d.get("type") == "tick_reversal"
    assert d.get("tick_count") == 15
    bars = d.get("bars", [])
    assert len(bars) > 0, "No reversal bars in export"
    # Each bar should have OHLC + ask_vol + bid_vol
    b = bars[0]
    for key in ["o", "h", "l", "c", "vol", "ask_vol", "bid_vol", "delta"]:
        assert key in b, f"Missing key {key} in reversal bar"
