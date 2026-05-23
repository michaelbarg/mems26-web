"""P31 Phase 2 — HistoryLoader parser + gap-fill regression tests.

Pins the Phase 2 fixes (Michael 2026-05-22, "see all data in dashboard when
turning on"):

  * Per-stream parsers map Sierra payload arrays into the expected DB row
    shape — VP uses ``profiles[]``, CVD uses ``points[]``, 5min uses
    ``bars[]``. A future schema rename surfaces here loudly.
  * ``_ts_iso_from_unix`` emits the **same** naive UTC format that
    SQLAlchemy persists via the live POST handler. Format drift was a
    real bug on 2026-05-22 — produced 601 duplicate v9_bars_5min rows
    keyed by ISO-with-T format that bypassed ``UNIQUE(ts, symbol)``.
  * ``run_gap_fill`` is idempotent — re-running against the same exports
    inserts no new rows (everything dedupes via INSERT OR IGNORE on the
    target table's UNIQUE constraint).
  * Stale exports (mtime > 600 s) are skipped — defensive against running
    a stale Sierra paused / weekend / market-closed export into DB.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

import pytest

# auth.py requires BRIDGE_TOKEN at import time — set placeholder for tests.
os.environ.setdefault("BRIDGE_TOKEN", "test-token")

from backend.v9.services.history_loader import (
    HistoryLoader,
    _ts_iso_from_unix,
    parse_5min_bars,
    parse_cvd_points,
    parse_vp_profiles,
    parse_footprint_bars,
    parse_woodies_bars,
)


# ----------------------------------------------------------------------
# Format helpers
# ----------------------------------------------------------------------


class TestTsFormat:
    def test_ts_iso_format_naive_with_microseconds(self):
        """``_ts_iso_from_unix`` must produce ``YYYY-MM-DD HH:MM:SS.ffffff``
        (naive UTC) to match what the live POST handler persists, so
        ``INSERT OR IGNORE`` on ``UNIQUE(ts, symbol)`` actually dedupes."""
        ts = _ts_iso_from_unix(1779417000, fix_chicago=False)
        assert ts is not None
        # Must be naive (no T separator, no TZ suffix).
        assert "T" not in ts
        assert "+" not in ts
        # ``.ffffff`` microsecond suffix matches SQLAlchemy's default
        assert ts.endswith(".000000")

    def test_chicago_to_utc_shifts_5h_in_summer(self):
        """Sierra DLL bug § 9: SCDateTime serializes as Chicago wall-clock
        encoded as unix. Bridge corrects with +5 h shift (CDT) — the
        loader must mirror that or it'd write rows 5 h behind live data."""
        # 1779417000 = 2026-05-22 02:30 UTC raw → with CDT shift becomes
        # 2026-05-22 07:30 UTC.
        ts = _ts_iso_from_unix(1779417000, fix_chicago=True)
        assert ts is not None
        assert ts.startswith("2026-05-22 07:30:00")

    def test_chicago_fix_disabled_via_env(self, monkeypatch):
        """When ``V9_DISABLE_CHICAGO_TS_FIX=1`` (DLL canonical fix shipped),
        the loader must stop shifting so it agrees with the bridge."""
        from backend.v9.services import history_loader

        monkeypatch.setattr(history_loader, "_DISABLE_CHICAGO_TS_FIX", True)
        ts = history_loader._ts_iso_from_unix(1779417000, fix_chicago=True)
        # Same as fix_chicago=False — no shift applied
        assert ts is not None
        assert ts.startswith("2026-05-22 02:30:00")

    def test_ts_iso_handles_none(self):
        assert _ts_iso_from_unix(None) is None

    def test_ts_iso_handles_invalid(self):
        assert _ts_iso_from_unix("not_a_number") is None


# ----------------------------------------------------------------------
# Per-stream parsers
# ----------------------------------------------------------------------


