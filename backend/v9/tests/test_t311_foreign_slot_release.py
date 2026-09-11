"""T-311: live_slot release when our account is flat, ignoring foreign position.

Golden case (10.09): trade #1409 closed STOP_HIT at 18:55:17. Sierra
position_qty=-12 (Eti's contracts). Our order IDs: 11110 + children
11102/11103/11105/11106/11108/11109/11111. Eti's orders since flat:
11131, 11132, 11135. All foreign → slot should free.

Three properties:
  (a) on_trade_close frees the slot when position is proven foreign.
  (b) _selfheal_live_slot frees a stuck slot on proven foreign ownership.
  (c) position_is_foreign correctly distinguishes our IDs from foreign.
"""
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest


# ── position_is_foreign tests ─────────────────────────────────────────────

def test_position_is_foreign_all_foreign(tmp_path):
    """All POSITION_CHANGE order_ids are foreign → True."""
    events_file = tmp_path / "events.jsonl"
    events_file.write_text(
        '{"type":"POSITION_CHANGE","new_qty":0,"prev_qty":-3,"order_id":11110}\n'
        '{"type":"POSITION_CHANGE","new_qty":-10,"prev_qty":0,"order_id":11131}\n'
        '{"type":"POSITION_CHANGE","new_qty":-9,"prev_qty":-10,"order_id":11132}\n'
        '{"type":"POSITION_CHANGE","new_qty":-6,"prev_qty":-9,"order_id":11135}\n'
    )
    state_file = tmp_path / "sierra_state.json"
    state_file.write_text(json.dumps({
        "ts": int(time.time()),
        "position_qty": -6,
        "working_orders": 3,
        "orders": [
            {"id": 11133, "bs": 1, "qty": 10},
            {"id": 11134, "bs": 1, "qty": 6},
            {"id": 11136, "bs": 2, "qty": 6},
        ],
    }))
    our_quality = {
        "sierra_order_id": 11110,
        "c1_target_id": 11102,
        "c1_stop_id": 11103,
        "c2_target_id": 11105,
        "c2_stop_id": 11106,
        "c3_target_id": 11108,
        "c3_stop_id": 11109,
    }
    with patch("backend.v9.services.sierra_position_reconciler.EVENTS_FILE", events_file), \
         patch("backend.v9.services.sierra_position_reconciler.STATE_FILE", state_file):
        from backend.v9.services.sierra_position_reconciler import position_is_foreign
        assert position_is_foreign(our_quality) is True


def test_position_is_foreign_one_ours(tmp_path):
    """At least one POSITION_CHANGE order_id is ours → False."""
    events_file = tmp_path / "events.jsonl"
    events_file.write_text(
        '{"type":"POSITION_CHANGE","new_qty":0,"prev_qty":-3,"order_id":11110}\n'
        '{"type":"POSITION_CHANGE","new_qty":-3,"prev_qty":0,"order_id":11110}\n'
    )
    state_file = tmp_path / "sierra_state.json"
    state_file.write_text(json.dumps({
        "ts": int(time.time()),
        "position_qty": -3,
        "working_orders": 0,
        "orders": [],
    }))
    our_quality = {"sierra_order_id": 11110}
    with patch("backend.v9.services.sierra_position_reconciler.EVENTS_FILE", events_file), \
         patch("backend.v9.services.sierra_position_reconciler.STATE_FILE", state_file):
        from backend.v9.services.sierra_position_reconciler import position_is_foreign
        assert position_is_foreign(our_quality) is False


def test_position_is_foreign_no_quality():
    """No quality data → None (can't determine)."""
    from backend.v9.services.sierra_position_reconciler import position_is_foreign
    assert position_is_foreign(None) is None
    assert position_is_foreign({}) is None


def test_position_is_foreign_account_flat(tmp_path):
    """Account flat → False (nothing foreign)."""
    state_file = tmp_path / "sierra_state.json"
    state_file.write_text(json.dumps({
        "ts": int(time.time()),
        "position_qty": 0,
        "working_orders": 0,
        "orders": [],
    }))
    events_file = tmp_path / "events.jsonl"
    events_file.write_text("")
    our_quality = {"sierra_order_id": 11110}
    with patch("backend.v9.services.sierra_position_reconciler.EVENTS_FILE", events_file), \
         patch("backend.v9.services.sierra_position_reconciler.STATE_FILE", state_file):
        from backend.v9.services.sierra_position_reconciler import position_is_foreign
        assert position_is_foreign(our_quality) is False


def test_our_sierra_order_ids_extraction():
    """_our_sierra_order_ids extracts all known order IDs from quality."""
    from backend.v9.services.sierra_position_reconciler import _our_sierra_order_ids
    q = {
        "sierra_order_id": 11110,
        "c1_target_id": 11102,
        "c1_stop_id": 11103,
        "c2_target_id": 11105,
        "c2_stop_id": 11106,
    }
    ids = _our_sierra_order_ids(q)
    assert ids == {11110, 11102, 11103, 11105, 11106}


def test_our_sierra_order_ids_empty():
    """Empty/None quality → empty set."""
    from backend.v9.services.sierra_position_reconciler import _our_sierra_order_ids
    assert _our_sierra_order_ids(None) == set()
    assert _our_sierra_order_ids({}) == set()
    assert _our_sierra_order_ids({"contracts": 3}) == set()


# ── golden case: 10.09 incident ──────────────────────────────────────────

def test_golden_1009_slot_freed_on_foreign(tmp_path):
    """10.09 golden: #1409 closed, Eti holds -12. Slot must free."""
    events_file = tmp_path / "events.jsonl"
    # Simulate: our trade closed (went to 0 at some point), then Eti opened
    events_file.write_text(
        '{"type":"POSITION_CHANGE","new_qty":0,"prev_qty":3,"order_id":11114}\n'
        '{"type":"POSITION_CHANGE","new_qty":-3,"prev_qty":0,"order_id":11121}\n'
        '{"type":"POSITION_CHANGE","new_qty":-12,"prev_qty":-3,"order_id":11121}\n'
    )
    state_file = tmp_path / "sierra_state.json"
    state_file.write_text(json.dumps({
        "ts": int(time.time()),
        "position_qty": -12,
        "working_orders": 0,
        "orders": [],
    }))

    our_quality = {
        "sierra_order_id": 11110,
        "c1_target_id": 11102,
        "c1_stop_id": 11103,
        "c2_target_id": 11105,
        "c2_stop_id": 11106,
        "c3_target_id": 11108,
        "c3_stop_id": 11109,
        "c4_target_id": 11111,
    }

    with patch("backend.v9.services.sierra_position_reconciler.EVENTS_FILE", events_file), \
         patch("backend.v9.services.sierra_position_reconciler.STATE_FILE", state_file):
        from backend.v9.services.sierra_position_reconciler import position_is_foreign
        assert position_is_foreign(our_quality) is True, \
            "10.09 golden: Eti's orders 11121 not in our set → foreign"
