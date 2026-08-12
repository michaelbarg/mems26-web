"""PRE_SEND_ENTRY_GUARD_V1 — refuse a LIVE entry the account state guarantees to kill.

F1 of CC_WORKORDER_2026-08-12 (the 48-session audits): 18 of 57 live routes (32%)
never became a position — `ORDER_FAILED:-1` / CANCELLED / entry_ts=NULL.

Diagnosis (2026-08-12, from v9_trades × trade_activity_events.jsonl × the raw
sierra_state.json quotes in docs/reports/ALERTS_LIVE.md):

* Every `-1` burst coincides with a STANDING POSITION the TradeManager was not
  managing at fire time — the 07-20 orphan (-6/-7), the 07-23 naked orphan
  (-8 → -12), Michael's manual short on 07-24 (-4), the +10 orphan stack on
  07-27.  The deployed DLL trading recipe (`MES_AI_DataExport_merged.cpp:1847+`)
  has `AllowOppositeEntryWithOpposingPositionOrOrders = 0` and
  `MaximumPositionAllowed = 10`, so Sierra synchronously rejects (r = -1,
  GENERAL_ERROR_OR_NOT_ENABLED):
    - any entry OPPOSITE to the standing position / its working orders, and
    - any entry that would push |position| past 10 (the -12 episodes).
  A same-direction 4-lot over a small foreign position is ACCEPTED — which is
  the 07-24 nightmare shape (stacking onto Michael's manual trade).  Both sides
  of that coin argue for the same rule: a LIVE entry may only be sent when the
  account is FLAT with no working orders (single-slot doctrine).
* The margin sub-class ("Insufficient NLV", 6 rejections on 07-28) is already
  root-fixed by MARGIN_AWARE_SIZING_V1=1 + the K1e zero-size abort; after
  07-28 there are zero `ORDER_FAILED:-1` rows.  This guard adds the missing
  position/working-orders class, which margin sizing cannot see.

Behavior: called by `TradingGateway._execute_live` BEFORE any DB row, slot, or
Sierra command exists.  It can only BLOCK (never resize, never fire).  When the
account state is missing or stale it blocks the LIVE send and says so — sending
a real-money order while blind to the account is the exact class Rule 1 forbids.

Kill-switch: PRE_SEND_ENTRY_GUARD_V1=0 disables (default ON in code — this IS
the F1 fix; disabling restores the audited 32% failure surface).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Same file + freshness contract as margin_sizing.py (the other pre-send reader).
STATE = Path(os.path.expanduser("~/SierraChart_Data/v9_export/sierra_state.json"))
STATE_MAX_AGE_S = 30.0

# The deployed DLL recipe caps |position| at 10 (MES_AI_DataExport_merged.cpp:1848).
MAX_POSITION_ALLOWED = 10


def enabled() -> bool:
    """Default ON — the guard is the F1 root-fix, not an experiment."""
    return os.getenv("PRE_SEND_ENTRY_GUARD_V1", "1").strip().lower() in ("1", "true", "yes")


def _read_state_fresh() -> Optional[dict]:
    """Raw sierra_state.json if present + fresh, else None.

    Unlike margin_sizing._read_state this does NOT require acct_ok: position_qty
    and working_orders are plain DLL exports, valid even when the account-data
    subscription lags.  ±DBL_MAX / -inf sentinels are scrubbed the same way.
    """
    try:
        if not STATE.exists():
            return None
        if (time.time() - STATE.stat().st_mtime) > STATE_MAX_AGE_S:
            return None
        raw = re.sub(r':\s*-?inf\b', ':null', STATE.read_text().strip() or "{}")
        return json.loads(raw)
    except Exception as e:  # unreadable == unavailable (caller blocks honestly)
        logger.warning("[EntryGuard] sierra_state unreadable: %s", e)
        return None


def check_live_entry(direction: Optional[str], contracts: int) -> Tuple[bool, str, List[str]]:
    """(ok, reason, warnings) for a LIVE entry of `contracts` in `direction`.

    ok=False → the caller must NOT send (no trade row, no slot, no command).
    warnings are non-blocking observations worth surfacing (disarmed / sim mode).
    Never raises.
    """
    warns: List[str] = []
    if not enabled():
        return True, "PRE_SEND_ENTRY_GUARD_V1 off", warns

    state = _read_state_fresh()
    if state is None:
        return False, (
            f"sierra_state.json missing/stale (> {STATE_MAX_AGE_S:.0f}s) — cannot "
            "verify account state before a LIVE order (Rule 1: no blind real-money send)"
        ), warns

    try:
        pos = int(state.get("position_qty") or 0)
    except (TypeError, ValueError):
        pos = 0
    try:
        working = int(state.get("working_orders") or 0)
    except (TypeError, ValueError):
        working = 0

    # Non-blocking observations first (they apply regardless of the verdict).
    if state.get("order_placement_armed") in (0, "0", False):
        warns.append("order_placement_armed=0 — the DLL will ACK_SHADOW, no real order")
    if state.get("is_sim") in (1, "1", True):
        warns.append("Sierra is in SIM mode (is_sim=1) — a live-mode order routes to sim")

    if pos != 0:
        return False, (
            f"standing position {pos:+d} on the account at fire time (live slot was "
            "free → not TM-managed). Sierra's recipe rejects opposite entries "
            "(AllowOppositeEntryWithOpposingPositionOrOrders=0) and stacking onto a "
            "foreign/manual position is the 07-24 class — blocked pre-send"
        ), warns

    if working > 0:
        return False, (
            f"{working} working order(s) on a FLAT account — stray brackets/manual "
            "orders present; a system entry over them mixes books — blocked pre-send"
        ), warns

    # Flat + no working orders: the recipe cap can only bind via |0 + n| > 10.
    if contracts > MAX_POSITION_ALLOWED:
        return False, (
            f"{contracts} contracts exceeds the DLL recipe cap "
            f"MaximumPositionAllowed={MAX_POSITION_ALLOWED} — Sierra would reject"
        ), warns

    return True, f"account flat (pos=0, working=0) — clear to send {contracts}", warns
