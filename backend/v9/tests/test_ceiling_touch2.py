"""T-328 §4: CEILING_TOUCH2_REJECT / FLOOR_TOUCH2_REJECT detector tests.

Geometry from 11.09: bars 11-12 (10:20/10:25 ET) had equal highs 7678.75.
Bar 12 closed 7674.75 < bar 11 close 7675.5 → rejection confirmed.
"""
from backend.v9.systems.ceiling_touch2 import detect_touch2


def _bar(h, l, c, o=None):
    return {"h": h, "l": l, "c": c, "o": o or c}


def test_ceiling_touch2_equal_peaks():
    """Equal peaks within tol → CEILING_TOUCH2_REJECT."""
    bars = [
        _bar(7670, 7660, 7668),     # bar 0 — context
        _bar(7675, 7665, 7672),     # bar 1 — context
        _bar(7678.75, 7673, 7675.5),  # bar 2 — TOUCH-1
        _bar(7678.75, 7673, 7674.75), # bar 3 — TOUCH-2 (closes BELOW bar 2 close)
    ]
    levels = {"vah": 7678.75, "ib_high": 7682.0}
    result = detect_touch2(bars, levels, atr=10.0, ib_width=18.75)
    assert result is not None
    assert result["state"] == "CEILING_TOUCH2_REJECT"
    assert result["p1"] == 7678.75
    assert result["p2"] == 7678.75
    assert result["confirm_close"] == 7674.75


def test_no_rejection_when_touch2_closes_above():
    """Mutation: touch-2 closes at or above touch-1 → no rejection."""
    bars = [
        _bar(7670, 7660, 7668),
        _bar(7675, 7665, 7672),
        _bar(7678.75, 7673, 7675.5),  # TOUCH-1
        _bar(7678.75, 7673, 7676.0),  # TOUCH-2 closes ABOVE → no rejection
    ]
    levels = {"vah": 7678.75, "ib_high": 7682.0}
    result = detect_touch2(bars, levels, atr=10.0, ib_width=18.75)
    assert result is None


def test_floor_touch2_mirror():
    """Floor mirror: equal lows, touch-2 closes above touch-1 close → FLOOR."""
    bars = [
        _bar(7600, 7590, 7595),       # context — high above edge
        _bar(7595, 7593, 7594),        # context
        _bar(7592, 7585.5, 7587),      # TOUCH-1 (low near VAL, closes low)
        _bar(7593, 7585.5, 7591),      # TOUCH-2 (equal low, closes ABOVE touch-1 = rejection)
    ]
    levels = {"val": 7585.5, "ib_low": 7583.0}
    result = detect_touch2(bars, levels, atr=10.0, ib_width=18.75)
    assert result is not None
    assert result["state"] == "FLOOR_TOUCH2_REJECT"
    assert result["confirm_close"] == 7591


def test_peaks_too_far_from_edge():
    """Peak far from any edge → no detection."""
    bars = [
        _bar(7650, 7640, 7645),
        _bar(7655, 7645, 7650),
        _bar(7658, 7650, 7655),
        _bar(7658, 7650, 7653),
    ]
    levels = {"vah": 7680.0, "ib_high": 7682.0}
    result = detect_touch2(bars, levels, atr=10.0, ib_width=18.75)
    assert result is None


def test_dedup_key_prevents_refire():
    """Same event should not fire twice."""
    bars = [
        _bar(7670, 7660, 7668),
        _bar(7675, 7665, 7672),
        _bar(7678.75, 7673, 7675.5),
        _bar(7678.75, 7673, 7674.75),
    ]
    levels = {"vah": 7678.75}
    r1 = detect_touch2(bars, levels, atr=10.0)
    assert r1 is not None
    # Fire again with already_fired containing the key → None
    r2 = detect_touch2(bars, levels, atr=10.0, already_fired={r1["key"]})
    assert r2 is None
