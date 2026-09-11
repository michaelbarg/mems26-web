#!/usr/bin/env python3
"""T-317 measurement: pre-T1 CEILING_FAILED/FLOOR_FAILED realize-on-confirm.

Reads live/demo trades from v9_trades since 2026-08-28 that have pnl_sierra.
For each trade, re-runs detect_ceiling_floor over the 5-min bars during the
trade's lifetime (oldest first, confirm bar = bar that closed BEFORE exit).
Checks whether CEILING_FAILED (against LONG) or FLOOR_FAILED (against SHORT)
would have fired BEFORE T1 hit, while open_pnl > 0 at that bar.

If so, computes:
  - realize_pnl_usd = (confirm_close - entry) × direction_sign × 5 × contracts
    (i.e. realize at the confirm bar's close)
  - vs actual pnl_sierra

Outputs: n trades affected, Σ$ difference (realize − actual).

DATABASE_URL = postgresql://localhost/mems26
MES: $5/point (0.25 tick = $1.25/tick).
"""
from __future__ import annotations

import sys
import os

# allow running from repo root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import psycopg2
import psycopg2.extras
from typing import Any, Dict, List, Optional, Tuple

DATABASE_URL = "postgresql://localhost/mems26"
MES_POINT_VALUE = 5.0  # $5 per point per contract

# ── minimal config fallback (avoids importing config_loader in isolation) ──
CF_CFG_DEFAULTS: Dict[str, Any] = {
    "tol_atr": 0.25,
    "max_bars_between": 12,
    "min_bars_between": 1,
    "confirm_max_bars": 12,
    "edge_sources": ["VAH", "SESSION_HIGH", "IB_HIGH"],
}


def _load_ceiling_floor_cfg() -> Dict[str, Any]:
    try:
        from backend.v9.config_loader import load_ceiling_floor
        cfg = load_ceiling_floor("baseline")
        return cfg if isinstance(cfg, dict) else CF_CFG_DEFAULTS
    except Exception:
        return CF_CFG_DEFAULTS


def _get_tpo_levels(cur, ts_utc) -> Dict[str, Optional[float]]:
    """Read stored TPO levels (VAH/VAL/IB) from v9_tpo_sessions for ts_utc."""
    try:
        cur.execute(
            "SELECT vah_price, val_price, ib_high, ib_low "
            "FROM v9_tpo_sessions "
            "WHERE trading_date::date <= %s::date "
            "ORDER BY trading_date DESC LIMIT 1",
            (ts_utc,),
        )
        row = cur.fetchone()
        if row is None:
            return {}

        def _f(v):
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        return {
            "vah":     _f(row["vah_price"]),
            "val":     _f(row["val_price"]),
            "ib_high": _f(row["ib_high"]),
            "ib_low":  _f(row["ib_low"]),
        }
    except Exception:
        return {}


def _session_extremes_from_bars(
    bars: List[Dict[str, Any]],
    up_to_index: int,
) -> Tuple[Optional[float], Optional[float]]:
    """Compute running RTH session high/low from bars up to index (inclusive).

    Mirrors five_min_system._maybe_ceiling_floor_state: only bars at or after
    09:30 ET (570 min since midnight) on the LAST bar's ET date.
    """
    import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI

    ET = _ZI("America/New_York")
    if not bars or up_to_index < 0:
        return None, None

    last_bar = bars[min(up_to_index, len(bars) - 1)]
    try:
        last_dt = _dt.datetime.fromtimestamp(
            float(last_bar["ets"]), tz=_dt.timezone.utc
        ).astimezone(ET)
        last_date = last_dt.date()
    except (TypeError, ValueError, KeyError):
        return None, None

    sh: Optional[float] = None
    sl: Optional[float] = None
    for b in bars[: up_to_index + 1]:
        try:
            b_dt = _dt.datetime.fromtimestamp(
                float(b["ets"]), tz=_dt.timezone.utc
            ).astimezone(ET)
        except (TypeError, ValueError):
            continue
        if b_dt.date() != last_date:
            continue
        if b_dt.hour * 60 + b_dt.minute < 570:  # before 09:30 ET
            continue
        bh, bl = float(b["h"]), float(b["l"])
        sh = bh if sh is None else max(sh, bh)
        sl = bl if sl is None else min(sl, bl)

    return sh, sl


def _contracts_from_trade(trade: Dict[str, Any]) -> int:
    """Estimate contract count from quality JSON or fallback to 1."""
    q = trade.get("quality") or {}
    if isinstance(q, str):
        import json as _j
        try:
            q = _j.loads(q)
        except Exception:
            q = {}
    # Count distinct cN_stop_id entries as proxy for live contracts
    n = 0
    for k in ("c1_stop_id", "c2_stop_id", "c3_stop_id", "c4_stop_id", "c5_stop_id"):
        if q.get(k) is not None:
            n += 1
    return max(n, 1)


