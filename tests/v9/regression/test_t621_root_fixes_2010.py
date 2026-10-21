"""T-621 (Michael 21.10 — the 20.10 plan, "מאשר את 2 ו 4"): the root fixes 1, 2, 4, 5 behind default-OFF flags.

  fix 1 IB_EXT_ACCEPTED_HINT_V1   the direction hint from an ACCEPTED IB extension only (released by the same rule)
  fix 2 DAYTYPE_SIDES_ACCEPTED_V1 a day-type side counts only when the extension was accepted
  fix 4 FLIP_RUNNER_ON_OPPOSITE_TAKE_V1  an opposite tree TAKE closes a runner (harness-executed; live = log only)
  fix 5 DOUBLE_TOP_STRUCT_STOP_V1 the double-top stop beyond the structure's higher top; T-616 authority for the
                                  DOUBLE_TOP/BOTTOM family only
The 20.10 bars below are v9_bars_5min_woodies (IL time label, o, h, l, c).
"""
import os
import types
from unittest.mock import patch

import pytest

from backend.v9.services import ib_acceptance as acc_mod
from backend.v9.services import flip_runner
from backend.v9.systems.ceiling_touch2 import detect_touch2, structure_extreme, struct_stop_max_atr
from backend.v9.systems.day_type.relative_features import compute_relative_features

_B2010 = [
    ("16:30", 7726.75, 7727.0, 7718.5, 7723.25), ("16:35", 7723.25, 7731.0, 7720.0, 7725.5),
    ("16:40", 7725.5, 7726.25, 7711.25, 7713.0), ("16:45", 7712.75, 7731.25, 7710.25, 7729.0),
    ("16:50", 7729.0, 7737.75, 7726.75, 7732.5), ("16:55", 7732.75, 7748.25, 7732.5, 7748.0),
    ("17:00", 7747.75, 7752.75, 7743.25, 7747.5), ("17:05", 7747.5, 7758.0, 7745.0, 7755.75),
    ("17:10", 7755.75, 7760.5, 7753.25, 7759.5), ("17:15", 7759.5, 7768.0, 7758.75, 7766.25),
    ("17:20", 7766.25, 7776.75, 7765.25, 7775.25), ("17:25", 7775.25, 7786.0, 7772.5, 7785.0),
    ("17:30", 7785.0, 7791.5, 7777.5, 7779.25), ("17:35", 7779.25, 7781.5, 7776.25, 7778.5),
    ("17:40", 7778.75, 7787.0, 7777.25, 7783.5), ("17:45", 7783.75, 7787.0, 7779.75, 7781.0),
    ("17:50", 7781.25, 7787.5, 7779.5, 7786.0), ("17:55", 7786.0, 7790.5, 7784.25, 7785.0),
    ("18:00", 7785.0, 7785.5, 7777.75, 7778.5), ("18:05", 7778.5, 7781.0, 7777.0, 7777.75),
    ("18:10", 7777.75, 7778.25, 7746.75, 7756.75), ("18:15", 7757.0, 7768.5, 7754.75, 7766.5),
]
IBH, IBL = 7786.0, 7710.25
FLAGS = ("IB_EXT_ACCEPTED_HINT_V1", "DAYTYPE_SIDES_ACCEPTED_V1", "FLIP_RUNNER_ON_OPPOSITE_TAKE_V1",
         "DOUBLE_TOP_STRUCT_STOP_V1", "IB_EXT_ACCEPT_CLOSES", "IB_EXT_ACCEPT_NOISE_PTS", "TOUCH2_STRUCT_STOP_MAX_ATR",
         "DAYTYPE_SIDES_MECHANICAL_V1", "IB_BREAK_ANY_EXPANSION_V1", "DAYTYPE_SIDES_NOISE_PTS", "DAYTYPE_MECH_HOLD_BARS")


def _bars(upto=None, kind="dict"):
    out = []
    for t, o, h, l, c in _B2010:
        if kind == "obj":
            out.append(types.SimpleNamespace(o=o, h=h, l=l, c=c, v=None, ts="2026-10-20 " + t))
        else:
            out.append({"ts": "2026-10-20 " + t, "o": o, "h": h, "l": l, "c": c})
        if t == upto:
            break
    return out


