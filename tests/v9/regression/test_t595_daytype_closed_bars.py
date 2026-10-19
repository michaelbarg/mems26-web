# -*- coding: utf-8 -*-
"""T-595 (19.10, Michael: "fix all the gaps"): DAYTYPE_MACHINE_CLOSED_BARS_V1 -- the day-type state machine judges
CLOSED 5-minute bars.

Finding: `_day_type_on_bar` (backend/main.py) de-duplicates the '5min' topic by bar ts (the bridge re-publishes the
developing bar ~41x per 5 minutes), so `DayTypeStateMachine.process_bar` only ever received the FIRST push of each bar --
flat (o=h=l=c), ~1% of the volume.  "OPEN_DRIVE" on 147 of 166 reconstructed days on flat bars, 31 of 166 on closed bars;
the first-hour Trend_Normal artifact (154/166); the acceptance demotion and the exhaustion veto judged a point.

Fix: with the flag ON the machine is fed the bar as it stood at its LAST push, handed over when the next ts arrives.
Default OFF: main.py runs exactly the code it ran before.

These tests run the REAL `_day_type_on_bar` closure out of backend/main.py (see _daytype_handler_harness) against a real
DayTypeStateMachine -- flag OFF must feed the first push as before, flag ON three pushes of one ts + a new ts must give
the machine ONE bar carrying the LAST push's OHLCV and never the flat first push.
"""
import logging
import os
from datetime import time as dtime

import pytest

from backend.v9.services.market_clock import minutes_since_rth_open
from backend.v9.systems.day_type import closed_bar_feed as cbf
from backend.v9.systems.day_type.schemas import BarInput, DayType
from tests.v9.regression._daytype_handler_harness import (
    PD, ROOT, UTC, Harness, bar_pushes, et, payload)

FLAG = "DAYTYPE_MACHINE_CLOSED_BARS_V1"
MAIN = os.path.join(ROOT, "backend", "main.py")

# b0 down, b1 up, b2 down: the FIRST pushes (each bar's open) walk 100.00 -> 100.50 -> 101.00 -- a monotone "drive" on
# flat bars -- while the CLOSED bars are a rotation that nets nothing (AUCTION_IN).
BARS = [
    (et(9, 30), (100.0, 101.5, 98.5, 99.0, 900)),
    (et(9, 35), (100.5, 102.0, 99.0, 101.25, 1100)),
    (et(9, 40), (101.0, 102.5, 99.5, 100.0, 1000)),
    (et(9, 45), (100.25, 101.0, 99.75, 100.5, 700)),
]


def _floats(final):
    return tuple(float(x) for x in final)


@pytest.fixture(autouse=True)
def _fresh_warn_limiter():
    cbf._last_warn.clear()


# ── the flag ────────────────────────────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("val,expected", [
    (None, False), ("", False), ("0", False), ("off", False), ("no", False), ("false", False),
    ("1", True), ("true", True), ("TRUE", True), ("yes", True), (" 1 ", True)])
def test_flag_is_read_at_call_time_and_defaults_off(monkeypatch, val, expected):
    if val is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, val)
    assert cbf.FLAG == FLAG
    assert cbf.enabled() is expected


# ── ClosedBarFeed ───────────────────────────────────────────────────────────────────────────────────────────────────


def test_feed_hands_over_the_last_push_of_the_previous_ts():
    feed = cbf.ClosedBarFeed()
    t0, t1 = et(9, 30), et(9, 35)
    assert feed.on_new_ts(payload(t0, 100.0, 100.0, 100.0, 100.0, 12)) is None   # first bar after a start: nothing closed
    feed.note_push(payload(t0, 100.0, 101.0, 99.0, 100.5, 400))                  # main.py's dedup branch
    feed.note_push(payload(t0, 100.0, 101.5, 98.5, 99.0, 900))
    closed = feed.on_new_ts(payload(t1, 100.5, 100.5, 100.5, 100.5, 13))
    assert (closed["o"], closed["h"], closed["l"], closed["c"], closed["v"]) == (100.0, 101.5, 98.5, 99.0, 900.0)
    assert closed["first_range"] == 0.0 and closed["first_v"] == 12.0 and closed["pushes"] == 3
    assert feed.held["dt"] == t1.astimezone(UTC)        # the new ts is now the bar being built


