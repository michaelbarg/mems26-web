"""FAILED_BREAK — entry after a failed attempt to break an edge.

Michael 26.08: "לזהות מתי המחיר נמצא בקיצון, לא מצליח לעבור אותו, ואז חוזר חזרה."

Sequence:
  1. ATTEMPT: bar trades beyond the edge (high > edge for SHORT fade, etc.)
  2. FAILURE: no acceptance (not 2 closes beyond), closes back inside
  3. RETURN: close inside value → candidate FAILED_BREAK
     Stop: beyond the failed extreme (the high/low of the attempt)
     Targets: POC → opposite edge

Three edge variants:
  A: VAH/VAL (value area edges)
  B: Session high/low (excess-style)
  C: IB edges

Zero percentage thresholds. All geometric. Pure function.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def _f(bar: Dict, *keys: str) -> Optional[float]:
    for k in keys:
        v = bar.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def detect_failed_break(
    bars: List[Dict[str, Any]],
    edge_high: float,
    edge_low: float,
    *,
    edge_label: str = "VA",
    already_fired: Optional[Set[str]] = None,
    min_bars: int = 12,
    stop_offset: float = 1.5,
    stop_cap: float = 12.0,
) -> Optional[Dict[str, Any]]:
    """Detect a failed break at the edges. Returns trigger or None.

    The THREE-STEP sequence on the LAST two bars:
      bar[-2]: ATTEMPT — probed beyond edge (high > edge_high or low < edge_low)
      bar[-1]: FAILURE+RETURN — closed back inside (no acceptance, back in value)
    """
    if len(bars) < max(min_bars, 3):
        return None
    fired = already_fired or set()

    prev = bars[-2]  # the attempt bar
    curr = bars[-1]  # the failure/return bar

    ph = _f(prev, "h", "high")
    pl = _f(prev, "l", "low")
    ch = _f(curr, "h", "high")
    cl = _f(curr, "l", "low")
    cc = _f(curr, "c", "close")
    co = _f(curr, "o", "open")
    if None in (ph, pl, ch, cl, cc, co):
        return None

    bar_rng = ch - cl
    if bar_rng <= 0:
        return None
    close_pos = (cc - cl) / bar_rng

    poc = (edge_high + edge_low) / 2.0

    # ── UPPER failed break → SHORT ──
    # Attempt: prev bar probed above edge_high
    # Failure: current bar did NOT make a new high beyond prev, AND closed below edge_high
    # Return: close is inside value (below edge_high)
    if (f"FB_HIGH_{edge_label}" not in fired
            and ph > edge_high                      # attempt: probed above
            and ch <= ph                            # failure: no new extreme
            and cc < edge_high                      # return: closed inside
            and close_pos < 0.5):                   # rejection bar: close in lower half
        extreme = ph  # the failed extreme
        stop = min(extreme + stop_offset, cc + stop_cap)
        return {
            "type": f"FB_HIGH_{edge_label}",
            "direction": "SHORT",
            "entry": round(cc, 2),
            "stop": round(stop, 2),
            "edge_high": round(edge_high, 2),
            "edge_low": round(edge_low, 2),
            "poc": round(poc, 2),
            "failed_extreme": round(extreme, 2),
            "target_poc": round(poc, 2),
            "target_opposite": round(edge_low, 2),
        }

    # ── LOWER failed break → LONG ──
    if (f"FB_LOW_{edge_label}" not in fired
            and pl < edge_low                       # attempt: probed below
            and cl >= pl                            # failure: no new low
            and cc > edge_low                       # return: closed inside
            and close_pos > 0.5):                   # rejection: close in upper half
        extreme = pl
        stop = max(extreme - stop_offset, cc - stop_cap)
        return {
            "type": f"FB_LOW_{edge_label}",
            "direction": "LONG",
            "entry": round(cc, 2),
            "stop": round(stop, 2),
            "edge_high": round(edge_high, 2),
            "edge_low": round(edge_low, 2),
            "poc": round(poc, 2),
            "failed_extreme": round(extreme, 2),
            "target_poc": round(poc, 2),
            "target_opposite": round(edge_high, 2),
        }

    return None


def build_failed_break_setup(trigger: Dict[str, Any],
                              contracts: int = 3) -> Dict[str, Any]:
    """Build a gateway-routable setup."""
    entry = float(trigger["entry"])
    stop = float(trigger["stop"])
    direction = trigger["direction"]
    risk = abs(entry - stop)
    sign = 1.0 if direction == "LONG" else -1.0
    # Michael ruling 26.08: "יעד POC, לא קצה-נגדי" — only 7/87 reach opposite edge.
    # T1 = POC. T2 = 2R (structured extension, not opposite edge).
    t1 = float(trigger["target_poc"])
    if (direction == "LONG" and t1 <= entry) or (direction == "SHORT" and t1 >= entry):
        t1 = entry + sign * 1.0 * risk
    t2 = entry + sign * 2.0 * risk
    pat = f"FAILED_BREAK_{direction}"
    return {
        "firing_system": 2,
        "pattern": pat,
        "classification": pat,
        "direction": direction,
        "entry_price": round(entry, 2),
        "stop": round(stop, 2),
        "t1": round(t1, 2),
        "t2": round(t2, 2),
        "t3": None,
        "metadata": {
            "pattern": pat,
            "source": "failed_break_v1",
            "edge_label": trigger.get("type", ""),
            "failed_extreme": trigger.get("failed_extreme"),
            "shadow_only": True,
        },
    }
