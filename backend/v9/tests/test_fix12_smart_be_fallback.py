"""FIX-12 — structure wider than current stop must fall back to BE±1T, not silent no-op.

Real fixture: sim trade 340 (2026-07-10 18:40): SHORT 2 @7596.00, stop 7603.75.
T1 filled 7587.00 → smart-BE ran, _structure_stop_after_t1 returned ~7605 (swing
high, WIDER than 7603.75) → old code took structure as target_stop → never-widen
guard returned silently → the stop never tightened (evidence: stop stayed 7603.75,
no SMART_BE in management log, no MODIFY_STOP emitted).

New behavior: structure is used only when it TIGHTENS vs the current stop;
otherwise BE±1T. Anti-tautological: on the old code test_short_fix12 FAILS
(stop stays 7603.75); on the new code it PASSES (stop → 7595.75 + emit).
"""
import os
import types

import pytest

from backend.v9.services.trade_manager.manager import TradeManager


def _mk_manager(struct_value):
    tm = TradeManager.__new__(TradeManager)  # skip __init__ (no DB needed)
    tm._structure_stop_after_t1 = lambda direction: struct_value
    tm._mgmt_log = []
    tm._log_management = lambda tid, kind, payload: tm._mgmt_log.append((tid, kind, payload))
    tm._emits = []
    tm._emit_modify_stop = lambda trade, stop: tm._emits.append((trade.id, stop))
    return tm


def _mk_trade(direction, entry, stop):
    t = types.SimpleNamespace()
    t.id = 340
    t.direction = direction
    t.entry_price = entry
    t.stop = stop
    t.quality = {}
    t.cross_context = []
    return t


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    monkeypatch.setenv("STOP_STRUCTURE_TRAIL_V1", "1")
    yield


def test_short_structure_wider_falls_back_to_be():
    """The 340 fixture: struct 7605 > stop 7603.75 → BE-1T (7595.75) + emit."""
    tm = _mk_manager(struct_value=7605.0)
    t = _mk_trade("SHORT", 7596.0, 7603.75)
    tm._apply_smart_be_after_t1(t)
    assert t.stop == pytest.approx(7595.75), f"stop must tighten to BE-1T, got {t.stop}"
    assert tm._emits and tm._emits[0][1] == pytest.approx(7595.75), "MODIFY_STOP must be emitted"
    assert any(k == "SMART_BE" for _, k, _p in tm._mgmt_log)


def test_long_structure_wider_falls_back_to_be():
    """Symmetric LONG: struct 7580 < stop 7581 (wider for LONG) → BE+1T."""
    tm = _mk_manager(struct_value=7580.0)
    t = _mk_trade("LONG", 7590.0, 7581.0)
    tm._apply_smart_be_after_t1(t)
    assert t.stop == pytest.approx(7590.25)
    assert tm._emits and tm._emits[0][1] == pytest.approx(7590.25)


def test_structure_that_tightens_still_wins():
    """Structure tighter than current → structure (not BE): SHORT struct 7599 < 7603.75."""
    tm = _mk_manager(struct_value=7599.0)
    t = _mk_trade("SHORT", 7596.0, 7603.75)
    tm._apply_smart_be_after_t1(t)
    assert t.stop == pytest.approx(7599.0), "tightening structure must win over BE"


def test_never_widen_still_holds():
    """Stop already tighter than both structure and BE → true no-op (and no emit)."""
    tm = _mk_manager(struct_value=7605.0)
    t = _mk_trade("SHORT", 7596.0, 7595.0)  # already inside BE-1T
    tm._apply_smart_be_after_t1(t)
    assert t.stop == 7595.0
    assert not tm._emits
