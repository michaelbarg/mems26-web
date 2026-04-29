"""
V7.12.0: Setup Quality Score Calculator + Position Sizing.

Weights:
  Vegas: 30pt, TPO: 25pt, FVG: 25pt, Footprint: 20pt
  Total: 0-100

Not wired to /trade/execute yet — standalone module.
"""


def calculate_quality_score(market_data: dict, direction: str) -> dict:
    """
    Calculate Setup Quality Score 0-100.
    Returns: {total, breakdown, reasons}
    """
    breakdown = {"vegas": 0, "tpo": 0, "fvg": 0, "footprint": 0}
    reasons = []

    # Vegas (30 points max)
    vegas = market_data.get("vegas") or {}
    vtrend = vegas.get("trend", "NEUTRAL")
    if (direction == "LONG" and vtrend == "BULLISH") or \
       (direction == "SHORT" and vtrend == "BEARISH"):
        breakdown["vegas"] = 30
        reasons.append(f"Vegas {vtrend} match")
    elif vtrend == "NEUTRAL":
        breakdown["vegas"] = 15
        reasons.append("Vegas NEUTRAL (partial)")
    else:
        reasons.append(f"Vegas {vtrend} OPPOSES direction")

    # TPO (25 points max)
    tpo = market_data.get("tpo") or {}
    tpo_cd = tpo.get("current_day") or {}
    price = market_data.get("price", 0)
    if tpo_cd and tpo_cd.get("poc_price"):
        poc = tpo_cd["poc_price"]
        above_poc = price > poc if price and poc else False
        if (direction == "LONG" and above_poc) or \
           (direction == "SHORT" and not above_poc):
            breakdown["tpo"] += 12
            reasons.append("TPO position favors direction")
        vah = tpo_cd.get("vah", 0)
        val = tpo_cd.get("val", 0)
        if vah and val and val <= price <= vah:
            breakdown["tpo"] += 13
            reasons.append("Price in TPO Value Area")

    # FVG (25 points max)
    triggers = (market_data.get("triggers") or {}).get("active", [])
    matching_fvg = [t for t in triggers
                    if t.get("type") == "FVG"
                    and t.get("direction") == direction.lower()]
    if matching_fvg:
        breakdown["fvg"] = 25
        reasons.append(f"FVG {direction.lower()} active ({len(matching_fvg)})")

    # Footprint (20 points max)
    fp = (market_data.get("triggers") or {}).get("footprint_last_bar") or {}
    if fp:
        delta = fp.get("delta", 0)
        if (direction == "LONG" and delta > 50) or \
           (direction == "SHORT" and delta < -50):
            breakdown["footprint"] += 12
            reasons.append(f"Delta {delta} confirms direction")
        imb = fp.get("imbalance_ratio", 0)
        if imb > 1.5:
            breakdown["footprint"] += 8
            reasons.append(f"Imbalance ratio {imb:.2f}")

    total = sum(breakdown.values())
    return {"total": total, "breakdown": breakdown, "reasons": reasons}


def determine_position_size(score: int, mode: str) -> dict:
    """
    Tiered position sizing based on quality score.
    Returns: {qty, exits, action, reject?, warn?}
    """
    if score >= 70:
        return {"qty": 3, "exits": ["C1", "C2", "C3"], "action": "FULL_SIZE"}
    elif score >= 50:
        return {"qty": 2, "exits": ["C1", "C2"], "action": "HALF_SIZE"}
    else:
        if mode == "DEMO":
            return {"qty": 0, "warn": True, "action": "WARN_LOW_SCORE", "score": score}
        else:
            return {"qty": 0, "reject": True, "action": "REJECT_LOW_SCORE", "score": score}


def calculate_targets(entry: float, stop: float, direction: str, tpo_data: dict) -> dict:
    """
    Risk-based targets:
      C1 = entry + 1R
      C2 = max(2R, nearest TPO level in direction)
      C3 = vegas trail (handled by DLL)
    """
    R = abs(entry - stop)
    sign = 1 if direction == "LONG" else -1

    c1 = round(entry + (R * sign), 2)
    c2_simple = round(entry + (2 * R * sign), 2)

    # Try to use TPO level for C2
    nearest_tpo = None
    tpo_cd = tpo_data.get("current_day") or {}
    if tpo_cd:
        if direction == "LONG":
            candidates = [tpo_cd.get("vah"), tpo_cd.get("poc_price")]
            candidates = [c for c in candidates if c and c > entry]
            if candidates:
                nearest_tpo = min(candidates)
        else:
            candidates = [tpo_cd.get("val"), tpo_cd.get("poc_price")]
            candidates = [c for c in candidates if c and c < entry]
            if candidates:
                nearest_tpo = max(candidates)

    if nearest_tpo:
        if direction == "LONG":
            c2 = round(max(c2_simple, nearest_tpo), 2)
        else:
            c2 = round(min(c2_simple, nearest_tpo), 2)
    else:
        c2 = c2_simple

    return {
        "c1": c1,
        "c2": c2,
        "R": round(R, 2),
        "tpo_used": nearest_tpo is not None,
    }
