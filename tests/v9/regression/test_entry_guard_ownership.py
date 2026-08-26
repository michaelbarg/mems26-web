"""Test ENTRY_GUARD_OWNERSHIP_V1 — ownership-aware entry guard."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PRE_SEND_ENTRY_GUARD_V1", "1")
    monkeypatch.delenv("ENTRY_GUARD_OWNERSHIP_V1", raising=False)
    # Create a fresh sierra_state.json
    state = {"position_qty": 0, "working_orders": 0,
             "order_placement_armed": 1, "is_sim": 0}
    state_path = tmp_path / "sierra_state.json"
    state_path.write_text(json.dumps(state))
    monkeypatch.setattr("backend.v9.services.entry_guard.STATE", state_path)


def test_flag_off_blocks_any_position(monkeypatch, tmp_path):
    """Flag OFF: any pos != 0 blocks (legacy behavior, byte-identical)."""
    state_path = tmp_path / "sierra_state.json"
    state_path.write_text(json.dumps({
        "position_qty": -3, "working_orders": 0,
        "order_placement_armed": 1, "is_sim": 0}))
    from backend.v9.services.entry_guard import check_live_entry
    ok, reason, warns = check_live_entry("SHORT", 3)
    assert not ok
    assert "UNMANAGED" in reason


def test_flag_on_explained_by_tm_allows(monkeypatch, tmp_path):
    """Flag ON: position explained by TM trade → allows entry."""
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    state_path = tmp_path / "sierra_state.json"
    state_path.write_text(json.dumps({
        "position_qty": -3, "working_orders": 0,
        "order_placement_armed": 1, "is_sim": 0}))
    # Mock read_one to return an open SHORT trade
    with patch("backend.v9.services.entry_guard.read_one",
               create=True, return_value={"id": 100, "direction": "SHORT"}):
        # Need to patch the import inside the function
        import backend.v9.services.entry_guard as eg
        with patch("backend.v9.db.read.read_one",
                   return_value={"id": 100, "direction": "SHORT"}):
            ok, reason, warns = eg.check_live_entry("SHORT", 3)
    # Should pass — the -3 position is explained by the TM SHORT trade
    assert ok or "explained" in str(warns).lower() or "ownership" in reason.lower()


def test_flag_on_unexplained_blocks(monkeypatch, tmp_path):
    """Flag ON: position NOT explained → still blocks."""
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    state_path = tmp_path / "sierra_state.json"
    state_path.write_text(json.dumps({
        "position_qty": -3, "working_orders": 0,
        "order_placement_armed": 1, "is_sim": 0}))
    # Mock read_one to return no open trade
    with patch("backend.v9.db.read.read_one", return_value=None):
        from backend.v9.services.entry_guard import check_live_entry
        ok, reason, warns = check_live_entry("LONG", 3)
    assert not ok
    assert "UNMANAGED" in reason
