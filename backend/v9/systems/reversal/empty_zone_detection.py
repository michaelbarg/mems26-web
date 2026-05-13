"""Empty zone detection for reversal bars per Constitution V3 D-047.

Empty zone = low-volume area adjacent to the cluster, used for stop placement.
  - Levels below cluster with volume < threshold
  - Single print zones
  - Gap in footprint

Threshold default: 20% of cluster volume (to calibrate in SHADOW).
"""

from typing import Dict, List, Optional
import json


# Calibration constant — percentage of cluster volume below which a level is "empty"
EMPTY_THRESHOLD_PCT = 0.20  # 🟡 default — calibrate in SHADOW


def identify_empty_zone(bar: dict, cluster: dict) -> Optional[Dict]:
    """Find empty zone (low-volume area) adjacent to cluster.

    For LONG setups: empty zone below cluster -> stop goes here.
    For SHORT setups: empty zone above cluster -> stop goes here.

    Args:
        bar: Raw bar dict with volume_per_price or footprint_json.
        cluster: Output from identify_cluster().

    Returns:
        Dict with empty_zone_top, empty_zone_bottom, empty_zone_volume
        or None if no empty zone found.
    """
    if not cluster:
        return None

    vol_per_price = _extract_volume_profile(bar)
    if not vol_per_price:
        return None

    threshold = cluster["cluster_volume"] * EMPTY_THRESHOLD_PCT

    # Find all low-volume prices
    low_vol_prices = sorted(
        [p for p, v in vol_per_price.items() if v < threshold]
    )

    if not low_vol_prices:
        return None

    # Find empty zone below cluster (for LONG stop placement)
    below = [p for p in low_vol_prices if p < cluster["cluster_bottom"]]
    above = [p for p in low_vol_prices if p > cluster["cluster_top"]]

    best_zone = None

    if below:
        runs = _find_contiguous_runs(below)
        widest = max(runs, key=lambda r: len(r))
        zone_vol = sum(vol_per_price.get(p, 0) for p in widest)
        best_zone = {
            "empty_zone_top": max(widest),
            "empty_zone_bottom": min(widest),
            "empty_zone_volume": zone_vol,
            "side": "below",
        }

    if above:
        runs = _find_contiguous_runs(above)
        widest = max(runs, key=lambda r: len(r))
        zone_vol = sum(vol_per_price.get(p, 0) for p in widest)
        above_zone = {
            "empty_zone_top": max(widest),
            "empty_zone_bottom": min(widest),
            "empty_zone_volume": zone_vol,
            "side": "above",
        }
        # Prefer below (LONG stop) but return above if no below zone
        if best_zone is None:
            best_zone = above_zone
        else:
            # Return both via the wider one
            if len(widest) > (best_zone["empty_zone_top"] - best_zone["empty_zone_bottom"]):
                best_zone = above_zone

    return best_zone


def _find_contiguous_runs(prices: List[float]) -> List[List[float]]:
    """Group sorted prices into contiguous runs (within tick tolerance)."""
    if not prices:
        return []

    # Infer tick size from minimum price gap
    if len(prices) >= 2:
        gaps = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
        tick = min(g for g in gaps if g > 0) if any(g > 0 for g in gaps) else 0.25
    else:
        tick = 0.25

    runs: List[List[float]] = [[prices[0]]]
    for i in range(1, len(prices)):
        if prices[i] - prices[i - 1] <= tick * 1.5:
            runs[-1].append(prices[i])
        else:
            runs.append([prices[i]])
    return runs


def _extract_volume_profile(bar: dict) -> Optional[Dict[float, float]]:
    """Extract price -> volume mapping from bar data."""
    vpp = bar.get("volume_per_price")
    if vpp and isinstance(vpp, dict):
        return {float(k): float(v) for k, v in vpp.items()}

    fp_raw = bar.get("footprint_json")
    if fp_raw:
        try:
            fp = json.loads(fp_raw) if isinstance(fp_raw, str) else fp_raw
            if isinstance(fp, dict):
                return {float(k): float(v.get("vol", v.get("volume", 0)))
                        if isinstance(v, dict) else float(v)
                        for k, v in fp.items()}
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return None
