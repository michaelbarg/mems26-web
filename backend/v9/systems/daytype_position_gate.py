"""daytype_position_gate — direction allowed by day-type + price position.

#68 unified gate. Replaces:
  - reactive_location_gate (POC-only, REACTIVE-only)
  - TREND_DIRECTION_GATE (CCI-based — wrong model per Michael)

The direction is determined by day-type + where the price is relative to
structural levels (IB/VA/POC), NOT by CCI trend_state.

Rules per day-type (from §1 table, Michael 2026-06-20):
  Nontrend:        SKIP (handled by daytype_playbook, not here)
  Normal:          LONG only below POC (near VAL) · SHORT only above POC (near VAH)
  Variation:       WITH expansion only: LONG if IB broke up · SHORT if IB broke down
  Neutral_Center:  Both sides allowed (fade both edges)
  Neutral_Extreme: Both sides allowed (fade edges, hold winner)
  Trend_DD:        WITH breakout direction only
  Trend_Normal:    WITH trend direction only

Flag: DAYTYPE_POSITION_GATE (default OFF). Fail-open on missing data.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.environ.get("DAYTYPE_POSITION_GATE", "0").lower() in ("1", "true", "yes")


def decide(
    *,
    pattern: Optional[str],
    direction: str,
    day_type: Optional[str],
    entry_price: Optional[float],
    tpo_ctx: Optional[Dict],
    trend_state: Optional[str] = None,
) -> Tuple[bool, str]:
    """Decide whether direction is allowed for this day-type + position.

    Returns (allow: bool, reason: str).
    Fail-open: missing data → allow.
    """
    if not _enabled():
        return (True, "gate OFF")

    if not day_type or not direction:
        return (True, "missing day_type/direction (fail-open)")

    dir_upper = direction.upper()

    # Nontrend: Michael's rule — all patterns disabled on Nontrend days.
    # Flag NONTREND_DISABLE_ALL (default OFF). When ON, blocks ALL fires (S2+S4,
    # both directions). The selectivity comes from location (DAYTYPE_POSITION_GATE)
    # + LSMA+CVD (DIRECTION_LSMA_VETO), NOT from per-pattern day-type matrices.
    if day_type == "Nontrend":
        if os.environ.get("NONTREND_DISABLE_ALL", "0").lower() in ("1", "true", "yes"):
            return (False, "Nontrend — all patterns disabled (Michael rule)")
        return (True, "Nontrend (NONTREND_DISABLE_ALL off — defer)")

    # Normal: fade VA edges — LONG only near VAL, SHORT only near VAH
    if day_type == "Normal":
        return _decide_normal(dir_upper, entry_price, tpo_ctx)

    # Variation: WITH IB expansion only
    if day_type == "Variation":
        return _decide_variation(dir_upper, entry_price, tpo_ctx)

    # Neutral_Center / Neutral_Extreme: fade VA edges, LOCATION-gated like Normal —
    # SHORT only above POC, LONG only below POC. The ZONE decides the side (NOT "both
    # sides all day"). The day is balanced, but you still fade the correct edge toward
    # value. Michael 2026-06-22.
    if day_type in ("Neutral_Center", "Neutral_Extreme"):
        ok, why = _decide_normal(dir_upper, entry_price, tpo_ctx)
        return (ok, why.replace("Normal:", day_type + ":"))

    # Trend_Normal / Trend_DD: WITH trend only (from IB expansion direction)
    if day_type in ("Trend_Normal", "Trend_DD"):
        return _decide_trend(dir_upper, day_type, tpo_ctx)

    return (True, f"unknown day_type={day_type} (fail-open)")


def _decide_normal(
    direction: str,
    entry_price: Optional[float],
    tpo_ctx: Optional[Dict],
) -> Tuple[bool, str]:
    """Normal day: LONG below POC, SHORT above POC."""
    if tpo_ctx is None or entry_price is None:
        return (True, "Normal: missing tpo/entry (fail-open)")

    poc = tpo_ctx.get("poc")
    if poc is None:
        return (True, "Normal: missing POC (fail-open)")

    try:
        entry = float(entry_price)
        poc_f = float(poc)
    except (TypeError, ValueError):
        return (True, "Normal: non-numeric (fail-open)")

    if direction == "LONG" and entry > poc_f:
        return (False, f"Normal: LONG entry={entry:.2f} > POC={poc_f:.2f} (above value — wrong side)")
    if direction == "SHORT" and entry < poc_f:
        return (False, f"Normal: SHORT entry={entry:.2f} < POC={poc_f:.2f} (below value — wrong side)")

    return (True, f"Normal: {direction} at correct side of POC={poc_f:.2f}")


def _decide_variation(
    direction: str,
    entry_price: Optional[float],
    tpo_ctx: Optional[Dict],
) -> Tuple[bool, str]:
    """Variation: only WITH the IB expansion.

    If price is above IBH → IB expanded up → LONG allowed, SHORT blocked.
    If price is below IBL → IB expanded down → SHORT allowed, LONG blocked.
    If inside IB → allow both (expansion not yet clear).
    """
    if tpo_ctx is None or entry_price is None:
        return (True, "Variation: missing tpo/entry (fail-open)")

    ibh = tpo_ctx.get("ib_high")
    ibl = tpo_ctx.get("ib_low")
    if ibh is None or ibl is None:
        return (True, "Variation: missing IB (fail-open)")

    try:
        entry = float(entry_price)
        ibh_f = float(ibh)
        ibl_f = float(ibl)
    except (TypeError, ValueError):
        return (True, "Variation: non-numeric (fail-open)")

    # Above IBH → expansion up
    if entry > ibh_f:
        if direction == "SHORT":
            return (False, f"Variation: SHORT entry={entry:.2f} > IBH={ibh_f:.2f} (against upward expansion)")
        return (True, f"Variation: LONG with upward expansion (entry > IBH)")

    # Below IBL → expansion down
    if entry < ibl_f:
        if direction == "LONG":
            return (False, f"Variation: LONG entry={entry:.2f} < IBL={ibl_f:.2f} (against downward expansion)")
        return (True, f"Variation: SHORT with downward expansion (entry < IBL)")

    # Inside IB → expansion direction not yet clear
    return (True, f"Variation: entry inside IB (expansion not yet determined)")


def _decide_trend(
    direction: str,
    day_type: str,
    tpo_ctx: Optional[Dict],
) -> Tuple[bool, str]:
    """Trend_Normal / Trend_DD: WITH trend direction only.

    Trend direction from IB expansion: if session_high > IBH (uptrend) → LONG only.
    If session_low < IBL (downtrend) → SHORT only.
    Both broken → allow both. Neither → fail-open.
    """
    if tpo_ctx is None:
        return (True, f"{day_type}: missing tpo (fail-open)")

    ibh = tpo_ctx.get("ib_high")
    ibl = tpo_ctx.get("ib_low")
    session_high = tpo_ctx.get("session_high") or tpo_ctx.get("rth_high")
    session_low = tpo_ctx.get("session_low") or tpo_ctx.get("rth_low")

    if ibh is None or ibl is None:
        return (True, f"{day_type}: missing IB (fail-open)")

    try:
        ibh_f = float(ibh)
        ibl_f = float(ibl)
    except (TypeError, ValueError):
        return (True, f"{day_type}: non-numeric IB (fail-open)")

    broke_up = session_high is not None and float(session_high) > ibh_f
    broke_down = session_low is not None and float(session_low) < ibl_f

    # Both broken → balanced extension, allow both
    if broke_up and broke_down:
        return (True, f"{day_type}: both IB edges broken (allow both)")

    # Only up broken → LONG only
    if broke_up and not broke_down:
        if direction == "SHORT":
            return (False, f"{day_type}: SHORT against upward trend (IBH broken, IBL intact)")
        return (True, f"{day_type}: LONG with upward trend")

    # Only down broken → SHORT only
    if broke_down and not broke_up:
        if direction == "LONG":
            return (False, f"{day_type}: LONG against downward trend (IBL broken, IBH intact)")
        return (True, f"{day_type}: SHORT with downward trend")

    # Neither broken yet → fail-open (trend not yet established)
    return (True, f"{day_type}: IB not yet broken (fail-open)")
