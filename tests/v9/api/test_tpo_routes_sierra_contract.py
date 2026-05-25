import json
import time

from backend.v9.api.v9 import tpo_routes


def test_normalize_sierra_tpo_contract():
    data = {
        "type": "tpo",
        "version": "v9.4.0-p30.9",
        "export_ts": 1779134300,
        "session": {
            "poc": 7408.25,
            "vah": 7430.50,
            "val": 7388.50,
            "session_high": 7454.25,
            "session_low": 7372.75,
            "total_volume": 1622751.0,
        },
        "ib": {"found": True, "high": 7454.25, "mid": 7434.75, "low": 7415.25},
        "prior_day": {"found": True, "high": 7435.25, "low": 7375.0, "close": 7385.5},
    }

    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.234)

    assert normalized["source"] == "sierra_tpo_json"
    assert normalized["poc"] == 7408.25
    assert normalized["vah"] == 7430.50
    assert normalized["val"] == 7388.50
    assert normalized["ib_high"] == 7454.25
    assert normalized["ib_mid"] == 7434.75
    assert normalized["ib_low"] == 7415.25
    assert normalized["ib_width"] == 39.0
    assert normalized["prior_day"]["high"] == 7435.25
    assert normalized["session_va_ok"] is True
    assert normalized["ib_found"] is True


def test_load_sierra_tpo_serves_stale_file_with_flag(tmp_path):
    export_path = tmp_path / "tpo.json"
    export_path.write_text(
        json.dumps(
            {
                "type": "tpo",
                "session": {"poc": 7411.25, "vah": 7428.5, "val": 7390.75},
                "ib": {"found": True, "high": 7378.75, "mid": 7366.25, "low": 7353.75},
            }
        )
    )
    old_ts = time.time() - 120
    export_path.touch()
    import os

    os.utime(export_path, (old_ts, old_ts))

    loaded = tpo_routes._load_sierra_tpo(export_path, max_age_s=1)
    assert loaded is not None
    assert loaded["stale"] is True
    assert loaded["poc"] == 7411.25
    assert loaded["session_va_ok"] is True


def test_va_spread_rejects_collapsed_session():
    assert tpo_routes._va_spread_ok(7392.5, 7393.5, 7392.5) is False
    assert tpo_routes._va_spread_ok(7411.25, 7428.5, 7390.75) is True


def test_normalize_emits_session_opened_ts_for_rth_anchor():
    """Frontend POC line anchors at RTH open; backend must always provide it.

    Sierra `tpo.json` currently omits `session.opened_ts`, so the backend
    computes 09:30 ET of the current trading day. Without this anchor the
    pink current-day POC starts at the first visible bar instead of RTH
    open — root cause of the "POC not big from RTH start" complaint.
    """
    data = {
        "type": "tpo",
        "session": {"poc": 7408.25, "vah": 7430.50, "val": 7388.50},
        "ib": {"found": True, "high": 7454.25, "mid": 7434.75, "low": 7415.25},
        "prior_day": {"found": True, "high": 7435.25, "low": 7375.0, "close": 7385.5},
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    assert normalized["session_opened_ts"] is not None
    assert normalized["session_opened_ts"].endswith(" 09:30:00")


def test_normalize_prefers_export_session_opened_ts_when_present():
    """If Sierra DLL ever exports session.opened_ts, honour it verbatim."""
    data = {
        "type": "tpo",
        "session": {
            "poc": 7408.25,
            "vah": 7430.50,
            "val": 7388.50,
            "opened_ts": "2026-05-19T09:30:00-04:00",
        },
        "ib": {"found": True, "high": 7454.25, "mid": 7434.75, "low": 7415.25},
        "prior_day": {"found": False},
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    assert normalized["session_opened_ts"] == "2026-05-19 09:30:00"


def test_load_tpo_periods_normalizes_unix_ts(monkeypatch):
    import sqlite3

    class FakeConn:
        def execute(self, *args, **kwargs):
            class R:
                def fetchall(self):
                    return [
                        {
                            "opened_ts": 1779141600,
                            "closed_ts": None,
                            "poc_price": 7415.25,
                            "vah_price": 7420.0,
                            "val_price": 7410.0,
                        }
                    ]

            return R()

        def close(self):
            pass

    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: FakeConn())
    periods = tpo_routes._load_tpo_periods(limit=1)
    assert periods[0]["poc_price"] == 7415.25
    assert periods[0]["opened_ts"].startswith("2026-")


def test_normalize_rejects_invalid_va_without_synthesis(monkeypatch, caplog):
    """Memorial Day fix #3 · CLAUDE.md compliance.

    When Sierra session VA is invalid, backend MUST return poc=None.
    It must NOT silently substitute stale DB period data.
    """
    import logging

    stale_periods = [
        {"poc_price": 7501.5, "vah_price": 7517.5, "val_price": 7485.5,
         "opened_ts": "2026-05-22 09:30:00", "closed_ts": "2026-05-22 16:00:00"},
    ]
    monkeypatch.setattr(tpo_routes, "_load_tpo_periods", lambda *a, **k: stale_periods)

    data = {
        "type": "tpo",
        "session": {"poc": 0.0, "vah": 0.0, "val": 0.0, "va_ok": False},
        "ib": {"found": False, "high": 0, "mid": 0, "low": 0},
        "prior_day": {"found": False},
    }

    with caplog.at_level(logging.WARNING, logger="backend.v9.api.v9.tpo_routes"):
        normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)

    assert normalized["poc"] is None, "synthesis leaked: poc should be None"
    assert normalized["vah"] is None, "synthesis leaked: vah should be None"
    assert normalized["val"] is None, "synthesis leaked: val should be None"
    assert normalized["session_va_ok"] is False
    assert any(
        "Sierra session VA invalid" in r.message and "rejecting" in r.message
        for r in caplog.records
    ), "expected warning log on rejection"


def test_normalize_valid_va_unchanged_by_fix3(monkeypatch):
    """Regression: Fix #3 must NOT affect the happy path."""
    monkeypatch.setattr(tpo_routes, "_load_tpo_periods", lambda *a, **k: [
        {"poc_price": 9999.0, "vah_price": 9999.0, "val_price": 9999.0}
    ])
    data = {
        "type": "tpo",
        "session": {"poc": 7559.5, "vah": 7563.5, "val": 7555.75},
        "ib": {"found": True, "high": 7570, "mid": 7562, "low": 7554},
        "prior_day": {"found": True, "high": 7524, "low": 7478.75, "close": 7484.25},
    }
    normalized = tpo_routes._normalize_sierra_tpo(data, age_s=1.0)
    assert normalized["poc"] == 7559.5
    assert normalized["session_va_ok"] is True
    assert normalized["poc"] != 9999.0
