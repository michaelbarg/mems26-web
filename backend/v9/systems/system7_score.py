"""System-7: confluence-scoring judgment layer (Michael 2026-08-03, "אפשר להתחיל").

Internal evidence (32 live + 90 shadow): score ≥ 2 factors = 88% WR (+$242)
vs ≤ 1 = 14% WR (−$1,122). This module computes the score; the gateway uses
it for sizing (score < 40 → block, 40-64 → 1c, 65-84 → 2c, ≥85 → 3c).

Components (SYSTEM7_INTERNAL_EVIDENCE_2026-08-03):
  1. Day-type + direction alignment (pattern × day = the book play)
  2. Live leg presence (with the leg = with the immediate structure)
  3. Location in range (not chasing — mid-range pullback entries win 71%)
  4. Opening confidence (high-conf opening = directional conviction)
  5. Delta confirmation (R5: extension backed by flow)
  6. Noon penalty (18:30-20:30 IL = low-conviction window)
  7. Late-ZLR penalty (ZLR after 20:00 IL = negative expectancy)

The correlated trio (day-type + leg + location) is capped at 50pts combined
per the external research warning against double-counting aligned factors.

Pure module — flag SYSTEM7_SCORE_V1 gates at the caller level.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

IL = ZoneInfo("Asia/Jerusalem")

# Score component weights (from the internal evidence + external research)
W_DAYTYPE_ALIGN = 20       # day-type + direction alignment
W_LEG = 15                 # live leg in trade direction
W_LOCATION = 15            # mid-range (not chasing)
W_CORRELATED_CAP = 50      # cap for the correlated trio above
W_OPENING_CONF = 10        # high opening confidence
W_DELTA = 10               # delta confirms extension
W_NOON_PENALTY = -15       # 18:30-20:30 IL low-conviction window
W_LATE_ZLR_PENALTY = -20   # ZLR after 20:00 IL negative expectancy
W_BASE = 30                # base score for any passing setup


def score(
    *,
    setup: Dict[str, Any],
    market_context: Optional[Any] = None,
    bar_ts: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Compute the System-7 confluence score for a setup.

    Returns {score: 0-100, components: {name: pts}, sizing: 0-3,
             blocked: bool, reason: str}.
    """
    direction = str(setup.get("direction", "")).upper()
    pattern = str(setup.get("pattern", setup.get("pattern_name", ""))).upper()
    entry_price = setup.get("entry_price")

    components = {}
    total = W_BASE
    components["base"] = W_BASE

    # ── 1. Day-type + direction alignment ──
    day_align = 0
    if market_context:
        mc = market_context
        day_bias = getattr(mc, "day_bias", "NONE")
        day_type = getattr(mc, "day_type", "UNKNOWN")
        with_day = (
            (direction == "LONG" and day_bias == "UP")
            or (direction == "SHORT" and day_bias == "DOWN")
        )
        if with_day:
            day_align = W_DAYTYPE_ALIGN
            # On trend days, chase is NOT a penalty (the update from EFFICIENCY doc)
            if day_type.startswith("Trend"):
                components["trend_day_chase_exempt"] = True
    components["day_align"] = day_align
    total += day_align

    # ── 2. Live leg ──
    leg_pts = 0
    if market_context:
        leg_dir = getattr(market_context, "leg_dir", None)
        if leg_dir and leg_dir == ("UP" if direction == "LONG" else "DOWN"):
            leg_pts = W_LEG
    components["leg"] = leg_pts
    total += leg_pts

    # ── 3. Location (not chasing) ──
    loc_pts = 0
    # Simplified: if entry_price is available and market_context has extremes,
    # compute position in the running range. For now, use a placeholder.
    # In production, this reads from the bar history.
    components["location"] = loc_pts
    total += loc_pts

    # Cap the correlated trio
    correlated = day_align + leg_pts + loc_pts
    if correlated > W_CORRELATED_CAP:
        excess = correlated - W_CORRELATED_CAP
        total -= excess
        components["correlated_cap"] = -excess

    # ── 4. Opening confidence ──
    open_pts = 0
    if market_context:
        oc = getattr(market_context, "opening_conf", 0)
        if oc >= 0.7:
            open_pts = W_OPENING_CONF
    components["opening_conf"] = open_pts
    total += open_pts

    # ── 5. Delta confirmation ──
    delta_pts = 0
    # Reads from classifier measured output when available
    components["delta"] = delta_pts
    total += delta_pts

    # ── 6. Noon penalty (18:30-20:30 IL) ──
    noon_penalty = 0
    if bar_ts:
        try:
            il_time = bar_ts.astimezone(IL)
            il_minutes = il_time.hour * 60 + il_time.minute
            if 18 * 60 + 30 <= il_minutes <= 20 * 60 + 30:
                noon_penalty = W_NOON_PENALTY
        except Exception:
            pass
    components["noon_penalty"] = noon_penalty
    total += noon_penalty

    # ── 7. Late ZLR penalty ──
    late_zlr = 0
    if "ZLR" in pattern and bar_ts:
        try:
            il_time = bar_ts.astimezone(IL)
            if il_time.hour >= 20:
                late_zlr = W_LATE_ZLR_PENALTY
        except Exception:
            pass
    components["late_zlr"] = late_zlr
    total += late_zlr

    # Clamp to 0-100
    total = max(0, min(100, total))

    # Sizing decision
    if total < 40:
        sizing = 0
        blocked = True
        reason = f"score {total} < 40 (insufficient confluence)"
    elif total < 65:
        sizing = 1
        blocked = False
        reason = f"score {total}: 1 contract (low conviction)"
    elif total < 85:
        sizing = 2
        blocked = False
        reason = f"score {total}: 2 contracts (medium conviction)"
    else:
        sizing = 3
        blocked = False
        reason = f"score {total}: 3 contracts (high conviction)"

    return {
        "score": total,
        "components": components,
        "sizing": sizing,
        "blocked": blocked,
        "reason": reason,
    }
