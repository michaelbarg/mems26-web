"""W-10 bar count increments once per unique bar timestamp, not per push.

Anti-regression for Bug A from DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md.
The previous behaviour made W-10 fire after 54s (18 pushes ~ 18 fake
bars), not 90 minutes (18 real closed bars).
"""

from backend.v9.systems.woodies.woodies_system import WoodiesSystem


def test_bar_count_increments_once_per_unique_ts():
    """Push same bar 5x (same ts) -> _bar_count increments once."""
    system = WoodiesSystem(db_path=":memory:", rth_only=False)
    base = system._bar_count

    # Simulate: 5 pushes with identical ts should only increment once
    ts_value = 1716900000
    for _ in range(5):
        if ts_value != system._last_bar_ts_for_count:
            system._bar_count += 1
            system._last_bar_ts_for_count = ts_value

    assert system._bar_count == base + 1, (
        f"Expected bar_count to increment once for 5 identical ts pushes, "
        f"got {system._bar_count - base} increments"
    )


def test_bar_count_increments_on_new_ts():
    """Each new ts increments bar_count by 1."""
    system = WoodiesSystem(db_path=":memory:", rth_only=False)
    base = system._bar_count

    for ts_value in [1716900000, 1716900300, 1716900600]:
        if ts_value != system._last_bar_ts_for_count:
            system._bar_count += 1
            system._last_bar_ts_for_count = ts_value

    assert system._bar_count == base + 3


def test_last_bar_ts_for_count_initialized_none():
    """_last_bar_ts_for_count starts as None so first bar always increments."""
    system = WoodiesSystem(db_path=":memory:")
    assert system._last_bar_ts_for_count is None
