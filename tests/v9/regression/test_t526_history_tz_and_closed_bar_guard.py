"""T-526 — 12 woodies bars of 01.10 (18:00–18:55 IL) were overwritten with the 19:00–19:55 bars (+4h
instead of +5h). Two roots, two guards (fix-agent, night 07→08.10, BRIEF §3.2):

1. THE WRITER: the bridge restart of 01.10 23:07:47 ran the startup history backfill
   (bridge/v9_history.py) whose Sierra-wall-clock→UTC re-interpretation had the zone HARDCODED to
   America/New_York, while the live stream (bridge/v9_streams/base_stream.py) reads V9_CHART_TZ
   (.env: America/Chicago). New York is one hour ahead of Chicago all year ⇒ every bar of the
   50-bar history was posted to /api/v9/bars/woodies_5min one hour EARLY, and the backend's
   INSERT … ON CONFLICT (ts, symbol) DO UPDATE wrote the 19:xx bars over the 18:xx rows. The live
   stream's own 50-bar window then re-corrected everything newer than its oldest bar — leaving
   exactly the 12 rows that cowork found at 23:16. Fix: v9_history.py honours V9_CHART_TZ with the
   same default as the live stream (unset ⇒ unchanged behaviour).
2. THE SECOND LINE (backend, flag OFF by default = byte-identical): WOODIES_CLOSED_BAR_GUARD_V1 —
   a stored bar that is already closed (older than WOODIES_CLOSED_BAR_SEC, 900s) is never re-written
   with DIFFERENT OHLC; the push is refused and logged. Forming bars, identical re-pushes and new
   bars are untouched.

The 24 rows below are harness_out/t524/woodies_1800_1855_{before,after}_restore.csv (01.10):
`before` = what the overwrite wrote (the 19:xx values under 18:xx ts), `after` = the true bars.
"""
import importlib
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

IL = timezone(timedelta(hours=3))

# (HH:MM IL, o, h, l, c) — 01.10, the 12 bars 18:00–18:55
OVERWRITTEN = [  # before_restore.csv: the 19:xx bars written under the 18:xx ts
    ("18:00", 7691.5, 7697.75, 7687.0, 7695.5), ("18:05", 7695.25, 7697.75, 7690.25, 7694.0),
    ("18:10", 7694.0, 7696.75, 7688.75, 7690.25), ("18:15", 7690.5, 7701.0, 7688.75, 7695.0),
    ("18:20", 7695.0, 7702.5, 7692.75, 7701.0), ("18:25", 7701.5, 7702.0, 7697.25, 7697.75),
    ("18:30", 7697.75, 7709.5, 7696.25, 7708.25), ("18:35", 7708.25, 7711.0, 7701.75, 7703.5),
    ("18:40", 7703.75, 7706.5, 7699.25, 7704.75), ("18:45", 7705.0, 7707.75, 7702.75, 7703.5),
    ("18:50", 7703.5, 7705.25, 7692.5, 7693.5), ("18:55", 7693.5, 7694.5, 7687.25, 7694.0),
]
TRUE = [  # after_restore.csv: the real 18:xx bars
    ("18:00", 7689.25, 7690.75, 7677.75, 7680.25), ("18:05", 7680.25, 7684.0, 7674.75, 7677.75),
    ("18:10", 7677.5, 7688.75, 7672.75, 7687.75), ("18:15", 7687.75, 7697.0, 7685.0, 7692.5),
    ("18:20", 7692.5, 7696.75, 7688.5, 7692.0), ("18:25", 7692.25, 7698.75, 7688.75, 7689.25),
    ("18:30", 7689.25, 7690.25, 7679.75, 7679.75), ("18:35", 7679.75, 7693.75, 7677.25, 7690.25),
    ("18:40", 7690.25, 7693.75, 7678.5, 7681.5), ("18:45", 7681.75, 7688.75, 7679.5, 7686.5),
    ("18:50", 7686.25, 7686.75, 7677.25, 7682.0), ("18:55", 7681.75, 7694.0, 7681.25, 7691.5),
]


