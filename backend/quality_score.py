"""
V7.13.1 Phase 5: Day-Adaptive Quality Score Calculator + Position Sizing.

Weights are dynamic per day type (from day_config.py).
"""

from typing import Optional
from day_config import get_config


def calculate_quality_score(market_data: dict, direction: str, day_type: str = None) -> dict:
    """
    Calculate Setup Quality Score 0-100 with day-adaptive weights.
    Returns: {total, breakdown, reasons, day_type_used, weights_applied}
    """
    config = get_config(day_type)
    weights = config["weights"]
    breakdown = {"vegas": 0, "tpo": 0, "fvg": 0, "footprint": 0}
    reasons = []

    # Vegas (dynamic weight)
    vegas = market_data.get("vegas") or {}
    vtrend = vegas.get("trend", "NEUTRAL")
    vwidth = vegas.get("tunnel_width", 0)
    max_vegas = weights["vegas"]

    if vwidth < config["vegas_min_width"]:
        reasons.append(f"Vegas width too narrow ({vwidth:.2f}pt) — no clear trend")
    elif (direction == "LONG" and vtrend == "BULLISH") or \
         (direction == "SHORT" and vtrend == "BEARISH"):
        breakdown["vegas"] = max_vegas
        reasons.append(f"Vegas {vtrend} match (+{max_vegas})")
    elif vtrend == "NEUTRAL":
        breakdown["vegas"] = max_vegas // 2
        reasons.append(f"Vegas NEUTRAL (partial +{max_vegas // 2})")
    else:
        reasons.append(f"Vegas {vtrend} OPPOSES direction")

    # TPO (dynamic weight)
    tpo = market_data.get("tpo") or {}
    tpo_cd = tpo.get("current_day") or {}
    price = market_data.get("current_price", 0) or market_data.get("price", 0)
    max_tpo = weights["tpo"]
    tpo_pos_pts = max_tpo // 2
    tpo_va_pts = max_tpo - tpo_pos_pts

    if tpo_cd and tpo_cd.get("poc_price"):
        poc = tpo_cd["poc_price"]
        above_poc = price > poc if price and poc else False
        if (direction == "LONG" and above_poc) or \
           (direction == "SHORT" and not above_poc):
            breakdown["tpo"] += tpo_pos_pts
            reasons.append(f"TPO position favors direction (+{tpo_pos_pts})")
        vah = tpo_cd.get("vah", 0)
        val = tpo_cd.get("val", 0)
        if vah and val and val <= price <= vah:
            breakdown["tpo"] += tpo_va_pts
            reasons.append(f"Price in TPO Value Area (+{tpo_va_pts})")

    # FVG (dynamic weight)
    triggers = (market_data.get("triggers") or {}).get("active", [])
    matching_fvg = [t for t in triggers
                    if t.get("type") == "FVG"
                    and t.get("direction") == direction.lower()]
    max_fvg = weights["fvg"]
    if matching_fvg:
        breakdown["fvg"] = max_fvg
        reasons.append(f"FVG {direction.lower()} active ({len(matching_fvg)}) (+{max_fvg})")

    # Footprint (dynamic weight)
    fp = (market_data.get("triggers") or {}).get("footprint_last_bar") or {}
    max_fp = weights["footprint"]
    fp_delta_pts = max_fp * 3 // 5  # 60% for delta
    fp_imb_pts = max_fp - fp_delta_pts  # 40% for imbalance
    if fp:
        delta = fp.get("delta", 0)
        if (direction == "LONG" and delta > 50) or \
           (direction == "SHORT" and delta < -50):
            breakdown["footprint"] += fp_delta_pts
            reasons.append(f"Delta {delta} confirms direction (+{fp_delta_pts})")
        imb = fp.get("imbalance_ratio", 0)
        if imb > 1.5:
            breakdown["footprint"] += fp_imb_pts
            reasons.append(f"Imbalance ratio {imb:.2f} (+{fp_imb_pts})")

    total = sum(breakdown.values())
    return {
        "total": total,
        "breakdown": breakdown,
        "reasons": reasons,
        "day_type_used": config["day_type"],
        "weights_applied": weights,
    }


def determine_position_size(score: int, mode: str, day_type: str = None) -> dict:
    """
    Tiered position sizing based on quality score with day-adaptive thresholds.
    Returns: {qty, exits, action, reject?, warn?, thresholds_used}
    """
    config = get_config(day_type)
    thresholds = config["thresholds"]
    full_thresh = thresholds["full"]
    half_thresh = thresholds["half"]

    if score >= full_thresh:
        return {"qty": 3, "exits": ["C1", "C2", "C3"], "action": "FULL_SIZE",
                "thresholds_used": thresholds}
    elif score >= half_thresh:
        return {"qty": 2, "exits": ["C1", "C2"], "action": "HALF_SIZE",
                "thresholds_used": thresholds}
    else:
        if mode == "DEMO":
            return {"qty": 0, "warn": True, "action": "WARN_LOW_SCORE",
                    "score": score, "thresholds_used": thresholds}
        else:
            return {"qty": 0, "reject": True, "action": "REJECT_LOW_SCORE",
                    "score": score, "thresholds_used": thresholds}


def calculate_targets(entry: float, stop: float, direction: str,
                      market_data: dict, day_type: str = None) -> dict:
    """
    Day-adaptive targets:
      C1 = entry + c1_R * R
      C2 = entry + c2_R * R (or PDC for GAP_FILL, or TPO confluence for NORMAL)
      C3 = enabled/disabled per day type
    """
    config = get_config(day_type)
    target_rules = config["targets"]
    R = abs(entry - stop)
    sign = 1 if direction == "LONG" else -1

    c1 = round(entry + (target_rules["c1_R"] * R * sign), 2)
    c2_r_based = round(entry + (target_rules["c2_R"] * R * sign), 2)

    c2 = c2_r_based
    c2_method = "R_based"

    # GAP_FILL special: use Previous Day Close if available and in direction
    if target_rules["c2_special"] == "PDC":
        mp = market_data.get("market_profile") or {}
        pdc = mp.get("prev_close") or mp.get("prev_day_close")
        if pdc:
            if direction == "LONG" and pdc > entry:
                c2 = round(pdc, 2)
                c2_method = "PDC"
            elif direction == "SHORT" and pdc < entry:
                c2 = round(pdc, 2)
                c2_method = "PDC"

    # TPO confluence only for NORMAL/DEVELOPING
    elif config["day_type"] in ("NORMAL", "DEVELOPING"):
        tpo = market_data.get("tpo") or {}
        tpo_cd = tpo.get("current_day") or {}
        if tpo_cd:
            nearest_tpo = None
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
                    c2 = round(max(c2_r_based, nearest_tpo), 2)
                else:
                    c2 = round(min(c2_r_based, nearest_tpo), 2)
                c2_method = "TPO_confluence"

    return {
        "c1": c1,
        "c2": c2,
        "c3_enabled": target_rules["c3_enabled"],
        "R": round(R, 2),
        "c2_method": c2_method,
        "day_type_used": config["day_type"],
    }


def get_be_strategy(day_type: Optional[str] = None) -> str:
    """Returns BE timing rule for the day type."""
    config = get_config(day_type)
    return config["be_rule"]
