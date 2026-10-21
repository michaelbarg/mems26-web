"""T-624 effort and result (Michael 21.10, on 19.10: "המערכת והעץ היה צריך לזהות בעצם נתיב אחר לפי איך היא מתנהגת
ועליה היה לפנות אליו — כמו עסקאות טקטיות של מערכת 4 או מדרגות שיש להן גם ווליום וגם נר שרואים גודל מאמץ מסוים וגודל
תוצאה — אני רוצה לתקן נתיב").

19.10: the up-extension was accepted at 18:30 and failed at 19:05 (back inside the IB). The tree already knew it (ibr
state failed_up, rel with_failed, turn down) and still refused every System 4 short 19:05–20:45 on tree:bias — the
hint stayed LONG. 19:05 GB100 SHORT's signal bar (19:00) carried 2.1× the volume of the 20 bars before it with a
1.45-ATR bearish body — effort and result — and reached its T1 (+22.5 pt).

Effort = the bar's volume / the mean volume of the `n_avg` closed RTH bars before it. Result = the bar's body IN THE
TRADE DIRECTION in ATR(14) units (negative when the candle closed against the trade).

  label(bars, direction, mode) → "strong" · "weak" · "unknown"
    mode "bar"  : the signal bar (the last CLOSED bar) — strong when effort ≥ k_vol and result ≥ k_body
    mode "step" : the step — an impulse bar in the trade direction among the last `lookback` closed bars with effort ≥
                  k_vol and result ≥ k_body, and every bar after it (the pullback) on effort < 1 (no demand / no supply)
    mode "none" : no filter — "strong" for every candidate (measures the path alone)

Pure functions over today's CLOSED RTH bars, oldest → newest ({o,h,l,c,v} or {open,high,low,close,volume}); no I/O.
Knobs (read only by the gateway caller, which is inert unless TACTICAL_EFFORT_MODE is set): TACTICAL_EFFORT_K_VOL
(1.2) · TACTICAL_RESULT_K_BODY (0.5) · TACTICAL_STEP_LOOKBACK (3) · TACTICAL_EFFORT_N_AVG (20).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Sequence

_ALIAS = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}


def _f(b: Dict[str, Any], k: str) -> Optional[float]:
    v = b.get(k)
    if v is None:
        v = b.get(_ALIAS[k])
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _env_f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def mode() -> str:
    """TACTICAL_EFFORT_MODE: bar · step · none; anything else (unset, 0) ⇒ "" (the feature is not computed)."""
    m = (os.getenv("TACTICAL_EFFORT_MODE", "") or "").strip().lower()
    return m if m in ("bar", "step", "none") else ""


def atr14(bars: Sequence[Dict[str, Any]], i: int, n: int = 14) -> Optional[float]:
    trs = []
    for j in range(max(1, i - n + 1), i + 1):
        p, h, l = _f(bars[j - 1], "c"), _f(bars[j], "h"), _f(bars[j], "l")
        if p is None or h is None or l is None:
            continue
        trs.append(max(h - l, abs(h - p), abs(l - p)))
    return (sum(trs) / len(trs)) if trs else None


def bar_effort_result(bars: Sequence[Dict[str, Any]], i: int, direction: str,
                      n_avg: int = 20) -> Dict[str, Optional[float]]:
    """{effort, result} of bar i (result in the trade direction, ATR units); None where it cannot be read."""
    b = bars[i]
    v = _f(b, "v")
    prev = [x for x in (_f(p, "v") for p in bars[max(0, i - n_avg):i]) if x is not None]
    effort = (v / (sum(prev) / len(prev))) if (v is not None and len(prev) >= 6 and sum(prev) > 0) else None
    o, c = _f(b, "o"), _f(b, "c")
    a = atr14(bars, i)
    body = None if (o is None or c is None) else ((c - o) if direction == "LONG" else (o - c))
    result = (body / a) if (body is not None and a) else None
    return {"effort": None if effort is None else round(effort, 3), "result": None if result is None else round(result, 3)}


def label(bars: Sequence[Dict[str, Any]], direction: Optional[str], mode_: str, *, k_vol: Optional[float] = None,
          k_body: Optional[float] = None, lookback: Optional[int] = None, n_avg: Optional[int] = None) -> Dict[str, Any]:
    """The effort/result reading of a candidate: {"label": strong|weak|unknown, ...the numbers}."""
    d = (direction or "").upper()
    k_vol = _env_f("TACTICAL_EFFORT_K_VOL", 1.2) if k_vol is None else k_vol
    k_body = _env_f("TACTICAL_RESULT_K_BODY", 0.5) if k_body is None else k_body
    lookback = int(_env_f("TACTICAL_STEP_LOOKBACK", 3)) if lookback is None else lookback
    n_avg = int(_env_f("TACTICAL_EFFORT_N_AVG", 20)) if n_avg is None else n_avg
    bars = [b for b in (bars or []) if b]
    if mode_ == "none":
        return {"label": "strong", "mode": "none"}
    if d not in ("LONG", "SHORT") or len(bars) < 8:
        return {"label": "unknown", "mode": mode_}
    last = len(bars) - 1
    if mode_ == "bar":
        er = bar_effort_result(bars, last, d, n_avg)
        if er["effort"] is None or er["result"] is None:
            return dict(er, label="unknown", mode="bar")
        ok = er["effort"] >= k_vol and er["result"] >= k_body
        return dict(er, label="strong" if ok else "weak", mode="bar", bar=last)
    if mode_ == "step":
        for i in range(last, max(last - lookback, 0), -1):
            er = bar_effort_result(bars, i, d, n_avg)
            if er["effort"] is None or er["result"] is None:
                continue
            if er["effort"] >= k_vol and er["result"] >= k_body:
                pull = [bar_effort_result(bars, j, d, n_avg)["effort"] for j in range(i + 1, last + 1)]
                quiet = all(p is not None and p < 1.0 for p in pull)
                return dict(er, label="strong" if quiet else "weak", mode="step", impulse=i,
                            pullback=[None if p is None else round(p, 3) for p in pull])
        return {"label": "weak", "mode": "step"}
    return {"label": "unknown", "mode": mode_}
