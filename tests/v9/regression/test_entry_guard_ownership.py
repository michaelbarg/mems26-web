"""Test ENTRY_GUARD_OWNERSHIP_V1 — ownership-aware entry guard.

Three paths:
  Path 1: TM has an open trade matching the position → explained
  Path 2: manual_position_ack.json valid for today → explained
  Path 3: neither → blocks (orphan guard intact)

Mutation tests: removing any explanation path ⇒ blocks.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

import backend.v9.services.entry_guard as eg


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PRE_SEND_ENTRY_GUARD_V1", "1")
    monkeypatch.delenv("ENTRY_GUARD_OWNERSHIP_V1", raising=False)
    state = {"position_qty": 0, "working_orders": 0,
             "order_placement_armed": 1, "is_sim": 0}
    state_path = tmp_path / "sierra_state.json"
    state_path.write_text(json.dumps(state))
    monkeypatch.setattr(eg, "STATE", state_path)
    # Default: no ack file
    monkeypatch.setattr(eg, "_ACK_PATH", tmp_path / "manual_position_ack.json")
    yield


def _write_state(tmp_path, pos, working=0):
    (tmp_path / "sierra_state.json").write_text(json.dumps({
        "position_qty": pos, "working_orders": working,
        "order_placement_armed": 1, "is_sim": 0}))


def _write_ack(tmp_path, date=None, owner="michael", max_qty=10):
    if date is None:
        date = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    (tmp_path / "manual_position_ack.json").write_text(json.dumps({
        "date": date, "owner": owner, "max_abs_qty": max_qty,
        "note": "test ack"}))


# ── Flag OFF: legacy behavior ──

def test_flag_off_blocks_any_position(tmp_path):
    _write_state(tmp_path, -3)
    ok, reason, _ = eg.check_live_entry("SHORT", 3)
    assert not ok
    assert "UNMANAGED" in reason


# ── Path 1: TM trade match ──

def test_path1_tm_trade_explains_position(monkeypatch, tmp_path):
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    _write_state(tmp_path, -3)
    with patch("backend.v9.db.read.read_one",
               return_value={"id": 100, "direction": "SHORT"}):
        ok, reason, warns = eg.check_live_entry("LONG", 3)
    assert ok
    assert any("explained" in w.lower() or "ownership" in w.lower() for w in warns)


def test_path1_wrong_direction_not_explained(monkeypatch, tmp_path):
    """TM has LONG trade but position is SHORT → NOT explained."""
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    _write_state(tmp_path, -3)
    with patch("backend.v9.db.read.read_one",
               return_value={"id": 100, "direction": "LONG"}):
        ok, reason, _ = eg.check_live_entry("SHORT", 3)
    assert not ok


# ── Path 2: manual ack ──

def test_path2_manual_ack_explains_position(monkeypatch, tmp_path):
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    _write_state(tmp_path, -3)
    _write_ack(tmp_path)  # today's date
    with patch("backend.v9.db.read.read_one", return_value=None):
        ok, reason, warns = eg.check_live_entry("LONG", 3)
    assert ok
    assert any("coexist" in w.lower() or "explained" in w.lower() for w in warns)


def test_path2_yesterday_ack_blocks(monkeypatch, tmp_path):
    """Ack from yesterday does NOT explain today's position."""
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    _write_state(tmp_path, -3)
    _write_ack(tmp_path, date="2026-08-25")  # yesterday
    with patch("backend.v9.db.read.read_one", return_value=None):
        ok, reason, _ = eg.check_live_entry("LONG", 3)
    assert not ok
    assert "UNMANAGED" in reason


def test_path2_no_ack_file_blocks(monkeypatch, tmp_path):
    """No ack file at all → blocks."""
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    _write_state(tmp_path, -3)
    # No ack file written
    with patch("backend.v9.db.read.read_one", return_value=None):
        ok, reason, _ = eg.check_live_entry("SHORT", 3)
    assert not ok


def test_path2_qty_exceeds_ack_blocks(monkeypatch, tmp_path):
    """Position exceeds ack max_abs_qty → blocks."""
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    _write_state(tmp_path, -15)
    _write_ack(tmp_path, max_qty=10)
    with patch("backend.v9.db.read.read_one", return_value=None):
        ok, reason, _ = eg.check_live_entry("LONG", 3)
    assert not ok


# ── Path 3: neither → blocks ──

def test_path3_no_explanation_blocks(monkeypatch, tmp_path):
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    _write_state(tmp_path, -3)
    with patch("backend.v9.db.read.read_one", return_value=None):
        ok, reason, _ = eg.check_live_entry("LONG", 3)
    assert not ok
    assert "UNMANAGED" in reason


# ── Mutation test: flat position always passes ──

def test_flat_position_always_passes(monkeypatch, tmp_path):
    monkeypatch.setenv("ENTRY_GUARD_OWNERSHIP_V1", "1")
    _write_state(tmp_path, 0)
    ok, _, _ = eg.check_live_entry("LONG", 3)
    assert ok
