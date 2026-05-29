"""Regression: mapIdx clamp detection.

Simulates what the DLL does in Python to verify the clamp-detect logic
produces non-frozen output when cross-chart mapping repeats an index.
"""


def simulate_mapIdx(dll_bar_idx: int, mapping: dict) -> int:
    """Mirrors the Option-A mapIdx lambda logic."""
    mi = mapping.get(dll_bar_idx, dll_bar_idx)
    if dll_bar_idx > 0:
        mi_prev = mapping.get(dll_bar_idx - 1, dll_bar_idx - 1)
        if mi == mi_prev:
            return dll_bar_idx  # clamped: fall back
    return mi


def test_no_clamp_passes_through():
    mapping = {0: 0, 1: 1, 2: 2, 3: 3}
    assert simulate_mapIdx(3, mapping) == 3


def test_clamp_detected_returns_dll_idx():
    # bars 3,4,5 all map to woodies bar 2 (clamped)
    mapping = {1: 1, 2: 2, 3: 2, 4: 2, 5: 2}
    assert simulate_mapIdx(3, mapping) == 3  # clamped → fallback
    assert simulate_mapIdx(4, mapping) == 4  # clamped → fallback
    assert simulate_mapIdx(5, mapping) == 5  # clamped → fallback


def test_first_bar_no_prev_check():
    mapping = {0: 0}
    assert simulate_mapIdx(0, mapping) == 0


def test_non_frozen_tail_stays_mapped():
    mapping = {10: 8, 11: 9, 12: 10, 13: 11}
    assert simulate_mapIdx(13, mapping) == 11
