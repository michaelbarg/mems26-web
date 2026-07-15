"""Item-20 — Sierra truth reconcile + naked-stop detector.

LIVE-blocker: on 2026-06-25 a Sierra fill left an orphan position the system
did not track; I-57 (07-02) was the mirror — the system believed it was in a
trade after Sierra had closed it. Both are DISAGREEMENTS between the three
sources of "am I in a position":

  1. gateway slot        — demo_slot / live_slot (in-memory belief)
  2. DB open trades      — v9_trades WHERE state NOT IN (CLOSED,...)
  3. Sierra actual       — TradeManager position, driven by real trade_fills.json

`reconcile_positions()` is a PURE verdict function (unit-testable). `main()`
gathers the real inputs and prints the verdict — runnable read-only at any time
(no restart needed). Wire the API route + periodic check at the next restart.

No Sierra-side net-position snapshot is exported today (trade_fills.json is
transient, cleared after each poll) → source #3 is the TradeManager's live
position. Full Sierra-position export (position_state.json) is a DLL change,
tracked separately. This reconcile catches every INTERNAL disagreement + the
TM-vs-belief orphan, which is where both live incidents lived.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

_SIGNALS_DIR = Path(os.environ.get(
    "V9_EXPORT_DIR", "/Users/michael/SierraChart_Data/v9_export"))
RESULT_PATH = _SIGNALS_DIR / "trade_result.json"

# trade_result.json statuses that confirm a protective stop is working.
# Statuses that confirm a protective stop exists — includes bracket placement
# (Sierra Attached Orders create stop + target as OCO; ORDER_SUBMITTED means the
# bracket was acknowledged, so the stop is working even if no MODIFY_STOP was sent).
_STOP_OK_STATUSES = {
    "MODIFY_STOP_OK", "PLACE_STOP_OK", "STOP_PLACED", "ENTRY_OK",
    "ORDER_SUBMITTED", "PLACE_BRACKET_OK",
}
# A stop confirmation older than this (seconds) is treated as stale for an
# open position → naked-stop suspect.
_STOP_STALE_S = 900.0


@dataclass
class ReconcileVerdict:
    verdict: str                       # see VERDICTS below
    in_position_belief: bool
    slot_occupied: bool
    db_open_ids: List[int] = field(default_factory=list)
    tm_in_position: Optional[bool] = None
    mismatch: bool = False
    naked_stop_suspect: bool = False
    detail: str = ""


# Verdict vocabulary
AGREED_FLAT = "AGREED_FLAT"
IN_POSITION_OK = "IN_POSITION_OK"
MISMATCH_ORPHAN_DB = "MISMATCH_ORPHAN_DB"      # DB open, slot flat (I-57 class)
MISMATCH_ORPHAN_TM = "MISMATCH_ORPHAN_TM"      # Sierra/TM position, nobody tracks (06-25 class)
MISMATCH_PHANTOM_SLOT = "MISMATCH_PHANTOM_SLOT"  # slot occupied, DB + TM flat
NAKED_STOP_SUSPECT = "NAKED_STOP_SUSPECT"      # in position, stop not confirmed
UNKNOWN_DEGRADED = "UNKNOWN_DEGRADED"          # a source errored → cannot claim flat


def reconcile_positions(
    *,
    slot_occupied: bool,
    db_open_ids: List[int],
    tm_in_position: Optional[bool] = None,
    last_result_status: Optional[str] = None,
    last_result_age_s: Optional[float] = None,
) -> ReconcileVerdict:
    """Pure three-way reconcile. Returns a verdict; never raises."""
    db_open = bool(db_open_ids)
    belief = slot_occupied or db_open or (tm_in_position is True)

    v = ReconcileVerdict(
        verdict=AGREED_FLAT, in_position_belief=belief,
        slot_occupied=slot_occupied, db_open_ids=list(db_open_ids),
        tm_in_position=tm_in_position,
    )

    # --- disagreements first (safety) ---
    if db_open and not slot_occupied:
        v.verdict, v.mismatch = MISMATCH_ORPHAN_DB, True
        v.detail = f"DB has open trade(s) {db_open_ids} but the gateway slot is flat (I-57 class)"
        return v
    if tm_in_position is True and not slot_occupied and not db_open:
        v.verdict, v.mismatch = MISMATCH_ORPHAN_TM, True
        v.detail = "Sierra/TradeManager holds a position that neither the slot nor the DB tracks (06-25 orphan class)"
        return v
    if slot_occupied and not db_open and tm_in_position is False:
        v.verdict, v.mismatch = MISMATCH_PHANTOM_SLOT, True
        v.detail = "gateway slot occupied but DB + TradeManager are flat (phantom slot)"
        return v

    # --- agreed states ---
    if not belief:
        v.verdict = AGREED_FLAT
        v.detail = "flat across slot, DB, and TradeManager"
        return v

    # In position by agreement → naked-stop check
    stop_ok = (last_result_status in _STOP_OK_STATUSES)
    stop_stale = (last_result_age_s is not None and last_result_age_s > _STOP_STALE_S)
    if (not stop_ok) or stop_stale:
        v.verdict, v.naked_stop_suspect = NAKED_STOP_SUSPECT, True
        v.detail = (f"in position but stop not confirmed "
                    f"(last_result={last_result_status!r}, age={last_result_age_s}s)")
        return v

    v.verdict = IN_POSITION_OK
    v.detail = f"in position with confirmed stop ({last_result_status})"
    return v


def _read_last_result():
    try:
        import time
        if not RESULT_PATH.exists():
            return None, None
        raw = RESULT_PATH.read_text().strip()
        if not raw:
            return None, None
        obj = json.loads(raw)
        status = obj.get("status")
        ts = obj.get("ts")
        age = (time.time() - float(ts)) if ts else None
        # Freshness window (Michael 07-15): a result older than 15 min is
        # yesterday's stale artifact — don't let it participate in any belief.
        # Without this, a 9hr-old MODIFY_STOP_OK survives overnight and feeds
        # a false "confirmed stop" or a noisy NAKED_STOP on a stale ghost.
        if age is not None and age > _STOP_STALE_S:
            logger.debug("[Reconcile] trade_result.json too old (%.0fs > %.0fs) — discarded",
                         age, _STOP_STALE_S)
            return None, None
        return status, age
    except Exception as e:
        logger.warning("[Reconcile] could not read trade_result.json: %s", e)
        return None, None


def gather_and_reconcile(gateway=None) -> ReconcileVerdict:
    """Collect the real inputs (DB + files + gateway) and reconcile.

    Fail-safe: any source that errors is treated as unknown, not as flat."""
    # DB open trades
    db_open_ids: List[int] = []
    db_ok = True
    try:
        from backend.v9.db.read import read_all
        rows = read_all(
            "SELECT id FROM v9_trades WHERE state NOT IN ('CLOSED','closed') "
            "ORDER BY id", {})
        db_open_ids = [int(r["id"]) for r in rows]
    except Exception as e:
        db_ok = False
        logger.warning("[Reconcile] DB open-trades query failed: %s", e)

    # Gateway slot
    slot_occupied = False
    if gateway is not None:
        slot_occupied = bool(getattr(gateway, "demo_slot", None) or
                             getattr(gateway, "live_slot", None))

    # TradeManager position (best-effort)
    tm_in_position: Optional[bool] = None
    if gateway is not None:
        tm = getattr(gateway, "_trade_manager", None)
        if tm is not None:
            pos = getattr(tm, "position", getattr(tm, "_position", None))
            if pos is not None:
                tm_in_position = bool(pos)

    status, age = _read_last_result()
    v = reconcile_positions(
        slot_occupied=slot_occupied, db_open_ids=db_open_ids,
        tm_in_position=tm_in_position, last_result_status=status,
        last_result_age_s=age,
    )
    # No-silent-failures: if a source errored, we must NOT report a confident
    # AGREED_FLAT — a hidden position could be exactly in the unread source.
    if not db_ok and v.verdict == AGREED_FLAT:
        v.verdict = UNKNOWN_DEGRADED
        v.detail = "DB open-trades source unavailable — cannot confirm flat"
        logger.warning("[Reconcile] %s — %s", v.verdict, v.detail)
        return v
    if v.mismatch or v.naked_stop_suspect:
        logger.warning("[Reconcile] %s — %s", v.verdict, v.detail)
    else:
        logger.info("[Reconcile] %s — %s", v.verdict, v.detail)
    return v


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    v = gather_and_reconcile(gateway=None)  # CLI has no live gateway → slot/TM unknown
    print(f"verdict={v.verdict}")
    print(f"  in_position_belief={v.in_position_belief} slot={v.slot_occupied} "
          f"db_open={v.db_open_ids} tm={v.tm_in_position}")
    print(f"  mismatch={v.mismatch} naked_stop_suspect={v.naked_stop_suspect}")
    print(f"  {v.detail}")
    print("\nnote: run from a live gateway (API route, next restart) for the "
          "slot + TradeManager sources; CLI sees DB + trade_result.json only.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    main()
