"""Test that /current endpoints reject ROLLED_OVER rows.

P31-H: After rollover, the old day's row gets status='ROLLED_OVER'.
The /current endpoints must not return it — they should treat it as
if no row exists (classified=false).
"""

import sqlite3
import tempfile
from datetime import date
from unittest.mock import patch

import pytest


@pytest.fixture
def day_type_db():
    """Create a temp DB with v9_day_type_history schema and a ROLLED_OVER row."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    conn = sqlite3.connect(f.name)
    conn.execute("""
        CREATE TABLE v9_day_type_history (
            date TEXT PRIMARY KEY,
            day_type TEXT,
            status TEXT,
            probability REAL,
            directional_certainty TEXT,
            trading_confidence TEXT,
            ib_high REAL,
            ib_low REAL,
            ib_width REAL,
            ib_width_class TEXT,
            opening_type TEXT,
            last_updated_at TEXT,
            reasoning_notes TEXT,
            active_zohar_rules TEXT,
            confidence REAL
        )
    """)
    conn.commit()
    conn.close()
    return f.name


class TestCurrentRejectsRolledOver:

    def test_v9_current_skips_rolled_over_row(self, day_type_db):
        """GET /api/v9/day_type/v9/current must not return a ROLLED_OVER row."""
        fake_today = date(2026, 5, 28)

        # Insert a ROLLED_OVER row for today
        conn = sqlite3.connect(day_type_db)
        conn.execute(
            """INSERT INTO v9_day_type_history
               (date, day_type, status, probability, ib_width_class)
               VALUES (?, 'Normal', 'ROLLED_OVER', 0.85, 'MEDIUM')""",
            (fake_today.isoformat(),)
        )
        conn.commit()
        conn.close()

        with patch("backend.v9.api.v9.day_type_v9_routes.et_today", return_value=fake_today), \
             patch("backend.v9.api.v9.day_type_v9_routes.DB_PATH", day_type_db):
            from backend.v9.api.v9.day_type_v9_routes import get_current
            result = get_current()

        assert result["classified"] is False, (
            f"ROLLED_OVER row should not be returned as classified, got: {result}"
        )
        assert result["data"] is None

    def test_v9_current_returns_active_row(self, day_type_db):
        """GET /api/v9/day_type/v9/current returns a non-ROLLED_OVER row normally."""
        fake_today = date(2026, 5, 28)

        conn = sqlite3.connect(day_type_db)
        conn.execute(
            """INSERT INTO v9_day_type_history
               (date, day_type, status, probability, ib_width_class, ib_high, ib_low)
               VALUES (?, 'Normal', 'LOCKED', 0.85, 'MEDIUM', 7550.0, 7520.0)""",
            (fake_today.isoformat(),)
        )
        conn.commit()
        conn.close()

        with patch("backend.v9.api.v9.day_type_v9_routes.et_today", return_value=fake_today), \
             patch("backend.v9.api.v9.day_type_v9_routes.DB_PATH", day_type_db):
            from backend.v9.api.v9.day_type_v9_routes import get_current
            result = get_current()

        assert result["classified"] is True
        assert result["data"]["day_type"] == "Normal"

    def test_key_levels_day_type_row_skips_rolled_over(self, day_type_db):
        """_day_type_row() in key_levels must not return a ROLLED_OVER row."""
        fake_today = date(2026, 5, 28)

        conn = sqlite3.connect(day_type_db)
        conn.execute(
            """INSERT INTO v9_day_type_history
               (date, day_type, status, opening_type)
               VALUES (?, 'Normal', 'ROLLED_OVER', 'OD_UP')""",
            (fake_today.isoformat(),)
        )
        conn.commit()
        conn.close()

        with patch("backend.v9.api.v9.key_levels_routes.et_today", return_value=fake_today), \
             patch("backend.v9.api.v9.key_levels_routes.DB_PATH", day_type_db):
            from backend.v9.api.v9.key_levels_routes import _day_type_row
            result = _day_type_row()

        assert result is None, (
            f"ROLLED_OVER row should not be returned by _day_type_row(), got: {result}"
        )

    def test_v9_current_null_status_still_returned(self, day_type_db):
        """Rows with NULL status (pre-migration) must still be returned."""
        fake_today = date(2026, 5, 28)

        conn = sqlite3.connect(day_type_db)
        conn.execute(
            """INSERT INTO v9_day_type_history
               (date, day_type, status, probability, ib_width_class, ib_high, ib_low)
               VALUES (?, 'Trend_Normal', NULL, 0.72, 'WIDE', 7600.0, 7540.0)""",
            (fake_today.isoformat(),)
        )
        conn.commit()
        conn.close()

        with patch("backend.v9.api.v9.day_type_v9_routes.et_today", return_value=fake_today), \
             patch("backend.v9.api.v9.day_type_v9_routes.DB_PATH", day_type_db):
            from backend.v9.api.v9.day_type_v9_routes import get_current
            result = get_current()

        assert result["classified"] is True, (
            "NULL status row should still be returned (backward compat)"
        )
        assert result["data"]["day_type"] == "Trend_Normal"
