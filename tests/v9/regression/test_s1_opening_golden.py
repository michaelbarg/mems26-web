"""S1-opening Golden Regression — flag OFF must reproduce original detection logic."""

import json
from pathlib import Path

from backend.v9.systems.day_type.schemas import BarInput, OpeningType

GOLDEN = Path(__file__).parent / "golden" / "s1_opening_constants.json"


def _load_golden():
    with GOLDEN.open() as f:
        return json.load(f)


def test_opening_type_enum_values():
    g = _load_golden()["opening_types"]
    for name in g:
        assert hasattr(OpeningType, name), f"Missing OpeningType.{name}"


def test_drive_detection():
    """Strong directional move → OPEN_DRIVE."""
    from backend.v9.systems.day_type.detector import detect_opening_type
    bars = [
        BarInput(ts=1, session_min=0, open=5200, high=5205, low=5200, close=5205),
        BarInput(ts=2, session_min=5, open=5205, high=5210, low=5205, close=5210),
        BarInput(ts=3, session_min=10, open=5210, high=5215, low=5210, close=5215),
    ]
    ot, direction, conf = detect_opening_type(bars)
    assert ot == OpeningType.OPEN_DRIVE
    assert direction == "UP"
    assert conf >= 0.9


def test_auction_in_detection():
    """Rotational bars inside prior range → OPEN_AUCTION_IN."""
    from backend.v9.systems.day_type.detector import detect_opening_type
    bars = [
        BarInput(ts=1, session_min=0, open=5200, high=5202, low=5198, close=5199,
                 pd_high=5210, pd_low=5190),
        BarInput(ts=2, session_min=5, open=5199, high=5201, low=5197, close=5200,
                 pd_high=5210, pd_low=5190),
    ]
    ot, direction, conf = detect_opening_type(bars)
    assert ot == OpeningType.OPEN_AUCTION_IN


def test_test_drive_detection():
    """Move, pullback, continuation → OPEN_TEST_DRIVE."""
    from backend.v9.systems.day_type.detector import detect_opening_type
    bars = [
        BarInput(ts=1, session_min=0, open=5200, high=5210, low=5200, close=5210),
        BarInput(ts=2, session_min=5, open=5210, high=5210, low=5206, close=5206),
        BarInput(ts=3, session_min=10, open=5206, high=5215, low=5206, close=5215),
    ]
    ot, direction, conf = detect_opening_type(bars)
    assert ot == OpeningType.OPEN_TEST_DRIVE
    assert direction == "UP"
