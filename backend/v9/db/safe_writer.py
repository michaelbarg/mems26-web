"""Centralized DB write serializer — prevents SQLite corruption.

All writes to mems26_local.db MUST go through `safe_execute` or `safe_executemany`.
A single threading.Lock ensures no concurrent writes. Every connection uses WAL +
busy_timeout and is opened/closed per operation (no persistent connections).

Root cause (2026-06-02): 70% of writers opened raw sqlite3.connect() without WAL
or busy_timeout. Concurrent writes from footprint (WAL) and woodies (rollback
journal) corrupted the B-tree within minutes.
"""

import logging
import sqlite3
import threading
from typing import Any, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger(__name__)

DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"

_write_lock = threading.RLock()  # RLock: safe if ORM handler calls safe_execute


def _open_conn(db_path: str) -> sqlite3.Connection:
    """Open a short-lived WAL connection with busy_timeout."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def safe_execute(
    sql: str,
    params: Union[Tuple, Sequence] = (),
    db_path: str = DB_PATH,
) -> Optional[int]:
    """Execute a single INSERT/UPDATE/DELETE with serialized write lock.

    Returns lastrowid on success, None on failure (logged, not raised).
    """
    with _write_lock:
        try:
            conn = _open_conn(db_path)
            cursor = conn.execute(sql, params)
            conn.commit()
            lastrowid = cursor.lastrowid
            conn.close()
            return lastrowid
        except Exception as e:
            logger.warning("[safe_writer] execute failed: %s — sql: %.80s", e, sql)
            try:
                conn.close()
            except Exception:
                pass
            return None


def safe_executemany(
    sql: str,
    params_list: List[Union[Tuple, Sequence]],
    db_path: str = DB_PATH,
) -> int:
    """Execute a batch INSERT with serialized write lock.

    Returns number of rows affected. Logs and returns 0 on failure.
    """
    with _write_lock:
        try:
            conn = _open_conn(db_path)
            cursor = conn.executemany(sql, params_list)
            conn.commit()
            n = cursor.rowcount
            conn.close()
            return n
        except Exception as e:
            logger.warning("[safe_writer] executemany failed: %s — sql: %.80s", e, sql)
            try:
                conn.close()
            except Exception:
                pass
            return 0


def safe_checkpoint(db_path: str = DB_PATH) -> None:
    """WAL checkpoint + truncate for graceful shutdown."""
    with _write_lock:
        try:
            conn = _open_conn(db_path)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
            logger.info("[safe_writer] WAL checkpoint complete")
        except Exception as e:
            logger.warning("[safe_writer] checkpoint failed: %s", e)
