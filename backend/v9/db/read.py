"""Cross-database read helper — works on both SQLite and Postgres.

Postgres migration (2026-06-03): replaces all raw sqlite3.connect(mode=ro)
calls with engine-based reads that work on any SQLAlchemy-supported backend.

Station-4 fix (2026-07-23): uses _read_engine (AUTOCOMMIT isolation) so
SELECTs never open a transaction. Prevents "idle in transaction" leak that
blocked DDL for 95 min (migration 023 wedge).
"""

import logging
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import text

from backend.v9.db.session import _read_engine as engine

logger = logging.getLogger(__name__)


def read_all(
    sql: str,
    params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute a SELECT and return all rows as list of dicts.

    SQL must use :named params (not ? positional).
    Returns [] on any error (logged, not raised).
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            columns = list(result.keys())
            return [dict(zip(columns, row)) for row in result.fetchall()]
    except Exception as e:
        logger.warning("[db.read] read_all failed: %s — sql: %.120s", e, sql)
        return []


def read_one(
    sql: str,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Execute a SELECT and return first row as dict, or None."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            columns = list(result.keys())
            row = result.fetchone()
            if row is None:
                return None
            return dict(zip(columns, row))
    except Exception as e:
        logger.warning("[db.read] read_one failed: %s — sql: %.120s", e, sql)
        return None


def read_scalar(
    sql: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """Execute a SELECT and return single scalar value, or None."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.warning("[db.read] read_scalar failed: %s — sql: %.120s", e, sql)
        return None
