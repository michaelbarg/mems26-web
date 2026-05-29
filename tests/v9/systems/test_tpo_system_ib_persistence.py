"""Regression: TPOSystem IB persistence must mirror Sierra 1:1 and never
wipe a previously-locked IB when Sierra goes silent (the "doesn't lock the
way it locked" requirement, Michael 2026-05-28 17:47 IDT).
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.v9.systems.tpo.tpo_system import TPOSystem


def _setup_db(tmp_path: Path) -> Path:
    """Minimal v9_tpo_sessions schema (mirrors prod columns we touch)."""
    db = tmp_path / "tpo_test.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """CREATE TABLE v9_tpo_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id   TEXT NOT NULL UNIQUE,
              session_type TEXT NOT NULL,
              trading_date TEXT NOT NULL,
              opened_ts    DATETIME NOT NULL,
              closed_ts    DATETIME,
              poc_price    REAL,
              vah_price    REAL,
              val_price    REAL,
              profile_shape TEXT,
              ib_high      REAL,
              ib_low       REAL,
              ib_locked    INTEGER DEFAULT 0,
              ib_width     REAL,
              ib_class     TEXT,
              ib_locked_ts TEXT,
              letter_count INTEGER DEFAULT 0
           )"""
    )
    conn.commit()
    conn.close()
    return db


def _row(db: Path, session_id: str) -> dict | None:
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    r = conn.execute(
        "SELECT ib_high, ib_low, ib_locked, ib_locked_ts, ib_width, ib_class "
        "FROM v9_tpo_sessions WHERE session_id=?",
        (session_id,),
    ).fetchone()
    conn.close()
    return dict(r) if r else None


def _make_system(db: Path) -> TPOSystem:
    sys = TPOSystem(db_path=str(db))
    today = date.today().isoformat()
    sys._open_session(f"CASH_{today}", "CASH", today, f"{today} 09:30:00")
    return sys


def test_persist_session_does_not_wipe_locked_ib_when_sierra_silent(tmp_path):
    """Sierra emitted IB earlier → DB row populated. Sierra now silent
    (`self.ib_high=None` after a hypothetical reset path) → `_persist_session`
    MUST NOT overwrite ib_high/ib_low with NULL.
    """
    db = _setup_db(tmp_path)
    sys = _make_system(db)

    # Simulate Sierra emitting locked IB once
    sys.ib_high = 7543.75
    sys.ib_low = 7522.0
    sys.ib_locked = True
    sys._ib_width = 21.75
    sys._ib_class = "MEDIUM"
    sys._ib_locked_ts = "2026-05-28T14:30:00+00:00"
    sys._persist_ib_to_session()
    row = _row(db, sys.current_session_id)
    assert row["ib_high"] == 7543.75
    assert row["ib_low"] == 7522.0
    assert row["ib_locked"] == 1

    # Simulate "Sierra silent" by clearing self.* (e.g. backend restart with
    # missing tpo.json) and triggering _persist_session via a fake bar persist.
    sys.ib_high = None
    sys.ib_low = None
    sys.ib_locked = False
    sys._persist_session(
        sys.current_session_id, "CASH", date.today().isoformat(),
        poc=7551.0, vah=7574.0, val=7541.0, shape="D",
    )

    row2 = _row(db, sys.current_session_id)
    assert row2["ib_high"] == 7543.75, "Sierra-locked IB high was wiped"
    assert row2["ib_low"] == 7522.0, "Sierra-locked IB low was wiped"
    assert row2["ib_locked"] == 1, "ib_locked flag was reset"


def test_persist_session_does_track_new_sierra_ib(tmp_path):
    """When Sierra emits a NEW IB mid-session (e.g. study re-configured),
    `_update_ib` overwrites DB unconditionally via `_persist_ib_to_session`.
    `_persist_session` (called from `process_bar`) must keep tracking.
    """
    db = _setup_db(tmp_path)
    sys = _make_system(db)

    sys.ib_high, sys.ib_low, sys.ib_locked = 7543.75, 7522.0, True
    sys._persist_ib_to_session()
    assert _row(db, sys.current_session_id)["ib_high"] == 7543.75

    # Sierra changes IB (e.g. Michael re-configured the study)
    sys.ib_high, sys.ib_low, sys.ib_locked = 7555.0, 7530.0, True
    sys._ib_width, sys._ib_class = 25.0, "MEDIUM"
    sys._persist_ib_to_session()
    row = _row(db, sys.current_session_id)
    assert row["ib_high"] == 7555.0
    assert row["ib_low"] == 7530.0


def test_open_session_same_trading_date_keeps_locked_ib(tmp_path):
    """A re-open within the same trading_date (CASH→GLOBEX transition, or
    bridge resubscribe) must NOT wipe a Sierra-emitted locked IB.
    """
    db = _setup_db(tmp_path)
    sys = _make_system(db)
    today = date.today().isoformat()

    sys.ib_high, sys.ib_low, sys.ib_locked = 7543.75, 7522.0, True
    sys._ib_locked_ts = "2026-05-28T14:30:00+00:00"

    # Same trading_date, different session_type — should NOT reset
    sys._open_session(f"GLOBEX_{today}", "GLOBEX", today, f"{today} 18:00:00")
    assert sys.ib_high == 7543.75
    assert sys.ib_low == 7522.0
    assert sys.ib_locked is True


def test_open_session_new_trading_date_resets_ib(tmp_path):
    """A new trading_date (next day) MUST reset IB."""
    db = _setup_db(tmp_path)
    sys = _make_system(db)

    sys.ib_high, sys.ib_low, sys.ib_locked = 7543.75, 7522.0, True

    sys._open_session("CASH_2026-05-29", "CASH", "2026-05-29", "2026-05-29 09:30:00")
    assert sys.ib_high is None
    assert sys.ib_low is None
    assert sys.ib_locked is False
