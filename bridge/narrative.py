"""
narrative.py -- Entry Narrative + Attribute Grading + Setup Quality Score (V6.5)

Builds a structured narrative for every trade/shadow explaining WHY
we entered. Grades each attribute A+/A/B/C/D. Computes a quality
score (0-10) from base 5 + weighted confluences.

Phase 1 thresholds are conservative placeholders.
Phase 3 will recalibrate grades using percentiles from real data.
"""


def grade_wick(pts: float) -> str:
    if pts >= 3.0: return "A+"
    if pts >= 2.0: return "A"
    if pts >= 1.5: return "B"
    if pts >= 1.0: return "C"
    return "D"


def grade_rel_vol(rv: float) -> str:
    if rv >= 2.0: return "A+"
    if rv >= 1.5: return "A"
    if rv >= 1.2: return "B"
    if rv >= 1.0: return "C"
    return "D"


def grade_stacked_count(count: int) -> str:
    if count >= 4: return "A+"
    if count == 3: return "A"
    if count == 2: return "B"
    return "D"


def grade_stacked_ratio(ratio: float) -> str:
    if ratio >= 4.0: return "A+"
    if ratio >= 3.0: return "A"
    if ratio >= 2.5: return "B"
    return "D"


def grade_fvg_size(pts: float) -> str:
    if 1.5 <= pts <= 2.5: return "A+"
    if 2.5 < pts <= 3.5: return "A"
    if 1.0 <= pts < 1.5: return "B"
    if (0.5 <= pts < 1.0) or (3.5 < pts <= 4.0): return "C"
    return "D"


def grade_mtf(count: int) -> str:
    if count >= 3: return "A+"
    if count == 2: return "B"
    if count == 1: return "C"
    return "D"


def compute_quality_score(
    mtf_aligned: bool,
    rel_vol: float,
    sweep_wick_pts: float,
    absorption_at_fvg: bool,
    stacked_count: int,
    post_news: bool,
    day_pnl: float,
    outside_killzone: bool,
) -> dict:
    """Compute Setup Quality Score per V6.5 Section 15.3.

    Returns dict with base, bonuses, penalties, final, rating.
    """
    base = 5
    bonuses = []
    penalties = []

    if mtf_aligned:
        bonuses.append({"reason": "MTF aligned", "points": 1})
    if rel_vol > 1.5:
        bonuses.append({"reason": "RelVol > 1.5", "points": 1})
    if sweep_wick_pts > 2.0:
        bonuses.append({"reason": "Sweep wick > 2pt", "points": 1})
    if absorption_at_fvg:
        bonuses.append({"reason": "Absorption at FVG", "points": 1})
    if stacked_count >= 3:
        bonuses.append({"reason": "Stacked count >= 3", "points": 1})

    if post_news:
        penalties.append({"reason": "Post-news < 30min", "points": -1})
    if day_pnl > 100:
        penalties.append({"reason": "Day PnL > +$100", "points": -1})
    if outside_killzone:
        penalties.append({"reason": "Outside killzone", "points": -1})

    bonus_pts = sum(b["points"] for b in bonuses)
    penalty_pts = sum(p["points"] for p in penalties)
    final = max(0, min(10, base + bonus_pts + penalty_pts))

    if final >= 9:
        rating = "GOLD"
    elif final >= 7:
        rating = "STRONG"
    elif final >= 5:
        rating = "BASELINE"
    else:
        rating = "WEAK"

    return {
        "base": base,
        "bonuses": bonuses,
        "penalties": penalties,
        "final": final,
        "rating": rating,
    }


