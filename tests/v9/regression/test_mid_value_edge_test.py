"""T-635 D2 · MID_VALUE_EDGE_TEST_V1 (22.10.2026) — inside value only as the test of an edge.

The six inside-value demo entries of 19–20.10 (all losers, −337.5$) and the three winners, with the
exact bars / levels the zoom-in printed (docs/reports/day_reviews/TRADE_ZOOM_2026-10-22.md).
"""
import os
from unittest.mock import patch

from backend.v9.systems.mid_value_edge_test import mid_value_edge_test, is_mid_value, bars_atr


def _b(h, l):
    return {"h": h, "l": l}


# 19.10 levels (cross_context tpo_system at the fires) + yesterday (16.10) VA 7693.50–7780.50, H/L 7803/7676
L1910 = dict(ib_low=7727.5, ib_high=7759.75, prev_val=7693.5, prev_vah=7780.5, prev_low=7676.0, prev_high=7803.0)
# 20.10 levels + yesterday (19.10) VA 7732.25–7750.50, H/L 7773.25/7727.50
L2010 = dict(val=7743.25, ib_low=7710.25, ib_high=7786.0, prev_val=7732.25, prev_vah=7750.5, prev_low=7727.5, prev_high=7773.25)


def test_3501_bought_the_poc_9_5_pts_above_the_tested_val():
    lv = dict(L1910, val=7735.5, vah=7758.25)
    assert is_mid_value(7745.0, lv["vah"], lv["val"], 7745.0, 5.12)
    v = mid_value_edge_test("LONG", 7745.0, [_b(7741.75, 7736.25), _b(7745.75, 7738.0)], lv, 5.12)
    assert v["ok"] is False and v["edge"] == 7735.5 and "middle after the test" in v["why"]


def test_3508_no_edge_in_the_last_two_bars():
    lv = dict(L1910, val=7735.5, vah=7757.0)
    assert is_mid_value(7747.25, lv["vah"], lv["val"], 7746.75, 5.39)
    v = mid_value_edge_test("LONG", 7747.25, [_b(7747.75, 7743.5), _b(7748.5, 7745.25)], lv, 5.39)
    assert v["ok"] is False and v["tested"] == [] and "without a test" in v["why"]


def test_3515_bar_touched_val_but_entry_6_5_pts_above():
    lv = dict(L1910, val=7735.5, vah=7756.25)
    v = mid_value_edge_test("LONG", 7742.0, [_b(7741.0, 7736.75), _b(7742.75, 7735.5)], lv, 5.71)
    assert v["ok"] is False and v["edge"] == 7735.5
    # the SAME bar, entered at the test (7737 — 1.5 pt off the VAL) is a legitimate responsive long
    ok = mid_value_edge_test("LONG", 7737.0, [_b(7741.0, 7736.75), _b(7742.75, 7735.5)], lv, 5.71)
    assert ok["ok"] is True and ok["edge"] == 7735.5


def test_3574_tested_yesterdays_vah_entered_8_75_pts_higher():
    lv = dict(L2010, vah=7781.75)
    assert is_mid_value(7759.75, lv["vah"], lv["val"], 7752.75, 7.91)
    v = mid_value_edge_test("LONG", 7759.75, [_b(7757.25, 7751.0), _b(7761.75, 7752.75)], lv, 7.91)
    assert v["ok"] is False and v["edge"] == 7750.5 and "prev_vah" in v["why"]


def test_3582_on_the_poc_4_pts_above_prev_vah_is_still_the_middle():
    lv = dict(L2010, vah=7779.25)
    assert is_mid_value(7754.5, lv["vah"], lv["val"], 7752.75, 7.3571)
    v = mid_value_edge_test("LONG", 7754.5, [_b(7756.5, 7752.5), _b(7757.25, 7750.0)], lv, 7.3571)
    assert v["ok"] is False and v["edge"] == 7750.5   # 4.0 pt = 0.54 ATR > 0.5 ATR


def test_3483_val_tested_entry_5_75_above():
    lv = dict(L1910, val=7737.25, vah=7761.0)
    v = mid_value_edge_test("LONG", 7743.0, [_b(7744.25, 7738.5), _b(7744.5, 7738.75)], lv, 5.27)
    assert v["ok"] is False and v["edge"] == 7737.25


def test_winners_are_not_inside_value_so_the_gate_does_not_apply():
    # #3544 OPENING_ORR LONG 7729 — near VAH 7728.25 (IB edge), not the middle
    assert not is_mid_value(7729.0, 7728.25, 7713.25, 7720.75, 15.67)
    # #3687 / #3702 SHORT above value (vah 7783.5 / 7792.0)
    assert not is_mid_value(7792.75, 7783.5, 7757.25, 7774.25, 4.8)
    assert not is_mid_value(7807.75, 7792.0, 7754.25, 7777.0, 5.38)


def test_short_mirror_and_fail_open():
    lv = dict(vah=7778.5, val=7763.0, ib_high=7780.75, ib_low=7751.0, prev_vah=7762.75, prev_val=7713.0, prev_high=7791.5)
    # a short at 7777 right after the bar touched VAH 7778.5 (hi2 7779.5) — a legitimate edge fade
    v = mid_value_edge_test("SHORT", 7777.0, [_b(7778.5, 7769.0), _b(7779.5, 7774.25)], lv, 8.82)
    assert v["ok"] is True and v["edge"] == 7778.5
    # no bars / no atr ⇒ never blocks blind
    assert mid_value_edge_test("SHORT", 7777.0, [], lv, None)["ok"] is True
    assert mid_value_edge_test("LONG", 7745.0, [_b(7741.75, 7736.25)], lv, None)["ok"] is True  # 1 bar: no ATR proxy
    assert bars_atr([_b(10, 9), _b(12, 10), _b(11, 9.5)]) == (1 + 2 + 1.5) / 3


def test_flag_default_off_in_the_gateway_source():
    # the gate is env-gated at call time; a fresh environment has it unset
    env = {k: v for k, v in os.environ.items() if k != "MID_VALUE_EDGE_TEST_V1"}
    with patch.dict(os.environ, env, clear=True):
        assert os.getenv("MID_VALUE_EDGE_TEST_V1", "0").strip().lower() not in ("1", "true", "yes")
    src = open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "v9", "gateway", "trading_gateway.py"), encoding="utf-8").read()
    assert 'os.getenv("MID_VALUE_EDGE_TEST_V1", "0")' in src and '"mid_value_no_edge_test"' in src
