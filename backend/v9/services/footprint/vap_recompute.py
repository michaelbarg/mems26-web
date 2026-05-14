"""W1.2 — VAP (Volume-at-Price) Python-side recompute.

DLL MaintainVAP=0 means no native VAP storage. This module computes
VAP from raw footprint cell data (bid_volume + ask_volume per price).

Produces POC, VAH, VAL within a single footprint bar's levels.
"""
from typing import Dict, List, Optional


def compute_bar_vap(levels: List[Dict]) -> Dict:
    """Compute Volume-at-Price from footprint cell levels.

    Args:
        levels: list of {price, bid_volume/bid_vol, ask_volume/ask_vol}

    Returns:
        {poc, vah, val, total_volume, level_count, vap: [{price, volume, pct}]}
    """
    if not levels:
        return {"poc": None, "vah": None, "val": None, "total_volume": 0,
                "level_count": 0, "vap": []}

    # Build volume per price
    vap = []
    for lv in levels:
        price = lv.get("price", 0)
        bid = float(lv.get("bid_volume", lv.get("bid_vol", lv.get("agg_sell_vol", 0))) or 0)
        ask = float(lv.get("ask_volume", lv.get("ask_vol", lv.get("agg_buy_vol", 0))) or 0)
        total = bid + ask
        vap.append({"price": price, "volume": total})

    total_volume = sum(v["volume"] for v in vap)
    if total_volume == 0:
        return {"poc": None, "vah": None, "val": None, "total_volume": 0,
                "level_count": len(vap), "vap": vap}

    # Sort by price ascending
    vap.sort(key=lambda v: v["price"])

    # POC = price with highest volume
    poc_entry = max(vap, key=lambda v: v["volume"])
    poc = poc_entry["price"]

    # VAH/VAL: 70% of total volume centered on POC
    target_vol = total_volume * 0.70
    # Start from POC, expand outward
    poc_idx = next(i for i, v in enumerate(vap) if v["price"] == poc)
    lo = poc_idx
    hi = poc_idx
    accumulated = vap[poc_idx]["volume"]

    while accumulated < target_vol and (lo > 0 or hi < len(vap) - 1):
        expand_lo = vap[lo - 1]["volume"] if lo > 0 else -1
        expand_hi = vap[hi + 1]["volume"] if hi < len(vap) - 1 else -1
        if expand_lo >= expand_hi and lo > 0:
            lo -= 1
            accumulated += vap[lo]["volume"]
        elif hi < len(vap) - 1:
            hi += 1
            accumulated += vap[hi]["volume"]
        else:
            break

    val = vap[lo]["price"]
    vah = vap[hi]["price"]

    # Add pct to each level
    for v in vap:
        v["pct"] = round(v["volume"] / total_volume * 100, 1) if total_volume > 0 else 0

    return {
        "poc": poc,
        "vah": vah,
        "val": val,
        "total_volume": total_volume,
        "level_count": len(vap),
        "vap": vap,
    }
