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


def test_load_sierra_tpo_rejects_stale_file(tmp_path):
    export_path = tmp_path / "tpo.json"
    export_path.write_text(json.dumps({"type": "tpo", "session": {}}))
    old_ts = time.time() - 120
    export_path.touch()
    import os

    os.utime(export_path, (old_ts, old_ts))

    assert tpo_routes._load_sierra_tpo(export_path, max_age_s=1) is None


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
