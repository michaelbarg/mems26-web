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

# ── Pattern-family map (OPENING_FIRE_CVD_V1 / DAYTYPE_PATTERN_AWARE_V1) ──────
# CONT = continuation patterns (with-trend / with-expansion)
# REV  = reversal / fade patterns (counter-trend / fade-edges)
# Unknown pattern → None (no family gate, fail-open).
_CONT_PATTERNS = frozenset({
    "INITIATIVE", "INITIATIVE_LONG", "INITIATIVE_SHORT",
    "BULL_FLAG", "BULL_FLAG_LONG", "BEAR_FLAG", "BEAR_FLAG_SHORT",
    "ZLR", "TLB", "TT", "GB100",
    # S2×S4 combined pattern (spec CONFLUENCE_PATTERN_SPEC_2026-07-17.md §4.2:
    # group CONT — the ZLR leg gives continuation momentum; unknown=fail-open
    # is not acceptable for a new pattern).
    "CONFLUENCE_RI_ZLR",
})
_REV_PATTERNS_BASE = frozenset({
    "REACTIVE", "REACTIVE_LONG", "REACTIVE_SHORT",
    "INVERSE_HNS", "INVERSE_HNS_LONG", "HNS_TOP", "HNS_TOP_SHORT",
    "DOUBLE_BOTTOM_EE", "DOUBLE_BOTTOM_EE_LONG",
    "DOUBLE_TOP_AA", "DOUBLE_TOP_AA_SHORT",
    "VEGAS", "GHOST", "FAMIR", "HTLB", "HFE",
})
# Root 2 (3ROOTS 25.08): PATTERN_FAMILY_DELTA_DBL_V1 — add S2_DELTA_DBL
# to the reversal family. Without this, the pattern is invisible to the
# position gate and playbook (105/108 gateway blocks are on this pattern).
# Flag OFF = same as today (unmapped → None → fail-open FULL).
_DELTA_DBL_PATTERNS = frozenset({
    "S2_DELTA_DBL", "S2_DELTA_DBL_LONG", "S2_DELTA_DBL_SHORT",
})
_REV_PATTERNS = (
    _REV_PATTERNS_BASE | _DELTA_DBL_PATTERNS
    if os.environ.get("PATTERN_FAMILY_DELTA_DBL_V1", "0").lower() in ("1", "true", "yes")
    else _REV_PATTERNS_BASE
)

# Day-types grouped by family allowance
_BALANCED_DAYTYPES = frozenset({"Normal", "Neutral_Center", "Neutral_Extreme"})
_TREND_DAYTYPES = frozenset({"Trend_Normal", "Trend_DD"})


def _pattern_family(pattern: Optional[str]) -> Optional[str]:
    """Map a pattern name to CONT / REV / None."""
    if not pattern:
        return None
    p = pattern.strip()
    if p in _CONT_PATTERNS:
        return "CONT"
    if p in _REV_PATTERNS:
        return "REV"
    # Try stripping _LONG / _SHORT suffix
    for suffix in ("_LONG", "_SHORT"):
        if p.endswith(suffix):
            base = p[: -len(suffix)]
            if base in _CONT_PATTERNS or (base + suffix) in _CONT_PATTERNS:
                return "CONT"
            if base in _REV_PATTERNS or (base + suffix) in _REV_PATTERNS:
                return "REV"
    return None


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

    # ── DAYTYPE_PATTERN_AWARE_V1: family gate (CONT vs REV by day-type) ────────
    # Post-IB-lock: balanced days → REV only; trend/variation → CONT only.
    # Unknown pattern → no family gate (fall through to location logic).
    # Flag OFF → skip (pattern ignored, byte-identical to before).
    if os.environ.get("DAYTYPE_PATTERN_AWARE_V1", "0").lower() in ("1", "true", "yes"):
        family = _pattern_family(pattern)
        if family is not None:
            if day_type in _BALANCED_DAYTYPES and family == "CONT":
                return (False, f"balanced day ({day_type}) — continuation ({pattern}) blocked")
            if day_type in _TREND_DAYTYPES and family == "REV":
                return (False, f"trend day ({day_type}) — reversal ({pattern}) blocked")
            # 07-15 Michael doctrine ruling: Variation REV is ALLOWED — a
            # Variation day finds new value then ROTATES around VAH/VAL/POC,
            # so responsive fades at the edges are the doctrine play there
            # (the old "CONT only" line was the exact inversion that let
            # 07-14's wrong-side LONG through while the location gate was
            # off AND would have blocked correct fades once enabled).
            # WHERE the fade is allowed (only at the edges, never mid-range)
            # is the LOCATION logic below / DAYTYPE_LOCATION_GATE spec.
            # Allowed family → fall through to existing location logic

    # Nontrend: Michael's rule — all patterns disabled on Nontrend days.
    # Flag NONTREND_DISABLE_ALL (default OFF). When ON, blocks ALL fires (S2+S4,
    # both directions). The selectivity comes from location (DAYTYPE_POSITION_GATE)
    # + LSMA+CVD (DIRECTION_LSMA_VETO), NOT from per-pattern day-type matrices.
    if day_type == "Nontrend":
        if os.environ.get("NONTREND_DISABLE_ALL", "0").lower() in ("1", "true", "yes"):
            return (False, "Nontrend — all patterns disabled (Michael rule)")
        return (True, "Nontrend (NONTREND_DISABLE_ALL off — defer)")

    # P1-8 Nonconviction (Dalton pp.300-302): no OTF footprints → no reference
    # points → NO trades, unconditionally. The label only exists when
    # S1_NONCONVICTION_V1 is ON (classifier-side), so no second flag here.
    if day_type == "Nonconviction":
        return (False, "Nonconviction — no OTF footprints, stand aside (Dalton pp.300-302)")

    # Normal: fade VA edges — LONG only near VAL, SHORT only near VAH
    if day_type == "Normal":
        return _decide_normal(dir_upper, entry_price, tpo_ctx, pattern=pattern)

    # Variation: WITH IB expansion only
    if day_type == "Variation":
        return _decide_variation(dir_upper, entry_price, tpo_ctx)

    # Neutral_Center / Neutral_Extreme: fade VA edges, LOCATION-gated like Normal —
    # SHORT only above POC, LONG only below POC. The ZONE decides the side (NOT "both
    # sides all day"). The day is balanced, but you still fade the correct edge toward
    # value. Michael 2026-06-22.
    if day_type in ("Neutral_Center", "Neutral_Extreme"):
        ok, why = _decide_normal(dir_upper, entry_price, tpo_ctx, pattern=pattern)
        return (ok, why.replace("Normal:", day_type + ":"))

    # Trend_Normal / Trend_DD: WITH trend only (from IB expansion direction)
    if day_type in ("Trend_Normal", "Trend_DD"):
        return _decide_trend(dir_upper, day_type, tpo_ctx)

    return (True, f"unknown day_type={day_type} (fail-open)")


