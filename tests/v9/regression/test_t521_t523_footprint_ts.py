# -*- coding: utf-8 -*-
"""T-521 / T-523 (Michael 2026-10-07 15:53 IL): System 3 footprint timestamps must be BAR time.

Proven from the DB before patching (docs/reports/S3_FIX_2026-10-07.md):
  * v9_bars_footprint: 5,312,719 rows, 5,312,618 of them with ts within 5 s of created_at —
    the bridge's FootprintBar.to_dict() emitted no `ts`, post_footprint fell back to now().
  * v9_footprint_journal: max(ts) = 179088-12-30 (712 rows) — BarEvent.ts is the raw epoch
    string "1790881230", which Postgres parsed as a DATE literal.
  * scid_ts_to_unix() used a NAIVE 1899 epoch → bar_start_ts was 3 h early on an IL machine.

Guarantees pinned here (anti-tautology: each compares against an INDEPENDENT value, never
against the function under test):
  1. scid_ts_to_unix is a true UTC epoch and does not depend on the process TZ.
  2. FootprintBar.to_dict() carries `ts` == the bar START (first tick), not export time.
  3. post_footprint never substitutes now() for a missing/garbage ts — the bar is skipped.
  4. FootprintSystem._write_journal/_write_setup write an aware-UTC ISO ts parsed from the
     raw epoch, and skip (not now()) when the event ts is unparseable.
"""
import importlib.util
import os
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

import pytest

os.environ.setdefault("BRIDGE_TOKEN", "test-token")

_REPO = os.path.join(os.path.dirname(__file__), "..", "..", "..")


