"""Tests for TPOSystem."""
from backend.v9.systems.tpo.tpo_system import TPOSystem, LETTERS
from backend.v9.systems.tpo.opening_classifier import classify_opening
from backend.v9.systems.base.trading_system import BaseV9TradingSystem


def test_tpo_extends_base():
    assert issubclass(TPOSystem, BaseV9TradingSystem)


def test_tpo_hydrate():
    sys = TPOSystem()
    r = sys.hydrate()
    assert r.success


def test_tpo_subscribes_5min():
    sys = TPOSystem()
    assert "5min" in sys.subscribed_bar_types()


def test_letter_assignment():
    assert LETTERS[0] == "A"
    assert LETTERS[5] == "F"
    assert LETTERS[12] == "M"


def test_poc_at_max_letter():
    sys = TPOSystem()
    sys.profile = {
        "100.00": ["A", "B", "C"],
        "100.25": ["A", "B", "C", "D", "E"],
        "100.50": ["A", "B"],
    }
    poc, vah, val = sys._compute_levels()
    assert poc == 100.25


def test_shape_D_balanced():
    sys = TPOSystem()
    sys.current_letter_idx = 5
    sys.profile = {f"{100 + i * 0.25:.2f}": ["A", "B"] for i in range(10)}
    sys.profile["101.25"] = ["A", "B", "C", "D", "E"]  # POC near center
    shape = sys._detect_shape()
    assert shape == "D"


def test_shape_b_poc_high():
    sys = TPOSystem()
    sys.current_letter_idx = 5
    sys.profile = {f"{100 + i * 0.25:.2f}": ["A"] for i in range(10)}
    sys.profile["102.25"] = ["A", "B", "C", "D", "E"]  # POC high
    shape = sys._detect_shape()
    assert shape == "b"


def test_opening_na_insufficient():
    result = classify_opening([], 0, 0)
    assert result == "NA"
