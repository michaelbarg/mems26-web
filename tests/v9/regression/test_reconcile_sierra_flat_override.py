"""Sierra-flat override in the reconcile verdict (2026-07-27).

Root incident: stuck PENDING/FILLED rows in our own bookkeeping (the entry-fill
handshake never completed) made `belief` True while Sierra was FLAT (pos=0,
working=0) — so the reconcile screamed NAKED_STOP_SUSPECT + fired the new loud
local alert repeatedly at Michael "with no reason". A safety alarm about a
position that does not exist trains the trader to ignore real alarms.

Rule: a FRESH Sierra position_qty == 0 overrides every internal belief →
AGREED_FLAT, naked_stop_suspect False. Unknown (None) → previous behaviour.
"""
from backend.v9.services.reconcile import (
    AGREED_FLAT, IN_POSITION_OK, NAKED_STOP_SUSPECT, reconcile_positions,
)


def test_sierra_flat_overrides_phantom_belief():
    """The exact 07-27 evening case: DB/slot think open, Sierra flat → no alarm."""
    v = reconcile_positions(
        slot_occupied=True, db_open_ids=[541], tm_in_position=True,
        last_result_status=None, last_result_age_s=None,
        sierra_position_qty=0,
    )
    assert v.verdict == AGREED_FLAT
    assert v.naked_stop_suspect is False
    assert "FLAT" in v.detail


def test_sierra_flat_overrides_even_with_stale_stop_result():
    v = reconcile_positions(
        slot_occupied=True, db_open_ids=[1], tm_in_position=True,
        last_result_status="MODIFY_STOP_NONE", last_result_age_s=9999.0,
        sierra_position_qty=0,
    )
    assert v.verdict == AGREED_FLAT and v.naked_stop_suspect is False


def test_real_naked_stop_still_alarms_when_sierra_in_position():
    """The protection must NOT be weakened: Sierra actually holds a position and
    the stop is unconfirmed → the alarm still fires (this is the 07-24 case that
    cost 837s of exposure)."""
    v = reconcile_positions(
        slot_occupied=True, db_open_ids=[1], tm_in_position=True,
        last_result_status="MODIFY_STOP_NONE", last_result_age_s=120.0,
        sierra_position_qty=-10,
    )
    assert v.verdict == NAKED_STOP_SUSPECT and v.naked_stop_suspect is True


def test_confirmed_stop_in_position_is_ok():
    v = reconcile_positions(
        slot_occupied=True, db_open_ids=[1], tm_in_position=True,
        last_result_status="ORDER_SUBMITTED", last_result_age_s=5.0,
        sierra_position_qty=4,
    )
    assert v.verdict == IN_POSITION_OK


def test_unknown_sierra_qty_keeps_previous_behaviour():
    """None (stale/missing state file) must not invent flatness — the old
    naked-stop path still applies (Rule 1: no synthetic safety)."""
    v = reconcile_positions(
        slot_occupied=True, db_open_ids=[1], tm_in_position=True,
        last_result_status=None, last_result_age_s=None,
        sierra_position_qty=None,
    )
    assert v.verdict == NAKED_STOP_SUSPECT


def test_flat_everywhere_is_still_agreed_flat():
    v = reconcile_positions(
        slot_occupied=False, db_open_ids=[], tm_in_position=False,
        sierra_position_qty=0,
    )
    assert v.verdict == AGREED_FLAT