def test_feed_every_closed_bar_is_a_whole_bar_never_the_flat_first_push():
    feed, closed, prev = cbf.ClosedBarFeed(), [], None
    for start, final in BARS:
        for _wall, body in bar_pushes(start, final):
            if body["ts"] == prev:
                feed.note_push(body)
                continue
            prev = body["ts"]
            c = feed.on_new_ts(body)
            if c is not None:
                closed.append(c)
    assert [(c["o"], c["h"], c["l"], c["c"], c["v"]) for c in closed] == [_floats(f) for _, f in BARS[:3]]
    assert all(c["h"] > c["l"] and c["v"] > 100 for c in closed)


def test_feed_same_instant_in_another_spelling_is_not_a_new_bar():
    feed, t0 = cbf.ClosedBarFeed(), et(9, 30)
    assert feed.on_new_ts(payload(t0, 100.0, 100.0, 100.0, 100.0, 12)) is None
    again = dict(payload(t0, 100.0, 101.5, 98.5, 99.0, 900), ts=int(t0.timestamp()))   # epoch seconds, same instant
    assert feed.on_new_ts(again) is None                  # main.py's raw-ts dedup missed it; the feed must not
    assert feed.held["c"] == 99.0 and feed.held["pushes"] == 2
    nxt = feed.on_new_ts(payload(et(9, 35), 100.5, 100.5, 100.5, 100.5, 13))
    assert (nxt["c"], nxt["v"]) == (99.0, 900.0)


def test_feed_older_ts_is_ignored_and_never_replaces_the_newer_bar():
    feed = cbf.ClosedBarFeed()
    assert feed.on_new_ts(payload(et(9, 35), 100.5, 100.5, 100.5, 100.5, 13)) is None
    assert feed.on_new_ts(payload(et(9, 30), 100.0, 101.5, 98.5, 99.0, 900)) is None   # replayed / out-of-order
    assert feed.held["dt"] == et(9, 35).astimezone(UTC) and feed.held["o"] == 100.5


def test_feed_never_judges_a_sessions_last_bar_inside_the_next_session():
    feed = cbf.ClosedBarFeed()
    feed.on_new_ts(payload(et(15, 55, day=16), 100.0, 101.0, 99.0, 100.5, 800))       # Friday 15:55 ET
    assert feed.on_new_ts(payload(et(9, 30), 100.0, 100.0, 100.0, 100.0, 12)) is None  # Monday 09:30 ET
    assert feed.held["dt"] == et(9, 30).astimezone(UTC)
    # inside one ET date the Globex 09:25 bar IS handed over when the 09:30 bar starts
    feed2 = cbf.ClosedBarFeed()
    feed2.on_new_ts(payload(et(9, 25), 99.0, 99.5, 98.5, 99.0, 300))
    assert feed2.on_new_ts(payload(et(9, 30), 100.0, 100.0, 100.0, 100.0, 12))["c"] == 99.0


@pytest.mark.parametrize("bad", [{}, {"ts": None}, {"ts": ""}, {"ts": "not a time"}])
def test_feed_bar_without_a_usable_ts_raises(bad):
    with pytest.raises(ValueError):
        cbf.ClosedBarFeed().on_new_ts(dict(bad, open=1, high=1, low=1, close=1))


@pytest.mark.parametrize("field,value", [("open", "x"), ("high", None), ("close", float("nan")), ("low", float("inf"))])
def test_feed_unusable_ohlcv_raises_and_forgets_the_held_bar(field, value):
    feed = cbf.ClosedBarFeed()
    feed.on_new_ts(payload(et(9, 30), 100.0, 101.0, 99.0, 100.5, 800))
    body = payload(et(9, 35), 100.5, 100.5, 100.5, 100.5, 13)
    body[field] = value
    body.pop({"open": "o", "high": "h", "low": "l", "close": "c"}[field], None)
    with pytest.raises(Exception):
        feed.on_new_ts(body)
    assert feed.held is None        # never keep a bar that could later be mistaken for the next one's predecessor


