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

    # Vegas: trend match is primary, width modulates confidence
    vegas = market_data.get("vegas") or {}
    vtrend = vegas.get("trend", "NEUTRAL")
    vwidth = vegas.get("tunnel_width", 0) or 0
    max_vegas = weights["vegas"]

    trend_matches = ((direction == "LONG" and vtrend == "BULLISH") or
                     (direction == "SHORT" and vtrend == "BEARISH"))
    if trend_matches:
        # Width modulates: >= 0.5 full, 0.2-0.5 75%, < 0.2 50%
        if vwidth >= 0.5:
            breakdown["vegas"] = max_vegas
            reasons.append(f"Vegas {vtrend} match ({vwidth:.2f}pt width) (+{max_vegas})")
        elif vwidth >= 0.2:
            pts = int(max_vegas * 0.75)
            breakdown["vegas"] = pts
            reasons.append(f"Vegas {vtrend} match, narrow tunnel ({vwidth:.2f}pt) (+{pts})")
        else:
            pts = int(max_vegas * 0.5)
            breakdown["vegas"] = pts
            reasons.append(f"Vegas {vtrend} match, very narrow ({vwidth:.2f}pt) (+{pts})")
    elif vtrend == "NEUTRAL":
        pts = int(max_vegas * 0.3)
        breakdown["vegas"] = pts
        reasons.append(f"Vegas NEUTRAL ({vwidth:.2f}pt width) (+{pts})")
    else:
        reasons.append(f"Vegas {vtrend} OPPOSES {direction}")

    # TPO (dynamic weight)
    tpo = market_data.get("tpo") or {}
    tpo_cd = tpo.get("current_day") or {}
    # Robust price extraction: try multiple field names
    price = market_data.get("price") or market_data.get("current_price") or 0
    if not price:
        bar = market_data.get("bar") or {}
        price = bar.get("c") or 0
    max_tpo = weights["tpo"]
    tpo_pos_pts = max_tpo // 2
    tpo_va_pts = max_tpo - tpo_pos_pts

    if tpo_cd and tpo_cd.get("poc_price") and price > 0:
        poc = tpo_cd["poc_price"]
        above_poc = price > poc
        if (direction == "LONG" and above_poc) or \
           (direction == "SHORT" and not above_poc):
            breakdown["tpo"] += tpo_pos_pts
            reasons.append(f"TPO position favors direction (price={'above' if above_poc else 'below'} POC {poc:.2f}) (+{tpo_pos_pts})")
        vah = tpo_cd.get("vah") or 0
        val = tpo_cd.get("val") or 0
        if vah and val and val <= price <= vah:
            breakdown["tpo"] += tpo_va_pts
            reasons.append(f"Price in TPO Value Area (+{tpo_va_pts})")
        elif not vah or not val:
            # VAH/VAL unavailable but POC exists — award partial VA points
            partial = tpo_va_pts // 2
            breakdown["tpo"] += partial
            reasons.append(f"TPO VA levels unavailable, POC-only partial (+{partial})")

    # FVG: direction match + recency filter (last 30 min only)
    import re, time as _time
    fvg_dir = "bullish" if direction == "LONG" else "bearish"
    triggers = (market_data.get("triggers") or {}).get("active", [])
    now_ts = int(_time.time())
    recency_sec = 30 * 60  # 30 minutes

    matching_fvg = []
    for t in triggers:
        if t.get("type") != "FVG" or t.get("direction") != fvg_dir:
            continue
        # Extract timestamp from ID (T_FVG_<unix>_<counter>) or detected_at
        fvg_ts = t.get("detected_at", 0)
        if not fvg_ts:
            m = re.search(r'T_FVG_(\d+)_', t.get("id", ""))
            fvg_ts = int(m.group(1)) if m else 0
        if fvg_ts > 0 and (now_ts - fvg_ts) <= recency_sec:
            matching_fvg.append(t)

    max_fvg = weights["fvg"]
    if len(matching_fvg) >= 3:
        breakdown["fvg"] = max_fvg
        reasons.append(f"FVG {fvg_dir}: {len(matching_fvg)} recent matches (+{max_fvg})")
    elif len(matching_fvg) >= 1:
        pts = int(max_fvg * 0.6)
        breakdown["fvg"] = pts
        reasons.append(f"FVG {fvg_dir}: {len(matching_fvg)} recent match(es) (+{pts})")
    else:
        all_fvg = [t for t in triggers if t.get("type") == "FVG" and t.get("direction") == fvg_dir]
        if all_fvg:
            reasons.append(f"FVG {fvg_dir}: {len(all_fvg)} total but none recent (<30min)")
        else:
            reasons.append(f"FVG: no {fvg_dir} triggers")

    # Footprint: check triggers.footprint_last_bar AND footprint_bools
    fp = (market_data.get("triggers") or {}).get("footprint_last_bar") or {}
    fp_bools = market_data.get("footprint_bools") or {}
    max_fp = weights["footprint"]
    fp_delta_pts = int(max_fp * 0.7)  # 70% for delta
    fp_imb_pts = max_fp - fp_delta_pts  # 30% for imbalance/booleans

    # Delta: from footprint_last_bar or footprint_bools
    delta = fp.get("delta", 0) or 0
    if not delta:
        # Fallback: compute from buy/sell in footprint_last_bar
        buy = fp.get("buy_vol", 0) or 0
        sell = fp.get("sell_vol", 0) or 0
        if buy or sell:
            delta = buy - sell

    if delta != 0:
        confirms = (direction == "LONG" and delta > 0) or \
                   (direction == "SHORT" and delta < 0)
        if confirms:
            # Scale: delta > 200 = full, > 50 = 60%, > 0 = 30%
            abs_delta = abs(delta)
            if abs_delta >= 200:
                breakdown["footprint"] += fp_delta_pts
                reasons.append(f"Footprint: delta={delta:+d} strong ({direction}) (+{fp_delta_pts})")
            elif abs_delta >= 50:
                pts = int(fp_delta_pts * 0.6)
                breakdown["footprint"] += pts
                reasons.append(f"Footprint: delta={delta:+d} moderate ({direction}) (+{pts})")
            else:
                pts = int(fp_delta_pts * 0.3)
                breakdown["footprint"] += pts
                reasons.append(f"Footprint: delta={delta:+d} weak ({direction}) (+{pts})")
        else:
            reasons.append(f"Footprint: delta={delta:+d} opposes {direction}")
    else:
        reasons.append("Footprint: no delta data available")

    # Imbalance: from footprint_last_bar or footprint_bools
    imb = fp.get("imbalance_ratio", 0) or 0
    absorption = fp_bools.get("absorption_detected", False)
    if imb > 1.5:
        breakdown["footprint"] += fp_imb_pts
        reasons.append(f"Imbalance ratio {imb:.2f} (+{fp_imb_pts})")
    elif absorption:
        breakdown["footprint"] += fp_imb_pts
        reasons.append(f"Absorption detected (+{fp_imb_pts})")

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
