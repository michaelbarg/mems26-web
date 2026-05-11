"""Layer 3: Cluster Identification — per tick-reversal bar.

Clusters are dense volume zones within a bar that indicate where the
market fought and resolved (Zohar's methodology).

- Yellow POC: single price level with max volume
- Primary cluster: 3 consecutive price levels with highest total volume
- Density: total cluster volume / total bar volume
"""

from typing import List, Optional
from pydantic import BaseModel


class PriceLevel(BaseModel):
    """Single price level with bid/ask volume."""
    price: float
    bid_vol: float = 0.0
    ask_vol: float = 0.0

    @property
    def total_vol(self) -> float:
        return self.bid_vol + self.ask_vol

    @property
    def delta(self) -> float:
        return self.ask_vol - self.bid_vol


class Cluster(BaseModel):
    """Identified cluster zone within a bar."""
    yellow_poc: float           # single level with max volume
    yellow_poc_vol: float       # volume at POC level
    cluster_high: float         # top of 3-level cluster
    cluster_low: float          # bottom of 3-level cluster
    cluster_vol: float          # total volume in cluster
    cluster_delta: float        # net delta in cluster (ask - bid)
    density: float              # cluster_vol / bar_vol (0-1)
    dominant_side: str          # "BUY" if delta > 0, "SELL" if < 0, "NEUTRAL"
    levels: List[PriceLevel]    # the cluster levels (sorted by price)


def identify_cluster(
    levels: List[PriceLevel],
    bar_total_vol: float = 0.0,
) -> Optional[Cluster]:
    """Identify the primary cluster in a list of price levels.

    Args:
        levels: price levels with bid/ask volume (from footprint or distribution)
        bar_total_vol: total bar volume (for density calculation)

    Returns:
        Cluster object, or None if levels empty
    """
    if not levels:
        return None

    # Sort by price (ascending)
    sorted_levels = sorted(levels, key=lambda lv: lv.price)
    n = len(sorted_levels)

    if bar_total_vol <= 0:
        bar_total_vol = sum(lv.total_vol for lv in sorted_levels)
    if bar_total_vol <= 0:
        return None

    # Yellow POC: level with max total volume
    poc_level = max(sorted_levels, key=lambda lv: lv.total_vol)

    # Primary cluster: best 3 consecutive levels by total volume
    best_start = 0
    best_vol = 0.0
    window_size = min(3, n)

    for i in range(n - window_size + 1):
        window_vol = sum(sorted_levels[i + j].total_vol for j in range(window_size))
        if window_vol > best_vol:
            best_vol = window_vol
            best_start = i

    cluster_levels = sorted_levels[best_start:best_start + window_size]
    cluster_delta = sum(lv.delta for lv in cluster_levels)
    density = best_vol / bar_total_vol if bar_total_vol > 0 else 0.0

    if cluster_delta > 0:
        dominant = "BUY"
    elif cluster_delta < 0:
        dominant = "SELL"
    else:
        dominant = "NEUTRAL"

    return Cluster(
        yellow_poc=poc_level.price,
        yellow_poc_vol=poc_level.total_vol,
        cluster_high=cluster_levels[-1].price,
        cluster_low=cluster_levels[0].price,
        cluster_vol=best_vol,
        cluster_delta=cluster_delta,
        density=round(density, 4),
        dominant_side=dominant,
        levels=cluster_levels,
    )
