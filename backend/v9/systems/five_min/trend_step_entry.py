"""trend_step_entry — H15: the missing STAIR-CONTINUATION entry generator.

Michael 13.08: "שוב מדרגה למעלה שהמערכת לא זיהתה — זה בסדר?" — no, it is not.
On 13.08 the tape climbed 7798→7814 in two clean steps with a textbook pause
and NEITHER machine produced a single candidate: S2/S4 detect their own shapes
(ZLR needs its pullback, GB100 its setup), and LEG_RIDE only EXEMPTS existing
signals from gates — it never creates one. When the market simply walks up (or
down) in steps, the system was mute.

This module ports the causal detector proven on the archive in
`scripts/replay_trend_step_entry.py::detect_trend_step` (the §9 analysis that
also produced the step-ladder geometry F3/H6 uses). It is a pure function:
bars in, setup-or-None out. Nothing here reaches the gateway until a caller is
wired behind TREND_STEP_ENTRY_V1 (default OFF) — build → replay → Michael's
ruling → enable, per the standing protocol.

Causal by construction: only bars[0..i] are ever read, so a replay over
historical bars produces exactly what live would have produced.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Defaults from the winning replay configuration (do NOT retune without a replay)
DEFAULTS: Dict[str, Any] = {
    "ZZ_REV": 5.0,            # pt — swing reversal that defines a step
    "IMP_MIN": 6.0,           # min impulse size (pt)
    "IMP_MAX": 40.0,          # max impulse size (pt)
    "IMP_BARS_MAX": 8,        # impulse must complete within N bars
    "REQUIRE_STAIR": True,    # must extend an existing staircase
    "SESSION_EXT_TOL": 3.0,   # step must be pushing the session extreme (pt)
    "PAUSE_MIN": 1,           # pause length after the step (bars)
    "PAUSE_MAX": 4,
    "RETR_MAX": 0.62,         # pause retracement of the impulse
    "CUTOFF": 1500,           # hhmm ET — no entries after 15:00
}


def _hl(b: Dict) -> Tuple[float, float]:
    return (float(b.get("h", b.get("high", 0))),
            float(b.get("l", b.get("low", 0))))


def zigzag(bars: List[Dict], rev: float) -> List[Tuple[int, float, str]]:
    """Causal zigzag pivots — identical construction to the §9 replay."""
    n = len(bars)
    if n < 2:
        return []
    hi_i, hi_p = 0, _hl(bars[0])[0]
    lo_i, lo_p = 0, _hl(bars[0])[1]
    direction, piv, start = 0, [], n
    for i in range(1, n):
        h, l = _hl(bars[i])
        if h > hi_p:
            hi_i, hi_p = i, h
        if l < lo_p:
            lo_i, lo_p = i, l
        if hi_p - lo_p >= rev and hi_i != lo_i:
            if lo_i < hi_i:
                direction, piv = 1, [(lo_i, _hl(bars[lo_i])[1], "L")]
                hi_i, hi_p = lo_i, _hl(bars[lo_i])[0]
                for j in range(lo_i, i + 1):
                    if _hl(bars[j])[0] > hi_p:
                        hi_i, hi_p = j, _hl(bars[j])[0]
            else:
                direction, piv = -1, [(hi_i, _hl(bars[hi_i])[0], "H")]
                lo_i, lo_p = hi_i, _hl(bars[hi_i])[1]
                for j in range(hi_i, i + 1):
                    if _hl(bars[j])[1] < lo_p:
                        lo_i, lo_p = j, _hl(bars[j])[1]
            start = i + 1
            break
    if direction == 0:
        return []
    for i in range(start, n):
        h, l = _hl(bars[i])
        if direction == 1:
            if h > hi_p:
                hi_i, hi_p = i, h
            if i > hi_i and hi_p - l >= rev:
                piv.append((hi_i, hi_p, "H"))
                direction = -1
                lo_i, lo_p = i, l
                for j in range(hi_i + 1, i + 1):
                    if _hl(bars[j])[1] < lo_p:
                        lo_i, lo_p = j, _hl(bars[j])[1]
        else:
            if l < lo_p:
                lo_i, lo_p = i, l
            if i > lo_i and h - lo_p >= rev:
                piv.append((lo_i, lo_p, "L"))
                direction = 1
                hi_i, hi_p = i, h
                for j in range(lo_i + 1, i + 1):
                    if _hl(bars[j])[0] > hi_p:
                        hi_i, hi_p = j, _hl(bars[j])[0]
    piv.append((hi_i, hi_p, "H") if direction == 1 else (lo_i, lo_p, "L"))
    return piv


def detect_trend_step(bars: List[Dict], i: int,
                      params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    """Return a setup dict if CLOSED bar `i` completes a stair-step entry.

    bars: [{o,h,l,c,v, hhmm(optional ET HHMM int)}, ...] ordered by time.
    Only bars[0..i] are read (causal).
    """
    p = dict(DEFAULTS)
    if params:
        p.update(params)
    if i < 4 or i >= len(bars):
        return None
    hhmm = bars[i].get("hhmm")
    if hhmm is not None and hhmm > p["CUTOFF"]:
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

        # stair structure: this step must extend an existing staircase
        stair = None
        if k >= 3:
            prev_ext_p, prev_org_p = piv[k - 2][1], piv[k - 3][1]
            stair = ((ext_p < prev_ext_p and org_p < prev_org_p) if direction == "SHORT"
                     else (ext_p > prev_ext_p and org_p > prev_org_p))
        if p["REQUIRE_STAIR"] and not stair:
            continue

        # must be pushing the SESSION extreme (inverse of extreme_chase_guard:
        # on a stair day, proximity to the extreme IS the setup)
        if p["SESSION_EXT_TOL"] >= 0:
            if direction == "SHORT":
                sess = min(_hl(bars[j])[1] for j in range(0, i + 1))
                if ext_p > sess + p["SESSION_EXT_TOL"]:
                    continue
            else:
                sess = max(_hl(bars[j])[0] for j in range(0, i + 1))
                if ext_p < sess - p["SESSION_EXT_TOL"]:
                    continue

        # pause geometry
        pause_bars = i - ext_i
        if not (p["PAUSE_MIN"] <= pause_bars <= p["PAUSE_MAX"]):
            continue
        if direction == "SHORT":
            pause_ext = max(_hl(bars[j])[0] for j in range(ext_i, i + 1))
            retr = (pause_ext - ext_p) / imp if imp else 1.0
        else:
            pause_ext = min(_hl(bars[j])[1] for j in range(ext_i, i + 1))
            retr = (ext_p - pause_ext) / imp if imp else 1.0
        if retr > p["RETR_MAX"]:
            continue

        entry = float(bars[i].get("c", bars[i].get("close", 0)))
        setup = {
            "pattern": "TREND_STEP",
            "classification": "TREND_STEP",
            "direction": direction,
            "entry_price": entry,
            "step_impulse": round(imp, 2),
            "pause_bars": pause_bars,
            "retracement": round(retr, 3),
            "stair": bool(stair),
            "metadata": {"source": "trend_step_entry", "bar_index": i},
        }
        logger.info("[TrendStep] %s entry=%.2f imp=%.1f pause=%d retr=%.2f stair=%s",
                    direction, entry, imp, pause_bars, retr, stair)
        return setup
    return None
