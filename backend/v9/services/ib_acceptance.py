"""IB_ACCEPTANCE (T-621, Michael 21.10 — the 20.10 root fixes 1 and 2): an IB range extension counts only when ACCEPTED.

20.10: IB 7710.25–7786.00 (75.75 pt). The 17:30 bar's wick reached 7791.50 (+5.5) and closed back inside at 7779.25;
no 5-min bar CLOSED above 7786 all day (17:50 closed 7786.00 — on the edge, not beyond). Yet
  · the gateway's Layer 2 (5b) direction hint read ANY extension > 0 ⇒ LONG from 17:35 to the close: every short of
    the afternoon (18:10 REACTIVE_SHORT 7777.75, the ZLR/GB100/INITIATIVE shorts 18:25–20:15) died on tree:bias,
    while ib_return (need = max(2, 0.10 × IB) = 7.6 pt) saw no extension and so could never release it;
  · the day-type side count (DAYTYPE_SIDES_MECHANICAL_V1 + IB_BREAK_ANY_EXPANSION_V1: two bars whose HIGH reaches
    0.5 pt beyond the IB) counted the wick bars as a side ⇒ "Variation" from 17:45, so the Normal-day location rule
    (LONG near/below VAL · SHORT near/above VAH) never applied to the mid-value TOUCH2 / REACTIVE longs that lost.
Dalton (Mind Over Markets): range extension is other-timeframe participation when the market ACCEPTS the new prices —
it spends time there; a probe that is rejected at once is a failed extension, not a side and not a direction.

One definition, used by both fixes:
  accepted — at least N CONSECUTIVE closed 5-min bars after the IB CLOSED beyond the IB edge by ≥ noise
             (N = IB_EXT_ACCEPT_CLOSES, default 2 · noise = IB_EXT_ACCEPT_NOISE_PTS, default 0.5 — the
             IB_BREAK_ANY_EXPANSION noise floor)
  released — after an acceptance, N consecutive closed bars closed back INSIDE the IB (strictly inside the edge):
             the extension failed. The same N, the same edge. A later acceptance makes the side live again.
Fix 1 (IB_EXT_ACCEPTED_HINT_V1) takes the gateway's direction hint from the LIVE accepted side; fix 2
(DAYTYPE_SIDES_ACCEPTED_V1) counts a day-type side when it was EVER accepted that session.

Pure functions over bars the caller already cut AS-OF (closed bars only — T-498). No I/O; the env helpers below are
the only env reads and the callers decide whether to use them.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence

_ALIAS = {"h": "high", "l": "low", "c": "close"}


def _f(b: Any, k: str) -> Optional[float]:
    """A bar's h/l/c from a dict ({h,l,c} or {high,low,close}) or an object with those attributes (the day-type
    machine passes Bar objects to relative_features)."""
    if isinstance(b, dict):
        v = b.get(k)
        if v is None:
            v = b.get(_ALIAS[k])
    else:
        v = getattr(b, k, None)
        if v is None:
            v = getattr(b, _ALIAS[k], None)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def accept_closes() -> int:
    """IB_EXT_ACCEPT_CLOSES as an int ≥ 1 (unset / bad / < 1 ⇒ 2)."""
    try:
        n = int(float(os.getenv("IB_EXT_ACCEPT_CLOSES", "2") or 2))
    except ValueError:
        return 2
    return n if n >= 1 else 2


def accept_noise() -> float:
    """IB_EXT_ACCEPT_NOISE_PTS as a float ≥ 0 (unset / bad / < 0 ⇒ 0.5)."""
    try:
        x = float(os.getenv("IB_EXT_ACCEPT_NOISE_PTS", "0.5") or 0.5)
    except ValueError:
        return 0.5
    return x if x >= 0 else 0.5


def _side_walk(closes: Sequence[float], beyond, inside, n: int) -> Dict[str, Any]:
    """Walk the post-IB closes for ONE side: ever accepted, live at the last close, the longest beyond-run."""
    ever = live = False
    run_b = run_i = best = 0
    first_idx = None
    for i, c in enumerate(closes):
        if beyond(c):
            run_b += 1; run_i = 0
            best = max(best, run_b)
            if run_b >= n:
                if not ever:
                    first_idx = i
                ever = live = True
        elif inside(c):
            run_i += 1; run_b = 0
            if live and run_i >= n:
                live = False
        else:          # between the edge and edge ± noise: neither beyond nor back inside
            run_b = 0; run_i = 0
    return {"ever": ever, "live": live, "best_run": best, "first_idx": first_idx}


def acceptance(bars: Sequence[Dict[str, Any]], ib_hi: Optional[float] = None, ib_lo: Optional[float] = None,
               ib_bars: int = 12, n: Optional[int] = None, noise: Optional[float] = None) -> Dict[str, Any]:
    """bars: today's CLOSED RTH 5-min bars, oldest → newest ({h,l,c} or {high,low,close}).

    The IB is (ib_hi, ib_lo) when both are given and ib_hi > ib_lo (the TPO / Sierra first hour), else the first
    `ib_bars` bars. Only the bars AFTER the first `ib_bars` can extend it. state: forming (IB not complete) · inside ·
    up · down · two_sided (the LIVE sides) · released_up / released_down (accepted earlier, failed back inside)."""
    n = accept_closes() if n is None else max(1, int(n))
    noise = accept_noise() if noise is None else max(0.0, float(noise))
    bars = [b for b in (bars or []) if b]
    if len(bars) <= ib_bars:
        return {"state": "forming", "n": n, "noise": noise}
    try:
        hi = float(ib_hi) if ib_hi is not None else None
        lo = float(ib_lo) if ib_lo is not None else None
    except (TypeError, ValueError):
        hi = lo = None
    if not (hi is not None and lo is not None and hi > lo > 0):
        ib = bars[:ib_bars]
        hs = [x for x in (_f(b, "h") for b in ib) if x is not None]
        ls = [x for x in (_f(b, "l") for b in ib) if x is not None]
        if not hs or not ls:
            return {"state": "forming", "n": n, "noise": noise}
        hi, lo = max(hs), min(ls)
    closes: List[float] = [c for c in (_f(b, "c") for b in bars[ib_bars:]) if c is not None]
    up = _side_walk(closes, lambda c: c >= hi + noise, lambda c: c < hi, n)
    dn = _side_walk(closes, lambda c: c <= lo - noise, lambda c: c > lo, n)
    if up["live"] and dn["live"]:
        state = "two_sided"
    elif up["live"]:
        state = "up"
    elif dn["live"]:
        state = "down"
    elif up["ever"] and not dn["ever"]:
        state = "released_up"
    elif dn["ever"] and not up["ever"]:
        state = "released_down"
    elif up["ever"] and dn["ever"]:
        state = "released_both"
    else:
        state = "inside"
    post_hs = [x for x in (_f(b, "h") for b in bars[ib_bars:]) if x is not None]
    post_ls = [x for x in (_f(b, "l") for b in bars[ib_bars:]) if x is not None]
    return {"state": state, "n": n, "noise": noise, "ib_hi": hi, "ib_lo": lo,
            "ext_up": round(max(0.0, max(post_hs) - hi), 2) if post_hs else 0.0,
            "ext_dn": round(max(0.0, lo - min(post_ls)), 2) if post_ls else 0.0,
            "up_accepted": up["ever"], "dn_accepted": dn["ever"], "up_live": up["live"], "dn_live": dn["live"],
            "up_run": up["best_run"], "dn_run": dn["best_run"], "last": closes[-1] if closes else None}


def hint(acc: Optional[Dict[str, Any]]) -> Optional[str]:
    """Fix 1: the session direction from the LIVE accepted extension — LONG / SHORT, None when no side is live. Both
    sides live (a Neutral day): the larger extension, as the Layer 2 tie-break always was; equal ⇒ None."""
    a = acc or {}
    up, dn = bool(a.get("up_live")), bool(a.get("dn_live"))
    if up and not dn:
        return "LONG"
    if dn and not up:
        return "SHORT"
    if up and dn:
        eu, ed = float(a.get("ext_up") or 0), float(a.get("ext_dn") or 0)
        return "LONG" if eu > ed else ("SHORT" if ed > eu else None)
    return None


def layer2_hint(mode: Optional[str], layer1: Optional[str], acc: Optional[Dict[str, Any]]) -> Optional[str]:
    """Fix 1 — the gateway's Layer 2 (5b) hint after the IB: the live accepted side when there is one; otherwise
    mode "1" keeps Layer 1 (the opening direction — exactly the old no-extension path) and mode "none" gives no
    direction once the IB is complete (state ≠ forming)."""
    h = hint(acc)
    if h:
        return h
    if str(mode or "").strip().lower() == "none" and (acc or {}).get("state") not in (None, "forming"):
        return None
    return layer1


def sides(acc: Optional[Dict[str, Any]]) -> int:
    """Fix 2: the day-type side count — a side counts once it was accepted this session (a later return does not
    un-extend the day; it only ends the direction, fix 1)."""
    a = acc or {}
    return int(bool(a.get("up_accepted"))) + int(bool(a.get("dn_accepted")))
