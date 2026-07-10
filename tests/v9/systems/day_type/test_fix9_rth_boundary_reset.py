"""FIX-9 — an overnight/Globex-derived day-type label must not survive the RTH open.

Incident (2026-07-10): the backend booted 10:47, the machine chewed Globex
bars all morning and held "Nontrend"; at the 16:30 open the one-source served
that stale label to the gates — 6 ZLR playbook blocks until a mid-day restart
recomputed it (~17:25).

Flag DAYTYPE_RTH_RESET_V1 (default OFF): on the first RTH bar after non-RTH
bars, carried state is dropped (machine.reset()) and the S1 stages decide
fresh. Anti-tautological: flag OFF keeps the carried state (reproduces the
incident); mid-RTH fresh boot (no prior non-RTH bar) is untouched.
"""
from backend.v9.systems.day_type.schemas import BarInput, DayType, Stage
from backend.v9.systems.day_type.state_machine import DayTypeStateMachine


def _bar(px, session_min, is_rth, ts=1_700_000_000.0):
    return BarInput(
        ts=ts, session_min=session_min, is_rth=is_rth,
        open=px, high=px + 1, low=px - 1, close=px, volume=50,
    )


def _machine_with_globex_label():
    """Feed non-RTH bars, then force the incident's carried state: a verdict
    AND an advanced stage (past the A-stage opening resets — that's what let
    the real 07-10 label survive 55 minutes of RTH bars)."""
    m = DayTypeStateMachine()
    for i in range(5):
        m.process_bar(_bar(7570 + i * 0.5, 0, is_rth=False))
    m.day_type = DayType.Nontrend
    m.stage = Stage.B2  # past A1-A4 → opening-stage resets never run
    return m


def test_flag_on_first_rth_bar_resets_carried_label(monkeypatch):
    monkeypatch.setenv("DAYTYPE_RTH_RESET_V1", "1")
    m = _machine_with_globex_label()
    assert m.day_type == DayType.Nontrend  # carried into the boundary
    m.process_bar(_bar(7585, 0, is_rth=True))  # 16:30 first RTH bar
    assert m.day_type == DayType.UNKNOWN, "carried Globex label must be dropped at RTH open"
    assert m.bar_count == 1, "fresh session: only the RTH bar counted"


def test_flag_off_reproduces_incident(monkeypatch):
    monkeypatch.delenv("DAYTYPE_RTH_RESET_V1", raising=False)
    m = _machine_with_globex_label()
    m.process_bar(_bar(7585, 0, is_rth=True))
    assert m.day_type == DayType.Nontrend, "flag OFF: old behavior (label carried)"


def test_flag_on_midrth_fresh_boot_untouched(monkeypatch):
    """Mid-RTH restart: machine starts empty, first bar is RTH → no reset path
    (prev is None, not False) — the TPO-seed mid-session logic stays in charge."""
    monkeypatch.setenv("DAYTYPE_RTH_RESET_V1", "1")
    m = DayTypeStateMachine()
    m.process_bar(_bar(7585, 120, is_rth=True))
    assert m.bar_count == 1  # processed normally, no spurious reset


def test_flag_on_rth_to_rth_no_reset(monkeypatch):
    """Consecutive RTH bars never trigger the boundary."""
    monkeypatch.setenv("DAYTYPE_RTH_RESET_V1", "1")
    m = DayTypeStateMachine()
    m.process_bar(_bar(7585, 0, is_rth=True))
    m.process_bar(_bar(7586, 5, is_rth=True))
    assert m.bar_count == 2
