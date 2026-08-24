"""Regression: SCID truth and DB bars must be compared in the same ET clock."""
from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "rebuild_bar_truth_test", ROOT / "scripts" / "rebuild_bar_truth.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_compare_to_db_selects_explicit_et_wall_clock(monkeypatch):
    captured = {}

    def fake_read_all(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        # The SQL alias must return naive America/New_York wall-clock.
        return [{
            "ts": dt.datetime(2026, 8, 21, 9, 30),
            "high": 7700.0,
            "low": 7690.0,
            "close": 7695.0,
        }]

    import backend.v9.db.read as db_read
    monkeypatch.setattr(db_read, "read_all", fake_read_all)
    truth = [{
        "ts": dt.datetime(
            2026, 8, 21, 13, 30, tzinfo=dt.timezone.utc),
        "o": 7694.0,
        "h": 7700.0,
        "l": 7690.0,
        "c": 7695.0,
        "vol": 100,
    }]

    result = MOD.compare_to_db(truth, "2026-08-21")

    assert "AT TIME ZONE 'America/New_York'" in captured["sql"]
    assert result["matches"] == 1
    assert result["mismatches_count"] == 0
