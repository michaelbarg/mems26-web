"""location_gate — DAYTYPE_LOCATION_GATE v2 (Michael 2026-07-22, default OFF).

v1 (2026-07-15): On ROTATION days (Variation / Normal / Neutral_*), RESPONSIVE
(REV) patterns may fire ONLY at the correct value edge (LONG@VAL, SHORT@VAH).
Blocks mid-range fades and counter-location entries (#372 class). CONT on
Variation must go WITH detected expansion.

v2 additions (פסיקת-מייקל 2026-07-21 22:18 + 2026-07-22 B1):
  - **Probe requirement:** REV at the correct edge is allowed ONLY after a
    mechanical probe — a 5-min bar that penetrated the edge (High >= VAH for
    SHORT / Low <= VAL for LONG) AND closed back inside (Close < VAH / Close >
    VAL). Without probe = BLOCK. Evidence: #449/#452/#456 (mid-value, no probe)
    BLOCKED; 19:55 VAH probe → SHORT allowed.
  - **S4 passes full gate** (no exemption — already confirmed in v1 code path).
  - **mid-value counter-expansion = BLOCK always** (already in v1 CONT path).

Zone tolerance: 0.25 × IB width (floor 1pt, cap 4pt) around each level.
Flag: DAYTYPE_LOCATION_GATE (default OFF). Pure functions, no I/O.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

_ROTATION_PREFIXES = ("Variation", "Normal_Variation", "Normal", "Neutral")


def probe_detected(
    direction: str,
    vah: float,
    val: float,
    recent_bars: Optional[List[Dict]] = None,
) -> Tuple[bool, str]:
    """Check if a recent bar probed the target edge and was rejected.

    Probe = bar penetrated the level AND closed back inside:
      SHORT@VAH: any bar with High >= VAH and Close < VAH
      LONG@VAL:  any bar with Low  <= VAL and Close > VAL
    Returns (found, description).
    """
    if not recent_bars:
        return (False, "no bars available")
    d = direction.upper()
    for i, bar in enumerate(recent_bars):
        try:
            h, l, c = float(bar["high"]), float(bar["low"]), float(bar["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if d == "SHORT" and h >= vah and c < vah:
            return (True, f"bar[{i}] probed VAH (H={h:.2f}>=VAH={vah:.2f}, C={c:.2f}<VAH) — rejected")
        if d == "LONG" and l <= val and c > val:
            return (True, f"bar[{i}] probed VAL (L={l:.2f}<=VAL={val:.2f}, C={c:.2f}>VAL) — rejected")
    return (False, f"no bar probed {'VAH' if d == 'SHORT' else 'VAL'} with rejection close")


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
    expansion: Optional[Dict] = None,
    recent_bars: Optional[List[Dict]] = None,
) -> Tuple[bool, str]:
    """(allow, reason). Fail-open on missing data — never a synthetic block.

    expansion: the CANONICAL live expansion {"dir","ref"} from
    get_live_expansion() (volume-accepted reference break, P0-1-v2) — or None.
    recent_bars: recent 5-min bars [{"high","low","close"}, ...] for probe check (v2)."""
    if os.getenv("DAYTYPE_LOCATION_GATE", "0").lower() not in ("1", "true", "yes"):
        return (True, "location gate OFF")
    if family == "CONT":
        # 07-15 (Michael: "לוודא שהמערכת תדע לזהות הרחבה"): on Variation days a
        # continuation must go WITH the detected expansion. When the canonical
        # accepted-break exists and the CONT direction opposes it → block.
        # No expansion signal → fail-open (the LSMA-color proxy in
        # require_with_trend still applies downstream).
        dt_ = str(day_type or "")
        _want_dir = "UP" if direction.upper() == "LONG" else "DOWN"
        if (dt_.startswith(("Variation", "Normal_Variation"))
                and expansion and expansion.get("dir") in ("UP", "DOWN")
                and _want_dir != expansion["dir"]):
            return (False,
                    f"{dt_}: CONT {direction.upper()} against detected expansion "
                    f"{expansion['dir']} ({expansion.get('ref')}) — continuation must go WITH expansion")
        return (True, f"CONT — {'with/no' if not expansion else 'with'} expansion")
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
    # v1: wrong location → immediate block
    if d == "LONG" and z not in ("near_val", "below_value"):
        return (False,
                f"{dt}: {d} fade at {z} — wrong location (LONG only at VAL-side, "
                f"SHORT only at VAH-side; the #372 class)")
    if d == "SHORT" and z not in ("near_vah", "above_value"):
        return (False,
                f"{dt}: {d} fade at {z} — wrong location (LONG only at VAL-side, "
                f"SHORT only at VAH-side; the #372 class)")
    # v2 (2026-07-22): correct edge — require probe (bar penetrated edge + closed back)
    probed, probe_reason = probe_detected(d, vah, val, recent_bars)
    if not probed:
        return (False,
                f"{dt}: {d} at correct edge ({z}) but no probe — "
                f"{probe_reason}; entry requires prior level-test rejection")
    return (True, f"fade {d} at {z} after probe — doctrine-correct ({probe_reason})")
