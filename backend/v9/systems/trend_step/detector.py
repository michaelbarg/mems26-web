"""trend_step.detector — H15 TREND_STEP_ENTRY_V1 (live port, 2026-08-14).

Michael 13.08: "שוב יש מדרגה למעלה שהמערכת לא זיהתה — זה בסדר?" — no. On a
stair-stepping session (11.08: four down-steps, 13.08: 7798→7814 in two up-steps)
NO detector produced a candidate: S2/S4 look for their own shapes, and LEG_RIDE
only EXEMPTS existing signals from gates — it never creates one.

This is a byte-faithful port of the causal detector proven on the archive in
`scripts/replay_trend_step_entry.py::detect_trend_step` (§9 study). Same zigzag,
same impulse/pause/retracement geometry, same LSMA + volume agreement, same
parameters — only the I/O changed (live DB bars instead of a replay frame).
Stops/targets are NOT computed here: the gateway's step-scaled ladder (F3/H6,
same swing-leg measure) owns them.

Flag TREND_STEP_ENTRY_V1 (default OFF). Every candidate still passes the full
gateway chain — this adds a producer, it does not bypass a single gate.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TICK = 0.25

# Parameters — identical to the replay defaults (env-tunable with the same names)
P: Dict[str, Any] = dict(
    ZZ_REV=5.0, REQUIRE_STAIR=0, SESSION_EXT_TOL=0.0,
    IMP_MIN=8.0, IMP_MAX=45.0, IMP_BARS_MAX=10,
    PAUSE_MIN=1, PAUSE_MAX=3, RETR_MIN=0.20, RETR_MAX=0.55,
    LSMA_SLOPE_MIN=0.15, REQUIRE_LSMA_SIDE=0, VOL_RATIO_MAX=1.10,
    REQUIRE_EXHAUST=0, CUTOFF="15:00",
)


def enabled() -> bool:
    return os.getenv("TREND_STEP_ENTRY_V1", "0").lower() in ("1", "true", "yes")


def _p() -> Dict[str, Any]:
    out = dict(P)
    for k in list(out):
        v = os.getenv(f"TSE_{k}")
        if v is not None:
            try:
                out[k] = type(P[k])(v)
            except Exception:
                pass
    return out


def zigzag(bars: List[Dict], rev: float) -> List[Tuple[int, float, str]]:
    """Causal zigzag pivots — identical construction to the replay."""
    n = len(bars)
    if n < 2:
        return []
    hi_i, hi_p = 0, bars[0]["h"]
    lo_i, lo_p = 0, bars[0]["l"]
    direction, piv, start = 0, [], n
    for i in range(1, n):
        b = bars[i]
        if b["h"] > hi_p:
            hi_i, hi_p = i, b["h"]
        if b["l"] < lo_p:
            lo_i, lo_p = i, b["l"]
        if hi_p - lo_p >= rev and hi_i != lo_i:
            if lo_i < hi_i:
                direction, piv = 1, [(lo_i, bars[lo_i]["l"], "L")]
                hi_i, hi_p = lo_i, bars[lo_i]["h"]
                for j in range(lo_i, i + 1):
                    if bars[j]["h"] > hi_p:
                        hi_i, hi_p = j, bars[j]["h"]
            else:
                direction, piv = -1, [(hi_i, bars[hi_i]["h"], "H")]
                lo_i, lo_p = hi_i, bars[hi_i]["l"]
                for j in range(hi_i, i + 1):
                    if bars[j]["l"] < lo_p:
                        lo_i, lo_p = j, bars[j]["l"]
            start = i + 1
            break
    if direction == 0:
        return []
    for i in range(start, n):
        b = bars[i]
        if direction == 1:
            if b["h"] > hi_p:
                hi_i, hi_p = i, b["h"]
            if i > hi_i and hi_p - b["l"] >= rev:
                piv.append((hi_i, hi_p, "H"))
                direction = -1
                lo_i, lo_p = i, b["l"]
                for j in range(hi_i + 1, i + 1):
                    if bars[j]["l"] < lo_p:
                        lo_i, lo_p = j, bars[j]["l"]
        else:
            if b["l"] < lo_p:
                lo_i, lo_p = i, b["l"]
            if i > lo_i and b["h"] - lo_p >= rev:
                piv.append((lo_i, lo_p, "L"))
                direction = 1
                hi_i, hi_p = i, b["h"]
                for j in range(lo_i + 1, i + 1):
                    if bars[j]["h"] > hi_p:
                        hi_i, hi_p = j, bars[j]["h"]
    piv.append((hi_i, hi_p, "H") if direction == 1 else (lo_i, lo_p, "L"))
    return piv


def detect_trend_step(bars: List[Dict], i: Optional[int] = None,
                      p: Optional[Dict] = None) -> Optional[Dict]:
    """Return a setup dict if bar `i` (default: last, already closed) is a
    TREND_STEP entry. Causal: only bars[0..i] are ever read."""
    p = p or _p()
    if not bars:
        return None
    i = len(bars) - 1 if i is None else i
    if i < 4:
        return None
    if bars[i].get("hhmm") and bars[i]["hhmm"] > p["CUTOFF"]:
        return None
    piv = zigzag(bars[:i + 1], float(p["ZZ_REV"]))
    if len(piv) < 2:
        return None

    for direction in ("SHORT", "LONG"):
        want = "L" if direction == "SHORT" else "H"
        k = None
        for j in range(len(piv) - 1, -1, -1):
            if piv[j][2] == want:
                k = j
                break
        if k is None or k == 0:
            continue
        ext_i, ext_p, _ = piv[k]
        org_i, org_p, org_k = piv[k - 1]
        if org_k == want:
            continue
        imp = (org_p - ext_p) if direction == "SHORT" else (ext_p - org_p)
        if not (p["IMP_MIN"] <= imp <= p["IMP_MAX"]):
            continue
        if ext_i - org_i > p["IMP_BARS_MAX"] or ext_i <= org_i:
            continue

        if p["REQUIRE_STAIR"] and k >= 3:
            prev_ext_p, prev_org_p = piv[k - 2][1], piv[k - 3][1]
            stair = ((ext_p < prev_ext_p and org_p < prev_org_p) if direction == "SHORT"
                     else (ext_p > prev_ext_p and org_p > prev_org_p))
            if not stair:
                continue

        # the step must be pushing the SESSION extreme (anti-rotation)
        if p["SESSION_EXT_TOL"] >= 0:
            if direction == "SHORT":
                sess = min(bars[j]["l"] for j in range(0, i + 1))
                if ext_p > sess + p["SESSION_EXT_TOL"]:
                    continue
            else:
                sess = max(bars[j]["h"] for j in range(0, i + 1))
                if ext_p < sess - p["SESSION_EXT_TOL"]:
                    continue

        pause_bars = i - ext_i
        if not (p["PAUSE_MIN"] <= pause_bars <= p["PAUSE_MAX"]):
            continue
        if direction == "SHORT":
            pause_ext = max(bars[j]["h"] for j in range(ext_i, i + 1))
            retr = (pause_ext - ext_p) / imp
        else:
            pause_ext = min(bars[j]["l"] for j in range(ext_i, i + 1))
            retr = (ext_p - pause_ext) / imp
        if not (p["RETR_MIN"] <= retr <= p["RETR_MAX"]):
            continue

        l_now, l_prev = bars[i].get("lsma"), bars[max(0, i - 3)].get("lsma")
        if l_now is None or l_prev is None:
            continue
        slope = (l_now - l_prev) / 3.0
        if direction == "SHORT" and slope > -p["LSMA_SLOPE_MIN"]:
            continue
        if direction == "LONG" and slope < p["LSMA_SLOPE_MIN"]:
            continue
        if p["REQUIRE_LSMA_SIDE"]:
            if direction == "SHORT" and bars[i]["c"] > l_now:
                continue
            if direction == "LONG" and bars[i]["c"] < l_now:
                continue

        iv = [bars[j].get("v", 0) for j in range(org_i + 1, ext_i + 1)]
        pv = [bars[j].get("v", 0) for j in range(ext_i + 1, i + 1)]
        if iv and pv and sum(iv):
            if (sum(pv) / len(pv)) / (sum(iv) / len(iv)) > p["VOL_RATIO_MAX"]:
                continue

        if p["REQUIRE_EXHAUST"]:
            prev = bars[i - 1]
            if direction == "SHORT":
                if not (bars[i]["h"] <= prev["h"] and bars[i]["c"] <= prev["c"]):
                    continue
            else:
                if not (bars[i]["l"] >= prev["l"] and bars[i]["c"] >= prev["c"]):
                    continue

        return {
            "direction": direction,
            "entry_price": bars[i]["c"],
            "impulse_pts": round(imp, 2),
            "pause_bars": pause_bars,
            "retracement": round(retr, 3),
            "step_extreme": ext_p,
            "pause_extreme": pause_ext,
            "lsma_slope": round(slope, 3),
            "reason": (f"stair {direction}: impulse {imp:.1f}pt in {ext_i - org_i} bars, "
                       f"pause {pause_bars} bars, retrace {retr:.0%}, LSMA slope {slope:+.2f}"),
        }
    return None


def live_bars(limit: int = 60) -> List[Dict]:
    """Today's RTH 5-min bars from the CANONICAL table (SOURCE_OF_TRUTH)."""
    from backend.v9.db.read import read_all
    rows = read_all(
        "SELECT ts, open, high, low, close, volume, lsma_value "
        "FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date = "
        "(now() AT TIME ZONE 'America/New_York')::date "
        "AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30' "
        "ORDER BY ts", {})
    out: List[Dict] = []
    for r in rows or []:
        ts = r["ts"]
        try:
            from zoneinfo import ZoneInfo
            hhmm = ts.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M")
        except Exception:
            hhmm = "00:00"
        out.append({
            "h": float(r["high"]), "l": float(r["low"]), "c": float(r["close"]),
            "o": float(r["open"]), "v": float(r["volume"] or 0),
            "lsma": float(r["lsma_value"]) if r.get("lsma_value") is not None else None,
            "hhmm": hhmm,
        })
    return out[-limit:]


def build_setup() -> Optional[Dict]:
    """Live entry point: detect on today's closed bars → gateway setup dict.
    Returns None when the flag is off, data is missing, or no step is present."""
    if not enabled():
        return None
    try:
        bars = live_bars()
        if len(bars) < 6:
            return None
        d = detect_trend_step(bars)
        if not d:
            return None
        logger.warning("[TrendStep] CANDIDATE %s @%.2f — %s",
                       d["direction"], d["entry_price"], d["reason"])
        return {
            "firing_system": 4,
            "direction": d["direction"],
            "classification": "TREND_STEP",
            "pattern": "TREND_STEP",
            "confidence": 0.75,
            "entry_price": d["entry_price"],
            "stop": None,   # gateway step-scaled ladder (F3/H6) owns stop+targets
            "t1": None, "t2": None, "t3": None,
            "metadata": {
                "pattern": "TREND_STEP",
                "trend_step": True,
                "impulse_pts": d["impulse_pts"],
                "pause_bars": d["pause_bars"],
                "retracement": d["retracement"],
                "reason": d["reason"],
            },
        }
    except Exception as e:
        logger.warning("[TrendStep] detector errored (no candidate): %s", e)
        return None
