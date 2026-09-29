#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-515 (29.09): v1 vs latched turn — how often the state differs per bar, and the detector's own opinion quality
(turn-as-producer: enter at the next open when the state switches INTO down/up, stop 1 tick beyond the defended
extreme, 1.5R, EOD close, 1 contract, $2.60 RT; no gates, no slot)."""
import collections, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from backend.v9.services.turn_state import detect_turn
sys.path.insert(0, os.path.join(ROOT, "harness_out", "t515"))
from turn_latch import detect_turn_latched

K, MAXR = 1.5, 12.0
sessions = [l.strip() for l in open("harness_out/t515/sessions.txt") if l.strip()]
diff = collections.Counter(); res = {"v1": [], "latch": []}
for d in sessions:
    B = [dict(t=r["t"], o=float(r["o"]), h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in read_all(
        """select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI') t, open o, high h, low l, close c from v9_bars_5min_woodies
        where symbol='MES' and (ts at time zone 'Asia/Jerusalem')::date = :d
        and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts""", {"d": d})]
    for name, fn in (("v1", detect_turn), ("latch", detect_turn_latched)):
        prev = "none"
        for i in range(3, len(B) - 1):
            st = fn(B[:i]); cur = st["turn"]
            if name == "latch":
                diff[(detect_turn(B[:i])["turn"], cur)] += 1
            if cur in ("down", "up") and cur != prev:
                short = cur == "down"; e = B[i]["o"]; lvl = st["level"]
                stop = lvl + 0.25 if short else lvl - 0.25; R = (stop - e) if short else (e - stop)
                if 0.5 <= R <= MAXR:
                    tgt = e - K * R if short else e + K * R; pts = None
                    for b in B[i:]:
                        if (b["h"] >= stop) if short else (b["l"] <= stop):
                            pts = -R; break
                        if (b["l"] <= tgt) if short else (b["h"] >= tgt):
                            pts = K * R; break
                    if pts is None:
                        pts = (e - B[-1]["c"]) if short else (B[-1]["c"] - e)
                    res[name].append(dict(d=d, t=B[i]["t"], dir="SHORT" if short else "LONG", usd=pts * 5 - 2.6, win=pts > 0))
            prev = cur
print("state per bar (v1 → latch):", {f"{a}→{b}": n for (a, b), n in sorted(diff.items()) if a != b},
      "| same:", sum(n for (a, b), n in diff.items() if a == b))
for name, rows in res.items():
    n = len(rows); s = sum(r["usd"] for r in rows); w = sum(r["win"] for r in rows)
    print(f"{name}: {n} entries · win {100 * w / max(1, n):.0f}% · Σ{s:+.2f}$")
    by = collections.defaultdict(lambda: [0, 0, 0.0])
    for r in rows:
        k = (r["dir"], "16-17" if r["t"] < "17:30" else ("17-21" if r["t"] < "21:00" else "21+"))
        by[k][0] += 1; by[k][1] += r["win"]; by[k][2] += r["usd"]
    for k, (n_, w_, s_) in sorted(by.items()):
        print(f"   {k}: n={n_} win {100 * w_ / n_:.0f}% Σ{s_:+.2f}$")
