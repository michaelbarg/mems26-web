"""P31 Phase 1 — EODArchiveScheduler + eod_archiver retention regression tests.

Pins:

  * ``ARCHIVED_FILES`` covers all 14 Sierra exports (10 original + 4 added in
    Phase 1: live_price.json, tick_reversal_12.json, tick_reversal_15.json,
    reversal_cluster.json). If a new export is added to the DLL, the test
    fails so the operator is forced to update ``ARCHIVED_FILES``.
  * ``ARCHIVE_RETENTION_DAYS`` defaults to 90 (Michael's choice in the
    unified-history review).
  * ``prune_old_archives`` deletes folders older than the cutoff and keeps
    the rest. Folders that don't parse as ``YYYY-MM-DD`` are skipped, not
    deleted (defensive against operator-created sub-folders).
  * ``EODArchiveScheduler.next_archive_utc`` advances past weekends and
    market holidays — Sunday → Monday, Thanksgiving Thursday → Friday.
  * ``archive_if_due`` skips weekends, holidays, and the pre-15:55 window.
  * ``archive_if_due`` succeeds at 16:00 ET on a normal RTH day and invokes
    both ``archive_today`` and ``prune_old_archives``.
"""

from __future__ import annotations

import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from backend.v9.services import eod_archiver, eod_archive_scheduler as sched_mod
from backend.v9.services.eod_archive_scheduler import EODArchiveScheduler

ET = ZoneInfo("America/New_York")


# ----------------------------------------------------------------------
# ARCHIVED_FILES coverage
# ----------------------------------------------------------------------


class TestArchivedFilesCoverage:
    def test_all_14_sierra_exports_listed(self):
        expected = {
            # Original P30 G6 set
            "5min.json",
            "cumulative_delta.json",
            "tpo.json",
            "woodies_5min.json",
            "woodies_30min.json",
            "volume_profile.json",
            "footprint.json",
            "imbalance_flags.json",
            "stacked_imbalances.json",
            "mes_ai_data.json",
            # P31 Phase 1 additions (Michael 2026-05-22)
            "live_price.json",
            "tick_reversal_12.json",
            "tick_reversal_15.json",
            "reversal_cluster.json",
        }
        assert set(eod_archiver.ARCHIVED_FILES) == expected, (
            "ARCHIVED_FILES drifted from the 14-file Sierra export set. "
            "If a new export is intentional, update the test and document "
            "the addition in eod_archiver.py."
        )

    def test_retention_default_90_days(self):
        # Michael selected `90_days` in the unified-history architecture review.
        assert eod_archiver.ARCHIVE_RETENTION_DAYS == 90


# ----------------------------------------------------------------------
# prune_old_archives
# ----------------------------------------------------------------------


