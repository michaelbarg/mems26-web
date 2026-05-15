"""Open Type Classification — 4 types per Steidlmayer/Dalton (D-072).

Trigger: at 10:00 ET (full 30-min window from RTH open).
Types: Open Drive / Open Test Drive / Open Auction / Open In Range.
"""
import logging
from datetime import time
from typing import Dict, List, Optional
from backend.v9.services.market_clock import now_et, now_utc, ET

logger = logging.getLogger(__name__)

TRIGGER_TIME = time(10, 0)  # D-072: 10:00 ET


def classify_open_type(
    bars_30min: List[Dict],
    open_price: float,
    prev_vah: Optional[float] = None,
    prev_val: Optional[float] = None,
) -> Dict:
    """Classify the open from first 30 min of RTH bars.

    Args:
        bars_30min: 6 five-min bars (09:30-10:00 ET), each with o/h/l/c keys
        open_price: first trade at 09:30 ET
        prev_vah/val: previous day value area (from /tpo/previous_day)

    Returns:
        { type, confidence, reasoning, ts_utc }
    """
    if not bars_30min or len(bars_30min) < 2:
        return {"type": None, "confidence": 0, "reasoning": ["Insufficient bars"], "ts_utc": now_utc().isoformat()}

    high_30 = max(b.get("h", b.get("high", 0)) for b in bars_30min)
    low_30 = min(b.get("l", b.get("low", float("inf"))) for b in bars_30min)
    range_30 = high_30 - low_30
    close_30 = bars_30min[-1].get("c", bars_30min[-1].get("close", open_price))

    # Open In Range: open inside prev day VA + narrow range
    if prev_vah and prev_val:
        if prev_val <= open_price <= prev_vah:
            va_width = prev_vah - prev_val
            if va_width > 0 and range_30 < va_width * 0.5:
                return {
                    "type": "Open In Range",
                    "confidence": 0.85,
                    "reasoning": [
                        f"Open ({open_price:.2f}) inside prev VA ({prev_val:.2f}-{prev_vah:.2f})",
                        f"30-min range ({range_30:.2f}) < half prev VA width ({va_width:.2f})",
                        "No directional commitment",
                        "Likely consolidation day",
                    ],
                    "ts_utc": now_utc().isoformat(),
                }

    # Open Drive: first 2 bars never trade back through open
    first_2 = bars_30min[:2]
    if all(b.get("l", b.get("low", 0)) >= open_price for b in first_2):
        if close_30 > open_price + range_30 * 0.6:
            return {
                "type": "Open Drive",
                "confidence": 0.85,
                "reasoning": [
                    f"Open ({open_price:.2f}) never retested in first 10 min",
                    f"30-min close ({close_30:.2f}) well above open",
                    "Strong directional commitment UP",
                    "Large early range indicates participation",
                ],
                "ts_utc": now_utc().isoformat(),
            }
    if all(b.get("h", b.get("high", float("inf"))) <= open_price for b in first_2):
        if close_30 < open_price - range_30 * 0.6:
            return {
                "type": "Open Drive",
                "confidence": 0.85,
                "reasoning": [
                    f"Open ({open_price:.2f}) never retested up in first 10 min",
                    f"30-min close ({close_30:.2f}) well below open",
                    "Strong directional commitment DOWN",
                ],
                "ts_utc": now_utc().isoformat(),
            }

    # Open Test Drive: first bar opposite, then reversal
    bar_1 = bars_30min[0]
    bar_1_close = bar_1.get("c", bar_1.get("close", open_price))
    if bar_1_close < open_price - range_30 * 0.15 and close_30 > open_price:
        return {
            "type": "Open Test Drive",
            "confidence": 0.75,
            "reasoning": [
                "First 5-min tested below open",
                f"30-min closed above open ({close_30:.2f} > {open_price:.2f})",
                "Two-phase: test then commitment UP",
                "Responsive buyers absorbed initial selling",
            ],
            "ts_utc": now_utc().isoformat(),
        }
    if bar_1_close > open_price + range_30 * 0.15 and close_30 < open_price:
        return {
            "type": "Open Test Drive",
            "confidence": 0.75,
            "reasoning": [
                "First 5-min tested above open",
                f"30-min closed below open ({close_30:.2f} < {open_price:.2f})",
                "Two-phase: test then commitment DOWN",
            ],
            "ts_utc": now_utc().isoformat(),
        }

    # Default: Open Auction
    return {
        "type": "Open Auction",
        "confidence": 0.7,
        "reasoning": [
            "No directional drive detected",
            "No clear test+reverse pattern",
            f"Balanced trade: range {range_30:.2f}, close {close_30:.2f} near open {open_price:.2f}",
            "Two-way participation in first 30 min",
        ],
        "ts_utc": now_utc().isoformat(),
    }
