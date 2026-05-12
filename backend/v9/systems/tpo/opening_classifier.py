"""TPO Opening Type Classifier.

Classifies the opening type based on first 30 min of cash session.
"""
from typing import Optional


def classify_opening(bars: list, ib_high: float = 0, ib_low: float = 0) -> str:
    """Classify opening type from first-hour bars.

    Returns: open_drive | open_test_drive | open_rejection_reverse | open_auction | NA
    """
    if not bars or len(bars) < 2:
        return "NA"

    first = bars[0]
    open_price = first.get("open", first.get("o", 0))
    ib_range = ib_high - ib_low if ib_high and ib_low else 0

    if ib_range <= 0:
        return "NA"

    # First 30 min move (first 6 bars of 5-min)
    first_half = bars[:6] if len(bars) >= 6 else bars
    highs = [b.get("high", b.get("h", 0)) for b in first_half]
    lows = [b.get("low", b.get("l", 0)) for b in first_half]
    closes = [b.get("close", b.get("c", 0)) for b in first_half]

    first_move = closes[-1] - open_price if closes else 0
    first_range = max(highs) - min(lows) if highs and lows else 0

    move_ratio = abs(first_move) / ib_range if ib_range > 0 else 0

    # Open Drive: strong directional move >= 60% of IB, no return
    if move_ratio >= 0.6:
        return "open_drive"

    # Open Test Drive: tests one side then drives opposite
    if len(bars) >= 4:
        mid_close = closes[len(closes) // 2] if closes else 0
        final_close = closes[-1] if closes else 0
        if (mid_close - open_price) * (final_close - open_price) < 0:
            return "open_test_drive"

    # Open Rejection Reverse: sharp reversal
    if first_range > 0 and abs(first_move) / first_range < 0.3:
        return "open_rejection_reverse"

    return "open_auction"
