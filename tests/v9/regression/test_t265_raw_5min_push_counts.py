# -*- coding: utf-8 -*-
"""T-265 / T-532 regression (fix-agent, night 08→09.10 — BRIEF §3.3): S1/S2 must be fed from the
canonical stream whenever the raw RTH export delivers nothing inside RTH.

The class: `5min.json` (Sierra's RTH chart export → POST /api/v9/bars/5min → BarRouter topic '5min',
the ONLY feed of S2 and the day-type machine) stays on Friday's bars on a Monday while the canonical
`v9_bars_5min_woodies` stream is live. The bridge re-pushes the frozen file every ~4s (fresh mtime),
the TS-OFFSET gate passes the NON-advancing batch "but logged", `_record_push("5min")` fired on every
push, so stream-health said "5min fresh", the 2026-08-14 woodies failover (which only asks "has the
raw channel pushed lately?") stayed quiet, and `_route_bar` blocked the stale bar: nobody fed S1/S2
behind a screen that looked alive. Same tracker: `_latest_known_price` took Friday's close, so the
50-pt price band then measured every fresh bar against it — a gap wider than the band would reject
the whole morning with nothing able to move the tracker (only an ACCEPTED bar does).

Pinned here, behaviourally (not by reading source):
  1. `_raw_5min_push_counts` — every branch, at fixed ET instants.
  2. POST /5min with the stuck-on-Friday payload inside RTH: push NOT counted, tracker untouched,
     nothing routed. A fresh push: counted, tracker moved, routed (byte-identical healthy path).
  3. The woodies failover then feeds '5min' because the raw channel's last COUNTED push is old.
  4. The price-band guards ignore a stale tracker (gap Monday after a weekend) and still bite while
     the tracker is fresh (a ghost price inside a live session).
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.v9.api.v9.bars as bars_mod
from backend.v9.api.v9.auth import verify_bridge_token

_ET = ZoneInfo("America/New_York")


def _et(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=_ET).astimezone(timezone.utc)


# 2026-10-05 is a Monday (T-532's day); 2026-10-02 the Friday before; 2026-09-07 Labor Day (holiday).
MON_1000 = _et(2026, 10, 5, 10, 0)
MON_0935 = _et(2026, 10, 5, 9, 35)
MON_0946 = _et(2026, 10, 5, 9, 46)
MON_1700 = _et(2026, 10, 5, 17, 0)
SAT_1000 = _et(2026, 10, 3, 10, 0)
SUN_2000 = _et(2026, 10, 4, 20, 0)
HOL_1000 = _et(2026, 9, 7, 10, 0)
FRI_1555 = _et(2026, 10, 2, 15, 55)   # the newest bar of the stuck export


def _frozen(monkeypatch, when):
    """Freeze bars_mod's datetime.now() at `when` (utc-aware); fromtimestamp etc. keep working."""
    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return when.astimezone(tz) if tz else when.replace(tzinfo=None)
    monkeypatch.setattr(bars_mod, "datetime", _DT)


class TestPushCounts:
    """Branch table of the pure helper (BAR5_RAW_STALE_SEC = 900 by default)."""

    def test_fresh_bar_always_counts(self, monkeypatch):
        for now in (MON_1000, SAT_1000, SUN_2000, HOL_1000, MON_0935):
            counts, why = bars_mod._raw_5min_push_counts(now, now - timedelta(seconds=300))
            assert counts and why == "fresh", (now, why)

    def test_stuck_on_friday_inside_rth_does_not_count(self):
        counts, why = bars_mod._raw_5min_push_counts(MON_1000, FRI_1555)
        assert not counts and why.startswith("inside RTH"), why

    def test_no_valid_bar_inside_rth_does_not_count(self):
        counts, why = bars_mod._raw_5min_push_counts(MON_1000, None)
        assert not counts and "no valid bar" in why

    def test_grace_after_the_open_counts(self):
        """09:30–09:45: the first raw bar of the day closes at 09:35 — yesterday's bar is not a fault."""
        counts, why = bars_mod._raw_5min_push_counts(MON_0935, FRI_1555)
        assert counts and why == "grace after the open"
        counts, _ = bars_mod._raw_5min_push_counts(MON_0946, FRI_1555)
        assert not counts, "16 min after the open a Friday bar is a stuck channel"

    def test_outside_rth_counts_byte_identical(self):
        """Weekend, Sunday-night Globex, a 2026 holiday, after the close: the RTH chart legitimately
        has no fresh bar — the push is counted exactly as before the fix (no new overnight failover)."""
        for now in (SAT_1000, SUN_2000, HOL_1000, MON_1700):
            counts, why = bars_mod._raw_5min_push_counts(now, now - timedelta(hours=65))
            assert counts and why == "outside RTH", (now, why)

    def test_window_is_env_tunable(self, monkeypatch):
        monkeypatch.setattr(bars_mod, "BAR5_RAW_STALE_SEC", 60.0)
        counts, _ = bars_mod._raw_5min_push_counts(MON_1000, MON_1000 - timedelta(seconds=300))
        assert not counts
        monkeypatch.setattr(bars_mod, "BAR5_RAW_STALE_SEC", 900.0)
        counts, _ = bars_mod._raw_5min_push_counts(MON_1000, MON_1000 - timedelta(seconds=300))
        assert counts


