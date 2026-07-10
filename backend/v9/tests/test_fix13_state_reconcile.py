"""FIX-13 — the reconciler prefers the DLL's sierra_state.json when fresh.

07-10 evidence for why the activity-journal path is fragile: duplicate feeders
sharing one offset file re-emitted stale real-account events (reconciler read
"Sierra says 0" while the sim held +2), and the sim activity file carries no
position lines at all. sierra_state.json is the DLL's native truth, written
every ~1s. Stale (>10s) or missing state file → honest fallback to events.
"""
import json
import time
import types

import pytest

from backend.v9.services import sierra_position_reconciler as spr


def _mk_tm(open_long_contracts=2):
    t = types.SimpleNamespace()
    t.id = 350
    t.mode = "live"
    t.state = "FILLED"
    t.direction = "LONG"
    t.quality = {"contracts": open_long_contracts}
    t.t1_hit_ts = None
    t.t2_hit_ts = None
    t.t3_hit_ts = None
    tm = types.SimpleNamespace()
    tm.get_active_trades = lambda: [t]
    return tm


def _write_state(path, qty, age_s=0.0):
    path.write_text(json.dumps({
        "ts": int(time.time()), "is_sim": 1, "position_qty": qty,
        "avg_price": 7608.5, "working_orders": 2, "orders": [],
    }) + "\n")
    if age_s:
        old = time.time() - age_s
        import os
        os.utime(path, (old, old))


def test_fresh_state_file_wins(monkeypatch, tmp_path):
    """State says 2, events (stale journal) say 0 → state wins → MATCH."""
    state = tmp_path / "sierra_state.json"
    _write_state(state, qty=2)
    monkeypatch.setattr(spr, "STATE_FILE", state)
    monkeypatch.setattr(spr, "_sierra_position_qty", lambda: 0)  # poisoned journal
    ok, msg = spr.reconcile_position(_mk_tm(2))
    assert ok, msg
    assert "src=state" in msg


def test_stale_state_falls_back_to_events(monkeypatch, tmp_path):
    state = tmp_path / "sierra_state.json"
    _write_state(state, qty=7, age_s=60.0)  # stale → ignored
    monkeypatch.setattr(spr, "STATE_FILE", state)
    monkeypatch.setattr(spr, "_sierra_position_qty", lambda: 2)
    ok, msg = spr.reconcile_position(_mk_tm(2))
    assert ok, msg
    assert "src=events" in msg


def test_missing_state_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(spr, "STATE_FILE", tmp_path / "nope.json")
    monkeypatch.setattr(spr, "_sierra_position_qty", lambda: 2)
    ok, msg = spr.reconcile_position(_mk_tm(2))
    assert ok, msg
    assert "src=events" in msg


def test_divergence_still_screams(monkeypatch, tmp_path):
    """State fresh but disagrees with TM → DIVERGENCE (the alarm must stay loud)."""
    state = tmp_path / "sierra_state.json"
    _write_state(state, qty=0)
    monkeypatch.setattr(spr, "STATE_FILE", state)
    ok, msg = spr.reconcile_position(_mk_tm(2))
    assert not ok
    assert "DIVERGENCE" in msg and "src=state" in msg
