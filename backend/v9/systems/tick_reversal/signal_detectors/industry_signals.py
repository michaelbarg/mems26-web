"""Industry 5 signals for tick_reversal observer.

Per spec Section 6 Step 6 — standard order-flow metrics:
1. Imbalance 250%+ (bid/ask dominance at price level)
2. Stacked imbalance (3+ consecutive levels)
3. Cumulative delta direction
4. Exhaustion at extreme (caution flag)
5. Liquidity sweep + return (stop hunt)

Each returns a dict with {active: bool, direction: str, weight: int, metadata: dict}.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from ..schemas import BarInput


def detect_imbalance_250(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Industry Signal 1: Imbalance 250%+ at any price level.

    Bid or Ask volume dominates by 250% at a footprint level.
    """
    cfg = config or {}
    threshold = cfg.get("imbalance_ratio", 250)

    imbalance_levels = []

    if bar.footprint and isinstance(bar.footprint, dict):
        levels = bar.footprint.get("levels", [])
        for level in levels:
            if isinstance(level, dict):
                bid = level.get("bid", 0)
                ask = level.get("ask", 0)
                if bid > 0 and ask > 0:
                    ratio_pct = max(ask / bid, bid / ask) * 100
                    if ratio_pct >= threshold:
                        direction = "LONG" if ask > bid else "SHORT"
                        imbalance_levels.append({
                            "price": level.get("price"),
                            "ratio_pct": round(ratio_pct, 0),
                            "direction": direction,
                        })

    # Bar-level check
    if not imbalance_levels and bar.ask_vol > 0 and bar.bid_vol > 0:
        ratio_pct = max(bar.ask_vol / bar.bid_vol, bar.bid_vol / bar.ask_vol) * 100
        if ratio_pct >= threshold:
            direction = "LONG" if bar.ask_vol > bar.bid_vol else "SHORT"
            imbalance_levels.append({"ratio_pct": round(ratio_pct, 0), "direction": direction})

    active = len(imbalance_levels) > 0
    direction = imbalance_levels[0]["direction"] if active else None

    return {
        "active": active,
        "direction": direction,
        "weight": 1,
        "signal_id": "imbalance_250",
        "metadata": {"imbalance_count": len(imbalance_levels), "levels": imbalance_levels[:3]},
    }


