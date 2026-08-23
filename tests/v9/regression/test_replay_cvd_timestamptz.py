"""Regression: research replays must consume migrated timestamptz CVD rows."""
from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "good_pattern_fix_replay_test", ROOT / "scripts" / "good_pattern_fix.py")
GPF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GPF)


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.params = None

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return self.rows


def test_load_cvd_uses_timestamptz_range_not_left_text():
    ts = dt.datetime(2026, 8, 21, 13, 30, tzinfo=dt.timezone.utc)
    cursor = _Cursor([(ts, 123.0)])

    rows = GPF.load_cvd(cursor)

    assert "left(" not in cursor.sql.lower()
    assert "at time zone 'America/New_York'" in cursor.sql
    assert list(rows) == ["2026-08-21"]
    key, value = rows["2026-08-21"][0]
    assert key == ts
    assert key.tzinfo is not None
    assert value == 123.0


def test_replay_bar_and_cvd_keys_share_aware_utc_type():
    bar = GPF._mk_bar({
        "t": dt.datetime(2026, 8, 21, 9, 30),
        "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 10,
    })

    assert bar["ts"] == dt.datetime(
        2026, 8, 21, 13, 30, tzinfo=dt.timezone.utc)


def test_replay_shim_rejects_partial_cvd_window():
    shim = GPF.S2Shim()
    start = dt.datetime(2026, 8, 21, 13, 30, tzinfo=dt.timezone.utc)
    bars = []
    for i in range(4):
        bars.append({"ts": start + dt.timedelta(minutes=5 * i)})

    shim._cvd_sorted = [
        (start, 100.0),
        (start + dt.timedelta(minutes=5), 120.0),
        (start + dt.timedelta(minutes=10), 130.0),
    ]
    assert shim._compute_setup_cvd(bars, window=4) is None

    shim._cvd_sorted.append(
        (start + dt.timedelta(minutes=15), 160.0))
    result = shim._compute_setup_cvd(bars, window=4)
    assert result["net_delta"] == 60.0
    assert result["perbar_deltas"] == [20.0, 10.0, 30.0]
