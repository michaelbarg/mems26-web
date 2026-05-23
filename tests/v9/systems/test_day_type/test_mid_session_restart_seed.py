"""P30 C1 — Regression tests for the mid-session restart IB-seed guard.

Investigation 651647eb (2026-05-19) found that a FastAPI restart in the
middle of RTH spawned a fresh DayTypeStateMachine which then locked
IB from a single 5-min bar (~5 pt → NARROW) and produced a wrong
`Nontrend` verdict for a day that ran a 79-pt range. The fix in
`backend/v9/api/v9/day_type_seed.py::maybe_seed_ib_from_tpo` seeds IB
from TPO's locked Initial Balance and jumps the machine to Stage.B1
when the restart happens after the IB window.

These tests pin the guard logic so we can never regress to that bug.
"""

from __future__ import annotations

import pytest

from backend.v9.api.v9.day_type_seed import maybe_seed_ib_from_tpo
from backend.v9.systems.day_type.schemas import IBWidth, Stage
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine


def _fresh_machine() -> DayTypeStateMachine:
    return DayTypeStateMachine()


# Sierra's TPO Initial Balance for the 2026-05-19 reference session.
_TPO_IB_HIGH = 7378.75
_TPO_IB_LOW = 7353.75
_TPO_IB_RANGE_PT = _TPO_IB_HIGH - _TPO_IB_LOW  # 25.00 — WIDE


def test_seeds_when_fresh_machine_post_ib_period_and_tpo_locked():
    """Happy path — the exact 2026-05-19 mid-RTH restart scenario."""
    m = _fresh_machine()

    seeded = maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,  # 13:30 ET — 4h into RTH
        tpo_ib_locked=True,
        tpo_ib_high=_TPO_IB_HIGH,
        tpo_ib_low=_TPO_IB_LOW,
    )

    assert seeded is True
    assert m.ib_high == _TPO_IB_HIGH
    assert m.ib_low == _TPO_IB_LOW
    assert m.ib_locked is True
    assert m.ib_class is not None
    assert m.ib_class.ib_range == pytest.approx(_TPO_IB_RANGE_PT)
    # 25.00 pt sits exactly on the NARROW/MEDIUM/WIDE thresholds; default
    # config (narrow<15, medium<=25) classifies it as MEDIUM.
    assert m.ib_class.ib_width == IBWidth.MEDIUM
    assert m.stage == Stage.B1


def test_does_not_seed_when_engine_already_running():
    """bar_count > 0 → engine has live state, never overwrite."""
    m = _fresh_machine()
    m.bar_count = 5

    seeded = maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,
        tpo_ib_locked=True,
        tpo_ib_high=_TPO_IB_HIGH,
        tpo_ib_low=_TPO_IB_LOW,
    )

    assert seeded is False
    assert m.ib_locked is False
    assert m.stage == Stage.A1


def test_does_not_seed_during_ib_window():
    """session_min <= ib_period_min → engine should still build IB itself."""
    m = _fresh_machine()

    seeded = maybe_seed_ib_from_tpo(
        machine=m,
        session_min=45,  # pre-10:30 ET
        tpo_ib_locked=True,
        tpo_ib_high=_TPO_IB_HIGH,
        tpo_ib_low=_TPO_IB_LOW,
    )

    assert seeded is False
    assert m.ib_locked is False
    assert m.stage == Stage.A1


def test_does_not_seed_when_tpo_ib_not_locked():
    """TPO not done with IB yet → no authoritative source to trust."""
    m = _fresh_machine()

    seeded = maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,
        tpo_ib_locked=False,
        tpo_ib_high=_TPO_IB_HIGH,
        tpo_ib_low=_TPO_IB_LOW,
    )

    assert seeded is False
    assert m.ib_locked is False


@pytest.mark.parametrize(
    "ib_h,ib_l",
    [
        (None, _TPO_IB_LOW),
        (_TPO_IB_HIGH, None),
        (None, None),
        (0.0, 0.0),
        (-78229.0, 7353.75),  # the uninitialized-memory value from DLL round 1
        (7353.75, 7378.75),  # inverted high < low
        (7378.75, 7378.75),  # zero range
    ],
)
def test_does_not_seed_on_invalid_tpo_inputs(ib_h, ib_l):
    """Never trust dirty TPO data — fall back to engine's own A1/A2/A3."""
    m = _fresh_machine()

    seeded = maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,
        tpo_ib_locked=True,
        tpo_ib_high=ib_h,
        tpo_ib_low=ib_l,
    )

    assert seeded is False
    assert m.ib_locked is False
    assert m.stage == Stage.A1


def test_seed_chooses_narrow_when_range_under_threshold():
    """Range < 15 → NARROW (matches config default narrow_max=15)."""
    m = _fresh_machine()

    seeded = maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,
        tpo_ib_locked=True,
        tpo_ib_high=7370.0,
        tpo_ib_low=7360.0,  # 10 pt range
    )

    assert seeded is True
    assert m.ib_class.ib_width == IBWidth.NARROW


