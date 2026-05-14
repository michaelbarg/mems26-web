"""W4-ζ — MFE peak 80% T2 triggers tighten."""
from backend.v9.services.layer4.mfe_peak_tighten import evaluate


def test_mfe_at_80_pct_t2_tightens():
    trade = {"entry": 5247.00, "stop": 5245.00, "t2": 5252.00,
             "current_price": 5251.00, "mfe": 5251.00, "direction": "LONG"}
    # T2 distance = 5, MFE = 4.0 → 80% → triggers
    # Lock 50% of MFE (4.0 * 0.5 = 2.0): new stop = 5247 + 2.0 = 5249.0
    result = evaluate(trade)
    assert result["action"] == "TIGHTEN_STOP"
    assert result["new_stop"] > trade["stop"]
    assert "reasoning_notes" in result


def test_mfe_below_threshold_no_action():
    trade = {"entry": 5247.00, "stop": 5245.00, "t2": 5251.00,
             "current_price": 5249.00, "mfe": 5249.00, "direction": "LONG"}
    # MFE = 2.0 / 4.0 = 50% < 80%
    result = evaluate(trade)
    assert result is None


def test_mfe_short_direction():
    trade = {"entry": 5252.00, "stop": 5254.00, "t2": 5247.00,
             "current_price": 5248.00, "mfe": 5248.00, "direction": "SHORT"}
    # T2 distance = 5, MFE = 4.0 = 80%
    # Lock 50% of 4.0 = 2.0: new stop = 5252 - 2.0 = 5250.0
    result = evaluate(trade)
    assert result["action"] == "TIGHTEN_STOP"
    assert result["new_stop"] < trade["stop"]


def test_new_stop_not_looser_than_current():
    """If calculated stop would be looser than current, skip."""
    trade = {"entry": 5247.00, "stop": 5249.50, "t2": 5251.00,
             "current_price": 5250.20, "mfe": 5250.20, "direction": "LONG"}
    # Lock 50% of MFE (3.2 * 0.5 = 1.6): new stop = 5248.6 < current 5249.5
    result = evaluate(trade)
    assert result is None  # don't loosen
