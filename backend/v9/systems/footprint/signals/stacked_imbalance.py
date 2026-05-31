"""Stacked Imbalance signal detector — Constitution V3 Layer 1 T3.

STACKED IMBALANCE: N consecutive price cells where one side dominates
by imbalance ratio. Indicates institutional one-directional commitment.

Algorithm:
  1. Read footprint cells for current bar (bid_vol, ask_vol per price level)
  2. For each level: compute ratio = ask_vol / bid_vol (or inverse)
  3. Find consecutive runs where ratio > imb_threshold
  4. If run length >= stack_n → Stacked Imbalance detected
  5. Direction: LONG if ask-dominated (buyers), SHORT if bid-dominated (sellers)

Returns signal dict or None.
"""
from typing import Dict, List, Optional


# 🟡 V1 defaults — calibrate post-SHADOW
STACK_N = 3  # minimum consecutive imbalanced levels
IMB_THRESHOLD = 2.5  # Sierra default imbalance ratio (ask/bid or bid/ask)
MIN_LEVEL_VOL = 10  # minimum volume at level to count

# S3 volume-relative MIN_LEVEL_VOL (E2E 2/2 · shadow only)
from backend.v9.shared.atr import S3_RELATIVE  # noqa: E402
_MIN_VOL_MEDIAN_K = 0.3  # prior: 0.3 × median_level_vol


def get_min_level_vol(median_level_vol: float = 0.0) -> float:
    """Min volume at level — volume-relative when flag ON, not ATR-based."""
    if S3_RELATIVE and median_level_vol > 0:
        return _MIN_VOL_MEDIAN_K * median_level_vol
    return MIN_LEVEL_VOL


def detect_stacked_imbalance(
    footprint_levels: List[Dict],
    bar: Dict,
) -> Optional[Dict]:
    """Detect stacked imbalance from footprint price levels.

    Args:
        footprint_levels: list of {price, bid_vol, ask_vol, ...} per level,
            sorted by price ascending. Can come from bar["footprint"]["levels"]
            or from Sierra DLL footprint export.
        bar: the current bar dict (for context — close price, direction)

    Returns:
        Signal dict or None.
    """
    if not footprint_levels or len(footprint_levels) < STACK_N:
        return None

    # Scan for consecutive buy-dominated levels (ask > bid * threshold)
    buy_run = 0
    buy_run_start = -1
    best_buy_run = 0
    best_buy_start = -1

    # Scan for consecutive sell-dominated levels (bid > ask * threshold)
    sell_run = 0
    sell_run_start = -1
    best_sell_run = 0
    best_sell_start = -1

    for i, level in enumerate(footprint_levels):
        ask_v = float(level.get("ask_vol", level.get("agg_buy_vol", 0)) or 0)
        bid_v = float(level.get("bid_vol", level.get("agg_sell_vol", 0)) or 0)

        if ask_v < MIN_LEVEL_VOL and bid_v < MIN_LEVEL_VOL:
            buy_run = 0
            sell_run = 0
            continue

        # Buy imbalance: ask dominates
        if bid_v > 0 and ask_v / bid_v >= IMB_THRESHOLD:
            if buy_run == 0:
                buy_run_start = i
            buy_run += 1
            if buy_run > best_buy_run:
                best_buy_run = buy_run
                best_buy_start = buy_run_start
        else:
            buy_run = 0

        # Sell imbalance: bid dominates
        if ask_v > 0 and bid_v / ask_v >= IMB_THRESHOLD:
            if sell_run == 0:
                sell_run_start = i
            sell_run += 1
            if sell_run > best_sell_run:
                best_sell_run = sell_run
                best_sell_start = sell_run_start
        else:
            sell_run = 0

    # Check for stacked buy imbalance (LONG signal)
    if best_buy_run >= STACK_N:
        price_lo = footprint_levels[best_buy_start].get("price", 0)
        price_hi = footprint_levels[best_buy_start + best_buy_run - 1].get("price", 0)
        strength = min(1.0, best_buy_run / (STACK_N * 2))
        return {
            "signal": "stacked_imbalance",
            "direction": "LONG",
            "level": (price_lo + price_hi) / 2 if price_lo and price_hi else 0,
            "strength": round(strength, 3),
            "evidence": {
                "stack_count": best_buy_run,
                "stack_type": "BUY_DOMINATED",
                "price_range": [price_lo, price_hi],
                "threshold": IMB_THRESHOLD,
            },
        }

    # Check for stacked sell imbalance (SHORT signal)
    if best_sell_run >= STACK_N:
        price_lo = footprint_levels[best_sell_start].get("price", 0)
        price_hi = footprint_levels[best_sell_start + best_sell_run - 1].get("price", 0)
        strength = min(1.0, best_sell_run / (STACK_N * 2))
        return {
            "signal": "stacked_imbalance",
            "direction": "SHORT",
            "level": (price_lo + price_hi) / 2 if price_lo and price_hi else 0,
            "strength": round(strength, 3),
            "evidence": {
                "stack_count": best_sell_run,
                "stack_type": "SELL_DOMINATED",
                "price_range": [price_lo, price_hi],
                "threshold": IMB_THRESHOLD,
            },
        }

    return None
