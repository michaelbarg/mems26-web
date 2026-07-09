"""direction_context_live — fetch TODAY's RTH bars + CVD + TPO and run the pure
`direction_context` model. Cached ~20s. Used by the live strip endpoint and (flag-gated,
default-OFF) the trading gate. READ-ONLY; honest (Rule 1): NEUTRAL when data/IB missing.
"""
from __future__ import annotations

import os
import time as _time
from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

_CT = ZoneInfo("America/Chicago")
_CACHE: Dict[str, Any] = {}
_STATE_STALE_WARN: Dict[str, float] = {"last": 0.0}


def _warn_if_state_stale(ts: Any, max_age_s: float = 600.0) -> None:
    """SYS-2 (Michael 2026-07-09): v9_day_type_state must never freeze silently. On 07-09 the
    writer died at 16:25 (split-brain: gates rode the flapping in-memory machine while this table
    stayed frozen). If the last write is older than max_age_s, emit a rate-limited WARNING
    (≤ once / 5 min) so a dead writer surfaces immediately instead of feeding a stale value."""
    try:
        import logging as _lg
        import datetime as _dtm
        if ts is None:
            return
        _now = _time.time()
        if _now - _STATE_STALE_WARN.get("last", 0.0) < 300:
            return
        # ts is stored naive-UTC (writer: datetime.now(utc).isoformat(), main.py)
        _t = ts if isinstance(ts, _dtm.datetime) else _dtm.datetime.fromisoformat(str(ts))
        _age = _now - _t.replace(tzinfo=_dtm.timezone.utc).timestamp()
        if _age > max_age_s:
            _STATE_STALE_WARN["last"] = _now
            _lg.getLogger(__name__).warning(
                "[DayType] v9_day_type_state STALE: last write %s (%.0fs ago) — writer may be dead (SYS-2)",
                ts, _age)
    except Exception:
        pass


def sustained_lsma_side(rows, k: int) -> str:
    """Pure: 'UP'/'DOWN' iff the k most-recent (close, lsma_value) rows are ALL on
    the same side of the LSMA; else 'NEUTRAL'. Used by CONT_TREND_FILTER to reject
    a momentary 1-bar poke (chop) — a continuation must hold the trend for k bars.
    `rows` is most-recent-first (ORDER BY ts DESC)."""
    sides = [1 if float(r["close"]) > float(r["lsma_value"]) else -1
             for r in (rows or []) if r.get("lsma_value") is not None]
    sides = sides[:k]
    if k >= 1 and len(sides) >= k and all(s == sides[0] for s in sides):
        return "UP" if sides[0] == 1 else "DOWN"
    return "NEUTRAL"


def lsma_slope_pts_per_bar(rows, k: int):
    """Pure: LSMA slope in POINTS-PER-BAR over the k most-recent lsma_value rows.
    `rows` is most-recent-first (ORDER BY ts DESC): slope = (newest − oldest)/(n−1),
    positive = rising. Returns None when fewer than 2 lsma values exist (honest
    Rule 1 — never synthesize). Used by LSMA_FLAT_GATE_V1 ("too horizontal" veto,
    Michael 2026-07-08): |slope| < LSMA_FLAT_MIN_SLOPE_PTS ⇒ flat ⇒ block fires.
    Distinct from sustained_lsma_side (SIDE of LSMA): a flat LSMA with price
    hugging one side passes dir_sustained but is still flat here."""
    vals = [float(r["lsma_value"]) for r in (rows or []) if r.get("lsma_value") is not None]
    vals = vals[:max(2, int(k))]
    if len(vals) < 2:
        return None
    return round((vals[0] - vals[-1]) / (len(vals) - 1), 4)


def _fetch_live_bars(today: str):
    """Return (bars, source). Prefer v9_bars_5min (carries CVD); but if the raw-bars
    stream stalls (e.g. 2026-06-22 stuck at 08:55) while the Woodies stream stays
    live, fall back to v9_bars_5min_woodies (correct OHLC, no CVD). Picks whichever
    table has the FRESHER last bar so the strip/gate never reads a dead stream.
    """
    from backend.v9.db.read import read_all
    q = ("SELECT (ts AT TIME ZONE 'America/Chicago')::time ct, high, low, close, %s "
         "FROM %s WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d "
         "AND (ts AT TIME ZONE 'America/Chicago')::time BETWEEN '08:30' AND '15:00' ORDER BY ts")
    try:
        main = read_all(q % ("cumulative_delta", "v9_bars_5min"), {"d": today}) or []
    except Exception:
        main = []
    try:
        wood = read_all(q % ("NULL::numeric AS cumulative_delta", "v9_bars_5min_woodies"), {"d": today}) or []
    except Exception:
        wood = []
    lm = main[-1]["ct"] if main else None
    lw = wood[-1]["ct"] if wood else None
    # Prefer woodies when it is FRESHER, OR equally-fresh but the 5min(cvd) series is
    # gapped/sparse (fewer bars over the same window). A sparse 5min series makes the CVD
    # 3-bar lookback misread (2026-06-22: gap 09:00-09:35 → cvd_slope read +1 off a trough and
    # flipped a real DOWN to NEUTRAL). Use 5min(cvd) only when it is at least as fresh AND at
    # least as complete; otherwise fall to contiguous woodies (location+breakout, no CVD).
    if wood and (lm is None or (lw is not None and (lw > lm or (lw == lm and len(wood) > len(main))))):
        rows, source = wood, "woodies(live,no-cvd)"
    else:
        rows, source = main, "5min(cvd)"
    bars = [{"high": float(b["high"]), "low": float(b["low"]), "close": float(b["close"]),
             "cumulative_delta": (float(b["cumulative_delta"]) if b["cumulative_delta"] is not None else None)}
            for b in rows]
    return bars, source


