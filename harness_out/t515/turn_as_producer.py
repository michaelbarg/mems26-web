#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-515 (29.09): is the turn itself a tradeable signal? For every session, every time detect_turn() switches INTO
down (or up) on a closed bar, enter at the next bar's open, stop one tick beyond the defended extreme, target k×R
(first touch, stop first on the same bar, EOD close), 1 contract, $5/pt, $2.60 RT. No gates, no slot — the
opinion quality of the detector, not a portfolio.   usage: turn_as_producer.py [k=1.5] [max_risk_pts=12]"""
import collections, datetime as dt, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from backend.v9.services.turn_state import detect_turn

K = float(sys.argv[1]) if len(sys.argv) > 1 else 1.5
MAXR = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
sessions = [l.strip() for l in open("harness_out/t515/sessions.txt") if l.strip()]
rows = []
for d in sessions:
    bars = read_all("""select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI') t, open o, high h, low l, close c
        from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'Asia/Jerusalem')::date = :d
        and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts""", {"d": d})
    B = [dict(t=r["t"], o=float(r["o"]), h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in bars]
    prev = "none"
    for i in range(3, len(B) - 1):
        st = detect_turn(B[:i])            # closed bars 0..i-1 ⇒ decision at bar i's open
        cur = st["turn"]
        if cur in ("down", "up") and cur != prev:
            short = cur == "down"
            e = B[i]["o"]
            lvl = st["level"]
            stop = lvl + 0.25 if short else lvl - 0.25
            R = (stop - e) if short else (e - stop)
            if 0.5 <= R <= MAXR:
                tgt = e - K * R if short else e + K * R
                pts = None
                for b in B[i:]:
                    if (b["h"] >= stop) if short else (b["l"] <= stop):
                        pts = -R; break
                    if (b["l"] <= tgt) if short else (b["h"] >= tgt):
                        pts = K * R; break
                if pts is None:
                    pts = (e - B[-1]["c"]) if short else (B[-1]["c"] - e)
                rows.append(dict(d=d, t=B[i]["t"], dir="SHORT" if short else "LONG", e=e, R=round(R, 2), pts=round(pts, 2),
                                 usd=round(pts * 5 - 2.6, 2)))
        prev = cur
n = len(rows); w = sum(1 for r in rows if r["pts"] > 0); s = sum(r["usd"] for r in rows)
print(f"turn-as-producer k={K} maxR={MAXR}: {n} entries on {len(set(r['d'] for r in rows))} days · win {100*w/max(1,n):.0f}% · Σ{s:+.2f}$")
by = collections.defaultdict(lambda: [0, 0, 0.0])
for r in rows:
    k = (r["dir"], "16-17" if r["t"] < "17:30" else ("17-21" if r["t"] < "21:00" else "21+"))
    by[k][0] += 1; by[k][1] += r["pts"] > 0; by[k][2] += r["usd"]
for k, (n_, w_, s_) in sorted(by.items()):
    print(f"   {k}: n={n_} win {100*w_/n_:.0f}% Σ{s_:+.2f}$")
for r in rows:
    if r["d"] == "2026-09-28":
        print("   28.09:", r)