# Minimum VA width (pts) for levels to be considered valid. Below this the
# profile is degenerate/frozen (e.g. 06-29 VA≈6pt vs IB≈80pt).
_VA_WIDTH_FLOOR = 8.0
# Tolerance for VA-edge gating (pts): REACTIVE SHORT allowed at VAH − tol.
_VA_EDGE_TOL = 2.0


def _tpo_degenerate(tpo_ctx: Dict) -> bool:
    """True when the TPO levels are degenerate (frozen/stale profile).

    Degenerate = VA width < floor, OR VAH ≈ VAL ≈ POC (all collapsed).
    """
    vah = tpo_ctx.get("vah")
    val = tpo_ctx.get("val")
    poc = tpo_ctx.get("poc")
    if vah is None or val is None:
        return False  # missing is handled by the caller's fail-open
    try:
        vah_f, val_f = float(vah), float(val)
    except (TypeError, ValueError):
        return False
    va_width = vah_f - val_f
    if va_width < _VA_WIDTH_FLOOR:
        return True
    # All three collapsed to the same value
    if poc is not None:
        try:
            poc_f = float(poc)
            if abs(vah_f - poc_f) < 1.0 and abs(val_f - poc_f) < 1.0:
                return True
        except (TypeError, ValueError):
            pass
    return False


def _decide_normal(
    direction: str,
    entry_price: Optional[float],
    tpo_ctx: Optional[Dict],
    *,
    pattern: Optional[str] = None,
) -> Tuple[bool, str]:
    """Normal day: LONG below POC, SHORT above POC.

    When DAYTYPE_PATTERN_AWARE_V1 is ON:
      - Degenerate TPO (VA < 8pt or collapsed) → fail-open.
      - REV patterns gated on VA EDGE (VAH/VAL) instead of strict POC.
      - CONT patterns keep POC gating.
    """
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

    _flag_on = os.environ.get("DAYTYPE_PATTERN_AWARE_V1", "0").lower() in ("1", "true", "yes")

    # Change A: degenerate TPO guard
    if _flag_on and _tpo_degenerate(tpo_ctx):
        logger.warning("[daytype_gate] degenerate TPO (VA < %.0f pt or collapsed) — fail-open", _VA_WIDTH_FLOOR)
        return (True, "Normal: degenerate TPO levels (fail-open)")

    # Change B: REV patterns gated on VA edge (VAH/VAL), not strict POC
    if _flag_on and _pattern_family(pattern) == "REV":
        vah = tpo_ctx.get("vah")
        val = tpo_ctx.get("val")
        if vah is not None and val is not None:
            try:
                vah_f, val_f = float(vah), float(val)
            except (TypeError, ValueError):
                return (True, "Normal: non-numeric VAH/VAL (fail-open)")
            if direction == "SHORT" and entry < vah_f - _VA_EDGE_TOL:
                return (False, f"Normal: SHORT entry={entry:.2f} < VAH={vah_f:.2f}−{_VA_EDGE_TOL} (not at upper edge)")
            if direction == "LONG" and entry > val_f + _VA_EDGE_TOL:
                return (False, f"Normal: LONG entry={entry:.2f} > VAL={val_f:.2f}+{_VA_EDGE_TOL} (not at lower edge)")
            return (True, f"Normal: {direction} at VA edge (VAH={vah_f:.2f}, VAL={val_f:.2f})")
        # Missing VAH/VAL → fall through to POC logic

    # Default: strict POC gating (CONT, unknown, or flag OFF)
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
