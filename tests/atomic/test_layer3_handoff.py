"""W2b.3 — Setup→Entry handoff"""
from backend.v9.services.layer3.handoff import refine_entry

def test_handoff_long_entry_above_cluster():
    setup = {"direction": "LONG", "signal_price": 5247.25, "system_id": 2}
    bar = {"open": 5246.00, "high": 5248.00, "low": 5246.00, "close": 5247.50}
    cells = [
        {"price": 5246.00, "bid_volume": 5, "ask_volume": 5},
        {"price": 5246.25, "bid_volume": 3, "ask_volume": 2},
        {"price": 5246.50, "bid_volume": 8, "ask_volume": 5},
        {"price": 5247.00, "bid_volume": 200, "ask_volume": 150},
        {"price": 5247.25, "bid_volume": 400, "ask_volume": 300},
        {"price": 5247.50, "bid_volume": 250, "ask_volume": 180},
    ]
    result = refine_entry(setup, bar, cells)
    assert result is not None
    assert result["entry_price"] > result["cluster_top"]
    assert result["stop_price"] < result["cluster_bottom"]
    assert result["entry_bar_type"] == "reversal_15"
    assert "reasoning_notes" in result

def test_handoff_rejects_when_no_cells():
    setup = {"direction": "LONG", "signal_price": 5247.00, "system_id": 2}
    bar = {"open": 5247.00, "high": 5247.25, "low": 5247.00, "close": 5247.25}
    result = refine_entry(setup, bar, [])
    assert result is None