def _run() -> None:
    from backend.v9.systems.ceiling_floor_state import detect_ceiling_floor
    from backend.v9.shared.atr import atr_5min

    cfg = _load_ceiling_floor_cfg()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. Load qualifying trades
    cur.execute(
        """
        SELECT id, mode, direction, entry_ts, exit_ts, entry_price,
               t1, t1_hit_ts, t2, t2_hit_ts, t3, t3_hit_ts,
               stop, pnl_sierra, quality
        FROM v9_trades
        WHERE pnl_sierra IS NOT NULL
          AND entry_ts >= '2026-08-28'
          AND mode IN ('live', 'demo')
        ORDER BY id
        """
    )
    trades = [dict(r) for r in cur.fetchall()]
    print(f"Loaded {len(trades)} trades with pnl_sierra since 2026-08-28")

    n_affected = 0
    sum_delta = 0.0
    details: List[str] = []

    for trade in trades:
        tid = trade["id"]
        direction = trade["direction"]
        entry_ts = trade["entry_ts"]
        exit_ts = trade["exit_ts"]
        entry_price = float(trade["entry_price"])
        t1_hit_ts = trade["t1_hit_ts"]
        pnl_sierra = float(trade["pnl_sierra"])
        contracts = _contracts_from_trade(trade)

        # direction_sign: LONG profits when price rises
        dir_sign = 1.0 if direction == "LONG" else -1.0

        if exit_ts is None:
            continue  # still open — skip

        # 2. Fetch 5-min bars that were CLOSED before/during the trade
        #    We look from 90 bars before entry (for ATR context) up to exit.
        cur.execute(
            """
            SELECT extract(epoch from ts) AS ets, ts,
                   open o, high h, low l, close c
            FROM v9_bars_5min_woodies
            WHERE ts <= %s
            ORDER BY ts DESC
            LIMIT 120
            """,
            (exit_ts,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        rows.reverse()  # oldest first

        if len(rows) < 3:
            continue

        # 3. Walk bars that closed DURING the trade's lifetime (after entry),
        #    and check detect_ceiling_floor on each, stopping at T1 or exit.
        import datetime as _dt

        # Load TPO levels once for this trade's date (static for the session)
        tpo_levels = _get_tpo_levels(cur, entry_ts)

        signal_found = None
        fired_keys: set = set()

        for i, bar in enumerate(rows):
            bar_ts_epoch = float(bar["ets"])
            bar_close_dt = _dt.datetime.fromtimestamp(bar_ts_epoch,
                                                      tz=_dt.timezone.utc)

            # Only bars that closed after entry
            if bar_close_dt <= entry_ts:
                continue
            # Stop scanning at T1 (if hit) — pre-T1 only
            if t1_hit_ts is not None and bar_close_dt > t1_hit_ts:
                break
            # Don't scan past exit
            if bar_close_dt > exit_ts:
                break

            # Feed bars[0..i] (up to and including this bar) to detector
            window = rows[: i + 1]
            if len(window) < 3:
                continue

            atr_val = atr_5min(window, period=14)
            if atr_val is None:
                continue

            # Session high/low computed from bars up to this point (RTH only)
            sh, sl = _session_extremes_from_bars(rows, i)
            levels: Dict[str, Optional[float]] = dict(tpo_levels)
            levels["session_high"] = sh
            levels["session_low"] = sl

            result = detect_ceiling_floor(
                window, levels, atr_val, cfg,
                already_fired=frozenset(fired_keys),
            )
            if result is None:
                continue

            # Dedup
            key = result.get("key", "")
            if key in fired_keys:
                continue
            fired_keys.add(key)

            state = result["state"]
            confirm_close = result["confirm_close"]

            # Check: is this AGAINST the trade direction?
            against_long = (state == "CEILING_FAILED" and direction == "LONG")
            against_short = (state == "FLOOR_FAILED" and direction == "SHORT")
            if not (against_long or against_short):
                continue

            # open_pnl at this confirm bar's close (1 contract per leg for
            # simplicity; realized at confirm_close rounded to tick)
            tick = 0.25
            if direction == "LONG":
                # realize target = confirm_close rounded DOWN toward entry
                realize_price = round(
                    confirm_close / tick) * tick
                # ensure it's below confirm_close (toward entry)
                if realize_price > confirm_close:
                    realize_price -= tick
            else:
                realize_price = round(confirm_close / tick) * tick
                if realize_price < confirm_close:
                    realize_price += tick

            open_pnl = (realize_price - entry_price) * dir_sign * MES_POINT_VALUE * contracts
            if open_pnl <= 0:
                # Not in profit — don't realize a loss
                continue

            # Found a valid pre-T1 signal
            signal_found = {
                "state": state,
                "confirm_close": confirm_close,
                "realize_price": realize_price,
                "bar_ts": bar_close_dt,
                "open_pnl": open_pnl,
            }
            break  # first signal per trade

        if signal_found is None:
            continue

        # 4. Compute delta
        realize_pnl = signal_found["open_pnl"]
        delta = realize_pnl - pnl_sierra

        n_affected += 1
        sum_delta += delta

        details.append(
            f"  trade={tid} dir={direction} entry={entry_price:.2f} "
            f"state={signal_found['state']} bar_ts={signal_found['bar_ts'].strftime('%Y-%m-%d %H:%M')} "
            f"confirm_close={signal_found['confirm_close']:.2f} "
            f"realize_price={signal_found['realize_price']:.2f} "
            f"open_pnl_at_signal=${signal_found['open_pnl']:.2f} "
            f"actual_pnl_sierra=${pnl_sierra:.2f} "
            f"delta=${delta:+.2f}"
        )

    conn.close()

    print("\n=== T-317 PRE-T1 REALIZE REPLAY ===")
    print(f"Trades with pnl_sierra (since 2026-08-28): {len(trades)}")
    print(f"Trades where CEILING/FLOOR_FAILED would have fired pre-T1 in profit: {n_affected}")
    print(f"Σ$ difference (realize_at_confirm − actual_pnl_sierra): ${sum_delta:+.2f}")
    if details:
        print("\nDetail:")
        for d in details:
            print(d)
    else:
        print("(no trades affected)")


if __name__ == "__main__":
    _run()