def _env(**kv):
    base = {k: v for k, v in os.environ.items() if k not in FLAGS}
    base.update(kv)
    return patch.dict(os.environ, base, clear=True)


def _synthetic(post_closes, ib_hi=100.0, ib_lo=90.0, wick=None):
    """12 IB bars inside [ib_lo, ib_hi], then one bar per close (high = close + 0.5, or `wick` for every bar)."""
    ib = [{"h": ib_hi if i == 3 else ib_hi - 1, "l": ib_lo if i == 7 else ib_lo + 1, "c": (ib_hi + ib_lo) / 2}
          for i in range(12)]
    post = [{"h": (wick if wick is not None else c + 0.5), "l": c - 0.5, "c": c} for c in post_closes]
    return ib + post


# ── the shared acceptance rule (fixes 1 and 2) ──────────────────────────────────────────────────────────────────

def test_2010_wick_is_not_an_accepted_extension():
    with _env():
        a = acc_mod.acceptance(_bars(), ib_hi=IBH, ib_lo=IBL)
    assert a["state"] == "inside" and a["ext_up"] == 5.5 and a["up_run"] == 0
    assert not a["up_accepted"] and acc_mod.hint(a) is None and acc_mod.sides(a) == 0


def test_bars_only_ib_equals_the_tpo_ib_on_2010():
    with _env():
        a = acc_mod.acceptance(_bars())
    assert (a["ib_hi"], a["ib_lo"]) == (IBH, IBL) and a["state"] == "inside"


def test_forming_before_the_ib_completes():
    with _env():
        assert acc_mod.acceptance(_bars("17:25"))["state"] == "forming"


def test_two_closes_beyond_accept_then_two_inside_release():
    with _env():
        a1 = acc_mod.acceptance(_synthetic([101.0]))
        a2 = acc_mod.acceptance(_synthetic([101.0, 101.25]))
        a3 = acc_mod.acceptance(_synthetic([101.0, 101.25, 99.0]))
        a4 = acc_mod.acceptance(_synthetic([101.0, 101.25, 99.0, 98.5]))
        a5 = acc_mod.acceptance(_synthetic([101.0, 101.25, 99.0, 98.5, 101.0, 102.0]))
    assert a1["state"] == "inside" and acc_mod.hint(a1) is None
    assert a2["state"] == "up" and acc_mod.hint(a2) == "LONG" and acc_mod.sides(a2) == 1
    assert a3["state"] == "up" and acc_mod.hint(a3) == "LONG"           # one close back inside is not a release
    assert a4["state"] == "released_up" and acc_mod.hint(a4) is None and acc_mod.sides(a4) == 1
    assert a5["state"] == "up" and acc_mod.hint(a5) == "LONG"           # accepted again


def test_noise_floor_and_non_consecutive_closes():
    with _env():
        thin = acc_mod.acceptance(_synthetic([100.25, 100.25]))         # beyond the edge but < 0.5 noise
        broken = acc_mod.acceptance(_synthetic([101.0, 99.0, 101.0]))   # never 2 in a row
        n3 = acc_mod.acceptance(_synthetic([101.0, 101.0]), n=3)
    assert thin["state"] == "inside" and broken["state"] == "inside" and n3["state"] == "inside"
    with _env(IB_EXT_ACCEPT_CLOSES="1", IB_EXT_ACCEPT_NOISE_PTS="0"):
        assert acc_mod.acceptance(_synthetic([100.25]))["state"] == "up"


def test_down_side_and_the_latest_accepted_side_wins():
    with _env():
        dn = acc_mod.acceptance(_synthetic([89.0, 88.5]))
        both = acc_mod.acceptance(_synthetic([101.0, 101.0, 89.0, 88.0]))
    assert dn["state"] == "down" and acc_mod.hint(dn) == "SHORT"
    # the two closes below the IB low are also back inside the IB high ⇒ the up side is released as the down side is
    # accepted: the direction is the LATEST accepted extension; the day still counts both sides (Neutral)
    assert both["state"] == "down" and acc_mod.sides(both) == 2 and acc_mod.hint(both) == "SHORT"
    assert acc_mod.hint({"up_live": True, "dn_live": True, "ext_up": 1.0, "ext_dn": 2.0}) == "SHORT"