def test_note_push_only_refreshes_the_held_ts_and_never_raises(caplog):
    feed, t0, t1 = cbf.ClosedBarFeed(), et(9, 30), et(9, 35)
    feed.note_push(payload(t0, 100.0, 101.0, 99.0, 100.5, 400))                    # nothing held yet: ignored
    assert feed.held is None
    feed.on_new_ts(payload(t0, 100.0, 100.0, 100.0, 100.0, 12))
    feed.note_push(payload(t1, 100.5, 102.0, 99.0, 101.0, 500))                    # another ts: ignored
    assert feed.held["h"] == 100.0 and feed.held["pushes"] == 1
    with caplog.at_level(logging.WARNING, logger=cbf.__name__):
        feed.note_push({"ts": str(t0.astimezone(UTC)), "open": "boom"})            # garbage: kept as it was, one WARNING
        feed.note_push(None)                                                       # not even a dict: still no raise
    assert feed.held["h"] == 100.0 and feed.held["pushes"] == 1
    assert [r.levelno for r in caplog.records].count(logging.WARNING) == 1          # rate-limited, not 41 per bar


def test_feed_reset_forgets_the_held_bar():
    feed = cbf.ClosedBarFeed()
    feed.on_new_ts(payload(et(9, 30), 100.0, 100.0, 100.0, 100.0, 12))
    feed.reset()
    assert feed.held is None


# ── closed_input / run_machine ──────────────────────────────────────────────────────────────────────────────────────


def _wall(wall_et, is_rth, o=100.0, v=12.0):
    return BarInput(ts=wall_et.timestamp(), session_min=minutes_since_rth_open(wall_et), is_rth=is_rth,
                    open=o, high=o, low=o, close=o, volume=v, ib_high=111.0, ib_low=99.0, **PD)


def _closed(start_et, o=100.0, h=101.5, l=98.5, c=99.0, v=900.0):
    return {"ts": str(start_et.astimezone(UTC)), "dt": start_et.astimezone(UTC), "o": o, "h": h, "l": l, "c": c, "v": v,
            "first_range": 0.0, "first_v": 12.0, "pushes": 3}


def test_closed_input_takes_rth_from_the_bars_own_timestamp():
    # the Globex 09:25 bar closes at 09:30:03 -- the wall clock says RTH, the bar is not
    assert cbf.closed_input(_wall(et(9, 30, 3), True), _closed(et(9, 25))).is_rth is False
    # the 15:55 bar closes at 16:00:03 -- the wall clock says not-RTH, the bar is
    assert cbf.closed_input(_wall(et(16, 0, 3), False), _closed(et(15, 55))).is_rth is True
    assert cbf.closed_input(_wall(et(9, 35, 3), True), _closed(et(9, 30))).is_rth is True      # 09:30 itself is RTH
    assert cbf.closed_input(_wall(et(16, 5, 3), False), _closed(et(16, 0))).is_rth is False    # 16:00 is not


def test_closed_input_distrusts_a_timestamp_far_from_the_wall_clock():
    # a mis-read ts (4 h off the wall clock): the bar's own RTH verdict is not trusted, today's wall flag stays
    off = _closed(et(5, 30))
    assert cbf.closed_input(_wall(et(9, 35, 3), True), off).is_rth is True
    assert cbf.closed_input(_wall(et(9, 35, 3), False), off).is_rth is False


def test_closed_input_changes_only_the_bar_and_leaves_the_wall_input_alone():
    wall = _wall(et(9, 35, 3), True, o=100.5, v=13.0)
    out = cbf.closed_input(wall, _closed(et(9, 30)))
    assert (out.open, out.high, out.low, out.close, out.volume) == (100.0, 101.5, 98.5, 99.0, 900.0)
    for f in ("ts", "session_min", "pd_high", "pd_low", "pd_close", "ib_high", "ib_low"):
        assert getattr(out, f) == getattr(wall, f)
    assert (wall.open, wall.high, wall.volume) == (100.5, 100.5, 13.0)       # the wall input is a new object, untouched


