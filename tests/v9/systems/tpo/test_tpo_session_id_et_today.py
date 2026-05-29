"""Test that TPOSystem.session_id uses et_today(), not date.today().

P31-E: Ensures the TPO session key is based on the ET calendar date,
so bars arriving after midnight UTC but before midnight ET still key
to the correct trading date.
"""

import ast
import inspect
import textwrap
from unittest.mock import patch, MagicMock
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

_ET = ZoneInfo("America/New_York")


class TestTPOSessionIdUsesEtToday:
    """Verify TPOSystem constructs session_id from et_today()."""

    def test_no_date_today_in_source(self):
        """Source code must not contain date.today() — et_today() only."""
        import backend.v9.systems.tpo.tpo_system as mod
        source = inspect.getsource(mod)
        assert "date.today()" not in source, (
            "tpo_system.py still uses date.today() — must use et_today()"
        )

    def test_et_today_import_present(self):
        """et_today must be imported in tpo_system module."""
        import backend.v9.systems.tpo.tpo_system as mod
        assert hasattr(mod, "et_today"), "et_today not imported in tpo_system"

    def test_session_id_uses_et_date_at_2300_et(self):
        """At 23:00 ET on May 28, session_id should use 2026-05-28 (not 05-29 UTC)."""
        fake_et_date = date(2026, 5, 28)
        with patch("backend.v9.systems.tpo.tpo_system.et_today", return_value=fake_et_date):
            from backend.v9.systems.tpo.tpo_system import TPOSystem
            tpo = TPOSystem(db_path=":memory:")

            # Simulate a bar event that triggers session_id construction
            mock_event = {
                "ts": "2026-05-29T03:00:00Z",  # 23:00 ET = 03:00 UTC next day
                "open": 7500.0, "high": 7510.0, "low": 7490.0, "close": 7505.0,
                "volume": 100, "session": "GLOBEX",
            }

            # Patch DB and market clock to avoid real IO
            with patch("backend.v9.systems.tpo.tpo_system.sqlite3") as mock_sql, \
                 patch("backend.v9.systems.tpo.tpo_system._market_now_utc",
                       return_value=datetime(2026, 5, 29, 3, 0, tzinfo=ZoneInfo("UTC"))):
                mock_conn = MagicMock()
                mock_sql.connect.return_value = mock_conn

                import asyncio
                asyncio.get_event_loop().run_until_complete(tpo.process_bar(mock_event))

                # session_id should be keyed on the ET date, not UTC date
                assert tpo.current_session_id is not None
                assert "2026-05-28" in tpo.current_session_id, (
                    f"Expected ET date 2026-05-28 in session_id, got: {tpo.current_session_id}"
                )

    def test_session_id_format(self):
        """session_id follows the pattern {SESSION_TYPE}_{YYYY-MM-DD}."""
        fake_et_date = date(2026, 6, 2)
        with patch("backend.v9.systems.tpo.tpo_system.et_today", return_value=fake_et_date):
            from backend.v9.systems.tpo.tpo_system import TPOSystem
            tpo = TPOSystem(db_path=":memory:")

            mock_event = {
                "ts": "2026-06-02T14:00:00Z",
                "open": 7600.0, "high": 7610.0, "low": 7590.0, "close": 7605.0,
                "volume": 200, "session": "CASH_OPEN",
            }

            with patch("backend.v9.systems.tpo.tpo_system.sqlite3") as mock_sql, \
                 patch("backend.v9.systems.tpo.tpo_system._market_now_utc",
                       return_value=datetime(2026, 6, 2, 14, 0, tzinfo=ZoneInfo("UTC"))):
                mock_conn = MagicMock()
                mock_sql.connect.return_value = mock_conn

                import asyncio
                asyncio.get_event_loop().run_until_complete(tpo.process_bar(mock_event))

                # Dict events don't have .session attr → defaults to GLOBEX
                assert tpo.current_session_id == "GLOBEX_2026-06-02"
