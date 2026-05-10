"""Zohar's 5 signals for tick_reversal observer.

Per spec Section 6 Step 6 — Zohar's proprietary order-flow signals:
1. Belly comparison (buyer vs seller belly volume)
2. 90% volume drop (losing side capitulation)
3. COT vs AMT (close-of-trade vs amount)
4. Tick breach (controlled wick at level)
5. POC migration (POC jumping with trend)

Each returns a dict with {active: bool, direction: str, weight: int, metadata: dict}.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from ..schemas import BarInput


def detect_belly_comparison(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Zohar Signal 1: Compare buy-side vs sell-side belly volume.

    LONG: buyer belly > seller belly x ratio.
    SHORT: inverse.
    """
    cfg = config or {}
    ratio_threshold = cfg.get("belly_dominance_ratio", 1.5)

    ask = bar.ask_vol
    bid = bar.bid_vol

    if ask <= 0 and bid <= 0:
        return {"active": False, "direction": None, "weight": 1, "signal_id": "belly_comparison"}

    if ask <= 0 or bid <= 0:
        direction = "LONG" if ask > bid else "SHORT"
        return {"active": True, "direction": direction, "weight": 1, "signal_id": "belly_comparison",
                "metadata": {"ask_vol": ask, "bid_vol": bid, "ratio": float("inf")}}

    ratio = max(ask / bid, bid / ask)
    if ratio < ratio_threshold:
        return {"active": False, "direction": None, "weight": 1, "signal_id": "belly_comparison"}

    direction = "LONG" if ask > bid else "SHORT"
    return {
        "active": True,
        "direction": direction,
        "weight": 1,
        "signal_id": "belly_comparison",
        "metadata": {"ask_vol": ask, "bid_vol": bid, "ratio": round(ratio, 2)},
    }


def detect_volume_drop_90(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Zohar Signal 2: 90% volume drop on losing side.

    The losing side's volume collapses vs recent average.
    """
    cfg = config or {}
    drop_threshold = cfg.get("volume_drop_pct", 90)

    if len(bars) < 3:
        return {"active": False, "direction": None, "weight": 1, "signal_id": "volume_drop_90"}

    lookback = bars[-4:-1] if len(bars) >= 4 else bars[:-1]
    is_up = bar.c > bar.o
    current_losing = bar.bid_vol if is_up else bar.ask_vol

    losing_vols = []
    for b in lookback:
        b_up = b.c > b.o
        losing_vols.append(b.bid_vol if b_up else b.ask_vol)

    if not losing_vols:
        return {"active": False, "direction": None, "weight": 1, "signal_id": "volume_drop_90"}

    avg_losing = sum(losing_vols) / len(losing_vols)
    if avg_losing <= 0:
        return {"active": False, "direction": None, "weight": 1, "signal_id": "volume_drop_90"}

    drop_pct = ((avg_losing - current_losing) / avg_losing) * 100
    active = drop_pct >= drop_threshold
    direction = "LONG" if is_up else "SHORT"

    return {
        "active": active,
        "direction": direction if active else None,
        "weight": 1,
        "signal_id": "volume_drop_90",
        "metadata": {"drop_pct": round(drop_pct, 1), "avg_losing": round(avg_losing, 0), "current_losing": current_losing},
    }


def detect_cot_vs_amt(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Zohar Signal 3: Close-of-Trade vs Amount.

    Close is on the winning side relative to bar midpoint.
    """
    midpoint = (bar.h + bar.l) / 2
    bar_range = bar.h - bar.l

    if bar_range <= 0:
        return {"active": False, "direction": None, "weight": 1, "signal_id": "cot_vs_amt"}

    is_up = bar.c > bar.o

    if is_up:
        active = bar.c > midpoint
        direction = "LONG"
    else:
        active = bar.c < midpoint
        direction = "SHORT"

    return {
        "active": active,
        "direction": direction if active else None,
        "weight": 1,
        "signal_id": "cot_vs_amt",
        "metadata": {"close": bar.c, "midpoint": round(midpoint, 2), "above_mid": bar.c > midpoint},
    }


def detect_tick_breach(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Zohar Signal 4: Tick breach controlled (4-5 ticks max).

    The non-dominant wick is limited, showing controlled price action.
    """
    bar_range = bar.h - bar.l
    if bar_range <= 0:
        return {"active": False, "direction": None, "weight": 1, "signal_id": "tick_breach"}

    tick = 0.25  # MES tick size
    max_breach_ticks = 5
    is_up = bar.c > bar.o

    if is_up:
        breach_wick = bar.o - bar.l
        direction = "LONG"
    else:
        breach_wick = bar.h - bar.o
        direction = "SHORT"

    breach_ticks = int(breach_wick / tick)
    active = breach_wick <= max_breach_ticks * tick

    return {
        "active": active,
        "direction": direction if active else None,
        "weight": 1,
        "signal_id": "tick_breach",
        "metadata": {"breach_ticks": breach_ticks, "max_allowed": max_breach_ticks},
    }


def detect_poc_migration(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Zohar Signal 5: POC migration (jumping with trend).

    POC must move in trend direction. Stuck POC = bad sign.
    """
    if len(bars) < 3:
        return {"active": False, "direction": None, "weight": 1, "signal_id": "poc_migration"}

    def get_poc(b: BarInput) -> float:
        if b.footprint and isinstance(b.footprint, dict):
            poc = b.footprint.get("poc_price")
            if poc is not None:
                return float(poc)
        if b.ask_vol + b.bid_vol > 0:
            weight = b.ask_vol / (b.ask_vol + b.bid_vol)
            return b.l + (b.h - b.l) * weight
        return (b.h + b.l) / 2

    recent = bars[-3:]
    pocs = [get_poc(b) for b in recent]
    current_poc = get_poc(bar)

    is_up = bar.c > bar.o

    if is_up:
        active = current_poc > pocs[-1] and pocs[-1] >= pocs[-2]
        direction = "LONG"
    else:
        active = current_poc < pocs[-1] and pocs[-1] <= pocs[-2]
        direction = "SHORT"

    return {
        "active": active,
        "direction": direction if active else None,
        "weight": 1,
        "signal_id": "poc_migration",
        "metadata": {"current_poc": round(current_poc, 2), "prev_pocs": [round(p, 2) for p in pocs[-2:]]},
    }
