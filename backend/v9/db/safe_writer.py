"""Centralized DB write layer — engine-based, works on SQLite and Postgres.

Postgres migration (2026-06-03): replaced raw sqlite3.connect with
SQLAlchemy engine.connect(). On Postgres, MVCC handles concurrency
natively — no lock needed. On SQLite, the _write_lock is kept for safety.

All callers use positional `?` placeholders — this module converts them
to `:p0, :p1, ...` named params for SQLAlchemy text().
"""

import contextlib
import logging
import os
import threading
from collections.abc import Mapping
from typing import Any, List, Optional, Sequence, Tuple, Union

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Legacy — only used when explicitly passing db_path (SQLite fallback)
DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

_write_lock = threading.RLock()


def _get_engine(db_path: str = None):
    """Return the app engine. Ignores db_path when running on Postgres.

    Split-brain fix (2026-06-04): when DATABASE_URL is Postgres, db_path
    is ignored with a warning — prevents silent writes to a stale SQLite
    file while reads go to PG. SQLite fallback only for tests that
    explicitly set DATABASE_URL to sqlite.
    """
    from backend.v9.db.session import engine
    if db_path is None:
        return engine
    # On Postgres: ignore db_path (would create a rogue SQLite engine)
    if _is_postgres(engine):
        logger.warning(
            "[safe_writer] db_path=%s ignored — using Postgres engine (split-brain guard)",
            db_path,
        )
        return engine
    # On SQLite: allow explicit db_path (tests use temp DBs)
    from sqlalchemy import create_engine
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def _is_postgres(engine) -> bool:
    return "postgresql" in str(engine.url)


def _convert_positional_to_named(sql: str, params: Sequence) -> tuple:
    """Convert `?` positional placeholders to `:p0, :p1, ...` named params.

    Returns (new_sql, params_dict).
    """
    if not params:
        return sql, {}
    parts = sql.split("?")
    if len(parts) - 1 != len(params):
        # Mismatch — return as-is and let the engine handle it
        return sql, dict(enumerate(params))
    new_parts = []
    params_dict = {}
    for i, part in enumerate(parts[:-1]):
        new_parts.append(part)
        new_parts.append(f":p{i}")
        params_dict[f"p{i}"] = params[i]
    new_parts.append(parts[-1])
    return "".join(new_parts), params_dict


def _sqlite_to_pg_upsert(sql: str) -> str:
    """Convert INSERT OR REPLACE/IGNORE to Postgres ON CONFLICT syntax.

    Simple heuristic: finds the table's UNIQUE/PK column from the SQL pattern.
    """
    sql_upper = sql.upper().strip()

    if "INSERT OR IGNORE" in sql_upper:
        return sql.replace("INSERT OR IGNORE", "INSERT", 1) + " ON CONFLICT DO NOTHING"

    if "INSERT OR REPLACE" in sql_upper:
        # Extract table name and columns for ON CONFLICT DO UPDATE
        import re
        # Match: INSERT OR REPLACE INTO table_name (col1, col2, ...) VALUES (...)
        m = re.match(
            r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
            sql.strip(),
            re.IGNORECASE,
        )
        if m:
            table = m.group(1)
            cols_str = m.group(2)
            vals_str = m.group(3)
            cols = [c.strip() for c in cols_str.split(",")]

            # Determine conflict column: bar_id (UNIQUE) or ts+symbol or ts
            if "bar_id" in cols:
                conflict_col = "bar_id"
            elif "symbol" in cols and "ts" in cols:
                conflict_col = "ts, symbol"
            elif "session_id" in cols:
                conflict_col = "session_id"
            elif "key" in cols:
                conflict_col = "key"
            elif "bar_ts" in cols:
                conflict_col = "bar_ts"
            else:
                conflict_col = "ts"

            # Build SET clause (update all non-conflict columns)
            conflict_cols_set = {c.strip() for c in conflict_col.split(",")}
            update_cols = [c for c in cols if c not in conflict_cols_set and c != "id"]
            if update_cols:
                set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
                return (
                    f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str}) "
                    f"ON CONFLICT ({conflict_col}) DO UPDATE SET {set_clause}"
                )
            else:
                return (
                    f"INSERT INTO {table} ({cols_str}) VALUES ({vals_str}) "
                    f"ON CONFLICT ({conflict_col}) DO NOTHING"
                )

        # Fallback: simple replacement (may fail on PG if no conflict clause)
        return sql.replace("INSERT OR REPLACE", "INSERT", 1)

    return sql


