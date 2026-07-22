"""REV_EDGE_DAY_STRUCTURE_V1 (Michael ruling 2026-07-22 'מאשר') — REV 'edge'
extended beyond prior-day value to DAY-STRUCTURE edges (day_low/high, IB
edges, opening extreme), with the SAME probe requirement against that level.

Root fixture: 2026-07-21 morning double-bottom at day-low 7521.0/7521.5
(bars 17:00+17:05 IL, second test closed 7533.25 = hard rejection) — price ran
to 7546.75. It was blocked 'not at VAL' because VAL 7496.75 was 25pt below and
day-structure edges were not recognized.
"""
import pytest

from backend.v9.systems.location_gate import (
    day_structure_edge, decide_location, probe_level)

VAH, VAL = 7535.25, 7496.75
IBW = 28.75  # tol = min(max(0.25*28.75,1),4) = 4.0

# yesterday's real morning bars (16:30-17:05 IL)
SESSION = [
    {"high": 7536.0, "low": 7529.0, "close": 7530.5},   # 16:30 open bar
    {"high": 7530.0, "low": 7524.25, "close": 7526.25},
    {"high": 7526.5, "low": 7521.0, "close": 7524.0},   # 16:40 day low 7521.0
    {"high": 7529.5, "low": 7528.0, "close": 7528.25},
    {"high": 7529.0, "low": 7526.0, "close": 7527.0},
    {"high": 7524.5, "low": 7521.5, "close": 7523.75},  # 17:00 first test
    {"high": 7533.5, "low": 7521.5, "close": 7533.25},  # 17:05 retest + hard rejection
]
DAY_LEVELS = {"vah": VAH, "val": VAL, "ib_width": IBW,
              "day_low": 7521.0, "day_high": 7536.0,
              "open_low": 7529.0, "open_high": 7536.0,
              "ib_low": 7504.5, "ib_high": 7533.25}


def _decide(entry, stop, flag_on, monkeypatch, direction="LONG", bars=SESSION):
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    monkeypatch.setenv("REV_EDGE_DAY_STRUCTURE_V1", "1" if flag_on else "0")
    return decide_location(
        family="REV", direction=direction, day_type="Variation",
        entry_price=entry, levels=DAY_LEVELS, expansion=None,
        recent_bars=bars, stop_price=stop, session_bars=bars)


def test_yesterday_double_bottom_now_allowed(monkeypatch):
    """REV LONG entry 7530 stop 7519.5: mid_value by VA (was the block) — but
    the stop sits 1.5pt from day_low 7521.0 and bars 17:00/17:05 PROBED the
    level with rejection closes → ALLOW."""
    allow, reason = _decide(7530.0, 7519.5, flag_on=True, monkeypatch=monkeypatch)
    assert allow, reason
    assert "day-structure edge" in reason and "day_low" in reason


def test_same_case_flag_off_still_blocked(monkeypatch):
    allow, reason = _decide(7530.0, 7519.5, flag_on=False, monkeypatch=monkeypatch)
    assert not allow
    assert "wrong location" in reason


def test_day_edge_without_probe_blocked(monkeypatch):
    """At the day-low edge but NO bar ever probed the level (falling knife
    protection): entry/stop near day_low, bars never touched it with a
    rejection close → BLOCK with precise reason."""
    bars = [
        {"high": 7536.0, "low": 7529.0, "close": 7530.5},
        {"high": 7530.0, "low": 7523.0, "close": 7523.5},  # sliding, no rejection close
    ]
    lv = dict(DAY_LEVELS, day_low=7523.0)
    monkeypatch.setenv("DAYTYPE_LOCATION_GATE", "1")
    monkeypatch.setenv("REV_EDGE_DAY_STRUCTURE_V1", "1")
    allow, reason = decide_location(
        family="REV", direction="LONG", day_type="Variation",
        entry_price=7524.0, levels=lv, expansion=None,
        recent_bars=bars, stop_price=7521.5, session_bars=bars)
    assert not allow
    assert "no probe" in reason


def test_mid_range_far_from_all_edges_still_blocked(monkeypatch):
    """The #372/#439 class stays dead: mid-value, far from every day edge."""
    allow, reason = _decide(7515.0, 7511.0, flag_on=True, monkeypatch=monkeypatch)
    assert not allow


def test_va_edge_path_unchanged(monkeypatch):
    """Correct VA edge + VA probe → allowed exactly as v2 (no regression)."""
    bars = SESSION + [{"high": 7536.5, "low": 7533.0, "close": 7534.0}]  # probed VAH, closed back
    allow, reason = _decide(7534.5, 7538.0, flag_on=True, monkeypatch=monkeypatch,
                            direction="SHORT", bars=bars)
    assert allow, reason


def test_probe_level_touch_tolerance():
    """17:00/17:05 lows were 7521.5 vs day_low 7521.0 — touch within 0.5 counts."""
    ok, why = probe_level("LONG", 7521.0, SESSION)
    assert ok and "rejected" in why
    ok2, _ = probe_level("LONG", 7519.0, SESSION)  # never within 0.5
    assert not ok2


def test_day_structure_edge_uses_stop_as_proxy():
    e = day_structure_edge("LONG", 7530.0, 7519.5, DAY_LEVELS, tol=4.0)
    assert e == ("day_low", 7521.0)  # stop 1.5pt from day_low wins (names order)
    # without the stop: entry 7530 is 1pt from open_low 7529 — a legitimate
    # opening-extreme edge match (Dalton: opening low is an edge)
    assert day_structure_edge("LONG", 7530.0, None, DAY_LEVELS, tol=4.0) == ("open_low", 7529.0)
    # far from everything → None
    assert day_structure_edge("LONG", 7512.0, None, DAY_LEVELS, tol=4.0) is None
    e3 = day_structure_edge("SHORT", 7534.5, 7538.5, DAY_LEVELS, tol=4.0)
    assert e3 and e3[0] in ("day_high", "open_high")