def detect_stacked_imbalance(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Industry Signal 2: Stacked imbalance (3+ consecutive levels).

    Strong directional conviction signal. Weight = +2 in confluence.
    """
    cfg = config or {}
    threshold = cfg.get("imbalance_ratio", 250)
    min_stacked = cfg.get("stacked_imbalance_count", 3)

    max_buy_streak = 0
    max_sell_streak = 0

    if bar.footprint and isinstance(bar.footprint, dict):
        levels = bar.footprint.get("levels", [])
        buy_streak = 0
        sell_streak = 0

        for level in levels:
            if not isinstance(level, dict):
                continue
            bid = level.get("bid", 0)
            ask = level.get("ask", 0)

            if bid > 0 and ask > 0:
                if (ask / bid) * 100 >= threshold:
                    buy_streak += 1
                    sell_streak = 0
                elif (bid / ask) * 100 >= threshold:
                    sell_streak += 1
                    buy_streak = 0
                else:
                    max_buy_streak = max(max_buy_streak, buy_streak)
                    max_sell_streak = max(max_sell_streak, sell_streak)
                    buy_streak = 0
                    sell_streak = 0
            else:
                max_buy_streak = max(max_buy_streak, buy_streak)
                max_sell_streak = max(max_sell_streak, sell_streak)
                buy_streak = 0
                sell_streak = 0

        max_buy_streak = max(max_buy_streak, buy_streak)
        max_sell_streak = max(max_sell_streak, sell_streak)

    elif bar.cluster and isinstance(bar.cluster, dict):
        max_buy_streak = bar.cluster.get("stacked_buy", 0) or 0
        max_sell_streak = bar.cluster.get("stacked_sell", 0) or 0

    active = max_buy_streak >= min_stacked or max_sell_streak >= min_stacked
    direction = None
    if max_buy_streak >= min_stacked:
        direction = "LONG"
    elif max_sell_streak >= min_stacked:
        direction = "SHORT"

    return {
        "active": active,
        "direction": direction,
        "weight": 2,  # +2 booster per spec
        "signal_id": "stacked_imbalance",
        "metadata": {"buy_streak": max_buy_streak, "sell_streak": max_sell_streak},
    }


def detect_cumulative_delta(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Industry Signal 3: Cumulative delta direction aligned with bar.

    LONG bar + positive delta = aligned.
    SHORT bar + negative delta = aligned.
    """
    delta = bar.delta
    if delta is None:
        delta = bar.ask_vol - bar.bid_vol

    is_up = bar.c > bar.o

    if is_up:
        active = delta > 0
        direction = "LONG"
    else:
        active = delta < 0
        direction = "SHORT"

    return {
        "active": active,
        "direction": direction if active else None,
        "weight": 1,
        "signal_id": "cumulative_delta",
        "metadata": {"delta": delta, "bar_direction": "UP" if is_up else "DOWN", "aligned": active},
    }


def detect_exhaustion(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Industry Signal 4: Exhaustion at extreme.

    High volume + small body at recent extreme = exhaustion.
    This is a CAUTION signal (penalty in confluence: -1).
    """
    if len(bars) < 3:
        return {"active": False, "direction": None, "weight": -1, "signal_id": "exhaustion"}

    bar_range = bar.h - bar.l
    if bar_range <= 0:
        return {"active": False, "direction": None, "weight": -1, "signal_id": "exhaustion"}

    body = abs(bar.c - bar.o)
    body_pct = body / bar_range

    lookback = bars[-4:-1] if len(bars) >= 4 else bars[:-1]
    avg_vol = sum(b.vol for b in lookback) / len(lookback) if lookback else bar.vol
    if avg_vol <= 0:
        return {"active": False, "direction": None, "weight": -1, "signal_id": "exhaustion"}

    high_volume = bar.vol > avg_vol * 1.5
    small_body = body_pct < 0.3

    window = bars[-6:] if len(bars) >= 6 else bars
    recent_high = max(b.h for b in window)
    recent_low = min(b.l for b in window)

    at_high = bar.h >= recent_high
    at_low = bar.l <= recent_low

    active = high_volume and small_body and (at_high or at_low)

    direction = None
    if active:
        direction = "SHORT" if at_high else "LONG"

    return {
        "active": active,
        "direction": direction,
        "weight": -1,  # penalty per spec
        "signal_id": "exhaustion",
        "metadata": {
            "vol_ratio": round(bar.vol / avg_vol, 2) if avg_vol > 0 else 0,
            "body_pct": round(body_pct, 2),
            "at_high": at_high,
            "at_low": at_low,
        },
    }


def detect_liquidity_sweep(
    bar: BarInput,
    bars: List[BarInput],
    config: Optional[dict] = None,
) -> Dict:
    """Industry Signal 5: Liquidity sweep + return.

    Price sweeps beyond prior high/low then closes back inside.
    Classic stop-hunt. Weight = +2 booster per spec.
    """
    if len(bars) < 5:
        return {"active": False, "direction": None, "weight": 2, "signal_id": "liquidity_sweep"}

    lookback = bars[-6:-1] if len(bars) >= 6 else bars[:-1]
    prior_high = max(b.h for b in lookback)
    prior_low = min(b.l for b in lookback)

    # Sweep high: wick above prior high, close back below
    if bar.h > prior_high and bar.c < prior_high:
        sweep_distance = bar.h - prior_high
        return {
            "active": True,
            "direction": "SHORT",
            "weight": 2,
            "signal_id": "liquidity_sweep",
            "metadata": {"sweep_type": "high", "sweep_distance": round(sweep_distance, 2),
                         "prior_high": round(prior_high, 2)},
        }

    # Sweep low: wick below prior low, close back above
    if bar.l < prior_low and bar.c > prior_low:
        sweep_distance = prior_low - bar.l
        return {
            "active": True,
            "direction": "LONG",
            "weight": 2,
            "signal_id": "liquidity_sweep",
            "metadata": {"sweep_type": "low", "sweep_distance": round(sweep_distance, 2),
                         "prior_low": round(prior_low, 2)},
        }

    return {"active": False, "direction": None, "weight": 2, "signal_id": "liquidity_sweep"}
