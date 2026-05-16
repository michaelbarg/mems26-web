"""Tests for Confluence count (Tree V3.3 §Q6 · max 4)."""
from backend.v9.systems.five_min.confluence import compute_confluence


def _directional_bars():
    """Clean uptrend bars (not choppy)."""
    return [
        {"o": 5250, "h": 5253, "l": 5249.5, "c": 5252.5},
        {"o": 5252.5, "h": 5256, "l": 5252, "c": 5255.5},
        {"o": 5255.5, "h": 5259, "l": 5255, "c": 5258.5},
    ]


def test_max_confluence_4():
    """All factors align → max 4."""
    kz = {"current_zone": {"name": "NY_PRIME", "edge_class": "high"}}
    score = compute_confluence(
        "LONG", _directional_bars(),
        opening_type="OPEN_DRIVE",
        killzone_data=kz,
        near_reference_line=True,
    )
    assert score == 4


def test_base_only_1():
    """No extras → base 1."""
    kz = {"current_zone": {"name": "LUNCH", "edge_class": "low"}}
    score = compute_confluence(
        "SHORT", _directional_bars(),
        opening_type="OPEN_DRIVE",  # counter-direction → no +1
        killzone_data=kz,
        near_reference_line=False,
    )
    assert score == 1  # base only (drive=LONG direction, pattern=SHORT → skip +1)


def test_choppy_subtracts():
    """Choppy opening → -1."""
    choppy_bars = [
        {"o": 5250, "h": 5251, "l": 5249, "c": 5250.5},
        {"o": 5250.5, "h": 5251, "l": 5249, "c": 5249.5},
        {"o": 5249.5, "h": 5251, "l": 5249, "c": 5250.5},
        {"o": 5250.5, "h": 5251, "l": 5249, "c": 5249.5},
        {"o": 5249.5, "h": 5251, "l": 5249, "c": 5250.5},
        {"o": 5250.5, "h": 5251, "l": 5249, "c": 5249.5},
    ]
    kz = {"current_zone": {"name": "LUNCH", "edge_class": "low"}}
    score = compute_confluence(
        "LONG", choppy_bars,
        opening_type=None,
        killzone_data=kz,
    )
    # base=1 + no align + no kz + no ref - choppy = 0 (clamped)
    assert score == 0


def test_clamped_at_zero():
    """Score never goes negative."""
    choppy = [
        {"o": 5250, "h": 5250.5, "l": 5249.5, "c": 5249.75},
        {"o": 5249.75, "h": 5250.5, "l": 5249.5, "c": 5250.25},
        {"o": 5250.25, "h": 5250.5, "l": 5249.5, "c": 5249.75},
        {"o": 5249.75, "h": 5250.5, "l": 5249.5, "c": 5250.25},
        {"o": 5250.25, "h": 5250.5, "l": 5249.5, "c": 5249.75},
        {"o": 5249.75, "h": 5250.5, "l": 5249.5, "c": 5250.25},
    ]
    kz = {"current_zone": {"name": "AFTER_HOURS"}}
    score = compute_confluence("SHORT", choppy, killzone_data=kz)
    assert score >= 0
