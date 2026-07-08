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
) -> Tuple[Dict, List[str]]:
    """Clamp t1/t2/t3 beyond the IB edge to the edge, on non-traveling days.

    Returns (setup, clamp_notes). Mutates a COPY of the target keys only.
    """
    notes: List[str] = []
    direction = str(setup.get("direction") or "").upper()
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
            setup[k] = float(edge)
            notes.append(f"{k} {tv} → IB-edge {edge} ({day_type} does not travel beyond IB)")
    if notes:
        logger.info("[TargetClamp] TP-1 applied (%s %s): %s", direction, day_type, "; ".join(notes))
    return setup, notes
