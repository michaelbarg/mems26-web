# -*- coding: utf-8 -*-
"""WAIT_FOR_TEST_V1 (T-635 D3-gate, 22.10.2026) — PURE: no I/O, no env, no clock.

Michael 21.10 21:1x: "המערכת צריכה לזהות מדרגה … ולחכות לבדיקה". 22.10 per trade: every demo entry that
fired 0–1 bars after an impulse — chasing it (#3540 sold the low of the drive bar, −225) or fading
into it (#3660 +12.5 in 3 bars, −118.75 · #3670 +11 in 6 bars, −75 · #3696 right after the 19:35
spike, −160) or on the climax bar itself (#3558 −31.5 pt / 57k, −215) — lost, MFE ≤ 3.5 pt, out in
2–24 min. The three winners (#3544 #3687 #3702) all entered after a PAUSE (6 flat bars / a slow grind /
the reversal bar that was itself the test).

The gate (the step detector's vocabulary, backend/v9/systems/steps.py): an IMPULSE is a close-to-close
move of >= k_impulse x ATR within <= m_bars closed bars, or a single closed bar whose range is >= k_bar x
ATR. If an impulse ENDED within the last `recent` closed bars there has been no pause yet — the template
(impulse -> pause -> test) says wait. Direction-agnostic on purpose: after a push the first entry is the
test, whichever way it goes. The full template (entry at the test close, stop beyond the base — T-629
entry_from_step) is the producers' job; this gate only refuses the entries the template would never take.
Fail-open without bars/ATR (never blocks blind).
"""
from typing import Any, Dict, List, Optional, Sequence


def _f(b, *keys) -> Optional[float]:
    for k in keys:
        v = b.get(k) if isinstance(b, dict) else None
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def push_without_pause(bars: Sequence[Dict[str, Any]], atr: Optional[float], *, k_impulse: float = 1.5,
                       k_bar: float = 1.5, m_bars: int = 3, recent: int = 2) -> Dict[str, Any]:
    """Did an impulse end within the last `recent` closed bars (no pause printed yet)?

    Returns {"blocked": bool, "why": str, "impulse_pts": float|None, "end_i": int|None, "kind": str|None}.
    bars = today's closed bars oldest -> newest (dicts with h/l/c or high/low/close).
    """
    rows = []
    for b in (bars or []):
        h, l, c = _f(b, "h", "high"), _f(b, "l", "low"), _f(b, "c", "close")
        if None not in (h, l, c):
            rows.append((h, l, c))
    try:
        a = float(atr) if atr is not None else 0.0
    except (TypeError, ValueError):
        a = 0.0
    n = len(rows)
    if a <= 0 or n < 2:
        return {"blocked": False, "why": "fail-open: no atr/bars", "impulse_pts": None, "end_i": None, "kind": None}
    need = k_impulse * a
    first_recent = max(0, n - int(recent))
    best = None
    for j in range(first_recent, n):            # candidate impulse END bars (the last `recent` closed bars)
        h, l, c = rows[j]
        if (h - l) >= k_bar * a:
            cand = ("bar", round(h - l, 2), j, "bar %d ranged %.2f pt = %.2f ATR" % (j, h - l, (h - l) / a))
            if best is None or cand[1] > best[1]:
                best = cand
        for i in range(max(0, j - int(m_bars)), j):
            mv = rows[j][2] - rows[i][2]
            if abs(mv) >= need:
                cand = ("close", round(abs(mv), 2), j,
                        "closes %d->%d moved %+.2f pt = %.2f ATR" % (i, j, mv, abs(mv) / a))
                if best is None or cand[1] > best[1]:
                    best = cand
    if best is None:
        return {"blocked": False, "why": "no impulse ended in the last %d closed bars" % recent,
                "impulse_pts": None, "end_i": None, "kind": None}
    kind, pts, j, why = best
    return {"blocked": True, "why": "impulse ended %d bar(s) ago without a pause (%s; ATR %.2f) — wait for the test"
            % (n - 1 - j, why, a), "impulse_pts": pts, "end_i": j, "kind": kind}
