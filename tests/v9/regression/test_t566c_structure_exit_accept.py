# -*- coding: utf-8 -*-
"""T-566c — STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1=accept: the pre-T1 tighten waits for the NEXT closed bar to close
back inside the value edge (acceptance back in value) before it emits; no acceptance ⇒ dropped. Variants a/b
(=1 / room knob) emit at the signal bar and are unchanged (test_t566_structure_exit_tighten_pre_t1.py)."""
import types
import pytest
from backend.v9.services.trade_manager.bar_level_detector import BarLevelDetector


def _bars(n=14, base=7825.0):
    return [{"h": base + 2, "l": base - 2, "c": base, "o": base} for _ in range(n)]


class _TM:
    def __init__(self):
        self.modifies = []

    def _ladder_group_for(self, trade, tgt):
        return 0

    def _target_order_key(self, trade, tgt):
        return f"{tgt}_order"

    def _emit_modify_stop(self, trade, new_stop):
        self.modifies.append((trade.id, float(new_stop)))
        trade.stop = float(new_stop)


def _trade(direction="SHORT", stop=7838.25, entry=7823.25):
    t = types.SimpleNamespace(id=3164, direction=direction, entry_price=entry, stop=stop, t1_hit_ts=None,
                              t2_hit_ts=None, t3_hit_ts=None, mode="demo",
                              quality={"c1_stop_id": 11438, "contracts": 1, "sierra_order_id": 11436})
    return t


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("STRUCTURE_EXIT_FAILBREAK_V1", "shadow")
    monkeypatch.setenv("STRUCTURE_EXIT_REALIZE_V1", "live")
    monkeypatch.setenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", "accept")
    monkeypatch.delenv("STRUCTURE_EXIT_TIGHTEN_ROOM_ATR", raising=False)
    import backend.v9.db.read as _read
    import backend.v9.systems.five_min.five_min_system as _fm
    import backend.v9.systems.failed_break as _fb
    monkeypatch.setattr(_read, "read_all", lambda *a, **k: _bars())
    monkeypatch.setattr(_fm, "_load_sierra_tpo", lambda *a, **k: {"vah": 7840.0, "val": 7820.0, "poc": 7830.0})
    # a failed break BELOW VAL that returned inside — bullish, against our SHORT
    state = {"fb": {"direction": "LONG", "type": "FB_LOW_VA", "poc": 7830.0, "edge_high": 7840.0, "edge_low": 7820.0}}
    monkeypatch.setattr(_fb, "detect_failed_break", lambda *a, **k: state["fb"])
    det = BarLevelDetector.__new__(BarLevelDetector)
    det._tm = _TM()
    return types.SimpleNamespace(det=det, tm=det._tm, state=state, monkeypatch=monkeypatch)


def _bar(env, trade, hi, lo, close, direction="SHORT"):
    env.det._maybe_structure_exit(trade, direction, hi, lo, close)


def test_signal_bar_only_stores_pending_no_emit(env):
    t = _trade()
    _bar(env, t, 7827.5, 7821.0, 7826.0)
    assert env.tm.modifies == [] and t.stop == 7838.25
    assert env.det._se_pending[3164]["ns"] == 7827.75 and env.det._se_pending[3164]["type"] == "FB_LOW_VA"


def test_next_bar_accepted_inside_value_emits_the_signal_new_stop(env):
    t = _trade()
    _bar(env, t, 7827.5, 7821.0, 7826.0)                      # signal bar
    env.state["fb"] = None                                      # no new signal on the next bar
    _bar(env, t, 7829.0, 7824.0, 7828.0)                      # next bar closes inside (> VAL 7820)
    assert env.tm.modifies == [(3164, 7827.75)] and t.stop == 7827.75
    assert 3164 not in env.det._se_pending


def test_next_bar_closes_back_outside_drops_the_tighten(env):
    t = _trade()
    _bar(env, t, 7827.5, 7821.0, 7826.0)
    env.state["fb"] = None
    _bar(env, t, 7824.0, 7816.0, 7818.0)                      # closed back below VAL — no acceptance
    assert env.tm.modifies == [] and t.stop == 7838.25
    assert 3164 not in env.det._se_pending


def test_same_bar_seen_again_is_not_the_next_bar(env):
    t = _trade()
    _bar(env, t, 7827.5, 7821.0, 7826.0)
    env.state["fb"] = None
    _bar(env, t, 7827.5, 7821.0, 7826.0)                      # identical closed bar re-delivered
    assert env.tm.modifies == [] and 3164 in env.det._se_pending


def test_after_t1_pending_is_discarded_without_emit(env):
    t = _trade()
    _bar(env, t, 7827.5, 7821.0, 7826.0)
    env.state["fb"] = None
    t.t1_hit_ts = "2026-10-08T15:00:00Z"
    _bar(env, t, 7829.0, 7824.0, 7828.0)
    assert env.tm.modifies == [] and 3164 not in env.det._se_pending


def test_mode_1_still_emits_at_the_signal_bar(env):
    env.monkeypatch.setenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", "1")
    t = _trade()
    _bar(env, t, 7827.5, 7821.0, 7826.0)
    assert env.tm.modifies == [(3164, 7827.75)]
