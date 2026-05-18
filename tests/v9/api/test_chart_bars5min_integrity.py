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


def test_bars5min_history_returns_newest_limit_rows(tmp_path, monkeypatch):
    """Regression: P27.5a over-fetch must not drop the newest bars.

    The endpoint over-fetches `limit + 20` rows from the DB to compensate for
    rows the integrity filter may strip. Before this fix, the slice used
    `result[:limit]`, which kept the OLDEST `limit` rows and silently dropped
    the 20 newest bars (e.g. all RTH bars after 08:10 disappeared from the chart).
    The correct slice is `result[-limit:]`.
    """
    db_path = tmp_path / "bars.db"
    conn = _create_bars_db(db_path)
    # Insert 25 valid sequential bars: 09:00 .. 11:00 (5-min step)
    rows = []
    base_price = 7400.0
    for i in range(25):
        hh = 9 + (i * 5) // 60
        mm = (i * 5) % 60
        ts = f"2026-05-16 {hh:02d}:{mm:02d}:00.000000"
        o = base_price + i
        rows.append((ts, o, o + 2, o - 2, o + 1, 1000 + i))
    conn.executemany("INSERT INTO v9_bars_5min VALUES (?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()

    monkeypatch.setattr(bars_5min_history, "DB_PATH", str(db_path))

    bars = bars_5min_history._fetch_bars_5min(limit=5)

    assert len(bars) == 5
    # Newest 5 bars: indices 20..24 → ts 10:40 .. 11:00
    assert [bar["ts"] for bar in bars] == [
        "2026-05-16 10:40:00.000000",
        "2026-05-16 10:45:00.000000",
        "2026-05-16 10:50:00.000000",
        "2026-05-16 10:55:00.000000",
        "2026-05-16 11:00:00.000000",
    ]


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
