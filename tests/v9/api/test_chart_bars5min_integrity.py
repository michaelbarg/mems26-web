"""Regression tests for P27.5a chart 5-minute bar integrity."""

import sqlite3

from backend.v9.api.v9 import bars_5min_history
from backend.v9.services import bar_ingestion


def _create_bars_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE v9_bars_5min (
            ts TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
        """
    )
    return conn


def test_bars5min_history_filters_known_bad_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "bars.db"
    conn = _create_bars_db(db_path)
    rows = [
        ("2026-05-16 05:00:00.000000", 7460.0, 7464.0, 7458.0, 7462.0, 1000),
        ("2026-05-16 05:05:00.000000", 7462.25, 7463.0, 7180.25, 7180.25, 890003),
        ("2026-05-16 05:10:00.000000", 7462.0, 7465.0, 7459.0, 7461.0, 1001),
    ]
    conn.executemany("INSERT INTO v9_bars_5min VALUES (?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()

    monkeypatch.setattr(bars_5min_history, "DB_PATH", str(db_path))

    bars = bars_5min_history._fetch_bars_5min(limit=10)

    assert [bar["ts"] for bar in bars] == [
        "2026-05-16 05:00:00.000000",
        "2026-05-16 05:10:00.000000",
    ]
    assert all(bar["high"] - bar["low"] < 20 for bar in bars)


def test_bar_ingestion_rejects_invalid_bar_before_db(monkeypatch):
    def fail_if_called():
        raise AssertionError("SessionLocal should not be called for invalid bars")

    monkeypatch.setattr(bar_ingestion, "SessionLocal", fail_if_called)

    service = bar_ingestion.BarIngestionService()
    accepted = service.ingest_bar(
        {
            "ts": "2026-05-16 05:05:00.000000",
            "symbol": "MES",
            "open": 7462.25,
            "high": 7463.0,
            "low": 7180.25,
            "close": 7180.25,
            "volume": 890003,
        }
    )

    assert accepted is False
    assert service._bars_ingested == 0
