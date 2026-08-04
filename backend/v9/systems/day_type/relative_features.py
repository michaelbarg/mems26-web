"""relative_features.py — RELATIVE day-type input features (S1).

Pure functions. Compute the relative signals that the dynamic day-type table
(`config/daytype_trading_plan.yaml`) needs, from the session's 5-min RTH bars +
the locked IB. NO absolute thresholds live here — only the relative MEASUREMENTS;
the bands/ratios live in the YAML. This module is NOT yet wired into the live
engine, so it changes no behavior on its own.

Bar-derived features (CVD / IB-percentile / TPO features are layered separately):
  rib                   = (session_high - session_low) / IB_width   ← master regime signal
  sides                 = # IB edges with a CLOSED bar beyond (+buffer)  → 0 / 1 / 2
  ext_up/dn_hold        = a closed 5-min bar beyond the IB edge (+buffer)
  ext_up/dn_bars        = how many closed bars beyond (>=2 = trend-grade hold)
  close_pos             = (last_close - session_low)/(session_high - session_low) ∈ 0..1
  one_tf                = "UP" / "DOWN" / None  (30-min period HL-no-LL / LH-no-HH)
  returned_through_open = a directional open that closed back through the open
  bars_since_ib         = bars after IB close (≈ minutes/5 past 60-min lock)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

TICK = 0.25


def _g(bar: Any, *keys: str):
    """First present key from a bar dict/obj (supports o/h/l/c and open/high/low/close)."""
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


@dataclass
class RelFeatures:
    rib: Optional[float] = None
    sides: int = 0
    ext_up_hold: bool = False
    ext_dn_hold: bool = False
    ext_up_bars: int = 0
    ext_dn_bars: int = 0
    close_pos: Optional[float] = None
    one_tf: Optional[str] = None
    # P1-4 (Dalton p.25): CURRENT consecutive stair-step run per side, over
    # 30-min periods, ending at the latest period. Up-step = higher-low AND
    # higher-high vs the prior period; down-step mirror. The one-timeframe
    # "control" measure that defines a Trend day — feeds P1-5/P0-3.
    stair_steps_up: int = 0
    stair_steps_dn: int = 0
    session_high: Optional[float] = None
    session_low: Optional[float] = None
    returned_through_open: bool = False
    bars_since_ib: int = 0
    n_bars: int = 0
    session_volume: Optional[float] = None
    avg_bar_volume: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _one_tf(period_lows: List[float], period_highs: List[float], tol: float) -> Optional[str]:
    """30-min-period one-timeframe: UP if no period makes a Lower-Low (and it's not
    also flat-down); DOWN if no period makes a Higher-High. Needs >=2 periods."""
    if len(period_lows) < 2:
        return None
    up = all(period_lows[i] >= period_lows[i - 1] - tol for i in range(1, len(period_lows)))
    dn = all(period_highs[i] <= period_highs[i - 1] + tol for i in range(1, len(period_highs)))
    if up and not dn:
        return "UP"
    if dn and not up:
        return "DOWN"
    return None


def _max_consec(closes: List[float], thr: float, up: bool) -> int:
    """Longest run of CONSECUTIVE closes beyond thr (a real held extension, not a drift)."""
    best = cur = 0
    for c in closes:
        if (c >= thr) if up else (c <= thr):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def level_acceptance(
    bars: List[Any],
    level: Optional[float],
    side: str,
    *,
    ext_buffer_ticks: float = 2.0,
    tick: float = TICK,
    hold_bars: int = 2,
    vol_accept_frac: float = 0.08,
) -> Dict[str, Any]:
    """P0-1 v2 (Michael 2026-07-12; Dalton pp.37-38, 278-293): acceptance test at an
    ARBITRARY reference level — prior-day high/low, prior value-area edge, balance
    bracket, or the IB edge itself. Same mechanics as the IB acceptance above:

      accepted  = >= `hold_bars` CONSECUTIVE closes beyond the level (+2-tick buffer)
                  AND >= `vol_accept_frac` of session volume traded beyond it
                  (typical-price test; volume gate skipped when bars carry no volume,
                  e.g. synthetic tests — close-hold decides, matching the IB code).
      rejected_after_accept = it WAS accepted earlier, but the LAST `hold_bars`
                  closes are back INSIDE the raw level — "return inside the
                  reference = rejection / failed breakout" (doctrine P0-1).
      accept_bar = index of the bar that completed the first hold (None if never).

    side: "UP" = acceptance above the level · "DOWN" = below. Pure, no I/O.
    """
    out = {"accepted": False, "rejected_after_accept": False, "accept_bar": None}
    if level is None or not bars or side not in ("UP", "DOWN"):
        return out
    closes = [c for c in (_g(b, "c", "close") for b in bars) if c is not None]
    if len(closes) < hold_bars:
        return out
    up = side == "UP"
    thr = level + ext_buffer_ticks * tick if up else level - ext_buffer_ticks * tick

    # first completed hold (consecutive closes beyond the buffered level)
    run = 0
    for i, c in enumerate(closes):
        if (c >= thr) if up else (c <= thr):
            run += 1
            if run >= hold_bars and out["accept_bar"] is None:
                out["accept_bar"] = i
        else:
            run = 0
    held = out["accept_bar"] is not None

    # volume acceptance beyond the RAW level (same test as the IB block above)
    vol_ok = True
    sess_v = sum(v for v in (_g(b, "v", "volume") for b in bars) if v is not None) or 0.0
    if sess_v > 0:
        def _tp(b):
            h, l, c = _g(b, "h", "high"), _g(b, "l", "low"), _g(b, "c", "close")
            return (h + l + c) / 3.0 if None not in (h, l, c) else None
        v_beyond = sum(
            (_g(b, "v", "volume") or 0) for b in bars
            if (tp := _tp(b)) is not None and ((tp > level) if up else (tp < level))
        )
        vol_ok = v_beyond >= vol_accept_frac * sess_v

    if not (held and vol_ok):
        return out

    # currently rejected? — the last `hold_bars` closes back INSIDE the raw level
    tail = closes[-hold_bars:]
    back_inside = all((c < level) if up else (c > level) for c in tail)
    if back_inside:
        out["rejected_after_accept"] = True
    else:
        out["accepted"] = True
    return out


def compute_relative_features(
    bars: List[Any],
    ib_high: Optional[float],
    ib_low: Optional[float],
    open_price: Optional[float] = None,
    *,
    ext_buffer_ticks: float = 2.0,
    tick: float = TICK,
    bars_per_30min: int = 6,
    ib_bars: int = 12,
    ext_min_frac: float = 0.3,   # a real range-extension closes >= 0.3*IB beyond the edge
    ext_hold_bars: int = 2,      # ...and HOLDS >= 2 consecutive bars (per the spec)
    vol_accept_frac: float = 0.08,  # ...AND >= 8% of session volume is ACCEPTED beyond the IB edge
) -> RelFeatures:
    """Compute relative features from ordered, in-session RTH 5-min bars.

    bars: list of bar dicts/objs with o/h/l/c (or open/high/low/close).
    ib_high/ib_low: locked IB (None => rib/sides degrade to None/0).
    open_price: session open (defaults to first bar's open).
    """
    f = RelFeatures(n_bars=len(bars))
    if not bars:
        return f

    highs = [h for h in (_g(b, "h", "high") for b in bars) if h is not None]
    lows = [l for l in (_g(b, "l", "low") for b in bars) if l is not None]
    closes = [c for c in (_g(b, "c", "close") for b in bars) if c is not None]
    if not highs or not lows or not closes:
        return f

    sh, sl = max(highs), min(lows)
    f.session_high, f.session_low = sh, sl
    vols = [v for v in (_g(b, "v", "volume") for b in bars) if v is not None]
    if vols:
        f.session_volume = round(sum(vols), 2)
        f.avg_bar_volume = round(sum(vols) / len(vols), 2)
    if open_price is None:
        open_price = _g(bars[0], "o", "open")
    buf = ext_buffer_ticks * tick
    rng = sh - sl

    if rng > 0:
        f.close_pos = round((closes[-1] - sl) / rng, 4)

    # --- IB = SIERRA's first-hour range (the authority — Michael 2026-06-20). Sierra has the full
    # first hour even when the ingested bars are missing period A (06-08: bars start 10:00, so a
    # bars-derived IB is wrong/tiny). RANGE EXTENSION = a CLOSE beyond Sierra's IB: since Sierra's
    # IB IS the first-hour high/low, any close beyond it is necessarily AFTER the first hour (during
    # the first hour price is inside the IB by definition) — so no bar-index restriction is needed,
    # which is what kept 06-08's two-sided break from registering. Fall back to the bars' first hour
    # ONLY when Sierra has no session (06-17).
    if ib_high is not None and ib_low is not None and (ib_high - ib_low) > 0:
        ib_ref_h, ib_ref_l, ext_pool = ib_high, ib_low, closes          # Sierra IB (authority)
    else:
        n_ib = min(ib_bars, len(bars))
        ib_ref_h = max(highs[:n_ib]) if n_ib else None                  # bars first-hour (fallback)
        ib_ref_l = min(lows[:n_ib]) if n_ib else None
        ext_pool = closes[n_ib:]                                        # only post-B bars extend it

    if ib_ref_h is not None and ib_ref_l is not None and (ib_ref_h - ib_ref_l) > 0:
        f.rib = round(rng / (ib_ref_h - ib_ref_l), 4)
        # A break is a CLOSE just beyond the IB edge (small buffer) that HOLDS >= 2 consecutive bars
        # (the 06-19 marginal-drift filter). No "0.3*IB" magnitude (it buried real breaks on wide IBs).
        up_thr = ib_ref_h + buf
        dn_thr = ib_ref_l - buf
        f.ext_up_bars = sum(1 for c in ext_pool if c >= up_thr)
        f.ext_dn_bars = sum(1 for c in ext_pool if c <= dn_thr)
        up_hold = _max_consec(ext_pool, up_thr, True) >= ext_hold_bars
        dn_hold = _max_consec(ext_pool, dn_thr, False) >= ext_hold_bars
        # ACCEPTANCE: a real side needs VOLUME accepted beyond the IB, not just a price poke.
        # 06-10's morning drift closed above the IB but carried only 2.7% of the day's volume (a
        # thin/rejected tail) → NOT a side → one-sided down = Normal_Variation, not Neutral
        # (Michael 2026-06-20). Skipped when bars carry no volume (synthetic tests) → close-hold decides.
        sess_v = sum(v for v in (_g(b, "v", "volume") for b in bars) if v is not None) or 0.0
        if sess_v > 0:
            def _tp(b):
                h, l, c = _g(b, "h", "high"), _g(b, "l", "low"), _g(b, "c", "close")
                return (h + l + c) / 3.0 if None not in (h, l, c) else None
            v_above = sum((_g(b, "v", "volume") or 0) for b in bars if (_tp(b) or -1e9) > ib_ref_h)
            v_below = sum((_g(b, "v", "volume") or 0) for b in bars if (_tp(b) or 1e9) < ib_ref_l)
            up_hold = up_hold and (v_above >= vol_accept_frac * sess_v)
            dn_hold = dn_hold and (v_below >= vol_accept_frac * sess_v)
        f.ext_up_hold, f.ext_dn_hold = up_hold, dn_hold
        f.sides = int(up_hold) + int(dn_hold)

        # FIX-14 (Michael doctrine ruling 2026-07-10; Dalton pp.27-29): side
        # counting is MECHANICAL Range-Extension beyond the IB — acceptance
        # belongs to reclassification (accepted_break above keeps the volume
        # test), NOT to counting. "נייטרלי = יום מבולגן עם פריצה משני הצדדים".
        # Noise floor per ruling: an extension counts when it reaches
        # max(2pt, 20% × IB width). Calibration pair: 07-10 (31.5/28pt on IB
        # 5.25 → sides=2 → Neutral) · 07-09 (3pt on IB 37 → not counted →
        # stays Variation). Flag DAYTYPE_SIDES_MECHANICAL_V1 (default OFF).
        # ext_up_hold/ext_dn_hold are NOT touched — accepted_break unchanged.
        if os.getenv("DAYTYPE_SIDES_MECHANICAL_V1", "0").lower() in ("1", "true", "yes"):
            _ib_w = ib_ref_h - ib_ref_l
            # IB_BREAK_ANY_EXPANSION_V1 (Dalton alignment 2026-07-20):
            # ANY acceptance beyond IB = expansion. Noise floor → 0 (just the
            # fixed minimum pts, typically 2pt). Overrides the IB-frac gate that
            # filtered real breaks on wide IB days (#420: 5pt break < 8pt floor).
            if os.getenv("IB_BREAK_ANY_EXPANSION_V1", "0").lower() in ("1", "true", "yes"):
                # The intent of IB_BREAK_ANY_EXPANSION is "any acceptance beyond
                # IB = expansion" — the noise floor should be minimal (2 ticks =
                # 0.5pt for MES). The old default of 2.0pt blocked real 1.75pt
                # extensions (07-16) and 1.0pt (07-30) → sides=1 instead of 2 →
                # misclassified as NV instead of Neutral.
                _noise = float(os.getenv("DAYTYPE_SIDES_NOISE_PTS", "0.5"))
            else:
                _noise = max(
                    float(os.getenv("DAYTYPE_SIDES_NOISE_PTS", "2.0")),
                    float(os.getenv("DAYTYPE_SIDES_NOISE_IB_FRAC", "0.20")) * _ib_w,
                )
            if ib_high is not None and ib_low is not None and (ib_high - ib_low) > 0:
                # Sierra IB is the first-hour extremes — any price beyond it is
                # necessarily post-first-hour, so session extremes are valid RE.
                _mech_hi, _mech_lo = sh, sl
            else:
                _n_ib = min(ib_bars, len(bars))
                _mech_hi = max(highs[_n_ib:]) if len(highs) > _n_ib else None
                _mech_lo = min(lows[_n_ib:]) if len(lows) > _n_ib else None
            _mech_up = _mech_hi is not None and (_mech_hi - ib_ref_h) >= _noise
            _mech_dn = _mech_lo is not None and (ib_ref_l - _mech_lo) >= _noise
            f.sides = int(_mech_up) + int(_mech_dn)

    period_lows: List[float] = []
    period_highs: List[float] = []
    for i in range(0, len(bars), bars_per_30min):
        chunk = bars[i:i + bars_per_30min]
        pl = [l for l in (_g(b, "l", "low") for b in chunk) if l is not None]
        ph = [h for h in (_g(b, "h", "high") for b in chunk) if h is not None]
        if pl and ph:
            period_lows.append(min(pl))
            period_highs.append(max(ph))
    f.one_tf = _one_tf(period_lows, period_highs, tol=tick)

    # P1-4 (Dalton p.25): stair-step counters — reset on any break of the run.
    for i in range(1, len(period_lows)):
        up = (period_lows[i] >= period_lows[i - 1] - tick
              and period_highs[i] > period_highs[i - 1])
        dn = (period_highs[i] <= period_highs[i - 1] + tick
              and period_lows[i] < period_lows[i - 1])
        f.stair_steps_up = f.stair_steps_up + 1 if up else 0
        f.stair_steps_dn = f.stair_steps_dn + 1 if dn else 0

    # returned_through_open: a DIRECTIONAL open that later closed back through the open
    if open_price is not None and len(closes) >= 2:
        init = closes[1] - open_price
        if init > buf:
            f.returned_through_open = any(c < open_price - buf for c in closes[1:])
        elif init < -buf:
            f.returned_through_open = any(c > open_price + buf for c in closes[1:])

    f.bars_since_ib = max(0, len(bars) - ib_bars)
    return f
