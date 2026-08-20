# -*- coding: utf-8 -*-
"""F1 replay — would DIRECTION_COMPASS_V1 have prevented the +$576 direction family?

Read-only. Reuses the MAX_DAYS_2026-08-20 engine's trade set (/tmp/mx_trades.json,
85 live CLOSED trades with entry_ts, Σ=+$320.00) and reconstructs the compass AT
ENTRY TIME from the real historical bars — no hindsight:

  leg             leg_state.detect_leg over the 12 CLOSED woodies bars before entry
  lsma            direction_context_live.lsma_slope_pts_per_bar over the last 4
  value_migration multiday_profile.value_migration over the prior 10 days
                  (exactly the query market_context.get_market_context uses)
  cvd             direction_context.cvd_slope over the last 3 closed v9_bars_5min
                  (that column only exists from 2026-08-07 — absent before, Rule 1)

Then applies direction_compass.direction_verdict (the same function the gateway
calls) and reports: prevented losses vs winners newly blocked.

COVERAGE — why this one gate accounts for ALL three wirings: `compass_or` (which
feeds direction_context and cont_trend_filter) overrides the legacy input under
exactly the same test as this gate (confident + structurally anchored), and this
gate is strictly the stricter of the two (it carries no neutral-responsive /
rotation exemption). So any trade those two could newly block is already inside
this block set. NOT measured (declared): `compass_or` can also RELAX
cont_trend_filter — when the compass agrees with a setup that `dir_sustained`
opposed, a trade that never happened could now fire. Those live in the decisions
archive, not in v9_trades, and are bounded by the existing
LEG_REPLACES_SUSTAINED_V1 precedent.

Usage:  DIRECTION_COMPASS_V1=1 python3 scripts/f1_compass_replay.py
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DIRECTION_COMPASS_V1", "1")

import psycopg2  # noqa: E402

from backend.v9.services.direction_compass import (  # noqa: E402
    compute_compass, direction_verdict)
from backend.v9.systems.direction_context import cvd_slope  # noqa: E402
from backend.v9.systems.direction_context_live import lsma_slope_pts_per_bar  # noqa: E402
from backend.v9.systems.leg_state import detect_leg  # noqa: E402
from backend.v9.systems.multiday_profile import (  # noqa: E402
    session_tpo_profile, value_migration)

TRADES = os.getenv("F1_TRADES", "/tmp/mx_trades.json")
conn = psycopg2.connect("postgresql://localhost/mems26")
conn.set_session(readonly=True, autocommit=True)
cur = conn.cursor()

# ── canonical bars (ts = bar OPEN; a bar is CLOSED at ts+5min) ───────────────
cur.execute("""SELECT ts AT TIME ZONE 'America/New_York', open, high, low, close,
                      volume, lsma_value, cci_14
               FROM v9_bars_5min_woodies WHERE ts >= '2026-06-20' ORDER BY ts""")
WOOD = [(t, float(o), float(h), float(l), float(c), int(v or 0),
         float(lv) if lv is not None else None,
         float(cc) if cc is not None else None)
        for t, o, h, l, c, v, lv, cc in cur.fetchall()]
WOOD_BY_DAY = defaultdict(list)
for r in WOOD:
    WOOD_BY_DAY[r[0].date()].append(r)

cur.execute("""SELECT ts AT TIME ZONE 'America/New_York', cumulative_delta
               FROM v9_bars_5min WHERE ts >= '2026-06-20' AND cumulative_delta IS NOT NULL
               ORDER BY ts""")
CVD = [(t, float(d)) for t, d in cur.fetchall()]


def closed_before(seq, when, n):
    """The n most recent bars fully CLOSED at `when` (oldest→newest)."""
    out = [r for r in seq if r[0] + timedelta(minutes=5) <= when]
    return out[-n:] if n else out


_MIG_CACHE = {}


def migration_for(day):
    """Prior-10-days value migration — the same window market_context uses."""
    if day in _MIG_CACHE:
        return _MIG_CACHE[day]
    sessions = []
    for d in sorted(WOOD_BY_DAY):
        if d >= day or (day - d).days > 10:
            continue
        bars = WOOD_BY_DAY[d]
        if len(bars) >= 12:
            sessions.append([{"o": b[1], "h": b[2], "l": b[3], "c": b[4], "vol": b[5]}
                             for b in bars])
    profiles = [p for p in (session_tpo_profile(s) for s in sessions) if p]
    out = value_migration(profiles).get("direction") if profiles else None
    _MIG_CACHE[day] = out
    return out


def compass_at(when):
    wb = closed_before(WOOD, when, 12)
    lsma_rows = [{"lsma_value": b[6]} for b in reversed(wb) if b[6] is not None]
    slope = lsma_slope_pts_per_bar(lsma_rows, 4) if len(lsma_rows) >= 2 else None
    leg_bars = [{"high": b[2], "low": b[3], "close": b[4],
                 "lsma_value": b[6], "cci_14": b[7]} for b in wb]
    leg, age, _ = detect_leg(leg_bars) if len(leg_bars) >= 5 else (None, 0, "")
    cb = [r for r in CVD if r[0] + timedelta(minutes=5) <= when][-3:]
    cvd = cvd_slope([{"cumulative_delta": d} for _, d in cb], 3) if len(cb) >= 3 else None
    return compute_compass(lsma_slope=slope, leg_dir=leg, leg_age=age,
                           value_migration=migration_for(when.date()), cvd_slope=cvd)


# ── the MAX_DAYS §3 "direction family" mistake set (mx5.py, verbatim rules) ──
trades = json.load(open(TRADES))
rth_open = {}
for d, bars in WOOD_BY_DAY.items():
    rth = [b for b in bars if (b[0].hour, b[0].minute) >= (9, 30) and b[0].hour < 16]
    if rth:
        rth_open[str(d)] = rth[0][1]

S2_FAMILY = ("ZLR", "REACTIVE", "INITIATIVE", "CONFLUENCE")


def maxdays_category(t):
    pat, dr, dt, d = str(t["pattern"]), t["dir"], str(t["day_type"]), t["date"]
    if pat.startswith("OPENING_DRIVE"):
        return "OD-corrected"
    if pat.startswith("TREND_STEP"):
        return None                      # G2 stair exemption
    if (dt == "Trend_Normal" and dr == "SHORT") or (dt == "Trend_DD" and dr == "LONG"):
        return "counter-day"
    if (dt == "Variation" and dr == "SHORT" and pat.startswith(S2_FAMILY)
            and d in rth_open and t["entry"] is not None
            and t["entry"] > rth_open[d] - 2.0):
        return "var-short-nodrift"
    return None


rows = []
for t in trades:
    when = datetime.strptime(t["et"][:19], "%Y-%m-%d %H:%M:%S")
    c = compass_at(when)
    allow, why = direction_verdict(pattern=t["pattern"], direction=t["dir"], compass=c)
    rows.append(dict(t=t, c=c, blocked=not allow, why=why, cat=maxdays_category(t)))

blocked = [r for r in rows if r["blocked"]]
bl_loss = [r for r in blocked if r["t"]["pnl"] < 0]
bl_win = [r for r in blocked if r["t"]["pnl"] > 0]
bl_be = [r for r in blocked if r["t"]["pnl"] == 0]

print("=" * 78)
print("F1 COMPASS REPLAY — 85 live closed trades, 2026-07-07..08-19 (books Σ=+$320.00)")
print("=" * 78)
print("compass verdicts: UP %d · DOWN %d · NEUTRAL %d"
      % (sum(1 for r in rows if r["c"]["direction"] == "UP"),
         sum(1 for r in rows if r["c"]["direction"] == "DOWN"),
         sum(1 for r in rows if r["c"]["direction"] == "NEUTRAL")))
print("BLOCKED total: %d/%d" % (len(blocked), len(rows)))
print("  losers prevented : %2d   recovered  %+9.2f" % (len(bl_loss), -sum(r["t"]["pnl"] for r in bl_loss)))
print("  winners lost     : %2d   forgone    %+9.2f" % (len(bl_win), -sum(r["t"]["pnl"] for r in bl_win)))
print("  BE blocked       : %2d" % len(bl_be))
print("  NET on the books : %+9.2f" % -sum(r["t"]["pnl"] for r in blocked))

print("\n---- the MAX_DAYS +$576.25 direction-family mistake set ----")
tot_c = defaultdict(lambda: [0, 0, 0.0, 0.0])   # cat -> [n, caught, $total, $caught]
for r in rows:
    if not r["cat"]:
        continue
    s = tot_c[r["cat"]]
    s[0] += 1
    s[2] += -r["t"]["pnl"]
    if r["blocked"]:
        s[1] += 1
        s[3] += -r["t"]["pnl"]
for cat in ("OD-corrected", "var-short-nodrift", "counter-day"):
    n, caught, tot, got = tot_c[cat]
    print("  %-18s n=%2d  compass prevents %2d  |  MAX_DAYS $%+8.2f  compass $%+8.2f"
          % (cat, n, caught, tot, got))
allc = sum(v[0] for v in tot_c.values())
allk = sum(v[1] for v in tot_c.values())
print("  %-18s n=%2d  compass prevents %2d  |  MAX_DAYS $%+8.2f  compass $%+8.2f"
      % ("TOTAL", allc, allk, sum(v[2] for v in tot_c.values()),
         sum(v[3] for v in tot_c.values())))

print("\n---- every blocked trade ----")
for r in sorted(blocked, key=lambda r: r["t"]["et"]):
    t = r["t"]
    print("  #%-4s %s %-6s %-20s pnl %+8.2f  cat=%-17s compass=%s conf=%.2f %s"
          % (t["id"], t["et"][:16], t["dir"], str(t["pattern"])[:20], t["pnl"],
             r["cat"] or "-", r["c"]["direction"], r["c"]["confidence"],
             {k: v for k, v in r["c"]["components"].items() if v is not None}))

print("\n---- mistake-set trades the compass does NOT catch ----")
for r in sorted([r for r in rows if r["cat"] and not r["blocked"]], key=lambda r: r["t"]["et"]):
    t = r["t"]
    print("  #%-4s %s %-6s %-20s pnl %+8.2f  cat=%-17s compass=%s conf=%.2f (%s)"
          % (t["id"], t["et"][:16], t["dir"], str(t["pattern"])[:20], t["pnl"],
             r["cat"], r["c"]["direction"], r["c"]["confidence"], r["c"]["reason"][:60]))

json.dump([{"id": r["t"]["id"], "et": r["t"]["et"], "dir": r["t"]["dir"],
            "pattern": r["t"]["pattern"], "pnl": r["t"]["pnl"], "cat": r["cat"],
            "blocked": r["blocked"], "compass": r["c"]["direction"],
            "conf": r["c"]["confidence"], "components": r["c"]["components"]}
           for r in rows], open("/tmp/f1_replay_out.json", "w"), indent=1, default=str)
print("\nwrote /tmp/f1_replay_out.json")