def test_object_bars_work():
    with _env():
        a = acc_mod.acceptance(_bars(kind="obj"), ib_hi=IBH, ib_lo=IBL)
    assert a["state"] == "inside" and a["ext_up"] == 5.5


def test_env_parsers():
    with _env():
        assert (acc_mod.accept_closes(), acc_mod.accept_noise()) == (2, 0.5)
    for raw, want in (("3", 3), ("0", 2), ("x", 2), ("1", 1)):
        with _env(IB_EXT_ACCEPT_CLOSES=raw):
            assert acc_mod.accept_closes() == want, raw
    with _env(IB_EXT_ACCEPT_NOISE_PTS="-1"):
        assert acc_mod.accept_noise() == 0.5


# ── fix 1: the Layer 2 hint ─────────────────────────────────────────────────────────────────────────────────────

def test_fix1_layer2_hint_modes_on_2010():
    with _env():
        a = acc_mod.acceptance(_bars(), ib_hi=IBH, ib_lo=IBL)
        forming = acc_mod.acceptance(_bars("17:25"), ib_hi=IBH, ib_lo=IBL)
        up = acc_mod.acceptance(_synthetic([101.0, 101.0]))
    # 20.10 after 17:30: the old rule said LONG (any ext > 0); mode 1 keeps Layer 1, mode none gives no direction
    assert acc_mod.layer2_hint("1", "SHORT", a) == "SHORT"
    assert acc_mod.layer2_hint("none", "SHORT", a) is None
    assert acc_mod.layer2_hint("none", "SHORT", forming) == "SHORT"     # IB not complete ⇒ Layer 1 stands
    assert acc_mod.layer2_hint("1", "SHORT", up) == "LONG" and acc_mod.layer2_hint("none", None, up) == "LONG"


def test_fix1_gateway_wiring_keeps_the_old_rule_when_off():
    src = open("backend/v9/gateway/trading_gateway.py", encoding="utf-8").read()
    i = src.index('_t621_mode = os.getenv("IB_EXT_ACCEPTED_HINT_V1", "0")')
    block = src[i:i + 2600]
    assert 'in ("1", "true", "yes", "none")' in block and "layer2_hint(_t621_mode, _t621_l1, _t621_acc)" in block
    # the OFF branch is the original ext>0 override, unchanged
    assert "elif _dp_ibh > 0 and _dp_ibl > 0:" in block
    assert "if _dp_ext_up > _dp_ext_dn and _dp_ext_up > 0:" in block


# ── fix 2: the day-type side count ──────────────────────────────────────────────────────────────────────────────

def test_fix2_2010_sides_mechanical_counts_the_wick_accepted_does_not():
    with _env(DAYTYPE_SIDES_MECHANICAL_V1="1", IB_BREAK_ANY_EXPANSION_V1="1"):
        f_old = compute_relative_features(_bars(), IBH, IBL)
    with _env(DAYTYPE_SIDES_MECHANICAL_V1="1", IB_BREAK_ANY_EXPANSION_V1="1", DAYTYPE_SIDES_ACCEPTED_V1="1"):
        f_new = compute_relative_features(_bars(), IBH, IBL)
        f_obj = compute_relative_features(_bars(kind="obj"), IBH, IBL)
    assert f_old.sides == 1                     # the 17:30–17:55 highs ≥ 7786.50 ⇒ "Variation"
    assert f_new.sides == 0 and f_obj.sides == 0
    assert (f_old.rib, f_old.session_high) == (f_new.rib, f_new.session_high)   # nothing else moves


def test_fix2_off_is_byte_identical_and_accepted_days_still_count():
    bars = _synthetic([101.0, 101.5, 102.0])
    with _env(DAYTYPE_SIDES_MECHANICAL_V1="1", IB_BREAK_ANY_EXPANSION_V1="1"):
        a = compute_relative_features(bars, 100.0, 90.0)
    with _env(DAYTYPE_SIDES_MECHANICAL_V1="1", IB_BREAK_ANY_EXPANSION_V1="1", DAYTYPE_SIDES_ACCEPTED_V1="1"):
        b = compute_relative_features(bars, 100.0, 90.0)
    assert a.sides == 1 and b.sides == 1
    with _env(DAYTYPE_SIDES_ACCEPTED_V1="1"):        # outside the mechanical block the flag is inert
        c = compute_relative_features(_bars(), IBH, IBL)
    with _env():
        d = compute_relative_features(_bars(), IBH, IBL)
    assert c.sides == d.sides


