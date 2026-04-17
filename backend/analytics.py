"""
Analytics engine for MEMS26 trade data.

Reads enriched trade records from Redis (mems26:tradelog:*) and computes:
- Daily reports (WR, P&L, MAE/MFE, pillar attribution, killzone breakdown)
- Weekly reports (18-trade rolling, pillar correlation, threshold recs)
- Pattern analysis (setup quality matrix, MAE/MFE distributions)

Trade records stored in Redis use the enriched schema — see TRADE_SCHEMA.
"""

import json
import logging
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

log = logging.getLogger("analytics")
ET = ZoneInfo("America/New_York")

# ── Enriched Trade Schema (stored in Redis as JSON) ──────────────────────
# These fields are added at execute + close time in main.py.
TRADE_SCHEMA = {
    # Identity
    "id": "T{unix}",
    "direction": "LONG|SHORT",
    "entry_price": 0.0,
    "exit_price": 0.0,
    "stop": 0.0,
    "t1": 0.0, "t2": 0.0, "t3": 0.0,
    "risk_pts": 0.0,
    "pnl_pts": 0.0,
    "pnl_usd": 0.0,
    "contracts": 1,
    "entry_ts": 0,
    "exit_ts": 0,
    "status": "CLOSED",
    "close_reason": "STOP|T1|T2|T3|MANUAL|EOD_FLATTEN",

    # Setup context (captured at entry)
    "setup_type": "LIQUIDITY_SWEEP|MANUAL",
    "day_type": "TREND|NORMAL|VOLATILE|ROTATIONAL",
    "killzone": "London|NY_Open|NY_Close|OUTSIDE",
    "sweep_wick_pts": 0.0,
    "stacked_count": 0,
    "pillars_passed": 0,       # 0-3
    "pillar_detail": "P1:pass P2:fail P3:wait",
    "rel_vol": 0.0,
    "cvd_trend": "BULLISH|BEARISH|NEUTRAL",
    "vwap_dist": 0.0,
    "vwap_above": False,
    "mtf_alignment": 0,        # 0-4 matching TFs
    "post_news": False,
    "manual_override": False,

    # Performance (computed at close)
    "mae_pts": 0.0,            # Max Adverse Excursion
    "mfe_pts": 0.0,            # Max Favorable Excursion
    "duration_min": 0.0,
    "bars_held": 0,
    "exit_efficiency": 0.0,    # mfe_pts > 0 ? pnl_pts / mfe_pts : 0
}


