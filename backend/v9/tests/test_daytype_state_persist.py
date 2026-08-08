"""K2 regression (2026-08-08): v9_day_type_state persist — ARM-AFTER-SUCCESS.

Friday 08-07 root: main.py armed the write-on-change signature BEFORE the
INSERT. safe_execute returns None on failure (never raises), so one failed
write armed the sig anyway and every later identical-state bar hit the skip
branch — 54-60 min row gaps during RTH while the watchdog screamed. The
extracted persist (backend/v9/systems/day_type/state_persist.py) must:

1. arm the sig only after a successful write (extended OR legacy),
2. leave the sig un-armed on total failure so the NEXT bar retries,
3. keep write-on-change semantics (unchanged sig → skip, no insert).
"""

from types import SimpleNamespace

import pytest

from backend.v9.systems.day_type import state_persist as sp


def _state(conf=0.33, day_type="Variation", stage="B2", lock="LOCKED_LOW_CONF"):
    return SimpleNamespace(
        day_type=day_type, stage=stage, confidence=conf,
        lock_state=lock, ib_width=None, behavior=None,
    )


@pytest.fixture
def calls(monkeypatch):
    """Capture safe_execute calls; behavior driven by a mutable results list."""
    rec = {"calls": [], "results": []}

    def fake_safe_execute(sql, params=(), db_path=None):
        rec["calls"].append(sql.strip().split("(")[0])
        return rec["results"].pop(0) if rec["results"] else 1

    monkeypatch.setattr("backend.v9.db.safe_writer.safe_execute", fake_safe_execute)
    return rec


def test_success_arms_sig_and_skips_next(calls):
    app_state = SimpleNamespace()
    st = _state()
    assert sp.persist_state_row(app_state, st, "AUCTION", None, "2026-08-08") == sp.WRITTEN
    assert app_state._last_dts_sig == sp.compute_sig(st)
    n_after_first = len(calls["calls"])

    # Same state again → write-on-change skip, no further insert
    assert sp.persist_state_row(app_state, st, "AUCTION", None, "2026-08-08") == sp.SKIPPED
    assert len(calls["calls"]) == n_after_first


def test_legacy_fallback_arms_sig(calls):
    app_state = SimpleNamespace()
    st = _state()
    calls["results"] = [None, 1]  # extended fails, legacy succeeds
    assert sp.persist_state_row(app_state, st, "AUCTION", None, "2026-08-08") == sp.WRITTEN_LEGACY
    assert app_state._last_dts_sig == sp.compute_sig(st)
    assert len(calls["calls"]) == 2


def test_total_failure_does_not_arm_sig_and_retries(calls):
    """THE Friday-gap regression: both inserts fail → sig must stay un-armed
    so the very next bar retries instead of silently skipping for an hour."""
    app_state = SimpleNamespace()
    st = _state()
    calls["results"] = [None, None]  # both inserts fail
    assert sp.persist_state_row(app_state, st, "AUCTION", None, "2026-08-08") == sp.FAILED
    assert getattr(app_state, "_last_dts_sig", None) is None, \
        "sig armed on FAILED write — the next identical bar would skip forever"

    # Next bar, same state: MUST retry the insert (and succeed this time)
    calls["results"] = [1]
    assert sp.persist_state_row(app_state, st, "AUCTION", None, "2026-08-08") == sp.WRITTEN
    assert app_state._last_dts_sig == sp.compute_sig(st)


def test_changed_state_writes_again(calls):
    app_state = SimpleNamespace()
    assert sp.persist_state_row(app_state, _state(conf=0.33), "A", None, "2026-08-08") == sp.WRITTEN
    assert sp.persist_state_row(app_state, _state(conf=0.08), "A", None, "2026-08-08") == sp.WRITTEN
    assert app_state._last_dts_sig == sp.compute_sig(_state(conf=0.08))


def test_never_raises_on_internal_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db exploded")
    monkeypatch.setattr("backend.v9.db.safe_writer.safe_execute", boom)
    app_state = SimpleNamespace()
    assert sp.persist_state_row(app_state, _state(), "A", None, "2026-08-08") == sp.FAILED
    assert getattr(app_state, "_last_dts_sig", None) is None
