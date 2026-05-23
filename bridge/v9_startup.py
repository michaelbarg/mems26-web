"""Bridge startup hooks — data hygiene to run BEFORE any stream starts pushing.

P30 (2026-05-20): opt-in wipe of today's session bars.

When `V9_BRIDGE_WIPE_TODAY_ON_START` is truthy ("1", "true", "yes"), the
bridge deletes rows from `v9_bars_5min` whose timestamp falls on or after
today's 00:00 in `America/New_York`. The cutoff is converted to UTC for
the DB filter because `_ts_from_unix` in `backend/v9/api/v9/bars.py`
persists `ts` as a naive UTC string (e.g. `2026-05-20 04:00:00.000000`
for 2026-05-20 00:00 ET during DST).

Hard constraints — every one of these is a pre-LIVE safety:
  • Default OFF. Without the flag, nothing is touched and the bridge
    behaves exactly as before this module existed.
  • Only `v9_bars_5min` is wiped. TPO sessions, woodies bars, footprint,
    and every other table depend on multi-day windows and stay intact.
  • Only TODAY's bars are wiped. The cutoff is calendar-day boundary in
    `America/New_York`; bars stamped before midnight ET stay.
  • Failure to wipe MUST NOT block bridge startup. Every DB exception is
    swallowed with a `logger.warning`.
  • Only SQLite is supported. Postgres / Render deployments are out of
    scope until LIVE infra moves off SQLite; the wipe is skipped with a
    warning if `DATABASE_URL` doesn't point at sqlite:///.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, time as dtime, timezone
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("v9_bridge")

DEFAULT_DATABASE_URL = "sqlite:///./data/mems26_local.db"
WIPE_FLAG_ENV = "V9_BRIDGE_WIPE_TODAY_ON_START"


def _resolve_sqlite_path(database_url: str) -> Optional[Path]:
    """Return the on-disk path for a sqlite DATABASE_URL, or None for non-SQLite.

    Matches the parsing convention in `backend/v9/db/session.py`: strip
    `sqlite:///` (three slashes); what remains is either a relative path
    (e.g. `./data/mems26_local.db`) or an absolute path
    (e.g. `/tmp/foo.db` from `sqlite:////tmp/foo.db`).
    """
    if not database_url.startswith("sqlite"):
        return None
    if database_url.startswith("sqlite:///"):
        raw = database_url[len("sqlite:///"):]
    elif database_url.startswith("sqlite://"):
        raw = database_url[len("sqlite://"):]
    else:
        return None
    if not raw:
        return None
    if raw.startswith("/"):
        return Path(raw)
    return Path(raw).resolve()


def _today_midnight_utc_iso(now_et: Optional[datetime] = None) -> str:
    """Today's midnight in America/New_York, expressed as a naive UTC string.

    Returned format matches `backend.v9.api.v9.bars._ts_from_unix` output
    so a lexical `ts >= ?` filter works on the SQLite TEXT column.
    """
    try:
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
    except Exception:
        from datetime import timezone as _tz
        ny = _tz.utc  # last-ditch — wipe is still safe, just shifted to UTC midnight

    if now_et is None:
        now_et = datetime.now(tz=ny)
    midnight_et = datetime.combine(now_et.date(), dtime(0, 0), tzinfo=ny)
    midnight_utc = midnight_et.astimezone(timezone.utc)
    return midnight_utc.strftime("%Y-%m-%d %H:%M:%S")


def wipe_today_bars_if_requested(
    database_url: Optional[str] = None,
    *,
    now_et_fn: Optional[Callable[[], datetime]] = None,
    table: str = "v9_bars_5min",
) -> int:
    """If `V9_BRIDGE_WIPE_TODAY_ON_START` is truthy, DELETE today's bars.

    Returns the number of rows deleted. Returns 0 when the flag is off
    OR when the wipe fails for any reason — the bridge MUST continue
    starting up either way.

    Parameters
    ----------
    database_url:
        Override of `DATABASE_URL` for testability. Defaults to the env
        var, falling back to the repo's SQLite path.
    now_et_fn:
        Override for `datetime.now(tz=ZoneInfo("America/New_York"))`. Lets
        tests pin the "today" boundary to a known timestamp.
    table:
        Override for the table name. Exposed for tests; production callers
        should leave it at the default.
    """
    flag = os.getenv(WIPE_FLAG_ENV, "").strip().lower()
    if flag not in ("1", "true", "yes"):
        return 0

    db_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    db_path = _resolve_sqlite_path(db_url)
    if db_path is None:
        logger.warning(
            "[BRIDGE STARTUP] %s set but DATABASE_URL=%s is not SQLite — wipe skipped",
            WIPE_FLAG_ENV, db_url,
        )
        return 0
    if not db_path.exists():
        logger.warning(
            "[BRIDGE STARTUP] %s set but DB file %s missing — wipe skipped",
            WIPE_FLAG_ENV, db_path,
        )
        return 0

    now_et = now_et_fn() if now_et_fn is not None else None
    cutoff = _today_midnight_utc_iso(now_et)

    try:
        # `timeout=5.0` mirrors the backend's busy_timeout (PRAGMA in
        # backend/v9/db/session.py) so a concurrent backend POST doesn't
        # surface as `database is locked` during this one-shot DELETE.
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        try:
            cur = conn.execute(
                f"DELETE FROM {table} WHERE ts >= ?",
                (cutoff,),
            )
            deleted = cur.rowcount or 0
            conn.commit()
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        logger.warning(
            "[BRIDGE STARTUP] wipe-today DB error: %s — startup continues",
            e,
        )
        return 0
    except Exception as e:
        logger.warning(
            "[BRIDGE STARTUP] wipe-today unexpected error: %s — startup continues",
            e,
        )
        return 0

    logger.warning(
        "[BRIDGE STARTUP] Wiped %d bars from today's session "
        "(table=%s, cutoff ts >= '%s' UTC = 00:00 ET today)",
        deleted, table, cutoff,
    )
    return deleted