class _FakeMachine:
    def __init__(self, fail_on_closed=False):
        self.calls, self._last_state, self.fail_on_closed = [], None, fail_on_closed

    def process_bar(self, bar):
        self.calls.append(bar)
        if self.fail_on_closed and bar.high > bar.low:
            raise RuntimeError("boom")
        self._last_state = "state-%d" % len(self.calls)
        return self._last_state

    def _build_state(self, bar):
        return "built-state"


def test_run_machine_nothing_closed_does_not_advance_the_machine():
    m, feed = _FakeMachine(), cbf.ClosedBarFeed()
    wall = _wall(et(9, 30, 3), True)
    assert cbf.run_machine(m, feed, payload(et(9, 30), 100.0, 100.0, 100.0, 100.0, 12), wall) == ("built-state", None)
    assert m.calls == []
    # second ts: the 09:30 bar closed -> the machine advances once, and the judged bar is returned for the demotion
    state, judged = cbf.run_machine(m, feed, payload(et(9, 35), 100.5, 100.5, 100.5, 100.5, 13), _wall(et(9, 35, 3), True))
    assert state == "state-1" and len(m.calls) == 1 and judged is m.calls[0]
    # an older ts: nothing to judge, the cached state is returned and the machine is not touched
    assert cbf.run_machine(m, feed, payload(et(9, 30), 1, 1, 1, 1, 1), _wall(et(9, 35, 5), True)) == ("state-1", None)
    assert len(m.calls) == 1


def test_run_machine_failure_feeds_the_first_push_input_as_before_and_warns(caplog):
    m, feed = _FakeMachine(fail_on_closed=True), cbf.ClosedBarFeed()
    cbf.run_machine(m, feed, payload(et(9, 30), 100.0, 100.0, 100.0, 100.0, 12), _wall(et(9, 30, 3), True))
    feed.note_push(payload(et(9, 30), 100.0, 101.5, 98.5, 99.0, 900))        # the bar grows: the closed bar is not flat
    wall = _wall(et(9, 35, 3), True, o=100.5, v=13.0)
    with caplog.at_level(logging.WARNING, logger=cbf.__name__):
        state, judged = cbf.run_machine(m, feed, payload(et(9, 35), 100.5, 100.5, 100.5, 100.5, 13), wall)
    assert judged is wall and m.calls[-1] is wall and state == "state-2"       # the old behaviour: the wall input
    assert any("closed-bar feed failed" in r.getMessage() for r in caplog.records)


def test_run_machine_bar_without_ts_is_the_old_feed_not_a_crash(caplog):
    m, wall = _FakeMachine(), _wall(et(9, 30, 3), True)
    with caplog.at_level(logging.WARNING, logger=cbf.__name__):
        state, judged = cbf.run_machine(m, cbf.ClosedBarFeed(), {"open": 1, "high": 1, "low": 1, "close": 1}, wall)
    assert judged is wall and m.calls == [wall]


# ── the real `_day_type_on_bar` closure ─────────────────────────────────────────────────────────────────────────────


def _legacy_input(wall_et, body):
    """The BarInput main.py has always built from a push: wall-clock ts/session_min/is_rth, the push's own OHLCV."""
    return BarInput(ts=wall_et.timestamp(), session_min=minutes_since_rth_open(wall_et),
                    is_rth=dtime(9, 30) <= wall_et.time() < dtime(16, 0),
                    open=body["open"], high=body["high"], low=body["low"], close=body["close"], volume=body["volume"],
                    ib_high=None, ib_low=None, **PD)


