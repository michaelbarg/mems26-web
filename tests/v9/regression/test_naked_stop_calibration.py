"""NAKED_STOP_SUSPECT calibration — don't alert when bracket stop exists.

Incident 07-10: 67 minutes of NAKED_STOP_SUSPECT alarm because last_result_status
was ORDER_SUBMITTED (bracket placement succeeded, stop is working via OCO).

If reverted → RED because ORDER_SUBMITTED would not be in _STOP_OK_STATUSES,
triggering a false alarm on every successful bracket placement.
"""
from backend.v9.services.reconcile import (
    reconcile_positions, IN_POSITION_OK, NAKED_STOP_SUSPECT,
)


def test_order_submitted_is_stop_confirmed():
    """ORDER_SUBMITTED from bracket placement confirms stop exists."""
    v = reconcile_positions(
        slot_occupied=True,
        db_open_ids=[337],
        last_result_status="ORDER_SUBMITTED",
        last_result_age_s=60.0,  # 1 min old — fresh
    )
    assert v.verdict == IN_POSITION_OK, (
        f"ORDER_SUBMITTED should confirm stop, got {v.verdict}"
    )
    assert not v.naked_stop_suspect


def test_unknown_status_still_naked_suspect():
    """An unknown/missing result status should still flag naked stop."""
    v = reconcile_positions(
        slot_occupied=True,
        db_open_ids=[337],
        last_result_status="SOME_UNKNOWN_STATUS",
        last_result_age_s=60.0,
    )
    assert v.verdict == NAKED_STOP_SUSPECT
    assert v.naked_stop_suspect


def test_stale_result_still_naked_suspect():
    """A confirmed stop that's too old should still flag as suspect."""
    v = reconcile_positions(
        slot_occupied=True,
        db_open_ids=[337],
        last_result_status="ENTRY_OK",
        last_result_age_s=1000.0,  # > 900s threshold
    )
    assert v.verdict == NAKED_STOP_SUSPECT
    assert v.naked_stop_suspect
