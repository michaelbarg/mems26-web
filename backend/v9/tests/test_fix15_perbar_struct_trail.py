"""FIX-15 — per-bar window-anchor stop improvement between consolidations.

Michael ruling 2026-07-10: "המערכת צריכה לבדוק על כל נר את הסטופ ולראות אם
אפשר לשפר במבנה חדש". The dynamic struct-trail only moved the stop when a
consolidation zone was detected; between zones the stop never improved even
when the rolling window anchor had tightened.

Fixture modeled on live trade 350 (2026-07-10 19:44): LONG 2 @7608.5,
stop 7604, price ran to 7615+ — the 8-bar window anchor rose above the
stop, but no consolidation zone formed → old code: stop stays 7604 forever.
New code (STOP_PERBAR_STRUCT_V1=1): stop ratchets to the anchor + emits
MODIFY_STOP. Anti-tautological: with the flag OFF (default) behavior is
byte-identical (no move, no emit).
"""
import types

import pytest

from backend.v9.services.trade_manager.manager import TradeManager


def _mk_manager(anchor_value):
    tm = TradeManager.__new__(TradeManager)  # skip __init__ (no DB needed)
    tm._structure_stop_after_t1 = lambda direction: anchor_value
    tm._mgmt_log = []
    tm._log_management = lambda tid, kind, payload: tm._mgmt_log.append((tid, kind, payload))
    tm._emits = []
    tm._emit_modify_stop = lambda trade, stop: tm._emits.append((trade.id, stop))
    return tm


def _mk_trade(direction, entry, stop):
    t = types.SimpleNamespace()
    t.id = 350
    t.direction = direction
    t.entry_price = entry
    t.stop = stop
    t.quality = {}
    t.cross_context = []
    return t


def test_long_anchor_tightens_moves_stop(monkeypatch):
    """350 fixture: anchor 7610.5 > stop 7604 → stop moves + MODIFY_STOP emitted."""
    monkeypatch.setenv("STOP_PERBAR_STRUCT_V1", "1")
    tm = _mk_manager(anchor_value=7610.5)
    t = _mk_trade("LONG", 7608.5, 7604.0)
    moved = tm._apply_window_anchor_trail(t)
    assert moved is True
    assert t.stop == pytest.approx(7610.5)
    assert tm._emits and tm._emits[0][1] == pytest.approx(7610.5)
    assert any(k == "STRUCT_TRAIL" for _, k, _p in tm._mgmt_log)
    assert t.cross_context and t.cross_context[-1]["event"] == "stop_move"


def test_long_anchor_wider_no_op(monkeypatch):
    """Anchor 7602 < stop 7604 → never widen: no move, no emit."""
    monkeypatch.setenv("STOP_PERBAR_STRUCT_V1", "1")
    tm = _mk_manager(anchor_value=7602.0)
    t = _mk_trade("LONG", 7608.5, 7604.0)
    moved = tm._apply_window_anchor_trail(t)
    assert moved is False
    assert t.stop == 7604.0
    assert not tm._emits


def test_short_symmetric(monkeypatch):
    """SHORT: anchor 7599 < stop 7603.75 → tightens; anchor 7606 → no-op."""
    monkeypatch.setenv("STOP_PERBAR_STRUCT_V1", "1")
    tm = _mk_manager(anchor_value=7599.0)
    t = _mk_trade("SHORT", 7596.0, 7603.75)
    assert tm._apply_window_anchor_trail(t) is True
    assert t.stop == pytest.approx(7599.0)

    tm2 = _mk_manager(anchor_value=7606.0)
    t2 = _mk_trade("SHORT", 7596.0, 7603.75)
    assert tm2._apply_window_anchor_trail(t2) is False
    assert t2.stop == 7603.75
    assert not tm2._emits


def test_flag_off_is_inert(monkeypatch):
    """Default (flag unset): identical behavior — no move even when anchor tightens."""
    monkeypatch.delenv("STOP_PERBAR_STRUCT_V1", raising=False)
    tm = _mk_manager(anchor_value=7610.5)
    t = _mk_trade("LONG", 7608.5, 7604.0)
    assert tm._apply_window_anchor_trail(t) is False
    assert t.stop == 7604.0
    assert not tm._emits


def test_anchor_none_honest_no_op(monkeypatch):
    """Anchor unavailable (honest None, Rule 1) → no move, no emit, no crash."""
    monkeypatch.setenv("STOP_PERBAR_STRUCT_V1", "1")
    tm = _mk_manager(anchor_value=None)
    t = _mk_trade("LONG", 7608.5, 7604.0)
    assert tm._apply_window_anchor_trail(t) is False
    assert t.stop == 7604.0
    assert not tm._emits
