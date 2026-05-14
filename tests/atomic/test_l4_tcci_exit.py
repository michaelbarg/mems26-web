"""W4-ζ — TCCI cross CCI14 triggers exit."""
from backend.v9.services.layer4.tcci_cross_exit import evaluate


def test_tcci_bearish_exits_long():
    trade = {"direction": "LONG"}
    event = {"type": "DIRECTION_CHANGE", "direction": "BEARISH",
             "reasoning_notes": "TCCI crossed below CCI14"}
    result = evaluate(trade, event)
    assert result["action"] == "EXIT"
    assert result["rule"] == "TCCI_CROSS"
    assert "reasoning_notes" in result


def test_tcci_bullish_exits_short():
    trade = {"direction": "SHORT"}
    event = {"type": "DIRECTION_CHANGE", "direction": "BULLISH",
             "reasoning_notes": "TCCI crossed above CCI14"}
    result = evaluate(trade, event)
    assert result["action"] == "EXIT"


def test_tcci_bullish_no_exit_for_long():
    """Same-direction change doesn't trigger exit."""
    trade = {"direction": "LONG"}
    event = {"type": "DIRECTION_CHANGE", "direction": "BULLISH",
             "reasoning_notes": "TCCI crossed above CCI14"}
    result = evaluate(trade, event)
    assert result is None


def test_no_event_no_exit():
    trade = {"direction": "LONG"}
    result = evaluate(trade, None)
    assert result is None
