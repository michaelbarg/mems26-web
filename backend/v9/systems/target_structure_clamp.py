"""TP-1 — targets live inside the day structure (Michael ruling 2026-07-08).

Live incident (trade 310): INITIATIVE_LONG on a Variation day carried
T1 +12.75 / T2 +46.75 — deep beyond IB-High. Michael: "the odds of realization
beyond IB-H are lowest unless it's a NEUTRAL day — a serious fault that can
cost a lot of money."

Rule (TRADING_SPEC TP-1): a target beyond the IB edge in the trade direction is
CLAMPED to the IB edge, unless the day type plausibly travels there:
  · Neutral_* — both-side extensions occur (rotation touches beyond IB)
  · Trend_Normal / Trend_DD — confirmed extension runs
Pure function; flag-gated at the gateway (TARGET_STRUCTURE_CLAMP_V1, default OFF).
Fail-safe: missing IB/day_type → no clamping (honest pass-through).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Day types where beyond-IB targets are structurally plausible
BEYOND_IB_ALLOWED = {"Neutral_Center", "Neutral_Extreme", "Trend_Normal", "Trend_DD"}


def clamp_targets_to_ib(
    setup: Dict,
    *,
    day_type: Optional[str],
    ib_high: Optional[float],
    ib_low: Optional[float],
    ib_locked: bool = True,
) -> Tuple[Dict, List[str]]:
    """Clamp t1/t2/t3 beyond the IB edge to the edge, on non-traveling days.

    Returns (setup, clamp_notes). Mutates a COPY of the target keys only.

    FIX-2 (incident 333):
    - ib_locked=False → passthrough (IB still forming, edge is unreliable).
    - Sanity: clamped target must remain beyond entry in the trade direction.
      LONG edge <= entry or SHORT edge >= entry → skip clamp for that target
      (otherwise the target ends up on the wrong side → phantom fills).
    """
    notes: List[str] = []
    direction = str(setup.get("direction") or "").upper()

    # FIX-2a: pre-IB-lock → no clamping (IB edge = running session high/low, unreliable)
    if not ib_locked:
        notes.append("ib_forming_no_clamp")
        return setup, notes

    if day_type in BEYOND_IB_ALLOWED or day_type is None:
        return setup, notes
    if direction == "LONG":
        edge = ib_high
    elif direction == "SHORT":
        edge = ib_low
    else:
        return setup, notes
    if edge is None:
        return setup, notes  # honest missing — never synthesize a structure

    entry = setup.get("entry_price")
    try:
        entry_f = float(entry) if entry is not None else None
    except (TypeError, ValueError):
        entry_f = None

    for k in ("t1", "t2", "t3"):
        tv = setup.get(k)
        if tv is None:
            continue
        try:
            tv = float(tv)
        except (TypeError, ValueError):
            continue
        beyond = tv > float(edge) if direction == "LONG" else tv < float(edge)
        if beyond:
            # FIX-2b: sanity — clamped target must stay beyond entry
            if entry_f is not None:
                if direction == "LONG" and float(edge) <= entry_f + 0.25:
                    notes.append(
                        f"{k} clamp SKIPPED: IB-edge {edge} <= entry {entry_f} "
                        f"(would place target on wrong side)")
                    logger.warning(
                        "[TargetClamp] SKIP %s: edge %.2f <= entry %.2f + 0.25 "
                        "(wrong-side clamp, %s)", k, float(edge), entry_f, direction)
                    continue
                if direction == "SHORT" and float(edge) >= entry_f - 0.25:
                    notes.append(
                        f"{k} clamp SKIPPED: IB-edge {edge} >= entry {entry_f} "
                        f"(would place target on wrong side)")
                    logger.warning(
                        "[TargetClamp] SKIP %s: edge %.2f >= entry %.2f - 0.25 "
                        "(wrong-side clamp, %s)", k, float(edge), entry_f, direction)
                    continue
            setup[k] = float(edge)
            notes.append(f"{k} {tv} → IB-edge {edge} ({day_type} does not travel beyond IB)")
    if notes:
        logger.info("[TargetClamp] TP-1 applied (%s %s): %s", direction, day_type, "; ".join(notes))
    return setup, notes
