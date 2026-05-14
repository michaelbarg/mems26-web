"""Sweep-Return signal detector — Constitution V3 Layer 1 T3.

SWEEP-RETURN: liquidity sweep through a price extreme (stop hunt)
followed by price returning inside the prior range. Indicates
false breakout / stop run — reversal signal.

Algorithm:
  1. Track recent range (highest high, lowest low over lookback)
  2. Current bar extends beyond range extreme (the sweep)
  3. Bar closes back inside the prior range (the return)
  4. Stronger if return happens within 1-3 bars
  Direction: opposite to the sweep direction

Returns signal dict or None.
"""
from typing import Dict, List, Optional


# V1 defaults — calibrate post-SHADOW
LOOKBACK = 5
MIN_SWEEP_TICKS = 2.0  # minimum extension beyond range (points)
RETURN_BARS = 3  # sweep must return within this many bars


def detect_sweep_return(
    recent_bars: List[Dict],
    current_bar: Dict,
) -> Optional[Dict]:
    """Detect sweep-return (liquidity sweep) pattern.

    Args:
        recent_bars: last N closed bars (oldest first)
        current_bar: the just-closed bar

    Returns:
        Signal dict or None.
    """
    if len(recent_bars) < LOOKBACK:
        return None

    window = recent_bars[-(LOOKBACK + RETURN_BARS):-RETURN_BARS] if len(recent_bars) > LOOKBACK + RETURN_BARS else recent_bars[-LOOKBACK:]

    # Establish prior range
    range_high = max(b.get("high", b.get("h", 0)) for b in window)
    range_low = min(b.get("low", b.get("l", float("inf"))) for b in window)

    cur_high = float(current_bar.get("high", current_bar.get("h", 0)))
    cur_low = float(current_bar.get("low", current_bar.get("l", float("inf"))))
    cur_close = float(current_bar.get("close", current_bar.get("c", 0)))

    # --- Sweep HIGH + return (bearish sweep → SHORT) ---
    if cur_high > range_high + MIN_SWEEP_TICKS:
        # Swept above range — did price return inside?
        if cur_close <= range_high:
            sweep_pts = cur_high - range_high
            strength = min(1.0, sweep_pts / (MIN_SWEEP_TICKS * 4))
            return {
                "signal": "sweep_return",
                "direction": "SHORT",
                "level": range_high,
                "strength": round(strength, 3),
                "evidence": {
                    "sweep_type": "high_sweep",
                    "range_high": range_high,
                    "sweep_high": cur_high,
                    "sweep_pts": round(sweep_pts, 2),
                    "close_inside": True,
                },
            }

    # --- Sweep LOW + return (bullish sweep → LONG) ---
    if cur_low < range_low - MIN_SWEEP_TICKS:
        # Swept below range — did price return inside?
        if cur_close >= range_low:
            sweep_pts = range_low - cur_low
            strength = min(1.0, sweep_pts / (MIN_SWEEP_TICKS * 4))
            return {
                "signal": "sweep_return",
                "direction": "LONG",
                "level": range_low,
                "strength": round(strength, 3),
                "evidence": {
                    "sweep_type": "low_sweep",
                    "range_low": range_low,
                    "sweep_low": cur_low,
                    "sweep_pts": round(sweep_pts, 2),
                    "close_inside": True,
                },
            }

    return None
