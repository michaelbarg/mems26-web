"""T-618 (Michael 20.10, #3582): T1 in FRONT of the level — T1_FRONT_RUN_TICKS.

#3582 LONG 7754.5 (stop 7749.25): T1 7768.5 = the 18:15/18:55/19:00 triple top; the high came to 7768.25
(one tick short), then the trade gave back +13.75 pt to its stop (−90$).
"""
import os
import pathlib
from unittest.mock import patch

from backend.v9.gateway.trading_gateway import t618_front_run_t1, t618_front_run_ticks

ROOT = pathlib.Path(__file__).resolve().parents[3]


def _env(**kv):
    base = {k: v for k, v in os.environ.items() if k not in ("T1_FRONT_RUN_TICKS", "T1_REALISM_FLOOR_R_V1")}
    base.update(kv)
    return patch.dict(os.environ, base, clear=True)


def _s(d="LONG", e=7754.5, stop=7749.25, t1=7768.5):
    return {"direction": d, "entry_price": e, "stop": stop, "t1": t1, "t2": 7770.25, "t3": 7780.75,
            "metadata": {"stop_initial": stop}}


def test_parse():
    for raw, want in (("", 0), ("0", 0), ("2", 2), ("2.0", 2), ("-1", 0), ("x", 0), (" 3 ", 3)):
        with _env(T1_FRONT_RUN_TICKS=raw):
            assert t618_front_run_ticks() == want, raw


def test_off_is_byte_identical():
    s = _s()
    before = repr(s)
    with _env():
        assert t618_front_run_t1(s) is None
    assert repr(s) == before


def test_3582_long_two_ticks_in_front_of_the_triple_top():
    s = _s()
    with _env(T1_FRONT_RUN_TICKS="2", T1_REALISM_FLOOR_R_V1="1.5"):
        assert t618_front_run_t1(s) == (7768.5, 7768.0)
    assert s["t1"] == 7768.0 and s["metadata"]["t1_pre_front_run"] == 7768.5
    assert s["t2"] == 7770.25 and s["t3"] == 7780.75          # only T1 moves
    assert 7768.25 >= s["t1"]                                 # the 20:50 high now fills it


def test_short_moves_up():
    s = _s("SHORT", 7757.0, 7767.75, 7748.0)
    with _env(T1_FRONT_RUN_TICKS="2"):
        assert t618_front_run_t1(s) == (7748.0, 7748.5)


def test_never_to_or_behind_the_entry():
    s = _s(t1=7754.75)                                        # one tick beyond the entry
    with _env(T1_FRONT_RUN_TICKS="2"):
        assert t618_front_run_t1(s) is None
    assert s["t1"] == 7754.75
    s = _s(t1=7755.25)                                        # three ticks ⇒ room for two
    with _env(T1_FRONT_RUN_TICKS="2"):
        assert t618_front_run_t1(s) == (7755.25, 7754.75)


def test_respects_the_t1_realism_floor():
    # risk 10 ⇒ 1.5R = 15.0; T1 15.25 away ⇒ only one tick of front-run is allowed
    s = _s(e=7700.0, stop=7690.0, t1=7715.25)
    with _env(T1_FRONT_RUN_TICKS="2", T1_REALISM_FLOOR_R_V1="1.5"):
        assert t618_front_run_t1(s) == (7715.25, 7715.0)
    s = _s(e=7700.0, stop=7690.0, t1=7715.0)                  # exactly on the floor ⇒ no room
    with _env(T1_FRONT_RUN_TICKS="2", T1_REALISM_FLOOR_R_V1="1.5"):
        assert t618_front_run_t1(s) is None


def test_bad_inputs_are_safe():
    with _env(T1_FRONT_RUN_TICKS="2"):
        assert t618_front_run_t1({"direction": "LONG", "entry_price": None, "t1": 7768.5}) is None
        assert t618_front_run_t1({"direction": "FLAT", "entry_price": 1.0, "t1": 2.0}) is None
        assert t618_front_run_t1({"direction": "LONG", "entry_price": "x", "t1": 2.0}) is None
        assert t618_front_run_t1({"direction": "LONG", "entry_price": 10.0, "t1": 9.0}) is None   # wrong side


def test_hook_sits_after_the_gates_before_any_execution():
    src = (ROOT / "backend/v9/gateway/trading_gateway.py").read_text(encoding="utf-8")
    i_hook = src.index("_t618 = t618_front_run_t1(setup)")
    i_shadow = src.index("shadow_trade = self._execute_shadow(setup, system_id, cross_context)")
    i_demo = src.index("demo_trade = self._execute_demo(setup, system_id, cross_context)")
    i_rr = src.index('result["blocked_by"] = "rr_hard_floor"')
    assert i_rr < i_hook < i_shadow < i_demo
