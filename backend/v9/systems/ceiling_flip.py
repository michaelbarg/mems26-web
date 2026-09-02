"""CEILING_FLIP_SHORT_V1 — reverse entry on double ceiling/floor failure.

Michael ruling T-140 (02.09 12:25): "כניסה הפוכה על סגירת הנגיעה-השנייה"
— the FAST variant, at the second touch bar, not at the neckline break.

When CEILING_FAILED fires at an edge:
  → SHORT entry at the confirm bar close
  → Stop above max(P1, P2) + 0.2×ATR (cap 1.5×ATR)
  → T1 = POC, T2 = opposite edge (VAL for ceiling, VAH for floor)

FLOOR_FAILED is the exact mirror → LONG.

Pure function. The caller (five_min_system or bar_level_detector) does
the flag check and the route_setup. This module never touches Sierra.

Consumer file:line: five_min_system.py:_maybe_ceiling_floor_state
(reads ceiling_floor_state, passes to this function).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def build_flip_setup(
    *,
    ceiling_floor: Dict[str, Any],
    atr: float,
    poc: Optional[float] = None,
    opposite_edge: Optional[float] = None,
    contracts: int = 3,
) -> Optional[Dict[str, Any]]:
    """Build a gateway-routable setup for the reverse entry.

    Args:
        ceiling_floor: the result dict from detect_ceiling_floor.
        atr: ATR-14 for relative thresholds.
        poc: POC price for T1 target.
        opposite_edge: VAL (for ceiling flip) or VAH (for floor flip) for T2.
        contracts: from effective_contracts.

    Returns setup dict or None if inputs are insufficient.
    """
    state = ceiling_floor.get("state")
    if state not in ("CEILING_FAILED", "FLOOR_FAILED"):
        return None

    p1 = ceiling_floor.get("p1")
    p2 = ceiling_floor.get("p2")
    confirm_close = ceiling_floor.get("confirm_close")
    signal_bar_ts = ceiling_floor.get("signal_bar_ts")

    if None in (p1, p2, confirm_close, atr) or atr <= 0:
        return None

    p1, p2, confirm_close = float(p1), float(p2), float(confirm_close)

    if state == "CEILING_FAILED":
        direction = "SHORT"
        entry = confirm_close
        extreme = max(p1, p2)
        stop_raw = extreme + 0.2 * atr
        stop_cap = entry + 1.5 * atr
        stop = round(min(stop_raw, stop_cap), 2)
        t1 = round(float(poc), 2) if poc is not None else round(entry - 1.0 * abs(entry - stop), 2)
        t2 = round(float(opposite_edge), 2) if opposite_edge is not None else round(entry - 2.0 * abs(entry - stop), 2)
    else:  # FLOOR_FAILED
        direction = "LONG"
        entry = confirm_close
        extreme = min(p1, p2)
        stop_raw = extreme - 0.2 * atr
        stop_cap = entry - 1.5 * atr
        stop = round(max(stop_raw, stop_cap), 2)
        t1 = round(float(poc), 2) if poc is not None else round(entry + 1.0 * abs(entry - stop), 2)
        t2 = round(float(opposite_edge), 2) if opposite_edge is not None else round(entry + 2.0 * abs(entry - stop), 2)

    # Sanity: target must be on the correct side of entry
    if direction == "SHORT" and (t1 >= entry or t2 >= entry):
        t1 = round(entry - abs(entry - stop), 2)
        t2 = round(entry - 2 * abs(entry - stop), 2)
    if direction == "LONG" and (t1 <= entry or t2 <= entry):
        t1 = round(entry + abs(entry - stop), 2)
        t2 = round(entry + 2 * abs(entry - stop), 2)

    pat = f"CEILING_FLIP_{direction}"
    return {
        "firing_system": 2,
        "pattern": pat,
        "classification": pat,
        "direction": direction,
        "entry_price": round(entry, 2),
        "stop": stop,
        "t1": t1,
        "t2": t2,
        "t3": None,
        "metadata": {
            "pattern": pat,
            "source": "ceiling_flip_v1",
            "ceiling_floor_state": state,
            "p1": p1,
            "p2": p2,
            "edge_source": ceiling_floor.get("edge_source"),
            "confirm_level": ceiling_floor.get("confirm_level"),
            "shadow_only": True,  # always shadow until promoted
        },
    }
