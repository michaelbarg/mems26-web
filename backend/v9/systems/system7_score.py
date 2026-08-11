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
    # Mid-range (30-70% of running day range) = pullback entry → +15pts.
    # Chase (entry in the last 30% toward the extreme in trade direction) → 0.
    # On trend days, chase is NOT a penalty (EFFICIENCY doc update).
    loc_pts = 0
    _trend_chase_exempt = components.get("trend_day_chase_exempt", False)
    if entry_price is not None:
        try:
            from backend.v9.db.read import read_all as _s7_read
            _s7_rows = _s7_read(
                "SELECT high, low FROM v9_bars_5min_woodies "
                "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
                "(now() AT TIME ZONE 'America/New_York')::date "
                "ORDER BY ts", {},
            )
            if _s7_rows and len(_s7_rows) >= 6:
                _s7_sh = max(float(r["high"]) for r in _s7_rows)
                _s7_sl = min(float(r["low"]) for r in _s7_rows)
                _s7_rng = _s7_sh - _s7_sl
                if _s7_rng >= 8:
                    _s7_pos = (float(entry_price) - _s7_sl) / _s7_rng
                    if direction == "SHORT":
                        _s7_pos = 1.0 - _s7_pos  # normalize: 0=near extreme, 1=far from it
                    _s7_is_chase = _s7_pos > 0.70
                    _s7_is_mid = 0.30 <= _s7_pos <= 0.70
                    if _s7_is_mid:
                        loc_pts = W_LOCATION  # pullback entry
                    elif _s7_is_chase and not _trend_chase_exempt:
                        loc_pts = 0  # chasing (penalty by omission)
                    elif _trend_chase_exempt:
                        loc_pts = W_LOCATION  # trend day: chase allowed
                    components["loc_pos"] = round(_s7_pos, 2)
        except Exception:
            pass
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
    # R5: delta confirms extension → +10pts (the extension is real, not a
    # failed auction). Reads from cumulative_delta export via delta_features.
    delta_pts = 0
    try:
        import os as _s7_os
        if _s7_os.getenv("DELTA_FEATURES_V1", "0").lower() in ("1", "true", "yes"):
            from backend.v9.systems.delta_features import (
                delta_confirms_extension as _s7_dce,
                cvd_directionality as _s7_cvd_d,
            )
            import json as _s7_json
            from pathlib import Path as _s7_P
            _s7_dp = _s7_P(os.path.expanduser(
                "~/SierraChart_Data/v9_export/cumulative_delta.json"))
            if _s7_dp.exists():
                _s7_de = _s7_json.loads(_s7_dp.read_text().strip() or "{}")
                _s7_pts = _s7_de.get("points", [])
                _break_dir = "UP" if direction == "LONG" else "DOWN"
                _s7_confirmed = _s7_dce(_s7_pts, _break_dir)
                if _s7_confirmed is True:
                    delta_pts = W_DELTA
                # Also report cvd_directionality for observability
                components["cvd_directionality"] = _s7_cvd_d(_s7_pts)
    except Exception:
        pass
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

    # ── E4. S2×S4 confluence boost (65% WR vs 50% solo) ──
    # When the gateway detected an S2×S4 same-bar agreement (K4 confluence_tag),
    # the combined pattern has measurably higher edge. +10pts.
    confluence_pts = 0
    _conf_tag = setup.get("confluence_tag") or (setup.get("metadata") or {}).get("confluence_tag")
    if _conf_tag and _conf_tag.get("quality_boost"):
        confluence_pts = 10
    components["s2_s4_confluence"] = confluence_pts
    total += confluence_pts

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
