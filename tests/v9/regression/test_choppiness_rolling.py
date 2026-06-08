"""Choppiness scorer uses the LAST max_bars, not the first — rolling window.

Bug: bars[:max_bars] scored the oldest bars in the buffer, never updating.
Fix: bars[-max_bars:] scores the most recent bars (rolling).
"""
from backend.v9.systems.five_min.choppiness import compute_choppiness


def _make_bars(n, directional=True, base=7400.0):
    """Make n bars. directional=True: clean uptrend. False: choppy."""
    bars = []
    for i in range(n):
        if directional:
            o = base + i * 2.0
            c = o + 1.5
            bars.append({"o": o, "h": c + 0.5, "l": o - 0.25, "c": c})
        else:
            # Alternating red/green, overlapping
            if i % 2 == 0:
                o, c = base, base + 0.5
            else:
                o, c = base + 0.5, base
            bars.append({"o": o, "h": base + 1.0, "l": base - 0.5, "c": c})
    return bars


def test_rolling_window_uses_last_bars():
    """If we pass 14 bars where the first 6 are choppy and last 6 are
    directional, the score should reflect the LAST 6 (directional = low)."""
    choppy_bars = _make_bars(8, directional=False)
    directional_bars = _make_bars(6, directional=True, base=7420.0)
    all_bars = choppy_bars + directional_bars  # 14 bars

    score = compute_choppiness(all_bars, max_bars=6)
    # Score should be LOW because the last 6 bars are directional
    assert score < 50, f"Expected low score for directional tail, got {score}"


def test_old_bug_would_score_first_bars():
    """Verify that if we reversed (took first 6), the score would be high."""
    choppy_bars = _make_bars(8, directional=False)
    directional_bars = _make_bars(6, directional=True, base=7420.0)
    all_bars = choppy_bars + directional_bars

    # Manually score the first 6 (the old bug behavior)
    first_6 = all_bars[:6]
    old_score = compute_choppiness(first_6, max_bars=6)
    # The first 6 bars are choppy → should be HIGH
    assert old_score > 50, f"Expected high score for choppy head, got {old_score}"


def test_min_bars_returns_neutral():
    """Fewer than min_bars → neutral 50."""
    assert compute_choppiness([{"o": 1, "h": 2, "l": 0, "c": 1}]) == 50.0
    assert compute_choppiness([]) == 50.0


def test_directional_bars_low_score():
    """Clean uptrend → low choppiness."""
    bars = _make_bars(6, directional=True)
    score = compute_choppiness(bars)
    assert score < 40, f"Expected low score for clean trend, got {score}"


def test_choppy_bars_high_score():
    """Alternating bars → high choppiness."""
    bars = _make_bars(6, directional=False)
    score = compute_choppiness(bars)
    assert score > 30, f"Expected higher score for choppy market, got {score}"
