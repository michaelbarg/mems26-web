"""TURN_STATE (T-515, Michael 29.09): has the market turned — right now, from the closed bars of the session?

Michael 29.09 08:20: "המערכת צריכה לזהות שינוי כיוון ולקבל החלטה בזמן אמת — היה תקרה כפולה … המערכת צריכה
לדעת לבצע את השורט בזמן, ובסוף היא קנתה בהיפוך". 28.09: the session high was tested twice (16:30 7775.25,
16:50 7774.75) with a 16.5-pt pullback between, and the second test closed away from it — from 16:55 twelve
short signals (TOUCH2 at the double top, ZLR ×8, VEGAS) all reached target while every long after 16:50 lost;
the system went long twice (16:50, 17:25).

The state is a discrete structural fact, not a score:
  down  — the session HIGH was tested ≥2 times (bars whose high is within `tol` of it), the first and the last
          test are ≥ `min_sep` bars apart with a pullback of ≥ `pull_min` between them, and from the second test
          on some bar CLOSED ≥ `tol` below the high: sellers defended the high. Sticky until a new high is made
          (a new high is a new single-test extreme, so the state resets by construction).
  up    — the mirror at the session LOW.
  range — both are confirmed (Dalton: both extremes defended ⇒ balance; only the edges are trades).
  none  — neither.

turn_rel places a candidate in that state: with / against (down, up) · edge / mid (range) · none.

Pure functions over bars the caller already cut AS-OF (closed bars only — the T-498 lesson: a bar that opened
seconds ago is not evidence). No I/O here.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

_ALIAS = {"h": "high", "l": "low", "c": "close", "o": "open"}


def _f(b: Dict[str, Any], k: str) -> float:
    v = b.get(k)
    if v is None:
        v = b.get(_ALIAS[k])
    return float(v)


def atr_of(bars: Sequence[Dict[str, Any]], n: int = 14) -> Optional[float]:
    """Mean high-low range of the last n closed bars (≥3 bars), else None."""
    rs = [(_f(b, "h") - _f(b, "l")) for b in list(bars)[-n:]]
    return (sum(rs) / len(rs)) if len(rs) >= 3 else None


def _side(bars: List[Dict[str, Any]], top: bool, tol: float, pull_min: float, min_sep: int) -> Optional[Dict[str, Any]]:
    hs = [(_f(b, "h") if top else _f(b, "l")) for b in bars]
    ext = max(hs) if top else min(hs)
    tests = [i for i, v in enumerate(hs) if (v >= ext - tol if top else v <= ext + tol)]
    if len(tests) < 2 or tests[-1] - tests[0] < min_sep:
        return None
    first, last = tests[0], tests[-1]
    between = bars[first + 1:last]
    if not between:
        return None
    pull = (ext - min(_f(b, "l") for b in between)) if top else (max(_f(b, "h") for b in between) - ext)
    if pull < pull_min:
        return None
    # the rejection — sticky: from the SECOND test on, some bar closed ≥ tol away from the extreme
    second = tests[1]
    if not any((_f(b, "c") <= ext - tol) if top else (_f(b, "c") >= ext + tol) for b in bars[second:]):
        return None
    return {"level": ext, "tests": len(tests), "last_test": last, "pullback": round(pull, 2)}


def detect_turn(bars: Sequence[Dict[str, Any]], *, tol: Optional[float] = None, pull_min: Optional[float] = None,
                min_sep: int = 2) -> Dict[str, Any]:
    """bars: today's CLOSED RTH 5-min bars, oldest → newest ({h,l,c} or {high,low,close}).
    tol defaults to max(1.0, 0.25×ATR); pull_min to max(3.0, 0.75×ATR)."""
    bars = [b for b in (bars or []) if b]
    if len(bars) < 3:
        return {"turn": "none"}
    atr = atr_of(bars) or 5.0
    tol = tol if tol is not None else max(1.0, 0.25 * atr)
    pull_min = pull_min if pull_min is not None else max(3.0, 0.75 * atr)
    down = _side(list(bars), True, tol, pull_min, min_sep)
    up = _side(list(bars), False, tol, pull_min, min_sep)
    base = {"tol": round(tol, 2), "pull_min": round(pull_min, 2)}
    if down and up:
        return dict(base, turn="range", top=down["level"], bottom=up["level"])
    if down:
        return dict(base, turn="down", level=down["level"], top=down["level"], tests=down["tests"], pullback=down["pullback"])
    if up:
        return dict(base, turn="up", level=up["level"], bottom=up["level"], tests=up["tests"], pullback=up["pullback"])
    return dict(base, turn="none")


def turn_rel(state: Dict[str, Any], direction: str, entry: Optional[float] = None) -> str:
    """The candidate in that state: with · against (down/up) · edge · mid (range) · none."""
    d = (direction or "").upper()
    t = (state or {}).get("turn", "none")
    if t == "down":
        return "with" if d == "SHORT" else ("against" if d == "LONG" else "none")
    if t == "up":
        return "with" if d == "LONG" else ("against" if d == "SHORT" else "none")
    if t == "range":
        try:
            top, bot, e = float(state["top"]), float(state["bottom"]), float(entry)
        except (TypeError, ValueError, KeyError):
            return "none"
        near = max(float(state.get("tol") or 1.0), 0.25 * (top - bot))
        if d == "SHORT" and e >= top - near:
            return "edge"
        if d == "LONG" and e <= bot + near:
            return "edge"
        return "mid"
    return "none"