def test_seed_chooses_wide_when_range_over_threshold():
    """Range > 25 → WIDE."""
    m = _fresh_machine()

    seeded = maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,
        tpo_ib_locked=True,
        tpo_ib_high=7400.0,
        tpo_ib_low=7350.0,  # 50 pt range
    )

    assert seeded is True
    assert m.ib_class.ib_width == IBWidth.WIDE


def test_seeded_machine_skips_a3_a4_on_next_process_bar():
    """End-to-end: after seeding, next bar must process at B1 — not A4."""
    from backend.v9.systems.day_type.schemas import BarInput

    m = _fresh_machine()
    maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,
        tpo_ib_locked=True,
        tpo_ib_high=_TPO_IB_HIGH,
        tpo_ib_low=_TPO_IB_LOW,
    )
    assert m.stage == Stage.B1

    bar = BarInput(
        ts=1779210000.0,
        session_min=245,
        open=7370.0,
        high=7372.5,
        low=7367.5,  # 5 pt — the single-bar trap from the bug
        close=7371.0,
        volume=100.0,
        ib_high=None,
        ib_low=None,
    )
    m.process_bar(bar)

    # The bug used to lock IB at ~5 pt NARROW from this single bar.
    # Post-fix, IB must remain TPO's MEDIUM 25 pt seeded values.
    assert m.ib_high == _TPO_IB_HIGH
    assert m.ib_low == _TPO_IB_LOW
    assert m.ib_class.ib_width == IBWidth.MEDIUM


def test_seed_populates_opening_so_b1_can_advance():
    """P31 §C followup: jumping to B1 without seeding ``machine.opening``
    left the machine permanently stuck at ``stage=B1, day_type=UNKNOWN``
    because ``_stage_b1`` returns early when ``self.opening is None``. The
    seed must populate a synthetic Opening (default INDETERMINATE → matrix
    falls through to Normal) so B1 can vote and B2-B6 progress as designed.
    """
    from backend.v9.systems.day_type.schemas import BarInput, DayType, OpeningType

    m = _fresh_machine()
    seeded = maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,
        tpo_ib_locked=True,
        tpo_ib_high=_TPO_IB_HIGH,
        tpo_ib_low=_TPO_IB_LOW,
    )
    assert seeded is True

    # The seed must leave the machine with a non-null opening so B1's guard
    # (``if self.opening is None or self.ib_class is None: return``) does
    # not abort the stage.
    assert m.opening is not None
    assert m.opening.opening_type == OpeningType.INDETERMINATE

    # Drive a bar through the machine and verify B1 actually voted (the
    # bug was that bar_count would tick but stage stayed at B1 and
    # day_type stayed at UNKNOWN forever).
    bar = BarInput(
        ts=1779210000.0,
        session_min=245,
        open=7370.0,
        high=7372.5,
        low=7367.5,
        close=7371.0,
        volume=100.0,
    )
    m.process_bar(bar)

    assert m.stage in (Stage.B2, Stage.B3, Stage.B4, Stage.B5, Stage.B6, Stage.C1, Stage.C2, Stage.C3), (
        f"machine stuck at {m.stage}; expected to advance past B1 after vote"
    )
    assert m.day_type != DayType.UNKNOWN, (
        "machine still UNKNOWN after process_bar; B1 never cast a vote"
    )
    # INDETERMINATE matrix entries all resolve to Normal at MEDIUM IB.
    assert len(m.vote_history) >= 1
    assert m.vote_history[0].day_type == DayType.Normal


def test_seeded_machine_produces_classification_consumable():
    """The full pipeline — seed → process_bar → to_classification() — must
    return a non-None DayTypeClassification so DayTypeConsumer can UPSERT
    into ``v9_day_type_history`` instead of silently producing no rows.
    Before this fix the live backend would produce zero upserts for the
    rest of the trading day after any mid-RTH restart.
    """
    from backend.v9.systems.day_type.schemas import BarInput

    m = _fresh_machine()
    maybe_seed_ib_from_tpo(
        machine=m,
        session_min=240,
        tpo_ib_locked=True,
        tpo_ib_high=_TPO_IB_HIGH,
        tpo_ib_low=_TPO_IB_LOW,
    )

    bar = BarInput(
        ts=1779210000.0,
        session_min=245,
        open=7370.0,
        high=7372.5,
        low=7367.5,
        close=7371.0,
        volume=100.0,
    )
    m.process_bar(bar)

    classification = m.to_classification()
    assert classification is not None, (
        "to_classification returned None — consumer would have nothing to UPSERT"
    )
    assert classification.day_type.value != "UNKNOWN"
    assert classification.opening_type == "INDETERMINATE"
    assert classification.ib_width_class == "MEDIUM"