class TestParsers:
    def test_5min_bar_parser(self):
        rows = parse_5min_bars(
            {
                "bars": [
                    {"ts": 1779417000, "o": 7480.0, "h": 7485.0, "l": 7478.0, "c": 7483.0, "vol": 1000, "poc_vol": 50, "vah": 7484.0, "val": 7479.0, "cumulative_delta": -50.0},
                ]
            }
        )
        assert len(rows) == 1
        # Chicago→UTC shift applied: 02:30 raw → 07:30 corrected
        assert rows[0]["ts"].startswith("2026-05-22 07:30")
        assert rows[0]["symbol"] == "MES"
        assert rows[0]["open"] == 7480.0
        assert rows[0]["vah"] == 7484.0

    def test_cvd_point_parser(self):
        rows = parse_cvd_points(
            {
                "points": [
                    {"i": 6107, "t": 1779408299, "d": 31.0, "cum": -85.0, "p": 7494.25}
                ]
            }
        )
        assert len(rows) == 1
        assert rows[0]["bar_id"] == "cvd_6107"
        assert rows[0]["cumulative"] == -85.0
        assert rows[0]["direction"] == "UP"  # d > 0

    def test_cvd_skips_points_without_index(self):
        rows = parse_cvd_points({"points": [{"t": 100, "d": 1, "cum": 1, "p": 7400}]})
        assert rows == []  # no `i` → dropped

    def test_vp_profile_parser(self):
        rows = parse_vp_profiles(
            {
                "profiles": [
                    {
                        "bar_idx": 6107,
                        "poc": 7493.0,
                        "poc_vol": 68.43,
                        "vah": 7494.0,
                        "val": 7493.0,
                        "total_vol": 479.0,
                        "levels": [{"p": 7493.0, "v": 68.43}],
                    }
                ]
            },
            export_ts=1779432786,
        )
        assert len(rows) == 1
        assert rows[0]["bar_id"] == "vp_6107"
        assert rows[0]["poc"] == 7493.0
        # Full profile stored as JSON for backtests (Michael's `save_full_profile`)
        parsed = json.loads(rows[0]["profile"])
        assert parsed[0]["p"] == 7493.0

    def test_footprint_drops_bars_without_ohlc(self):
        rows = parse_footprint_bars(
            {"bars": [{"idx": 1, "vol": 100}]}, export_ts=1779432786,
        )
        assert rows == []

    def test_woodies_uses_history_array_not_current_bar(self):
        rows = parse_woodies_bars(
            {
                "history": [
                    {
                        "ts": 1779417000,
                        "ohlc": {"o": 7480.0, "h": 7485.0, "l": 7478.0, "c": 7483.0},
                        "cci_14": -42.0,
                        "zlr_detected": True,
                        "zlr_direction": "LONG",
                        "trend_state": "GREEN",
                    }
                ],
                "current_bar": {"ts": 1779417300, "ohlc": {"o": 1, "h": 1, "l": 1, "c": 1}},
            },
            period_minutes=5,
        )
        assert len(rows) == 1, "Only persist completed bars; current_bar is mutable"
        assert rows[0]["zlr_detected"] == 1  # boolean → 0/1
        assert rows[0]["zlr_direction"] == "LONG"
        assert rows[0]["trend_state"] == "GREEN"


# ----------------------------------------------------------------------
# End-to-end gap-fill against temp SQLite
# ----------------------------------------------------------------------


