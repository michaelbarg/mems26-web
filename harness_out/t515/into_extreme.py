#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-515 (29.09): is 28.09 16:50 a class? — trades that enter NEAR the session extreme on its side and need to break it to
reach T1 (LONG within k×ATR under the session high with T1 above it; SHORT mirror). From closed bars at the entry. Over a
variant's trades (default the same-day reference t515ref)."""
import collections, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from backend.v9.services.turn_state import atr_of
TAG = sys.argv[1] if len(sys.argv) > 1 else "t515ref"; K = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
agg = collections.defaultdict(lambda: [0, 0, 0.0]); rows = []
for p in sorted(glob.glob(f"harness_out/t466/{TAG}_2026-*.json")):
    d = p[-15:-5]; trades = json.load(open(p))["trades"]
    if not trades:
        continue
    B = [dict(t=r["t"], h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in read_all(
        """select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI') t, high h, low l, close c from v9_bars_5min_woodies
        where symbol='MES' and (ts at time zone 'Asia/Jerusalem')::date = :d
        and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts""", {"d": d})]
    for t in trades:
        fi = str(t.get("fired_il") or "")[:5]
        m = int(fi[:2]) * 60 + int(fi[3:]) if fi else None
        closed = [b for b in B if m is not None and int(b["t"][:2]) * 60 + int(b["t"][3:]) + 5 <= m]
        if len(closed) < 3:
            k = "early(<3 bars)"
        else:
            atr = atr_of(closed) or 5.0; hi = max(b["h"] for b in closed); lo = min(b["l"] for b in closed)
            e = float(t["entry"]); t1 = float(t.get("t1_target") or 0) or None
            if t["direction"] == "LONG":
                k = "LONG into high" if (hi - e) <= K * atr and t1 and t1 > hi else "LONG other"
            else:
                k = "SHORT into low" if (e - lo) <= K * atr and t1 and t1 < lo else "SHORT other"
        u = float(t.get("pnl_usd") or 0); a = agg[k]; a[0] += 1; a[1] += u > 0; a[2] += u
        if k.endswith(("high", "low")):
            rows.append((d, fi, t["classification"], t["direction"], t["entry"], t.get("outcome"), round(u, 2)))
print(f"{TAG} · k={K}×ATR")
for k, (n, w, s) in sorted(agg.items()):
    print(f"   {k:16s} n={n:3d} win {100 * w / max(1, n):3.0f}% Σ{s:+9.2f}$ net {s - 2.6 * n:+9.2f}$")
for r in rows:
    print("  ", r)