# ── end-to-end through the router, with the module's I/O seams replaced ─────────────────────────

class _Health:
    def __init__(self):
        self.pushes, self.last = [], {}

    def record_push(self, name):
        import time
        self.pushes.append(name)
        self.last[name] = time.time()

    def record_error(self, name, err):
        pass

    def record_dispatch(self, *a):
        pass

    def get_all_streams(self):
        return {"streams": [{"name": n, "last_push_ts": t} for n, t in self.last.items()]}


class _Router:
    def __init__(self):
        self.published = []

    def publish_threadsafe(self, bar_type, data):
        self.published.append((bar_type, data))


def _client():
    app = FastAPI()
    app.include_router(bars_mod.router)
    app.dependency_overrides[verify_bridge_token] = lambda: "test"
    return TestClient(app)


def _isolate(monkeypatch, now):
    """Freeze the clock, replace DB/health/router seams, reset the module's per-process state."""
    _frozen(monkeypatch, now)
    health, router = _Health(), _Router()
    monkeypatch.setattr(bars_mod, "_stream_health", health)
    monkeypatch.setattr(bars_mod, "_bar_router", router)
    monkeypatch.setattr(bars_mod, "safe_executemany", lambda sql, rows: len(rows))
    monkeypatch.setattr(bars_mod, "safe_execute", lambda sql, params=None: 1)
    monkeypatch.setattr(bars_mod, "_contradicts_woodies", lambda *a, **k: None)
    monkeypatch.setattr(bars_mod, "_sticky_zlr", lambda ts, flag, d: (flag, d))
    monkeypatch.setattr(bars_mod, "_closed_bar_guard_active", lambda: False)
    monkeypatch.setattr(bars_mod, "_ts_gate_last_newest", {})
    monkeypatch.setattr(bars_mod, "_latest_known_price", None)
    monkeypatch.setattr(bars_mod, "_latest_bar_ts", None)
    monkeypatch.setattr(bars_mod, "_uncounted_push_warn_ts", 0.0)
    monkeypatch.setattr(bars_mod, "STALE_PRICE_BAND", 50.0)       # .env may widen it; pin the band
    monkeypatch.setattr(bars_mod, "MAX_STALE_AGE", timedelta(hours=24))
    monkeypatch.setattr(bars_mod, "BAR5_RAW_STALE_SEC", 900.0)
    monkeypatch.setenv("BAR_SEAM_REJECT_V1", "0")
    monkeypatch.setenv("WOODIES_TS_HOUR_FIX", "0")
    monkeypatch.delenv("BAR5_FAILOVER_SECONDS", raising=False)
    return health, router


def _raw_payload(newest, n=3, close=7700.0):
    """n RTH bars, 5 min apart, the newest at `newest` (utc-aware)."""
    out = []
    for i in range(n):
        ts = newest - timedelta(minutes=5 * (n - 1 - i))
        out.append({"ts": ts.timestamp(), "symbol": "MES", "o": close - 1, "h": close + 2,
                    "l": close - 2, "c": close, "vol": 3000})
    return out


class TestRawPushEndToEnd:
    def test_stuck_on_friday_push_inside_rth_is_not_counted_and_moves_nothing(self, monkeypatch):
        health, router = _isolate(monkeypatch, MON_1000)
        resp = _client().post("/api/v9/bars/5min", json=_raw_payload(FRI_1555))
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True                      # the write itself is still accepted
        assert health.pushes == []                            # ← the fix: no '5min' push recorded
        assert router.published == []                         # stale bar blocked, as before
        assert bars_mod._latest_known_price is None           # Friday's close is not "latest"
        assert bars_mod._latest_bar_ts is None

    def test_fresh_push_inside_rth_is_byte_identical(self, monkeypatch):
        health, router = _isolate(monkeypatch, MON_1000)
        newest = MON_1000 - timedelta(minutes=10)             # the 09:50 bar, closed at 09:55
        resp = _client().post("/api/v9/bars/5min", json=_raw_payload(newest, close=7790.0))
        assert resp.status_code == 200, resp.text
        assert health.pushes == ["5min"]
        assert [t for t, _ in router.published] == ["5min"]
        assert bars_mod._latest_known_price == 7790.0
        assert bars_mod._latest_bar_ts == newest

    def test_stuck_push_outside_rth_is_counted_as_before(self, monkeypatch):
        """Sunday night: the frozen file is pushed, counted (health 'fresh'), nothing routed — the
        pre-fix accounting, so the failover's overnight behaviour does not change."""
        health, router = _isolate(monkeypatch, SUN_2000)
        resp = _client().post("/api/v9/bars/5min", json=_raw_payload(FRI_1555))
        assert resp.status_code == 200, resp.text
        assert health.pushes == ["5min"]
        assert router.published == []
        assert bars_mod._latest_known_price is None


