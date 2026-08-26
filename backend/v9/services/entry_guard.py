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

# Manual position acknowledgment file — written ONLY by cowork/Michael.
_ACK_PATH = Path(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))).joinpath("config", "manual_position_ack.json")


def _read_manual_ack() -> Optional[dict]:
    """Read the manual position ack if present AND dated today.

    The ack is valid for ONE calendar day only (ET). A stale ack from
    yesterday does NOT explain today's position — that's an orphan.
    Never raises.
    """
    try:
        if not _ACK_PATH.exists():
            return None
        ack = json.loads(_ACK_PATH.read_text(encoding="utf-8"))
        if not isinstance(ack, dict):
            return None
        # Date check: must be today ET
        from datetime import datetime
        from zoneinfo import ZoneInfo
        today_et = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        if ack.get("date") != today_et:
            return None
        if not ack.get("owner"):
            return None
        return ack
    except Exception:
        return None


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
        # ENTRY_GUARD_OWNERSHIP_V1 (3ROOTS Phase 1, Michael 26.08):
        # ownership-aware check. The old code blocked on ANY pos != 0.
        # The fix: a position is either (a) TM-managed (open trade matches),
        # (b) attributed to another machine / manual assignment, or
        # (c) truly unexplained (orphan). Only (c) blocks.
        _explained = False
        if os.getenv("ENTRY_GUARD_OWNERSHIP_V1", "0").lower() in ("1", "true", "yes"):
            try:
                # Check if TM has an open trade that matches the position
                from backend.v9.db.read import read_one
                _tm_open = read_one(
                    "SELECT id, direction FROM v9_trades "
                    "WHERE mode = 'live' AND state IN ('FILLED', 'PARTIAL', 'OPEN') "
                    "ORDER BY id DESC LIMIT 1", {})
                if _tm_open:
                    _tm_dir = (_tm_open.get("direction") or "").upper()
                    # Position matches TM trade direction
                    if (pos > 0 and _tm_dir == "LONG") or (pos < 0 and _tm_dir == "SHORT"):
                        _explained = True
                        logger.info(
                            "[EntryGuard] pos=%+d explained by TM trade #%s (%s) — "
                            "ownership check PASS",
                            pos, _tm_open.get("id"), _tm_dir)
                if not _explained:
                    # Path 2: explicit manual position acknowledgment.
                    # config/manual_position_ack.json, written ONLY by
                    # cowork/Michael (never auto-generated). Valid for ONE
                    # day (date must be today). This preserves the orphan
                    # guard: an unacknowledged position still blocks.
                    try:
                        _ack = _read_manual_ack()
                        if _ack and abs(pos) <= _ack.get("max_abs_qty", 0):
                            _explained = True
                            logger.info(
                                "[EntryGuard] pos=%+d coexist_manual "
                                "(ack %s, owner=%s) — ownership PASS",
                                pos, _ack.get("date"), _ack.get("owner"))
                    except Exception:
                        pass
            except Exception as _eo_err:
                logger.warning("[EntryGuard] ownership check error (fail-closed): %s", _eo_err)

        if not _explained:
            _reason = (
                f"UNMANAGED POSITION {pos:+d} on the account (live slot was free → not "
                "TM-managed). No manual trading (ruling 2026-08-21) → this is an "
                "anomaly (orphan/missed-fill). Investigate. Blocked pre-send"
            )
            try:
                from backend.v9.services.phone_alert import push as _eg_push
                _eg_push("entry_guard_unmanaged",
                         "\U0001f534 MEMS26: פוזיציה לא-מנוהלת",
                         f"pos={pos:+d} על החשבון, לא בספרים — אורפן/fill-שאבד. "
                         f"ירי-לייב חסום. לחקור.",
                         priority=1)
            except Exception:
                pass
            return False, _reason, warns
        # Position is explained → allow entry (with tagging)
        warns.append(f"existing position {pos:+d} is ownership-explained — entry allowed")

    if working > 0:
        _reason = (
            f"{working} working order(s) on a FLAT account — stray brackets present "
            "(no manual trading per ruling 2026-08-21 → anomaly). Blocked pre-send"
        )
        try:
            from backend.v9.services.phone_alert import push as _eg_push
            _eg_push("entry_guard_stray_orders",
                     "\U0001f534 MEMS26: הוראות-עבודה תקועות",
                     f"{working} הוראות על חשבון שטוח — אורפן. ירי-לייב חסום.",
                     priority=1)
        except Exception:
            pass
        return False, _reason, warns

    # Flat + no working orders: the recipe cap can only bind via |0 + n| > 10.
    if contracts > MAX_POSITION_ALLOWED:
        return False, (
            f"{contracts} contracts exceeds the DLL recipe cap "
            f"MaximumPositionAllowed={MAX_POSITION_ALLOWED} — Sierra would reject"
        ), warns

    return True, f"account flat (pos=0, working=0) — clear to send {contracts}", warns
