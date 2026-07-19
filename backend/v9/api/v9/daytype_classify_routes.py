"""V9 API: run the NEW relative day-type classifier over a historical day (read-only).

GET /api/v9/day_type/classify_replay?date=YYYY-MM-DD
  → the classifier's day-type TIMELINE (segments) for that date, so the Day-Type
    Labeler can show the auto-classifier's guess next to the human label.

Uses only the pure feature + classifier modules + the existing replay bar source
(_bars_for_date handles the contract roll). Touches no live state, synthesizes
nothing (Rule 1). dd_second_dist is not computed yet (TPO single-print pending),
so Trend_DD will not fire from this endpoint yet — honest, not faked.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from backend.v9.db.read import read_all, read_one, read_scalar
from backend.v9.api.v9.chart_replay_routes import _bars_for_date
from backend.v9.systems.day_type.relative_features import compute_relative_features
from backend.v9.systems.day_type.cvd_features import compute_cvd_features
from backend.v9.systems.day_type.context_features import (
    ib_width_percentile, open_location, poc_drift,
)  # second_distribution removed — dead POC-jump proxy, superseded by dd_features (2026-06-20)
from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type
from backend.v9.systems.day_type.dd_features import detect_double_distribution
from backend.v9.systems.day_type.daytype_classifier import classify, load_plan, smooth_confidence
from backend.v9.systems.day_type.classifier_core import classify_session

router = APIRouter(prefix="/api/v9/day_type", tags=["v9-daytype-classify"])
_ET = ZoneInfo("America/New_York")
_CT = ZoneInfo("America/Chicago")


@router.get("/direction_now")
def direction_now() -> Dict[str, Any]:
    """Read-only CURRENT direction (UP/DOWN/NEUTRAL) from CVD + location + breakout-state
    on today's RTH 5-min bars. DISPLAY ONLY — does not affect any trading decision.
    Prototype of the #68 direction-context; honest (Rule 1): NEUTRAL when data/IB missing.
    """
    # Delegate to the hardened live helper (fresh-with-fallback: v9_bars_5min for CVD,
    # else the live v9_bars_5min_woodies when the raw-bars stream stalls — 2026-06-22).
    # DISPLAY ONLY — does not affect any trading decision.
    from backend.v9.systems.direction_context_live import current
    return current()


def _as_dt(ts: Any) -> Optional[datetime]:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(str(ts))
    except Exception:
        return None


def _et_min(ts: Any) -> Optional[int]:
    dt = _as_dt(ts)
    if dt is None:
        return None
    et = dt.astimezone(_ET)
    return et.hour * 60 + et.minute


def _hhmm(ts: Any) -> str:
    dt = _as_dt(ts)
    return dt.astimezone(_ET).strftime("%H:%M") if dt else ""


def _ff(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


@router.get("/live")
def day_type_live() -> Dict[str, Any]:
    """Override-aware LIVE day-type — the label the TRADING GATE actually acts on
    (`get_live_day_type`: manual override → live machine → prelock → antiflap).

    GAP G-16 / S124 G5: the UI historically read `classify_replay` (date-based,
    ignores the manual override) → the on-screen day-type could contradict the
    gate when Michael set a `DAY_TYPE_MANUAL_OVERRIDE`. The UI now overlays THIS
    value for the displayed label. Secret-free (no key). Never raises → {None}."""
    try:
        from backend.v9.services.trade_context import get_live_day_type
        dt = get_live_day_type()
        return {"day_type": dt, "source": "get_live_day_type"}
    except Exception as e:  # display endpoint must never 500
        return {"day_type": None, "source": "error", "error": str(e)}


@router.get("/classify_replay")
def classify_replay(date: str = Query(..., description="ET trading date, YYYY-MM-DD")):
    rows, source = _bars_for_date(date)
    rth = []
    for r in rows:
        m = _et_min(r["ts"])
        o, h, l, c = _ff(r["o"]), _ff(r["h"]), _ff(r["l"]), _ff(r["c"])
        if m is None or not (570 <= m < 960) or None in (o, h, l, c):
            continue
        rth.append({"o": o, "h": h, "l": l, "c": c, "v": _ff(r["v"]), "cum": _ff(r["cum_delta"]), "ts": r["ts"]})
    if not rth:
        return {"date": date, "n_bars": 0, "segments": [], "final": None, "note": "no RTH bars"}

    n = len(rth)
    open_price = rth[0]["o"]

    def _ib(k: int):
        kk = min(k, n)
        return max(b["h"] for b in rth[:kk]), min(b["l"] for b in rth[:kk])

    ib6_h, ib6_l = _ib(6)      # provisional IB (30 min) — drives the 30→60 min commitment
    ib12_h, ib12_l = _ib(12)   # structural IB (60 min) — bar fallback
    ib_source = "bars"
    # Prefer Sierra's TPO IB (accurate, per-contract — Michael 2026-06-20): never recompute when Sierra has it.
    sib = read_one(
        "SELECT ib_high, ib_low, profile_shape, vah_price, val_price FROM v9_tpo_sessions "
        "WHERE trading_date = :date AND session_type = 'CASH' ORDER BY id DESC LIMIT 1",
        {"date": date},
    )
    profile_shape = (sib or {}).get("profile_shape")
    va_width = None
    if sib and _ff(sib.get("vah_price")) is not None and _ff(sib.get("val_price")) is not None:
        va_width = round(_ff(sib["vah_price"]) - _ff(sib["val_price"]), 2)
    if sib and _ff(sib.get("ib_high")) is not None and _ff(sib.get("ib_low")) is not None:
        ib12_h, ib12_l = _ff(sib["ib_high"]), _ff(sib["ib_low"])
        ib_source = "sierra_tpo"

    hist = read_all(
        "SELECT ib_width FROM v9_day_type_history WHERE date < :date AND ib_width IS NOT NULL",
        {"date": date},
    )
    ib_hist = [float(r["ib_width"]) for r in hist if r.get("ib_width") is not None]
    ibp6 = ib_width_percentile(ib6_h - ib6_l, ib_hist)
    ibp12 = ib_width_percentile(ib12_h - ib12_l, ib_hist)

    # session volume vs the trailing-day median (the LOW-participation signal → Nontrend)
    session_vol = sum(b["v"] for b in rth if b.get("v") is not None)
    vol_rows = read_all(
        "SELECT sum(volume) AS vol FROM v9_bars_5min_woodies WHERE symbol='MES' "
        "AND (ts AT TIME ZONE 'America/New_York')::date < :date "
        "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
        "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
        "GROUP BY (ts AT TIME ZONE 'America/New_York')::date "
        "HAVING count(*) >= 60",   # only COMPLETE RTH days — a baseline of partial days gave 20-69x junk
        {"date": date},
    )
    vols = sorted(float(r["vol"]) for r in vol_rows if r.get("vol") is not None)
    med_vol = vols[len(vols) // 2] if len(vols) >= 3 else None  # need >=3 complete days for a stable median
    vol_ratio = round(session_vol / med_vol, 3) if med_vol and med_vol > 0 else None

    # --- P2 context features (built modules, now fed to the classifier) ---
    prior_date = read_scalar(
        "SELECT max((ts AT TIME ZONE 'America/New_York')::date) FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date < :date AND symbol='MES'",
        {"date": date},
    )
    pdh = pdl = pvah = pval = None
    if prior_date is not None:
        pd_iso = prior_date.isoformat() if hasattr(prior_date, "isoformat") else str(prior_date)
        hl = read_one(
            "SELECT max(high) AS h, min(low) AS l FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = :pd AND symbol='MES'",
            {"pd": pd_iso},
        )
        pdh, pdl = _ff((hl or {}).get("h")), _ff((hl or {}).get("l"))
        pv = read_one(
            "SELECT poc_price AS poc, vah_price AS vah, val_price AS val FROM v9_tpo_sessions "
            "WHERE trading_date = :pd ORDER BY id DESC LIMIT 1",
            {"pd": pd_iso},
        )
        if pv:
            pvah, pval = _ff(pv.get("vah")), _ff(pv.get("val"))
    tpo_rows = read_all(
        "SELECT poc FROM v9_tpo_history WHERE (ts AT TIME ZONE 'America/New_York')::date = :date ORDER BY ts ASC",
        {"date": date},
    )
    period_pocs = [p for p in (_ff(r.get("poc")) for r in tpo_rows) if p is not None]
    poc_now = period_pocs[-1] if period_pocs else None
    poc_at_ib = period_pocs[1] if len(period_pocs) >= 2 else (period_pocs[0] if period_pocs else None)
    ibw12 = ib12_h - ib12_l
    op = detect_opening_type(rth[:6], open_price, prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl)
    opening_type = op.get("opening_type")
    open_loc = open_location(open_price, pvah, pval, pdh, pdl)
    pocdrift = poc_drift(poc_now, poc_at_ib, ibw12)
    # Double-Distribution: detect the STRUCTURE from the bars (narrow IB + two distributions +
    # single-print neck + new value held) — Sierra's profile_shape said "b" (single) for 06-16/17
    # and missed them. OR Sierra's explicit B/DD label when present. Only matters on one-sided
    # (sides==1) days — the classifier gates it there; a two-sided break is Neutral, not DD.
    ibmed_rows = read_all(
        "SELECT (ib_high - ib_low) AS w FROM v9_tpo_sessions WHERE session_type='CASH' "
        "AND trading_date < :date AND ib_high IS NOT NULL AND ib_low IS NOT NULL "
        "ORDER BY trading_date DESC LIMIT 20", {"date": date})
    ibmeds = sorted(_ff(r["w"]) for r in ibmed_rows if _ff(r.get("w")) is not None)
    ib_median = ibmeds[len(ibmeds) // 2] if ibmeds else None
    dd_bar = detect_double_distribution(rth, ibw12, ib_median)
    sierra_dd = (profile_shape or "").strip() in ("B", "DD")
    dd = {"detected": sierra_dd or dd_bar["detected"], "profile_shape": profile_shape,
          "source": "sierra_shape" if sierra_dd else ("bars" if dd_bar["detected"] else None), "bar": dd_bar}

    timeline: List[Dict[str, Any]] = []
    _conf_prev: Optional[float] = None   # N1 RC#3 smoothing state (per-session, this loop)
    for i in range(1, n + 1):
        # progressive IB (no lookahead): 30-min IB until the 60-min IB completes
        if i < 12:
            ibh, ibl = ib6_h, ib6_l
        else:
            ibh, ibl = ib12_h, ib12_l
        # ONE code path with the live engine (P0-1 ACCEPT: "UI==gate==engine one value",
        # Michael 2026-07-12). The hand-assembled feat that used to live here silently
        # missed every doctrine feature added to classifier_core (stair-steps/P1-5,
        # neck-refill/P1-7, open_dir/P0-2, accepted_break/P0-1) — the exact source-split
        # failure class. classify_session recomputes opening/DD per bar-prefix (no
        # lookahead), so the replay now shows what the live engine would have shown.
        res = classify_session(
            bars=rth[:i], ib_high=ibh, ib_low=ibl, open_price=open_price,
            ib_width_hist=ibmeds, profile_shape=profile_shape, vol_ratio=vol_ratio,
            prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl,
            poc_now=poc_now, poc_at_ib=poc_at_ib, is_eod=(i == n),
        )
        # N1 RC#3 (S1_CONF_SMOOTH_V1, default OFF → returns raw unchanged): slew-cap the
        # per-bar confidence so it cannot flap 0.12↔1.00 on adjacent bars. Type untouched.
        _craw = res.get("confidence")
        if _craw is not None:
            _csm = smooth_confidence(_conf_prev, _craw, res.get("day_type") or "")
            if _csm != _craw:
                res["confidence_raw"] = _craw
                res["confidence"] = _csm
            _conf_prev = None if res.get("day_type") == "FORMING" else _csm
        timeline.append({"i": i - 1, "time": _hhmm(rth[i - 1]["ts"]), **res})

    segments: List[Dict[str, Any]] = []
    for t in timeline:
        if (not segments) or segments[-1]["day_type"] != t["day_type"] or segments[-1]["status"] != t["status"]:
            segments.append({"startBar": t["i"], "time": t["time"], "day_type": t["day_type"],
                             "status": t["status"], "direction": t["direction"], "reason": t.get("reason")})

    # P2-10/12 (Michael 07-13): held-extreme range estimate + EOD continuation tag.
    from backend.v9.systems.day_type.day_context_extras import range_estimate, eod_continuation_tag
    _rng_rows = read_all(
        "SELECT (ts AT TIME ZONE 'America/New_York')::date AS d, max(high)-min(low) AS rng "
        "FROM v9_bars_5min_woodies WHERE symbol='MES' "
        "AND (ts AT TIME ZONE 'America/New_York')::date < :date "
        "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
        "AND (ts AT TIME ZONE 'America/New_York')::time < '16:00' "
        "GROUP BY 1 HAVING count(*) >= 60 "
        "ORDER BY d DESC LIMIT 20",   # the 20 most-RECENT complete days (not the 20 smallest!)
        {"date": date})
    _rngs = sorted(float(r["rng"]) for r in _rng_rows if r.get("rng") is not None)
    _med_rng = _rngs[len(_rngs) // 2] if len(_rngs) >= 3 else None
    _range_est = range_estimate(rth, _med_rng)
    _range_est["med_daily_range"] = _med_rng
    _fin = timeline[-1]
    _eod_tag = eod_continuation_tag(_fin.get("day_type"),
                                    (_fin.get("measured") or {}).get("close_pos"),
                                    _fin.get("direction"))

    return {
        "date": date, "n_bars": n, "source": source,
        "ib_high": ib12_h, "ib_low": ib12_l, "ib_width": round(ib12_h - ib12_l, 2), "ib_source": ib_source,
        "ib_pctile": ibp12["pctile"], "ib_class": ibp12["klass"], "ib_pctile_n": ibp12["n"],
        "session_volume": round(session_vol, 0), "vol_ratio": vol_ratio,
        "opening_type": opening_type, "open_location": open_loc, "profile_shape": profile_shape,
        "va_width": va_width, "poc_drift": pocdrift, "second_distribution": dd,
        "pdh": pdh, "pdl": pdl, "prior_vah": pvah, "prior_val": pval,
        "measured": timeline[-1].get("measured", {}),
        # P2-10/12 (Michael 07-13): day-range estimate from the held extreme +
        # the EOD continuation tag (tomorrow's statistical morning bias).
        "range_estimate": _range_est,
        "eod_continuation_tag": _eod_tag,
        "segments": segments, "final": timeline[-1],
    }
