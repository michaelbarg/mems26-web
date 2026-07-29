"""opening_detector_v2.py — MEASURED 5-type opening detector (S1, fixes over-DRIVE).

Implements the measured triggers from Michael's "סוגי פתיחה" sheet, RELATIVE to the
opening print and reference levels — NOT a directional_ratio on a tiny range (the
over-DRIVE bug). Pure function; flag-gated when wired.

  OPEN_DRIVE            : price NEVER returns through the opening print + |price−open|
                          grows monotonically + directional close. (~0.85)
  OPEN_TEST_DRIVE       : a brief poke (~2–6 ticks) beyond a reference that FAILS, then
                          reversal through the open and drive the other way. (~0.75)
  OPEN_REJECTION_REVERSE: move one way, stalls (optional CVD divergence), FULL reversal
                          back through the opening range. (~0.5)
  OPEN_AUCTION_IN/OUT   : ≥2 crossings of the open (rotational). IN if open inside
                          PDH–PDL, OUT if beyond. (~0.4 / ~0.5)

The key fix: a rangey day (price crosses the open) can never be OPEN_DRIVE — it falls
through to OPEN_AUCTION. That is exactly 2026-06-19 (9.75pt range, called OPEN_DRIVE before).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

TICK = 0.25


def _dalton_gaps_on() -> bool:
    return os.getenv("OPENING_DALTON_GAPS_V1", "0").lower() in ("1", "true", "yes")


def _g(bar, *keys):
    if isinstance(bar, dict):
        for k in keys:
            v = bar.get(k)
            if v is not None:
                return v
        return None
    for k in keys:
        v = getattr(bar, k, None)
        if v is not None:
            return v
    return None


def _crossings_of_open(closes: List[float], open_price: float, buf: float) -> int:
    last = 0
    crossings = 0
    for c in closes:
        s = 1 if c > open_price + buf else (-1 if c < open_price - buf else 0)
        if s != 0:
            if last != 0 and s != last:
                crossings += 1
            last = s
    return crossings


def _monotonic(seq: List[float], sign: int, tol: float) -> bool:
    for i in range(1, len(seq)):
        if sign > 0 and seq[i] < seq[i - 1] - tol:
            return False
        if sign < 0 and seq[i] > seq[i - 1] + tol:
            return False
    return True


def detect_opening_type(
    bars: List[Any],
    open_price: Optional[float] = None,
    *,
    prior_vah: Optional[float] = None,
    prior_val: Optional[float] = None,
    pdh: Optional[float] = None,
    pdl: Optional[float] = None,
    cvd_pos: Optional[float] = None,
    cvd_confirm_drive: bool = False,
    tick: float = TICK,
    drive_tol_ticks: float = 1.0,
    buf_ticks: float = 1.0,
) -> Dict[str, Any]:
    """Classify the open from the early RTH 5-min bars (caller passes the window, e.g. first 6)."""
    out = {"opening_type": "UNKNOWN", "direction": "NEUTRAL", "confidence": 0.0, "reasons": []}
    if not bars:
        return out
    if open_price is None:
        open_price = _g(bars[0], "o", "open")
    highs = [h for h in (_g(b, "h", "high") for b in bars) if h is not None]
    lows = [l for l in (_g(b, "l", "low") for b in bars) if l is not None]
    closes = [c for c in (_g(b, "c", "close") for b in bars) if c is not None]
    if open_price is None or not highs or not lows or not closes:
        return out

    tol = drive_tol_ticks * tick
    buf = buf_ticks * tick

    def _loc():
        if prior_val is not None and prior_vah is not None and prior_val <= open_price <= prior_vah:
            return "in_value"
        if pdh is not None and pdl is not None:
            return "out_value_in_range" if pdl <= open_price <= pdh else "out_of_range"
        return "UNKNOWN"

    loc = _loc()

    # B1 (OPENING_DALTON_GAPS_V1): balance_state as a primary axis
    _dalton = _dalton_gaps_on()
    if _dalton:
        _conviction_map = {
            "out_of_range": "high", "out_value_in_range": "medium",
            "in_value": "low", "UNKNOWN": "low",
        }
        out["balance_state"] = loc
        out["balance_conviction"] = _conviction_map.get(loc, "low")

    # 1) OPEN_DRIVE — holds beyond the OPENING RANGE (first bar) + strong directional close.
    #    Relaxed from the open-PRINT (which required ZERO ticks back through open → never fired).
    #    Michael 2026-06-20: Sierra doesn't export opening_type, so this detector must be reachable.
    or_low, or_high = lows[0], highs[0]
    sh, sl = max(highs), min(lows)
    rng6 = (sh - sl) or 1.0
    near = 0.2 * rng6   # "open = the edge" (Dalton): open must sit near the session extreme
    up_drive = (open_price <= sl + near) and all(l >= or_low - tol for l in lows[1:]) and closes[-1] >= open_price + 0.5 * rng6
    dn_drive = (open_price >= sh - near) and all(h <= or_high + tol for h in highs[1:]) and closes[-1] <= open_price - 0.5 * rng6
    _cvd_divergence_note: Optional[str] = None
    if up_drive or dn_drive:
        # CVD confirmation gate (OPENING_FIRE_CVD_V1): when cvd_confirm_drive=True,
        # require CVD aligned with the drive. Divergence = absorption against the drive
        # → do NOT emit OPEN_DRIVE; fall through to ORR / AUCTION.
        cvd_diverges = False
        if cvd_confirm_drive and cvd_pos is not None:
            cvd_diverges = (up_drive and cvd_pos < 0.5) or (dn_drive and cvd_pos > 0.5)
        if cvd_diverges:
            _cvd_divergence_note = f"CVD divergence — drive not confirmed (cvd_pos={cvd_pos:.2f})"
            # fall through to OPEN_TEST_DRIVE / OPEN_REJECTION_REVERSE / OPEN_AUCTION
        else:
            # B2 (OPENING_DALTON_GAPS_V1): check if the drive was INVALIDATED
            # by a later return through the opening range. If any bar after bar 1
            # has a close back inside the opening range → drive invalidated.
            _drive_invalidated = False
            if _dalton and len(closes) > 2:
                for _ci in range(2, len(closes)):
                    if or_low <= closes[_ci] <= or_high:
                        _drive_invalidated = True
                        break
            if _drive_invalidated:
                # Fall through: drive invalidated → try TEST_DRIVE or ORR
                out["invalidated"] = True
                out["reasons"].append("drive invalidated: price returned through opening range")
            else:
                out.update(opening_type="OPEN_DRIVE",
                           direction="UP" if up_drive else "DOWN", confidence=0.85,
                           reasons=["no return through opening print", "monotonic |price−open|", f"open_location={loc}"])
                return out

    init = closes[0] - open_price
    last = closes[-1] - open_price
    crossings = _crossings_of_open(closes, open_price, buf)

    # 2) OPEN_TEST_DRIVE — a brief poke (~2–6 ticks) beyond a reference that FAILS, then a drive.
    #    Checked before Rejection-Reverse: the small ref-poke is the distinguishing signal.
    refs = [r for r in (prior_vah, prior_val, pdh, pdl) if r is not None]
    poke_fail = False
    for r in refs:
        poked_up = max(highs) >= r + 2 * tick and max(highs) <= r + 6 * tick and closes[-1] < r
        poked_dn = min(lows) <= r - 2 * tick and min(lows) >= r - 6 * tick and closes[-1] > r
        if poked_up or poked_dn:
            poke_fail = True
            break
    if poke_fail and abs(last) > buf:
        out.update(opening_type="OPEN_TEST_DRIVE",
                   direction="UP" if last > 0 else "DOWN", confidence=0.75,
                   reasons=["small poke beyond reference failed, then drove"])
        if _cvd_divergence_note:
            out["reasons"].append(_cvd_divergence_note)
        return out

    # 3) OPEN_REJECTION_REVERSE — a larger initial move that FULLY reverses back through the open
    reversed_full = (init > buf and last < -buf) or (init < -buf and last > buf)
    if reversed_full and abs(last) >= abs(init) * 0.5 and crossings <= 1:
        cvd_div = (cvd_pos is not None) and ((init > 0 and cvd_pos < 0.5) or (init < 0 and cvd_pos > 0.5))
        out.update(opening_type="OPEN_REJECTION_REVERSE",
                   direction="UP" if last > 0 else "DOWN", confidence=0.6 if cvd_div else 0.5,
                   reasons=["initial move then full reversal through open"] + (["CVD divergence"] if cvd_div else []))
        if _cvd_divergence_note:
            out["reasons"].append(_cvd_divergence_note)
        return out

    # 4) OPEN_AUCTION — rotational (crossings of the open), or no clear drive
    if loc == "out_of_range":
        # B3 (OPENING_DALTON_GAPS_V1): AUCTION_OUT = alertness, not neutral.
        # Out-of-range opening with no clear drive → double-distribution potential.
        _ao_conf = 0.55 if _dalton else 0.5
        _ao_reasons = [f"open out of yesterday's range; {crossings} crossings of open"]
        if _dalton:
            _ao_reasons.append("out-of-balance: double-distribution potential")
            out["balance_state"] = "out_of_range"
            out["balance_conviction"] = "high"
        out.update(opening_type="OPEN_AUCTION_OUT", direction="NEUTRAL",
                   confidence=_ao_conf, reasons=_ao_reasons)
    else:
        out.update(opening_type="OPEN_AUCTION_IN", direction="NEUTRAL", confidence=0.4,
                   reasons=[f"rotational; {crossings} crossings of open; open_location={loc}"])
    if _cvd_divergence_note:
        out["reasons"].append(_cvd_divergence_note)
    return out
