"""ATR utilities — source-of-truth from ingested DB bars.

Two flavours:
  - atr_5min(period=14)  : Wilder's ATR-14 from v9_bars_5min (intraday volatility)
  - atr_daily(period=14) : Wilder's ATR-14 from daily OHLC aggregated from v9_bars_5min

Both return None when fewer than `period` bars are available — callers
MUST fall back to absolute thresholds when ATR is None (Rule 1: honest
failure > synthetic value).

Period/timeframe/source documented per E2E 2/2 §2.
"""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def _wilder_atr(bars: List[dict], period: int = 14) -> Optional[float]:
    """Wilder's smoothed ATR over ordered bar dicts with keys h, l, c.

    Returns None if len(bars) < period.
    """
    if len(bars) < period:
        return None

    trs: list[float] = []
    for i, bar in enumerate(bars):
        h = bar.get("h", bar.get("high", 0.0))
        l = bar.get("l", bar.get("low", 0.0))
        bar_range = h - l
        if i > 0:
            prev_c = bars[i - 1].get("c", bars[i - 1].get("close", 0.0))
            tr = max(bar_range, abs(h - prev_c), abs(l - prev_c))
        else:
            tr = bar_range
        trs.append(tr)

    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period

    return float(atr)


def atr_5min(bars_5min: List[dict], period: int = 14) -> Optional[float]:
    """ATR-14 from 5-minute bars (intraday volatility measure).

    Args:
        bars_5min: ordered list of 5-min bar dicts [{h, l, c, ...}, ...]
                   from v9_bars_5min, oldest first.
        period: ATR period (default 14 = 70 minutes of 5-min bars).

    Returns:
        Wilder's ATR as float, or None if < period bars.
    """
    return _wilder_atr(bars_5min, period)


def atr_daily(daily_bars: List[dict], period: int = 14) -> Optional[float]:
    """ATR-14 from daily OHLC bars.

    Args:
        daily_bars: ordered list of daily bar dicts [{h, l, c, ...}, ...],
                    oldest first. These are session-level aggregates
                    (one row per trading day).
        period: ATR period (default 14 = 14 trading days).

    Returns:
        Wilder's ATR as float, or None if < period bars.
    """
    return _wilder_atr(daily_bars, period)


# ---------------------------------------------------------------------------
# Feature flags — all default OFF (E2E 2/2 §3)
# ---------------------------------------------------------------------------
import os

S2_ATR_RELATIVE = os.environ.get("S2_ATR_RELATIVE", "").lower() in ("1", "true", "yes")
S3_RELATIVE = os.environ.get("S3_RELATIVE", "").lower() in ("1", "true", "yes")
S1_CVD_OPENING = os.environ.get("S1_CVD_OPENING", "").lower() in ("1", "true", "yes")
S1_DAYTYPE_STAGING = os.environ.get("S1_DAYTYPE_STAGING", "").lower() in ("1", "true", "yes")
S1_IB_WIDTH_ATR = os.environ.get("S1_IB_WIDTH_ATR", "").lower() in ("1", "true", "yes")
S1_DYNAMIC_RECLASS = os.environ.get("S1_DYNAMIC_RECLASS", "").lower() in ("1", "true", "yes")
S4_EXTREME_TREND_RELABEL = os.environ.get("S4_EXTREME_TREND_RELABEL", "").lower() in ("1", "true", "yes")
S3_MUTE = os.environ.get("S3_MUTE", "").lower() in ("1", "true", "yes")  # D-S3MUTE
FOOTPRINT_DISABLED = os.environ.get("FOOTPRINT_DISABLED", "").lower() in ("1", "true", "yes")  # Full S3 disable
S1_LIVE_RECLASS = os.environ.get("S1_LIVE_RECLASS", "").lower() in ("1", "true", "yes")  # Phase 4: promote shadow→live
S2_VSA_VOLUME = os.environ.get("S2_VSA_VOLUME", "").lower() in ("1", "true", "yes")  # D-RVX: VSA volume gate
