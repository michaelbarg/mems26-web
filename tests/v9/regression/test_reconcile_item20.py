"""Item-20 — Sierra truth reconcile verdict logic.

Drives the pure reconcile_positions() through every disagreement class the
two live incidents produced (06-25 orphan, I-57 mirror) plus naked-stop.
"""
from backend.v9.services.reconcile import (
    reconcile_positions,
    AGREED_FLAT, IN_POSITION_OK, MISMATCH_ORPHAN_DB, MISMATCH_ORPHAN_TM,
    MISMATCH_PHANTOM_SLOT, NAKED_STOP_SUSPECT,
)


def test_agreed_flat():
    v = reconcile_positions(slot_occupied=False, db_open_ids=[], tm_in_position=False)
    assert v.verdict == AGREED_FLAT and not v.mismatch


def test_in_position_ok_with_confirmed_stop():
    v = reconcile_positions(slot_occupied=True, db_open_ids=[301], tm_in_position=True,
                            last_result_status="MODIFY_STOP_OK", last_result_age_s=30.0)
    assert v.verdict == IN_POSITION_OK
    assert not v.mismatch and not v.naked_stop_suspect


def test_orphan_db_i57_class():
    """DB says open, gateway slot flat — the I-57 'system still thinks it's in
    a trade' / released-slot-with-open-row class."""
    v = reconcile_positions(slot_occupied=False, db_open_ids=[276], tm_in_position=None)
    assert v.verdict == MISMATCH_ORPHAN_DB and v.mismatch


def test_orphan_tm_0625_class():
    """Sierra/TM holds a position nobody tracks — the 06-25 orphan."""
    v = reconcile_positions(slot_occupied=False, db_open_ids=[], tm_in_position=True)
    assert v.verdict == MISMATCH_ORPHAN_TM and v.mismatch


def test_phantom_slot():
    v = reconcile_positions(slot_occupied=True, db_open_ids=[], tm_in_position=False)
    assert v.verdict == MISMATCH_PHANTOM_SLOT and v.mismatch


def test_naked_stop_no_confirmation():
    """In position but the last result is not a stop-OK → naked-stop suspect."""
    v = reconcile_positions(slot_occupied=True, db_open_ids=[310], tm_in_position=True,
                            last_result_status="ENTRY_REJECTED", last_result_age_s=10.0)
    assert v.verdict == NAKED_STOP_SUSPECT and v.naked_stop_suspect


def test_naked_stop_stale_confirmation():
    """In position with a stop-OK that is too old → still suspect."""
    v = reconcile_positions(slot_occupied=True, db_open_ids=[310], tm_in_position=True,
                            last_result_status="MODIFY_STOP_OK", last_result_age_s=5000.0)
    assert v.verdict == NAKED_STOP_SUSPECT


def test_disagreement_takes_priority_over_naked_stop():
    """An orphan is reported even when the stop looks unconfirmed — safety
    ordering: structural mismatch first."""
    v = reconcile_positions(slot_occupied=False, db_open_ids=[276], tm_in_position=None,
                            last_result_status=None, last_result_age_s=None)
    assert v.verdict == MISMATCH_ORPHAN_DB


def test_degraded_when_db_source_errors(monkeypatch):
    """No-silent-failures: a failed DB read must NOT report AGREED_FLAT."""
    import backend.v9.services.reconcile as rc
    monkeypatch.setattr(rc, "_read_last_result", lambda: (None, None))
    import backend.v9.db.read as dbread
    def _boom(*a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr(dbread, "read_all", _boom)
    v = rc.gather_and_reconcile(gateway=None)
    assert v.verdict == rc.UNKNOWN_DEGRADED
