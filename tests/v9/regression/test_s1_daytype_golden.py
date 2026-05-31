"""S1-daytype Golden Regression — flag OFF must reproduce original classification."""

import json
from pathlib import Path

from backend.v9.systems.day_type.schemas import IBWidth, OpeningType
from backend.v9.systems.day_type.detector import classify_ib_width, calculate_confidence

GOLDEN = Path(__file__).parent / "golden" / "s1_daytype_constants.json"


def _load_golden():
    with GOLDEN.open() as f:
        return json.load(f)


def test_ib_width_enum_has_original_values():
    g = _load_golden()["ib_width_enum"]
    for name in g:
        assert hasattr(IBWidth, name), f"Missing IBWidth.{name}"


def test_classify_ib_width_defaults():
    g = _load_golden()["classify_ib_width_defaults"]
    assert classify_ib_width(10.0) == IBWidth.NARROW
    assert classify_ib_width(g["narrow_max"]) == IBWidth.MEDIUM
    assert classify_ib_width(g["medium_max"]) == IBWidth.MEDIUM
    assert classify_ib_width(g["medium_max"] + 1) == IBWidth.WIDE


def test_classify_ib_width_functional():
    assert classify_ib_width(14.9) == IBWidth.NARROW
    assert classify_ib_width(15.0) == IBWidth.MEDIUM
    assert classify_ib_width(25.0) == IBWidth.MEDIUM
    assert classify_ib_width(25.1) == IBWidth.WIDE


def test_confidence_base():
    g = _load_golden()["confidence_components"]
    assert calculate_confidence([], False, False) == g["base"]


def test_confidence_max():
    result = calculate_confidence(["T"] * 10, True, True)
    assert result == 1.0
