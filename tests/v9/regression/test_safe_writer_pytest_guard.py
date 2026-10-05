# -*- coding: utf-8 -*-
"""T-542 (05.10): pytest must never write into the LIVE Postgres.

On 05.10 a regression run wrote 14 fake DECISION rows into the production
v9_decision_vectors (the suite imports the real gateway, whose decision
logger calls safe_execute against DATABASE_URL from .env). The 2026-08-19
fix for the same class guarded only the DECISIONS JSONL. The guard now sits
in safe_writer, on the one path every production write takes.
"""
import os

import pytest

from backend.v9.db import safe_writer as sw


class _NeverConnect:
    """Engine stand-in: records any attempt to connect (safe_execute swallows
    exceptions, so the attempt itself is the evidence)."""

    connected = False

    def connect(self):
        _NeverConnect.connected = True
        raise RuntimeError("safe_writer connected to Postgres under pytest (T-542)")


@pytest.fixture
def pg_engine(monkeypatch):
    monkeypatch.setattr(sw, "_get_engine", lambda db_path=None: _NeverConnect())
    monkeypatch.setattr(sw, "_is_postgres", lambda engine: True)
    monkeypatch.delenv("MEMS26_ALLOW_TEST_DB_WRITES", raising=False)
    _NeverConnect.connected = False
    assert os.environ.get("PYTEST_CURRENT_TEST"), "pytest sets this for every test"


def test_safe_execute_refuses_postgres_under_pytest(pg_engine):
    assert sw.safe_execute("INSERT INTO v9_decision_vectors (kind) VALUES (?)", ("DECISION",)) is None
    assert _NeverConnect.connected is False


def test_safe_executemany_refuses_postgres_under_pytest(pg_engine):
    assert sw.safe_executemany("INSERT INTO t (a) VALUES (?)", [(1,), (2,)]) in (None, 0)
    assert _NeverConnect.connected is False


def test_opt_in_env_lets_the_write_through(pg_engine, monkeypatch):
    monkeypatch.setenv("MEMS26_ALLOW_TEST_DB_WRITES", "1")
    sw.safe_execute("INSERT INTO t (a) VALUES (?)", (1,))  # failure is swallowed by design
    assert _NeverConnect.connected is True


def test_sqlite_engines_are_not_refused(monkeypatch):
    # A test that brings its own tmp SQLite DB (e.g. test_t284) must keep working.
    monkeypatch.setattr(sw, "_is_postgres", lambda engine: False)
    assert sw._refuse_under_pytest(False) is False
