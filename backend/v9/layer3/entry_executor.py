"""Layer 3: Entry Execution Logic.

Given a setup from Layer 1 (system signal) + Layer 2 (quality/confluence),
this module determines the exact entry, stop, and target levels using
tick-reversal bar microstructure (cluster + empty zone analysis).

Entry rule (Zohar): enter above cluster (LONG) / below cluster (SHORT).
Stop rule: place stop at empty zone (gap in volume).
Targets: per Day Type playbook (from System A / Day Type Engine).
"""

from typing import Optional, List
from pydantic import BaseModel
from backend.v9.layer3.cluster import Cluster, PriceLevel, identify_cluster
from backend.v9.layer3.empty_zone import EmptyZone, identify_empty_zones


class EntryPlan(BaseModel):
    """Complete entry plan for a trade setup."""
    direction: str             # "LONG" or "SHORT"
    entry_price: float         # above cluster (LONG) / below cluster (SHORT)
    stop_price: float          # empty zone level
    stop_distance_pt: float    # entry - stop (always positive)
    risk_r: float = 1.0        # normalized risk unit

    # Targets (from Day Type playbook)
    t1_price: Optional[float] = None
    t1_r: Optional[float] = None
    t2_price: Optional[float] = None
    t2_r: Optional[float] = None
    t3_price: Optional[float] = None
    t3_r: Optional[float] = None

    # Sizing (from Day Type playbook)
    contracts: int = 1
    sizing_label: str = "FULL"  # FULL, HALF, MIN

    # Context
    cluster_poc: float = 0.0
    cluster_density: float = 0.0
    empty_zone_width_pt: float = 0.0
    confidence: float = 0.0


class TargetConfig(BaseModel):
    """Per-day-type target configuration."""
    t1_r: float = 1.0
    t2_r: Optional[float] = None
    t3_r: Optional[float] = None
    time_stop_min: Optional[int] = None
    sizing: str = "FULL"
    contracts: int = 1


# Default target configs per day type (from spec Section C3)
DAY_TYPE_TARGETS = {
    "Trend_Normal": TargetConfig(t1_r=1.0, t2_r=2.0, t3_r=4.0, sizing="FULL", contracts=2),
    "Trend_DD":     TargetConfig(t1_r=1.0, t2_r=2.5, t3_r=4.0, sizing="FULL", contracts=2),
    "Variation":    TargetConfig(t1_r=1.0, t2_r=2.5, time_stop_min=60, sizing="FULL", contracts=2),
    "Normal":       TargetConfig(t1_r=1.0, t2_r=2.0, time_stop_min=30, sizing="HALF", contracts=1),
    "Neutral_Extreme": TargetConfig(t1_r=0.75, time_stop_min=45, sizing="HALF", contracts=1),
    "Neutral_Center":  TargetConfig(t1_r=0.75, time_stop_min=30, sizing="HALF", contracts=1),
    "Neutral":         TargetConfig(t1_r=0.75, time_stop_min=30, sizing="HALF", contracts=1),  # DEPRECATED
    "Nontrend":        TargetConfig(t1_r=0.5, time_stop_min=20, sizing="MIN", contracts=1),
}


def compute_entry_plan(
    direction: str,
    levels: List[PriceLevel],
    bar_total_vol: float,
    day_type: str = "Variation",
    tick_size: float = 0.25,
    entry_offset_ticks: int = 2,
    min_stop_ticks: int = 4,
    max_stop_ticks: int = 15,
) -> Optional[EntryPlan]:
    """Compute entry/stop/targets from bar microstructure.

    Args:
        direction: "LONG" or "SHORT"
        levels: footprint price levels from the reversal bar
        bar_total_vol: total volume of the bar
        day_type: current day type classification (for targets)
        tick_size: MES tick size (0.25)
        entry_offset_ticks: ticks above/below cluster for entry
        min_stop_ticks: minimum stop distance
        max_stop_ticks: maximum stop distance
    """
    cluster = identify_cluster(levels, bar_total_vol)
    if cluster is None:
        return None

    empty_zones = identify_empty_zones(
        levels, bar_total_vol, threshold_pct=0.05, min_consecutive=2, tick_size=tick_size,
    )

    # Entry: above cluster high (LONG) / below cluster low (SHORT)
    offset = entry_offset_ticks * tick_size
    if direction == "LONG":
        entry = cluster.cluster_high + offset
        # Stop: nearest empty zone BELOW entry, or cluster_low - offset
        stop_candidates = [ez.zone_low for ez in empty_zones if ez.zone_low < entry]
        if stop_candidates:
            stop = max(stop_candidates)  # closest empty zone below
        else:
            stop = cluster.cluster_low - offset
    elif direction == "SHORT":
        entry = cluster.cluster_low - offset
        # Stop: nearest empty zone ABOVE entry, or cluster_high + offset
        stop_candidates = [ez.zone_high for ez in empty_zones if ez.zone_high > entry]
        if stop_candidates:
            stop = min(stop_candidates)  # closest empty zone above
        else:
            stop = cluster.cluster_high + offset
    else:
        return None

    stop_dist = abs(entry - stop)

    # Enforce min/max stop distance
    min_dist = min_stop_ticks * tick_size
    max_dist = max_stop_ticks * tick_size
    if stop_dist < min_dist:
        stop_dist = min_dist
        stop = entry - min_dist if direction == "LONG" else entry + min_dist
    if stop_dist > max_dist:
        stop_dist = max_dist
        stop = entry - max_dist if direction == "LONG" else entry + max_dist

    # Targets per day type
    targets = DAY_TYPE_TARGETS.get(day_type, DAY_TYPE_TARGETS["Variation"])

    t1_price = None
    t2_price = None
    t3_price = None
    sign = 1.0 if direction == "LONG" else -1.0

    if targets.t1_r is not None:
        t1_price = round(entry + sign * targets.t1_r * stop_dist, 2)
    if targets.t2_r is not None:
        t2_price = round(entry + sign * targets.t2_r * stop_dist, 2)
    if targets.t3_r is not None:
        t3_price = round(entry + sign * targets.t3_r * stop_dist, 2)

    ez_width = empty_zones[0].zone_width_pt if empty_zones else 0.0

    return EntryPlan(
        direction=direction,
        entry_price=round(entry, 2),
        stop_price=round(stop, 2),
        stop_distance_pt=round(stop_dist, 2),
        t1_price=t1_price,
        t1_r=targets.t1_r,
        t2_price=t2_price,
        t2_r=targets.t2_r,
        t3_price=t3_price,
        t3_r=targets.t3_r,
        contracts=targets.contracts,
        sizing_label=targets.sizing,
        cluster_poc=cluster.yellow_poc,
        cluster_density=cluster.density,
        empty_zone_width_pt=ez_width,
        confidence=cluster.density,  # density as confidence proxy
    )
