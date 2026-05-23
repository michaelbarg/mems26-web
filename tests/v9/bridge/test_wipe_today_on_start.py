"""Regression tests for `bridge.v9_startup.wipe_today_bars_if_requested`.

P30 (2026-05-20): the bridge can be asked to wipe today's session bars on
startup. The four mandatory axes for this hook:

  1. Flag OFF → no DELETE issued (we mock sqlite3.connect to assert it
     was never opened).
  2. Flag ON + empty DB → wipe runs, reports 0 rows, no error path.
  3. Flag ON + 5 bars today + 10 bars yesterday → exactly the 5 today
     rows are deleted; yesterday is untouched (TPO / Day Type depend
     on multi-day windows).
  4. Flag ON + DB error → returns 0, logs a warning, and DOES NOT raise
     (bridge startup must continue).

Today is anchored via the `now_et_fn` injection so the test is stable
across calendar days and across local-machine timezones.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Tuple
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from bridge.v9_startup import (
    WIPE_FLAG_ENV,
    _resolve_sqlite_path,
    _today_midnight_utc_iso,
    wipe_today_bars_if_requested,
)

NY = ZoneInfo("America/New_York")


def _seed_db(path: Path) -> sqlite3.Connection:
    """Create a `v9_bars_5min` table matching the real schema's ts column."""
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE v9_bars_5min (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            symbol TEXT NOT NULL DEFAULT 'MES',
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    return conn


def _insert(
    conn: sqlite3.Connection,
    ts: str,
    *,
    symbol: str = "MES",
    o: float = 5400.0,
) -> None:
    conn.execute(
        "INSERT INTO v9_bars_5min (ts, symbol, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ts, symbol, o, o + 1, o - 1, o, 100),
    )


def _fixed_now_et(year: int, month: int, day: int, hour: int = 12) -> datetime:
    """Stable America/New_York reference point for `now_et_fn`."""
    return datetime(year, month, day, hour, 0, tzinfo=NY)


@pytest.fixture
def db_paths(tmp_path: Path) -> Iterator[Tuple[Path, str]]:
    """Empty SQLite DB ready for tests to seed. Yields (path, db_url)."""
    db_path = tmp_path / "bars.db"
    db_url = f"sqlite:///{db_path}"
    yield db_path, db_url


@pytest.fixture(autouse=True)
def _clear_wipe_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test owns its flag — clear any leakage from the parent env."""
    monkeypatch.delenv(WIPE_FLAG_ENV, raising=False)


# ── Helpers ──


def test_resolve_sqlite_path_absolute() -> None:
    assert _resolve_sqlite_path("sqlite:////tmp/foo.db") == Path("/tmp/foo.db")


def test_resolve_sqlite_path_relative_resolves_to_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    resolved = _resolve_sqlite_path("sqlite:///./data/foo.db")
    assert resolved is not None
    assert resolved.is_absolute()
    assert resolved.name == "foo.db"


def test_resolve_sqlite_path_non_sqlite_returns_none() -> None:
    assert _resolve_sqlite_path("postgresql://user:pass@host/db") is None


def test_today_midnight_utc_iso_during_edt() -> None:
    """EDT (Mar–Nov): midnight ET = 04:00 UTC same calendar day."""
    iso = _today_midnight_utc_iso(_fixed_now_et(2026, 5, 20, hour=14))
    assert iso == "2026-05-20 04:00:00"


def test_today_midnight_utc_iso_during_est() -> None:
    """EST (Nov–Mar): midnight ET = 05:00 UTC same calendar day."""
    iso = _today_midnight_utc_iso(_fixed_now_et(2026, 1, 15, hour=14))
    assert iso == "2026-01-15 05:00:00"


# ── Behaviour ──


def test_flag_off_does_not_open_db(db_paths: Tuple[Path, str]) -> None:
    """Without the flag, no DB connection is opened. Zero rows reported."""
    _, db_url = db_paths
    with patch("bridge.v9_startup.sqlite3.connect") as mock_connect:
        deleted = wipe_today_bars_if_requested(database_url=db_url)
    assert deleted == 0
    mock_connect.assert_not_called()


def test_flag_on_empty_db_reports_zero(
    db_paths: Tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flag on, empty table → 0 deleted, no exception."""
    db_path, db_url = db_paths
    conn = _seed_db(db_path)
    conn.close()
    monkeypatch.setenv(WIPE_FLAG_ENV, "1")
    deleted = wipe_today_bars_if_requested(
        database_url=db_url,
        now_et_fn=lambda: _fixed_now_et(2026, 5, 20, hour=12),
    )
    assert deleted == 0


def test_flag_on_today_5_yesterday_10_wipes_only_today(
    db_paths: Tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """5 today (≥ 04:00 UTC) + 10 yesterday (< 04:00 UTC) → exactly 5 deleted.

    Anchor: today = 2026-05-20 12:00 ET (DST → midnight ET = 04:00 UTC).
    Pre-cutoff (yesterday in ET terms) rows are stamped 2026-05-19 22:XX,
    2026-05-20 00:XX – 03:XX UTC. Today rows are stamped 2026-05-20
    04:00 UTC and later.
    """
    db_path, db_url = db_paths
    conn = _seed_db(db_path)
    # Yesterday (in ET) — all strictly BEFORE 2026-05-20 04:00 UTC
    yesterday_stamps = [
        "2026-05-19 14:00:00.000000",
        "2026-05-19 18:30:00.000000",
        "2026-05-19 22:00:00.000000",
        "2026-05-19 23:00:00.000000",
        "2026-05-19 23:55:00.000000",
        "2026-05-20 00:00:00.000000",  # 20:00 ET on 2026-05-19
        "2026-05-20 01:00:00.000000",  # 21:00 ET on 2026-05-19
        "2026-05-20 02:00:00.000000",
        "2026-05-20 03:00:00.000000",
        "2026-05-20 03:55:00.000000",  # 23:55 ET on 2026-05-19
    ]
    # Today (in ET) — all AT OR AFTER 2026-05-20 04:00 UTC
    today_stamps = [
        "2026-05-20 04:00:00.000000",  # exactly midnight ET → must be wiped
        "2026-05-20 13:30:00.000000",
        "2026-05-20 14:30:00.000000",
        "2026-05-20 19:55:00.000000",
        "2026-05-20 20:00:00.000000",  # 16:00 ET (RTH close)
    ]
    for ts in yesterday_stamps + today_stamps:
        _insert(conn, ts)
    conn.commit()
    conn.close()

    monkeypatch.setenv(WIPE_FLAG_ENV, "1")
    deleted = wipe_today_bars_if_requested(
        database_url=db_url,
        now_et_fn=lambda: _fixed_now_et(2026, 5, 20, hour=12),
    )
    assert deleted == 5

    # Cardinality check — yesterday's 10 must survive.
    conn = sqlite3.connect(str(db_path))
    remaining = [row[0] for row in conn.execute("SELECT ts FROM v9_bars_5min ORDER BY ts ASC")]
    conn.close()
    assert remaining == yesterday_stamps


def test_flag_on_db_missing_warns_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """DB file missing → returns 0, logs warning, never raises."""
    missing = tmp_path / "does_not_exist.db"
    monkeypatch.setenv(WIPE_FLAG_ENV, "1")
    with caplog.at_level("WARNING", logger="v9_bridge"):
        deleted = wipe_today_bars_if_requested(
            database_url=f"sqlite:///{missing}",
            now_et_fn=lambda: _fixed_now_et(2026, 5, 20),
        )
    assert deleted == 0
    assert any("DB file" in r.message and "missing" in r.message for r in caplog.records)


def test_flag_on_db_error_continues_startup(
    db_paths: Tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the DELETE blows up, bridge MUST keep starting. Returns 0, logs warning."""
    db_path, db_url = db_paths
    conn = _seed_db(db_path)
    conn.close()
    monkeypatch.setenv(WIPE_FLAG_ENV, "1")

    real_connect = sqlite3.connect

    class _BoomConn:
        def __init__(self, target: sqlite3.Connection) -> None:
            self._target = target

        def execute(self, *_args, **_kwargs):
            raise sqlite3.OperationalError("simulated DB lock")

        def commit(self) -> None:
            self._target.commit()

        def close(self) -> None:
            self._target.close()

    def _boom_connect(*args, **kwargs):
        return _BoomConn(real_connect(*args, **kwargs))

    with patch("bridge.v9_startup.sqlite3.connect", side_effect=_boom_connect):
        with caplog.at_level("WARNING", logger="v9_bridge"):
            deleted = wipe_today_bars_if_requested(
                database_url=db_url,
                now_et_fn=lambda: _fixed_now_et(2026, 5, 20),
            )

    assert deleted == 0
    assert any("wipe-today" in r.message for r in caplog.records)


def test_flag_on_non_sqlite_url_skips_with_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Production Postgres is out of scope — skip safely with a warning."""
    monkeypatch.setenv(WIPE_FLAG_ENV, "1")
    with caplog.at_level("WARNING", logger="v9_bridge"):
        deleted = wipe_today_bars_if_requested(
            database_url="postgresql://user:pass@host/db",
            now_et_fn=lambda: _fixed_now_et(2026, 5, 20),
        )
    assert deleted == 0
    assert any("not SQLite" in r.message for r in caplog.records)


@pytest.mark.parametrize("falsy", ["", "0", "false", "no", "off", "FALSE", "  "])
def test_falsy_flag_values_keep_wipe_off(
    falsy: str, db_paths: Tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only explicit truthy values trigger the wipe."""
    monkeypatch.setenv(WIPE_FLAG_ENV, falsy)
    _, db_url = db_paths
    with patch("bridge.v9_startup.sqlite3.connect") as mock_connect:
        deleted = wipe_today_bars_if_requested(database_url=db_url)
    assert deleted == 0
    mock_connect.assert_not_called()


@pytest.mark.parametrize("truthy", ["1", "true", "TRUE", "Yes", "yes"])
def test_truthy_flag_values_trigger_wipe(
    truthy: str,
    db_paths: Tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accepted truthy spellings: '1', 'true', 'yes' (case-insensitive)."""
    db_path, db_url = db_paths
    conn = _seed_db(db_path)
    # one today row to verify wipe ran
    _insert(conn, "2026-05-20 12:00:00.000000")
    conn.commit()
    conn.close()
    monkeypatch.setenv(WIPE_FLAG_ENV, truthy)
    deleted = wipe_today_bars_if_requested(
        database_url=db_url,
        now_et_fn=lambda: _fixed_now_et(2026, 5, 20),
    )
    assert deleted == 1


def test_flag_on_does_not_touch_other_tables(
    db_paths: Tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sibling tables (TPO sessions, woodies) must survive — the wipe is
    SCOPED to v9_bars_5min only because Day Type Engine and TPO require
    multi-day data."""
    db_path, db_url = db_paths
    conn = _seed_db(db_path)
    _insert(conn, "2026-05-20 14:00:00.000000")
    conn.execute(
        "CREATE TABLE v9_tpo_sessions (id INTEGER PRIMARY KEY, opened_ts TEXT)"
    )
    conn.execute(
        "INSERT INTO v9_tpo_sessions (opened_ts) VALUES ('2026-05-20 13:30:00')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv(WIPE_FLAG_ENV, "1")
    deleted = wipe_today_bars_if_requested(
        database_url=db_url,
        now_et_fn=lambda: _fixed_now_et(2026, 5, 20),
    )
    assert deleted == 1

    conn = sqlite3.connect(str(db_path))
    tpo_count = conn.execute("SELECT COUNT(*) FROM v9_tpo_sessions").fetchone()[0]
    conn.close()
    assert tpo_count == 1, "TPO sessions table must NOT be touched by the wipe"
