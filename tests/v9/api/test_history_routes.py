"""P30 G6 — Tests for /api/v9/history/* and the EOD archiver service.

Covers:
  * archive_today copies all Sierra exports present and skips missing ones
  * read_session bundles JSON files for a date
  * list_archived_dates sorts newest-first
  * GET /api/v9/history/{date}, /yesterday, /dates
  * POST /api/v9/history/archive_now
  * Idempotency: re-archiving overwrites
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.v9.app import app
from backend.v9.services import eod_archiver

client = TestClient(app)


SAMPLE_CVD = {
    "type": "cumulative_delta",
    "version": "v9.4.2",
    "export_ts": 1779200000,
    "points": [{"i": 100, "t": 1779100000, "d": -88, "cum": -88, "p": 7400.0}],
}
SAMPLE_TPO = {
    "type": "tpo",
    "version": "v9.4.2",
    "session": {"poc": 7400.0, "vah": 7405.0, "val": 7395.0},
}
SAMPLE_5MIN = {
    "type": "5min",
    "bars": [{"ts": 1779200000, "o": 7400, "h": 7405, "l": 7398, "c": 7402, "vol": 1000}],
}


def _populate_export_dir(d: Path) -> None:
    (d / "cumulative_delta.json").write_text(json.dumps(SAMPLE_CVD))
    (d / "tpo.json").write_text(json.dumps(SAMPLE_TPO))
    (d / "5min.json").write_text(json.dumps(SAMPLE_5MIN))


def test_archive_today_copies_present_files(monkeypatch, tmp_path):
    export_dir = tmp_path / "export"
    archive_dir = tmp_path / "archive"
    export_dir.mkdir()
    _populate_export_dir(export_dir)

    monkeypatch.setattr(eod_archiver, "EXPORT_DIR", export_dir)
    monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", archive_dir)

    result = eod_archiver.archive_today(target_date="2026-05-19")
    assert result["date"] == "2026-05-19"
    assert set(result["archived"]) == {"cumulative_delta.json", "tpo.json", "5min.json"}
    # All the other expected files were missing — must show up in `skipped`.
    assert "woodies_5min.json" in result["skipped"]
    # On-disk verification
    out = archive_dir / "2026-05-19"
    assert (out / "cumulative_delta.json").exists()
    assert json.loads((out / "tpo.json").read_text())["session"]["poc"] == 7400.0


def test_archive_today_idempotent_overwrite(monkeypatch, tmp_path):
    export_dir = tmp_path / "export"
    archive_dir = tmp_path / "archive"
    export_dir.mkdir()
    _populate_export_dir(export_dir)
    monkeypatch.setattr(eod_archiver, "EXPORT_DIR", export_dir)
    monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", archive_dir)

    eod_archiver.archive_today(target_date="2026-05-19")
    # Change the source then re-archive — the new content must overwrite.
    (export_dir / "tpo.json").write_text(json.dumps({"session": {"poc": 9999.0}}))
    eod_archiver.archive_today(target_date="2026-05-19")
    stored = json.loads((archive_dir / "2026-05-19" / "tpo.json").read_text())
    assert stored["session"]["poc"] == 9999.0


def test_list_archived_dates_sorted_newest_first(monkeypatch, tmp_path):
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    for d in ("2026-05-15", "2026-05-19", "2026-05-17"):
        (archive_dir / d).mkdir()
    # Decoy: short folder name, ignore
    (archive_dir / "tmp").mkdir()
    monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", archive_dir)
    assert eod_archiver.list_archived_dates() == ["2026-05-19", "2026-05-17", "2026-05-15"]


def test_read_session_returns_only_available_files(monkeypatch, tmp_path):
    archive_dir = tmp_path / "archive"
    sess = archive_dir / "2026-05-19"
    sess.mkdir(parents=True)
    (sess / "cumulative_delta.json").write_text(json.dumps(SAMPLE_CVD))
    monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", archive_dir)

    payload = eod_archiver.read_session("2026-05-19")
    assert payload["date"] == "2026-05-19"
    assert payload["available_files"] == ["cumulative_delta.json"]
    assert payload["cumulative_delta"]["version"] == "v9.4.2"
    # Absent files must NOT appear as keys.
    assert "tpo" not in payload
    assert "5min" not in payload


def test_endpoint_history_dates_lists_archive(monkeypatch, tmp_path):
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    (archive_dir / "2026-05-19").mkdir()
    monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", archive_dir)

    resp = client.get("/api/v9/history/dates")
    assert resp.status_code == 200
    assert resp.json() == {"dates": ["2026-05-19"]}


def test_endpoint_history_by_date_404_on_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", tmp_path / "archive_missing")
    resp = client.get("/api/v9/history/2026-05-19")
    assert resp.status_code == 404
    assert "no archive" in resp.json()["detail"]


def test_endpoint_history_by_date_bad_format():
    resp = client.get("/api/v9/history/2026-5-1")
    assert resp.status_code == 400


def test_endpoint_archive_now_writes_files(monkeypatch, tmp_path):
    export_dir = tmp_path / "export"
    archive_dir = tmp_path / "archive"
    export_dir.mkdir()
    _populate_export_dir(export_dir)
    monkeypatch.setattr(eod_archiver, "EXPORT_DIR", export_dir)
    monkeypatch.setattr(eod_archiver, "ARCHIVE_DIR", archive_dir)

    resp = client.post("/api/v9/history/archive_now?date=2026-05-19")
    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2026-05-19"
    assert "cumulative_delta.json" in data["archived"]
    assert (archive_dir / "2026-05-19" / "tpo.json").exists()


def test_endpoint_archive_now_rejects_bad_date():
    resp = client.post("/api/v9/history/archive_now?date=invalid")
    assert resp.status_code == 400