# ── fix 4: flip the runner ──────────────────────────────────────────────────────────────────────────────────────

def test_fix4_decide():
    ok, _ = flip_runner.decide("LONG", True, "SHORT", "TAKE", "on")
    assert ok
    for args in (("LONG", True, "LONG", "TAKE", "on"), ("LONG", False, "SHORT", "TAKE", "on"),
                 ("LONG", True, "SHORT", "SKIP", "on"), ("LONG", True, "SHORT", "TAKE", "shadow"),
                 (None, True, "SHORT", "TAKE", "on")):
        assert not flip_runner.decide(*args)[0], args


def _fake_gw(runner=True, exit_ok=True, new_trade=True):
    from backend.v9.gateway import trading_gateway as tg
    calls = {"exit": 0, "exec": 0}
    g = types.SimpleNamespace(live_slot={"trade_id": "OLD", "direction": "LONG"}, _last_live_abort=None,
                              _daily_pnl=0.0, _daily_trades=0, _consecutive_losses=0)

    def _exit(slot, setup):
        calls["exit"] += 1
        if exit_ok:
            g.live_slot = None
        return exit_ok

    def _exec(setup, sid, cc):
        calls["exec"] += 1
        return {"trade_id": "NEW", "direction": setup["direction"]} if new_trade else None
    g._t621_slot_is_runner = lambda slot: runner
    g._t621_exit_runner = _exit
    g._execute_live = _exec
    return tg, g, calls


def test_fix4_flip_off_is_inert():
    tg, g, calls = _fake_gw()
    res = {"tree_v3": {"leaf": "TAKE", "mode": "on"}}
    with _env():
        assert tg.TradingGateway._t621_flip_runner(g, {"direction": "SHORT"}, 2, {}, res) is False
    assert calls == {"exit": 0, "exec": 0} and "flip_runner" not in res and g.live_slot["trade_id"] == "OLD"


def test_fix4_flip_closes_the_runner_and_routes_the_candidate():
    tg, g, calls = _fake_gw()
    res = {"tree_v3": {"leaf": "TAKE", "mode": "on"}}
    with _env(FLIP_RUNNER_ON_OPPOSITE_TAKE_V1="1"), patch.object(tg, "passes_strict_checks", lambda *a: True):
        assert tg.TradingGateway._t621_flip_runner(g, {"direction": "SHORT", "classification": "X"}, 2, {}, res)
    assert calls == {"exit": 1, "exec": 1} and g.live_slot["trade_id"] == "NEW" and res["live"] == "NEW"
    assert res["flip_runner"]["flipped"] is True


@pytest.mark.parametrize("runner,leaf,exit_ok", [(False, "TAKE", True), (True, "SKIP", True), (True, "TAKE", False)])
def test_fix4_no_flip_cases_keep_the_slot(runner, leaf, exit_ok):
    tg, g, calls = _fake_gw(runner=runner, exit_ok=exit_ok)
    res = {"tree_v3": {"leaf": leaf, "mode": "on"}}
    with _env(FLIP_RUNNER_ON_OPPOSITE_TAKE_V1="1"), patch.object(tg, "passes_strict_checks", lambda *a: True):
        assert tg.TradingGateway._t621_flip_runner(g, {"direction": "SHORT"}, 2, {}, res) is False
    assert calls["exec"] == 0


def test_fix4_live_exit_seam_is_log_only():
    from backend.v9.gateway import trading_gateway as tg
    g = types.SimpleNamespace()
    assert tg.TradingGateway._t621_exit_runner(g, {"trade_id": 1, "direction": "LONG"},
                                               {"direction": "SHORT", "entry_price": 1.0}) is False


# ── fix 5: the structure's higher top ───────────────────────────────────────────────────────────────────────────

LV_1750 = {"vah": 7781.75, "val": 7743.25, "session_high": 7791.5, "session_low": 7710.25,
           "ib_high": IBH, "ib_low": IBL}


