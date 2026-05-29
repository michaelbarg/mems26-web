"""Test SessionBoundaryManager rollover idempotency.

P31-B: Calling check_rollover() twice on the same day must be a no-op.
The second call returns False and does not re-reset systems.
"""

import sqlite3
import tempfile
from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from backend.v9.services.session_boundary.manager import SessionBoundaryManager


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return f.name


class TestRolloverIdempotency:

    def test_first_call_performs_rollover(self, tmp_db):
        """First check_rollover() on a fresh DB should perform rollover."""
        machine = MagicMock()
        sbm = SessionBoundaryManager(db_path=tmp_db, day_type_machine=machine)

        with patch("backend.v9.services.session_boundary.manager.et_today",
                   return_value=date(2026, 5, 28)):
            result = sbm.check_rollover()

        assert result is True
        machine.reset.assert_called_once()

    def test_second_call_is_noop(self, tmp_db):
        """Second check_rollover() on the same day must be a no-op."""
        machine = MagicMock()
        sbm = SessionBoundaryManager(db_path=tmp_db, day_type_machine=machine)
        fake_date = date(2026, 5, 28)

        with patch("backend.v9.services.session_boundary.manager.et_today",
                   return_value=fake_date):
            first = sbm.check_rollover()
            second = sbm.check_rollover()

        assert first is True
        assert second is False
        # reset called exactly once, not twice
        machine.reset.assert_called_once()

    def test_new_day_triggers_rollover_again(self, tmp_db):
        """Next day should trigger a new rollover."""
        machine = MagicMock()
        sbm = SessionBoundaryManager(db_path=tmp_db, day_type_machine=machine)

        with patch("backend.v9.services.session_boundary.manager.et_today",
                   return_value=date(2026, 5, 28)):
            sbm.check_rollover()

        with patch("backend.v9.services.session_boundary.manager.et_today",
                   return_value=date(2026, 5, 29)):
            result = sbm.check_rollover()

        assert result is True
        assert machine.reset.call_count == 2

    def test_persists_last_rollover_date(self, tmp_db):
        """last_rollover_date is persisted to v9_session_meta."""
        sbm = SessionBoundaryManager(db_path=tmp_db)

        with patch("backend.v9.services.session_boundary.manager.et_today",
                   return_value=date(2026, 5, 28)):
            sbm.check_rollover()

        conn = sqlite3.connect(tmp_db)
        row = conn.execute(
            "SELECT value FROM v9_session_meta WHERE key='last_rollover_date'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "2026-05-28"

    def test_rollover_without_machine_succeeds(self, tmp_db):
        """Rollover works even without a day_type_machine (graceful degradation)."""
        sbm = SessionBoundaryManager(db_path=tmp_db)

        with patch("backend.v9.services.session_boundary.manager.et_today",
                   return_value=date(2026, 5, 28)):
            result = sbm.check_rollover()

        assert result is True

    def test_risk_validator_reset_called(self, tmp_db):
        """RiskValidator.daily_reset() is called during rollover."""
        machine = MagicMock()
        risk = MagicMock()
        sbm = SessionBoundaryManager(
            db_path=tmp_db, day_type_machine=machine, risk_validator=risk
        )

        with patch("backend.v9.services.session_boundary.manager.et_today",
                   return_value=date(2026, 5, 28)):
            sbm.check_rollover()

        risk.daily_reset.assert_called_once()
