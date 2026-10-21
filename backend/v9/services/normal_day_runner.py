"""NORMAL_DAY_RUNNER (T-622, Michael 21.10: "אם מדובר ביום נורמלי וזאת הסיבה להפסדים צריך לבצע תיקונים שיהיו בהתאם
ליום נורמלי") — on a Normal day the runner ends at the OTHER SIDE.

Michael's Normal-day doctrine (11.09 ~09:50): "ביום נורמלי אנחנו צריכים לסחור את ההיפוך ב-VAH ו-VAL עד ל-POC, או כל
עוד הוא ממשיך לצד השני — עד הצד השני; לא נכון להיכנס באזור ה-POC". The T-319 plan wrote it as T1 = POC · T2 = the
opposite VA edge · T3 = the opposite IB edge, no open runner — EDGE_FADE_TARGETS_V1 (T-354) applies that ladder to
the entries the tree approves at the edge. A trade opened BEFORE the day was identified keeps the open runner of its
own producer: 20.10's 16:50 OPENING_ORR LONG 7729.00 (phase B, the day still FORMING) banked T1 17:00 and T2 17:15 and
its last contract — RUNNER_TRAIL_V2, no target order — held the ONE slot until 18:10 (trailed out at 7776), while the
Normal-day trade at the other side (17:35 DALTON_EDGE_SHORT 7779.25 above VAH, 17:50 CEILING_FLIP_TOUCH2 SHORT 7781.00 —
both tree TAKE) was refused live_slot_occupied. The runner had reached the other side — the IB high 7786.00 — at 17:25.

The rule (pure): once the IB is complete (12 closed RTH bars) and the live day-type label is Normal, a runner (T1
filled) whose last CLOSED bar reached the other side of the IB (LONG: high ≥ IB high · SHORT: low ≤ IB low) has its
stop tightened to one tick inside min(close, IB high) (LONG; mirror for SHORT):
  · the bar closed back inside the IB ⇒ one tick under that close — the probe failed, out on the next tick down;
  · the bar closed beyond ⇒ one tick inside the IB edge — out if price comes back in; an ACCEPTED breakout makes the
    day not-Normal (DAYTYPE_SIDES_ACCEPTED_V1) and the runner keeps its trail.
Tighten only. The live lever is MODIFY_STOP — with the attached OCO targets the only working exit (op=EXIT is broken,
CLAUDE.md §op=EXIT). Flag NORMAL_DAY_RUNNER_OTHER_SIDE_V1, default OFF ⇒ never called.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Sequence, Tuple

TICK = 0.25
_ALIAS = {"h": "high", "l": "low", "c": "close"}


def enabled() -> bool:
    return os.getenv("NORMAL_DAY_RUNNER_OTHER_SIDE_V1", "0").strip().lower() in ("1", "true", "yes")


def _f(b: Any, k: str) -> Optional[float]:
    v = b.get(k) if isinstance(b, dict) else getattr(b, k, None)
    if v is None:
        v = b.get(_ALIAS[k]) if isinstance(b, dict) else getattr(b, _ALIAS[k], None)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def ib_of(closed_rth_bars: Sequence[Any], ib_bars: int = 12) -> Optional[Tuple[float, float]]:
    """(IB high, IB low) from the first `ib_bars` closed RTH bars; None while the IB is not complete."""
    bars = [b for b in (closed_rth_bars or []) if b is not None]
    if len(bars) < ib_bars:
        return None
    hs = [x for x in (_f(b, "h") for b in bars[:ib_bars]) if x is not None]
    ls = [x for x in (_f(b, "l") for b in bars[:ib_bars]) if x is not None]
    if len(hs) < ib_bars or len(ls) < ib_bars:
        return None
    return max(hs), min(ls)


def runner_stop(direction: Optional[str], day_type: Optional[str], ib_hi: Optional[float], ib_lo: Optional[float],
                bar_high: Optional[float], bar_low: Optional[float], bar_close: Optional[float],
                cur_stop: Optional[float], tick: float = TICK) -> Optional[float]:
    """The tightened runner stop, or None (not a Normal day / the other side not reached / it would not tighten)."""
    if str(day_type or "").strip() != "Normal":
        return None
    try:
        hi, lo, bh, bl, bc = float(ib_hi), float(ib_lo), float(bar_high), float(bar_low), float(bar_close)
    except (TypeError, ValueError):
        return None
    if not hi > lo > 0:
        return None
    d = str(direction or "").upper()
    if d == "LONG":
        if bh < hi:
            return None
        new = round(min(bc, hi) - tick, 2)
        return new if (cur_stop is None or new > float(cur_stop)) else None
    if d == "SHORT":
        if bl > lo:
            return None
        new = round(max(bc, lo) + tick, 2)
        return new if (cur_stop is None or new < float(cur_stop)) else None
    return None