def test_fix5_2010_touch2_short_stop_goes_beyond_the_wick():
    with _env():
        st = detect_touch2(_bars("17:45"), LV_1750, atr=7.8, ib_width=IBH - IBL)
        assert st is not None and st["state"] == "CEILING_TOUCH2_REJECT"
        assert (st["p1"], st["p2"], st["confirm_close"]) == (7787.0, 7787.0, 7781.0)
        assert structure_extreme(_bars("17:45"), st, "SHORT", 7.8) == 7791.5
        assert structure_extreme(_bars("17:45"), st, "SHORT", 4.0) is None       # 4.5 pt > 1 × ATR 4.0
        assert structure_extreme(_bars("17:45"), st, "SHORT", 4.0, max_atr=1.5) == 7791.5


def test_fix5_no_higher_top_and_long_mirror():
    st = {"p1_index": 1, "p2_index": 3, "p1": 10.0, "p2": 10.0}
    flat = [{"h": 10.0, "l": 5.0, "c": 7.0}] * 4
    assert structure_extreme(flat, st, "SHORT", 2.0) is None
    stl = {"p1_index": 1, "p2_index": 3, "p1": 5.0, "p2": 5.25}
    lows = [{"h": 9.0, "l": 4.0, "c": 7.0}, {"h": 9.0, "l": 5.0, "c": 7.0},
            {"h": 9.0, "l": 6.0, "c": 7.0}, {"h": 9.0, "l": 5.25, "c": 7.0}]
    assert structure_extreme(lows, stl, "LONG", 2.0) == 4.0
    assert structure_extreme(lows, None, "LONG", 2.0) is None and structure_extreme(lows, stl, "X", 2.0) is None
    with _env():
        assert struct_stop_max_atr() == 1.0
    with _env(TOUCH2_STRUCT_STOP_MAX_ATR="0.5"):
        assert struct_stop_max_atr() == 0.5


def test_fix5_double_top_family_authority():
    from backend.v9.gateway.trading_gateway import t621_double_top_family, t616_anchor_stop_is_structural
    s = {"classification": "DOUBLE_TOP_AA_SHORT", "stop": 7795.5, "metadata": {"structural_anchor": 7791.75}}
    with _env():
        assert t621_double_top_family(s) is False
    with _env(DOUBLE_TOP_STRUCT_STOP_V1="1"):
        assert t621_double_top_family(s) is True
        assert t621_double_top_family({"classification": "DOUBLE_BOTTOM_AA_LONG"}) is True
        assert t621_double_top_family({"classification": "CEILING_FLIP_SHORT"}) is False
        assert t621_double_top_family(None) is False
    assert t616_anchor_stop_is_structural(s, "SHORT") == (7795.5, 7791.75)      # #3558's stop is structural


def test_fix5_struct_stop_moves_a_stop_inside_the_structure_out():
    from backend.v9.gateway.trading_gateway import t621_struct_stop
    s1815 = {"stop": 7795.5, "metadata": {"structural_anchor": 7791.75}}
    s1835 = {"stop": 7783.25, "metadata": {"structural_anchor": 7791.75}}          # 20.10 18:35: the ATR-capped stop
    assert t621_struct_stop(s1815, "SHORT") == (7795.5, 7791.75, False)
    assert t621_struct_stop(s1835, "SHORT") == (7791.75, 7791.75, True)
    assert t621_struct_stop({"stop": 99.0, "metadata": {"structural_anchor": 100.0}}, "LONG") == (99.0, 100.0, False)
    assert t621_struct_stop({"stop": 101.0, "metadata": {"structural_anchor": 100.0}}, "LONG") == (100.0, 100.0, True)
    for bad in ({"stop": 1.0}, {"metadata": {"structural_anchor": 1.0}}, {"stop": "x", "metadata": {"structural_anchor": 1}}):
        assert t621_struct_stop(bad, "SHORT") is None
    assert t621_struct_stop(s1835, "FLAT") is None


def test_fix5_producer_wiring_is_flag_gated():
    src = open("backend/v9/systems/five_min/five_min_system.py", encoding="utf-8").read()
    i = src.index('os.getenv("DOUBLE_TOP_STRUCT_STOP_V1", "0")')
    j = src.index("_t2_stop = round(_t2_extreme + _t2_tick, 2)")
    assert i < j and "structure_extreme as _t2_sx" in src[i:j]
