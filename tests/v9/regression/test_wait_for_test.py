"""T-635 D3-gate · WAIT_FOR_TEST_V1 (22.10.2026) — no entry 0–1 closed bars after an impulse.

Real 5-min bars (h, l, c) from v9_bars_5min_woodies, the last one = the signal bar of each demo trade
(docs/reports/day_reviews/TRADE_ZOOM_2026-10-22.md). ATR14 as the zoom printed it.
"""
import os
from unittest.mock import patch

from backend.v9.systems.wait_for_test import push_without_pause


def _bars(*hlc):
    return [{"h": h, "l": l, "c": c} for h, l, c in hlc]


# 21.10 #3660 TOUCH2 SHORT 17:55 (signal 17:50): +14.25 closes 17:35→17:45, then one bar — fade INTO the push
B3660 = _bars((7761.75, 7752.25, 7758.25), (7764.0, 7755.5, 7761.0), (7768.5, 7760.0, 7766.5), (7768.0, 7761.25, 7762.5),
              (7771.75, 7762.0, 7769.25), (7778.5, 7769.0, 7776.75), (7779.5, 7774.25, 7775.0))
# 21.10 #3670 TOUCH2 SHORT 18:45 (signal 18:40): +13.25 closes 18:20→18:35, one bar later
B3670 = _bars((7782.75, 7777.75, 7782.0), (7784.5, 7777.0, 7777.5), (7783.75, 7776.25, 7780.75), (7789.25, 7779.75, 7787.5),
              (7790.0, 7786.75, 7788.5), (7795.75, 7788.0, 7794.0), (7794.5, 7791.5, 7793.0))
# 21.10 #3696 TOUCH2 SHORT 19:45 (signal 19:40): the 19:35 spike bar (16.5 pt) and the 11.5-pt signal bar
B3696 = _bars((7793.75, 7790.25, 7793.25), (7794.25, 7791.75, 7792.75), (7794.25, 7791.0, 7792.25), (7792.25, 7787.75, 7790.25),
              (7791.75, 7788.75, 7790.0), (7805.75, 7789.25, 7804.0), (7806.5, 7795.0, 7798.0))
# 20.10 #3558 DOUBLE_TOP SHORT 18:15 (signal 18:10 = the climax bar, −31.5 pt / 57k)
B3558 = _bars((7787.0, 7777.25, 7783.5), (7787.0, 7779.75, 7781.0), (7787.5, 7779.5, 7786.0), (7790.5, 7784.25, 7785.0),
              (7785.5, 7777.75, 7778.5), (7781.0, 7777.0, 7777.75), (7778.25, 7746.75, 7756.75))
# 21.10 #3687 TOUCH2 SHORT 19:20 (signal 19:15): six flat bars — a pause, the winner
B3687 = _bars((7796.25, 7793.0, 7796.0), (7796.75, 7793.25, 7793.75), (7795.5, 7793.0, 7794.0), (7795.0, 7791.0, 7792.75),
              (7794.0, 7789.75, 7791.25), (7793.75, 7790.25, 7793.25), (7794.25, 7791.75, 7792.75))
# 21.10 #3702 TOUCH2 SHORT 20:25 (signal 20:20): a slow grind, the winner
B3702 = _bars((7802.75, 7797.0, 7802.75), (7804.0, 7801.5, 7801.75), (7803.5, 7799.0, 7801.75), (7807.25, 7801.0, 7806.25),
              (7807.75, 7804.5, 7806.25), (7809.75, 7806.0, 7808.5), (7810.75, 7807.25, 7807.75))
# 20.10 #3582 TOUCH2 LONG 20:05 (signal 20:00): the −9.75 dip of 19:50 is < 1.5 ATR — not this gate's class (B)
B3582 = _bars((7764.0, 7758.0, 7760.75), (7766.5, 7760.0, 7762.75), (7765.0, 7758.25, 7761.0), (7763.5, 7757.25, 7762.0),
              (7762.0, 7749.5, 7752.25), (7756.5, 7752.5, 7754.25), (7757.25, 7750.0, 7754.5))


def test_fades_into_a_fresh_push_are_blocked():
    v = push_without_pause(B3660, 8.82)
    assert v["blocked"] and v["end_i"] == 5 and v["kind"] == "close" and v["impulse_pts"] == 14.25
    v = push_without_pause(B3670, 6.39)
    assert v["blocked"] and v["end_i"] == 5 and v["impulse_pts"] == 13.25
    v = push_without_pause(B3696, 5.21)
    assert v["blocked"] and v["end_i"] == 5 and v["kind"] == "bar" and v["impulse_pts"] == 16.5


def test_the_climax_bar_itself_is_blocked():
    v = push_without_pause(B3558, 10.59)
    assert v["blocked"] and v["end_i"] == 6 and v["impulse_pts"] == 31.5 and "wait for the test" in v["why"]


def test_entries_after_a_pause_pass():
    assert push_without_pause(B3687, 4.8)["blocked"] is False
    assert push_without_pause(B3702, 5.38)["blocked"] is False
    assert push_without_pause(B3582, 7.3571)["blocked"] is False


def test_an_impulse_two_bars_ago_is_a_pause_not_a_push():
    # the #3660 push, then TWO overlapping bars: the pause printed ⇒ the next entry is judged by the test, not here
    paused = B3660 + _bars((7778.0, 7773.5, 7776.0))
    assert push_without_pause(paused, 8.82)["blocked"] is False
    # but recent=3 would still see it (the parameter is the measurement's business)
    assert push_without_pause(paused, 8.82, recent=3)["blocked"] is True


def test_fail_open_without_atr_or_bars():
    assert push_without_pause(B3660, None)["blocked"] is False
    assert push_without_pause([], 8.0)["blocked"] is False
    assert push_without_pause(B3660[:1], 8.0)["blocked"] is False


def test_flag_default_off_and_wired_in_the_gateway():
    env = {k: v for k, v in os.environ.items() if k != "WAIT_FOR_TEST_V1"}
    with patch.dict(os.environ, env, clear=True):
        assert os.getenv("WAIT_FOR_TEST_V1", "0").strip().lower() not in ("1", "true", "yes")
    src = open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "v9", "gateway", "trading_gateway.py"), encoding="utf-8").read()
    assert 'os.getenv("WAIT_FOR_TEST_V1", "0")' in src and '"wait_for_test"' in src
