# -*- coding: utf-8 -*-
"""DAYTYPE_HISTORY_LIVE_LOCK_V1 -- the end-of-day history row records what the system actually traded on.

FINDING (Michael ruling 19.10.2026, "fix all the gaps").  `v9_day_type_history` is written by
`DayTypeConsumer.consume` on every bar from `DayTypeStateMachine.to_classification()`, so its `opening_type` is the
machine's own A2 reading -- not the T-314 opening lock (`opening_lock.update_opening_lock`) that the gateway, the tree
and the playbook actually act on.  The two differ on 6 of 17 days, and `locked_at` is NULL in 113 of 113 rows.

FIX (flag-gated, default OFF => `apply_live_lock` returns the very same event object, the writer is untouched).
With the flag ON and the T-314 lock held for the row's own ET session date, the event handed to the consumer carries
  opening_type    = the live locked type (the value after the last negation re-read -- what the gateway read);
  locked_at       = the lock time, UTC (the consumer writes it only when the key is present);
  reasoning_notes = the machine's notes + one token  live_lock=<type>/<dir>@<HH:MM> IL  (Israel time).
`day_type` and every other column stay as today.  No lock for this session date -> the event is unchanged.
No new table or column: the lock lives on the same `day_type_machine` object main.py's handler already holds.

Notes.  After a mid-session restart T-330b re-derives the lock from the rehydrated bars, so `locked_at` is then the
restore time (the type is recomputed from the same closed bars).  The lock attributes live on the machine and
`machine.reset()` does not clear them, so a lock stamped on another ET date is NOT today's lock and is ignored here.

FAIL-SAFE: any exception -> WARNING and the event goes through unchanged.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

FLAG = "DAYTYPE_HISTORY_LIVE_LOCK_V1"
_TRUE = ("1", "true", "yes")
_ET = ZoneInfo("America/New_York")
_IL = ZoneInfo("Asia/Jerusalem")
_NOTES_MAX = 1024              # v9_day_type_history.reasoning_notes is VARCHAR(1024)

__all__ = ["FLAG", "enabled", "read_lock", "apply_live_lock"]


def enabled() -> bool:
    """Read at call time (never cached)."""
    return os.getenv(FLAG, "0").strip().lower() in _TRUE


def _parse_at(value: Any) -> Optional[datetime]:
    """`_opening_locked_at` is ET ISO text (main.py passes now_et().isoformat()); a naive value is read as ET."""
    if value is None or value == "":
        return None
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_ET)
    return dt


def read_lock(machine: Any, session_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """The T-314 lock exactly as the gateway/tree read it: {"type", "dir", "at"} (`at` aware), or None.

    Not locked, no type, or (when `session_date` is given) not stamped on that ET date -> None."""
    if machine is None or not getattr(machine, "_opening_type_locked", False):
        return None
    val = getattr(machine, "_opening_locked_val", None)
    val = str(val).strip() if val is not None else ""
    if not val:
        return None
    at = _parse_at(getattr(machine, "_opening_locked_at", None))
    if session_date is not None and (at is None or at.astimezone(_ET).date() != session_date):
        return None
    direction = getattr(machine, "_opening_locked_dir", None)
    return {"type": val, "dir": None if direction is None else str(direction), "at": at}


def _with_token(notes: Any, token: str) -> str:
    base = "" if notes is None else str(notes)
    if token in base:
        return base
    out = (base + " " + token) if base else token
    if len(out) > _NOTES_MAX:      # keep the token whole, trim the machine's text
        out = base[: max(0, _NOTES_MAX - len(token) - 1)].rstrip() + " " + token
    return out


def apply_live_lock(event: Dict[str, Any], machine: Any) -> Dict[str, Any]:
    """Event for `DayTypeConsumer.consume`, with the live lock folded in when the flag is ON."""
    if not enabled():
        return event
    try:
        from backend.v9.systems.day_type.consumer import DayTypeConsumer
        session_date = DayTypeConsumer._extract_session_date(event["timestamp"])
        lock = read_lock(machine, session_date)
        if lock is None:
            return event
        at = lock["at"]
        token = "live_lock=%s/%s@%s IL" % (
            lock["type"], lock["dir"] or "NONE", at.astimezone(_IL).strftime("%H:%M"))
        out = dict(event)
        out["opening_type"] = lock["type"]
        out["locked_at"] = at.astimezone(timezone.utc)
        out["reasoning_notes"] = _with_token(event.get("reasoning_notes"), token)
        return out
    except Exception as exc:
        logger.warning("[DayTypeHistory] live-lock bridge failed (%s) -- row written as before", exc)
        return event
