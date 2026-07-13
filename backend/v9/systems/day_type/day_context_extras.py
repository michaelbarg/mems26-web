"""day_context_extras — P2-9/10/11/12: the four Dalton context reads (Michael 07-13).

Pure functions, bar-based, no I/O. Consumed by the morning briefing, the replay
surface, and (P2-9 only, flag-gated) the confidence score.

P2-9  profile_imbalance — volume above vs below the developing POC ∈ [-1,1].
      HONEST NAMING: this is a volume-at-price proxy for Dalton's TPO-count
      (true TPO letters are not exported); sign = OTF body pressure.
P2-10 range_estimate — once one session extreme HELD through >=2 30-min periods,
      the expected day range projects from it: held_extreme ± median daily
      range (±10% band) (Dalton pp.107-110 day-range estimates).
P2-11 va_rule_read — open OUTSIDE prior VA that gets ACCEPTED back INSIDE
      (2 consecutive closes) → odds favor full traverse to the FAR VA extreme
      (Dalton's 80% rule read); blocks counter-fading the rotation.
P2-12 eod_continuation_tag — terminal day-type + close location → a named
      statistical morning bias for tomorrow (pp.239-247 EOD carry).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.v9.systems.day_type.value_migration import developing_value, _g


# ── P2-9 · volume-profile imbalance (TPO-count proxy) ──────────────────────

def profile_imbalance(bars: List[Any], bucket: float = 1.0) -> Optional[float]:
    """(volume above POC − volume below) / total ∈ [-1, 1]; None when no data."""
    if not bars:
        return None
    dv = developing_value(bars, bucket)
    poc = dv.get("poc")
    if poc is None:
        return None
    above = below = 0.0
    for b in bars:
        h, l, c = _g(b, "h", "high"), _g(b, "l", "low"), _g(b, "c", "close")
        if None in (h, l, c):
            continue
        tp = (h + l + c) / 3.0
        v = _g(b, "v", "volume") or 1.0
        if tp > poc:
            above += v
        elif tp < poc:
            below += v
    tot = above + below
    return round((above - below) / tot, 3) if tot > 0 else None


# ── P2-10 · day-range estimate from the held extreme ───────────────────────

def range_estimate(bars: List[Any], med_daily_range: Optional[float],
                   bars_per_30min: int = 6, tick: float = 0.25) -> Dict[str, Any]:
    """Project the expected day range from the HELD extreme.

    held = the session low (resp. high) that no 30-min period has violated for
    >=2 completed periods. Estimate: held_low + med_range (UP projection) or
    held_high − med_range, with a ±10% band. Honest None when no extreme held
    yet or no median range supplied.
    """
    out = {"held_side": None, "est_target": None, "est_lo": None, "est_hi": None}
    if not bars or not med_daily_range or med_daily_range <= 0:
        return out
    lows, highs = [], []
    for i in range(0, len(bars), bars_per_30min):
        ch = bars[i:i + bars_per_30min]
        ls = [x for x in (_g(b, "l", "low") for b in ch) if x is not None]
        hs = [x for x in (_g(b, "h", "high") for b in ch) if x is not None]
        if ls and hs:
            lows.append(min(ls))
            highs.append(max(hs))
    if len(lows) < 3:            # need >=2 completed periods AFTER the extreme
        return out
    sess_lo, sess_hi = min(lows), max(highs)
    lo_per, hi_per = lows.index(sess_lo), highs.index(sess_hi)
    lo_held = (len(lows) - 1 - lo_per) >= 2 and all(l >= sess_lo - tick for l in lows[lo_per + 1:])
    hi_held = (len(highs) - 1 - hi_per) >= 2 and all(h <= sess_hi + tick for h in highs[hi_per + 1:])
    if lo_held and not hi_held:
        t = sess_lo + med_daily_range
        out.update(held_side="LOW", est_target=round(t, 2),
                   est_lo=round(sess_lo + 0.9 * med_daily_range, 2),
                   est_hi=round(sess_lo + 1.1 * med_daily_range, 2))
    elif hi_held and not lo_held:
        t = sess_hi - med_daily_range
        out.update(held_side="HIGH", est_target=round(t, 2),
                   est_lo=round(sess_hi - 1.1 * med_daily_range, 2),
                   est_hi=round(sess_hi - 0.9 * med_daily_range, 2))
    return out


# ── P2-11 · Value-Area rule read ────────────────────────────────────────────

def va_rule_read(bars: List[Any], prior_vah: Optional[float],
                 prior_val: Optional[float], open_price: Optional[float],
                 accept_closes: int = 2) -> Dict[str, Any]:
    """Open outside prior VA + acceptance back inside → expected full traverse.

    Returns {'active': bool, 'target_side': 'VAL'|'VAH'|None, 'target': px}:
    opened ABOVE value and accepted back in → rotation target = prior VAL
    (and mirror). Counter-fading that rotation is the losing trade the rule
    blocks. Inactive when open was inside value or acceptance never happened.
    """
    out = {"active": False, "target_side": None, "target": None}
    if not bars or None in (prior_vah, prior_val) or open_price is None:
        return out
    hi, lo = max(prior_vah, prior_val), min(prior_vah, prior_val)
    if lo <= open_price <= hi:
        return out                                # opened inside value — rule N/A
    closes = [c for c in (_g(b, "c", "close") for b in bars) if c is not None]
    run = 0
    for c in closes:
        run = run + 1 if (lo <= c <= hi) else 0
        if run >= accept_closes:
            if open_price > hi:
                out.update(active=True, target_side="VAL", target=lo)
            else:
                out.update(active=True, target_side="VAH", target=hi)
            return out
    return out


# ── P2-12 · EOD continuation tag ────────────────────────────────────────────

def eod_continuation_tag(day_type: Optional[str], close_pos: Optional[float],
                         direction: Optional[str] = None) -> Optional[str]:
    """Terminal type + close location → tomorrow's named statistical bias.

    Tags (Dalton EOD carry): NE_CLOSE_UP/DOWN (Neutral-Extreme resolved late —
    momentum carry), TREND_CARRY_UP/DOWN (trend close = higher-open odds),
    BALANCE_NO_CARRY (center close — no edge). None when inputs missing.
    """
    if not day_type or close_pos is None:
        return None
    up = close_pos >= 0.75
    dn = close_pos <= 0.25
    if day_type == "Neutral_Extreme" and (up or dn):
        return "NE_CLOSE_UP" if up else "NE_CLOSE_DOWN"
    if day_type in ("Trend_Normal", "Trend_DD") and (up or dn):
        return "TREND_CARRY_UP" if up else "TREND_CARRY_DOWN"
    if day_type in ("Normal", "Neutral_Center", "Nontrend", "Nonconviction"):
        return "BALANCE_NO_CARRY"
    if day_type == "Normal_Variation" and (up or dn):
        return "VARIATION_LEAN_UP" if up else "VARIATION_LEAN_DOWN"
    return "BALANCE_NO_CARRY"