def _epoch(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(datetime(2026, 10, 1, int(h), int(m), tzinfo=IL).timestamp())


def _incoming_bar(row, **studies):
    hhmm, o, h, l, c = row
    bar = {"ts": _epoch(hhmm), "ohlc": {"o": o, "h": h, "l": l, "c": c, "vol": 1000},
           "cci_14": 10.0 + _epoch(hhmm) % 97, "cci_6_tcci": 1.0, "swi_value": 2.0, "czi_value": 3.0,
           "ema_34": 7690.0, "lsma_value": 7690.0, "trend_state": "BLUE", "predictor_next_cci": 0.0}
    bar.update(studies)
    return bar


def _stored_from(rows):
    return {_epoch(r[0]): (r[1], r[2], r[3], r[4]) for r in rows}


# ── 1. the writer: history backfill must convert exactly like the live stream ─────────────────────
def _reload_bridge_tz_modules():
    import bridge.v9_history as hist
    import bridge.v9_streams.base_stream as base
    return importlib.reload(hist), importlib.reload(base)


def test_history_backfill_converts_like_the_live_stream(monkeypatch):
    """Same wall-clock epoch, same zone, same result — for Chicago (this Mac) and New York.
    The pre-fix code gave +4h for every chart; with the chart in Chicago the true shift is +5h."""
    wall = int(datetime(2026, 10, 1, 11, 15, tzinfo=timezone.utc).timestamp())  # 11:15 chart wall-clock
    try:
        monkeypatch.setenv("V9_CHART_TZ", "America/Chicago")
        hist, base = _reload_bridge_tz_modules()
        assert hist._chicago_to_utc(wall) == base.BaseV9Stream._chicago_to_utc(wall) == wall + 5 * 3600
        assert hist.fix_chicago_bar_ts({"history": [{"ts": wall}]})["history"][0]["ts"] == wall + 5 * 3600

        monkeypatch.setenv("V9_CHART_TZ", "America/New_York")
        hist, base = _reload_bridge_tz_modules()
        assert hist._chicago_to_utc(wall) == base.BaseV9Stream._chicago_to_utc(wall) == wall + 4 * 3600

        # knob absent ⇒ the historical default (New York) — unchanged behaviour, like the live stream
        monkeypatch.delenv("V9_CHART_TZ", raising=False)
        hist, base = _reload_bridge_tz_modules()
        assert hist._CHART_TZ_NAME == "America/New_York"
        assert hist._chicago_to_utc(wall) == base.BaseV9Stream._chicago_to_utc(wall) == wall + 4 * 3600
    finally:
        monkeypatch.undo()
        _reload_bridge_tz_modules()  # leave the modules as the process env defines them


# ── 2. the second line: WOODIES_CLOSED_BAR_GUARD_V1 on the real ingest handler ─────────────────────
def _quiet_other_gates(monkeypatch):
    for k in ("BAR_SEAM_REJECT_V1", "TS_OFFSET_INGEST_GATE_V1", "TS_WHOLE_HOUR_NORMALIZE_V1",
              "WOODIES_TS_HOUR_FIX"):
        monkeypatch.setenv(k, "0")
    monkeypatch.delenv("WOODIES_CLOSED_BAR_GUARD_V1", raising=False)
    monkeypatch.delenv("WOODIES_CLOSED_BAR_SEC", raising=False)


def _post(bars_mod, history, stored=None):
    """Drive post_woodies_5min directly (no app boot); return (response, writes, routed)."""
    writes, routed = [], []
    payload = bars_mod.Woodies5MinPayload(type="woodies_5min", export_ts=time.time(), history=history)
    with patch.object(bars_mod, "safe_execute", side_effect=lambda sql, params: writes.append(params) or 1), \
         patch.object(bars_mod, "_route_bar", side_effect=lambda topic, flat: routed.append((topic, flat))), \
         patch.object(bars_mod, "_record_push", lambda *_a, **_k: None), \
         patch("backend.v9.db.read.read_one", lambda *_a, **_k: None), \
         patch.object(bars_mod, "_closed_bar_guard_load",
                      side_effect=(lambda bars: dict(stored)) if stored is not None else AssertionError) as load:
        resp = bars_mod.post_woodies_5min(payload, _token="test")
    return resp, writes, routed, load


def test_flag_off_by_default_is_todays_behaviour(monkeypatch):
    """Flag absent: the guard is never consulted (no extra read) and the 12 mislabeled bars are
    written exactly as on 01.10 — this is the byte-identical default the night rules require."""
    _quiet_other_gates(monkeypatch)
    import backend.v9.api.v9.bars as bars_mod
    assert bars_mod._closed_bar_guard_active() is False
    resp, writes, routed, load = _post(bars_mod, [_incoming_bar(r) for r in OVERWRITTEN])
    load.assert_not_called()
    assert resp == {"ok": True, "inserted": 12, "type": "woodies_5min"}
    assert [p[0] for p in writes] == [datetime.fromtimestamp(_epoch(r[0]), tz=timezone.utc).isoformat()
                                      for r in OVERWRITTEN]
    # routed once on 'woodies_5min' (+ the 2026-08-14 failover copy on '5min' when that channel is silent)
    assert [t for t, _ in routed][:1] == ["woodies_5min"] and routed[0][1]["close"] == OVERWRITTEN[-1][4]


def test_flag_on_refuses_the_01_10_overwrite(monkeypatch, caplog):
    """Flag ON, the true 18:xx bars stored, the 19:xx values arriving under the 18:xx ts (the exact
    01.10 23:07:47 push): zero writes, zero routing, one loud writer-log line, refused_closed=12."""
    _quiet_other_gates(monkeypatch)
    monkeypatch.setenv("WOODIES_CLOSED_BAR_GUARD_V1", "1")
    import backend.v9.api.v9.bars as bars_mod
    with caplog.at_level(logging.ERROR, logger=bars_mod.logger.name):
        resp, writes, routed, load = _post(bars_mod, [_incoming_bar(r) for r in OVERWRITTEN],
                                           stored=_stored_from(TRUE))
    load.assert_called_once()
    assert writes == [] and routed == []
    assert resp == {"ok": True, "inserted": 0, "type": "woodies_5min", "refused_closed": 12}
    lines = [r.getMessage() for r in caplog.records if "CLOSED-BAR-OVERWRITE REFUSED" in r.getMessage()]
    assert len(lines) == 1 and "12/12 bars (T-526)" in lines[0] and "2026-10-01T15:00:00+00:00" in lines[0]


def test_flag_on_identical_repush_and_new_bars_still_write(monkeypatch):
    """Flag ON, the SAME closed bars re-pushed (idempotent backfill) + one bar with no stored row:
    all 13 written, nothing refused — the guard only bites on a DIFFERENT closed bar."""
    _quiet_other_gates(monkeypatch)
    monkeypatch.setenv("WOODIES_CLOSED_BAR_GUARD_V1", "1")
    import backend.v9.api.v9.bars as bars_mod
    history = [_incoming_bar(r) for r in TRUE] + [_incoming_bar(("19:00", 7695.5, 7697.75, 7687.0, 7695.0))]
    resp, writes, routed, _ = _post(bars_mod, history, stored=_stored_from(TRUE))
    assert resp == {"ok": True, "inserted": 13, "type": "woodies_5min", "refused_closed": 0}
    assert len(writes) == 13 and [t for t, _ in routed][:1] == ["woodies_5min"]


def test_forming_bar_and_tolerance_rules(monkeypatch):
    """The helper itself: a forming / just-closed bar may change (the DLL finalizes it), a closed bar
    may not; no stored row or non-numeric ts ⇒ the guard stays out; equal OHLC ⇒ no refusal."""
    monkeypatch.delenv("WOODIES_CLOSED_BAR_SEC", raising=False)
    import backend.v9.api.v9.bars as bars_mod
    why = bars_mod._closed_bar_overwrite_reason
    ts = _epoch("18:00"); stored = (7689.25, 7690.75, 7677.75, 7680.25)
    # forming (age 60s) and just-closed (age 600s < 900s): the different OHLC is accepted
    assert why(stored, 7691.5, 7697.75, 7687.0, 7695.5, ts, ts + 60) is None
    assert why(stored, 7691.5, 7697.75, 7687.0, 7695.5, ts, ts + 600) is None
    # closed (age 900s+): refused, and the reason names the differing fields
    reason = why(stored, 7691.5, 7697.75, 7687.0, 7695.5, ts, ts + 900)
    assert reason and reason.startswith("closed bar") and "o 7689.25→7691.5" in reason
    # closed but identical ⇒ passes; float noise inside the tolerance ⇒ passes
    assert why(stored, 7689.25, 7690.75, 7677.75, 7680.25, ts, ts + 86400) is None
    assert why(stored, 7689.25 + 1e-9, 7690.75, 7677.75, 7680.25, ts, ts + 86400) is None
    # no stored row / no usable ts ⇒ never refused
    assert why(None, 7691.5, 7697.75, 7687.0, 7695.5, ts, ts + 86400) is None
    assert why(stored, 7691.5, 7697.75, 7687.0, 7695.5, None, ts + 86400) is None
    # the knob: WOODIES_CLOSED_BAR_SEC widens the forming window
    monkeypatch.setenv("WOODIES_CLOSED_BAR_SEC", "3600")
    assert why(stored, 7691.5, 7697.75, 7687.0, 7695.5, ts, ts + 900) is None
    assert why(stored, 7691.5, 7697.75, 7687.0, 7695.5, ts, ts + 3600) is not None
    # ts parsing: numeric only
    assert bars_mod._bar_epoch(ts) == ts and bars_mod._bar_epoch(float(ts) + 0.4) == ts
    assert bars_mod._bar_epoch("1759338000") is None and bars_mod._bar_epoch(None) is None
    assert bars_mod._bar_epoch(True) is None and bars_mod._bar_epoch(-5) is None
