# -*- coding: utf-8 -*-
"""T-566 — STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1 (Michael 08.10 11:5x: "אם יש שינוי בסוג היום
אז לפחות היית מזיז את הסטופ — איפה מערכת 6 בכל זה").

07.10 #3164 OPENING_DRIVE SHORT 16:50 @7823.25, stop 7838.25 (15 pt). 16:55:06 the
grade-A structure exit fired ("failed break LONG while SHORT — tighten stop") and the
pre-T1 rule (STRUCTURE_EXIT_REALIZE_V1, Michael 02.09: "before T1 → no action") skipped
it; System 6 alerted stop_too_wide every 5 min for 55 min; the original stop was hit at
17:51 (−75$). With the flag the detector's own `new_stop` (one tick beyond the return
bar) is applied pre-T1 — tighten only, never widen, never flatten.

Flag OFF = the REALIZE skip, byte-identical (first test). Fixture: BarLevelDetector via
__new__ with a recording TradeManager double; the detector and TPO are monkeypatched at
their import sites (the method imports them lazily).
"""
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
    t = types.SimpleNamespace()
    t.id = 3164
    t.direction = direction
    t.entry_price = entry
    t.stop = stop
    t.t1_hit_ts = None
    t.t2_hit_ts = None
    t.t3_hit_ts = None
    t.quality = {"c1_stop_id": 11438, "contracts": 1, "sierra_order_id": 11436}
    t.mode = "demo"
    return t


@pytest.fixture
def env(monkeypatch):
    """Live flag state of 07.10 (FAILBREAK shadow, REALIZE live), the detector firing a
    failed break AGAINST the trade, VA edges present. The tighten flag is unset."""
    monkeypatch.setenv("STRUCTURE_EXIT_FAILBREAK_V1", "shadow")
    monkeypatch.setenv("STRUCTURE_EXIT_REALIZE_V1", "live")
    monkeypatch.delenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", raising=False)
    monkeypatch.delenv("STRUCTURE_EXIT_DOUBLE_V1", raising=False)
    monkeypatch.delenv("STRUCTURE_EXIT_REALIZE_PRE_T1_V1", raising=False)
    import backend.v9.db.read as _read
    import backend.v9.systems.five_min.five_min_system as _fm
    import backend.v9.systems.failed_break as _fb
    monkeypatch.setattr(_read, "read_all", lambda *a, **k: _bars())
    monkeypatch.setattr(_fm, "_load_sierra_tpo", lambda *a, **k: {"vah": 7840.0, "val": 7820.0, "poc": 7830.0})
    state = {"fb": {"direction": "LONG", "type": "FB_LOW", "poc": 7830.0}}
    monkeypatch.setattr(_fb, "detect_failed_break", lambda *a, **k: state["fb"])
    det = BarLevelDetector.__new__(BarLevelDetector)
    det._tm = _TM()
    return types.SimpleNamespace(det=det, tm=det._tm, state=state, monkeypatch=monkeypatch)


def _fire(env, trade, direction="SHORT", hi=7827.5, lo=7821.0, close=7826.0):
    env.det._maybe_structure_exit(trade, direction, hi, lo, close)


def test_flag_off_pre_t1_is_the_07_10_skip(env):
    """07.10 16:55:06 as it happened: grade-A against the SHORT, pre-T1 → no MODIFY."""
    t = _trade()
    _fire(env, t)
    assert env.tm.modifies == []
    assert t.stop == 7838.25


def test_flag_on_short_tightens_to_one_tick_above_the_return_bar(env):
    env.monkeypatch.setenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", "1")
    t = _trade()
    _fire(env, t, hi=7827.5, lo=7821.0, close=7826.0)
    assert env.tm.modifies == [(3164, 7827.75)]       # bar_high + 0.25
    assert t.stop == 7827.75


def test_flag_on_long_tightens_to_one_tick_below_the_return_bar(env):
    env.monkeypatch.setenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", "1")
    env.state["fb"] = {"direction": "SHORT", "type": "FB_HIGH", "poc": 7830.0}
    t = _trade(direction="LONG", stop=7815.5, entry=7823.5)
    _fire(env, t, direction="LONG", hi=7829.0, lo=7822.0, close=7823.0)
    assert env.tm.modifies == [(3164, 7821.75)]       # bar_low − 0.25
    assert t.stop == 7821.75


def test_flag_on_never_widens(env):
    """A stop already tighter than the return bar stays where it is."""
    env.monkeypatch.setenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", "1")
    t = _trade(stop=7825.0)                            # tighter than 7827.75
    _fire(env, t, hi=7827.5, lo=7821.0, close=7826.0)
    assert env.tm.modifies == []
    assert t.stop == 7825.0


def test_flag_on_fires_once_per_trade_and_type(env):
    env.monkeypatch.setenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", "1")
    t = _trade()
    _fire(env, t, hi=7827.5, lo=7821.0, close=7826.0)
    _fire(env, t, hi=7830.0, lo=7824.0, close=7829.0)  # same trade, same type: already fired
    assert env.tm.modifies == [(3164, 7827.75)]


def test_flag_on_failed_break_in_our_favour_does_nothing(env):
    """A failed break SHORT (price failed to go up) while SHORT is not against us."""
    env.monkeypatch.setenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", "1")
    env.state["fb"] = {"direction": "SHORT", "type": "FB_HIGH", "poc": 7830.0}
    t = _trade()
    _fire(env, t)
    assert env.tm.modifies == []


def test_flag_on_after_t1_the_existing_realize_path_is_untouched(env):
    """Post-T1 the 02.09 REALIZE rule still owns the action (bar_close ± tick)."""
    env.monkeypatch.setenv("STRUCTURE_EXIT_TIGHTEN_PRE_T1_V1", "1")
    t = _trade()
    t.t1_hit_ts = "2026-10-07T14:30:00+00:00"
    _fire(env, t, hi=7827.5, lo=7821.0, close=7826.0)
    # REALIZE: close + 0.25 for SHORT, one emit per unhit target (the live emitter dedups
    # identical stops within 60s) — unchanged by the pre-T1 flag.
    assert env.tm.modifies and all(m == (3164, 7826.25) for m in env.tm.modifies)
