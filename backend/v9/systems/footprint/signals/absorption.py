"""Absorption signal detector — Constitution V3 Layer 1 T3.

ABSORPTION: strong opposing volume at a price extreme that fails to
push price further in that direction. Indicates institutional defense
of a level — reversal signal.

Algorithm:
  1. Look at last N bars (lookback window)
  2. Find extreme bar (highest high or lowest low)
  3. At extreme: counter-side volume > same-side volume * absorption_ratio
  4. Price did NOT extend extreme in subsequent bar(s)
  → Absorption detected

Returns signal dict or None.
"""
from typing import Dict, List, Optional


# 🟡 V1 defaults — calibrate post-SHADOW
LOOKBACK = 5
ABSORPTION_RATIO = 2.0  # counter-volume must be 2x same-side
MIN_VOLUME = 50  # minimum volume at extreme to be meaningful


def detect_absorption(
    recent_bars: List[Dict],
    current_bar: Dict,
) -> Optional[Dict]:
    """Detect absorption at price extremes.

    Args:
        recent_bars: last N closed bars (oldest first), each with
            high/low/close/ask_vol/bid_vol
        current_bar: the just-closed bar

    Returns:
        Signal dict or None if no absorption detected.
    """
    if len(recent_bars) < LOOKBACK:
        return None

    window = recent_bars[-LOOKBACK:]

    # Find extremes in the window
    highest_bar = max(window, key=lambda b: b.get("high", b.get("h", 0)))
    lowest_bar = min(window, key=lambda b: b.get("low", b.get("l", float("inf"))))

    cur_high = current_bar.get("high", current_bar.get("h", 0))
    cur_low = current_bar.get("low", current_bar.get("l", float("inf")))

    # --- Absorption at HIGH (bearish absorption → LONG signal from defense) ---
    extreme_high = highest_bar.get("high", highest_bar.get("h", 0))
    if cur_high <= extreme_high:  # price did NOT extend the high
        ask_vol = float(highest_bar.get("ask_vol", highest_bar.get("agg_buy_vol", 0)) or 0)
        bid_vol = float(highest_bar.get("bid_vol", highest_bar.get("agg_sell_vol", 0)) or 0)
        # At a high, sellers (bid_vol) absorbing buyers (ask_vol) = bearish
        # Buyers pushing but sellers absorbing → SHORT signal
        if bid_vol > ask_vol * ABSORPTION_RATIO and bid_vol >= MIN_VOLUME:
            strength = min(1.0, (bid_vol / max(ask_vol, 1)) / (ABSORPTION_RATIO * 2))
            return {
                "signal": "absorption",
                "direction": "SHORT",
                "level": extreme_high,
                "strength": round(strength, 3),
                "evidence": {
                    "extreme_type": "high",
                    "ask_vol": ask_vol,
                    "bid_vol": bid_vol,
                    "ratio": round(bid_vol / max(ask_vol, 1), 2),
                    "price_extended": False,
                },
            }

    # --- Absorption at LOW (bullish absorption → SHORT signal from defense) ---
    extreme_low = lowest_bar.get("low", lowest_bar.get("l", float("inf")))
    if cur_low >= extreme_low:  # price did NOT extend the low
        ask_vol = float(lowest_bar.get("ask_vol", lowest_bar.get("agg_buy_vol", 0)) or 0)
        bid_vol = float(lowest_bar.get("bid_vol", lowest_bar.get("agg_sell_vol", 0)) or 0)
        # At a low, buyers (ask_vol) absorbing sellers (bid_vol) = bullish
        # Sellers pushing but buyers absorbing → LONG signal
        if ask_vol > bid_vol * ABSORPTION_RATIO and ask_vol >= MIN_VOLUME:
            strength = min(1.0, (ask_vol / max(bid_vol, 1)) / (ABSORPTION_RATIO * 2))
            return {
                "signal": "absorption",
                "direction": "LONG",
                "level": extreme_low,
                "strength": round(strength, 3),
                "evidence": {
                    "extreme_type": "low",
                    "ask_vol": ask_vol,
                    "bid_vol": bid_vol,
                    "ratio": round(ask_vol / max(bid_vol, 1), 2),
                    "price_extended": False,
                },
            }

    return None
