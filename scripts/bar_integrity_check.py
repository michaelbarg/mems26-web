#!/usr/bin/env python3
"""Bar-stream integrity check — the silent thief under everything (2026-07-29).

Found while answering Michael's "which blocker prevented winning trades": the
stored bars for 2026-07-28 CHANGED overnight. At 18:09 IL that day the session
high read 7455.75; the next morning the same minutes read 7482 — and the stored
day contains a 38-point "jump" between two adjacent 5-minute bars (17:20 close
7430.25 → 17:25 low 7468.00). Markets do not teleport 38 points between bars;
re-sent bars landed on the wrong hour (the WOODIES_TS_HOUR class).

Why this is the deepest root and not a display bug:
  • signals are computed FROM these bars → bogus setups;
  • the day-type LEG oscillated DOWN↔UP intraday — session high/low corrupted
    mid-day flips the leg, which flips the with-trend gates;
  • every counterfactual (gate accountability, pattern ranking) inherits it.

This is a READ-ONLY detector: seams (adjacent-bar gaps > threshold), duplicate
timestamps, and a live cross-check of the latest bar close against Sierra's own
last_price. Run pre-open and at EOD; wire into mems26_verify.

    python3 scripts/bar_integrity_check.py               # today (ET)
    python3 scripts/bar_integrity_check.py 2026-07-28
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

SEAM_PTS = float(os.getenv("BAR_SEAM_MAX_PTS", "15"))     # MES rarely gaps >15pt in 5min intraday
STATE = os.path.expanduser("~/SierraChart_Data/v9_export/sierra_state.json")


def main() -> int:
    day = sys.argv[1] if len(sys.argv) > 1 else None
    import psycopg2
    cn = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://localhost/mems26"))
    cur = cn.cursor()
    if day is None:
        cur.execute("SELECT (now() AT TIME ZONE 'America/New_York')::date")
        day = cur.fetchone()[0].isoformat()
    cur.execute(
        "SELECT ts AT TIME ZONE 'Asia/Jerusalem', open, high, low, close "
        "FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date = %s ORDER BY ts", (day,))
    bars = [(t, float(o), float(h), float(l), float(c)) for t, o, h, l, c in cur.fetchall()]
    print(f"═══ bar integrity · {day} · {len(bars)} bars ═══")
    if len(bars) < 2:
        print("  not enough bars to judge")
        return 0

    problems = 0

    # 1 — seams: adjacent bars that do not overlap and gap wider than SEAM_PTS
    for a, b in zip(bars, bars[1:]):
        gap = max(b[3] - a[2], a[3] - b[2])       # low(next)-high(prev) or reverse
        if gap > SEAM_PTS:
            problems += 1
            print(f"  🔴 SEAM {gap:+.2f}pt: {a[0]:%H:%M} (H{a[2]} L{a[3]} C{a[4]}) → "
                  f"{b[0]:%H:%M} (H{b[2]} L{b[3]}) — misplaced/shifted bars")

    # 2 — duplicate timestamps
    seen = {}
    for t, *_ in bars:
        seen[t] = seen.get(t, 0) + 1
    for t, n in seen.items():
        if n > 1:
            problems += 1
            print(f"  🔴 DUPLICATE ts {t:%H:%M} ×{n}")

    # 3 — freshness cross-check vs Sierra's own last price (live days only)
    try:
        st = json.load(open(STATE))
        lp = float(st.get("last_price") or 0)
        today_et = None
        cur.execute("SELECT (now() AT TIME ZONE 'America/New_York')::date")
        today_et = cur.fetchone()[0].isoformat()
        if day == today_et and lp > 0:
            last_close = bars[-1][4]
            drift = abs(lp - last_close)
            if drift > SEAM_PTS:
                problems += 1
                print(f"  🔴 LIVE DRIFT {drift:.2f}pt: last bar close {last_close} "
                      f"vs Sierra last_price {lp} — the stored stream is not the market")
            else:
                print(f"  ✅ live cross-check: bar close {last_close} vs Sierra {lp} "
                      f"(drift {drift:.2f}pt)")
    except Exception as e:
        print(f"  (live cross-check unavailable: {e})")

    if problems == 0:
        print("  ✅ no seams, no duplicates — stream looks coherent")
    else:
        print(f"\n  verdict: {problems} problem(s) — do NOT trust classifications, "
              f"gate levels, or counterfactuals computed from this day until resolved")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
