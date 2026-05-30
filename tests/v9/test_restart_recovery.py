"""Restart Recovery regression tests (R2-9, 2026-05-30).

Tests:
1. day_type_seed loads opening_type from DB instead of forcing INDETERMINATE
2. day_type_seed falls back to INDETERMINATE when no DB row exists
3. bars_5min_stream backfills on first push
"""

import sqlite3
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from bridge.v9_streams.base_stream import BaseV9Stream


# ── day_type_seed: load from DB ──

class TestDayTypeSeedFromDB:
    def _make_machine(self):
        from backend.v9.systems.day_type.schemas import Stage, DayType
        m = MagicMock()
        m.bar_count = 0
        m.opening = None
        m.ib_high = 0.0
        m.ib_low = float("inf")
        m.ib_locked = False
        m.ib_class = None
        m.stage = Stage.A1
        m.day_type = DayType.UNKNOWN
        m.confidence = 0.0
        m.config = MagicMock()
        m.config.ib_period_min = 60
        m.config.ib_narrow_max_pt = 15.0
        m.config.ib_medium_max_pt = 25.0
        return m

    def test_loads_opening_from_db_when_row_exists(self):
        """Restart after OPEN_DRIVE was saved → seed uses OPEN_DRIVE, not INDETERMINATE."""
        from backend.v9.api.v9.day_type_seed import maybe_seed_ib_from_tpo
        from backend.v9.systems.day_type.schemas import OpeningType

        m = self._make_machine()

        # Mock the DB session to return a row with OPEN_DRIVE
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("OPEN_DRIVE", "Trend_Normal", 85.0)
        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        mock_session.close = MagicMock()

        with patch("backend.v9.db.session.SessionLocal", return_value=mock_session):
            result = maybe_seed_ib_from_tpo(
                machine=m, session_min=120,
                tpo_ib_locked=True, tpo_ib_high=7600.0, tpo_ib_low=7575.0,
            )

        assert result is True
        assert m.opening.opening_type == OpeningType.OPEN_DRIVE

    def test_falls_back_to_indeterminate_when_no_row(self):
        """No DB row for today → INDETERMINATE (not crash)."""
        from backend.v9.api.v9.day_type_seed import maybe_seed_ib_from_tpo
        from backend.v9.systems.day_type.schemas import OpeningType

        m = self._make_machine()

        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = None
        mock_session.close = MagicMock()

        with patch("backend.v9.db.session.SessionLocal", return_value=mock_session):
            result = maybe_seed_ib_from_tpo(
                machine=m, session_min=120,
                tpo_ib_locked=True, tpo_ib_high=7600.0, tpo_ib_low=7575.0,
            )

        assert result is True
        assert m.opening.opening_type == OpeningType.INDETERMINATE


# ── bars_5min_stream: backfill on first push ──

class TestBars5MinBackfill:
    def test_first_push_sends_backfill_bars(self, monkeypatch):
        """First push after startup sends bars after last_db_ts, not just latest."""
        from bridge.v9_streams.bars_5min_stream import Bars5MinStream

        stream = Bars5MinStream.__new__(Bars5MinStream)
        stream._first_push = True
        stream._last_db_ts = 1000.0
        stream._stop = MagicMock()
        stream._last_mtime = 0
        stream._last_export_ts = None
        stream._last_heartbeat = 0
        stream._consecutive_errors = 0

        pushed_data = {}
        monkeypatch.setattr(BaseV9Stream, "_push_api", lambda self, d: pushed_data.update(d))

        data = {
            "bars": [
                {"ts": 900.0, "o": 100, "h": 101, "l": 99, "c": 100},
                {"ts": 1100.0, "o": 102, "h": 103, "l": 101, "c": 102},
                {"ts": 1400.0, "o": 104, "h": 105, "l": 103, "c": 104},
            ]
        }

        stream._push_api(data)

        assert len(pushed_data.get("bars", [])) == 2
        assert stream._first_push is False

    def test_second_push_sends_latest_only(self, monkeypatch):
        """After first push, normal mode sends only latest bar."""
        from bridge.v9_streams.bars_5min_stream import Bars5MinStream

        stream = Bars5MinStream.__new__(Bars5MinStream)
        stream._first_push = False
        stream._last_db_ts = 1000.0
        stream._stop = MagicMock()

        pushed_data = {}
        monkeypatch.setattr(BaseV9Stream, "_push_api", lambda self, d: pushed_data.update(d))

        data = {"bars": [
            {"ts": 1100.0, "o": 100, "h": 101, "l": 99, "c": 100},
            {"ts": 1400.0, "o": 102, "h": 103, "l": 101, "c": 102},
        ]}

        stream._push_api(data)

        assert len(pushed_data.get("bars", [])) == 1
        assert pushed_data["bars"][0]["ts"] == 1400.0
