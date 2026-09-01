#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Is the stop band at the open calibrated on pre-market volatility?

Michael 2026-09-01: *"יש לה עסקאות טיפשיות בפתיחה — אי-זיהוי נכון של הכיוון,
או סטופ קרוב."*

The tight-stop half of that, traced to a mechanism. `stop_resolver` walks the
rung ladder nearest-to-farthest and takes the first rung inside a band whose
floor AND cap are both multiples of ATR-14 on 5-min bars. From the live log,
the same instrument on the same day:

    16:35 (five minutes after the open)   band [2.1,  5.0]
    mid-session                           band [7.6, 11.8]

The narrowest band of the day sits on its most volatile minutes. #875 took a
rung 4.50 points away — it cleared a floor of 2.1 — while the structural rung
was 14.25 away. Against a 7.6 floor that rung would not have qualified.

The suspected cause, from `five_min_system.py:1741-1752`:

    self._bar_buffer = self._bar_buffer[-20:]
    self._current_atr_5m = atr_5min(self._bar_buffer, period=14)

14 bars x 5 minutes = 70 minutes of history. Five minutes after the open that
window is one RTH bar and thirteen from before it. The band that governs the
opening trade is therefore built almost entirely from pre-market bars.

This script measures it instead of asserting it. For each session it computes
the ATR the resolver would actually have held at each RTH minute, against the
ATR of RTH bars alone, and reports the ratio and the bands each implies.

Honest-failure: a session without enough bars on either side is reported as
NOT_JUDGEABLE and excluded — never back-filled, never averaged over.

    python3 scripts/opening_atr_audit.py
    python3 scripts/opening_atr_audit.py --days 20
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# .env before anything imports the app — a script that silently falls back to
# the stale SQLite mirror reports a fiction with a straight face (T-161).
for _ln in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    _ln = _ln.strip()
    if _ln and not _ln.startswith("#") and "=" in _ln:
        _k, _v = _ln.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.split("#")[0].strip())

if "postgres" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("DATABASE_URL is not Postgres — refusing to report from a stale "
             "SQLite mirror (T-161).")

from backend.v9.db.read import read_all           # noqa: E402
from backend.v9.shared.atr import atr_5min        # noqa: E402

# RTH in exchange time. The bars carry UTC; 13:30 UTC == 09:30 ET == 16:30 IL.
RTH_OPEN_UTC_MIN = 13 * 60 + 30
RTH_CLOSE_UTC_MIN = 20 * 60

# The generic band multipliers the resolver applies to ATR_5m (CONT family;
# REV uses 1.5). Reported so the ATR difference can be read as points of stop.
BAND_FLOOR_MULT = 0.5
BAND_CAP_MULT = 1.2


def _minute(ts):
    return ts.hour * 60 + ts.minute


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--buffer", type=int, default=20,
                    help="bars kept in _bar_buffer (five_min_system: 20)")
    ap.add_argument("--period", type=int, default=14)
    a = ap.parse_args()

    rows = read_all(
        "SELECT ts, high AS h, low AS l, close AS c "
        "FROM v9_bars_5min_woodies "
        "WHERE ts >= now() - (:d || ' days')::interval "
        "ORDER BY ts", {"d": a.days}) or []
    if not rows:
        sys.exit("no bars returned — refusing to report zero as a quiet market")

    by_day = defaultdict(list)
    for r in rows:
        by_day[r["ts"].date()].append(r)

    print(f"\n{'='*86}")
    print(" ATR the resolver HELD vs ATR of the session it was about to trade")
    print(f" buffer={a.buffer} bars · period={a.period} "
          f"({a.period * 5} min of history)")
    print(f"{'='*86}")
    print(f" {'date':<12} {'@open':>7} {'RTH-only':>9} {'ratio':>6}   "
          f"{'band @open':>14} {'band RTH':>14}")

    ratios = []
    skipped = []
    for day in sorted(by_day):
        bars = by_day[day]
        rth = [b for b in bars
               if RTH_OPEN_UTC_MIN <= _minute(b["ts"]) < RTH_CLOSE_UTC_MIN]
        if len(rth) < a.period + 1:
            skipped.append((day, f"only {len(rth)} RTH bars"))
            continue

        # What the buffer held one bar after the open: the newest `buffer` bars
        # ending at the first RTH bar — exactly what _bar_buffer would contain.
        first_rth_ts = rth[0]["ts"]
        upto = [b for b in bars if b["ts"] <= first_rth_ts][-a.buffer:]
        if len(upto) < a.period:
            skipped.append((day, f"only {len(upto)} bars before the open"))
            continue

        atr_open = atr_5min(upto, period=a.period)
        atr_rth = atr_5min(rth, period=a.period)
        if not atr_open or not atr_rth:
            skipped.append((day, "ATR returned None"))
            continue

        ratio = atr_rth / atr_open
        ratios.append(ratio)
        b_open = f"[{BAND_FLOOR_MULT*atr_open:.1f}, {BAND_CAP_MULT*atr_open:.1f}]"
        b_rth = f"[{BAND_FLOOR_MULT*atr_rth:.1f}, {BAND_CAP_MULT*atr_rth:.1f}]"
        print(f" {str(day):<12} {atr_open:>7.2f} {atr_rth:>9.2f} "
              f"{ratio:>6.2f}x   {b_open:>14} {b_rth:>14}")

    print(f"{'-'*86}")
    if len(ratios) < 3:
        print(f" NOT_JUDGEABLE — {len(ratios)} usable sessions. No verdict on "
              f"fewer than 3.")
    else:
        ratios.sort()
        med = ratios[len(ratios) // 2]
        print(f" sessions={len(ratios)}  median ratio={med:.2f}x  "
              f"min={ratios[0]:.2f}x  max={ratios[-1]:.2f}x")
        print()
        if med >= 1.3:
            print(" READING: the session is materially more volatile than the")
            print(" window the resolver holds when it sizes the opening stop.")
            print(" Both band bounds scale with that ATR, so at the open the")
            print(" FLOOR is low enough to admit a rung inside the noise —")
            print(" which is the tight-stop failure, not a cap problem.")
        elif med <= 1.1:
            print(" READING: the windows agree. The hypothesis does NOT hold —")
            print(" the tight opening stop has some other cause. Say so and")
            print(" stop; do not tune a band on this.")
        else:
            print(" READING: a real but modest difference. Not enough on its")
            print(" own to justify changing a risk surface.")

    if skipped:
        print(f"\n excluded ({len(skipped)}) — never imputed:")
        for d, why in skipped[:8]:
            print(f"   {d}  {why}")

    print(f"""
 WHAT THIS DOES NOT SAY. It does not claim a wider opening stop would have
 won those trades: a wider stop buys fewer contracts and, past 15.0 points,
 is refused outright by RISK_BUDGET_SIZING_V1. It answers one question —
 whether the band that governs the opening trade is built from the opening's
 own volatility or from the quiet hours before it.
{'='*86}
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
