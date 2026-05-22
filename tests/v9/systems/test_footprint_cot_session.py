"""P31: COT resets at session open — regression test.

Given: journal entry from 2026-05-21 14:00 UTC (10:00 ET)
       hydrate called   at 2026-05-22 09:00 UTC (05:00 ET)
       session_open     = 2026-05-21 22:00 UTC (18:00 ET May 21)

Expected: _cumulative_delta == 0.0 (previous session data discarded)
"""

import sqlite3
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest


@pytest.fixture
def fp_db(tmp_path):
    """Create a temp DB with footprint journal table and one old-session row."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE v9_footprint_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cumulative_delta REAL,
            created_at TEXT
        )
    """)
    # Insert a journal entry from 2026-05-21 14:00 UTC (10:00 ET) — previous session
    conn.execute(
        "INSERT INTO v9_footprint_journal (cumulative_delta, created_at) VALUES (?, ?)",
        (-144527.0, "2026-05-21T14:00:00+00:00"),
    )
    conn.commit()
    conn.close()
    return db_path


def _make_footprint_system(db_path):
    from backend.v9.systems.footprint.footprint_system import FootprintSystem
    return FootprintSystem(db_path=db_path)


def test_cot_resets_at_session_open(fp_db):
    """COT must reset to 0 when last journal entry is from a previous session."""
    # "now" = 2026-05-22 09:00 UTC = 05:00 ET
    # session_open = 2026-05-21 22:00 UTC = 18:00 ET May 21
    # journal entry = 2026-05-21 14:00 UTC < session_open → discard
    fake_now_utc = datetime(2026, 5, 22, 9, 0, tzinfo=timezone.utc)

    from backend.v9.common.session_classifier import SessionClassifier
    sc = SessionClassifier()
    session_open = sc.current_session_open_utc(now=fake_now_utc)

    # Verify session_open is 2026-05-21 22:00 UTC
    assert session_open.year == 2026
    assert session_open.month == 5
    assert session_open.day == 21
    assert session_open.hour == 22
    assert session_open.minute == 0

    # Patch current_session_open_utc to use our fake "now"
    with patch.object(
        SessionClassifier,
        "current_session_open_utc",
        return_value=session_open,
    ):
        fp = _make_footprint_system(fp_db)
        result = fp.hydrate()

    assert result.success is True
    assert fp._cumulative_delta == 0.0, (
        f"COT should reset to 0 at session boundary, got {fp._cumulative_delta}"
    )
    assert fp.current_state["cot"] == 0
    assert fp.current_state["cumulative_delta"] == 0


def test_cot_restores_within_session(fp_db):
    """COT must restore when last journal entry is from the current session."""
    # Insert a same-session entry: 2026-05-22 01:00 UTC = 21:00 ET May 21
    # session_open = 2026-05-21 22:00 UTC → entry is AFTER open → restore
    conn = sqlite3.connect(fp_db)
    conn.execute(
        "INSERT INTO v9_footprint_journal (cumulative_delta, created_at) VALUES (?, ?)",
        (500.0, "2026-05-22T01:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    fake_now_utc = datetime(2026, 5, 22, 9, 0, tzinfo=timezone.utc)

    from backend.v9.common.session_classifier import SessionClassifier
    sc = SessionClassifier()
    session_open = sc.current_session_open_utc(now=fake_now_utc)

    with patch.object(
        SessionClassifier,
        "current_session_open_utc",
        return_value=session_open,
    ):
        fp = _make_footprint_system(fp_db)
        result = fp.hydrate()

    assert result.success is True
    assert fp._cumulative_delta == 500.0, (
        f"COT should restore within session, got {fp._cumulative_delta}"
    )
    assert fp.current_state["cot"] == 500.0


def test_session_open_utc_before_1800():
    """Before 18:00 ET, session_open is yesterday 18:00 ET."""
    from backend.v9.common.session_classifier import SessionClassifier
    sc = SessionClassifier()

    # 2026-05-22 15:00 UTC = 11:00 ET → before 18:00 ET → yesterday's open
    now = datetime(2026, 5, 22, 15, 0, tzinfo=timezone.utc)
    result = sc.current_session_open_utc(now=now)

    assert result.day == 21  # yesterday
    assert result.hour == 22  # 18:00 ET = 22:00 UTC


def test_session_open_utc_after_1800():
    """After 18:00 ET, session_open is today 18:00 ET."""
    from backend.v9.common.session_classifier import SessionClassifier
    sc = SessionClassifier()

    # 2026-05-22 23:00 UTC = 19:00 ET → after 18:00 ET → today's open
    now = datetime(2026, 5, 22, 23, 0, tzinfo=timezone.utc)
    result = sc.current_session_open_utc(now=now)

    assert result.day == 22  # today
    assert result.hour == 22  # 18:00 ET = 22:00 UTC
