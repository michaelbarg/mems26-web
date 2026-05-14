"""W4-δ — UFL/UFH detection per V3 Layer 2"""
import sys
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
from backend.v9.systems.tpo.levels import detect_ufl_ufh


class FakeLevel:
    def __init__(self, price, count):
        self.price = price
        self.count = count


def test_ufh_single_letter_at_high():
    levels = {
        "5247.00": FakeLevel(5247.00, 4),
        "5247.25": FakeLevel(5247.25, 3),
        "5247.50": FakeLevel(5247.50, 2),
        "5248.00": FakeLevel(5248.00, 1),  # single at high
    }
    result = detect_ufl_ufh(levels, session_low=5247.00, session_high=5248.00)
    assert result["ufh"] == 5248.00
    assert result["ufl"] is None  # low has 4 letters
    assert "UFH" in result["reasoning_notes"]


def test_ufl_single_letter_at_low():
    levels = {
        "5247.00": FakeLevel(5247.00, 1),  # single at low
        "5247.25": FakeLevel(5247.25, 3),
        "5248.00": FakeLevel(5248.00, 4),
    }
    result = detect_ufl_ufh(levels, session_low=5247.00, session_high=5248.00)
    assert result["ufl"] == 5247.00
    assert result["ufh"] is None  # high has 4 letters
    assert "UFL" in result["reasoning_notes"]


def test_no_ufl_ufh_when_multiple_letters():
    levels = {
        "5247.00": FakeLevel(5247.00, 3),
        "5248.00": FakeLevel(5248.00, 2),
    }
    result = detect_ufl_ufh(levels, session_low=5247.00, session_high=5248.00)
    assert result["ufl"] is None
    assert result["ufh"] is None
    assert "No UFL/UFH" in result["reasoning_notes"]


def test_both_ufl_and_ufh():
    levels = {
        "5247.00": FakeLevel(5247.00, 1),  # single at low
        "5247.50": FakeLevel(5247.50, 5),
        "5248.00": FakeLevel(5248.00, 1),  # single at high
    }
    result = detect_ufl_ufh(levels, session_low=5247.00, session_high=5248.00)
    assert result["ufl"] == 5247.00
    assert result["ufh"] == 5248.00


def test_none_with_empty_data():
    result = detect_ufl_ufh({}, None, None)
    assert result["ufl"] is None
    assert result["ufh"] is None


if __name__ == "__main__":
    test_ufh_single_letter_at_high()
    test_ufl_single_letter_at_low()
    test_no_ufl_ufh_when_multiple_letters()
    test_both_ufl_and_ufh()
    test_none_with_empty_data()
    print("✅ All 5 UFL/UFH tests passed")
