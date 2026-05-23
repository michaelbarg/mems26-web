"""W3-gamma -- Targets per Day Type table per V3 Layer 4"""
import sys
sys.path.insert(0, '/Users/michael/Downloads/mems26_web_git')

from backend.v9.systems.day_type.targets_table import get_targets, DAY_TYPES


def test_all_seven_types_present():
    assert DAY_TYPES == {
        "Trend_Normal", "Trend_DD", "Variation",
        "Normal", "Neutral_Extreme", "Neutral_Center",
        "Nontrend",
    }


def test_trend_normal_no_time_stop():
    t = get_targets("Trend_Normal")
    assert t is not None
    assert t["t1"] == "1R"
    assert "2R" in t["t2"] and "TPO" in t["t2"]
    assert t["time_stop_minutes"] is None
    assert t["contracts"] == 3


def test_trend_dd_90min():
    t = get_targets("Trend_DD")
    assert t["t1_r"] == 1.0
    assert t["time_stop_minutes"] == 90
    assert t["t3"] == "4R cap"


def test_variation_60min():
    t = get_targets("Variation")
    assert t["t2_r"] == 2.5
    assert t["time_stop_minutes"] == 60
    assert t["trail_after_t2"] is True


def test_normal_poc_target():
    t = get_targets("Normal")
    assert t["t2"] == "POC"
    assert t["t3"] is None
    assert t["time_stop_minutes"] == 30


def test_neutral_extreme_target():
    t = get_targets("Neutral_Extreme")
    assert t["t2"] == "extreme"
    assert t["t3"] is None
    assert t["time_stop_minutes"] == 45


def test_nontrend_strict():
    t = get_targets("Nontrend")
    assert t["no_trade"] is True
    assert t["t1"] is None
    assert t["t2"] is None
    assert t["t3"] is None
    assert t["time_stop_minutes"] is None
    assert t["contracts"] == 0


def test_uppercase_alias():
    t = get_targets("TREND_NORMAL")
    assert t is not None
    assert t["t1"] == "1R"


def test_unknown_returns_none():
    t = get_targets("BOGUS_TYPE")
    assert t is None


def test_every_target_has_reasoning_notes():
    for dt in DAY_TYPES:
        t = get_targets(dt)
        assert t is not None
        assert "reasoning_notes" in t and len(t["reasoning_notes"]) > 0, f"{dt} missing reasoning_notes"
