"""Exhaustion signal detector — Constitution V3 Layer 1 T3.

EXHAUSTION: strong directional bar with diminishing volume compared
to prior bars average. Indicates the trend is running out of fuel —
counter-trend reversal signal.

Algorithm:
  1. Current bar is directional (close near high or low)
  2. Prior N bars show a trend in same direction
  3. Current bar volume < avg_volume * exhaustion_factor
  → Exhaustion detected, direction = counter-trend

Returns signal dict or None.
"""
from typing import Dict, List, Optional


# V1 defaults — calibrate post-SHADOW
TREND_BARS = 4  # minimum bars in same direction to qualify as trend
EXHAUSTION_FACTOR = 0.6  # volume must be < 60% of avg
DIRECTIONAL_BODY_PCT = 0.5  # bar body must be >= 50% of range


def detect_exhaustion(
    recent_bars: List[Dict],
    current_bar: Dict,
) -> Optional[Dict]:
    """Detect exhaustion (volume divergence at trend end).

    Args:
        recent_bars: last N closed bars (oldest first)
        current_bar: the just-closed bar

    Returns:
        Signal dict or None.
    """
    if len(recent_bars) < TREND_BARS:
        return None

    cur_o = float(current_bar.get("open", current_bar.get("o", 0)))
    cur_h = float(current_bar.get("high", current_bar.get("h", 0)))
    cur_l = float(current_bar.get("low", current_bar.get("l", 0)))
    cur_c = float(current_bar.get("close", current_bar.get("c", 0)))
    cur_vol = float(current_bar.get("volume", current_bar.get("v", current_bar.get("vol", 0))) or 0)

    bar_range = cur_h - cur_l
    if bar_range <= 0 or cur_vol <= 0:
        return None

    body = abs(cur_c - cur_o)
    body_pct = body / bar_range

    # Bar must be directional (body >= 60% of range)
    if body_pct < DIRECTIONAL_BODY_PCT:
        return None

    is_bull_bar = cur_c > cur_o

    # Check prior bars form a trend in same direction
    window = recent_bars[-TREND_BARS:]
    trend_count = 0
    for b in window:
        b_c = float(b.get("close", b.get("c", 0)))
        b_o = float(b.get("open", b.get("o", 0)))
        if is_bull_bar and b_c > b_o:
            trend_count += 1
        elif not is_bull_bar and b_c < b_o:
            trend_count += 1

    if trend_count < TREND_BARS:
        return None  # no sustained trend

    # Volume check: current bar volume < avg * factor
    avg_vol = sum(
        float(b.get("volume", b.get("v", b.get("vol", 0))) or 0)
        for b in window
    ) / max(len(window), 1)

    if avg_vol <= 0:
        return None

    if cur_vol >= avg_vol * EXHAUSTION_FACTOR:
        return None  # volume not diminished enough

    vol_ratio = cur_vol / avg_vol
    strength = min(1.0, (1.0 - vol_ratio) / 0.5)

    # Direction = counter-trend (exhaustion signals reversal)
    direction = "SHORT" if is_bull_bar else "LONG"
    level = cur_h if is_bull_bar else cur_l

    return {
        "signal": "exhaustion",
        "direction": direction,
        "level": level,
        "strength": round(strength, 3),
        "evidence": {
            "trend_direction": "UP" if is_bull_bar else "DOWN",
            "trend_bars": trend_count,
            "current_vol": cur_vol,
            "avg_vol": round(avg_vol, 1),
            "vol_ratio": round(vol_ratio, 3),
            "body_pct": round(body_pct, 3),
        },
    }
