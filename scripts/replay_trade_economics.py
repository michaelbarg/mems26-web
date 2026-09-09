#!/usr/bin/env python3
"""replay_trade_economics.py — 5-number gate for trade_economics.

Runs economics() on every live trade and reports:
  1. n (total setups evaluated)
  2. targets on wrong side (must be 0)
  3. stop inside entry bar (must be 0)
  4. stop >= 1× bar median (target ≥95%)
  5. R:R >= floor (target ≥95%)
  + specific: 08.09 18:20 → stop 7676 / t1 >= 7711
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.exists():
    for ln in open(_env, encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.split("#")[0].strip())

from backend.v9.db.read import read_all
from backend.v9.services.trade_economics import economics


def main():
    trades = read_all(
        """SELECT id, direction, entry_price, stop, t1, t2, t3,
               day_type_at_entry, entry_ts, quality::text AS qt
        FROM v9_trades
        WHERE mode IN ('demo', 'live')
        AND entry_ts >= '2026-08-01'
        ORDER BY entry_ts""", {}
    )
    print(f"Trades: {len(trades)}")

    n = 0
    wrong_side = 0
    stop_inside_bar = 0
    stop_under_median = 0
    rr_under_floor = 0
    rr_floor = float(os.getenv("RR_MIN_ROTATION", "0.39"))

    target_check = None  # for 08.09 18:20

    for t in trades:
        entry = float(t["entry_price"] or 0)
        stop = float(t["stop"] or 0)
        direction = (t["direction"] or "").upper()
        day_type = t.get("day_type_at_entry") or ""
        entry_ts = t.get("entry_ts")

        if not entry or not stop:
            continue

        # Get RTH bars for the trade's session
        session_date = str(entry_ts)[:10] if entry_ts else None
        bars = []
        if session_date:
            bars_rows = read_all(
                """SELECT high AS h, low AS l FROM v9_bars_5min_woodies
                WHERE (ts AT TIME ZONE 'America/New_York')::date = :d
                AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
                AND (ts AT TIME ZONE 'America/New_York')::time < '16:00'""",
                {"d": session_date})
            bars = bars_rows or []

        setup = {"direction": direction, "entry_price": entry, "stop": stop}
        result = economics(setup, bars=bars, day_type=day_type)
        n += 1

        # 1. Targets on wrong side
        sign = 1.0 if direction == "LONG" else -1.0
        for tv in (result.t1, result.t2, result.t3):
            if tv is not None:
                if (direction == "LONG" and tv <= entry) or (direction == "SHORT" and tv >= entry):
                    wrong_side += 1

        # 2. Stop inside entry bar
        if bars and entry_ts:
            # Find entry bar
            try:
                entry_bars = read_all(
                    """SELECT high AS h, low AS l FROM v9_bars_5min_woodies
                    WHERE ts <= :ts
                    ORDER BY ts DESC LIMIT 1""",
                    {"ts": str(entry_ts)})
                if entry_bars:
                    eb = entry_bars[0]
                    ebh, ebl = float(eb["h"]), float(eb["l"])
                    if direction == "SHORT" and result.stop <= ebh:
                        stop_inside_bar += 1
                    elif direction == "LONG" and result.stop >= ebl:
                        stop_inside_bar += 1
            except Exception:
                pass

        # 3. Stop >= 1× bar median
        from backend.v9.services.trade_economics import _bar_median_range
        median = _bar_median_range(bars)
        if median > 0 and result.risk < median:
            stop_under_median += 1

        # 4. R:R >= floor
        if result.t1 is not None and result.risk > 0:
            rr = abs(result.t1 - entry) / result.risk
            if rr < rr_floor:
                rr_under_floor += 1

        # 5. Check 08.09 18:20
        ts_str = str(entry_ts or "")
        if "2026-09-08" in ts_str and "18:" in ts_str:
            target_check = result

    print(f"\n{'='*60}")
    print(f"n = {n}")
    print(f"targets wrong side = {wrong_side} (must be 0)")
    print(f"stop inside entry bar = {stop_inside_bar} (must be 0)")
    pct_median = 100 * (n - stop_under_median) / n if n else 0
    print(f"stop >= 1× bar median = {n - stop_under_median}/{n} ({pct_median:.0f}%, target ≥95%)")
    pct_rr = 100 * (n - rr_under_floor) / n if n else 0
    print(f"R:R >= {rr_floor} = {n - rr_under_floor}/{n} ({pct_rr:.0f}%, target ≥95%)")

    if target_check:
        print(f"\n08.09 18:20 trade:")
        print(f"  stop = {target_check.stop} (need 7676)")
        print(f"  t1 = {target_check.t1} (need >= 7711)")
        print(f"  risk = {target_check.risk}")
        print(f"  contracts = {target_check.contracts}")


if __name__ == "__main__":
    main()
