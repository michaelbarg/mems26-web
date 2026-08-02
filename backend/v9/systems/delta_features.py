"""Delta / CVD features for day-type + entry confirmation (DEV_PLAN 02.08 §P2).

Michael's ruling 02.08: footprint enters ("להוסיף את פוטפרינט שחסר כדי שידייק
את זיהוי סוג היום ומיקום נקודות חשובות"). Phase-1 needs NO new exports — the
DLL already ships cumulative_delta.json (per-interval delta `d`, cumulative
`cum`, price `p`, plus its own divergence/trend verdicts).

Research grounding (external research 02.08, sourced):
  R5 — delta-confirmed extension: a range extension WITH the CVD making a
       new session extreme in the break direction is real (supports
       Variation/Trend classification and runner-holding); an extension
       withOUT delta is a failed-auction candidate (supports Neutral/fade).
  R6 — cvd_directionality: |net cum move| / Σ|per-interval delta| — high =
       one-sided conviction day, low = rotation. Order flow leads structure,
       so this can lead the classifier inside the first 30-60 min.
  R3 — delta divergence at a price extreme: price new-extreme on weakening
       delta ⇒ do-not-chase / responsive candidate.

SoT discipline (Rule 1): canonical DLL values only, never synthesized; any
missing field ⇒ None (honest missing), never a guess.

Pure module — no env, no I/O. Caller loads the export and gates on
DELTA_FEATURES_V1.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def _pts(points: Sequence[Dict[str, Any]]) -> List[Dict[str, float]]:
    out = []
    for p in points or []:
        try:
            out.append({"t": float(p["t"]), "d": float(p["d"]),
                        "cum": float(p["cum"]), "p": float(p["p"])})
        except (KeyError, TypeError, ValueError):
            continue
    return out


def cvd_directionality(points: Sequence[Dict[str, Any]]) -> Optional[float]:
    """R6 — |net cumulative move| / sum(|per-interval delta|), in [0,1].
    ~1.0 = one-sided flow (conviction day), ~0.0 = churn (rotation).
    None when the data cannot support the ratio (Rule 1)."""
    pts = _pts(points)
    if len(pts) < 5:
        return None
    gross = sum(abs(p["d"]) for p in pts)
    if gross <= 0:
        return None
    net = abs(pts[-1]["cum"] - pts[0]["cum"])
    return round(min(1.0, net / gross), 3)


def delta_confirms_extension(points: Sequence[Dict[str, Any]],
                             break_dir: str,
                             extreme_frac: float = 0.15) -> Optional[bool]:
    """R5 — is the CVD at/near its own session extreme in the break direction?
    True  = the extension is delta-backed (real range extension).
    False = price extended but flow did not (failed-auction candidate).
    None  = insufficient data (Rule 1).
    `extreme_frac`: the CVD must be within this fraction of its session range
    from the corresponding extreme."""
    pts = _pts(points)
    if len(pts) < 5:
        return None
    cums = [p["cum"] for p in pts]
    c_hi, c_lo = max(cums), min(cums)
    c_rng = c_hi - c_lo
    if c_rng <= 0:
        return None
    cur = cums[-1]
    d = str(break_dir).upper()
    if d in ("UP", "LONG"):
        return bool(cur >= c_hi - extreme_frac * c_rng)
    if d in ("DOWN", "SHORT"):
        return bool(cur <= c_lo + extreme_frac * c_rng)
    return None


def delta_divergence_at_extreme(points: Sequence[Dict[str, Any]],
                                lookback: int = 12) -> Optional[str]:
    """R3 — price new-extreme on weakening flow, over the last `lookback`
    points. Returns "BEARISH" (price high w/o cum high — don't chase longs),
    "BULLISH" (price low w/o cum low — don't chase shorts), or None.
    The DLL exports its own `divergence` verdict too — the caller should
    prefer the canonical field when present and use this only as fallback."""
    pts = _pts(points)
    if len(pts) < lookback:
        return None
    win = pts[-lookback:]
    p_hi_i = max(range(len(win)), key=lambda i: win[i]["p"])
    p_lo_i = min(range(len(win)), key=lambda i: win[i]["p"])
    c_hi_i = max(range(len(win)), key=lambda i: win[i]["cum"])
    c_lo_i = min(range(len(win)), key=lambda i: win[i]["cum"])
    last_q = len(win) - max(3, lookback // 4)
    if p_hi_i >= last_q and c_hi_i < last_q:
        return "BEARISH"
    if p_lo_i >= last_q and c_lo_i < last_q:
        return "BULLISH"
    return None


def extract_features(export: Dict[str, Any]) -> Dict[str, Any]:
    """One call for consumers: canonical passthroughs + computed features.
    Missing ⇒ None everywhere."""
    points = export.get("points") or []
    return {
        # canonical DLL verdicts (SoT — preferred by consumers)
        "dll_divergence": export.get("divergence"),
        "dll_trend": export.get("trend"),
        "session_delta": export.get("session_delta"),
        # computed (phase-1)
        "cvd_directionality": cvd_directionality(points),
        "delta_div_fallback": delta_divergence_at_extreme(points),
    }
