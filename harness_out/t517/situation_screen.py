#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-517 (29.09) SITUATION SCREEN — Michael 16:25: "לבחון בכל פעם אם אפשר לייצר ענף שמתאים לעומק הרוכשים והמוכרים,
התנהגות המחיר, אם זה יום ניטרלי ששינה כיוון או יום וריאציה שחזר לבחון שוב". The IB-return candidates (the price is
taking a one-sided IB extension back: returning = ≥ half back, failed = inside the IB again — backend/v9/services/
ib_return.py), split by the circumstance the system already knows at the decision:
  · day type (the vector's day_type: Neutral* · Variation · Trend* · Normal* · FORMING/other)
  · the order flow of the return — Σ delta of the 15-min bars (v9_bars_5min_continuous, Sierra) CLOSED at the decision,
    from the bucket of the extension extreme on: buyers took it back (Σ>0) or not, for a LONG (mirror for a SHORT)
Candidate level only (independent 1.5R on the candidate's own stop, first touch, EOD close, $2.60 RT, unique per
session/pattern/direction/entry/stop) — a screen; only the day-total replay decides.   usage: situation_screen.py [TAG]"""
import collections, datetime as dt, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from backend.v9.services.ib_return import ib_return_state, ib_return_rel

TAG = sys.argv[1] if len(sys.argv) > 1 else "t515ref"; COMM = 2.60; IL = dt.timezone(dt.timedelta(hours=3))


def mins(t):
    return int(t[:2]) * 60 + int(t[3:])


def bars_of(d):
    return [dict(t=r["t"], m=mins(r["t"]), h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in read_all(
        """select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI') t, high h, low l, close c from v9_bars_5min_woodies
        where symbol='MES' and (ts at time zone 'Asia/Jerusalem')::date = :d
        and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts""", {"d": d})]


def flow_of(d):
    return [dict(m=mins(r["t"]), delta=float(r["delta"] or 0)) for r in read_all(
        """select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI') t, delta from v9_bars_5min_continuous
        where (ts at time zone 'Asia/Jerusalem')::date = :d
        and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:59' order by ts""", {"d": d})]


def sim(after, short, ep, st, k=1.5):
    R = abs(ep - st)
    if R <= 0:
        return None
    for b in after:
        if (b["h"] >= st) if short else (b["l"] <= st):
            return -R
        if ((ep - b["l"]) if short else (b["h"] - ep)) >= k * R:
            return k * R
    return ((ep - after[-1]["c"]) if short else (after[-1]["c"] - ep)) if after else 0.0


def day_group(dt_):
    s = str(dt_ or "")
    for k in ("Neutral", "Variation", "Trend", "Normal", "Nontrend"):
        if s.startswith(k):
            return k
    return "other"


agg = collections.defaultdict(lambda: [0, 0, 0.0, set()]); ex = []
for p in sorted(glob.glob(f"harness_out/t466/{TAG}_2026-*.json")):
    d = p[-15:-5]; j = json.load(open(p)); B = bars_of(d); F = flow_of(d)
    if len(B) < 20:
        continue
    seen = set()
    for g in j.get("gateway_decisions") or []:
        mt = g.get("mfe_track") or {}; tv = g.get("tree_v3") or {}; v = tv.get("vec") or {}
        if not mt.get("stop") or not g.get("entry"):
            continue
        t = dt.datetime.fromisoformat(g["ts"]).astimezone(IL); m = t.hour * 60 + t.minute
        key = (g.get("pattern"), g.get("direction"), float(g["entry"]), float(mt["stop"]))
        if key in seen:
            continue
        seen.add(key)
        closed = [b for b in B if b["m"] + 5 <= m]
        st = ib_return_state(closed); rel = ib_return_rel(st, g.get("direction"))
        if not rel.startswith("with_"):
            continue
        # the extension extreme and the order flow since it (15-min buckets fully closed at m)
        post = closed[12:]
        if st["state"].endswith("_down"):
            ext_m = min(post, key=lambda b: b["l"])["m"]; sign = 1.0
        else:
            ext_m = max(post, key=lambda b: b["h"])["m"]; sign = -1.0
        bucket = ext_m - ((ext_m - 16 * 60 - 30) % 15)
        dsum = sum(f["delta"] for f in F if f["m"] >= bucket and f["m"] + 15 <= m)
        flow = "flow WITH" if sign * dsum > 0 else ("flow against" if sign * dsum < 0 else "flow none")
        after = [b for b in B if b["m"] >= m]
        pts = sim(after, g.get("direction") == "SHORT", float(g["entry"]), float(mt["stop"]))
        if pts is None:
            continue
        usd = pts * 5 - COMM
        blk = "bias" if g.get("blocked_by") == "tree:bias" else ("live" if g.get("outcome") == "live" else "other")
        dg = day_group(v.get("day_type"))
        for k in ((rel, dg, flow, blk), (rel, dg, flow, "ALL"), (rel, "ANY", flow, blk), (rel, "ANY", flow, "ALL")):
            a = agg[k]; a[0] += 1; a[1] += pts > 0; a[2] += usd; a[3].add(d)
        if d == "2026-09-28":
            ex.append(f"{t:%H:%M} {g.get('pattern')} {g.get('direction')} @{g['entry']} · {rel} · {v.get('day_type')} · Σδ={dsum:+.0f} · {blk} ⇒ {usd:+.2f}$")
print(f"{TAG}: candidates WITH the IB return — (state · day type · order flow of the return · what blocked) → 1.5R independent")
for k, (n, w, s, days) in sorted(agg.items()):
    if n >= 3:
        print(f"   {k[0]:15s} {k[1]:9s} {k[2]:12s} {k[3]:5s} n={n:4d} win {100 * w / n:3.0f}% Σ{s:+9.2f}$ days {len(days)}")
print("   28.09:")
for x in ex:
    print("     ", x)