def test_handler_flag_off_machine_gets_the_first_push_exactly_as_before(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    h = Harness(monkeypatch)
    h.play(BARS)
    expected = [_legacy_input(*bar_pushes(start, final)[0]) for start, final in BARS]
    assert [b.model_dump() for b in h.fed] == [e.model_dump() for e in expected]
    assert all(b.open == b.high == b.low == b.close for b in h.fed)             # the flat first push, as always
    assert h.machine.opening.opening_type.value == "OPEN_DRIVE"                 # what flat monotone bars "see"
    assert h.warnings == []


def test_handler_flag_off_is_the_same_with_the_flag_spelled_zero(monkeypatch):
    monkeypatch.setenv(FLAG, "0")
    h = Harness(monkeypatch)
    h.play(BARS)
    assert len(h.fed) == len(BARS) and all(b.high == b.low for b in h.fed)


def test_handler_flag_on_machine_gets_one_closed_bar_per_ts_carrying_the_last_push(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    h = Harness(monkeypatch)
    h.play(BARS)
    # three pushes of every ts + the next ts: ONE bar per ts, with the LAST push's OHLCV -- the 4th is still developing
    assert [(b.open, b.high, b.low, b.close, b.volume) for b in h.fed] == [_floats(f) for _, f in BARS[:3]]
    assert all(b.high > b.low and b.volume > 100 for b in h.fed)                # never a flat first-push bar
    assert [b.session_min for b in h.fed] == [5, 10, 15]                        # wall-clock stage clock: judged on close
    assert all(b.is_rth for b in h.fed) and all(b.pd_close == PD["pd_close"] for b in h.fed)
    assert h.machine.opening.opening_type.value == "OPEN_AUCTION_IN"            # the closed bars rotate; flat ones "drove"
    assert h.warnings == []


def test_handler_flag_on_the_classifier_buffer_is_untouched(monkeypatch):
    """Design: only the machine feed changes; `_cls_rth_bars` (lock, tree, classifier) keeps its own semantics."""
    runs = []
    for flag in ("0", "1"):
        monkeypatch.setenv(FLAG, flag)
        h = Harness(monkeypatch)
        h.play(BARS)
        runs.append(list(h.cls_rth_bars))
    assert runs[0] == runs[1] and len(runs[0]) == len(BARS)


def test_handler_flag_on_repeat_pushes_never_reach_the_machine(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    h = Harness(monkeypatch)
    h.play(BARS[:1])                                    # three pushes of ONE ts: nothing closed yet
    assert h.fed == []
    wall, body = bar_pushes(*BARS[1])[0]                # the first push of the next ts closes the 09:30 bar
    h.push(wall, body)
    assert len(h.fed) == 1 and (h.fed[0].high, h.fed[0].low, h.fed[0].volume) == (101.5, 98.5, 900.0)
    h.push(wall, body)                                  # an exact repeat of that push: the dedup drops it
    assert len(h.fed) == 1


def test_handler_flag_on_rth_flag_comes_from_the_bar_not_the_wall_clock(monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    h = Harness(monkeypatch)
    h.play([(et(9, 25), (99.0, 99.5, 98.5, 99.0, 300)), BARS[0], BARS[1]])
    # the Globex 09:25 bar closes at 09:30:03 (wall clock: RTH) -- the machine must see it as NOT RTH
    assert [(b.close, b.is_rth) for b in h.fed] == [(99.0, False), (99.0, True)]
    h2 = Harness(monkeypatch)
    h2.play([(et(15, 50), (100.0, 101.0, 99.0, 100.5, 800)), (et(15, 55), (100.5, 101.5, 100.0, 101.0, 900)),
             (et(16, 0), (101.0, 101.5, 100.5, 101.0, 100))])
    # the 15:55 bar closes at 16:00:03 (wall clock: not RTH) -- the machine must see it as RTH
    assert (h2.fed[-1].close, h2.fed[-1].is_rth) == (101.0, True)


def _demotion_run(monkeypatch, flag, bars):
    monkeypatch.setenv(FLAG, flag)
    h = Harness(monkeypatch)
    monkeypatch.setenv("DAYTYPE_ACCEPTANCE_DEMOTION_V1", "1")
    monkeypatch.setenv("DAYTYPE_DEMOTION_K_BARS", "3")
    h.machine.day_type, h.machine.ib_high, h.machine.ib_low = DayType.Trend_Normal, 110.0, 90.0   # tol 4 -> inside = 94..106
    steps = []
    for start, final in bars:
        for wall, body in bar_pushes(start, final):
            h.push(wall, body)
        steps.append(h.machine.day_type)
    return h, steps


def test_handler_acceptance_demotion_counts_the_bar_the_machine_judged(monkeypatch):
    # first pushes sit inside the IB (flat at ~100); the CLOSED bars all reach 107+ -- outside the 94..106 band
    outside = [(et(9, 30), (100.0, 107.0, 99.0, 100.5, 900)), (et(9, 35), (100.5, 107.5, 99.5, 101.0, 900)),
               (et(9, 40), (101.0, 108.0, 99.5, 100.0, 900)), (et(9, 45), (100.0, 107.0, 99.0, 100.5, 900)),
               (et(9, 50), (100.5, 101.0, 100.0, 100.5, 700))]
    h_off, steps_off = _demotion_run(monkeypatch, "0", outside)
    assert steps_off[2] == DayType.Variation            # OFF: the flat first pushes are "inside" 3 times -> demoted
    h_on, steps_on = _demotion_run(monkeypatch, "1", outside)
    assert set(steps_on) == {DayType.Trend_Normal}      # ON: the judged (closed) bars are not inside -> no demotion
    assert h_on.app.state._dem_inside_count == 0


def test_handler_acceptance_demotion_waits_for_k_judged_bars_not_k_pushes(monkeypatch):
    inside = [(et(9, 30), (100.0, 102.0, 98.0, 100.5, 900)), (et(9, 35), (100.5, 102.5, 99.0, 101.0, 900)),
              (et(9, 40), (101.0, 103.0, 99.5, 100.0, 900)), (et(9, 45), (100.0, 102.0, 99.0, 100.5, 900)),
              (et(9, 50), (100.5, 101.0, 100.0, 100.5, 700))]
    _h, steps_off = _demotion_run(monkeypatch, "0", inside)
    assert steps_off[1] == DayType.Trend_Normal and steps_off[2] == DayType.Variation       # 3rd push
    _h, steps_on = _demotion_run(monkeypatch, "1", inside)
    # the 09:30 push judges nothing; the 09:35/09:40/09:45 pushes judge b0/b1/b2 -> demoted on the 4th push
    assert steps_on[:3] == [DayType.Trend_Normal] * 3 and steps_on[3] == DayType.Variation


def test_handler_flag_on_without_the_module_keeps_the_first_push_feed(monkeypatch):
    """main.py's import of the feed is fail-safe: `_t595 = None` -> the legacy line, flag or not."""
    monkeypatch.setenv(FLAG, "1")
    h = Harness(monkeypatch, t595=False)
    h.play(BARS)
    assert len(h.fed) == len(BARS) and all(b.high == b.low for b in h.fed)
    assert h.warnings == []


def test_handler_flag_on_a_failure_inside_the_feed_falls_back_and_warns(monkeypatch, caplog):
    monkeypatch.setenv(FLAG, "1")
    h = Harness(monkeypatch)

    def boom(self, bar):
        raise RuntimeError("boom")

    monkeypatch.setattr(cbf.ClosedBarFeed, "on_new_ts", boom)
    with caplog.at_level(logging.WARNING, logger=cbf.__name__):
        h.play(BARS[:2])
    assert len(h.fed) == 2 and all(b.high == b.low for b in h.fed)               # the old first-push feed
    assert any("closed-bar feed failed" in r.getMessage() for r in caplog.records)
    assert h.warnings == []                                                      # the handler itself did not trip


# ── main.py wiring (strings) ────────────────────────────────────────────────────────────────────────────────────────


def test_main_wiring_strings():
    s = open(MAIN, encoding="utf-8").read()
    assert "from backend.v9.systems.day_type import closed_bar_feed as _t595" in s
    assert "_t595_feed = _t595.ClosedBarFeed()" in s
    assert "if _t595 is not None and _t595.enabled():\n                    _t595_feed.note_push(bar)" in s
    assert "_t595_on = _t595 is not None and _t595.enabled()" in s
    assert "state, _dem_in = _t595.run_machine(day_type_machine, _t595_feed, bar, bar_input)" in s
    # the flag-OFF branch is the line it replaced, untouched
    assert ("                else:\n                    state = day_type_machine.process_bar(bar_input)\n"
            "                    _dem_in = bar_input\n") in s
    assert "if _ib_h is not None and _ib_l is not None and _dem_in is not None:" in s
    assert "_bar_h = _dem_in.high" in s and "_bar_l = _dem_in.low" in s
    assert "_bar_h = bar_input.high" not in s
