#!/usr/bin/env python3
"""gate_profit_audit — did a gate block a WINNER? (Michael 14.08)

"אני רוצה שתאמת את הדגלים ולוודא שהדגלים לא חוסמים עסקאות מנצחות."

Method: for every blocked decision in the archive, walk the woodies bars
FORWARD from the decision timestamp and measure what the trade would have
done — MFE (max favourable excursion) vs MAE (max adverse) over the next
12 bars (60 min), using the SAME step-scaled geometry the live ladder uses
(stop = max(4, 0.6×median session step)). A block is judged:
  SAVER   — MAE hit the stop before MFE reached 1R  → the gate saved money
  KILLER  — MFE reached >= 1R before MAE hit stop   → the gate killed a winner
  NEUTRAL — neither within the window
Per-gate totals tell you which flags to keep and which to bring to Michael.

Usage: python3 scripts/gate_profit_audit.py [--days 10] [--min 5]
Read-only: touches nothing but the DB and the decision archive.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import sys
from datetime import datetime, timedelta

import psycopg2

BARS_FWD = 12          # 60 minutes
R_MULT = 1.0           # "winner" = 1R favourable before stop


def load_bars(conn):
    cur = conn.cursor()
    cur.execute("""SELECT ts, high, low, close FROM v9_bars_5min_woodies
                   ORDER BY ts""")
    return [(r[0], float(r[1]), float(r[2]), float(r[3])) for r in cur.fetchall()]


def median_step(bars, upto_idx, direction, zz_rev=5.0):
    """Same wide zigzag-leg measure as the live ladder (H6)."""
    seg = bars[max(0, upto_idx - 78):upto_idx]
    if len(seg) < 6:
        return None
    piv, d = [], 0
    hi_i = lo_i = 0
    hi_p, lo_p = seg[0][1], seg[0][2]
    for i in range(1, len(seg)):
        h, l = seg[i][1], seg[i][2]
        if h > hi_p: hi_i, hi_p = i, h
        if l < lo_p: lo_i, lo_p = i, l
        if d == 0 and hi_p - lo_p >= zz_rev:
            d = 1 if lo_i < hi_i else -1
            piv.append(lo_p if d == 1 else hi_p)
        elif d == 1 and hi_p - l >= zz_rev:
            piv.append(hi_p); d = -1; lo_i, lo_p = i, l
        elif d == -1 and h - lo_p >= zz_rev:
            piv.append(lo_p); d = 1; hi_i, hi_p = i, h
    legs = [abs(b - a) for a, b in zip(piv, piv[1:]) if abs(b - a) > 0]
    if len(legs) < 3:
        return None
    legs.sort()
    return legs[len(legs) // 2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--min", type=int, default=5, help="min samples to report a gate")
    args = ap.parse_args()

    conn = psycopg2.connect("postgresql://localhost/mems26")
    bars = load_bars(conn)
    if not bars:
        print("no bars"); return 2
    idx = {b[0].replace(tzinfo=None): i for i, b in enumerate(bars)}
    keys = sorted(idx)

    cutoff = datetime.utcnow() - timedelta(days=args.days)
    files = sorted(glob.glob('/Users/michael/SierraChart_Data/v9_export/decisions_archive/*.jsonl')) + \
            ['/Users/michael/SierraChart_Data/v9_export/gateway_decisions.jsonl']

    verdicts = collections.defaultdict(lambda: collections.Counter())
    pts = collections.defaultdict(float)
    examples = collections.defaultdict(list)

    for f in files:
        try:
            fh = open(f)
        except FileNotFoundError:
            continue
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            gate = d.get("blocked_by")
            entry = d.get("entry")
            ts = d.get("ts")
            if not (gate and entry and ts):
                continue
            try:
                entry = float(entry)
                if entry < 7000:      # old fixture rows
                    continue
                t = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            if t < cutoff:
                continue
            # nearest bar at/after the decision
            i = None
            for k in keys:
                if k >= t:
                    i = idx[k]; break
            if i is None or i + BARS_FWD >= len(bars):
                continue
            direction = str(d.get("direction", "")).upper()
            if direction not in ("LONG", "SHORT"):
                continue
            step = median_step(bars, i, direction)
            stop_d = max(4.0, 0.6 * step) if step else 6.0

            mfe = mae = 0.0
            hit_stop_first = False
            for j in range(i, i + BARS_FWD):
                _, h, l, _ = bars[j]
                if direction == "LONG":
                    mfe = max(mfe, h - entry); mae = max(mae, entry - l)
                else:
                    mfe = max(mfe, entry - l); mae = max(mae, h - entry)
                if mae >= stop_d and mfe < R_MULT * stop_d:
                    hit_stop_first = True
                    break
            if hit_stop_first:
                v = "SAVER"; pts[gate] -= stop_d
            elif mfe >= R_MULT * stop_d:
                v = "KILLER"; pts[gate] += mfe
                if len(examples[gate]) < 2:
                    examples[gate].append(f"{ts[:16]} {d.get('pattern')} {direction} @{entry} → MFE +{mfe:.1f}pt (stop {stop_d:.1f})")
            else:
                v = "NEUTRAL"
            verdicts[gate][v] += 1

    print(f"══ gate profit audit · last {args.days} days · winner = {R_MULT}R before stop ══")
    rows = []
    for gate, c in verdicts.items():
        n = sum(c.values())
        if n < args.min:
            continue
        rows.append((c["KILLER"] - c["SAVER"], gate, n, c, pts[gate]))
    rows.sort(reverse=True)
    print(f"{'gate':26s} {'n':>5s} {'KILLER':>7s} {'SAVER':>6s} {'NEUTRAL':>8s}  net_pts")
    for _, gate, n, c, p in rows:
        flag = "🔴" if c["KILLER"] > c["SAVER"] else ("🟢" if c["SAVER"] > c["KILLER"] else "⚪")
        print(f"{flag} {gate:24s} {n:5d} {c['KILLER']:7d} {c['SAVER']:6d} {c['NEUTRAL']:8d}  {p:+.0f}")
    print("\n🔴 = blocked more winners than losers → bring to Michael with this evidence")
    for _, gate, *_ in rows[:5]:
        for ex in examples.get(gate, []):
            print(f"   {gate}: {ex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
