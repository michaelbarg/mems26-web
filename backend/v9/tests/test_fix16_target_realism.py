"""FIX-16 — realistic T1 (trade 350 fixture, 2026-07-10).

Three layers:
1. _cap_target side-flip BUG: a wrong-side target 16.9pt below a LONG entry
   was "capped" to entry+14 — flipping it to the profit side and masking it
   from _fix_side. 350's ladder: c1 7591.6→7622.5(flip), c2/c3 R-fallbacks,
   monotonic sort crowned 2R as T1=7617.5 — above the 7614 day high.
2. realism_ceiling: session extreme + today's average breakout step.
3. apply_target_realism_perbar: pending target beyond the ceiling is
   tightened + MODIFY emitted (flag-gated, tighten-only).
"""
import types

import pytest

from backend.v9.systems.structural_targets import _cap_target, realism_ceiling
from backend.v9.services.trade_manager.manager import TradeManager


# ── layer 1: the cap side-flip bug ──────────────────────────────────────────

def test_cap_never_flips_wrong_side_target():
    """350 numbers: c1=7591.625 below LONG entry 7608.5, cap 14 → must stay
    wrong-side (old code returned 7622.5 = entry+14, ABOVE entry)."""
    out = _cap_target(7608.5, 7591.625, "LONG", 14.0)
    assert out == 7591.625, f"wrong-side target must pass through, got {out}"


def test_cap_still_caps_correct_side():
    out = _cap_target(7608.5, 7640.0, "LONG", 14.0)
    assert out == pytest.approx(7622.5)
    out_s = _cap_target(7596.0, 7550.0, "SHORT", 14.0)
    assert out_s == pytest.approx(7582.0)


# ── layer 2: the realism ceiling ────────────────────────────────────────────

def _bars(seq):
    return [{"high": h, "low": l} for h, l in seq]


def test_ceiling_long_day_high_plus_avg_step():
    """Highs advance 7610→7612→7613→7614 (steps 2,1,1 → avg 4/3=1.333).
    ceiling = 7614 + 1.333 → snapped 7615.25."""
    bars = _bars([(7610, 7606), (7612, 7607), (7613, 7609), (7614, 7610), (7612, 7608)])
    c = realism_ceiling("LONG", 7608.5, bars=bars)
    assert c == pytest.approx(7615.25)


def test_ceiling_short_symmetric():
    bars = _bars([(7610, 7606), (7609, 7604), (7608, 7602), (7607, 7601), (7609, 7603)])
    # lows advance down 7606→7604→7602→7601 (steps 2,2,1 → avg 5/3), day_lo 7601
    c = realism_ceiling("SHORT", 7605.0, bars=bars)
    assert c == pytest.approx(7599.25)  # 7601 - 1.667 → snap 7599.25


def test_ceiling_honest_none_without_bars():
    assert realism_ceiling("LONG", 7608.5, bars=[]) is None
    assert realism_ceiling("LONG", 7608.5, bars=_bars([(7610, 7606)])) is None


# ── layer 3: per-bar tighten on the live trade ──────────────────────────────

def _mk_tm():
    tm = TradeManager.__new__(TradeManager)
    tm._mgmt_log = []
    tm._log_management = lambda tid, kind, payload: tm._mgmt_log.append((tid, kind, payload))
    tm._target_emits = []
    tm._emit_modify_target = (
        lambda trade, tgt, target_order_id=None:
        tm._target_emits.append((trade.id, tgt, target_order_id)))
    return tm


def _mk_trade_350():
    t = types.SimpleNamespace()
    t.id = 350
    t.direction = "LONG"
    t.entry_price = 7608.5
    t.stop = 7604.0
    t.t1, t.t2, t.t3 = 7617.5, 7622.0, 7622.5
    t.t1_hit_ts = None
    t.t2_hit_ts = None
    t.t3_hit_ts = None
    t.quality = {"c1_target_id": 8718, "c2_target_id": 8721}
    t.cross_context = []
    return t


def _patch_ceiling(monkeypatch, value):
    import backend.v9.systems.structural_targets as st
    monkeypatch.setattr(st, "realism_ceiling", lambda direction, entry, bars=None: value)


def test_perbar_tightens_unrealistic_t1(monkeypatch):
    """350: t1 7617.5, ceiling 7615.25 → t1 → 7615.25 + MODIFY on order 8718."""
    monkeypatch.setenv("TARGET_REALISM_V1", "1")
    _patch_ceiling(monkeypatch, 7615.25)
    tm = _mk_tm()
    t = _mk_trade_350()
    assert tm.apply_target_realism_perbar(t) is True
    assert t.t1 == pytest.approx(7615.25)
    assert tm._target_emits == [(350, 7615.25, 8718)]
    assert any(k == "TARGET_REALISM" for _, k, _p in tm._mgmt_log)
    assert t.cross_context and t.cross_context[-1]["event"] == "target_move"


def test_perbar_realistic_target_untouched(monkeypatch):
    monkeypatch.setenv("TARGET_REALISM_V1", "1")
    _patch_ceiling(monkeypatch, 7620.0)  # ceiling above t1 → fine
    tm = _mk_tm()
    t = _mk_trade_350()
    assert tm.apply_target_realism_perbar(t) is False
    assert t.t1 == 7617.5
    assert not tm._target_emits


def test_perbar_flag_off_inert(monkeypatch):
    monkeypatch.delenv("TARGET_REALISM_V1", raising=False)
    _patch_ceiling(monkeypatch, 7615.25)
    tm = _mk_tm()
    t = _mk_trade_350()
    assert tm.apply_target_realism_perbar(t) is False
    assert t.t1 == 7617.5


def test_perbar_after_t1_moves_front_runner(monkeypatch):
    """Post-T1: the front runner (t2) is the one checked; never crosses entry."""
    monkeypatch.setenv("TARGET_REALISM_V1", "1")
    _patch_ceiling(monkeypatch, 7612.0)
    tm = _mk_tm()
    t = _mk_trade_350()
    t.t1_hit_ts = object()  # T1 done
    assert tm.apply_target_realism_perbar(t) is True
    assert t.t2 == pytest.approx(7612.0)
    assert tm._target_emits == [(350, 7612.0, 8721)]


def test_perbar_ceiling_none_honest_skip(monkeypatch):
    monkeypatch.setenv("TARGET_REALISM_V1", "1")
    _patch_ceiling(monkeypatch, None)
    tm = _mk_tm()
    t = _mk_trade_350()
    assert tm.apply_target_realism_perbar(t) is False
    assert t.t1 == 7617.5