def safe_execute(
    sql: str,
    params: Union[Tuple, Sequence] = (),
    db_path: str = None,
) -> Optional[int]:
    """Execute a single INSERT/UPDATE/DELETE.

    Returns lastrowid on success, None on failure (logged, not raised).
    Converts ? placeholders and INSERT OR REPLACE for Postgres compatibility.

    `params` is POSITIONAL (`?` placeholders). Passing a dict for `:named`
    binds is NOT supported and now raises instead of silently writing nothing.

    T-182 (30.08): `t160_pnl_trust_audit.py --apply` passed a dict. It reached
    `_convert_positional_to_named`, whose mismatch branch does
    `dict(enumerate(params))` — and `enumerate()` over a dict walks its KEYS,
    producing `{0: 'q', 1: 'id'}`. The engine then raised "A value is required
    for bind parameter 'q'", the except below swallowed it, and the script
    reported "Marked 62 trades" while ZERO rows were written: it counted
    intention instead of result. (The 62 rows were later marked BY HAND in
    psql — so the DB looks marked today even though the script never wrote a
    single row. Don't read the marked rows as evidence the script worked.)

    Failing loud here is safe. AST sweep of every call site in the repo
    (31.08): 40 sites — 39 production (backend/bridge), all positional
    tuples/lists; 1 script (t160_pnl_trust_audit.py) which was the sole
    dict-passer and is fixed to positional `?` in the same commit. No
    production caller is affected. That sweep is kept honest by
    tests/v9/regression/test_safe_execute_dict_guard.py, which re-runs it on
    every test run and fails if a new dict-passing caller appears.

    STILL OPEN (T-182 part 3): 23 production call sites DISCARD the return
    value. Note the naive remedy is wrong — this returns `result.lastrowid`,
    which psycopg2 leaves None for a successful UPDATE/DELETE, so `is not
    None` is NOT a success test on Postgres. A real fix returns rowcount.
    """
    if isinstance(params, Mapping):
        raise TypeError(
            "safe_execute() takes POSITIONAL params for `?` placeholders; got a "
            f"{type(params).__name__}. A dict is silently mangled into "
            "{0: <key>, 1: <key>} and writes nothing (T-182). Use a tuple with "
            "`?`, or go through the ORM / read.py for :named binds."
        )
    engine = _get_engine(db_path)
    is_pg = _is_postgres(engine)

    # Convert SQL for Postgres
    exec_sql = _sqlite_to_pg_upsert(sql) if is_pg else sql
    exec_sql, params_dict = _convert_positional_to_named(exec_sql, params)

    lock = contextlib.nullcontext() if is_pg else _write_lock
    with lock:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(exec_sql), params_dict)
                conn.commit()
                return result.lastrowid if hasattr(result, 'lastrowid') else 0
        except Exception as e:
            logger.warning("[safe_writer] execute failed: %s — sql: %.120s", e, exec_sql)
            return None


def safe_executemany(
    sql: str,
    params_list: List[Union[Tuple, Sequence]],
    db_path: str = None,
) -> int:
    """Execute a batch INSERT.

    Returns number of rows affected. Logs and returns 0 on failure.
    """
    if not params_list:
        return 0

    engine = _get_engine(db_path)
    is_pg = _is_postgres(engine)

    exec_sql = _sqlite_to_pg_upsert(sql) if is_pg else sql

    # Convert each param tuple to a named dict
    sample = params_list[0]
    # Count ? placeholders
    placeholder_count = sql.count("?")
    param_names = [f"p{i}" for i in range(placeholder_count)]

    # Build named SQL
    parts = exec_sql.split("?")
    if len(parts) - 1 == placeholder_count:
        new_parts = []
        for i, part in enumerate(parts[:-1]):
            new_parts.append(part)
            new_parts.append(f":p{i}")
        new_parts.append(parts[-1])
        exec_sql = "".join(new_parts)

    dict_list = [dict(zip(param_names, row)) for row in params_list]

    lock = contextlib.nullcontext() if is_pg else _write_lock
    with lock:
        try:
            with engine.connect() as conn:
                for params_dict in dict_list:
                    conn.execute(text(exec_sql), params_dict)
                conn.commit()
                return len(dict_list)
        except Exception as e:
            logger.warning("[safe_writer] executemany failed: %s — sql: %.120s", e, exec_sql)
            return 0


def safe_checkpoint(db_path: str = None) -> None:
    """WAL checkpoint — only relevant for SQLite. No-op on Postgres."""
    engine = _get_engine(db_path)
    if _is_postgres(engine):
        return  # Postgres has no WAL checkpoint concept
    with _write_lock:
        try:
            with engine.connect() as conn:
                conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
                conn.commit()
                logger.info("[safe_writer] WAL checkpoint complete")
        except Exception as e:
            logger.warning("[safe_writer] checkpoint failed: %s", e)
