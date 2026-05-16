"""Tests for Opening Choppiness scorer (Tree V3.3 §Q4)."""
from backend.v9.systems.five_min.choppiness import compute_choppiness, is_choppy


def test_directional_low_score():
    """Clean uptrend → low choppiness."""
    bars = [
        {"o": 5250, "h": 5252, "l": 5249.5, "c": 5251.5},
        {"o": 5251.5, "h": 5254, "l": 5251, "c": 5253.5},
        {"o": 5253.5, "h": 5256, "l": 5253, "c": 5255.5},
        {"o": 5255.5, "h": 5258, "l": 5255, "c": 5257.5},
    ]
    score = compute_choppiness(bars)
    assert score < 40  # directional = low choppiness


def test_choppy_high_score():
    """Alternating red/green doji bars → high choppiness."""
    bars = [
        {"o": 5250, "h": 5251, "l": 5249, "c": 5250.5},  # green
        {"o": 5250.5, "h": 5251, "l": 5249, "c": 5249.5},  # red
        {"o": 5249.5, "h": 5251, "l": 5249, "c": 5250.5},  # green
        {"o": 5250.5, "h": 5251, "l": 5249, "c": 5249.5},  # red
    ]
    score = compute_choppiness(bars)
    assert score > 30  # choppy


def test_insufficient_bars_neutral():
    bars = [{"o": 5250, "h": 5252, "l": 5249, "c": 5251}]
    assert compute_choppiness(bars) == 50.0  # neutral
