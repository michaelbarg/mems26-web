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
# 2026-08-19 (W3 false-alarm fix): a FLATTEN_ACCOUNT_OK younger than this is an
# intentional close in progress (MAE-scratch / manual flatten) — suppress the
# naked-stop alarm during the fill-propagation race.
_FLATTEN_GRACE_S = 120.0


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
    sierra_position_qty: Optional[int] = None,
    ack_within_position: bool = False,
) -> ReconcileVerdict:
    """Pure three-way reconcile. Returns a verdict; never raises.

    `sierra_position_qty` (2026-07-27) is Sierra's OWN net position — the
    hardest available truth. When it is a fresh 0 the account is FLAT, and a
    "naked stop" alarm is impossible by definition: there is nothing to protect.
    Without it, stuck PENDING/FILLED rows in our own bookkeeping produced a
    phantom belief and screamed NAKED_STOP_SUSPECT at Michael while Sierra was
    flat (07-27 evening: an alert popping "with no reason"). None = unknown →
    previous behaviour (no new assumptions).
    """
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

    # Sierra flat overrides every internal belief: no position → no naked stop.
    # (Bookkeeping drift must NEVER produce a safety alarm about a position that
    # does not exist — it trains Michael to ignore real alarms.)
    if sierra_position_qty is not None and int(sierra_position_qty) == 0:
        v.verdict = AGREED_FLAT
        v.detail = ("Sierra reports FLAT (position_qty=0) — internal belief "
                    f"(slot={slot_occupied}, db_open={db_open_ids}, tm={tm_in_position}) "
                    "is stale bookkeeping, not a live position")
        v.naked_stop_suspect = False
        return v

    # 2026-08-19 (false-alarm fix): a fresh FLATTEN_ACCOUNT_OK means the position
    # is being closed ON PURPOSE (MAE-scratch/manual flatten). During that race
    # window (flatten ACKed, fill not yet propagated) a "naked stop" alarm is
    # noise — it fired on every scratch on 08-19 (#741/#746, age 0.65-2.26s)
    # while the FLATTEN command was already acknowledged by Sierra.
    if (last_result_status == "FLATTEN_ACCOUNT_OK"
            and last_result_age_s is not None
            and float(last_result_age_s) <= _FLATTEN_GRACE_S):
        v.verdict = IN_POSITION_OK
        v.detail = (f"flatten in progress (FLATTEN_ACCOUNT_OK "
                    f"{float(last_result_age_s):.1f}s ago) — naked-stop check suppressed")
        return v

    # In position by agreement → naked-stop check
    #
    # 2026-08-21 (Michael, live: "מקבל התראה שיש נייקד סטופ וזה לא נכון"):
    # the age test below used to ALSO run here, and it silently undid the
    # 08-19 fix. `_read_last_result` already guarantees that any status it
    # returns either (a) is younger than _STOP_STALE_S, or (b) was written
    # at/after THIS position's entry — i.e. it is this position's own truth,
    # however old. Re-testing the age here therefore re-raised the alarm on
    # exactly the case the fix was written for: an attached OCO stop resting
    # Sierra-side emits no new ACKs, so a quiet trade older than 15 minutes
    # alarmed on every single bar. Today that produced **14,524** CRITICAL
    # lines while Sierra showed 3 working stops covering the position — the
    # kind of noise that teaches Michael to ignore a real alarm.
    # The staleness guard is not lost: it lives in `_read_last_result`, which
    # returns (None, None) for anything older than the position (or older than
    # 15 min when the entry time is unknown) — and `not stop_ok` catches that.
    stop_ok = (last_result_status in _STOP_OK_STATUSES)
    # The age test still applies to an ACK whose provenance we do NOT know
    # (direct callers / tests). `gather_and_reconcile` passes
    # ack_within_position=True when `_read_last_result` proved the ACK belongs
    # to this position, and only then is age irrelevant.
    stop_stale = (not ack_within_position
                  and last_result_age_s is not None
                  and last_result_age_s > _STOP_STALE_S)
    # T-175: before raising NAKED_STOP_SUSPECT, check Sierra's ACTUAL working
    # orders. The `last_result` file is a DLL ACK that goes stale after 15min
    # on a quiet trade (OCO stop resting Sierra-side emits no new ACKs).
    # Sierra's own order list is the ground truth. If it shows a protective
    # stop → the position is covered, regardless of last_result staleness.
    if (not stop_ok) or stop_stale:
        try:
            from backend.v9.services.sierra_position_reconciler import (
                _has_protective_stop, _sierra_state_orders, _sierra_state_avg_price,
                _sierra_state_qty)
            _sq = _sierra_state_qty()
            if _sq is not None and _sq != 0:
                _orders = _sierra_state_orders()
                _avg = _sierra_state_avg_price()
                _protected = _has_protective_stop(_sq, _orders, _avg)
                if _protected is True:
                    v.verdict = IN_POSITION_OK
                    v.detail = (f"T-175: last_result stale but Sierra shows "
                                f"protective stop (orders={len(_orders or [])})")
                    return v
        except Exception:
            pass  # fail-open: can't check → fall through to original alarm
        v.verdict, v.naked_stop_suspect = NAKED_STOP_SUSPECT, True
        v.detail = (f"in position but stop not confirmed "
                    f"(last_result={last_result_status!r}, age={last_result_age_s}s)")
        return v

    v.verdict = IN_POSITION_OK
    v.detail = f"in position with confirmed stop ({last_result_status})"
    return v


