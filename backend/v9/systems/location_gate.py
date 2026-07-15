"""location_gate — DAYTYPE_LOCATION_GATE v1 (Michael 2026-07-15, default OFF).

Dalton doctrine enforcement the audit found MISSING end-to-end: direction must
match LOCATION per day type. The playbook's `daytype_style` block documented it
but nothing read it; #372 (07-14) bought the VAH ceiling on a Variation day and
no gate objected.

v1 scope — sharp and minimal (the #372 class):
  On ROTATION days (Variation / Normal / Neutral_*), RESPONSIVE (REV) patterns
  may fire ONLY at the correct value edge, in the fade direction:
    LONG  → near-VAL or stretched below value (buying the floor)
    SHORT → near-VAH or stretched above value (selling the ceiling)
  Everything else for REV on those days is blocked: mid-range fades and
  counter-location entries (LONG@VAH — the #372 trade — or SHORT@VAL).

  CONT patterns are untouched (with-expansion/with-trend is enforced by
  require_with_trend + cont_trend_filter). Trend days are untouched (family
  gate owns REV there). Missing levels/entry → fail-open with reason.

Zone tolerance: 0.25 × IB width (floor 1pt, cap 4pt) around each level.
Flag: DAYTYPE_LOCATION_GATE (default OFF). Pure functions, no I/O.
"""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

_ROTATION_PREFIXES = ("Variation", "Normal_Variation", "Normal", "Neutral")


def _tol(ib_width: Optional[float]) -> float:
    try:
        if ib_width and float(ib_width) > 0:
            return min(max(0.25 * float(ib_width), 1.0), 4.0)
    except (TypeError, ValueError):
        pass
    return 2.0


def zone_of(entry: float, vah: float, val: float, ib_width: Optional[float]) -> str:
    """Classify entry location relative to the value area."""
    t = _tol(ib_width)
    if entry >= vah + t:
        return "above_value"        # stretched above — responsive SHORT territory
    if entry >= vah - t:
        return "near_vah"
    if entry <= val - t:
        return "below_value"        # stretched below — responsive LONG territory
    if entry <= val + t:
        return "near_val"
    return "mid_value"


def decide_location(
    *,
    family: Optional[str],
    direction: str,
    day_type: Optional[str],
    entry_price: Optional[float],
    levels: Optional[Dict],
) -> Tuple[bool, str]:
    """(allow, reason). Fail-open on missing data — never a synthetic block."""
    if os.getenv("DAYTYPE_LOCATION_GATE", "0").lower() not in ("1", "true", "yes"):
        return (True, "location gate OFF")
    if family != "REV":
        return (True, f"family {family or '?'} — location v1 gates REV only")
    dt = str(day_type or "")
    if not dt.startswith(_ROTATION_PREFIXES):
        return (True, f"{dt or 'unknown day'} — not a rotation day (family gate owns REV there)")
    try:
        e = float(entry_price)
        vah = float((levels or {}).get("vah"))
        val = float((levels or {}).get("val"))
    except (TypeError, ValueError):
        return (True, "levels/entry missing (fail-open)")
    if vah <= val:
        return (True, "degenerate VA (fail-open)")

    z = zone_of(e, vah, val, (levels or {}).get("ib_width"))
    d = direction.upper()
    if d == "LONG" and z in ("near_val", "below_value"):
        return (True, f"fade LONG at the floor ({z}) — doctrine-correct")
    if d == "SHORT" and z in ("near_vah", "above_value"):
        return (True, f"fade SHORT at the ceiling ({z}) — doctrine-correct")
    return (False,
            f"{dt}: {d} fade at {z} — wrong location (LONG only at VAL-side, "
            f"SHORT only at VAH-side; the #372 class)")
