"""CCI (Commodity Channel Index) computation — bar-dict interface.

Wraps existing cci_calc.py for use with BarRouter bar dicts.
Formula: CCI = (TP - SMA(TP, n)) / (0.015 * Mean Deviation)
"""
from typing import List, Optional


def typical_price(bar: dict) -> float:
    h = bar.get("high", bar.get("h", 0))
    l = bar.get("low", bar.get("l", 0))
    c = bar.get("close", bar.get("c", 0))
    return (h + l + c) / 3.0


def cci(bars: List[dict], period: int = 14) -> Optional[float]:
    if len(bars) < period:
        return None
    relevant = bars[-period:]
    tps = [typical_price(b) for b in relevant]
    sma = sum(tps) / period
    mean_dev = sum(abs(tp - sma) for tp in tps) / period
    if mean_dev == 0:
        return 0.0
    current_tp = tps[-1]
    return (current_tp - sma) / (0.015 * mean_dev)