def _read_last_result(min_ts=None):
    """Read trade_result.json → (status, age_s).

    `min_ts` (2026-08-19 W3 false-alarm root-fix): epoch of the CURRENT open
    position's entry. An attached-OCO stop rests Sierra-side and produces NO
    new ACKs, so on any quiet trade >15 min the blanket 900s discard turned the
    file into (None, None) → NAKED_STOP_SUSPECT on every bar (08-19: #738/#744
    alarmed for minutes with their brackets working). An ACK written at/after
    this position's entry is still THIS position's truth, however old. The
    07-15 "yesterday's stale artifact" protection is preserved: anything older
    than the entry (or when min_ts is unknown) is discarded as before.
    """
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
            # 120s slack: the entry ACK can be written a moment before the DB row.
            if (min_ts is not None and ts is not None
                    and float(ts) >= float(min_ts) - 120.0):
                return status, age  # stale by clock, but within THIS position's lifetime
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

    # 2026-08-19: bound last-result staleness by the open position's lifetime
    # (see _read_last_result docstring). live/demo only — shadow rows are not
    # a real position and must not extend the acceptance window.
    _entry_epoch = None
    try:
        if db_open_ids:
            _r = read_all(
                "SELECT EXTRACT(EPOCH FROM MIN(entry_ts)) AS ep FROM v9_trades "
                "WHERE state NOT IN ('CLOSED','closed') AND mode IN ('live','demo') "
                "AND entry_ts IS NOT NULL", {})
            if _r and _r[0].get("ep") is not None:
                _entry_epoch = float(_r[0]["ep"])
    except Exception:
        _entry_epoch = None

    status, age = _read_last_result(min_ts=_entry_epoch)
    # 2026-07-27: feed Sierra's OWN net position (hardest truth, ≤10s fresh) so
    # stale internal bookkeeping can never raise a naked-stop alarm on a flat
    # account. Unknown/stale → None → previous behaviour.
    _sq: Optional[int] = None
    try:
        from backend.v9.services.sierra_position_reconciler import _sierra_state_qty as _sq_read
        _sq = _sq_read()
    except Exception:
        _sq = None
    v = reconcile_positions(
        slot_occupied=slot_occupied, db_open_ids=db_open_ids,
        tm_in_position=tm_in_position, last_result_status=status,
        last_result_age_s=age, sierra_position_qty=_sq,
        # `_read_last_result` already discarded anything that predates this
        # position, so a status it returned IS this position's own ACK — its
        # clock age must not re-raise the naked-stop alarm (2026-08-21).
        ack_within_position=(status is not None and _entry_epoch is not None),
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


# ─────────────────────────────────────────────────────────────────────────────
# T-183 — STUCK LIVE SLOT (root-cause-independent alarm)
#
# 2026-08-31: the live path was blocked SILENTLY for ~3.5h (17:45→21:07). The
# books were closed in the DB but `gateway.live_slot` stayed occupied, so every
# new live fire was refused with `live_blocked_by="live_slot_occupied"` and
# NOTHING said so. This is the third instance of the class: I-57 (07-08, fixed
# at one call site in trades.py) and T-178 (08-31) are the same failure.
#
# Why the EXISTING reconcile did not catch it — MISMATCH_PHANTOM_SLOT is
# UNREACHABLE DEAD CODE, and has been since 2026-07-27:
#   It requires `slot_occupied and not db_open and tm_in_position is False`.
#   `db_open_ids` above is built with the DENYLIST `state NOT IN ('CLOSED')`.
#   v9_trades holds 35 rows in state 'CANCELLED' (live, 07-10..07-27) which are
#   terminal but are NOT 'CLOSED' — so that query NEVER returns empty, `db_open`
#   is PERMANENTLY True, and the phantom branch can never run on any day.
#   Verified 09-01: `SELECT state, count(*) FROM v9_trades GROUP BY 1`
#   → CLOSED 788, CANCELLED 35 (and nothing else).
#   The run instead falls through to the naked-stop path, which on 08-31 emitted
#   403 CRITICAL "NAKED_STOP_SUSPECT — in position" lines: the exact opposite of
#   the truth. Evidence: `grep -c PHANTOM_SLOT /tmp/backend.err.log` → 0,
#   `grep -c 'Reconcile-live' …` → 403, all NAKED_STOP_SUSPECT.
#   (Open SHADOW rows add to db_open during a session, but the CANCELLED rows
#   alone make the masking permanent — the mode filter is not sufficient.)
#
# Hence this check uses an ALLOW-LIST of genuinely open states, never a denylist.
#
# This check is deliberately NOT a second opinion on the root cause. It asks one
# question that is true in every variant: *is the live slot held by a trade that
# is not actually open?* It compares the slot against OPEN LIVE/DEMO trades only
# (never shadow), and ignores the TradeManager's boolean entirely — that belief
# was stale in T-178 and is what misrouted the verdict.
#
# ALERT-ONLY. It never releases a slot, never writes, never touches execution.
STUCK_SLOT_THRESHOLD_S = 600.0  # 10 min — long enough to outlast entry/fill races


@dataclass
class StuckSlotState:
    stuck: bool = False
    alarm: bool = False               # stuck for longer than the threshold
    slot_trade_id: Optional[int] = None
    live_open_ids: List[int] = field(default_factory=list)
    stuck_since: Optional[float] = None
    stuck_seconds: float = 0.0
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "stuck": self.stuck, "alarm": self.alarm,
            "slot_trade_id": self.slot_trade_id,
            "live_open_ids": list(self.live_open_ids),
            "stuck_seconds": round(self.stuck_seconds, 1),
            "threshold_seconds": STUCK_SLOT_THRESHOLD_S,
            "detail": self.detail,
        }


