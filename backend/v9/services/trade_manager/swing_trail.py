"""swing_trail — F5 structural swing trail for the runner leg (RUNNER_TRAIL_V2).

WHY THIS EXISTS (ORACLE_STUDY_2026-08-20, Michael ruling 2026-08-20)
-------------------------------------------------------------------
Over 32 live sessions the system booked +$320 on 85 trades. The SAME entries with
the same stops, exited on a structural trail instead of the fixed ladder, book
**+$2,635** — a +$2,315 gap that is 100% exit-management (trades 3+ per day
contributed +$32.50, i.e. firing count is NOT the problem). 2026-08-03 is the
shape of it: one 95.75pt LONG swing, 9 live trades all in the right direction,
+$183.75 booked — the first one exited at a fixed T2 nine points above entry,
ten minutes after entry, while the day ran seventy-five more points.

WHAT THIS MODULE IS
-------------------
The *definition* of "the last confirmed swing" — nothing else. It is a pure
function over closed 5-min bars: no DB, no I/O, no clock, no flags. The manager
owns the policy (never-widen, BE+1T floor, runner-only); this owns the geometry,
so live code and `scripts/replay_f5_runner_trail.py` measure the same thing.

CONSTRUCTION (identical to scripts/oracle_study.py::zigzag — the engine that
measured the $2,315, kept byte-compatible on purpose)
-------------------------------------------------------------------------------
* Pivots are found on 5-min **CLOSES**, not on highs/lows. This is not a
  preference — it is a measured failure: an MES 5-min bar is ~1x ATR wide, so a
  high/low ZigZag with a ~1x ATR threshold flips inside single bars and shreds a
  session into dozens of fake swings (49 legs / 520pt on 2026-07-07 vs 13 legs /
  218pt on closes).
* A pivot is **CONFIRMED** only at the first bar whose close retraced `rev` from
  the running extreme (`confirm_i`). Everything this module returns is therefore
  lookahead-free: the caller may act on bar `confirm_i` and no earlier.
  The running (unconfirmed) extreme is deliberately NOT returned — trailing
  behind an unconfirmed extreme is just a tighter chandelier, which is the very
  behaviour that produced +$320.
* The pivot PRICE is the bar's actual high/low — the best price that traded
  there — because that is where structure actually sits for a stop.

Rule 1 (honest failure): every "cannot tell" path returns None. Never a
synthesised level.
"""
from __future__ import annotations

import statistics
from typing import Dict, List, Optional, Sequence

# MES tick. Kept local so this module imports nothing from the trading stack
# (it is exercised by the replay script outside the app process).
TICK = 0.25

# Swing threshold = clamp(ATR_MULT x ATR(prev session), REV_MIN, REV_MAX).
# Values are the ORACLE study's, which is where the +$2,315 was measured.
REV_ATR_MULT = 1.0
REV_MIN_PTS = 4.0
REV_MAX_PTS = 12.0


def _hl(b: Dict) -> tuple:
    """(high, low, close) from either the woodies row shape or the {h,l,c} shape."""
    h = b.get("h", b.get("high"))
    l = b.get("l", b.get("low"))
    c = b.get("c", b.get("close"))
    return (float(h), float(l), float(c))


def swing_rev_threshold(prev_session_bars: Optional[Sequence[Dict]]) -> Optional[float]:
    """`rev` for the zigzag = clamp(1.0 x ATR(previous RTH session), 4.0, 12.0) pt.

    The PREVIOUS session is used on purpose: it is fully known at 09:30, so the
    threshold is causal for every bar of today (ORACLE §1). Mean true range over
    the whole prior RTH — not the last 14 bars, which are the quietest of the day
    and produced a systematically too-small threshold in the first version.

    Honest None when there is no usable prior session (caller must NOT invent one).
    """
    if not prev_session_bars or len(prev_session_bars) < 20:
        return None
    trs: List[float] = []
    for i in range(1, len(prev_session_bars)):
        h, l, _ = _hl(prev_session_bars[i])
        _, _, pc = _hl(prev_session_bars[i - 1])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs:
        return None
    atr = statistics.fmean(trs)
    raw = max(REV_ATR_MULT * atr, REV_MIN_PTS)
    return round(min(raw, REV_MAX_PTS) * 4) / 4.0  # snap to tick


def confirmed_pivots(bars: Sequence[Dict], rev: float) -> List[Dict]:
    """Confirmed alternating H/L pivots on 5-min closes.

    Returns [{i, kind: 'H'|'L', price, confirm_i}, ...] — every entry is already
    confirmed (a close retraced `rev` from the extreme at bar `confirm_i`). The
    provisional terminal pivot of the ORACLE version is intentionally omitted:
    a trail may only act on confirmed structure.
    """
    n = len(bars)
    if n < 3 or rev is None or rev <= 0:
        return []
    C = [_hl(b)[2] for b in bars]
    piv: List[Dict] = []
    hi = lo = C[0]
    hi_i = lo_i = 0
    dirn = 0
    for i in range(1, n):
        c = C[i]
        if dirn >= 0 and c > hi:
            hi, hi_i = c, i
        if dirn <= 0 and c < lo:
            lo, lo_i = c, i
        flip = None
        if dirn == 0:
            if hi - c >= rev and hi_i < i:
                flip = "H"
            elif c - lo >= rev and lo_i < i:
                flip = "L"
        elif dirn > 0 and hi - c >= rev:
            flip = "H"
        elif dirn < 0 and c - lo >= rev:
            flip = "L"
        if flip == "H":
            piv.append(dict(i=hi_i, kind="H", price=_hl(bars[hi_i])[0], confirm_i=i))
            dirn = -1
            seg = C[hi_i:i + 1]
            lo = min(seg)
            lo_i = hi_i + seg.index(lo)
        elif flip == "L":
            piv.append(dict(i=lo_i, kind="L", price=_hl(bars[lo_i])[1], confirm_i=i))
            dirn = 1
            seg = C[lo_i:i + 1]
            hi = max(seg)
            hi_i = lo_i + seg.index(hi)
    return piv


def last_confirmed_swing(bars: Sequence[Dict], direction: str,
                         rev: float) -> Optional[Dict]:
    """The last CONFIRMED swing low (LONG) / swing high (SHORT).

    LONG trails behind the low the current up-leg started from; SHORT behind the
    high. Honest None when the session has not yet printed one — the caller then
    holds its existing stop rather than inventing a level (Rule 1).
    """
    d = (direction or "").upper()
    if d not in ("LONG", "SHORT"):
        return None
    want = "L" if d == "LONG" else "H"
    piv = confirmed_pivots(bars, rev)
    for p in reversed(piv):
        if p["kind"] == want:
            return p
    return None


def swing_trail_stop(bars: Sequence[Dict], direction: str, *,
                     rev: float, offset_ticks: int = 1) -> Optional[float]:
    """Structural trail level = last confirmed swing extreme -/+ `offset_ticks`.

    LONG  -> swing_low  - offset (stop sits UNDER the structure that must hold)
    SHORT -> swing_high + offset

    Pure geometry. The never-widen rule and the BE+1T floor are policy and live
    in the manager — deliberately not here, so this stays testable on bars alone.
    """
    sw = last_confirmed_swing(bars, direction, rev)
    if sw is None:
        return None
    off = max(0, int(offset_ticks)) * TICK
    d = (direction or "").upper()
    price = float(sw["price"])
    return round(price - off, 2) if d == "LONG" else round(price + off, 2)
