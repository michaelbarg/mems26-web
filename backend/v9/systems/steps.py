"""T-629 — the STEP detector (מדרגה): impulse → pause → test. PURE: no I/O, no env, no clock.

Michael 21.10.2026 21:1x: "המערכת צריכה לזהות מדרגה … ולחכות לבדיקה" — one definition that serves the opening
template (entry at the TEST of the step, stop beyond the step's extreme), the with-extension entries (19:05 /
19:25 on 21.10) and System 6 (trail under the last step whose test held). Everything here is lookahead-free: a
step is CONFIRMED only once its pause has printed `n_pause` closed bars, and a test only on the closed bar that
touched the base and closed back on the step's side.

Vocabulary (an UP step; a DOWN step is the mirror):
  impulse  — within at most `m_bars` consecutive closed bars the close rose by >= `k_impulse` x ATR
             (first close of the window → last close); the impulse EXTREME is the highest high in the window
  pause    — the next >= `n_pause` closed bars after the impulse: overlapping bars whose joint range
             (max high − min low) is <= `r_pause` x impulse size and whose closes stay >= the pause low
             (no close through the base) — the market resting, not reversing
  base     — the lowest low of the pause (the structure that must hold)
  test     — a later closed bar whose LOW probes the base within `tol` (low <= base + tol) and whose CLOSE is
             back above the base (close > base) → the test HELD; a close below base − tol INVALIDATES the step
Parameters are the measurement's business (pre-registered candidates), never tuned here.

Returns plain dicts so the harness, the gateway and tests read the same shape:
  step = {"dir": "UP"|"DOWN", "base": float, "extreme": float, "impulse_pts": float, "i0": int (impulse start),
          "i1": int (impulse end), "p0": int, "p1": int (pause first/last bar), "confirm_i": int (= p1)}
  test = {"i": int, "low"/"high": float, "close": float, "held": True}
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

TICK = 0.25


def _f(b: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = b.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _ohlc(b: Dict[str, Any]):
    return (_f(b, "o", "open"), _f(b, "h", "high"), _f(b, "l", "low"), _f(b, "c", "close"))


def detect_steps(bars: Sequence[Dict[str, Any]], atr: Optional[float], *, k_impulse: float = 1.5,
                 m_bars: int = 3, n_pause: int = 2, r_pause: float = 0.7) -> List[Dict[str, Any]]:
    """Every CONFIRMED step in `bars` (closed bars, oldest → newest), in order of confirmation.

    Honest empty list when ATR is unusable or there are too few bars (Rule 1: no invented structure).
    A step is confirmed at the bar that completes its pause (`confirm_i`); later bars never change it.
    """
    try:
        a = float(atr) if atr is not None else 0.0
    except (TypeError, ValueError):
        a = 0.0
    rows = [_ohlc(b) for b in (bars or []) if b]
    rows = [r for r in rows if None not in r[1:]]
    n = len(rows)
    if a <= 0 or n < m_bars + n_pause:
        return []
    need = k_impulse * a
    steps: List[Dict[str, Any]] = []
    i = 0
    while i + 1 < n:
        found = None
        # the SHORTEST window from i that qualifies as an impulse (1..m_bars bars of travel)
        for j in range(i + 1, min(i + m_bars, n - 1) + 1):
            c0, c1 = rows[i][3], rows[j][3]
            if c1 - c0 >= need:
                found = ("UP", j)
                break
            if c0 - c1 >= need:
                found = ("DOWN", j)
                break
        if found is None:
            i += 1
            continue
        d, j = found
        win = rows[i:j + 1]
        if d == "UP":
            extreme = max(r[1] for r in win)
            impulse = extreme - min(r[2] for r in win)
        else:
            extreme = min(r[2] for r in win)
            impulse = max(r[1] for r in win) - extreme
        if impulse <= 0:
            i += 1
            continue
        # the pause: n_pause bars after j, overlapping, joint range <= r_pause * impulse, closes on the step's side
        p0, p1 = j + 1, j + n_pause
        if p1 >= n:
            break  # not enough closed bars yet — the step is not confirmed (no lookahead)
        pause = rows[p0:p1 + 1]
        ph, pl = max(r[1] for r in pause), min(r[2] for r in pause)
        ok = (ph - pl) <= r_pause * impulse
        if d == "UP":
            ok = ok and all(r[3] >= pl for r in pause) and all(r[3] <= extreme + TICK for r in pause)
            base = pl
        else:
            ok = ok and all(r[3] <= ph for r in pause) and all(r[3] >= extreme - TICK for r in pause)
            base = ph
        if not ok:
            i += 1
            continue
        steps.append({"dir": d, "base": round(base, 2), "extreme": round(extreme, 2),
                      "impulse_pts": round(impulse, 2), "i0": i, "i1": j, "p0": p0, "p1": p1, "confirm_i": p1})
        i = p1 + 1   # the next step can only start after this pause
    return steps


def last_step(bars: Sequence[Dict[str, Any]], atr: Optional[float], direction: Optional[str] = None,
              **kw) -> Optional[Dict[str, Any]]:
    """The most recently CONFIRMED step, optionally only of `direction` ("UP"/"DOWN" or LONG/SHORT)."""
    d = str(direction or "").upper()
    want = {"LONG": "UP", "SHORT": "DOWN"}.get(d, d) or None
    for s in reversed(detect_steps(bars, atr, **kw)):
        if want is None or s["dir"] == want:
            return s
    return None


def step_test(bars: Sequence[Dict[str, Any]], step: Dict[str, Any], tol: float = 2 * TICK) -> Optional[Dict[str, Any]]:
    """The first closed bar AFTER the step's pause that TESTS the base and HOLDS; None while no test has printed.

    UP step: low <= base + tol and close > base → {"held": True}. A close < base − tol before any held test
    → {"held": False, "invalidated": True} (the step failed; the structure no longer holds). Mirror for DOWN.
    """
    if not step:
        return None
    rows = [_ohlc(b) for b in (bars or []) if b]
    base = float(step["base"])
    up = step.get("dir") == "UP"
    for idx in range(int(step["p1"]) + 1, len(rows)):
        o, h, l, c = rows[idx]
        if None in (h, l, c):
            continue
        if up:
            if c < base - tol:
                return {"i": idx, "low": l, "close": c, "held": False, "invalidated": True}
            if l <= base + tol and c > base:
                return {"i": idx, "low": l, "close": c, "held": True}
        else:
            if c > base + tol:
                return {"i": idx, "high": h, "close": c, "held": False, "invalidated": True}
            if h >= base - tol and c < base:
                return {"i": idx, "high": h, "close": c, "held": True}
    return None


def entry_from_step(step: Dict[str, Any], test: Optional[Dict[str, Any]], *, stop_offset_ticks: int = 1,
                    t1_r: float = 1.5) -> Optional[Dict[str, Any]]:
    """The template's trade from a HELD test: entry = the test bar's close, stop beyond the step's BASE
    (the structure that must hold) ∓ offset, T1 = t1_r × risk in the step's direction. None without a held test."""
    if not step or not test or not test.get("held"):
        return None
    up = step.get("dir") == "UP"
    entry = float(test["close"])
    off = max(0, int(stop_offset_ticks)) * TICK
    stop = float(step["base"]) - off if up else float(step["base"]) + off
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    t1 = entry + t1_r * risk if up else entry - t1_r * risk
    return {"direction": "LONG" if up else "SHORT", "entry": round(entry, 2), "stop": round(stop, 2),
            "t1": round(t1, 2), "risk_pts": round(risk, 2), "step": step, "test": test}
