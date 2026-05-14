"""W4-ζ — SWI red triggers stop tighten."""
from backend.v9.services.layer4.swi_tighten import evaluate


def test_swi_red_tightens_long_stop():
    trade = {"direction": "LONG", "current_price": 5247.50, "stop_price": 5245.00}
    swi = {"value": -250, "color": "red"}
    result = evaluate(trade, swi)
    assert result["action"] == "TIGHTEN_STOP"
    assert result["new_stop"] > trade["stop_price"]
    assert abs(result["new_stop"] - 5245.625) < 0.01  # 5245.00 + 0.625
    assert "reasoning_notes" in result


def test_swi_red_tightens_short_stop():
    trade = {"direction": "SHORT", "current_price": 5245.00, "stop_price": 5247.50}
    swi = {"value": -300, "color": "red"}
    result = evaluate(trade, swi)
    assert result["action"] == "TIGHTEN_STOP"
    assert result["new_stop"] < trade["stop_price"]


def test_swi_green_no_action():
    trade = {"direction": "LONG", "current_price": 5247.50, "stop_price": 5245.00}
    swi = {"value": 250, "color": "green"}
    result = evaluate(trade, swi)
    assert result is None


def test_swi_yellow_no_action():
    trade = {"direction": "LONG", "current_price": 5247.50, "stop_price": 5245.00}
    swi = {"value": 100, "color": "yellow"}
    result = evaluate(trade, swi)
    assert result is None