def _safe_float(v, default=0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def _safe_int(v, default=0) -> int:
    try:
        return int(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def _trade_date(t: dict) -> str:
    """Get trade date in ET timezone."""
    ts = t.get("exit_ts") or t.get("entry_ts") or 0
    if ts <= 0:
        return ""
    return datetime.fromtimestamp(ts, tz=ET).strftime("%Y-%m-%d")


def _is_win(t: dict) -> bool:
    return _safe_float(t.get("pnl_pts")) > 0


def compute_mae_mfe(candles: list, entry_price: float, entry_ts: int,
                    exit_ts: int, direction: str) -> dict:
    """Scan candles between entry and exit to find MAE and MFE."""
    is_long = direction == "LONG"
    mae = 0.0  # worst drawdown (always positive)
    mfe = 0.0  # best run (always positive)

    for c in candles:
        ts = c.get("ts", 0)
        if ts < entry_ts or ts > exit_ts:
            continue
        h = _safe_float(c.get("h", c.get("high")))
        l = _safe_float(c.get("l", c.get("low")))
        if h == 0 or l == 0:
            continue

        if is_long:
            adverse = entry_price - l   # how far price went against us
            favorable = h - entry_price  # how far price went for us
        else:
            adverse = h - entry_price
            favorable = entry_price - l

        if adverse > mae:
            mae = adverse
        if favorable > mfe:
            mfe = favorable

    return {"mae_pts": round(mae, 2), "mfe_pts": round(mfe, 2)}


def snapshot_market_context(data: dict) -> dict:
    """Extract market context from /market/latest payload for trade enrichment."""
    if not data:
        return {}

    day = data.get("day", {}) or {}
    session = data.get("session", {}) or {}
    vwap = data.get("vwap", {}) or {}
    cvd = data.get("cvd", {}) or {}
    vol_ctx = data.get("volume_context", {}) or {}
    fp = data.get("footprint_bools", {}) or {}
    mtf = data.get("mtf", {}) or {}

    # Killzone
    try:
        et_now = datetime.now(ET)
        et_min = et_now.hour * 60 + et_now.minute
        kz_zones = [("London", 180, 300), ("NY_Open", 570, 630), ("NY_Close", 900, 960)]
        killzone = "OUTSIDE"
        for name, start, end in kz_zones:
            if start <= et_min < end:
                killzone = name
                break
    except Exception:
        killzone = "UNKNOWN"

    # MTF alignment count
    mtf_aligned = 0
    for tf_key in ["m5", "m15", "m30", "m60"]:
        tf_d = mtf.get(tf_key) or {}
        if tf_d.get("c", 0) > tf_d.get("o", 0) and tf_d.get("delta", 0) > 0:
            mtf_aligned += 1
        elif tf_d.get("c", 0) < tf_d.get("o", 0) and tf_d.get("delta", 0) < 0:
            mtf_aligned += 1

    return {
        "day_type": day.get("type", "UNKNOWN"),
        "killzone": killzone,
        "rel_vol": round(_safe_float(vol_ctx.get("rel_vol", 1)), 2),
        "cvd_trend": cvd.get("trend", "NEUTRAL"),
        "vwap_dist": round(_safe_float(vwap.get("distance")), 2),
        "vwap_above": bool(vwap.get("above")),
        "mtf_alignment": mtf_aligned,
        "stacked_count": _safe_int(fp.get("stacked_imbalance_count")),
        "post_news": False,  # set separately from news_tag
    }


# ── Daily Report ─────────────────────────────────────────────────────────

def compute_daily_report(trades: list, target_date: str) -> dict:
    """Compute daily analytics for a specific date."""
    day_trades = [t for t in trades if _trade_date(t) == target_date]

    if not day_trades:
        return {
            "date": target_date,
            "trade_count": 0,
            "win_rate": 0,
            "total_pnl_pts": 0,
            "total_pnl_usd": 0,
            "avg_mae_pts": 0,
            "avg_mfe_pts": 0,
            "trades": [],
            "killzone_breakdown": {},
            "setup_type_breakdown": {},
            "pillar_attribution": {},
            "observations": ["No trades on this date"],
        }

    wins = [t for t in day_trades if _is_win(t)]
    losses = [t for t in day_trades if not _is_win(t)]
    total_pnl = sum(_safe_float(t.get("pnl_pts")) for t in day_trades)
    total_usd = sum(_safe_float(t.get("pnl_usd")) for t in day_trades)

    # MAE/MFE averages
    maes = [_safe_float(t.get("mae_pts")) for t in day_trades if t.get("mae_pts")]
    mfes = [_safe_float(t.get("mfe_pts")) for t in day_trades if t.get("mfe_pts")]

    # Killzone breakdown
    kz_groups: dict = {}
    for t in day_trades:
        kz = t.get("killzone", "UNKNOWN")
        if kz not in kz_groups:
            kz_groups[kz] = {"count": 0, "wins": 0, "pnl_pts": 0}
        kz_groups[kz]["count"] += 1
        if _is_win(t):
            kz_groups[kz]["wins"] += 1
        kz_groups[kz]["pnl_pts"] += _safe_float(t.get("pnl_pts"))

    # Setup type breakdown
    setup_groups: dict = {}
    for t in day_trades:
        st = t.get("setup_type", "MANUAL")
        if st not in setup_groups:
            setup_groups[st] = {"count": 0, "wins": 0, "pnl_pts": 0}
        setup_groups[st]["count"] += 1
        if _is_win(t):
            setup_groups[st]["wins"] += 1
        setup_groups[st]["pnl_pts"] += _safe_float(t.get("pnl_pts"))

    # Pillar attribution
    pillar_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    pillar_wins = {0: 0, 1: 0, 2: 0, 3: 0}
    for t in day_trades:
        pp = _safe_int(t.get("pillars_passed"))
        pp = min(pp, 3)
        pillar_counts[pp] += 1
        if _is_win(t):
            pillar_wins[pp] += 1

    # Observations
    observations = []
    wr = round(len(wins) / len(day_trades) * 100) if day_trades else 0
    if wr >= 60:
        observations.append(f"Win rate {wr}% — above target")
    elif wr < 40:
        observations.append(f"Win rate {wr}% — below minimum threshold")

    avg_mae = round(sum(maes) / len(maes), 2) if maes else 0
    avg_mfe = round(sum(mfes) / len(mfes), 2) if mfes else 0
    if avg_mae > 0 and avg_mfe > 0 and avg_mae > avg_mfe * 0.8:
        observations.append(f"MAE ({avg_mae}) close to MFE ({avg_mfe}) — entries may be late")

    best_kz = max(kz_groups.items(), key=lambda x: x[1]["pnl_pts"]) if kz_groups else None
    if best_kz:
        observations.append(f"Best killzone: {best_kz[0]} ({best_kz[1]['pnl_pts']:+.1f}pt)")

    return {
        "date": target_date,
        "trade_count": len(day_trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": wr,
        "total_pnl_pts": round(total_pnl, 2),
        "total_pnl_usd": round(total_usd, 2),
        "avg_mae_pts": avg_mae,
        "avg_mfe_pts": avg_mfe,
        "avg_risk_pts": round(sum(_safe_float(t.get("risk_pts")) for t in day_trades) / len(day_trades), 2) if day_trades else 0,
        "avg_duration_min": round(sum(_safe_float(t.get("duration_min")) for t in day_trades) / len(day_trades), 1) if day_trades else 0,
        "killzone_breakdown": kz_groups,
        "setup_type_breakdown": setup_groups,
        "pillar_attribution": {
            str(k): {"count": pillar_counts[k], "wins": pillar_wins[k],
                     "wr": round(pillar_wins[k] / pillar_counts[k] * 100) if pillar_counts[k] > 0 else 0}
            for k in range(4)
        },
        "observations": observations,
        "trades": day_trades,
    }


# ── Weekly Report ────────────────────────────────────────────────────────

def compute_weekly_report(trades: list, week_start: str) -> dict:
    """Compute weekly analytics from week_start (Monday) to +6 days."""
    try:
        ws = datetime.strptime(week_start, "%Y-%m-%d").date()
    except ValueError:
        ws = date.today() - timedelta(days=date.today().weekday())

    we = ws + timedelta(days=6)
    week_trades = [t for t in trades
                   if ws.isoformat() <= _trade_date(t) <= we.isoformat()]

    if not week_trades:
        return {"week_start": ws.isoformat(), "week_end": we.isoformat(),
                "trade_count": 0, "observations": ["No trades this week"]}

    wins = [t for t in week_trades if _is_win(t)]
    wr = round(len(wins) / len(week_trades) * 100) if week_trades else 0
    total_pnl = sum(_safe_float(t.get("pnl_pts")) for t in week_trades)

    # Pillar correlation with win rate
    pillar_wr: dict = {}
    for pp in range(4):
        group = [t for t in week_trades if _safe_int(t.get("pillars_passed")) == pp]
        if group:
            w = len([t for t in group if _is_win(t)])
            pillar_wr[str(pp)] = {"count": len(group), "wins": w,
                                  "wr": round(w / len(group) * 100)}

    # Daily breakdown
    daily: dict = {}
    for t in week_trades:
        d = _trade_date(t)
        if d not in daily:
            daily[d] = {"count": 0, "wins": 0, "pnl_pts": 0}
        daily[d]["count"] += 1
        if _is_win(t):
            daily[d]["wins"] += 1
        daily[d]["pnl_pts"] += _safe_float(t.get("pnl_pts"))

    # Threshold recommendations
    recs = []
    if wr < 50 and len(week_trades) >= 5:
        recs.append("Win rate below 50% — consider tighter P1 ZONE criteria")
    maes = [_safe_float(t.get("mae_pts")) for t in week_trades if t.get("mae_pts")]
    if maes and sum(maes) / len(maes) > 4:
        recs.append(f"Avg MAE {sum(maes)/len(maes):.1f}pt — stops may be too wide")

    observations = []
    if len(week_trades) >= 18:
        observations.append(f"18+ trade window reached ({len(week_trades)} trades) — statistical significance improving")
    observations.append(f"Weekly P&L: {total_pnl:+.1f}pt")

    return {
        "week_start": ws.isoformat(),
        "week_end": we.isoformat(),
        "trade_count": len(week_trades),
        "wins": len(wins),
        "win_rate": wr,
        "total_pnl_pts": round(total_pnl, 2),
        "total_pnl_usd": round(total_pnl * 5, 2),
        "pillar_correlation": pillar_wr,
        "daily_breakdown": daily,
        "threshold_recommendations": recs,
        "observations": observations,
    }


# ── Pattern Analysis ─────────────────────────────────────────────────────

def compute_pattern_analysis(trades: list) -> dict:
    """Setup Quality Matrix, MAE/MFE distributions, Exit Efficiency."""
    if not trades:
        return {"trade_count": 0, "quality_matrix": [], "mae_mfe_dist": {},
                "exit_efficiency": {}, "observations": []}

    # Quality Matrix: WR by (setup_type × killzone)
    combos: dict = {}
    for t in trades:
        key = f"{t.get('setup_type', 'MANUAL')}|{t.get('killzone', 'UNKNOWN')}"
        if key not in combos:
            combos[key] = {"count": 0, "wins": 0, "pnl_pts": 0, "mae_sum": 0, "mfe_sum": 0}
        combos[key]["count"] += 1
        if _is_win(t):
            combos[key]["wins"] += 1
        combos[key]["pnl_pts"] += _safe_float(t.get("pnl_pts"))
        combos[key]["mae_sum"] += _safe_float(t.get("mae_pts"))
        combos[key]["mfe_sum"] += _safe_float(t.get("mfe_pts"))

    quality_matrix = []
    for key, v in sorted(combos.items(), key=lambda x: -x[1]["count"]):
        setup, kz = key.split("|")
        wr = round(v["wins"] / v["count"] * 100) if v["count"] > 0 else 0
        quality_matrix.append({
            "setup_type": setup, "killzone": kz,
            "count": v["count"], "wins": v["wins"], "wr": wr,
            "avg_pnl_pts": round(v["pnl_pts"] / v["count"], 2),
            "avg_mae": round(v["mae_sum"] / v["count"], 2) if v["count"] else 0,
            "avg_mfe": round(v["mfe_sum"] / v["count"], 2) if v["count"] else 0,
        })

    # MAE/MFE distribution buckets
    mae_buckets = {"0-2": 0, "2-4": 0, "4-6": 0, "6-8": 0, "8+": 0}
    mfe_buckets = {"0-2": 0, "2-4": 0, "4-6": 0, "6-8": 0, "8+": 0}
    for t in trades:
        mae = _safe_float(t.get("mae_pts"))
        mfe = _safe_float(t.get("mfe_pts"))
        for val, buckets in [(mae, mae_buckets), (mfe, mfe_buckets)]:
            if val < 2: buckets["0-2"] += 1
            elif val < 4: buckets["2-4"] += 1
            elif val < 6: buckets["4-6"] += 1
            elif val < 8: buckets["6-8"] += 1
            else: buckets["8+"] += 1

    # Exit efficiency: pnl / mfe (how much of the move was captured)
    efficiencies = []
    for t in trades:
        mfe = _safe_float(t.get("mfe_pts"))
        pnl = _safe_float(t.get("pnl_pts"))
        if mfe > 0:
            efficiencies.append(round(pnl / mfe * 100))

    avg_eff = round(sum(efficiencies) / len(efficiencies)) if efficiencies else 0

    # Exit type breakdown
    exit_types: dict = {}
    for t in trades:
        et = t.get("close_reason", "UNKNOWN")
        if et not in exit_types:
            exit_types[et] = {"count": 0, "avg_pnl": 0, "total_pnl": 0}
        exit_types[et]["count"] += 1
        exit_types[et]["total_pnl"] += _safe_float(t.get("pnl_pts"))
    for et in exit_types:
        if exit_types[et]["count"] > 0:
            exit_types[et]["avg_pnl"] = round(exit_types[et]["total_pnl"] / exit_types[et]["count"], 2)

    observations = []
    if avg_eff < 40:
        observations.append(f"Exit efficiency {avg_eff}% — exiting too early, leaving money on table")
    elif avg_eff > 80:
        observations.append(f"Exit efficiency {avg_eff}% — excellent capture rate")
    if quality_matrix:
        best = max(quality_matrix, key=lambda x: x["wr"])
        if best["count"] >= 3:
            observations.append(f"Best combo: {best['setup_type']}+{best['killzone']} WR={best['wr']}% ({best['count']} trades)")

    return {
        "trade_count": len(trades),
        "quality_matrix": quality_matrix,
        "mae_mfe_dist": {"mae": mae_buckets, "mfe": mfe_buckets},
        "exit_efficiency": {
            "avg_pct": avg_eff,
            "distribution": efficiencies,
        },
        "exit_type_breakdown": exit_types,
        "observations": observations,
    }
