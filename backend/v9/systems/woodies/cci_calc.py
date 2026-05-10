"""CCI and indicator calculations — Python port of v9_woodies_export.h.

Reference: Sierra DLL v9_calc_cci, v9_calc_ema, v9_calc_lsma, etc.
Formula: CCI = (TP - SMA(TP, n)) / (0.015 * MeanDeviation)
"""

from typing import List, Tuple


def typical_price(high: float, low: float, close: float) -> float:
    return (high + low + close) / 3.0


def calc_cci(highs: List[float], lows: List[float], closes: List[float],
             period: int) -> float:
    """Standard CCI calculation matching DLL reference."""
    n = len(closes)
    if n < period:
        return 0.0

    tps = [typical_price(highs[i], lows[i], closes[i])
           for i in range(n - period, n)]
    sma_tp = sum(tps) / period
    tp_current = tps[-1]

    mean_dev = sum(abs(tp - sma_tp) for tp in tps) / period
    if mean_dev < 0.0001:
        return 0.0

    return (tp_current - sma_tp) / (0.015 * mean_dev)


def calc_cci_series(highs: List[float], lows: List[float],
                    closes: List[float], period: int) -> List[float]:
    """Compute CCI for every bar that has enough history."""
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(0.0)
        else:
            result.append(calc_cci(
                highs[:i + 1], lows[:i + 1], closes[:i + 1], period
            ))
    return result


def calc_ema(closes: List[float], period: int) -> float:
    """EMA matching DLL: warmup = period*3, then standard EMA."""
    if not closes:
        return 0.0
    k = 2.0 / (period + 1)
    start = max(0, len(closes) - period * 3)
    ema = closes[start]
    for i in range(start + 1, len(closes)):
        ema = closes[i] * k + ema * (1.0 - k)
    return ema


def calc_ema_series(closes: List[float], period: int) -> List[float]:
    """EMA at every bar."""
    result = []
    for i in range(len(closes)):
        result.append(calc_ema(closes[:i + 1], period))
    return result


def calc_lsma(closes: List[float], period: int) -> float:
    """Least Squares Moving Average matching DLL reference."""
    n = len(closes)
    if n < period:
        return closes[-1] if closes else 0.0

    window = closes[n - period:]
    sum_x = sum_y = sum_xy = sum_x2 = 0.0
    for i in range(period):
        x = float(i)
        y = window[i]
        sum_x += x
        sum_y += y
        sum_xy += x * y
        sum_x2 += x * x

    denom = period * sum_x2 - sum_x * sum_x
    if abs(denom) < 0.0001:
        return closes[-1]
    b = (period * sum_xy - sum_x * sum_y) / denom
    a = (sum_y - b * sum_x) / period
    return a + b * (period - 1)


def calc_sidewinder(cci_current: float, cci_3ago: float) -> float:
    """SWI = CCI(14) - CCI(14)[3 bars ago]."""
    return cci_current - cci_3ago


def calc_chopzone(highs: List[float], lows: List[float],
                  closes: List[float], ema_val: float) -> float:
    """ChopZone: (close - EMA) / ATR * 100."""
    n = len(closes)
    if n < 2:
        return 0.0

    atr_start = max(1, n - 14)
    atr_sum = 0.0
    atr_count = 0
    for i in range(atr_start, n):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        atr_sum += max(tr1, tr2, tr3)
        atr_count += 1

    atr = atr_sum / atr_count if atr_count > 0 else 1.0
    if atr < 0.01:
        atr = 0.01

    return (closes[-1] - ema_val) / atr * 100.0


def calc_trend_state(cci14: float, cci14_prev: float, swi: float) -> str:
    """Trend state matching DLL: BLUE/RED/YELLOW/GRAY."""
    if cci14 > 50 and cci14_prev > 0 and swi > 20:
        return "BLUE"
    if cci14 < -50 and cci14_prev < 0 and swi < -20:
        return "RED"
    if (cci14 > 0 and cci14_prev < 0) or (cci14 < 0 and cci14_prev > 0):
        return "YELLOW"
    return "GRAY"


def calc_predictor(cci_current: float, cci_prev: float) -> float:
    """Linear extrapolation: next = current + (current - prev)."""
    return cci_current + (cci_current - cci_prev)


def compute_all_studies(
    highs: List[float], lows: List[float], closes: List[float],
) -> dict:
    """Compute all 11 Woodies studies for the latest bar.

    Returns dict with all study values matching DLL JSON field names.
    """
    n = len(closes)
    if n < 14:
        return {
            "cci_14": 0, "cci_6_tcci": 0, "ema_34": 0, "lsma_value": 0,
            "lsma_above_price": False, "swi_value": 0, "czi_value": 0,
            "trend_state": "GRAY", "predictor_next_cci": 0,
        }

    cci14 = calc_cci(highs, lows, closes, 14)
    cci6 = calc_cci(highs, lows, closes, 6)
    ema34 = calc_ema(closes, 34)
    lsma25 = calc_lsma(closes, 25)
    cci14_prev = calc_cci(highs[:-1], lows[:-1], closes[:-1], 14) if n > 14 else 0.0
    cci14_3ago = calc_cci(highs[:-3], lows[:-3], closes[:-3], 14) if n > 16 else 0.0
    swi = calc_sidewinder(cci14, cci14_3ago)
    czi = calc_chopzone(highs, lows, closes, ema34)
    trend = calc_trend_state(cci14, cci14_prev, swi)
    predictor = calc_predictor(cci14, cci14_prev)

    return {
        "cci_14": round(cci14, 2),
        "cci_6_tcci": round(cci6, 2),
        "ema_34": round(ema34, 2),
        "lsma_value": round(lsma25, 2),
        "lsma_above_price": lsma25 > closes[-1],
        "swi_value": round(swi, 2),
        "czi_value": round(czi, 2),
        "trend_state": trend,
        "predictor_next_cci": round(predictor, 2),
    }
