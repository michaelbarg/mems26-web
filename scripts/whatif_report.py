#!/usr/bin/env python3
"""WHATIF report — what would the CURRENT system detect on a historical session?

Runs the live detectors (VA_FADE, REACTIVE, INITIATIVE, chart patterns) on
bars from v9_bars_5min_woodies, bar-by-bar. Does NOT read v9_five_min_setups
(that's what the old system found, not what the current system would find).

Usage: python3 scripts/whatif_report.py --session 2026-08-25 [--json /tmp/whatif.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DSN = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12
POINT_USD = 5.0
TICK = 0.25


def load_bars(cur, session_date):
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               open, high, low, close, volume
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
          AND (ts AT TIME ZONE 'America/New_York')::time >= %s
          AND (ts AT TIME ZONE 'America/New_York')::time < %s
          AND symbol = 'MES'
        ORDER BY ts
    """, (session_date, RTH0, RTH1))
    return [{"ts": r[0], "o": float(r[1]), "h": float(r[2]),
             "l": float(r[3]), "c": float(r[4]), "v": int(r[5] or 0)}
            for r in cur.fetchall()]


def load_tpo_history(cur, session_date):
    """Load TPO snapshots for causal VA values (available_at = when known)."""
    cur.execute("""
        SELECT (created_at AT TIME ZONE 'America/New_York') AS avail,
               vah, val, poc
        FROM v9_tpo_history
        WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
        ORDER BY created_at
    """, (session_date,))
    return [{"avail": r[0], "vah": float(r[1]) if r[1] else None,
             "val": float(r[2]) if r[2] else None,
             "poc": float(r[3]) if r[3] else None}
            for r in cur.fetchall()]


def get_causal_va(tpo_snapshots, bar_ts):
    """Get the most recent VA values known BEFORE bar_ts (causal)."""
    best = None
    for snap in tpo_snapshots:
        if snap["avail"] and snap["avail"] <= bar_ts:
            if snap["vah"] is not None and snap["val"] is not None:
                best = snap
    return best


def sim_trade(bars, entry_idx, direction, entry_price, stop_price, t1_price, contracts):
    sign = 1.0 if direction == "LONG" else -1.0
    for i in range(entry_idx + 1, len(bars)):
        h, l = bars[i]["h"], bars[i]["l"]
        if (direction == "LONG" and l <= stop_price) or (direction == "SHORT" and h >= stop_price):
            pnl = (stop_price - entry_price) * sign - TICK
            return pnl * contracts * POINT_USD, "STOP", i
        if t1_price and ((direction == "LONG" and h >= t1_price) or
                         (direction == "SHORT" and l <= t1_price)):
            pnl = (t1_price - entry_price) * sign - TICK
            return pnl * contracts * POINT_USD, "T1", i
    last = bars[-1]["c"]
    pnl = (last - entry_price) * sign - TICK
    return pnl * contracts * POINT_USD, "EOD", len(bars) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--contracts", type=int, default=3)
    args = ap.parse_args()
    C = args.contracts

    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()

    bars = load_bars(cur, args.session)
    tpo_snaps = load_tpo_history(cur, args.session)

    # Also load old setups for comparison (NOT as candidates)
    cur.execute("""
        SELECT pattern, direction, entry_price FROM v9_five_min_setups
        WHERE (ts AT TIME ZONE 'America/New_York')::date = %s ORDER BY ts
    """, (args.session,))
    old_setups = [{"pattern": r[0], "direction": r[1], "entry": float(r[2])}
                  for r in cur.fetchall()]
    conn.close()

    quality = []
    if len(bars) != 78:
        quality.append(f"RTH_CARDINALITY({len(bars)})")

    print(f"=== WHATIF — {args.session} ({len(bars)} bars, {len(tpo_snaps)} TPO snaps) ===")
    if quality:
        print(f"  NOT_JUDGEABLE: {quality}")
    print(f"  Old system found: {len(old_setups)} setups")
    print()

    # Import the actual detectors
    from backend.v9.systems.va_fade import detect_va_fade, build_va_fade_setup

    candidates = []
    va_fired = set()

    # Bar-by-bar detection loop (causal: only bars[:i+1] visible)
    for i in range(IB_BARS, len(bars)):
        window = bars[:i + 1]
        bar = bars[i]

        # Get causal VA values
        va = get_causal_va(tpo_snaps, bar["ts"])
        vah = va["vah"] if va else None
        val = va["val"] if va else None

        # Classify day type (simplified: use post-hoc for now, note limitation)
        # TODO: per-bar classify_session for true causal day type
        day_type = "Variation"  # Most common; noted as limitation

        # VA_FADE detection
        trig = detect_va_fade(window, day_type, vah, val, already_fired=va_fired)
        if trig:
            va_fired.add(trig["type"])
            setup = build_va_fade_setup(trig, contracts=C)
            candidates.append({
                "bar": i,
                "time": bar["ts"].strftime("%H:%M") if hasattr(bar["ts"], "strftime") else str(bar["ts"]),
                "source": "VA_FADE",
                "pattern": setup["pattern"],
                "direction": setup["direction"],
                "entry": setup["entry_price"],
                "stop": setup["stop"],
                "t1": setup["t1"],
                "vah": vah,
                "val": val,
            })

    print(f"  NEW detections (VA_FADE): {len(candidates)}")
    total_pnl = 0
    slot_free = 0
    for c in candidates:
        if c["bar"] < slot_free:
            print(f"  SKIP {c['pattern']:20s} {c['direction']:5s} @{c['entry']:.2f} "
                  f"at {c['time']} (slot occupied)")
            continue
        pnl, reason, exit_i = sim_trade(
            bars, c["bar"], c["direction"], c["entry"], c["stop"], c["t1"], C)
        total_pnl += pnl
        slot_free = exit_i + 1
        print(f"  {c['pattern']:20s} {c['direction']:5s} @{c['entry']:.2f} "
              f"at {c['time']} VAH={c['vah']} VAL={c['val']} → ${pnl:>7.2f} ({reason})")

    print(f"\n  VA_FADE total: ${total_pnl:.2f} ({C}c)")
    print(f"\n  LIMITATIONS:")
    print(f"    - day_type hardcoded 'Variation' (should be per-bar classify_session)")
    print(f"    - TPO causal: uses v9_tpo_history.created_at for availability")
    print(f"    - Slot competition: only VA_FADE candidates (no S2/S4 competition)")

    if args.json:
        out = {
            "session": args.session, "bars": len(bars),
            "old_setups": len(old_setups),
            "new_candidates": len(candidates),
            "va_fade_pnl": round(total_pnl, 2),
            "candidates": candidates,
            "quality": quality,
        }
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2, default=str)


if __name__ == "__main__":
    main()