def evaluate_stuck_slot(
    *,
    slot_occupied: bool,
    slot_trade_id: Optional[int],
    live_open_ids: List[int],
    stuck_since: Optional[float],
    now: float,
    threshold_s: float = STUCK_SLOT_THRESHOLD_S,
) -> StuckSlotState:
    """PURE verdict: is the live slot blocking fires while holding nothing real?

    `stuck_since` is the caller's memory of when this condition started (None if
    it was healthy last time). Returns the new state; the caller persists
    `stuck_since` for the next call. No I/O, no clock — unit-testable.
    """
    ids = [int(i) for i in (live_open_ids or [])]

    if not slot_occupied:
        return StuckSlotState(stuck=False, live_open_ids=ids,
                              detail="live slot is free")

    # Occupied by a trade that IS open live/demo → healthy, nothing to say.
    if slot_trade_id is not None and int(slot_trade_id) in ids:
        return StuckSlotState(stuck=False, slot_trade_id=int(slot_trade_id),
                              live_open_ids=ids,
                              detail=f"slot holds open live trade {int(slot_trade_id)}")

    began = stuck_since if stuck_since is not None else now
    held = max(0.0, now - began)
    why = ("slot holds trade "
           f"{slot_trade_id!r} which is NOT among the open live/demo trades {ids}"
           if slot_trade_id is not None else
           f"slot is occupied but carries no readable trade_id; open live/demo trades: {ids}")
    return StuckSlotState(
        stuck=True, alarm=held >= threshold_s,
        slot_trade_id=(int(slot_trade_id) if slot_trade_id is not None else None),
        live_open_ids=ids, stuck_since=began, stuck_seconds=held,
        detail=(f"LIVE PATH BLOCKED: {why} — every new live fire is being "
                f"refused with live_slot_occupied ({held / 60.0:.1f} min)"),
    )


def _slot_trade_id(gateway) -> Optional[int]:
    """The trade_id inside the gateway slot, whether dict (post-08-08) or scalar.

    Same shape trap that made /system6/diagnose blind for 23 days (T-187).
    """
    slot = (getattr(gateway, "demo_slot", None) or
            getattr(gateway, "live_slot", None)) if gateway is not None else None
    if not slot:
        return None
    raw = slot.get("trade_id") if isinstance(slot, dict) else slot
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def gather_stuck_slot(gateway, stuck_since: Optional[float] = None) -> StuckSlotState:
    """Gather the live inputs and evaluate. Never raises."""
    import time as _t
    slot_occupied = bool(
        getattr(gateway, "demo_slot", None) or getattr(gateway, "live_slot", None)
    ) if gateway is not None else False

    live_open_ids: List[int] = []
    try:
        from backend.v9.db.read import read_all
        # ALLOW-LIST, not `state NOT IN ('CLOSED')` — that denylist is the exact
        # bug that made MISMATCH_PHANTOM_SLOT unreachable (see the note above).
        # Plus the mode filter: shadow rows are not a live position.
        # 'OPEN' is the legacy cockpit alias for FILLED (see bar_level_detector).
        rows = read_all(
            "SELECT id FROM v9_trades "
            "WHERE state IN ('PENDING','FILLED','PARTIAL','OPEN') "
            "AND mode IN ('live','demo') ORDER BY id", {})
        live_open_ids = [int(r["id"]) for r in rows]
    except Exception as e:
        # Rule 1: a failed read is NOT evidence of a stuck slot. Report unknown.
        logger.warning("[StuckSlot] open live-trade query failed: %s", e)
        return StuckSlotState(stuck=False, detail=f"unknown — DB read failed: {str(e)[:100]}")

    return evaluate_stuck_slot(
        slot_occupied=slot_occupied,
        slot_trade_id=_slot_trade_id(gateway),
        live_open_ids=live_open_ids,
        stuck_since=stuck_since,
        now=_t.time(),
    )


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
