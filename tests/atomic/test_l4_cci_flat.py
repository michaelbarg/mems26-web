"""W4-ζ — CCI flat 3+ bars triggers stop tighten."""
from backend.v9.services.layer4.cci_flat_tighten import evaluate


def test_cci_flat_tightens():
    trade = {"direction": "LONG", "current_price": 5250.00, "stop_price": 5247.00}
    cci = [45.0, 48.0, 50.0]  # all within ±10
    result = evaluate(trade, cci)
    assert result is not None
    assert result["action"] == "TIGHTEN_STOP"
    assert result["new_stop"] > trade["stop_price"]
    assert "reasoning_notes" in result


def test_cci_volatile_no_action():
    trade = {"direction": "LONG", "current_price": 5250.00, "stop_price": 5247.00}
    cci = [45.0, 80.0, 50.0]  # 35-point swing
    result = evaluate(trade, cci)
    assert result is None


def test_cci_insufficient_bars():
    trade = {"direction": "LONG", "current_price": 5250.00, "stop_price": 5247.00}
    cci = [45.0, 48.0]  # only 2
    result = evaluate(trade, cci)
    assert result is None
