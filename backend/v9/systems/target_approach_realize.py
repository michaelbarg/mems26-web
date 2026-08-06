"""S6_TARGET_APPROACH_REALIZE_V1 — discretionary realization near target.

When price reaches within APPROACH_DIST_PTS (default 1.0) of the pending
target (T1/T2/T3), doesn't fill within MAX_APPROACH_BARS (default 2), and
shows a rejection signature, realize remaining contracts via FLATTEN
(never op=EXIT — per CLAUDE.md).

Rejection signatures (any one is sufficient):
  1. Bar closes AWAY from the target (back toward entry)
  2. CCI reversal: cci_14 crosses zero or reverses sign vs previous bar
  3. Delta flip: cumulative delta direction reverses

Case study: trade #633 (2026-08-05) — price reached target area, didn't
break through, reversed → ~$86 potential profit lost.

Flag-OFF by default. Build → replay 15.07-05.08 → Michael rules.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

APPROACH_DIST_PTS = float(os.environ.get("S6_APPROACH_DIST_PTS", "1.0") or 1.0)
MAX_APPROACH_BARS = int(os.environ.get("S6_MAX_APPROACH_BARS", "2") or 2)


@dataclass
class ApproachState:
    """Tracks how long price has been near a target without filling."""
    target_field: str         # "t1", "t2", or "t3"
    target_price: float
    bars_near: int = 0        # consecutive bars within approach distance
    high_water: float = 0.0   # closest approach in points
    triggered: bool = False   # already triggered realize for this target


def should_realize(
    *,
    trade: Dict[str, Any],
    bar_high: float,
    bar_low: float,
    bar_close: float,
    approach_state: Optional[ApproachState] = None,
    cci_current: Optional[float] = None,
    cci_previous: Optional[float] = None,
    delta_direction: Optional[str] = None,
    delta_direction_prev: Optional[str] = None,
    extremes: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str], Optional[ApproachState]]:
    """Check if a target-approach-realize condition is met.

    Returns (should_realize, reason, updated_state).
    Pure function — never writes to DB or Sierra.
    """
    if os.getenv("S6_TARGET_APPROACH_REALIZE_V1", "0").lower() not in ("1", "true", "yes"):
        return False, None, approach_state

    direction = str(trade.get("direction", "")).upper()
    entry = trade.get("entry_price")
    if not entry or direction not in ("LONG", "SHORT"):
        return False, None, approach_state

    # Find the pending (unfilled) target
    t1_hit = trade.get("t1_hit_ts") is not None or trade.get("t1_hit")
    t2_hit = trade.get("t2_hit_ts") is not None or trade.get("t2_hit")

    if not t1_hit and trade.get("t1"):
        tgt_field, tgt_price = "t1", float(trade["t1"])
    elif t1_hit and not t2_hit and trade.get("t2"):
        tgt_field, tgt_price = "t2", float(trade["t2"])
    elif t1_hit and t2_hit and trade.get("t3"):
        tgt_field, tgt_price = "t3", float(trade["t3"])
    else:
        return False, None, approach_state

    # Check proximity: is price within APPROACH_DIST_PTS of the target?
    if direction == "LONG":
        closest = bar_high
        near = (tgt_price - closest) <= APPROACH_DIST_PTS and closest < tgt_price
    else:
        closest = bar_low
        near = (closest - tgt_price) <= APPROACH_DIST_PTS and closest > tgt_price

    # Initialize or update approach state
    if approach_state is None or approach_state.target_field != tgt_field:
        approach_state = ApproachState(
            target_field=tgt_field, target_price=tgt_price,
        )

    if approach_state.triggered:
        return False, None, approach_state

    if near:
        approach_state.bars_near += 1
        dist = abs(closest - tgt_price)
        if approach_state.high_water == 0.0 or dist < approach_state.high_water:
            approach_state.high_water = dist
    else:
        # Reset if price moved away
        if approach_state.bars_near > 0:
            approach_state.bars_near = 0
        return False, None, approach_state

    # ── EXTREMES_AWARE_REALIZE_V1: EXCESS boost (before K-bar gate) ──
    # On an EXCESS extreme, realize after just 1 bar near (no K-bar wait).
    # On a POOR extreme, suppress realize entirely (magnet — target will fill).
    _extremes_aware = os.getenv("EXTREMES_AWARE_REALIZE_V1", "0").lower() in ("1", "true", "yes")
    _extreme_quality = None
    if _extremes_aware and isinstance(extremes, dict):
        if direction == "LONG":
            _extreme_quality = extremes.get("high_quality")
        else:
            _extreme_quality = extremes.get("low_quality")

        if _extreme_quality == "POOR":
            return False, None, approach_state

        if _extreme_quality == "EXCESS" and near and approach_state.bars_near >= 1:
            approach_state.triggered = True
            reason = (
                f"{tgt_field} EXCESS-realize: {approach_state.bars_near} bars within "
                f"{approach_state.high_water:.2f}pt of {tgt_price:.2f}, "
                f"EXCESS extreme (protected — auction complete)"
            )
            return True, reason, approach_state

    # Need at least MAX_APPROACH_BARS near without fill
    if approach_state.bars_near < MAX_APPROACH_BARS:
        return False, None, approach_state

    # Check rejection signatures
    rejections = []

    # 1. Bar closes away from target (back toward entry)
    if direction == "LONG" and bar_close < tgt_price - APPROACH_DIST_PTS:
        rejections.append("close_away")
    elif direction == "SHORT" and bar_close > tgt_price + APPROACH_DIST_PTS:
        rejections.append("close_away")

    # 2. CCI reversal (crosses zero or sign change)
    if cci_current is not None and cci_previous is not None:
        if (cci_current > 0 and cci_previous < 0) or (cci_current < 0 and cci_previous > 0):
            rejections.append("cci_reversal")
        # CCI turning away from extreme
        if direction == "LONG" and cci_current < cci_previous and cci_previous > 50:
            rejections.append("cci_turning")
        elif direction == "SHORT" and cci_current > cci_previous and cci_previous < -50:
            rejections.append("cci_turning")

    # 3. Delta direction flip
    if delta_direction and delta_direction_prev:
        expected = "UP" if direction == "LONG" else "DOWN"
        if delta_direction_prev == expected and delta_direction != expected:
            rejections.append("delta_flip")

    if not rejections:
        return False, None, approach_state

    approach_state.triggered = True
    reason = (
        f"{tgt_field} approach-realize: {approach_state.bars_near} bars within "
        f"{approach_state.high_water:.2f}pt of {tgt_price:.2f}, rejection: "
        f"{'+'.join(rejections)}"
    )
    if _extremes_aware and _extreme_quality:
        reason += f" [extreme={_extreme_quality}]"
    return True, reason, approach_state


def replay_on_trades(trades_with_bars: List[Dict]) -> List[Dict]:
    """Replay the target-approach-realize rule on historical trades.

    Each entry in trades_with_bars should have:
      - trade: {direction, entry_price, t1, t2, t3, t1_hit_ts, t2_hit_ts, ...}
      - bars: [{high, low, close, cci_14, ...}] — bars from entry to exit
      - actual_pnl: the real P&L

    Returns list of dicts with replay results.
    """
    # Force the flag ON for replay
    _orig = os.environ.get("S6_TARGET_APPROACH_REALIZE_V1")
    os.environ["S6_TARGET_APPROACH_REALIZE_V1"] = "1"

    results = []
    try:
        for item in trades_with_bars:
            trade = item["trade"]
            bars = item["bars"]
            actual_pnl = item.get("actual_pnl", 0)

            state = None
            realized = False
            realize_bar_idx = None
            realize_price = None
            realize_reason = None

            for i, bar in enumerate(bars):
                should, reason, state = should_realize(
                    trade=trade,
                    bar_high=float(bar.get("high", bar.get("h", 0))),
                    bar_low=float(bar.get("low", bar.get("l", 0))),
                    bar_close=float(bar.get("close", bar.get("c", 0))),
                    approach_state=state,
                    cci_current=bar.get("cci_14"),
                    cci_previous=bars[i-1].get("cci_14") if i > 0 else None,
                    delta_direction=bar.get("delta_direction"),
                    delta_direction_prev=bars[i-1].get("delta_direction") if i > 0 else None,
                )
                if should:
                    realized = True
                    realize_bar_idx = i
                    realize_price = float(bar["close"])
                    realize_reason = reason
                    break

            # Compute counterfactual P&L
            entry = float(trade.get("entry_price", 0))
            direction = trade.get("direction", "LONG")
            if realized and realize_price:
                if direction == "LONG":
                    realize_pnl = (realize_price - entry) * 5.0  # $5/pt MES
                else:
                    realize_pnl = (entry - realize_price) * 5.0
            else:
                realize_pnl = actual_pnl

            results.append({
                "trade_id": trade.get("id"),
                "direction": direction,
                "entry": entry,
                "actual_pnl": actual_pnl,
                "realized": realized,
                "realize_bar": realize_bar_idx,
                "realize_price": realize_price,
                "realize_pnl": round(realize_pnl, 2),
                "delta_pnl": round(realize_pnl - actual_pnl, 2),
                "reason": realize_reason,
            })
    finally:
        if _orig is None:
            os.environ.pop("S6_TARGET_APPROACH_REALIZE_V1", None)
        else:
            os.environ["S6_TARGET_APPROACH_REALIZE_V1"] = _orig

    return results
