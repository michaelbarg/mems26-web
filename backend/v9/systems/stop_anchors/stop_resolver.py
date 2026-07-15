"""Stop Resolver V1 — structural stop band enforcement.

Flag: STOP_RESOLVER_V1 (default OFF, SHADOW).

Band: floor 0.5×ATR_5m, cap 1.2×ATR CONT / 1.5×ATR REV, hard-cap 25pt.
Rule: walk the per-pattern rung ladder from nearest to farthest. Pick the
first rung whose distance (edge ±3T) falls within the band. Too close →
next rung out. All above cap → no_stop_in_band (reject). No synthetic levels.

Per-pattern ladders from CC_PATTERN_ECONOMICS_PACKAGE_2026-07-02.md §4:
  REACTIVE:       b3_low → b2_low → w4 zone
  INITIATIVE:     breakout_bar → b2_low → broken_level ±3T
  BULL/BEAR_FLAG: breakout_bar → lowest/highest bar in the accumulation
  VEGAS:          entry_bar → handle_edge → cup_extreme
  GHOST:          entry_bar → right_shoulder → head
  FAMIR:          fail_bar → stage3_edge → stage1_extreme
  ZLR/TLB/TT/GB100: current anchor (single rung)
  HTLB:           consolidation_extreme (single rung)
  DBDT/HNS:       current anchor (single rung)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

TICK = 0.25


@dataclass
class StopResolverResult:
    stop_price: float
    risk_points: float
    rung_index: int         # which rung was selected (0-based)
    rung_name: str          # human label ("breakout_bar", "b2_low", etc.)
    floor_pts: float
    cap_pts: float
    in_band: bool           # True if within [floor, cap]
    rejected: bool          # True if no rung fits the band


def resolve_stop(
    *,
    direction: str,
    entry_price: float,
    rungs: List[float],
    rung_names: List[str],
    atr_5m: float,
    family: str = "CONT",
    offset_ticks: int = 3,
    day_type: Optional[str] = None,
) -> StopResolverResult:
    """Walk the rung ladder and pick the first within the band.

    Args:
        direction: "LONG" or "SHORT"
        entry_price: the trade entry price
        rungs: price levels from nearest to farthest (bar extremes, NOT offset)
        rung_names: human labels for each rung (same length as rungs)
        atr_5m: live ATR in POINTS (not ticks)
        family: "CONT" or "REV" (drives the cap multiplier)
        offset_ticks: structural offset beyond each rung (default 3T = 0.75pt)
    """
    offset = offset_ticks * TICK
    # 07-15 Michael decision 5/6: DYNAMIC floor by day type. On rotation days
    # (Variation / Neutral_*) a 0.5×ATR stop sits inside the noise — trade #372
    # (07-14) got a 6pt stop on ATR 10.8 and died in 3 minutes. Rotation floor
    # = STOP_FLOOR_ROTATION_ATR (default 0.8×ATR); trend/other days keep 0.5
    # (continuation entries legitimately hug structure). Cap unchanged.
    _floor_mult = 0.5
    _dt = (day_type or "").strip()
    if _dt.startswith(("Variation", "Normal_Variation", "Neutral")):
        try:
            _floor_mult = float(os.getenv("STOP_FLOOR_ROTATION_ATR", "0.8"))
        except (TypeError, ValueError):
            _floor_mult = 0.8
    floor_pts = max(_floor_mult * atr_5m, 1.0)  # at least 1pt
    cap_mult = 1.5 if family == "REV" else 1.2
    cap_pts = min(cap_mult * atr_5m, 25.0)  # hard cap 25pt

    for i, (rung, name) in enumerate(zip(rungs, rung_names)):
        if rung is None or rung <= 0:
            continue
        # Defensive (property-test finding 2026-07-03): a stop must sit on the
        # PROTECTIVE side of entry. Skip a rung on the target side (LONG stop
        # must be below entry; SHORT above) so a mis-supplied ladder can never
        # yield a stop on the wrong side of the trade.
        if direction == "LONG" and rung >= entry_price:
            continue
        if direction == "SHORT" and rung <= entry_price:
            continue
        # Apply structural offset
        if direction == "LONG":
            stop = rung - offset
        else:
            stop = rung + offset

        dist = abs(entry_price - stop)

        if dist < floor_pts:
            # Too close → try next rung
            logger.debug("[StopResolver] rung %d (%s) dist=%.2f < floor=%.2f → skip",
                         i, name, dist, floor_pts)
            continue

        if dist > cap_pts:
            # Too far → reject (all remaining will be farther)
            logger.info("[StopResolver] rung %d (%s) dist=%.2f > cap=%.2f → no_stop_in_band",
                        i, name, dist, cap_pts)
            return StopResolverResult(
                stop_price=stop, risk_points=dist,
                rung_index=i, rung_name=name,
                floor_pts=floor_pts, cap_pts=cap_pts,
                in_band=False, rejected=True,
            )

        # In band — use this rung
        # Snap to grid
        stop = round(round(stop / TICK) * TICK, 2)
        dist = abs(entry_price - stop)
        logger.info("[StopResolver] selected rung %d (%s) stop=%.2f dist=%.2f (band [%.1f, %.1f])",
                    i, name, stop, dist, floor_pts, cap_pts)
        return StopResolverResult(
            stop_price=stop, risk_points=dist,
            rung_index=i, rung_name=name,
            floor_pts=floor_pts, cap_pts=cap_pts,
            in_band=True, rejected=False,
        )

    # No rungs provided or all skipped (below floor)
    logger.warning("[StopResolver] no valid rung in band → rejected")
    return StopResolverResult(
        stop_price=entry_price, risk_points=0,
        rung_index=-1, rung_name="none",
        floor_pts=floor_pts, cap_pts=cap_pts,
        in_band=False, rejected=True,
    )
