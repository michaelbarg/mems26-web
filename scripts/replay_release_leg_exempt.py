#!/usr/bin/env python3
"""replay_release_leg_exempt — H18: would a live-leg exemption on the release
gate have helped or hurt?

Michael 14.08 (architect review): "זיהוי היפוכים וכניסה לעסקאות — תבצע חקירה
עמוקה". 13.08 evidence: `awaiting_release` held 4 of 10 candidates, including
the 16:34 LONG (+12pt) and the 18:05 reversal SHORT.

Method (honest, single-slot): for every historical `awaiting_release` block in
the decisions archive, recompute leg_state.detect_leg on the bars available AT
THAT TIME (causal — only bars strictly before the decision). If the leg agreed
with the blocked direction, the exemption would have let it through; score that
entry on the real tape with the live ladder rules (stop = step-scaled floor 4,
T1 = 1×stop, time-stop 12 bars) and sum.

Usage: python3 scripts/replay_release_leg_exempt.py [--days 30]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2  # noqa: E402

from backend.v9.systems.leg_state import detect_leg  # noqa: E402

DSN = "postgresql://localhost/mems26"
POINT_VALUE = 5.0  # MES $ per point per contract
CONTRACTS = 1      # single-slot honesty


def _bars_for_day(cur, day: str):
    cur.execute("""
        SELECT ts, open, high, low, close, lsma_value, cci_14
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date = %s
          AND (ts AT TIME ZONE 'America/New_York')::time >= '09:30'
        ORDER BY ts""", (day,))
    return [{"ts": r[0], "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
             "close": float(r[4]),
             "lsma_value": float(r[5]) if r[5] is not None else None,
             "cci_14": float(r[6]) if r[6] is not None else None} for r in cur.fetchall()]


def _score(bars, idx, direction, entry):
    """Score from bar idx forward. stop 4pt (ladder floor), T1 = 1R, 12-bar time stop."""
    stop_d, t1_d = 4.0, 4.0
    for b in bars[idx + 1: idx + 13]:
        if direction == "LONG":
            if b["low"] <= entry - stop_d:
                return -stop_d
            if b["high"] >= entry + t1_d:
                return t1_d
        else:
            if b["high"] >= entry + stop_d:
                return -stop_d
            if b["low"] <= entry - t1_d:
                return t1_d
    last = bars[min(idx + 12, len(bars) - 1)]["close"]
    return (last - entry) if direction == "LONG" else (entry - last)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.expanduser(
        "~/SierraChart_Data/v9_export/decisions_archive/gateway_decisions.*.jsonl")))
    live = os.path.expanduser("~/SierraChart_Data/v9_export/gateway_decisions.jsonl")
    if os.path.exists(live):
        files.append(live)
    files = files[-args.days:]
    if not files:
        print("no decision archives found")
        return 2

    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    bars_cache: dict = {}
    exempt_pnl, exempt_n, wins = 0.0, 0, 0
    per_day = defaultdict(float)
    kept_blocked = 0

    for f in files:
        for line in open(f):
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("blocked_by") != "awaiting_release":
                continue
            ts = str(d.get("ts") or "")
            entry = float(d.get("entry") or 0)
            direction = str(d.get("direction") or "").upper()
            if not ts or entry <= 0 or direction not in ("LONG", "SHORT"):
                continue
            day = ts[:10]
            if day not in bars_cache:
                bars_cache[day] = _bars_for_day(cur, day)
            bars = bars_cache[day]
            if len(bars) < 12:
                continue
            # causal index: last bar strictly before the decision timestamp
            idx = None
            for i, b in enumerate(bars):
                if b["ts"].isoformat() < ts:
                    idx = i
                else:
                    break
            if idx is None or idx < 6 or idx >= len(bars) - 2:
                continue
            leg, age, why = detect_leg(bars[max(0, idx - 9): idx + 1])
            want = "UP" if direction == "LONG" else "DOWN"
            if leg != want:
                kept_blocked += 1
                continue
            pts = _score(bars, idx, direction, entry)
            usd = pts * POINT_VALUE * CONTRACTS
            exempt_pnl += usd
            exempt_n += 1
            per_day[day] += usd
            if pts > 0:
                wins += 1
            print(f"  {ts[:16]} {direction:5s} @{entry:8.2f} leg={leg} age={age} "
                  f"→ {pts:+.2f}pt (${usd:+.2f})")

    print("\n══ H18 release-gate leg-exemption replay ══")
    print(f"  blocks that WOULD have been exempted : {exempt_n}")
    print(f"  blocks that stay held (leg disagrees): {kept_blocked}")
    if exempt_n:
        print(f"  win rate                            : {wins}/{exempt_n} "
              f"({100.0 * wins / exempt_n:.0f}%)")
    print(f"  NET (single slot, 1 contract)       : ${exempt_pnl:+.2f}")
    if per_day:
        worst = min(per_day.items(), key=lambda kv: kv[1])
        best = max(per_day.items(), key=lambda kv: kv[1])
        print(f"  best day {best[0]} ${best[1]:+.2f} · worst day {worst[0]} ${worst[1]:+.2f}")
    print("  verdict:", "GO" if exempt_pnl > 0 and exempt_n >= 3 else "NO-GO / insufficient")
    return 0


if __name__ == "__main__":
    sys.exit(main())
