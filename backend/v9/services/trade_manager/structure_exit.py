"""STRUCTURE_EXIT_FAILBREAK_V1 — exit on structural failure (Michael 30.08).

"למעשה אני רוצה לראות סגירה בכישלון פריצה." — the same failed_break detector
that fires entry shorts now also triggers exits from longs (and vice versa).

Grade A: a failed break IN THE DIRECTION of the open position means the trade
is on the wrong side of a structural event. Three graduated actions:
  1. MODIFY_TARGET → pull remaining target to the return line (bar close) or POC
  2. MODIFY_STOP  → tighten to beyond the return bar (LONG: below bar low)
  3. FLATTEN      → if open profit ≥ 1.0R or ≥ 0.75×ATR

Grade B (STRUCTURE_EXIT_DOUBLE_V1): CEILING/FLOOR_FAILED confirms → FLATTEN
Grade C (STRUCTURE_EXIT_REVERSAL_V1): grade B + S1 direction flip + lower-high

Pure function (should_exit). The caller (bar_level_detector) does the flagging
and the actual emit. This module never touches Sierra, the DB, or os.getenv.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def should_exit_on_failbreak(
    *,
    trade_direction: str,
    trade_entry_price: float,
    trade_stop: Optional[float],
    trade_t1_hit: bool,
    bar_high: float,
    bar_low: float,
    bar_close: float,
    failed_break: Optional[Dict[str, Any]],
    atr: Optional[float] = None,
    initial_risk_pts: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Grade-A: should we exit this trade because of a structural failed break?

    Returns {"action": "modify_target"|"modify_stop"|"flatten", ...} or None.

    The failed_break dict comes from detect_failed_break — the SAME detector
    the entry system uses. We don't re-detect; the caller runs the detector
    and passes the result. This keeps the two consumers (entry + exit)
    guaranteed byte-identical.

    Logic:
      Upper failed break (direction=SHORT in the trigger) → exit from LONG
      Lower failed break (direction=LONG in the trigger)  → exit from SHORT
    """
    if failed_break is None:
        return None

    td = (trade_direction or "").upper()
    fb_dir = (failed_break.get("direction") or "").upper()
    if not td or not fb_dir:
        return None

    # The failed break fires in the OPPOSITE direction from the failed move.
    # FB_HIGH → SHORT entry (price failed to go UP → SHORT).
    # If we're LONG and a failed break fires SHORT → we're on the wrong side.
    exit_signal = (td == "LONG" and fb_dir == "SHORT") or \
                  (td == "SHORT" and fb_dir == "LONG")
    if not exit_signal:
        return None

    # ── Compute the three graduated actions ──
    return_line = bar_close
    poc = failed_break.get("target_poc") or failed_break.get("poc")

    # Action 1: pull target to return line or POC (whichever is closer to entry)
    if poc is not None:
        if td == "LONG":
            new_target = max(return_line, poc)  # closest above
        else:
            new_target = min(return_line, poc)  # closest below
    else:
        new_target = return_line

    # Action 2: tighten stop to beyond the return bar
    if td == "LONG":
        new_stop = bar_low - 0.25  # one tick below bar low
    else:
        new_stop = bar_high + 0.25  # one tick above bar high

    # Action 3: flatten if profit is sufficient
    flatten = False
    if trade_stop is not None and atr is not None and atr > 0:
        risk_pts = abs(trade_entry_price - trade_stop)
        if td == "LONG":
            open_profit_pts = bar_close - trade_entry_price
        else:
            open_profit_pts = trade_entry_price - bar_close

        flatten = (
            (risk_pts > 0 and open_profit_pts >= 1.0 * risk_pts) or
            (open_profit_pts >= 0.75 * atr)
        )

    action = "flatten" if flatten else "modify_stop"

    return {
        "action": action,
        "new_target": round(new_target, 2),
        "new_stop": round(new_stop, 2),
        "flatten": flatten,
        "reason": (
            f"STRUCTURE_EXIT grade-A: failed break {fb_dir} while {td} — "
            f"{'FLATTEN (profit sufficient)' if flatten else 'tighten stop'}"
        ),
        "failed_break_type": failed_break.get("type", ""),
        "return_line": round(return_line, 2),
        "poc": round(poc, 2) if poc else None,
    }


def should_exit_on_double_top(
    *,
    trade_direction: str,
    ceiling_floor_state: Optional[Dict[str, Any]],
    grade_a_fired: bool,
) -> Optional[Dict[str, Any]]:
    """Grade-B: CEILING_FAILED/FLOOR_FAILED confirms → FLATTEN unconditionally.

    Only fires if grade-A didn't already close the trade (double evidence needed
    to override the "didn't have enough profit" clause from grade-A).
    """
    if ceiling_floor_state is None:
        return None
    if grade_a_fired:
        return None  # grade-A already handled it

    state = ceiling_floor_state.get("state", "")
    td = (trade_direction or "").upper()

    # CEILING_FAILED while LONG → exit (the ceiling we failed to break is our direction)
    # FLOOR_FAILED while SHORT → exit
    if (td == "LONG" and state == "CEILING_FAILED") or \
       (td == "SHORT" and state == "FLOOR_FAILED"):
        return {
            "action": "flatten",
            "flatten": True,
            "reason": (
                f"STRUCTURE_EXIT grade-B: {state} while {td} — "
                f"FLATTEN (double evidence, no profit threshold)"
            ),
            "p1": ceiling_floor_state.get("p1"),
            "p2": ceiling_floor_state.get("p2"),
            "confirm_level": ceiling_floor_state.get("confirm_level"),
        }

    return None


def should_exit_on_reversal(
    *,
    trade_direction: str,
    ceiling_floor_state: Optional[Dict[str, Any]],
    s1_direction: Optional[str],
    lower_high_broken: bool,
) -> Optional[Dict[str, Any]]:
    """Grade-C: grade-B AND direction reversal — BOTH conditions required.

    Deliberately strict (two conditions) to avoid exiting on label jitter (T-137).
    """
    td = (trade_direction or "").upper()

    # Need BOTH: ceiling/floor failure AND direction reversal
    if ceiling_floor_state is None:
        return None

    state = ceiling_floor_state.get("state", "")
    structure_exit = (td == "LONG" and state == "CEILING_FAILED") or \
                     (td == "SHORT" and state == "FLOOR_FAILED")
    if not structure_exit:
        return None

    # S1 must publish the OPPOSITE direction
    s1 = (s1_direction or "").upper()
    direction_flipped = (td == "LONG" and s1 == "DOWN") or \
                        (td == "SHORT" and s1 == "UP")
    if not direction_flipped:
        return None

    # Lower-high (for LONG) or higher-low (for SHORT) must be broken
    if not lower_high_broken:
        return None

    return {
        "action": "flatten_and_lock",
        "flatten": True,
        "lock_edge": True,
        "reason": (
            f"STRUCTURE_EXIT grade-C: {state} + S1={s1} + "
            f"structural break → FLATTEN + lock edge"
        ),
    }
