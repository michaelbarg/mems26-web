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


def probe_level(
    direction: str,
    level: float,
    bars: Optional[List[Dict]] = None,
    touch_tol: float = 0.5,
    reject_min: Optional[float] = None,
) -> Tuple[bool, str]:
    """Generalized probe against an arbitrary level (day-structure edges,
    Michael ruling 2026-07-22 'מאשר'): a bar TOUCHED/pierced the level
    (within touch_tol) and CLOSED back on the safe side.
      LONG@edge:  Low <= level + touch_tol and Close > level + reject_min
      SHORT@edge: High >= level - touch_tol and Close < level - reject_min
    reject_min: how far beyond the level the rejection close must clear.
    Default = touch_tol (0.5). 07-23 calibration (32-session study): relaxing
    to >0 was worth +8.3R — env PROBE_REJECT_MIN_PTS tunes it (sim first)."""
    if not bars:
        return (False, "no bars available")
    if reject_min is None:
        try:
            reject_min = float(os.getenv("PROBE_REJECT_MIN_PTS", str(touch_tol)))
        except (TypeError, ValueError):
            reject_min = touch_tol
    d = direction.upper()
    for i, bar in enumerate(bars):
        try:
            h, l, c = float(bar["high"]), float(bar["low"]), float(bar["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if d == "LONG" and l <= level + touch_tol and c > level + reject_min:
            return (True, f"bar[{i}] probed {level:.2f} (L={l:.2f}, C={c:.2f}>lvl+{reject_min:g}) — rejected")
        if d == "SHORT" and h >= level - touch_tol and c < level - reject_min:
            return (True, f"bar[{i}] probed {level:.2f} (H={h:.2f}, C={c:.2f}<lvl-{reject_min:g}) — rejected")
    return (False, f"no bar probed {level:.2f} with rejection close")


def day_structure_edge(
    direction: str,
    entry: float,
    stop_price: Optional[float],
    levels: Dict,
    tol: float,
) -> Optional[Tuple[str, float]]:
    """Michael ruling 07-22 ('מאשר', extending 'קצה' beyond prior-day value):
    is the trade AT a day-structure edge? Candidate edges for LONG = day_low /
    ib_low / open_low; for SHORT = day_high / ib_high / open_high. 'At' = entry
    OR the stop (the structure proxy — it sits just beyond the pattern's
    anchor) within tol of the level. Returns (edge_name, level) or None."""
    d = direction.upper()
    names = ("day_low", "ib_low", "open_low") if d == "LONG" else \
            ("day_high", "ib_high", "open_high")
    for name in names:
        lv = levels.get(name)
        try:
            lv = float(lv)
        except (TypeError, ValueError):
            continue
        if abs(entry - lv) <= tol:
            return (name, lv)
        if stop_price is not None:
            try:
                if abs(float(stop_price) - lv) <= tol:
                    return (name, lv)
            except (TypeError, ValueError):
                pass
    return None


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
    stop_price: Optional[float] = None,
    session_bars: Optional[List[Dict]] = None,
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
    _t = _tol((levels or {}).get("ib_width"))
    # v1: wrong location by VALUE edges → before blocking, check DAY-STRUCTURE
    # edges (Michael ruling 2026-07-22 'מאשר': a day that bases above value
    # never touches VAL — the 07-21 double-bottom at day-low 7521.5 had no
    # armed edge. Edge = also day_low/high, ib_low/high, open extreme — WITH
    # the same probe requirement, against THAT level). Flag-gated; fail-open
    # only into the ORIGINAL block (never allows without probe).
    if (d == "LONG" and z not in ("near_val", "below_value")) or \
       (d == "SHORT" and z not in ("near_vah", "above_value")):
        if os.getenv("REV_EDGE_DAY_STRUCTURE_V1", "0").lower() in ("1", "true", "yes"):
            _edge = day_structure_edge(d, e, stop_price, levels or {}, _t)
            if _edge:
                _ename, _elvl = _edge
                _pbars = session_bars or recent_bars
                _p_ok, _p_why = probe_level(d, _elvl, _pbars)
                if _p_ok:
                    return (True,
                            f"fade {d} at day-structure edge {_ename}={_elvl:.2f} "
                            f"after probe — doctrine-correct ({_p_why})")
                return (False,
                        f"{dt}: {d} at day-structure edge {_ename}={_elvl:.2f} "
                        f"but no probe — {_p_why}; entry requires prior level-test rejection")
        return (False,
                f"{dt}: {d} fade at {z} — wrong location (LONG only at VAL-side, "
                f"SHORT only at VAH-side, or day-structure edge w/probe; the #372 class)")
    # v2 (2026-07-22): correct edge — require probe (bar penetrated edge + closed back)
    probed, probe_reason = probe_detected(d, vah, val, recent_bars)
    if not probed:
        return (False,
                f"{dt}: {d} at correct edge ({z}) but no probe — "
                f"{probe_reason}; entry requires prior level-test rejection")
    return (True, f"fade {d} at {z} after probe — doctrine-correct ({probe_reason})")
