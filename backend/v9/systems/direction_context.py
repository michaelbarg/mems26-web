"""direction_context — the dynamic auction-direction brain (#68, Michael 2026-06-22).

Determines the CURRENT trade direction continuously from FOUR inputs, NOT from a
static day-type label:
  (1) price LOCATION vs IB / value (POC),
  (2) CVD (cumulative volume delta) slope — is the move backed by volume,
  (3) the IB BREAKOUT STATE — accepted (held beyond IB) vs failed (poked then back),
  (4) the day-type frames the levels.

Michael's model (06-11 was the teaching case):
  - IB broke up and HELD (accepted) + CVD up   → go-WITH up      → UP
  - IB broke up but FAILED (poked, back inside) + CVD down → fade → DOWN
  - IB broke down but FAILED (poked, back inside) + CVD up  → reversal → UP   ← the 06-11 "home-run"
  - IB broke down and HELD (accepted) + CVD down → go-WITH down  → DOWN
  - inside / balance: revert to value by location + CVD

This is a PURE, side-effect-free function so it is unit-testable and reusable by
the live endpoint/strip and (later, flag-gated) the trading gate. Honest (Rule 1):
returns NEUTRAL whenever the data or the IB is missing — never guesses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def cvd_slope(bars: List[Dict[str, Any]], lookback: int = 3) -> int:
    """+1 if net volume delta is positive over the last `lookback` bars, -1 if negative, 0 flat/unknown.

    NOTE (2026-06-24 bug-fix): the `cumulative_delta` column in v9_bars_5min actually
    holds PER-BAR delta (ask−bid for that bar), not a running cumulative. The old formula
    `sign(cum[-1] − cum[-1-3])` compared two arbitrary per-bar values = noise/wrong sign.
    Fixed to `sign(Σ delta over last N bars)` = net buying/selling pressure over the window.
    """
    window = bars[-lookback:] if len(bars) >= lookback else bars
    if not window:
        return 0
    total = 0.0
    count = 0
    for b in window:
        d = b.get("cumulative_delta")
        if d is not None:
            total += float(d)
            count += 1
    if count == 0:
        return 0
    return _sign(total)


def is_chop(bars: List[Dict[str, Any]], ib_high: Optional[float],
            ib_low: Optional[float], lookback: int = 8, range_frac: float = 0.55) -> bool:
    """Chop-guard: the last `lookback` bars stayed inside a band NARROWER than
    `range_frac` x the IB width → no real movement → fades just bleed (the 06-11
    failure). Pure + testable. False when data/IB missing (honest, Rule 1)."""
    if not bars or ib_high is None or ib_low is None:
        return False
    ibw = float(ib_high) - float(ib_low)
    if ibw <= 0:
        return False
    w = bars[-lookback:] if len(bars) >= lookback else bars
    if len(w) < 3:
        return False
    rng = max(float(b["high"]) for b in w) - min(float(b["low"]) for b in w)
    return rng < range_frac * ibw


def lsma_cvd_veto_direction(lsma_side: int, cvd_slope_val: int) -> str:
    """Pure LSMA-lead + CVD-veto direction rule.

    Direction = LSMA side; CVD only vetoes (→ NEUTRAL) when it directly opposes.

    Truth table:
      lsma +1, cvd +1 → UP
      lsma +1, cvd −1 → NEUTRAL (CVD opposes)
      lsma +1, cvd  0 → UP     (CVD silent → LSMA leads)
      lsma −1, cvd −1 → DOWN
      lsma −1, cvd +1 → NEUTRAL
      lsma −1, cvd  0 → DOWN
    """
    if cvd_slope_val != 0 and _sign(cvd_slope_val) == -lsma_side:
        return "NEUTRAL"
    return "UP" if lsma_side > 0 else "DOWN"


def compute_direction(
    *,
    bars: List[Dict[str, Any]],
    ib_high: Optional[float],
    ib_low: Optional[float],
    poc: Optional[float] = None,
    cvd_lookback: int = 3,
    day_type: Optional[str] = None,
    lsma_side: Optional[int] = None,
    lsma_veto: bool = False,
) -> Dict[str, Any]:
    """Current auction direction from CVD + location + IB breakout-state.

    bars: chronological RTH 5-min bars, each a dict with at least
          `high`, `low`, `close`, `cumulative_delta` (per-bar delta, not running cumulative).
    Returns: {dir: UP|DOWN|NEUTRAL, breakout_state, reason, cvd_slope,
              session_high, session_low, close}.
    """
    if not bars:
        return {"dir": "NEUTRAL", "breakout_state": "no_data",
                "reason": "no bars", "cvd_slope": 0}

    cs = cvd_slope(bars, cvd_lookback)
    session_high = max(float(b["high"]) for b in bars)
    session_low = min(float(b["low"]) for b in bars)
    close = float(bars[-1]["close"])

    base = {"cvd_slope": cs, "session_high": session_high,
            "session_low": session_low, "close": close}

    # --- LSMA-lead + CVD-veto override (DIRECTION_LSMA_VETO flag) ---
    if lsma_veto and lsma_side is not None:
        d = lsma_cvd_veto_direction(lsma_side, cs)
        return {**base, "dir": d, "breakout_state": "lsma_cvd_veto",
                "lsma_side": lsma_side,
                "reason": "LSMA %s + CVD-slope %+d → %s" % (
                    "UP" if lsma_side > 0 else "DOWN", cs, d)}

    if ib_high is None or ib_low is None:
        return {**base, "dir": "NEUTRAL", "breakout_state": "forming",
                "reason": "IB not locked yet (forming)"}

    H = float(ib_high)
    L = float(ib_low)
    P = float(poc) if poc is not None else (H + L) / 2.0

    broke_up = session_high > H
    broke_down = session_low < L
    holding_up = close > H
    holding_down = close < L

    # --- accepted breakouts → go WITH ---
    if holding_up and cs >= 0:
        return {**base, "dir": "UP", "breakout_state": "accepted_up",
                "reason": "accepted breakout above IB + CVD up → go-with"}
    if holding_down and cs <= 0:
        return {**base, "dir": "DOWN", "breakout_state": "accepted_down",
                "reason": "accepted breakdown below IB + CVD down → go-with"}

    # --- TREND-day override (fixes 06-16) ---
    # On a confirmed trend day, anything that is NOT an accepted breakout the OTHER way is a
    # PULLBACK, not a reversal. Stay WITH the established trend instead of fading-to-value or
    # calling a failed-low a "reversal" on every CVD uptick (24 wrong UP reads on 06-16). The
    # day-type is the authority; on Neutral/Normal the fade/reversal branches below still apply
    # (preserves the 06-11 failed-low→reversal). A real reversal shows up as an accepted breakout
    # the other way (handled above) or as the classifier flipping day_type off Trend.
    if day_type in ("Trend_Normal", "Trend_DD"):
        broke_dn_amt = max(0.0, L - session_low)
        broke_up_amt = max(0.0, session_high - H)
        if broke_dn_amt > broke_up_amt:
            return {**base, "dir": "DOWN", "breakout_state": "trend_with",
                    "reason": "trend day (%s) — pullback stays with DOWN trend" % day_type}
        if broke_up_amt > broke_dn_amt:
            return {**base, "dir": "UP", "breakout_state": "trend_with",
                    "reason": "trend day (%s) — pullback stays with UP trend" % day_type}

    # --- failed breakouts → fade / reversal ---
    if broke_up and not holding_up and cs < 0:
        return {**base, "dir": "DOWN", "breakout_state": "failed_up",
                "reason": "failed high (poked IB, back inside) + CVD down → fade short"}
    if broke_down and not holding_down and cs > 0:
        return {**base, "dir": "UP", "breakout_state": "failed_low",
                "reason": "failed low (poked IB, back inside) + CVD up → reversal long"}

    # --- inside / balance ---
    # chop-guard FIRST: in a narrow chop band, don't fade (06-11) — stand aside.
    if is_chop(bars, H, L):
        return {**base, "dir": "NEUTRAL", "breakout_state": "chop",
                "reason": "chop — narrow range, no conviction → stand aside (no fade)"}
    # otherwise revert to value by location + CVD
    if close > P and cs < 0:
        return {**base, "dir": "DOWN", "breakout_state": "balance",
                "reason": "above value + CVD down → back to value"}
    if close < P and cs > 0:
        return {**base, "dir": "UP", "breakout_state": "balance",
                "reason": "below value + CVD up → back to value"}

    return {**base, "dir": "NEUTRAL", "breakout_state": "balance",
            "reason": "inside value / CVD unclear"}