class TestPruneOldArchives:
    @pytest.fixture
    def isolated_archive_dir(self, tmp_path, monkeypatch):
        """Redirect ARCHIVE_DIR to a temp tree for the test."""
        archive_dir = tmp_path / "archives"
        archive_dir.mkdir()
        monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", archive_dir)
        return archive_dir

    def _make_folder(self, archive_dir: Path, name: str) -> Path:
        f = archive_dir / name
        f.mkdir()
        (f / "marker.json").write_text("{}")
        return f

    def test_prune_deletes_older_than_retention(self, isolated_archive_dir):
        today_et = datetime.now(tz=ET).date()
        # Within retention
        recent = self._make_folder(isolated_archive_dir, (today_et - timedelta(days=5)).isoformat())
        edge = self._make_folder(isolated_archive_dir, (today_et - timedelta(days=89)).isoformat())
        # Outside retention
        old = self._make_folder(isolated_archive_dir, (today_et - timedelta(days=91)).isoformat())
        ancient = self._make_folder(isolated_archive_dir, (today_et - timedelta(days=365)).isoformat())

        result = eod_archiver.prune_old_archives()

        assert recent.exists()
        assert edge.exists()
        assert not old.exists()
        assert not ancient.exists()
        assert set(result["deleted"]) == {old.name, ancient.name}
        assert set(result["kept"]) == {recent.name, edge.name}

    def test_prune_skips_non_date_folders(self, isolated_archive_dir):
        weird = isolated_archive_dir / "manual-export-2026"
        weird.mkdir()
        (weird / "data.json").write_text("{}")

        result = eod_archiver.prune_old_archives()

        assert weird.exists(), "non-date folders must not be deleted"
        assert weird.name in result["skipped"]

    def test_prune_empty_archive_dir_is_safe(self, tmp_path, monkeypatch):
        empty_dir = tmp_path / "empty-archives"
        monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", empty_dir)
        result = eod_archiver.prune_old_archives()
        assert result == {"retention_days": 90, "deleted": [], "kept": [], "skipped": []}

    def test_prune_honours_custom_retention(self, isolated_archive_dir):
        today_et = datetime.now(tz=ET).date()
        f7 = self._make_folder(isolated_archive_dir, (today_et - timedelta(days=7)).isoformat())
        f3 = self._make_folder(isolated_archive_dir, (today_et - timedelta(days=3)).isoformat())

        result = eod_archiver.prune_old_archives(retention_days=5)

        assert f3.exists()
        assert not f7.exists()
        assert f7.name in result["deleted"]


# ----------------------------------------------------------------------
# EODArchiveScheduler — scheduling math
# ----------------------------------------------------------------------


class TestSchedulingMath:
    def test_next_archive_skips_to_tomorrow_after_threshold(self):
        sched = EODArchiveScheduler()
        # Tuesday 16:00 ET — past 15:55 today, so next is Wednesday 15:55 ET
        ref = datetime(2026, 5, 19, 16, 0, 0, tzinfo=ET)  # Tuesday
        nxt = sched.next_archive_utc(ref_et=ref)
        # 15:55 ET = 19:55 UTC (EDT)
        assert nxt.strftime("%Y-%m-%d %H:%M") == "2026-05-20 19:55"

    def test_next_archive_uses_today_when_before_threshold(self):
        sched = EODArchiveScheduler()
        ref = datetime(2026, 5, 19, 10, 0, 0, tzinfo=ET)  # Tuesday morning
        nxt = sched.next_archive_utc(ref_et=ref)
        assert nxt.strftime("%Y-%m-%d %H:%M") == "2026-05-19 19:55"

    def test_next_archive_skips_weekend(self):
        sched = EODArchiveScheduler()
        # Friday May 15 16:00 ET — Sat/Sun are weekend → Monday May 18.
        # (Picked a Friday that *isn't* followed by a holiday so the test
        # isolates the weekend-skip logic from the holiday-skip logic.)
        ref = datetime(2026, 5, 15, 16, 0, 0, tzinfo=ET)
        nxt = sched.next_archive_utc(ref_et=ref)
        assert nxt.strftime("%Y-%m-%d") == "2026-05-18"

    def test_next_archive_skips_market_holiday(self):
        sched = EODArchiveScheduler()
        # Memorial Day 2026 = 2026-05-25 (Monday); next archive should be Tuesday
        ref = datetime(2026, 5, 22, 16, 0, 0, tzinfo=ET)  # Friday before Memorial Day
        nxt = sched.next_archive_utc(ref_et=ref)
        assert nxt.strftime("%Y-%m-%d") == "2026-05-26"  # Tuesday — skips Monday holiday


# ----------------------------------------------------------------------
# EODArchiveScheduler — archive_if_due gating
# ----------------------------------------------------------------------


