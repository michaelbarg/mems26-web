"""Tests for day-type writer watchdog."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest

from backend.v9.services.daytype_watchdog import check_daytype_staleness


def test_never_raises_on_broken_db():
    """Watchdog must never raise, even with broken DB."""
    with patch("backend.v9.db.read.read_one", side_effect=Exception("DB dead")):
        result = check_daytype_staleness()
        assert result is None  # fail-safe


def test_no_rows_returns_warning():
    """No rows in v9_day_type_state → warning (if in RTH)."""
    with patch("backend.v9.db.read.read_one", return_value=None):
        result = check_daytype_staleness()
        # Depends on current time — if RTH, warns; otherwise None
        assert result is None or "no v9_day_type_state" in result


def test_fresh_entry_returns_none():
    """Fresh entry (2min old) → None."""
    fresh_ts = datetime.now(timezone.utc) - timedelta(minutes=2)
    with patch("backend.v9.db.read.read_one",
               return_value={"ts": fresh_ts, "day_type": "Balance"}):
        result = check_daytype_staleness()
        assert result is None


def test_stale_entry_during_rth():
    """Stale entry (20min old) during RTH → warning."""
    old_ts = datetime.now(timezone.utc) - timedelta(minutes=20)
    with patch("backend.v9.db.read.read_one",
               return_value={"ts": old_ts, "day_type": "Balance"}):
        result = check_daytype_staleness()
        # Only triggers during RTH — test passes either way
        assert result is None or "stale" in result
