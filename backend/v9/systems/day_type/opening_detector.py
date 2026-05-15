"""Opening Detector — 5 sub-types per Mind Over Markets pp.63-74 + Zohar Figure 4-6.

Types: OD (Open Drive), OTD (Open Test Drive), ORR (Open Rejection Reverse),
       OA_IN (Open Auction Inside PDH/PDL), OA_OUT (Open Auction Outside PDH/PDL)

Lock time: 09:40 ET (first 10 min of RTH).
"""
from datetime import time
from typing import Optional
from .schemas import OpeningType

# LOCKED: 09:40 ET lock time (Zohar Figure 4-6)
OPENING_LOCK_TIME = time(9, 40)


def detect_opening_type(
    bars_first_10min: list,
    open_price: float,
    prev_day_high: Optional[float] = None,
    prev_day_low: Optional[float] = None,
) -> OpeningType:
    """Classify opening type from first 10 minutes of RTH bars.

    Args:
        bars_first_10min: first 2 five-min bars (09:30-09:40), each with o/h/l/c
        open_price: first trade at 09:30 ET
        prev_day_high/low: previous day range (for OA_IN vs OA_OUT)

    Returns:
        OpeningType enum value
    """
    if not bars_first_10min:
        return OpeningType.UNKNOWN

    high_10 = max(b.get("h", b.get("high", 0)) for b in bars_first_10min)
    low_10 = min(b.get("l", b.get("low", float("inf"))) for b in bars_first_10min)
    range_10 = high_10 - low_10
    close_10 = bars_first_10min[-1].get("c", bars_first_10min[-1].get("close", open_price))

    # OD: Open Drive — aggressive move, no retest of open (Mind Over Markets p.65)
    bar_1 = bars_first_10min[0]
    bar_1_low = bar_1.get("l", bar_1.get("low", 0))
    bar_1_high = bar_1.get("h", bar_1.get("high", 0))

    if bar_1_low >= open_price and close_10 > open_price + range_10 * 0.6:
        return OpeningType.OPEN_DRIVE
    if bar_1_high <= open_price and close_10 < open_price - range_10 * 0.6:
        return OpeningType.OPEN_DRIVE

    bar_1_close = bar_1.get("c", bar_1.get("close", open_price))

    # ORR: Open Rejection Reverse — check BEFORE OTD (stronger signal) (Mind Over Markets p.69)
    if len(bars_first_10min) >= 2:
        bar_2 = bars_first_10min[1]
        bar_2_close = bar_2.get("c", bar_2.get("close", 0))
        if bar_1_close > open_price + range_10 * 0.2 and bar_2_close < open_price:
            return OpeningType.OPEN_REJECTION_REVERSE
        if bar_1_close < open_price - range_10 * 0.2 and bar_2_close > open_price:
            return OpeningType.OPEN_REJECTION_REVERSE

    # OTD: Open Test Drive — brief test opposite then drive (Mind Over Markets p.67)
    if bar_1_close < open_price - range_10 * 0.15 and close_10 > open_price:
        return OpeningType.OPEN_TEST_DRIVE
    if bar_1_close > open_price + range_10 * 0.15 and close_10 < open_price:
        return OpeningType.OPEN_TEST_DRIVE

    # OA: Open Auction — balanced (Mind Over Markets p.71)
    # Split into IN (inside prev day range) vs OUT (outside) per Zohar Figure 4-6
    if prev_day_high is not None and prev_day_low is not None:
        if prev_day_low <= open_price <= prev_day_high:
            return OpeningType.OPEN_AUCTION_IN
        else:
            return OpeningType.OPEN_AUCTION_OUT
    return OpeningType.OPEN_AUCTION_OUT  # fallback if no prev day data
