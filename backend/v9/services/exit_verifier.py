"""T4 — books close only after Sierra proves the exit actually happened.

Michael, live 2026-08-14: "המערכת הודיעה על מימוש ובפועל לא בוצע המימוש בסיארה."

Trade #682 was booked CLOSED / $0 at 20:00:07 while Sierra still held SHORT 4 @
7799.25 for the next 62 minutes (fills-journal: no exit fill until the 21:02—21:09
STOPs, real loss −$75, booked $0). Root cause: every exit path treated *"a
command file was written"* as *"the position is gone"*. A queued command can sit
unsent, be sent and never ACKed, or be archived stale — none of those is an exit.

This module holds the close PENDING until Sierra's own state proves it. Two
independent facts are available:

  1. **wire** — the queue file disappeared (`drain_command_queue` removes a file
     only after a DLL ACK), and
  2. **reality** — `sierra_state.json` shows the position flat.

Fact 2 is the one that decides. Fact 1 alone is NOT sufficient and must never be
used alone: the DLL happily ACKs a command it then fails to execute — that is
precisely what `op=EXIT` does (`r=-1`, known-broken, see CLAUDE.md). Fact 1 is
recorded for diagnosis only.

Failure is loud and SAFE-SIDE: if the exit cannot be verified we do **not** close
the books. An open book over a live position is recoverable; a closed book over a
live position is a ghost — it frees the LIVE slot (so the engine stacks another
fire on top), reports $0 (so the daily risk counter under-counts), and stops all
management of a position that is still losing money.

Flag `EXIT_VERIFY_V1` (default ON — implements Michael's 08-14/08-15 ruling;
`=0` restores the old close-immediately behavior for rollback only).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.getenv("EXIT_VERIFY_V1", "1").lower() in ("1", "true", "yes")


def _timeout_s() -> float:
    """How long one verification attempt waits for Sierra to go flat."""
    return float(os.getenv("EXIT_VERIFY_TIMEOUT_S", "45"))


def _max_attempts() -> int:
    """How many FLATTEN emissions total (1 = the original, no retry)."""
    return int(os.getenv("EXIT_VERIFY_MAX_ATTEMPTS", "2"))


def _unknown_max_s() -> float:
    """How long we tolerate 'Sierra state unknown' before shouting about it.

    Waiting silently forever is not the safe side — it just moves the failure
    somewhere nobody looks.
    """
    return float(os.getenv("EXIT_VERIFY_UNKNOWN_MAX_S", "300"))


@dataclass
class PendingExit:
    trade_id: int
    source: str
    reason: str
    on_confirmed: Callable[[], None]
    registered_ts: float
    still_open: Optional[Callable[[], bool]] = None
    attempt: int = 1
    last_emit_ts: float = 0.0
    qty_before: Optional[int] = None
    notes: List[str] = field(default_factory=list)


# trade_id → PendingExit. Module-level so it survives across poller cycles.
_pending: Dict[int, PendingExit] = {}


def pending_count() -> int:
    return len(_pending)


def is_pending(trade_id: int) -> bool:
    return int(trade_id) in _pending


def clear() -> None:
    """Test hook / cold-start reset."""
    _pending.clear()


def register(trade_id: int, *, source: str, reason: str,
             on_confirmed: Callable[[], None],
             still_open: Optional[Callable[[], bool]] = None,
             qty_before: Optional[int] = None) -> bool:
    """Record that a FLATTEN was emitted for `trade_id`; close only when proven.

    Returns True when the close was deferred to the verifier, False when the
    flag is off (caller must then close immediately, old behavior).
    """
    if not _enabled():
        return False
    tid = int(trade_id)
    now = time.time()
    if tid in _pending:
        # Already waiting — do not stack a second pending or reset its clock.
        _pending[tid].notes.append(f"duplicate register from {source} at {now:.0f}")
        return True
    _pending[tid] = PendingExit(
        trade_id=tid, source=source, reason=reason,
        on_confirmed=on_confirmed, registered_ts=now, last_emit_ts=now,
        still_open=still_open, qty_before=qty_before,
    )
    logger.info("[ExitVerify] trade %d exit PENDING (%s) — books stay open until "
                "Sierra proves flat", tid, source)
    return True


def _sierra_qty() -> Optional[int]:
    """Fresh net position from the DLL state file; None when stale/missing.

    Reuses the reconciler's reader so there is exactly one definition of
    "Sierra's position" in the codebase (and one staleness rule: >10s → None,
    honest unknown per Rule 1 — never a synthesized zero).
    """
    try:
        from backend.v9.services.sierra_position_reconciler import _sierra_state_qty
        return _sierra_state_qty()
    except Exception:
        return None


def _reemit_flatten(p: PendingExit) -> bool:
    try:
        from backend.v9.services.sierra_command import write_flatten_account
        write_flatten_account(trade_id=str(p.trade_id),
                              source=f"{p.source}_retry{p.attempt}",
                              reason=f"exit not verified: {p.reason}")
        return True
    except Exception as err:
        logger.critical("[ExitVerify] retry FLATTEN failed for trade %d: %s",
                        p.trade_id, err)
        return False


def _push(event: str, title: str, body: str) -> None:
    try:
        from backend.v9.services.phone_alert import push
        push(event, title, body, priority=1)
    except Exception:
        pass


def verify_pending(now: Optional[float] = None) -> int:
    """Run one verification sweep. Returns the number of exits confirmed.

    Called from the FillPoller cycle (≤2s), so a normal exit confirms within one
    tick of Sierra writing its state file.
    """
    if not _pending:
        return 0
    now = time.time() if now is None else now
    qty = _sierra_qty()
    confirmed = 0

    for tid in list(_pending.keys()):
        p = _pending.get(tid)
        if p is None:
            continue
        elapsed = now - p.registered_ts

        # Another path may legitimately have closed the books first —
        # POSITION_TRUTH_SYNC_V1 ('SIERRA_FLAT'), a Sierra stop fill, or a
        # manual close. That is a correct outcome, not a failure: drop the
        # pending quietly instead of closing twice.
        if p.still_open is not None:
            try:
                if not p.still_open():
                    del _pending[tid]
                    logger.info("[ExitVerify] trade %d already closed by another "
                                "path after %.1fs — pending dropped", tid, elapsed)
                    continue
            except Exception:
                pass  # unknown → keep verifying (safe side)

        # ── reality check ────────────────────────────────────────────────────
        if qty == 0:
            # Sierra is flat → the exit happened. Close the books now.
            del _pending[tid]
            try:
                p.on_confirmed()
                confirmed += 1
                logger.info("[ExitVerify] trade %d exit CONFIRMED flat after "
                            "%.1fs (%s) — books closed", tid, elapsed, p.source)
            except Exception as err:
                logger.critical("[ExitVerify] trade %d verified flat but the "
                                "close callback FAILED: %s", tid, err)
                _push("exit_close_callback_failed",
                      "\U0001f534 MEMS26: סגירת-ספרים נכשלה",
                      f"trade {tid}: סיירה שטוחה אך רישום-הסגירה נכשל — לבדוק ידנית")
            continue

        if qty is None:
            # Stale/absent state file — we do NOT know. Never guess flat.
            # But "wait forever, quietly" is its own failure: the books stay
            # open, the LIVE slot stays occupied, and nobody is told. Bound it:
            # after EXIT_VERIFY_UNKNOWN_MAX_S of no fresh state, say so loudly
            # once and stop tracking. The books still stay open (an open book
            # over a possibly-live position is the recoverable side).
            if elapsed > _unknown_max_s():
                del _pending[tid]
                logger.critical("[ExitVerify] trade %d: no fresh sierra_state for "
                                "%.0fs — exit UNVERIFIABLE. Books stay OPEN; "
                                "check Sierra manually.", tid, elapsed)
                _push("exit_unverifiable",
                      "\U0001f534 MEMS26: אי-אפשר לאמת מימוש",
                      f"trade {tid} ({p.source}): אין קריאת-מצב טרייה מסיירה "
                      f"{elapsed:.0f} שניות — לא ידוע אם הפוזיציה נסגרה. "
                      f"הספרים נשארו פתוחים. לבדוק ידנית בסיירה.")
            elif elapsed > _timeout_s() * 2:
                logger.warning("[ExitVerify] trade %d: no fresh sierra_state for "
                               "%.0fs — cannot verify exit", tid, elapsed)
            continue

        # ── still holding → escalate on timeout ──────────────────────────────
        if (now - p.last_emit_ts) < _timeout_s():
            continue

        if p.attempt < _max_attempts():
            p.attempt += 1
            p.last_emit_ts = now
            logger.critical("[ExitVerify] trade %d STILL OPEN in Sierra (%s c) "
                            "%.0fs after %s FLATTEN — re-emitting (attempt %d)",
                            tid, qty, elapsed, p.source, p.attempt)
            _reemit_flatten(p)
            _push("exit_not_executed_retry",
                  "\U0001f7e0 MEMS26: המימוש לא בוצע — שולח שוב",
                  f"trade {tid}: {p.source} — סיירה עדיין מחזיקה {qty} חוזים "
                  f"{elapsed:.0f} שניות אחרי פקודת-הסגירה. ניסיון {p.attempt}.")
            continue

        # Exhausted. Keep the books OPEN — never a ghost. Alert and stop
        # re-emitting (a command loop against a stuck DLL helps nobody).
        del _pending[tid]
        logger.critical("[ExitVerify] trade %d EXIT NOT EXECUTED — Sierra still "
                        "holds %s after %d attempts / %.0fs. Books stay OPEN. "
                        "MANUAL FLATTEN REQUIRED.", tid, qty, p.attempt, elapsed)
        _push("exit_not_executed",
              "\U0001f534 MEMS26: המימוש לא בוצע בסיירה",
              f"trade {tid} ({p.source}): נשלחו {p.attempt} פקודות סגירה, "
              f"סיירה עדיין מחזיקה {qty} חוזים. הספרים נשארו פתוחים — "
              f"נדרש FLATTEN ידני.")

    return confirmed
