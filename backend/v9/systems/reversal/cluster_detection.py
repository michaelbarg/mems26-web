"""Cluster detection for 15-tick reversal bars per Constitution V3 D-047.

Priority order:
  1. Yellow POC of bar (price with max volume) — primary
  2. 3 consecutive price levels with most volume — secondary
  3. Highest bid+ask volume density
"""

from typing import Dict, Optional
import json


def identify_cluster(bar: dict) -> Optional[Dict]:
    """Identify the volume cluster within a reversal bar.

    Args:
        bar: Raw bar dict. Expects either:
             - "volume_per_price": {price_str: volume, ...}
             - "footprint_json": JSON string with per-level volumes
             - "cluster_data": pre-computed JSON (pass through)

    Returns:
        Dict with cluster_top, cluster_bottom, cluster_volume, poc_price
        or None if insufficient volume data.
    """
    vol_per_price = _extract_volume_profile(bar)
    if not vol_per_price:
        return None

    # 1. POC = price level with max volume (Yellow POC)
    poc_price = max(vol_per_price, key=vol_per_price.get)
    poc_volume = vol_per_price[poc_price]

    # 2. Find 3 consecutive prices with highest combined volume
    prices = sorted(vol_per_price.keys())
    if len(prices) < 3:
        # Fewer than 3 levels — cluster is just the POC
        return {
            "cluster_top": poc_price,
            "cluster_bottom": poc_price,
            "cluster_volume": poc_volume,
            "poc_price": poc_price,
        }

    best_start = 0
    best_vol = 0
    for i in range(len(prices) - 2):
        window_vol = sum(vol_per_price[prices[j]] for j in range(i, i + 3))
        if window_vol > best_vol:
            best_vol = window_vol
            best_start = i

    return {
        "cluster_top": prices[best_start + 2],
        "cluster_bottom": prices[best_start],
        "cluster_volume": best_vol,
        "poc_price": poc_price,
    }


def _extract_volume_profile(bar: dict) -> Optional[Dict[float, float]]:
    """Extract price -> volume mapping from bar data."""
    # Direct volume_per_price dict
    vpp = bar.get("volume_per_price")
    if vpp and isinstance(vpp, dict):
        return {float(k): float(v) for k, v in vpp.items()}

    # Footprint JSON (Sierra export format)
    fp_raw = bar.get("footprint_json")
    if fp_raw:
        try:
            fp = json.loads(fp_raw) if isinstance(fp_raw, str) else fp_raw
            if isinstance(fp, dict):
                return {float(k): float(v.get("vol", v.get("volume", 0)))
                        if isinstance(v, dict) else float(v)
                        for k, v in fp.items()}
            if isinstance(fp, list):
                result = {}
                for entry in fp:
                    if isinstance(entry, dict) and "price" in entry:
                        result[float(entry["price"])] = float(
                            entry.get("vol", entry.get("volume", 0)))
                return result if result else None
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Pre-computed cluster_data (pass-through)
    cd_raw = bar.get("cluster_data")
    if cd_raw:
        try:
            cd = json.loads(cd_raw) if isinstance(cd_raw, str) else cd_raw
            if isinstance(cd, dict) and "poc_price" in cd:
                return None  # Already enriched — caller should use directly
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return None
