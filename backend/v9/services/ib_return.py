"""IB_RETURN (T-517, Michael 29.09 "כן"): has the IB extension failed — right now, from the closed bars of the session?

28.09: the IB (first RTH hour, 7758.75-7775.25) broke down at 17:35 and extended to 7726.0; from 19:00 the price came back
(19:20 closed 7768.25, back inside the IB) and ran to 7786 — +43 pts from the 19:10 low — while every long 18:10-19:35
died on `tree:bias`: the session hint stayed SHORT. A structural fact, not a score:

  extended_down  — after the IB (the first 12 closed RTH bars) the low went ≥ `need` below IB low (need = max(2, 0.10 ×
                   IB range), the same threshold as decision_tree.structure_of) and the upside did not
  returning_down — extended_down, and the last closed bar has taken back ≥ half of that extension (not yet inside)
  failed_down    — extended_down, and the last closed bar closed back above IB low (inside the IB again)
  *_up           — the mirror;  two_sided — both sides extended;  inside — neither;  forming — the IB is not complete

ib_return_rel places a candidate in that state: with_returning / with_failed (the candidate goes WITH the return, i.e.
against the extension) · against_return · none.

Pure functions over bars the caller already cut AS-OF (closed bars only — T-498). No I/O. Imported only by the gateway
block that is inert unless IB_RETURN_HINT_RELEASE_V1 is set (harness measurement, default OFF).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

_ALIAS = {"h": "high", "l": "low", "c": "close"}


def _f(b: Dict[str, Any], k: str) -> float:
    v = b.get(k)
    if v is None:
        v = b.get(_ALIAS[k])
    return float(v)


def ib_return_state(bars: Sequence[Dict[str, Any]], ib_bars: int = 12) -> Dict[str, Any]:
    """bars: today's CLOSED RTH 5-min bars, oldest → newest ({h,l,c} or {high,low,close})."""
    bars = [b for b in (bars or []) if b]
    if len(bars) <= ib_bars:
        return {"state": "forming"}
    ib = bars[:ib_bars]; post = bars[ib_bars:]
    hi = max(_f(b, "h") for b in ib); lo = min(_f(b, "l") for b in ib)
    need = max(2.0, 0.10 * (hi - lo))
    ext_dn = lo - min(_f(b, "l") for b in post)
    ext_up = max(_f(b, "h") for b in post) - hi
    last = _f(bars[-1], "c")
    out: Dict[str, Any] = {"ib_hi": hi, "ib_lo": lo, "need": round(need, 2), "ext_dn": round(ext_dn, 2),
                           "ext_up": round(ext_up, 2), "last": last}
    if ext_dn >= need and ext_up >= need:
        return dict(out, state="two_sided")
    if ext_dn >= need:
        if last > lo:
            return dict(out, state="failed_down")
        if last >= lo - ext_dn / 2.0:
            return dict(out, state="returning_down")
        return dict(out, state="extended_down")
    if ext_up >= need:
        if last < hi:
            return dict(out, state="failed_up")
        if last <= hi + ext_up / 2.0:
            return dict(out, state="returning_up")
        return dict(out, state="extended_up")
    return dict(out, state="inside")


def ib_return_rel(state: Optional[Dict[str, Any]], direction: Optional[str]) -> str:
    """The candidate in that state: with_returning · with_failed · against_return · none."""
    s = (state or {}).get("state", "none"); d = (direction or "").upper()
    if s in ("returning_down", "failed_down"):
        if d == "LONG":
            return "with_returning" if s == "returning_down" else "with_failed"
        return "against_return" if d == "SHORT" else "none"
    if s in ("returning_up", "failed_up"):
        if d == "SHORT":
            return "with_returning" if s == "returning_up" else "with_failed"
        return "against_return" if d == "LONG" else "none"
    return "none"


def extension_extreme_epoch(bars_e: Sequence[Dict[str, Any]], state: Optional[Dict[str, Any]],
                            ib_bars: int = 12) -> Optional[float]:
    """bars_e: the same closed RTH bars with 'e' (bar-start epoch) — the epoch of the bar that made the extension
    extreme (lowest low after the IB for *_down, highest high for *_up); None when there is no one-sided extension."""
    s = (state or {}).get("state", "")
    post = [b for b in list(bars_e or [])[ib_bars:] if b]
    if not post or not (s.endswith("_down") or s.endswith("_up")):
        return None
    pick = min(post, key=lambda b: _f(b, "l")) if s.endswith("_down") else max(post, key=lambda b: _f(b, "h"))
    return float(pick["e"])


def bucket_start(ext_e: float, rth_open_e: float, width_s: int = 900) -> float:
    """Start of the 15-min order-flow bucket (aligned to the RTH open) that holds the extension extreme."""
    return ext_e - ((ext_e - rth_open_e) % width_s)


def flow_ok(state: Optional[Dict[str, Any]], dsum: Optional[float]) -> bool:
    """Michael 29.09 16:25 ("עומק הרוכשים והמוכרים"): the order flow since the extension extreme did not fight the
    return — Σ delta ≥ 0 when a DOWN extension is being taken back (buyers), ≤ 0 for an UP one (sellers)."""
    s = (state or {}).get("state", "")
    sign = 1.0 if s.endswith("_down") else (-1.0 if s.endswith("_up") else 0.0)
    try:
        return sign != 0.0 and sign * float(dsum or 0.0) >= 0.0
    except (TypeError, ValueError):
        return False


def release_modes(mode: Optional[str]) -> tuple:
    """IB_RETURN_HINT_RELEASE_V1 → the ibr_rel values whose rel_bias=against is released to none (empty = off)."""
    m = (mode or "0").strip().lower()
    return {"returning": ("with_returning",), "failed": ("with_failed",),
            "both": ("with_returning", "with_failed")}.get(m, ())