def build_entry_narrative(
    direction: str,
    hit: dict,
    eval_result: dict,
    market_data: dict,
    tags: dict,
    levels: dict,
    fvg_size: float,
    candles: list,
) -> dict:
    """Build full entry narrative per V6.5 Appendix F.

    Args:
        direction: 'LONG' or 'SHORT'
        hit: setup hit dict with level, levelName, bar, relVol, type
        eval_result: pillar evaluation result
        market_data: full market data snapshot
        tags: strategic tags dict
        levels: entry/stop/t1/t2/t3 dict
        fvg_size: FVG size in points
        candles: recent sorted candles
    """
    is_long = direction == "LONG"
    bar = hit.get("bar", {})
    fp = market_data.get("footprint_bools", {}) or {}
    of2 = market_data.get("order_flow", {}) or {}
    cvd = market_data.get("cvd", {}) or {}

    # Compute wick
    if is_long:
        wick_pts = min(bar.get("o", 0), bar.get("c", 0)) - bar.get("l", 0)
    else:
        wick_pts = bar.get("h", 0) - max(bar.get("o", 0), bar.get("c", 0))
    wick_pts = round(max(0, wick_pts), 2)

    wick_grade = grade_wick(wick_pts)
    rel_vol = hit.get("relVol", 1.0)
    rel_vol_grade = grade_rel_vol(rel_vol)
    fvg_grade = grade_fvg_size(fvg_size)

    stacked_count = fp.get("stacked_imbalance_count", 0) or 0
    stacked_ratio = 2.5  # default from config
    stacked_count_grade = grade_stacked_count(stacked_count)
    stacked_ratio_grade = grade_stacked_ratio(stacked_ratio)

    mtf = market_data.get("mtf", {}) or {}
    mtf_count = 0
    for tf in ["m5", "m15", "m30", "m60"]:
        tf_d = mtf.get(tf) or {}
        if tf_d.get("c", 0) > tf_d.get("o", 0) and tf_d.get("delta", 0) > 0:
            mtf_count += 1
        elif tf_d.get("c", 0) < tf_d.get("o", 0) and tf_d.get("delta", 0) < 0:
            mtf_count += 1
    mtf_grade = grade_mtf(mtf_count)

    absorption = fp.get("absorption_at_fvg") or \
                 (of2.get("absorption_bull") if is_long else of2.get("absorption_bear")) or False
    delta_confirmed = fp.get("delta_confirmed_1m", False) or fp.get("delta_confirmed_5m", False)

    # Confluence factors
    confluence = []
    if mtf_count >= 3:
        confluence.append(f"MTF {mtf_count}/4 aligned")
    kz = tags.get("killzone_at_entry", "")
    if kz and kz != "OUTSIDE":
        mins = tags.get("minutes_into_session", 0)
        confluence.append(f"{kz} killzone active (minute {mins})")
    day_type = tags.get("day_type_at_entry", "")
    if day_type:
        setup_label = "trend_continuation" if day_type == "TREND" else "range_sweep"
        confluence.append(f"{day_type} day -- {setup_label} setup")

    # Risk factors
    risks = []
    news = tags.get("news_state_at_entry", "CLEAR")
    if news not in ("CLEAR", "NORMAL", ""):
        risks.append(f"News state: {news}")
    day_pnl = tags.get("day_pnl_before_entry", 0) or 0
    if abs(day_pnl) > 100:
        risks.append(f"Day PnL already ${day_pnl:.0f}")

    # Quality score
    score = compute_quality_score(
        mtf_aligned=mtf_count >= 3,
        rel_vol=rel_vol,
        sweep_wick_pts=wick_pts,
        absorption_at_fvg=bool(absorption),
        stacked_count=stacked_count,
        post_news=news not in ("CLEAR", "NORMAL", ""),
        day_pnl=day_pnl,
        outside_killzone=kz == "OUTSIDE",
    )

    # Build trigger summary
    parts = []
    if hit.get("type") == "sweep":
        parts.append(f"{'Deep' if wick_pts >= 2.0 else ''} sweep of {hit.get('levelName', '?')}".strip())
    else:
        parts.append(f"{hit.get('type', '?')} at {hit.get('levelName', '?')}")
    parts.append(f"MSS + FVG {fvg_size:.1f}pt")
    if absorption:
        parts.append("absorption confirmed")
    trigger = " + ".join(parts)

    depth = "deep" if wick_pts >= 2.5 else "moderate" if wick_pts >= 1.5 else "shallow"

    narrative = {
        "trigger_summary": trigger,
        "pillar_1": {
            "type": hit.get("type", "unknown"),
            "level": hit.get("levelName", ""),
            "level_price": hit.get("level", 0),
            "wick_pts": wick_pts,
            "wick_grade": wick_grade,
            "depth_rating": depth,
        },
        "pillar_2": {
            "fvg": {
                "detected": fvg_size > 0,
                "size_pts": fvg_size,
                "size_grade": fvg_grade,
            },
            "rel_vol": {
                "value": round(rel_vol, 2),
                "grade": rel_vol_grade,
            },
            "stacked": {
                "count": stacked_count,
                "count_grade": stacked_count_grade,
                "ratio_grade": stacked_ratio_grade,
                "direction": fp.get("stacked_imbalance_dir", "NONE"),
            },
        },
        "pillar_3": {
            "absorption_at_fvg": bool(absorption),
            "delta_confirmation_1m": bool(delta_confirmed),
        },
        "confluence_factors": confluence,
        "risk_factors": risks,
        "score": score,
        "model_version": "v1_phase1",
    }

    # V6.5 Appendix G: Tick Reversal Signals (collection only, NO scoring effect)
    tls = fp.get("tick_level_signals")
    if tls and isinstance(tls, dict):
        # Cap raw_ticks to 50 entries to limit storage
        if "raw_ticks" in tls and isinstance(tls["raw_ticks"], list):
            tls["raw_ticks"] = tls["raw_ticks"][:50]
        narrative["pillar_3"]["tick_level_signals"] = tls

    return narrative
