"""Regression: S1 provisional day_type @ ~30 min (S1_PROVISIONAL_DAYTYPE).

Root (06-09/06-10 live data): the day-type machine classified day_type only at
B1 (post IB-lock @ ib_period_min = 60 min). Both S2 and S4 read
``ib_class.ib_width``, which was None until lock -> both blind for the first
hour -> day_type=UNKNOWN @ 30 min (the recurring failure Michael flagged).

These tests call the PRODUCTION DayTypeStateMachine.process_bar (no duplicated
logic). RED-on-revert: delete ``_maybe_provisional_classify`` (or its call site)
and ``test_provisional_fires_at_30min_when_flag_on`` FAILS — day_type stays
UNKNOWN, exactly the pre-fix behaviour.
"""
import pytest

from backend.v9.systems.day_type.state_machine import DayTypeStateMachine
from backend.v9.systems.day_type.schemas import BarInput, DayType


def _bar(sm, o, h, l, c, rth=True, ibh=None, ibl=None):
    return BarInput(ts=0.0, session_min=sm, is_rth=rth, open=o, high=h, low=l,
                    close=c, volume=1000, pd_high=7480, pd_low=7400,
                    pd_close=7450, ib_high=ibh, ib_low=ibl)


def _drive_to_30min(machine, with_sierra_ib=True):
    """A1 -> A2 (opening @ 15m) -> A3 with a developing Sierra IB, to session_min=30."""
    machine.process_bar(_bar(0, 7458, 7460, 7456, 7458, rth=False))
    machine.process_bar(_bar(5, 7458, 7470, 7457, 7469))
    machine.process_bar(_bar(10, 7469, 7482, 7468, 7481))
    machine.process_bar(_bar(15, 7481, 7491, 7480, 7490))   # opening set @ 15m
    ibh, ibl = (7491, 7458) if with_sierra_ib else (None, None)
    machine.process_bar(_bar(20, 7490, 7491, 7470, 7475, ibh=ibh, ibl=ibl))
    machine.process_bar(_bar(25, 7475, 7480, 7465, 7470, ibh=ibh, ibl=ibl))
    machine.process_bar(_bar(30, 7470, 7475, 7460, 7465, ibh=ibh, ibl=ibl))


@pytest.fixture
def flag(monkeypatch):
    def _set(v):
        if v is None:
            monkeypatch.delenv("S1_PROVISIONAL_DAYTYPE", raising=False)
        else:
            monkeypatch.setenv("S1_PROVISIONAL_DAYTYPE", v)
    return _set


def test_provisional_fires_at_30min_when_flag_on(flag):
    flag("1")
    m = DayTypeStateMachine()
    _drive_to_30min(m)
    # opening detected at 15 min (3 RTH bars)
    assert m.opening is not None and m.opening.opening_type.value == "OPEN_DRIVE"
    # provisional day_type present at 30 min — the whole point of the fix
    assert m.day_type != DayType.UNKNOWN
    assert m.ib_class is not None and m.ib_class.ib_width.value != "UNKNOWN"
    # honest: NOT a real lock
    assert m.ib_locked is False
    assert m.lock_state == "PENDING"
    assert m.meta.get("provisional_day_type") is True


def test_no_provisional_when_flag_off(flag):
    """RED-on-revert anchor: flag OFF (code default) -> UNKNOWN @ 30 min."""
    flag(None)
    m = DayTypeStateMachine()
    _drive_to_30min(m)
    assert m.day_type == DayType.UNKNOWN
    assert m.ib_locked is False


def test_provisional_needs_sierra_ib_no_synthesis(flag):
    """Source-of-truth (Rule 1): no developing Sierra IB -> honest UNKNOWN."""
    flag("1")
    m = DayTypeStateMachine()
    _drive_to_30min(m, with_sierra_ib=False)
    assert m.day_type == DayType.UNKNOWN  # never synthesize IB from bars


def test_lock_at_60min_overwrites_provisional(flag):
    """Provisional @ 30 is replaced by the real locked vote @ 60 (A4 -> B1)."""
    flag("1")
    m = DayTypeStateMachine()
    _drive_to_30min(m)
    assert m.day_type != DayType.UNKNOWN          # provisional present
    assert m.ib_locked is False
    m.process_bar(_bar(60, 7465, 7470, 7455, 7460, ibh=7491, ibl=7458))
    assert m.ib_locked is True                    # real lock now
    assert m.day_type != DayType.UNKNOWN          # finalized from locked IB
