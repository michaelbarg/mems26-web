"""W4-ζ — Day Type targets verify."""
from backend.v9.services.layer4.day_type_targets_verify import evaluate


def test_mismatch_warns():
    trade = {"day_type_at_entry": "Trend_Normal", "direction": "LONG"}
    result = evaluate(trade, "Nontrend")
    assert result is not None
    assert result["action"] == "WARN"
    assert result["more_restrictive"] is True  # Nontrend = 20min vs Trend_Normal = None
    assert "reasoning_notes" in result


def test_same_day_type_no_action():
    trade = {"day_type_at_entry": "Normal", "direction": "LONG"}
    result = evaluate(trade, "Normal")
    assert result is None


def test_case_insensitive():
    trade = {"day_type_at_entry": "TREND_NORMAL", "direction": "LONG"}
    result = evaluate(trade, "TREND_NORMAL")
    assert result is None
