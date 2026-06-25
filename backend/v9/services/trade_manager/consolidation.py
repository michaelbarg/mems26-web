"""Consolidation detector — pure function for dynamic structure-trailing.

Detects a NEW CONSOLIDATION (balance/congestion zone) in the trade's favor:
≥ K bars whose total range ≤ R, occurring AFTER price advanced ≥ M in the
trade direction since the last anchor.

Michael's rule (2026-06-24): "new place = a new CONSOLIDATION — NOT a single
swing bar, NOT value-migration. A few bars that balance in a tight range
after price advanced."

All parameters (K, R, M) are tunable via config/stop_anchors.yaml.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def detect_consolidation(
    *,
    bars: List[Dict[str, Any]],
    direction: str,
    last_anchor_price: float,
    entry_price: float,
    initial_risk: float,
    min_bars: int = 3,
    max_range_atr_frac: float = 0.5,
    min_advance_risk_mult: float = 1.0,
    atr_14: Optional[float] = None,
    range_floor_pts: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """Detect a new consolidation zone in the trade direction.

    Args:
        bars: chronological price bars since entry (each has 'high', 'low', 'close').
        direction: "LONG" or "SHORT".
        last_anchor_price: the stop price or last consolidation edge (the reference
            point — price must have ADVANCED beyond this to form a new consolidation).
        entry_price: original entry price.
        initial_risk: |entry - initial_stop| in price points.
        min_bars: K — minimum bars in the consolidation zone (default 3).
        max_range_atr_frac: R — max range as fraction of ATR-14 (default 0.5).
        min_advance_risk_mult: M — min advance (in risk multiples) since last anchor
            before a consolidation counts (default 1.0).
        atr_14: ATR-14 in price points (for range threshold). If None, uses range_floor_pts.
        range_floor_pts: absolute floor for range threshold (points).

    Returns:
        dict with {zone_high, zone_low, anchor_extreme, bar_span, advance} if found,
        None otherwise.
    """
    if not bars or len(bars) < min_bars:
        return None
    if initial_risk <= 0:
        return None

    dir_upper = direction.upper()
    min_advance = min_advance_risk_mult * initial_risk

    # Compute max allowed consolidation range
    if atr_14 and atr_14 > 0:
        max_range = max(max_range_atr_frac * atr_14, range_floor_pts)
    else:
        max_range = range_floor_pts

    # Scan from the end of the bar list backward to find the most recent
    # consolidation zone (K consecutive bars with range ≤ max_range, after advance)
    n = len(bars)

    # Find the furthest point price reached in the trade direction (the advance)
    if dir_upper == "LONG":
        best_price = max(float(b["high"]) for b in bars)
        advance = best_price - last_anchor_price
    else:
        best_price = min(float(b["low"]) for b in bars)
        advance = last_anchor_price - best_price

    if advance < min_advance:
        return None  # price hasn't advanced enough since last anchor

    # Scan backward: find K consecutive bars whose combined range ≤ max_range
    # AND that are AFTER the advance (i.e., the consolidation is recent, near the best price)
    for start in range(n - min_bars, -1, -1):
        window = bars[start:start + min_bars]
        zone_high = max(float(b["high"]) for b in window)
        zone_low = min(float(b["low"]) for b in window)
        zone_range = zone_high - zone_low

        if zone_range > max_range:
            continue

        # The zone must be IN the trade's favor direction (not back near entry)
        if dir_upper == "LONG":
            # Zone must be above last_anchor (progress)
            if zone_low <= last_anchor_price:
                continue
            anchor_extreme = zone_low  # stop goes just below the zone
        else:
            if zone_high >= last_anchor_price:
                continue
            anchor_extreme = zone_high  # stop goes just above the zone

        return {
            "zone_high": zone_high,
            "zone_low": zone_low,
            "anchor_extreme": anchor_extreme,
            "bar_span": min_bars,
            "advance": round(advance, 2),
            "zone_range": round(zone_range, 2),
        }

    return None


def next_target_from_levels(
    *,
    direction: str,
    current_price: float,
    zone_projection: Optional[float],
    key_levels: List[float],
) -> Optional[float]:
    """Pick the next target = the EARLIER (closer) of zone projection and key levels.

    Args:
        direction: "LONG" or "SHORT".
        current_price: the current close (reference for distance).
        zone_projection: projected target from the consolidation zone (zone range added
            to the breakout edge). None if no projection.
        key_levels: list of structural levels (POC, VAH, VAL, IB edges, PDH, PDL) that
            are IN the trade direction (already filtered).

    Returns:
        The nearest level in the trade direction, or None if no candidates.
    """
    candidates = []

    if zone_projection is not None:
        if direction == "LONG" and zone_projection > current_price:
            candidates.append(zone_projection)
        elif direction == "SHORT" and zone_projection < current_price:
            candidates.append(zone_projection)

    for lvl in key_levels:
        if direction == "LONG" and lvl > current_price:
            candidates.append(lvl)
        elif direction == "SHORT" and lvl < current_price:
            candidates.append(lvl)

    if not candidates:
        return None

    # "Earlier" = closest to current price in the trade direction
    if direction == "LONG":
        return min(candidates)
    else:
        return max(candidates)