def current() -> Dict[str, Any]:
    """Current direction-context for today's RTH session (cached ~20s)."""
    today = datetime.now(_CT).date().isoformat()
    if _CACHE.get("date") == today and (_time.time() - _CACHE.get("ts", 0.0)) < 20:
        return _CACHE["val"]

    from backend.v9.db.read import read_one
    from backend.v9.systems.direction_context import compute_direction

    bars, source = _fetch_live_bars(today)

    tpo = None
    try:
        tpo = read_one(
            "SELECT ib_high, ib_low, poc_price FROM v9_tpo_sessions "
            "WHERE trading_date = :d AND session_type='CASH' ORDER BY id DESC LIMIT 1",
            {"d": today})
    except Exception:
        tpo = None
    ibh = tpo.get("ib_high") if tpo else None
    ibl = tpo.get("ib_low") if tpo else None
    poc = tpo.get("poc_price") if tpo else None

    # day_type for the trend-day override (06-16 fix). 2026-07-09: the v9_day_type_state writer
    # died mid-session while the gates rode the flapping in-memory machine (split-brain). Prefer
    # the ONE live source (get_live_day_type, hysteresis-stabilized) when DAYTYPE_ONE_SOURCE_V1 is
    # on (P0-3: engine=UI=gates read one value); otherwise fall back to the table AND warn if it
    # is stale. Default OFF → unchanged (table read).
    day_type = None
    if os.getenv("DAYTYPE_ONE_SOURCE_V1", "0").lower() in ("1", "true", "yes"):
        try:
            from backend.v9.services.trade_context import get_live_day_type as _gldt
            day_type = _gldt()
        except Exception:
            day_type = None
    if day_type is None:
        try:
            _dt = read_one(
                "SELECT day_type, ts FROM v9_day_type_state "
                "WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d ORDER BY id DESC LIMIT 1",
                {"d": today})
            day_type = _dt.get("day_type") if _dt else None
            _warn_if_state_stale(_dt.get("ts") if _dt else None)
        except Exception:
            day_type = None

    # --- Pre-compute lsma_slope (needed by FIX-7 CERT before compute_direction) ---
    lsma_slope = None
    try:
        _fk = max(2, int(os.getenv("LSMA_FLAT_LOOKBACK_BARS", "4") or "4"))
        from backend.v9.db.read import read_all as _slope_ra
        _slope_rows = _slope_ra(
            "SELECT lsma_value FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d AND lsma_value IS NOT NULL "
            "ORDER BY ts DESC LIMIT " + str(_fk), {"d": today})
        lsma_slope = lsma_slope_pts_per_bar(_slope_rows, _fk)
    except Exception:
        lsma_slope = None

    # --- DIRECTION_LSMA_VETO flag: LSMA-lead + CVD-veto direction override ---
    lsma_veto = os.getenv("DIRECTION_LSMA_VETO", "0").lower() in ("1", "true", "yes")
    lsma_side_val = None
    if lsma_veto:
        try:
            _lsma_row = read_one(
                "SELECT close, lsma_value, trend_state FROM v9_bars_5min_woodies "
                "WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d "
                "AND lsma_value IS NOT NULL "
                "ORDER BY ts DESC LIMIT 1",
                {"d": today})
            if _lsma_row and _lsma_row.get("lsma_value") is not None:
                lsma_side_val = 1 if float(_lsma_row["close"]) > float(_lsma_row["lsma_value"]) else -1

                # FIX-7 (incident 333, 21:45): pullback-blindness in the main direction
                # engine. lsma_side=-1 (close < rising LSMA) during a BLUE uptrend →
                # compute_direction returns DOWN → blocks CONT longs in a drive-up day.
                # CERT override: BLUE + slope>0 → force lsma_side=+1 (UP).
                if lsma_side_val < 0 and \
                        os.getenv("CONT_TREND_STATE_CERT_V1", "0").lower() in ("1", "true", "yes"):
                    _ts = str(_lsma_row.get("trend_state", "")).upper()
                    if _ts == "BLUE" and lsma_slope is not None and lsma_slope > 0:
                        import logging as _f7log
                        _f7log.getLogger(__name__).info(
                            "[DirContext] FIX-7 CERT: lsma_side -1→+1 (BLUE + slope=%.4f)",
                            lsma_slope)
                        lsma_side_val = 1
                    elif _ts == "RED" and lsma_slope is not None and lsma_slope < 0:
                        pass  # lsma_side already +1 (above falling LSMA) — no override needed
                # Symmetric: if lsma_side_val > 0 and RED + slope<0, force to -1
                if lsma_side_val > 0 and \
                        os.getenv("CONT_TREND_STATE_CERT_V1", "0").lower() in ("1", "true", "yes"):
                    _ts = str(_lsma_row.get("trend_state", "")).upper()
                    if _ts == "RED" and lsma_slope is not None and lsma_slope < 0:
                        import logging as _f7log
                        _f7log.getLogger(__name__).info(
                            "[DirContext] FIX-7 CERT: lsma_side +1→-1 (RED + slope=%.4f)",
                            lsma_slope)
                        lsma_side_val = -1
        except Exception:
            lsma_side_val = None  # fail-safe: fall through to existing engine

    res = compute_direction(bars=bars, ib_high=ibh, ib_low=ibl, poc=poc, day_type=day_type,
                            lsma_side=lsma_side_val, lsma_veto=lsma_veto)
    out = {
        **res, "n_bars": len(bars), "source": source, "day_type": day_type,
        "ib_high": float(ibh) if ibh is not None else None,
        "ib_low": float(ibl) if ibl is not None else None,
        "poc": float(poc) if poc is not None else None,
    }

    # --- dir_sustained: K-bar SUSTAINED LSMA-side trend gate (for CONT_TREND_FILTER) ---
    # The gateway applies this ONLY to continuation patterns (reversals fire against the
    # trend by design and are exempt). Fixes the BULL_FLAG_LONG bug: a momentary 1-bar
    # poke above LSMA in chop (2026-06-24 10:25) passes the single-bar veto; requiring K
    # consecutive bars on the same side of LSMA rejects chop. UP/DOWN only when all K agree;
    # else NEUTRAL (no sustained trend → continuations blocked).
    dir_sustained = "NEUTRAL"
    try:
        _k = max(2, int(os.getenv("LSMA_SUSTAIN_BARS", "3") or "3"))
        from backend.v9.db.read import read_all as _ra
        # FIX-5 restore: include trend_state for certification mode
        _srows = _ra(
            "SELECT close, lsma_value, trend_state FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/Chicago')::date = :d AND lsma_value IS NOT NULL "
            "ORDER BY ts DESC LIMIT " + str(_k), {"d": today})
        dir_sustained = sustained_lsma_side(_srows, _k)
    except Exception:
        _srows = []
        dir_sustained = "NEUTRAL"  # fail-safe → NEUTRAL (gateway treats as no-trend)
    out["dir_sustained"] = dir_sustained

    # --- lsma_slope_ppb (already computed above for FIX-7; reuse) ---
    out["lsma_slope_ppb"] = lsma_slope

    # FIX-5 (incident 333): CONT_TREND_STATE_CERT_V1 — pullback bars close below
    # the RISING LSMA → sustained returns "DOWN"/"NEUTRAL" even during a BLUE uptrend.
    # Certification: if all K bars are BLUE AND lsma_slope>0 → force UP.
    if dir_sustained == "NEUTRAL" and \
            os.getenv("CONT_TREND_STATE_CERT_V1", "0").lower() in ("1", "true", "yes"):
        try:
            import logging as _cert_log
            _cert_states = [str(r.get("trend_state", "")).upper()
                           for r in (_srows or [])[:_k]]
            if len(_cert_states) >= _k:
                if all(s == "BLUE" for s in _cert_states) and \
                        lsma_slope is not None and lsma_slope > 0:
                    dir_sustained = "UP"
                    out["dir_sustained"] = dir_sustained
                    _cert_log.getLogger(__name__).info(
                        "[DirContext] CERT override: BLUE×%d + slope=%.4f → UP", _k, lsma_slope)
                elif all(s == "RED" for s in _cert_states) and \
                        lsma_slope is not None and lsma_slope < 0:
                    dir_sustained = "DOWN"
                    out["dir_sustained"] = dir_sustained
                    _cert_log.getLogger(__name__).info(
                        "[DirContext] CERT override: RED×%d + slope=%.4f → DOWN", _k, lsma_slope)
        except Exception:
            pass  # fail-safe

    if lsma_veto:
        out["lsma_side"] = lsma_side_val
        out["mode"] = "lsma_cvd_veto" if lsma_side_val is not None else "fallback(lsma_missing)"
    if not bars:
        out["reason"] = "no RTH bars yet (pre-open / forming)"
    _CACHE.update({"date": today, "ts": _time.time(), "val": out})
    return out
