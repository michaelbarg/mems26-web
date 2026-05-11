"""Layer 3: Empty Zone Identification — per tick-reversal bar.

Empty zones are price levels where volume is significantly below average,
indicating price moved quickly through without trading. These represent:
- Support/resistance gaps (fast moves)
- Single prints (only one TPO letter)
- Potential stop placement zones (Zohar methodology)
"""

from typing import List, Optional
from pydantic import BaseModel
from backend.v9.layer3.cluster import PriceLevel


class EmptyZone(BaseModel):
    """Identified empty zone within a bar."""
    zone_high: float       # top of empty zone
    zone_low: float        # bottom of empty zone
    zone_width_pt: float   # zone_high - zone_low
    avg_vol_pct: float     # average volume in zone as % of bar avg
    is_single_print: bool  # only 1 TPO letter touched
    levels: List[PriceLevel]


def identify_empty_zones(
    levels: List[PriceLevel],
    bar_total_vol: float = 0.0,
    threshold_pct: float = 0.05,
    min_consecutive: int = 2,
    tick_size: float = 0.25,
) -> List[EmptyZone]:
    """Identify empty zones in a list of price levels.

    Args:
        levels: price levels with volume data
        bar_total_vol: total bar volume
        threshold_pct: max volume as fraction of average to count as empty
        min_consecutive: minimum consecutive empty levels to form a zone
        tick_size: price increment for width calculation

    Returns:
        List of EmptyZone objects, sorted by price
    """
    if not levels or len(levels) < 3:
        return []

    sorted_levels = sorted(levels, key=lambda lv: lv.price)
    n = len(sorted_levels)

    if bar_total_vol <= 0:
        bar_total_vol = sum(lv.total_vol for lv in sorted_levels)
    if bar_total_vol <= 0:
        return []

    avg_vol_per_level = bar_total_vol / n
    vol_threshold = avg_vol_per_level * threshold_pct

    # Find consecutive runs of low-volume levels
    zones: List[EmptyZone] = []
    run_start: Optional[int] = None

    for i in range(n):
        is_empty = sorted_levels[i].total_vol <= vol_threshold

        if is_empty:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None and (i - run_start) >= min_consecutive:
                zone_levels = sorted_levels[run_start:i]
                zone_avg_pct = (
                    sum(lv.total_vol for lv in zone_levels) / len(zone_levels)
                ) / avg_vol_per_level if avg_vol_per_level > 0 else 0.0

                zones.append(EmptyZone(
                    zone_high=zone_levels[-1].price,
                    zone_low=zone_levels[0].price,
                    zone_width_pt=zone_levels[-1].price - zone_levels[0].price,
                    avg_vol_pct=round(zone_avg_pct, 4),
                    is_single_print=all(lv.total_vol <= tick_size for lv in zone_levels),
                    levels=zone_levels,
                ))
            run_start = None

    # Handle trailing run
    if run_start is not None and (n - run_start) >= min_consecutive:
        zone_levels = sorted_levels[run_start:]
        zone_avg_pct = (
            sum(lv.total_vol for lv in zone_levels) / len(zone_levels)
        ) / avg_vol_per_level if avg_vol_per_level > 0 else 0.0

        zones.append(EmptyZone(
            zone_high=zone_levels[-1].price,
            zone_low=zone_levels[0].price,
            zone_width_pt=zone_levels[-1].price - zone_levels[0].price,
            avg_vol_pct=round(zone_avg_pct, 4),
            is_single_print=all(lv.total_vol <= tick_size for lv in zone_levels),
            levels=zone_levels,
        ))

    return zones