class TestArchiveIfDueGating:
    @pytest.fixture
    def isolated_export_archive(self, tmp_path, monkeypatch):
        """Point both EXPORT_DIR and ARCHIVE_DIR at temp paths so the test
        doesn't touch real Sierra files."""
        export = tmp_path / "v9_export"
        export.mkdir()
        # Seed minimal exports so archive_today has something to copy
        for fname in ("5min.json", "tpo.json"):
            (export / fname).write_text("{}")
        archive = tmp_path / "v9_archive"
        archive.mkdir()
        monkeypatch.setattr(eod_archiver, "EXPORT_DIR", export)
        monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", archive)
        return export, archive

    def test_skip_when_clock_pending(self, isolated_export_archive, monkeypatch):
        from backend.v9.services.market_clock import ClockSnapshot, ClockStatus, ClockMode

        def fake_state():
            return ClockSnapshot(
                mode=ClockMode.REPLAY,
                status=ClockStatus.PENDING,
                now_utc=None,
                now_et=None,
                source="replay_bar",
                reason="pending",
            )

        monkeypatch.setattr(sched_mod, "current_clock_state", fake_state)
        sched = EODArchiveScheduler()
        result = sched.archive_if_due(reason="test")
        assert result["skipped"] == "clock_pending"

    def test_skip_on_weekend(self, isolated_export_archive, monkeypatch):
        from backend.v9.services.market_clock import ClockSnapshot, ClockStatus, ClockMode

        saturday = datetime(2026, 5, 23, 16, 0, 0, tzinfo=ET)  # Saturday

        def fake_state():
            return ClockSnapshot(
                mode=ClockMode.REALTIME,
                status=ClockStatus.READY,
                now_utc=saturday.astimezone(ZoneInfo("UTC")),
                now_et=saturday,
                source="test",
            )

        monkeypatch.setattr(sched_mod, "current_clock_state", fake_state)
        sched = EODArchiveScheduler()
        result = sched.archive_if_due(reason="test")
        assert result["skipped"] == "weekend"

    def test_skip_on_holiday(self, isolated_export_archive, monkeypatch):
        from backend.v9.services.market_clock import ClockSnapshot, ClockStatus, ClockMode

        memorial_day = datetime(2026, 5, 25, 16, 0, 0, tzinfo=ET)

        def fake_state():
            return ClockSnapshot(
                mode=ClockMode.REALTIME,
                status=ClockStatus.READY,
                now_utc=memorial_day.astimezone(ZoneInfo("UTC")),
                now_et=memorial_day,
                source="test",
            )

        monkeypatch.setattr(sched_mod, "current_clock_state", fake_state)
        sched = EODArchiveScheduler()
        result = sched.archive_if_due(reason="test")
        assert result["skipped"] == "holiday"

    def test_skip_before_archive_time(self, isolated_export_archive, monkeypatch):
        from backend.v9.services.market_clock import ClockSnapshot, ClockStatus, ClockMode

        morning = datetime(2026, 5, 22, 10, 0, 0, tzinfo=ET)  # Friday morning

        def fake_state():
            return ClockSnapshot(
                mode=ClockMode.REALTIME,
                status=ClockStatus.READY,
                now_utc=morning.astimezone(ZoneInfo("UTC")),
                now_et=morning,
                source="test",
            )

        monkeypatch.setattr(sched_mod, "current_clock_state", fake_state)
        sched = EODArchiveScheduler()
        result = sched.archive_if_due(reason="test")
        assert result["skipped"] == "before_archive_time"

    def test_archives_at_close_on_trading_day(self, isolated_export_archive, monkeypatch):
        from backend.v9.services.market_clock import ClockSnapshot, ClockStatus, ClockMode

        export_dir, archive_dir = isolated_export_archive
        close_time = datetime(2026, 5, 22, 16, 0, 0, tzinfo=ET)  # Friday 16:00 ET

        def fake_state():
            return ClockSnapshot(
                mode=ClockMode.REALTIME,
                status=ClockStatus.READY,
                now_utc=close_time.astimezone(ZoneInfo("UTC")),
                now_et=close_time,
                source="test",
            )

        monkeypatch.setattr(sched_mod, "current_clock_state", fake_state)
        sched = EODArchiveScheduler()
        result = sched.archive_if_due(reason="scheduled")
        assert result.get("ok") is True
        assert (archive_dir / "2026-05-22").exists()
        assert "archive" in result
        assert "prune" in result
