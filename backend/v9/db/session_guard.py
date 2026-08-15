"""session_guard — a poisoned transaction must never silence the system.

ROOT CAUSE (proven 2026-08-14, two independent evidence paths):
mac-2 produced fires that passed the FULL gate chain (the gateway logged
`duplicate_fire`, which is only reachable after registration at
trading_gateway.py ~2875) yet wrote ZERO rows to v9_trades — and its
`v9_trades_id_seq.last_value` still equalled `MAX(id)`, proving `Session.add()`
was never reached. Its backend log carried 37 × `psycopg2.errors.
InFailedSqlTransaction`. Postgres discards every command in an aborted
transaction, so once ANY consumer of the shared session (backend/main.py:1076
hands one `SessionLocal()` to TradeManager + BarLevelDetector + FillPoller)
failed without rolling back, every later write died silently — for 28 days.

The defect was never "no DB connection": `pool_pre_ping` was already on and
detects a *dead connection*, not an *aborted transaction on a live one*.
The defect was that every error path swallowed the failure with a bare warning
and left the transaction poisoned.

This module is the antidote, used at the write choke-points:
  ensure_clean(session)  — call BEFORE work: if the session is poisoned, roll
                           it back so the next statement can run.
  safe_write(session, fn)— run fn(); on a poisoned/aborted transaction roll back
                           and retry ONCE, then re-raise. Never hides a failure.

Both log at WARNING (No Silent Failures rule) and never raise from the cleanup
itself.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Errors that mean "this transaction is aborted; roll back and you may proceed"
_POISON_MARKERS = (
    "infailedsqltransaction",
    "current transaction is aborted",
    "pendingrollbackerror",
    "can't reconnect until invalid transaction is rolled back",
)


def _is_poisoned(exc: BaseException) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(m in text for m in _POISON_MARKERS)


def ensure_clean(session: Any, *, where: str = "") -> bool:
    """Roll the session back if it is in a failed/aborted transaction.

    Returns True when a rollback was performed. Cheap: probes with SELECT 1,
    which is exactly what Postgres refuses inside an aborted transaction.
    Never raises.
    """
    if session is None:
        return False
    try:
        from sqlalchemy import text as _text
        session.execute(_text("SELECT 1"))
        return False
    except Exception as probe_err:
        try:
            session.rollback()
            logger.warning(
                "[session_guard] poisoned transaction detected%s → rolled back "
                "(%s: %s)",
                f" in {where}" if where else "",
                type(probe_err).__name__, str(probe_err)[:120],
            )
            return True
        except Exception as rb_err:  # cleanup must never break the caller
            logger.warning("[session_guard] rollback failed%s: %s",
                           f" in {where}" if where else "", rb_err)
            return False


def safe_write(session: Any, fn: Callable[[], T], *, where: str = "") -> T:
    """Run fn(); if the transaction was poisoned, roll back and retry ONCE.

    A second failure is re-raised — the caller (and the log) must see it.
    """
    try:
        return fn()
    except Exception as e:
        if not _is_poisoned(e):
            raise
        logger.warning(
            "[session_guard] write hit a poisoned transaction%s (%s) — "
            "rolling back and retrying once",
            f" in {where}" if where else "", type(e).__name__)
        try:
            session.rollback()
        except Exception as rb_err:
            logger.warning("[session_guard] rollback before retry failed%s: %s",
                           f" in {where}" if where else "", rb_err)
        return fn()
