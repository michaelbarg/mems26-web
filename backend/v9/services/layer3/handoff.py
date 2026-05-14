"""W2b.3 — Setup→Entry Handoff (refines signal_price → cluster-based).

Per Constitution V3 D-047: Setup identified by Layer 1 (T1/T2/T3) →
wait for matching 15-tick reversal bar → entry above cluster (LONG) /
below cluster (SHORT) → stop = empty zone.

Wraps existing backend.v9.layer3 modules (cluster, empty_zone, entry_executor).
"""
import logging
from typing import Dict, List, Optional

from backend.v9.layer3.cluster import PriceLevel, identify_cluster
from backend.v9.layer3.empty_zone import identify_empty_zones
from backend.v9.layer3.entry_executor import compute_entry_plan

logger = logging.getLogger(__name__)

TICK_SIZE = 0.25  # MES


def refine_entry(
    setup: Dict,
    reversal_bar: Dict,
    footprint_cells: List[Dict],
    day_type: str = "Variation",
) -> Optional[Dict]:
    """Refine a firing system's signal_price into cluster-based entry/stop.

    Args:
        setup: dict with direction, signal_price, system_id, signal_strength
        reversal_bar: latest reversal bar dict (OHLC + timestamp)
        footprint_cells: list of {price, bid_volume/bid_vol, ask_volume/ask_vol}
        day_type: current day type classification for targets

    Returns:
        Refined entry dict or None if no valid cluster/empty zone.
        None = explicit reject (no silent fallback per §6.7).
    """
    direction = setup.get("direction")
    if direction not in ("LONG", "SHORT"):
        logger.warning("[Layer3] refine_entry: invalid direction=%s", direction)
        return None  # noqa: explicit-reject

    # Convert footprint cells to PriceLevel objects
    levels = []
    for cell in footprint_cells:
        price = cell.get("price", cell.get("p", 0))
        bid = float(cell.get("bid_volume", cell.get("bid_vol", cell.get("bid", 0))) or 0)
        ask = float(cell.get("ask_volume", cell.get("ask_vol", cell.get("ask", 0))) or 0)
        if price > 0:
            levels.append(PriceLevel(price=price, bid_vol=bid, ask_vol=ask))

    if not levels:
        logger.info("[Layer3] refine_entry: no footprint cells, rejecting setup")
        return None  # noqa: explicit-reject

    bar_vol = sum(lv.total_vol for lv in levels)

    plan = compute_entry_plan(
        direction=direction,
        levels=levels,
        bar_total_vol=bar_vol,
        day_type=day_type,
        tick_size=TICK_SIZE,
    )

    if plan is None:
        logger.info("[Layer3] refine_entry: no valid entry plan (no cluster)")
        return None  # noqa: explicit-reject

    # Build cluster/empty zone for response
    cluster = identify_cluster(levels, bar_vol)
    empty_zones = identify_empty_zones(levels, bar_vol)

    reasoning = (
        f"Layer3 {direction}: entry={plan.entry_price} (above cluster {cluster.cluster_low}-{cluster.cluster_high}), "
        f"stop={plan.stop_price}, POC={cluster.yellow_poc}, density={cluster.density:.2f}, "
        f"day_type={day_type}, sizing={plan.sizing_label}"
    ) if cluster else f"Layer3 {direction}: entry={plan.entry_price} stop={plan.stop_price}"

    logger.info("[Layer3] %s", reasoning)

    return {
        "entry_price": plan.entry_price,
        "stop_price": plan.stop_price,
        "t1_price": plan.t1_price,
        "t2_price": plan.t2_price,
        "t3_price": plan.t3_price,
        "cluster_top": cluster.cluster_high if cluster else None,
        "cluster_bottom": cluster.cluster_low if cluster else None,
        "cluster_poc": cluster.yellow_poc if cluster else None,
        "empty_zone_top": empty_zones[0].zone_high if empty_zones else None,
        "empty_zone_bottom": empty_zones[0].zone_low if empty_zones else None,
        "entry_bar_type": "reversal_15",
        "entry_method": f"cluster_{'above' if direction == 'LONG' else 'below'}",
        "contracts": plan.contracts,
        "sizing_label": plan.sizing_label,
        "reasoning_notes": reasoning,
    }
