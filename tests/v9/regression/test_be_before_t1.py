"""T-635 D1 · BE_BEFORE_T1_V1 (22.10.2026) — System 6 before T1.

Michael 19.10: "after T1 the stop goes to the entry — unless a mechanism says when it is better
earlier or not at all". Per trade (22.10 zoom-in): #3582 20.10 LONG 7754.50 stop 7749.25 (R 5.25)
ran 13.75 pts (2.6R) open on 4 contracts and came back to the full stop (−90$); #3515 19.10 ran
1.85R and was flattened at 22:50 with nothing. Flag OFF ⇒ byte-identical (the hook is never
entered, the method returns False without touching the trade).
"""
import os
from types import SimpleNamespace
from unittest.mock import patch

from backend.v9.services.trade_manager.manager import (
    TradeManager, be_before_t1_decision, _be_before_t1_enabled)

TICK = 0.25
# #3582 — v9_bars_5min_woodies 20.10 after the 20:05 entry (IL label, o, h, l, c)
B3582 = [
    ("20:05", 7754.5, 7755.25, 7751.75, 7753.75), ("20:10", 7753.5, 7756.75, 7751.0, 7755.25),
    ("20:15", 7755.25, 7759.0, 7753.5, 7756.5), ("20:20", 7756.5, 7764.0, 7756.25, 7761.75),
    ("20:25", 7761.75, 7764.25, 7760.75, 7763.75), ("20:30", 7763.75, 7766.0, 7760.75, 7762.5),
    ("20:35", 7762.25, 7764.75, 7762.25, 7764.25), ("20:40", 7764.25, 7766.25, 7763.0, 7764.0),
    ("20:45", 7764.25, 7766.5, 7762.75, 7764.5), ("20:50", 7764.5, 7768.25, 7763.5, 7767.5),
    ("20:55", 7767.5, 7767.5, 7761.75, 7764.0), ("21:00", 7764.0, 7766.5, 7760.75, 7760.75),
]
ENTRY, STOP0, ATR = 7754.5, 7749.25, 7.3571


def _walk(bars, direction="LONG", entry=ENTRY, stop0=STOP0, atr=ATR, **kw):
    """Replay the hook's bookkeeping over closed bars: returns [(label, new_stop or None)]."""
    hwm = entry; cur = stop0; prev_l = prev_h = None; out = []
    for t, o, h, l, c in bars:
        hwm = max(hwm, h) if direction == "LONG" else min(hwm, l)
        sl = min(l, prev_l) if prev_l is not None else l
        sh = max(h, prev_h) if prev_h is not None else h
        dec = be_before_t1_decision(direction, entry, stop0, cur, hwm, sl, sh, TICK, atr, **kw)
        if dec is not None:
            cur = dec[0]
        out.append((t, dec[0] if dec else None))
        prev_l, prev_h = l, h
        # the stop is a real order: once the bar trades through it the trade is out
        if (direction == "LONG" and l <= cur and dec is None and cur > stop0) or \
           (direction == "SHORT" and h >= cur and dec is None and cur < stop0):
            out.append((t, "HIT@%.2f" % cur)); break
    return out


def test_3582_be_then_step_trail_exits_in_profit():
    path = _walk(B3582)
    moves = {t: s for t, s in path if s is not None}
    # nothing before the 1R excursion (7759.75): 20:05 / 20:10 / 20:15 highs 7755.25 / 7756.75 / 7759.00
    assert all(moves.get(t) is None for t in ("20:05", "20:10", "20:15"))
    # 20:20 high 7764 ⇒ armed (fav 9.5 = 1.81R): stop → entry + 1 tick (the 2-bar step 7753.25 is below it)
    assert moves["20:20"] == 7754.75
    # from here the 2-bar low trails: 20:25 → 7756.00 · 20:30 → 7760.50 · 20:40 → 7762.00 · 20:45 → 7762.50
    assert moves["20:25"] == 7756.0 and moves["20:30"] == 7760.5
    assert moves["20:40"] == 7762.0 and moves["20:45"] == 7762.5
    # 20:35 / 20:50: the 2-bar low did not rise ⇒ no re-send (idempotent, never widen)
    assert moves.get("20:35") is None and moves.get("20:50") is None
    # 20:55 low 7761.75 trades through 7762.50 ⇒ out at +8.00 (demo took the full −5.25 at 21:42)
    assert path[-1] == ("20:55", "HIT@7762.50")


def test_be_only_variant_keeps_breakeven_until_t1():
    # trail_r=99 ⇒ never a step trail: the only move is BE+tick, and 21:00 low 7760.75 does not reach it
    path = _walk(B3582, trail_r=99.0)
    moves = [s for _, s in path if s is not None]
    assert moves == [7754.75]


def test_not_armed_below_1r_and_below_atr_floor():
    # fav 4.0 < max(1R=5.25, 0.6×7.36=4.41) ⇒ None
    assert be_before_t1_decision("LONG", ENTRY, STOP0, STOP0, ENTRY + 4.0, ENTRY - 1, ENTRY + 4, TICK, ATR) is None
    # with a tiny R (3.0) the ATR floor governs: fav 3.5 ≥ 1R but < 0.6×ATR ⇒ None
    assert be_before_t1_decision("LONG", 7800.0, 7797.0, 7797.0, 7803.5, 7801.0, 7803.5, TICK, 7.0) is None
    assert be_before_t1_decision("LONG", 7800.0, 7797.0, 7797.0, 7804.25, 7801.0, 7804.25, TICK, 7.0) == (7800.25, "BE_BEFORE_T1 fav=4.25 (1.42R) >= arm=4.20")


