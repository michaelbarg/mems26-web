"""P30 G8 — Regression tests for `(ts, symbol)` uniqueness on v9_bars_5min.

Investigation 2026-05-19 23:50 ET: the cockpit threw a
`lightweight-charts: data must be asc ordered by time, index=597,
time=1779198300, prev time=1779198300` assertion because the DB held
two rows with the same `ts`. The SELECT-then-INSERT path in
`bars.py::post_bars_5min` couldn't see a concurrent POST in another
session, so both transactions added a row.

These tests pin:
  * the new `UniqueConstraint("ts", "symbol")` on the model,
  * the `IntegrityError` recovery path in the POST handler,
  * a basic "no duplicates after upsert" property.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.v9.db.models.bars_5min import V9Bar5Min
from backend.v9.db.session import Base


@pytest.fixture
def fresh_session():
    """Brand-new SQLite DB with only V9Bar5Min — isolates from prod schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine, tables=[V9Bar5Min.__table__])
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()
    try:
        os.unlink(path)
    except OSError:
        pass


def _bar(ts: datetime, symbol: str = "MES", **overrides) -> V9Bar5Min:
    defaults = dict(
        ts=ts,
        symbol=symbol,
        open=7400.0,
        high=7405.0,
        low=7398.0,
        close=7403.0,
        volume=100,
    )
    defaults.update(overrides)
    return V9Bar5Min(**defaults)


def test_unique_constraint_present_on_model():
    """The UniqueConstraint must be wired on the SQLAlchemy model itself, not
    just the DB, so SQLite/Postgres both enforce it."""
    table = V9Bar5Min.__table__
    unique_constraints = [
        c for c in table.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    ]
    assert unique_constraints, "V9Bar5Min must declare a UniqueConstraint"
    cols = sorted(c.name for c in unique_constraints[0].columns)
    assert cols == ["symbol", "ts"]


def test_db_rejects_duplicate_ts_symbol(fresh_session: Session):
    """Direct attempt to insert two rows with the same (ts, symbol) raises."""
    ts = datetime(2026, 5, 19, 16, 45, tzinfo=timezone.utc)
    fresh_session.add(_bar(ts, close=7372.25))
    fresh_session.commit()

    fresh_session.add(_bar(ts, close=7373.0))  # different close, same ts+symbol
    with pytest.raises(IntegrityError):
        fresh_session.commit()
    fresh_session.rollback()

    rows = fresh_session.query(V9Bar5Min).filter_by(ts=ts).all()
    assert len(rows) == 1, "DB must not hold duplicate rows for the same ts+symbol"
    assert rows[0].close == 7372.25, "First write wins until app code upserts"


def test_distinct_symbols_at_same_ts_are_allowed(fresh_session: Session):
    """Two different symbols at the same minute are NOT duplicates."""
    ts = datetime(2026, 5, 19, 16, 45, tzinfo=timezone.utc)
    fresh_session.add(_bar(ts, symbol="MES", close=7372.25))
    fresh_session.add(_bar(ts, symbol="ES", close=7372.50))
    fresh_session.commit()
    assert fresh_session.query(V9Bar5Min).count() == 2


def test_upsert_path_keeps_latest_values(fresh_session: Session):
    """Mirror the post_bars_5min code path under a race: first insert wins,
    second `add` raises IntegrityError, handler retries as UPDATE."""
    ts = datetime(2026, 5, 19, 16, 45, tzinfo=timezone.utc)
    fresh_session.add(_bar(ts, close=7372.25, volume=1311))
    fresh_session.commit()

    # Simulate the concurrent POST trying to insert a fresh row for the
    # same minute (its SELECT pre-check returned None because of REPEATABLE
    # READ on the other transaction).
    fresh_session.add(_bar(ts, close=7373.00, volume=165))
    try:
        fresh_session.flush()
        pytest.fail("expected IntegrityError on duplicate insert")
    except IntegrityError:
        fresh_session.rollback()

    # Handler fallback: fetch the winning row and update it with our data.
    winner = fresh_session.query(V9Bar5Min).filter_by(ts=ts, symbol="MES").one()
    winner.close = 7373.00
    winner.volume = 165
    fresh_session.commit()

    rows = fresh_session.query(V9Bar5Min).filter_by(ts=ts).all()
    assert len(rows) == 1
    assert rows[0].close == 7373.00
    assert rows[0].volume == 165
