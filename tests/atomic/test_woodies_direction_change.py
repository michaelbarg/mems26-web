"""W3-β — Direction Change Detector (TCCI crosses CCI14)"""
import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
from backend.v9.systems.woodies.direction_change_detector import detect


def test_tcci_crosses_above_cci14():
    history = [
        {"cci_14": 50, "tcci": 45},   # tcci below
        {"cci_14": 55, "tcci": 60},    # tcci crossed above
    ]
    event = detect(history)
    assert event is not None
    assert event["type"] == "DIRECTION_CHANGE"
    assert event["direction"] == "BULLISH"
    assert "reasoning_notes" in event
    assert "ABOVE" in event["reasoning_notes"]


def test_tcci_crosses_below_cci14():
    history = [
        {"cci_14": 50, "tcci": 60},    # tcci above
        {"cci_14": 55, "tcci": 45},    # tcci crossed below
    ]
    event = detect(history)
    assert event is not None
    assert event["direction"] == "BEARISH"
    assert "BELOW" in event["reasoning_notes"]


def test_no_cross_when_same_side():
    history = [
        {"cci_14": 50, "tcci": 60},
        {"cci_14": 55, "tcci": 70},    # still above, no cross
    ]
    event = detect(history)
    assert event is None


def test_none_when_insufficient_data():
    event = detect([{"cci_14": 50, "tcci": 60}])
    assert event is None


def test_none_when_missing_fields():
    history = [
        {"cci_14": 50},               # missing tcci
        {"cci_14": 55, "tcci": 60},
    ]
    event = detect(history)
    assert event is None  # explicit None, no fallback per §6.7


if __name__ == "__main__":
    test_tcci_crosses_above_cci14()
    test_tcci_crosses_below_cci14()
    test_no_cross_when_same_side()
    test_none_when_insufficient_data()
    test_none_when_missing_fields()
    print("✅ All 5 direction change tests passed")