def test_short_symmetry_and_tick_rounding():
    # SHORT 7798 stop 7806.75 (R 8.75): fav 9 ⇒ BE−tick 7797.75; at 1.5R (13.125) the 2-bar high trails
    assert be_before_t1_decision("SHORT", 7798.0, 7806.75, 7806.75, 7789.0, 7789.0, 7795.0, TICK, 5.2) == (
        7797.75, "BE_BEFORE_T1 fav=9.00 (1.03R) >= arm=8.75")
    dec = be_before_t1_decision("SHORT", 7798.0, 7806.75, 7797.75, 7784.0, 7784.0, 7790.1, TICK, 5.2)
    assert dec is not None and dec[0] == 7790.25 and dec[1].startswith("STEP_TRAIL_BEFORE_T1")


def test_never_widens_and_bad_inputs_are_none():
    assert be_before_t1_decision("LONG", ENTRY, STOP0, 7760.0, ENTRY + 20, 7758.0, 7775.0, TICK, ATR) is None  # step 7757.75 < current 7760
    assert be_before_t1_decision("LONG", ENTRY, ENTRY, STOP0, ENTRY + 20, 7758.0, 7775.0, TICK, ATR) is None   # risk 0
    assert be_before_t1_decision("FLAT", ENTRY, STOP0, STOP0, ENTRY + 20, 7758.0, 7775.0, TICK, ATR) is None
    assert be_before_t1_decision("LONG", None, STOP0, STOP0, ENTRY + 20, 7758.0, 7775.0, TICK, ATR) is None


class _FakeTM:
    """Just enough of TradeManager for the method under test (no DB, no Sierra)."""
    def __init__(self):
        self.log = []; self.emitted = []
    def _zlr_stop_locked(self, trade): return False
    def _initial_stop(self, trade):
        q = trade.quality if isinstance(trade.quality, dict) else {}
        return float(q.get("initial_stop", trade.stop))
    def _log_management(self, tid, action, value=None): self.log.append((action, value))
    def _emit_modify_stop(self, trade, new_stop): self.emitted.append(new_stop)


def _trade(**kw):
    base = dict(id=3582, direction="LONG", entry_price=ENTRY, stop=STOP0, state="FILLED", t1_hit_ts=None,
                quality={"metadata": {"situation": {"atr_causal": ATR}}}, cross_context=[])
    base.update(kw)
    return SimpleNamespace(**base)


def test_flag_off_is_byte_identical():
    env = {k: v for k, v in os.environ.items() if k != "BE_BEFORE_T1_V1"}
    with patch.dict(os.environ, env, clear=True):
        assert not _be_before_t1_enabled()
        tm = _FakeTM(); tr = _trade(); q0 = dict(tr.quality)
        assert TradeManager.apply_be_before_t1(tm, tr, 7770.0, 7760.0) is False
        assert tr.stop == STOP0 and tr.quality == q0 and tm.emitted == [] and tm.log == []


def test_flag_on_moves_once_logs_and_emits_modify_stop_only():
    with patch.dict(os.environ, {"BE_BEFORE_T1_V1": "1"}):
        tm = _FakeTM(); tr = _trade()
        assert TradeManager.apply_be_before_t1(tm, tr, 7759.0, 7753.5) is False      # 20:15: fav 4.5 < 1R
        assert tr.stop == STOP0 and tm.emitted == []
        assert TradeManager.apply_be_before_t1(tm, tr, 7764.0, 7756.25) is True      # 20:20
        assert tr.stop == 7754.75 and tm.emitted == [7754.75]
        assert tr.quality["initial_stop"] == STOP0 and tr.quality["bb_hwm"] == 7764.0
        assert tm.log[-1][0] == "BE_BEFORE_T1" and tm.log[-1][1]["from"] == STOP0 and tm.log[-1][1]["to"] == 7754.75
        assert tr.cross_context[-1]["event"] == "stop_move"
        assert TradeManager.apply_be_before_t1(tm, tr, 7764.25, 7760.75) is True     # 20:25: 2-bar step → 7756.00
        assert tr.stop == 7756.0
        # after T1 the method stands aside (the existing SMART_BE / BE rule own the stop)
        tr.t1_hit_ts = "2026-10-20T18:00:00+00:00"
        assert TradeManager.apply_be_before_t1(tm, tr, 7770.0, 7766.0) is False
        assert tr.stop == 7756.0


def test_zlr_trade_untouched_even_when_on():
    with patch.dict(os.environ, {"BE_BEFORE_T1_V1": "1"}):
        tm = _FakeTM(); tm._zlr_stop_locked = lambda trade: True
        tr = _trade()
        assert TradeManager.apply_be_before_t1(tm, tr, 7770.0, 7760.0) is False
        assert tr.stop == STOP0 and tm.emitted == []
