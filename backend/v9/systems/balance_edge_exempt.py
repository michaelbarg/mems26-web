"""Balance-edge direction_context exemption (P1-4, Dalton).

When regime=BALANCE and price is at the rotation/VA edge with a rejection
signature, exempt the trade from the direction_context gate. The rationale:
at the edge of a balanced rotation, a rejection IS the trade — the
direction_context gate (which blocks counter-trend fires) shouldn't
prevent taking this setup.

Flag: BALANCE_EDGE_EXEMPT_V1 (default OFF). Build → replay → ruling.

Case study: 06.08 — direction_context blocked 2 shorts at the exact
rotation edge (7758-59) that would have been profitable.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def should_exempt(
    *,
    direction: str,
    entry_price: float,
    day_type: Optional[str] = None,
    regime: Optional[str] = None,
    extremes: Optional[Dict[str, Any]] = None,
    balance7: Optional[Dict[str, Any]] = None,
    session_high: Optional[float] = None,
    session_low: Optional[float] = None,
) -> tuple:
    """Check if a trade at the balance edge should be exempt from direction_context.

    Returns (should_exempt: bool, reason: str or None).
    """
    if os.getenv("BALANCE_EDGE_EXEMPT_V1", "0").lower() not in ("1", "true", "yes"):
        return False, None

    # Must be a balance regime
    if regime not in ("BALANCE", "TRANSITIONAL"):
        return False, None

    # Check if price is at session rotation edge
    dir_up = direction.upper() == "LONG"
    at_edge = False
    edge_reason = None

    # Check session extremes
    if dir_up and session_low is not None:
        dist = entry_price - session_low
        if dist <= 2.0:  # within 2pt of session low
            at_edge = True
            edge_reason = f"at session low ({session_low:.2f}, dist {dist:.1f}pt)"
    elif not dir_up and session_high is not None:
        dist = session_high - entry_price
        if dist <= 2.0:
            at_edge = True
            edge_reason = f"at session high ({session_high:.2f}, dist {dist:.1f}pt)"

    # Also check balance7 value area edges
    if not at_edge and balance7:
        b7_value = balance7.get("value") or []
        if len(b7_value) >= 2:
            val, vah = float(b7_value[0]), float(b7_value[1])
            if dir_up and abs(entry_price - val) <= 3.0:
                at_edge = True
                edge_reason = f"at balance7 VAL ({val:.2f})"
            elif not dir_up and abs(entry_price - vah) <= 3.0:
                at_edge = True
                edge_reason = f"at balance7 VAH ({vah:.2f})"

    if not at_edge:
        return False, None

    # Check for rejection signature (EXCESS at the edge)
    has_rejection = False
    if extremes:
        if dir_up and extremes.get("low_quality") == "EXCESS":
            has_rejection = True
            edge_reason += " + EXCESS low"
        elif not dir_up and extremes.get("high_quality") == "EXCESS":
            has_rejection = True
            edge_reason += " + EXCESS high"

    # At edge is enough for exemption (rejection is a bonus)
    reason = f"balance-edge exempt: {edge_reason}" + (" (confirmed)" if has_rejection else " (edge-only)")
    return True, reason