@pytest.fixture
def tmp_loader(tmp_path):
    """HistoryLoader pointed at a tmp Sierra export dir + tmp SQLite DB."""
    export_dir = tmp_path / "v9_export"
    export_dir.mkdir()
    db_path = tmp_path / "test.db"

    # Seed v9_bars_5min schema with UNIQUE so INSERT OR IGNORE dedupe works.
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE v9_bars_5min (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts DATETIME NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                open FLOAT NOT NULL,
                high FLOAT NOT NULL,
                low FLOAT NOT NULL,
                close FLOAT NOT NULL,
                volume INTEGER NOT NULL,
                poc_vol INTEGER, vah FLOAT, val FLOAT, cumulative_delta FLOAT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE UNIQUE INDEX ux_v9_bars_5min_ts_symbol ON v9_bars_5min (ts, symbol);

            CREATE TABLE v9_bars_cumulative_delta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                bar_id TEXT UNIQUE,
                delta REAL, cumulative REAL, direction TEXT, session TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE v9_bars_volume_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                bar_id TEXT UNIQUE,
                profile TEXT, poc REAL, vah REAL, val REAL,
                total_volume INTEGER, session TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    # Seed exports with realistic Sierra shape
    (export_dir / "5min.json").write_text(
        json.dumps(
            {
                "type": "5min",
                "export_ts": int(time.time()),
                "bars": [
                    {"ts": 1779417000, "o": 7480.0, "h": 7485.0, "l": 7478.0, "c": 7483.0, "vol": 1000, "poc_vol": 50, "vah": 7484.0, "val": 7479.0, "cumulative_delta": -50.0},
                    {"ts": 1779417300, "o": 7483.0, "h": 7486.0, "l": 7482.0, "c": 7485.0, "vol": 1500, "poc_vol": 75, "vah": 7486.0, "val": 7483.0, "cumulative_delta": 100.0},
                ],
            }
        )
    )
    (export_dir / "cumulative_delta.json").write_text(
        json.dumps(
            {
                "type": "cumulative_delta",
                "export_ts": int(time.time()),
                "points": [
                    {"i": 6107, "t": 1779417000, "d": -50.0, "cum": -50.0, "p": 7483.0},
                    {"i": 6108, "t": 1779417300, "d": 100.0, "cum": 50.0, "p": 7485.0},
                ],
            }
        )
    )
    (export_dir / "volume_profile.json").write_text(
        json.dumps(
            {
                "type": "volume_profile",
                "export_ts": int(time.time()),
                "profiles": [
                    {"bar_idx": 6107, "poc": 7483.0, "poc_vol": 50.0, "vah": 7484.0, "val": 7483.0, "total_vol": 1000.0, "levels": []},
                ],
            }
        )
    )
    # Other exports are not required for these tests — loader will skip them.

    return HistoryLoader(export_dir=export_dir, db_path=str(db_path))


class TestGapFillEndToEnd:
    def test_first_run_inserts_all(self, tmp_loader):
        summary = tmp_loader.run_gap_fill(reason="test")
        streams = summary["streams"]
        assert streams["5min.json"]["inserted"] == 2
        assert streams["cumulative_delta.json"]["inserted"] == 2
        assert streams["volume_profile.json"]["inserted"] == 1
        # last_summary cached on instance
        assert tmp_loader.last_summary is summary

    def test_second_run_is_idempotent(self, tmp_loader):
        tmp_loader.run_gap_fill(reason="first")
        summary2 = tmp_loader.run_gap_fill(reason="second")
        # Nothing new — every row already exists
        for stream, result in summary2["streams"].items():
            assert result.get("inserted", 0) == 0, f"{stream} re-inserted on second run"

    def test_stale_export_skipped(self, tmp_loader):
        # Force 5min.json to be 20 min old
        old_ts = time.time() - 1200
        os.utime(tmp_loader.export_dir / "5min.json", (old_ts, old_ts))

        summary = tmp_loader.run_gap_fill(reason="stale_test")
        assert summary["streams"]["5min.json"].get("skipped") == "export_stale"

    def test_missing_export_skipped(self, tmp_loader):
        # Run without 5min.json
        (tmp_loader.export_dir / "5min.json").unlink()
        summary = tmp_loader.run_gap_fill(reason="missing_test")
        assert summary["streams"]["5min.json"].get("skipped") == "export_missing"

    def test_format_matches_live_post_no_duplicates(self, tmp_loader):
        """The gap-fill's ``_ts_iso_from_unix`` must produce the same string
        format the live POST handler uses, so re-ingesting the same bar
        DOES dedupe via the UNIQUE constraint. Pre-fix on 2026-05-22 this
        was broken — 601 duplicate rows were inserted before discovery."""
        tmp_loader.run_gap_fill(reason="initial")
        conn = sqlite3.connect(tmp_loader.db_path)
        try:
            iso_format = conn.execute(
                "SELECT COUNT(*) FROM v9_bars_5min WHERE ts LIKE '%T%' OR ts LIKE '%+%'"
            ).fetchone()[0]
            naive_format = conn.execute(
                "SELECT COUNT(*) FROM v9_bars_5min WHERE ts NOT LIKE '%T%' AND ts NOT LIKE '%+%'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert iso_format == 0, "No ISO-T format rows allowed (would bypass UNIQUE dedupe)"
        assert naive_format == 2  # both seeded bars
