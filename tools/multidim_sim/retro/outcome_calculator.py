"""
Outcome calculator — walk ticks sequentially to determine trade result.

Single-target (compute_outcome) and multi-target (compute_outcome_multi_target)
variants. Both use exact temporal ordering (stop wins ties = conservative).
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# MES minimum tick = 0.25pt
MES_TICK = 0.25
PTS_TO_USD = 5.0  # $5 per point for MES


def compute_outcome(
    ticks: List[dict],
    entry_ts: datetime,
    entry_price: float,
    stop_price: float,
    c1_target: float,
    direction: str,
    timeout_minutes: int = 60,
) -> Dict:
    """
    Walk ticks sequentially from entry. Return first outcome reached.

    For LONG:
      HIT_C1  if any tick high >= c1_target
      HIT_STOP if any tick low <= stop_price
      If both in same tick: HIT_STOP (conservative)

    For SHORT:
      HIT_C1  if any tick low <= c1_target
      HIT_STOP if any tick high >= stop_price

    Tracks MAE (worst adverse excursion) and MFE (best favorable)
    throughout the walk.

    Returns dict with: outcome, closed_ts, t1_hit_ts, stop_hit_ts,
                       mae_pts, mfe_pts, pnl_pts, duration_seconds,
                       n_ticks_walked
    """
    if direction not in ("LONG", "SHORT"):
        raise ValueError(f"Invalid direction: {direction}")

    # Ensure timezone-aware
    if entry_ts.tzinfo is None:
        entry_ts = entry_ts.replace(tzinfo=timezone.utc)

    timeout_dt = entry_ts + timedelta(minutes=timeout_minutes)
    mae = 0.0
    mfe = 0.0
    n_walked = 0

    for tick in ticks:
        tick_ts = tick["ts"]
        if tick_ts.tzinfo is None:
            tick_ts = tick_ts.replace(tzinfo=timezone.utc)

        if tick_ts > timeout_dt:
            break

        n_walked += 1
        h = tick["high"]
        l = tick["low"]

        if direction == "LONG":
            adverse = entry_price - l
            favorable = h - entry_price
            stop_hit = l <= stop_price
            target_hit = h >= c1_target
        else:  # SHORT
            adverse = h - entry_price
            favorable = entry_price - l
            stop_hit = h >= stop_price
            target_hit = l <= c1_target

        mae = max(mae, adverse)
        mfe = max(mfe, favorable)

        # Stop wins ties (conservative)
        if stop_hit:
            return {
                "outcome": "HIT_STOP",
                "closed_ts": tick_ts,
                "t1_hit_ts": None,
                "stop_hit_ts": tick_ts,
                "mae_pts": round(mae, 2),
                "mfe_pts": round(mfe, 2),
                "pnl_pts": -abs(entry_price - stop_price),
                "duration_seconds": int((tick_ts - entry_ts).total_seconds()),
                "n_ticks_walked": n_walked,
            }

        if target_hit:
            return {
                "outcome": "HIT_C1",
                "closed_ts": tick_ts,
                "t1_hit_ts": tick_ts,
                "stop_hit_ts": None,
                "mae_pts": round(mae, 2),
                "mfe_pts": round(mfe, 2),
                "pnl_pts": abs(c1_target - entry_price),
                "duration_seconds": int((tick_ts - entry_ts).total_seconds()),
                "n_ticks_walked": n_walked,
            }

    # Timeout
    return {
        "outcome": "TIMEOUT",
        "closed_ts": timeout_dt,
        "t1_hit_ts": None,
        "stop_hit_ts": None,
        "mae_pts": round(mae, 2),
        "mfe_pts": round(mfe, 2),
        "pnl_pts": 0.0,
        "duration_seconds": timeout_minutes * 60,
        "n_ticks_walked": n_walked,
    }


def compute_outcome_multi_target(
    ticks: List[dict],
    entry_ts: datetime,
    entry_price: float,
    stop_price: float,
    c1_target: float,
    c2_target: float,
    c3_target: Optional[float] = None,
    c3_enabled: bool = False,
    direction: str = "LONG",
    timeout_minutes: int = 60,
) -> Dict:
    """
    Simulate 3-contract bracket order with BE move after C1.

    Contracts: C1 (1R), C2 (~2-3R), C3 (runner, optional).
    After C1 fills, stop moves to breakeven (entry_price).
    After timeout, remaining contracts close at last traded price.
    If c3_target is None but c3_enabled, C3 exits at timeout or stop.

    Returns dict with per-contract PnL and aggregate totals.
    """
    if direction not in ("LONG", "SHORT"):
        raise ValueError(f"Invalid direction: {direction}")

    if entry_ts.tzinfo is None:
        entry_ts = entry_ts.replace(tzinfo=timezone.utc)

    timeout_dt = entry_ts + timedelta(minutes=timeout_minutes)
    has_c3 = c3_enabled and c3_target is not None

    # State
    current_stop = stop_price
    c1_filled = False
    c2_filled = False
    c3_filled = False
    t1_ts = t2_ts = t3_ts = stop_ts = None
    c1_pnl = c2_pnl = c3_pnl = 0.0
    mae = mfe = 0.0
    last_price = entry_price
    n_walked = 0
    closed_ts = timeout_dt  # default

    # How many contracts are active
    n_contracts = 3 if c3_enabled else 2

    for tick in ticks:
        tick_ts = tick["ts"]
        if tick_ts.tzinfo is None:
            tick_ts = tick_ts.replace(tzinfo=timezone.utc)
        if tick_ts > timeout_dt:
            break

        n_walked += 1
        h, l, c = tick["high"], tick["low"], tick["close"]
        last_price = c

        if direction == "LONG":
            mae = max(mae, entry_price - l)
            mfe = max(mfe, h - entry_price)
            _stop_hit = l <= current_stop
            _c1_hit = h >= c1_target
            _c2_hit = h >= c2_target
            _c3_hit = has_c3 and h >= c3_target
        else:
            mae = max(mae, h - entry_price)
            mfe = max(mfe, entry_price - l)
            _stop_hit = h >= current_stop
            _c1_hit = l <= c1_target
            _c2_hit = l <= c2_target
            _c3_hit = has_c3 and l <= c3_target

        # STOP checked first (conservative)
        if _stop_hit:
            stop_ts = tick_ts
            closed_ts = tick_ts
            # PnL for remaining contracts at current_stop
            if direction == "LONG":
                stop_pnl = current_stop - entry_price
            else:
                stop_pnl = entry_price - current_stop
            if not c1_filled:
                c1_pnl = stop_pnl
            if not c2_filled:
                c2_pnl = stop_pnl
            if c3_enabled and not c3_filled:
                c3_pnl = stop_pnl
            break

        # C1 — NO stop change; original stop stays for C2/C3
        if not c1_filled and _c1_hit:
            c1_filled = True
            t1_ts = tick_ts
            c1_pnl = abs(c1_target - entry_price)

        # C2 — AFTER C2 fills, move stop to BE for remaining C3
        if c1_filled and not c2_filled and _c2_hit:
            c2_filled = True
            t2_ts = tick_ts
            c2_pnl = abs(c2_target - entry_price)
            current_stop = entry_price  # BE after C2

        # C3
        if has_c3 and c2_filled and not c3_filled and _c3_hit:
            c3_filled = True
            t3_ts = tick_ts
            c3_pnl = abs(c3_target - entry_price)

        # All done?
        all_filled = c1_filled and c2_filled and (not c3_enabled or c3_filled)
        if all_filled:
            closed_ts = tick_ts
            break
    else:
        # Timeout — close remaining contracts at last price
        closed_ts = timeout_dt
        if direction == "LONG":
            timeout_pnl = last_price - entry_price
        else:
            timeout_pnl = entry_price - last_price

        if c2_filled:
            # C2 hit → stop is at BE for C3 → can't lose more than 0
            if c3_enabled and not c3_filled:
                c3_pnl = max(0.0, timeout_pnl)
        elif c1_filled:
            # C1 hit but C2 didn't → stop is STILL ORIGINAL
            # Close C2 (and C3) at last price — could be negative
            if not c2_filled:
                c2_pnl = timeout_pnl
            if c3_enabled and not c3_filled:
                c3_pnl = timeout_pnl
        else:
            # Nothing hit — all contracts close at last price
            c1_pnl = timeout_pnl
            c2_pnl = timeout_pnl
            if c3_enabled:
                c3_pnl = timeout_pnl

    # Outcome label
    if has_c3 and c3_filled:
        outcome = "HIT_C3"
    elif c2_filled:
        outcome = "HIT_C2"
    elif c1_filled and stop_ts is not None:
        outcome = "PARTIAL"  # C1 hit, then C2/C3 stopped at original stop
    elif c1_filled:
        outcome = "HIT_C1"
    elif stop_ts is not None:
        outcome = "HIT_STOP"
    else:
        outcome = "TIMEOUT"

    # Total PnL (1 contract per tier)
    total_pnl_pts = c1_pnl + c2_pnl
    if c3_enabled:
        total_pnl_pts += c3_pnl
    total_pnl_usd = total_pnl_pts * PTS_TO_USD

    dur = int((closed_ts - entry_ts).total_seconds()) if closed_ts else timeout_minutes * 60

    return {
        "outcome": outcome,
        "closed_ts": closed_ts,
        "t1_hit_ts": t1_ts,
        "t2_hit_ts": t2_ts,
        "t3_hit_ts": t3_ts,
        "stop_hit_ts": stop_ts,
        "c1_filled": c1_filled,
        "c2_filled": c2_filled,
        "c3_filled": c3_filled,
        "c1_pnl_pts": round(c1_pnl, 2),
        "c2_pnl_pts": round(c2_pnl, 2),
        "c3_pnl_pts": round(c3_pnl, 2),
        "total_pnl_pts": round(total_pnl_pts, 2),
        "total_pnl_usd": round(total_pnl_usd, 2),
        "mae_pts": round(mae, 2),
        "mfe_pts": round(mfe, 2),
        "duration_seconds": dur,
        "n_ticks_walked": n_walked,
    }


def compute_outcome_conservative(
    ticks: List[dict],
    entry_ts: datetime,
    entry_price: float,
    stop_price: float,
    c1_target: float,
    direction: str,
    timeout_minutes: int = 60,
    fill_buffer: float = MES_TICK,
) -> Dict:
    """
    Conservative variant: price must STRICTLY EXCEED target/stop by
    fill_buffer (default 0.25pt = 1 MES tick) to count as filled.

    More realistic for limit orders — touching the price doesn't
    guarantee a fill if the order book is thick at that level.
    """
    if direction not in ("LONG", "SHORT"):
        raise ValueError(f"Invalid direction: {direction}")

    if entry_ts.tzinfo is None:
        entry_ts = entry_ts.replace(tzinfo=timezone.utc)

    timeout_dt = entry_ts + timedelta(minutes=timeout_minutes)
    mae = 0.0
    mfe = 0.0
    n_walked = 0

    for tick in ticks:
        tick_ts = tick["ts"]
        if tick_ts.tzinfo is None:
            tick_ts = tick_ts.replace(tzinfo=timezone.utc)

        if tick_ts > timeout_dt:
            break

        n_walked += 1
        h = tick["high"]
        l = tick["low"]

        if direction == "LONG":
            adverse = entry_price - l
            favorable = h - entry_price
            # Require price to exceed by buffer
            stop_hit = l < stop_price - fill_buffer
            target_hit = h > c1_target + fill_buffer
        else:
            adverse = h - entry_price
            favorable = entry_price - l
            stop_hit = h > stop_price + fill_buffer
            target_hit = l < c1_target - fill_buffer

        mae = max(mae, adverse)
        mfe = max(mfe, favorable)

        if stop_hit:
            return {
                "outcome": "HIT_STOP",
                "closed_ts": tick_ts,
                "t1_hit_ts": None,
                "stop_hit_ts": tick_ts,
                "mae_pts": round(mae, 2),
                "mfe_pts": round(mfe, 2),
                "pnl_pts": -abs(entry_price - stop_price),
                "duration_seconds": int((tick_ts - entry_ts).total_seconds()),
                "n_ticks_walked": n_walked,
            }

        if target_hit:
            return {
                "outcome": "HIT_C1",
                "closed_ts": tick_ts,
                "t1_hit_ts": tick_ts,
                "stop_hit_ts": None,
                "mae_pts": round(mae, 2),
                "mfe_pts": round(mfe, 2),
                "pnl_pts": abs(c1_target - entry_price),
                "duration_seconds": int((tick_ts - entry_ts).total_seconds()),
                "n_ticks_walked": n_walked,
            }

    return {
        "outcome": "TIMEOUT",
        "closed_ts": timeout_dt,
        "t1_hit_ts": None,
        "stop_hit_ts": None,
        "mae_pts": round(mae, 2),
        "mfe_pts": round(mfe, 2),
        "pnl_pts": 0.0,
        "duration_seconds": timeout_minutes * 60,
        "n_ticks_walked": n_walked,
    }
