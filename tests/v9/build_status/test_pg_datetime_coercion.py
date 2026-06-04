"""Regression test: PG returns datetime objects for timestamp columns.

Pydantic str-typed fields (last_bar_ts, last_fire_ts, Freshness.ts) must
accept datetime inputs without validation errors.

Root cause: SQLite→PG migration. PG driver returns datetime objects for
timestamp columns, but DataFreshness.last_bar_ts was typed Optional[str].
Fix: field_validator(mode="before") coerces datetime→.isoformat().

if reverted (coercion validators removed) → RED because pydantic rejects
datetime input on str fields with ValidationError.
"""

from datetime import datetime, timezone, timedelta

import pytest

from backend.v9.systems.build_status.types import (
    DataFreshness,
    Freshness,
    PatternStatus,
    SystemStatus,
)


# Simulate what Postgres returns for a timestamp column
_PG_DATETIME = datetime(2026, 6, 4, 14, 30, 0, tzinfo=timezone.utc)
_PG_DATETIME_ET = datetime(2026, 6, 4, 10, 30, 0,
                           tzinfo=timezone(timedelta(hours=-4)))


class TestDataFreshnessCoercion:
    """DataFreshness.last_bar_ts must accept datetime (PG) without error."""

    def test_datetime_input_produces_iso_string(self):
        df = DataFreshness(last_bar_ts=_PG_DATETIME, fresh=True)
        assert isinstance(df.last_bar_ts, str)
        assert df.last_bar_ts == _PG_DATETIME.isoformat()

    def test_datetime_with_offset_tz(self):
        df = DataFreshness(last_bar_ts=_PG_DATETIME_ET, fresh=False)
        assert isinstance(df.last_bar_ts, str)
        assert "2026-06-04" in df.last_bar_ts

    def test_string_input_unchanged(self):
        iso = "2026-06-04T14:30:00+00:00"
        df = DataFreshness(last_bar_ts=iso)
        assert df.last_bar_ts == iso

    def test_none_input_unchanged(self):
        df = DataFreshness(last_bar_ts=None)
        assert df.last_bar_ts is None


class TestPatternStatusCoercion:
    """PatternStatus.last_fire_ts must accept datetime."""

    def test_datetime_input(self):
        ps = PatternStatus(id="test", name="Test", last_fire_ts=_PG_DATETIME)
        assert isinstance(ps.last_fire_ts, str)
        assert ps.last_fire_ts == _PG_DATETIME.isoformat()

    def test_string_passthrough(self):
        iso = "2026-06-04T14:30:00+00:00"
        ps = PatternStatus(id="test", name="Test", last_fire_ts=iso)
        assert ps.last_fire_ts == iso


class TestSystemStatusCoercion:
    """SystemStatus.last_fire_ts must accept datetime."""

    def test_datetime_input(self):
        ss = SystemStatus(id="test", name="Test", last_fire_ts=_PG_DATETIME)
        assert isinstance(ss.last_fire_ts, str)
        assert ss.last_fire_ts == _PG_DATETIME.isoformat()


class TestFreshnessCoercion:
    """Freshness.ts must accept datetime (defense-in-depth)."""

    def test_datetime_input(self):
        f = Freshness(ts=_PG_DATETIME, source="db")
        assert isinstance(f.ts, str)
        assert f.ts == _PG_DATETIME.isoformat()

    def test_string_passthrough(self):
        iso = "2026-06-04T14:30:00+00:00"
        f = Freshness(ts=iso, source="db")
        assert f.ts == iso