def _load_vap():
    spec = importlib.util.spec_from_file_location(
        "vap_recompute_t521", os.path.join(_REPO, "bridge", "v9_streams", "vap_recompute.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── 1. SCID DateTime is UTC ──────────────────────────────────────────────────

# Golden: last record of the live MESZ26 SCID at probe time (2026-10-07 13:21:06Z, file mtime
# 13:21:01.47Z). The UTC-explicit conversion gave age=5 s; the old naive one gave age=10805 s.
_GOLDEN_SCID_US = 4000540861061000
_GOLDEN_UTC = datetime(2026, 10, 7, 13, 21, 1, 61000, tzinfo=timezone.utc)


def test_scid_ts_to_unix_matches_independent_utc_golden():
    vap = _load_vap()
    got = vap.scid_ts_to_unix(_GOLDEN_SCID_US)
    assert abs(got - _GOLDEN_UTC.timestamp()) < 0.001, (
        f"scid_ts_to_unix={got} ({datetime.fromtimestamp(got, tz=timezone.utc).isoformat()}) "
        f"≠ golden {_GOLDEN_UTC.isoformat()}")


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="POSIX tzset required")
def test_scid_ts_to_unix_is_process_tz_independent():
    vap = _load_vap()
    results = {}
    old_tz = os.environ.get("TZ")
    try:
        for tz in ("Asia/Jerusalem", "UTC", "America/Chicago"):
            os.environ["TZ"] = tz
            time.tzset()
            results[tz] = vap.scid_ts_to_unix(_GOLDEN_SCID_US)
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        time.tzset()
    assert len(set(round(v, 3) for v in results.values())) == 1, results
    assert abs(results["UTC"] - _GOLDEN_UTC.timestamp()) < 0.001


# ── 2. to_dict carries the bar START ts ──────────────────────────────────────

def test_footprint_bar_to_dict_emits_bar_start_ts():
    vap = _load_vap()
    start = 1791379261.5
    bar = vap.FootprintBar(start, 7840.5)
    bar.add_tick(7840.75, 1, 2)
    d = bar.to_dict(0)
    assert "ts" in d
    assert d["ts"] == start


def test_get_footprint_bars_carry_first_tick_ts_not_export_time():
    vap = _load_vap()
    r = vap.VAPRecomputer.__new__(vap.VAPRecomputer)
    r.bars = __import__("collections").deque(maxlen=vap.MAX_BARS)
    r._current_bar = None
    r._current_bar_end_ts = 0
    r._last_valid_ts = 0
    r._ticks_processed = 0
    r._ticks_dropped = 0
    t0 = 1790881230.0                      # 2026-10-01 19:00:30Z — fixed, days from now()
    r.process_tick(t0, 7840.0, 1, 0)
    r.process_tick(t0 + 10, 7840.25, 0, 1)
    r.process_tick(t0 + vap.BAR_DURATION_SEC + 1, 7841.0, 0, 1)   # opens bar 2
    fp = r.get_footprint()
    assert [b["ts"] for b in fp["bars"]] == [t0, t0 + vap.BAR_DURATION_SEC + 1]
    for b in fp["bars"]:
        assert abs(b["ts"] - fp["export_ts"]) > 3600, "bar ts must not be the export/write time"


# ── 3. post_footprint: missing/garbage ts → skipped, never now() ─────────────

class _FakeDB:
    def __init__(self):
        self.rows = []
        self.committed = 0

    def add(self, row):
        self.rows.append(row)

    def commit(self):
        self.committed += 1


def _payload(bars):
    from backend.v9.api.v9.bars import FootprintPayload
    return FootprintPayload(type="footprint", export_ts=time.time(), bars=bars)


def _bar(**kw):
    b = {"idx": 0, "o": 7840.0, "h": 7841.0, "l": 7839.0, "c": 7840.5, "vol": 10, "delta": 2,
         "poc_price": 7840.0, "poc_vol": 5, "stacked_buy": 0, "stacked_sell": 0, "levels": []}
    b.update(kw)
    return b


def test_post_footprint_missing_ts_is_skipped_not_now():
    from backend.v9.api.v9 import bars as bars_mod
    db = _FakeDB()
    res = bars_mod.post_footprint(_payload([_bar()]), db=db, _token="x")   # no `ts` key
    assert res["inserted"] == 0
    assert res["skipped_bad_ts"] == 1
    assert db.rows == [], "a bar without ts must not be written with a now() timestamp"


@pytest.mark.parametrize("garbage", [
    None, "", "abc", 0, -5, True, float("nan"), float("inf"),
    1790881230,       # 2026-10-01 — > MAX_STALE_AGE (24 h) old → outside plausibility
    4102444800,       # 2100-01-01 — far future
])
def test_post_footprint_garbage_ts_is_skipped(garbage):
    from backend.v9.api.v9 import bars as bars_mod
    db = _FakeDB()
    res = bars_mod.post_footprint(_payload([_bar(ts=garbage)]), db=db, _token="x")
    assert res["inserted"] == 0 and res["skipped_bad_ts"] == 1, (garbage, res)
    assert db.rows == []


def test_post_footprint_valid_ts_is_bar_time_not_write_time():
    from backend.v9.api.v9 import bars as bars_mod
    db = _FakeDB()
    bar_ts = time.time() - 600          # a bar that started 10 minutes ago
    res = bars_mod.post_footprint(_payload([_bar(ts=bar_ts), _bar(ts=bar_ts + 180)]), db=db, _token="x")
    assert res["inserted"] == 2 and res["skipped_bad_ts"] == 0
    assert [r.ts for r in db.rows] == [
        datetime.fromtimestamp(bar_ts, tz=timezone.utc),
        datetime.fromtimestamp(bar_ts + 180, tz=timezone.utc),
    ]
    for r in db.rows:
        assert r.ts.tzinfo is not None
        assert (datetime.now(timezone.utc) - r.ts) > timedelta(minutes=5), "ts must not be the write time"


def test_footprint_bar_ts_helper_boundaries():
    from backend.v9.api.v9.bars import _footprint_bar_ts, MAX_STALE_AGE
    now = datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc)
    ok = now - timedelta(minutes=3)
    assert _footprint_bar_ts(ok.timestamp(), now=now) == ok
    assert _footprint_bar_ts(str(ok.timestamp()), now=now) == ok          # numeric string OK
    assert _footprint_bar_ts((now - MAX_STALE_AGE - timedelta(seconds=1)).timestamp(), now=now) is None
    assert _footprint_bar_ts((now + timedelta(minutes=6)).timestamp(), now=now) is None
    assert _footprint_bar_ts((now + timedelta(minutes=4)).timestamp(), now=now) is not None


