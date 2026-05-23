"""P31 Issue B — TPOHistorySnapshotter regression tests.

These tests pin behavior that previously broke or had no coverage:

  * RTH gating uses ``market_clock.is_rth_open`` (holiday/half-day aware).
  * Stale ``tpo.json`` (>120 s) is skipped — never writes garbage to DB.
  * ``slot_start_ts_str`` truncates to the start of the 30-min slot in ET
    wall-clock format ``YYYY-MM-DD HH:MM:SS`` (matching the
    ``v9_bars_5min.ts`` convention).
  * ``next_boundary_utc`` advances by exactly ``interval_min`` from the
    current slot start, regardless of how far into the slot we are.
  * ``snapshot_now`` is idempotent thanks to ``ux_v9_tpo_history_ts`` —
    calling it twice for the same slot writes once and updates in place.
  * Schema mismatch (e.g., legacy row leaking through a shared mock) makes
    ``_load_periods_from_history`` return ``[]`` so ``_load_tpo_periods``
    falls back to ``v9_tpo_sessions`` instead of crashing.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.v9.services import tpo_history_snapshotter as snap_mod
from backend.v9.services.tpo_history_snapshotter import TPOHistorySnapshotter

ET = ZoneInfo("America/New_York")


def _seed_history_table(db_path: str) -> None:
    """Create v9_tpo_history with the production schema + unique index."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS v9_tpo_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts DATETIME NOT NULL,
                poc REAL NOT NULL,
                vah REAL NOT NULL,
                val REAL NOT NULL,
                ib_high REAL,
                ib_low REAL,
                profile_shape TEXT,
                poc_migration_direction TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ux_v9_tpo_history_ts
                ON v9_tpo_history(ts);
            """
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def snapshotter(tmp_path) -> TPOHistorySnapshotter:
    tpo_json = tmp_path / "tpo.json"
    tpo_json.write_text(
        json.dumps(
            {
                "type": "tpo",
                "version": "v9.4.2-p30.11",
                "export_ts": int(time.time()),
                "session": {
                    "poc": 7483.25,
                    "vah": 7489.25,
                    "val": 7475.25,
                    "session_high": 7494.75,
                    "session_low": 7484.25,
                },
                "ib": {"found": True, "high": 7501.75, "mid": 7495.88, "low": 7490.0},
            }
        )
    )
    db_path = tmp_path / "test.db"
    _seed_history_table(str(db_path))
    return TPOHistorySnapshotter(
        tpo_json_path=tpo_json,
        db_path=str(db_path),
        stale_threshold_s=120.0,
    )


# ----------------------------------------------------------------------
# Pure-function slot math
# ----------------------------------------------------------------------


class TestSlotMath:
    @pytest.mark.parametrize(
        "h, m, expected_min",
        [
            (9, 30, "09:30"),
            (9, 45, "09:30"),
            (10, 0, "10:00"),
            (10, 14, "10:00"),
            (10, 29, "10:00"),
            (10, 30, "10:30"),
            (15, 59, "15:30"),
        ],
    )
    def test_slot_start_ts_str_rounds_down(self, h, m, expected_min):
        et = datetime(2026, 5, 22, h, m, 0, tzinfo=ET)
        assert TPOHistorySnapshotter.slot_start_ts_str(et) == f"2026-05-22 {expected_min}:00"

    def test_next_boundary_advances_30_min_from_current_slot(self, snapshotter):
        et = datetime(2026, 5, 22, 10, 14, 0, tzinfo=ET)
        utc = snapshotter.next_boundary_utc(ref_et=et)
        # 10:00 ET slot start → next boundary is 10:30 ET = 14:30 UTC (EDT)
        assert utc.strftime("%Y-%m-%d %H:%M") == "2026-05-22 14:30"

    def test_next_boundary_handles_boundary_exact(self, snapshotter):
        et = datetime(2026, 5, 22, 10, 30, 0, tzinfo=ET)
        utc = snapshotter.next_boundary_utc(ref_et=et)
        # At exactly 10:30, next boundary is 11:00 (don't re-snapshot the same slot)
        assert utc.strftime("%Y-%m-%d %H:%M") == "2026-05-22 15:00"


# ----------------------------------------------------------------------
# snapshot_now gating
# ----------------------------------------------------------------------


class TestSnapshotGating:
    def test_skip_when_clock_pending(self, snapshotter, monkeypatch):
        from backend.v9.services.market_clock import ClockSnapshot, ClockStatus, ClockMode

        def fake_clock_state():
            return ClockSnapshot(
                mode=ClockMode.REPLAY,
                status=ClockStatus.PENDING,
                now_utc=None,
                now_et=None,
                source="replay_bar",
                reason="replay_clock_enabled_but_no_replay_timestamp",
            )

        monkeypatch.setattr(snap_mod, "current_clock_state", fake_clock_state)
        result = snapshotter.snapshot_now(reason="test")
        assert result["skipped"] == "clock_pending"

    def test_skip_when_not_rth(self, snapshotter, monkeypatch):
        monkeypatch.setattr(snap_mod, "is_rth_open", lambda et: False)
        result = snapshotter.snapshot_now(reason="test")
        assert result["skipped"] == "not_rth"

    def test_skip_when_tpo_json_missing(self, snapshotter, monkeypatch):
        monkeypatch.setattr(snap_mod, "is_rth_open", lambda et: True)
        snapshotter.tpo_json_path.unlink()
        result = snapshotter.snapshot_now(reason="test")
        assert result["skipped"] == "tpo_json_missing"

    def test_skip_when_tpo_json_stale(self, snapshotter, monkeypatch):
        monkeypatch.setattr(snap_mod, "is_rth_open", lambda et: True)
        # Force mtime older than threshold
        old_ts = time.time() - 200
        os.utime(snapshotter.tpo_json_path, (old_ts, old_ts))
        result = snapshotter.snapshot_now(reason="test")
        assert result["skipped"] == "tpo_stale"
        assert result["age_s"] > 120

    def test_skip_when_session_levels_missing(self, snapshotter, monkeypatch):
        monkeypatch.setattr(snap_mod, "is_rth_open", lambda et: True)
        snapshotter.tpo_json_path.write_text(
            json.dumps(
                {
                    "type": "tpo",
                    "session": {"poc": None, "vah": None, "val": None},
                    "ib": {"found": False},
                }
            )
        )
        result = snapshotter.snapshot_now(reason="test")
        assert result["skipped"] == "session_levels_missing"


# ----------------------------------------------------------------------
# snapshot_now writes
# ----------------------------------------------------------------------


class TestSnapshotWrite:
    def test_writes_row_when_all_checks_pass(self, snapshotter, monkeypatch):
        monkeypatch.setattr(snap_mod, "is_rth_open", lambda et: True)
        result = snapshotter.snapshot_now(reason="test")

        assert result.get("ok") is True
        assert result["poc"] == 7483.25
        assert result["vah"] == 7489.25
        assert result["val"] == 7475.25
        # IB found=True in the fixture, so ib values must round-trip
        assert result["ib_high"] == 7501.75
        assert result["ib_low"] == 7490.0

        # DB row landed
        conn = sqlite3.connect(snapshotter.db_path)
        try:
            rows = conn.execute(
                "SELECT ts, poc, vah, val, ib_high, ib_low FROM v9_tpo_history"
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        assert rows[0][1] == 7483.25  # poc
        assert rows[0][4] == 7501.75  # ib_high

    def test_ib_skipped_when_found_false(self, snapshotter, monkeypatch):
        monkeypatch.setattr(snap_mod, "is_rth_open", lambda et: True)
        # Reset tpo.json with IB found=False
        snapshotter.tpo_json_path.write_text(
            json.dumps(
                {
                    "type": "tpo",
                    "session": {"poc": 7480.0, "vah": 7485.0, "val": 7475.0},
                    "ib": {"found": False, "high": 0.0, "low": 0.0},
                }
            )
        )
        result = snapshotter.snapshot_now(reason="test")
        assert result["ok"] is True
        assert result["ib_high"] is None
        assert result["ib_low"] is None

    def test_idempotent_on_repeated_call_same_slot(self, snapshotter, monkeypatch):
        """ux_v9_tpo_history_ts UNIQUE INDEX means INSERT OR REPLACE → 1 row."""
        monkeypatch.setattr(snap_mod, "is_rth_open", lambda et: True)

        # First snapshot
        result1 = snapshotter.snapshot_now(reason="first")
        assert result1.get("ok") is True

        # Mutate the JSON so a second snapshot writes new values for the same slot
        snapshotter.tpo_json_path.write_text(
            json.dumps(
                {
                    "type": "tpo",
                    "session": {"poc": 7490.0, "vah": 7495.0, "val": 7485.0},
                    "ib": {"found": True, "high": 7501.75, "mid": 7495.88, "low": 7490.0},
                }
            )
        )
        result2 = snapshotter.snapshot_now(reason="second")
        assert result2.get("ok") is True

        conn = sqlite3.connect(snapshotter.db_path)
        try:
            rows = conn.execute("SELECT ts, poc FROM v9_tpo_history").fetchall()
        finally:
            conn.close()
        assert len(rows) == 1, "UNIQUE index on ts must keep exactly one row per slot"
        assert rows[0][1] == 7490.0, "second snapshot must overwrite the first"


# ----------------------------------------------------------------------
# tpo_routes integration — defensive fallback
# ----------------------------------------------------------------------


class TestLoadTpoPeriodsFallback:
    def test_history_schema_mismatch_falls_through_silently(self, monkeypatch):
        """If `_load_periods_from_history` gets a row without the new schema
        (e.g., shared test mock returning legacy fields), it must return []
        so `_load_tpo_periods` cascades into the sessions source instead of
        propagating a KeyError to the API caller.
        """
        from backend.v9.api.v9 import tpo_routes

        class FakeRow(dict):
            def keys(self):
                return list(super().keys())

        class FakeCursor:
            def __init__(self, rows):
                self._rows = rows

            def fetchall(self):
                return self._rows

        class FakeConn:
            def execute(self, *args, **kwargs):
                # Legacy session-shape row — missing 'ts' / 'poc' columns
                return FakeCursor([FakeRow({"opened_ts": "2026-05-21 10:00:00", "poc_price": 7400.0})])

            def close(self):
                pass

        monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: FakeConn())
        # _load_periods_from_history must return [] (not raise)
        result = tpo_routes._load_periods_from_history(limit=12)
        assert result == []
