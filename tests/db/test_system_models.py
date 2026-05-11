"""Tests for all 6 system DB tables — created via init_db."""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/mems26_test.db")

import pytest
from sqlalchemy import inspect

from backend.v9.db.session import engine, init_db, Base
from backend.v9.db.models import (
    V9DayTypeHistory, V9FiveMinSetup, V9FootprintMarker,
    V9WoodiesPattern, V9TpoHistory, V9KillzoneLog,
)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    yield


class TestTablesExist:
    def test_day_type_history(self):
        insp = inspect(engine)
        assert "v9_day_type_history" in insp.get_table_names()

    def test_five_min_setups(self):
        insp = inspect(engine)
        assert "v9_five_min_setups" in insp.get_table_names()

    def test_footprint_markers(self):
        insp = inspect(engine)
        assert "v9_footprint_markers" in insp.get_table_names()

    def test_woodies_patterns(self):
        insp = inspect(engine)
        assert "v9_woodies_patterns" in insp.get_table_names()

    def test_tpo_history(self):
        insp = inspect(engine)
        assert "v9_tpo_history" in insp.get_table_names()

    def test_killzone_log(self):
        insp = inspect(engine)
        assert "v9_killzone_log" in insp.get_table_names()

    def test_total_v9_tables_at_least_19(self):
        insp = inspect(engine)
        v9_tables = [t for t in insp.get_table_names() if t.startswith("v9_")]
        assert len(v9_tables) >= 19
