"""V9 database session — SQLite (local dev) or PostgreSQL (production).

Decision D-069: Local dev uses SQLite, production uses DATABASE_URL.
"""

import json
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/mems26_local.db"
)

# Handle Render's postgres:// vs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


# P31 §10 — make SQLAlchemy JSON columns tolerate datetime / Decimal / etc.
# Without this, an `INSERT INTO v9_trades` carrying a datetime in
# `quality.metadata` or `cross_context` raises
# `TypeError: Object of type datetime is not JSON serializable`, which then
# surfaces as PendingRollbackError storms (observed as Woodies process_bar
# 18s SLOW: each TLB/ZLR/VEGAS fire tried to persist a trade with datetime
# in nested metadata and failed → retry storm).
#
# `default=str` mirrors what `gateway._persist_trade` already did via raw
# sqlite3 (`json.dumps(..., default=str)`) — consistent behaviour across both
# paths. Round-trip: datetime → ISO-ish string ("2026-05-21 12:34:56+00:00")
# is read back as a string (acceptable for advisory metadata; structured
# DATETIME columns are not affected).
def _json_default(o):
    return str(o)


def _json_serializer(obj):
    return json.dumps(obj, default=_json_default)


# Auto-create data/ dir for SQLite
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        json_serializer=_json_serializer,
    )
    # Enable WAL mode for better concurrent read/write on SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        json_serializer=_json_serializer,
    )

# Station-4 fix (2026-07-23): read-only engine with AUTOCOMMIT isolation.
# The main engine starts implicit transactions on every execute() — if a read
# path holds a connection (exception, reference leak), it stays as
# "idle in transaction" and blocks DDL (migration 023 wedge, 95 min).
# read.py uses this engine so SELECTs never open a transaction.
_read_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=3,
    isolation_level="AUTOCOMMIT",
    json_serializer=_json_serializer,
) if not DATABASE_URL.startswith("sqlite") else engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session.

    SQLite WAL mode + busy_timeout=5000 (set via engine pragma) handle
    concurrent writes safely. The _LockedSession approach caused deadlocks
    in uvicorn's single-threaded event loop (one commit() blocked all requests).

    Write serialization for raw sqlite3 callers goes through safe_writer._write_lock.
    ORM writes rely on WAL's built-in serialization (single WAL writer at a time,
    busy_timeout waits rather than corrupts). The original corruption was caused by
    mixing WAL and non-WAL connections — now all connections use WAL.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called by db_init.sh, tests, and boot (main.py:_startup)."""
    from backend.v9.db import models  # noqa: F401 — registers all models
    # V9DayTypeState lives OUTSIDE the db/models package (systems/day_type/models.py),
    # so the line above never registers it → create_all skipped v9_day_type_state →
    # "relation does not exist" spam + FiveMin hydrate failure on a fresh DB (iMac 07-13).
    # Same Base (session.Base) → importing it here puts it on the shared metadata.
    from backend.v9.systems.day_type.models import V9DayTypeState  # noqa: F401
    Base.metadata.create_all(bind=engine)