def _woodies_payload(ts_utc, close=7790.0):
    bar = {"ts": ts_utc.timestamp(),
           "ohlc": {"o": close - 1, "h": close + 2, "l": close - 2, "c": close, "vol": 1200},
           "cci_14": 40.0, "cci_6_tcci": 10.0, "swi_value": 5.0, "czi_value": 50.0,
           "trend_state": "BLUE", "ema_34": close - 3, "lsma_value": close - 2,
           "predictor_next_cci": 41.0}
    return {"type": "woodies_5min", "history": [bar], "current_bar": dict(bar)}


class TestFailoverTakesOver:
    def test_woodies_feeds_5min_after_an_uncounted_raw_push(self, monkeypatch):
        """Monday 10:00 ET, raw export stuck on Friday (pushed, uncounted), canonical stream live:
        the woodies push republishes its bar on '5min' — S1/S2 are fed from the canonical path."""
        import time
        health, router = _isolate(monkeypatch, MON_1000)
        _client().post("/api/v9/bars/5min", json=_raw_payload(FRI_1555))
        assert health.pushes == []                              # raw channel: pushed, not counted
        health.last["5min"] = time.time() - 200                 # last COUNTED push: before the open
        resp = _client().post("/api/v9/bars/woodies_5min",
                              json=_woodies_payload(MON_1000 - timedelta(minutes=5)))
        assert resp.status_code == 200, resp.text
        topics = [t for t, _ in router.published]
        assert "woodies_5min" in topics and "5min" in topics, topics
        assert "5min" in health.pushes                          # the failover counts its own feed

    def test_woodies_stays_quiet_while_raw_channel_delivers(self, monkeypatch):
        """Healthy RTH: the raw push 60s ago was counted → no failover (F2 single-source guarantee)."""
        health, router = _isolate(monkeypatch, MON_1000)
        _client().post("/api/v9/bars/5min", json=_raw_payload(MON_1000 - timedelta(minutes=10)))
        assert health.pushes == ["5min"]
        resp = _client().post("/api/v9/bars/woodies_5min",
                              json=_woodies_payload(MON_1000 - timedelta(minutes=5)))
        assert resp.status_code == 200, resp.text
        assert [t for t, _ in router.published] == ["5min", "woodies_5min"]


class TestPriceBandConsultsOnlyAFreshTracker:
    """The gap-Monday deadlock: tracker = Friday's close (65 h old) → a fresh bar 90 pt away used to be
    rejected as off_market, and since only an accepted bar refreshes the tracker, every bar of the
    morning followed. The band is for ghost prices INSIDE a live session — it must still bite there."""

    def test_stale_tracker_lets_the_gap_bar_through(self, monkeypatch):
        _isolate(monkeypatch, MON_1000)
        monkeypatch.setattr(bars_mod, "_latest_known_price", 7700.0)
        monkeypatch.setattr(bars_mod, "_latest_bar_ts", FRI_1555)
        fresh = MON_1000 - timedelta(minutes=10)
        assert bars_mod._is_stale_bar(fresh, 7790.0) is None
        bars_mod._route_bar("5min", {"ts": fresh.timestamp(), "close": 7790.0, "c": 7790.0})
        assert [t for t, _ in bars_mod._bar_router.published] == ["5min"]

    def test_fresh_tracker_still_rejects_a_ghost_price(self, monkeypatch):
        _isolate(monkeypatch, MON_1000)
        monkeypatch.setattr(bars_mod, "_latest_known_price", 7700.0)
        monkeypatch.setattr(bars_mod, "_latest_bar_ts", MON_1000 - timedelta(minutes=5))
        fresh = MON_1000 - timedelta(minutes=2)
        why = bars_mod._is_stale_bar(fresh, 7790.0)
        assert why and why.startswith("off_market"), why
        bars_mod._route_bar("5min", {"ts": fresh.timestamp(), "close": 7790.0, "c": 7790.0})
        assert bars_mod._bar_router.published == []

    def test_gap_monday_end_to_end_accepts_the_first_fresh_bar(self, monkeypatch):
        """Weekend restart → backfill push (Friday bars) → tracker stays None → the 09:50 bar, 90 pt
        above Friday's close, is written, counted and routed; the tracker then moves to it."""
        health, router = _isolate(monkeypatch, MON_1000)
        c = _client()
        c.post("/api/v9/bars/5min", json=_raw_payload(FRI_1555, close=7700.0))
        assert bars_mod._latest_known_price is None
        c.post("/api/v9/bars/5min", json=_raw_payload(MON_1000 - timedelta(minutes=10), close=7790.0))
        assert bars_mod._latest_known_price == 7790.0
        assert health.pushes == ["5min"] and [t for t, _ in router.published] == ["5min"]