# ── 4. Journal / setup ts: aware UTC from the raw epoch, skip on garbage ─────

def _fp_system():
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    return FootprintSystem()


_CLUSTER = SimpleNamespace(yellow_poc_price=7840.0, yellow_poc_pct=40.0)
_EMPTY = SimpleNamespace(zones=[])
_CTX = SimpleNamespace(accumulation=False, jumps_count=0, jumps_direction="NONE", otf_state=0)


def test_journal_ts_from_raw_epoch_string_is_aware_utc_iso():
    fp = _fp_system()
    # exactly the live shape that produced 179088-12-30: BarEvent.ts = str(epoch)
    ev = SimpleNamespace(ts="1790881230", bar_id="tick_reversal_12_1790881230", session="CASH_HOURS")
    with mock.patch("backend.v9.db.safe_writer.safe_execute") as se:
        fp._write_journal(ev, {}, _CLUSTER, _EMPTY, _CTX, None, {}, 0, "NO_SETUP")
    assert se.call_count == 1
    sql, params = se.call_args[0]
    assert sql.startswith("INSERT OR IGNORE INTO v9_footprint_journal")
    assert params[0] == "2026-10-01T19:00:30+00:00"        # independent: epoch 1790881230
    assert params[1] == "tick_reversal_12_1790881230"
    assert not params[0].startswith("1790"), "raw epoch digits must never reach the ts column"


def test_journal_ts_accepts_iso_and_numeric_event_ts():
    fp = _fp_system()
    cases = {
        1790881230: "2026-10-01T19:00:30+00:00",
        1790881230.0: "2026-10-01T19:00:30+00:00",
        "2026-10-01T19:00:30Z": "2026-10-01T19:00:30+00:00",
        "2026-10-01T22:00:30+03:00": "2026-10-01T19:00:30+00:00",   # IL → UTC, consistently UTC
    }
    for raw, want in cases.items():
        with mock.patch("backend.v9.db.safe_writer.safe_execute") as se:
            fp._write_journal(SimpleNamespace(ts=raw, bar_id=f"b_{raw}", session="X"),
                              {}, _CLUSTER, _EMPTY, _CTX, None, {}, 0, "NO_SETUP")
        assert se.call_args[0][1][0] == want, raw


@pytest.mark.parametrize("garbage", ["", None, "garbage", "not-a-date"])
def test_journal_and_setup_skip_on_garbage_ts_never_now(garbage):
    fp = _fp_system()
    ev = SimpleNamespace(ts=garbage, bar_id="b", session="X") if garbage is not None \
        else SimpleNamespace(bar_id="b", session="X")           # no ts attribute at all
    with mock.patch("backend.v9.db.safe_writer.safe_execute") as se:
        fp._write_journal(ev, {}, _CLUSTER, _EMPTY, _CTX, None, {}, 0, "NO_SETUP")
        fp._write_setup(ev, {"close": 1.0, "open": 0.5, "low": 0.4}, "TACTICAL", None, 4)
    assert se.call_count == 0, f"garbage ts {garbage!r} must skip the write, not stamp now()"


def test_setup_ts_from_raw_epoch_is_aware_utc_iso():
    fp = _fp_system()
    ev = SimpleNamespace(ts="1790881230", bar_id="b", session="CASH_HOURS")
    with mock.patch("backend.v9.db.safe_writer.safe_execute") as se:
        fp._write_setup(ev, {"close": 7841.0, "open": 7840.0, "low": 7839.0}, "TACTICAL", "ACCUMULATION_BREAKOUT", 4)
    assert se.call_count == 1
    assert se.call_args[0][1][0] == "2026-10-01T19:00:30+00:00"
