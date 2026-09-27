#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-493/T-494 (27.09) — where does a replayed configuration lose money, path by path?

For every harness session of <TAG> (harness_out/t466/<TAG>_<d>.json, DECISION_TREE_V3 on) every route carries
tree_v3 {leaf,id,path} and the gateway result. Routes are folded into UNIQUE candidates per session
(classification, direction, entry, stop) — the same idea re-evaluated on consecutive bars counts once:
  · TAKE at least once and live at least once     → "live"
  · TAKE at least once, never live, shadow once   → "shadow" (the producer is shadow-only)
  · TAKE at least once, never live/shadow         → blocked by the first TAKE occurrence's gate
  · never TAKE                                    → refused by the tree, leaf id of the first occurrence
Each unique candidate is simulated INDEPENDENTLY on the bars (its own stop, 1.5R target, first touch, EOD close,
1 contract, $2.60 RT) — the same evaluation model as scripts/tree_measure.py. Σ$ is the opinion quality of a
bucket, not a portfolio: a bucket that would have made money is a CANDIDATE for a branch, and only the day-total
replay of that branch decides (Michael 24.09).

usage: python3 harness_out/t494/gate_audit.py <TAG> [--json out.json]
"""
import collections, datetime as dt, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all

TAG = sys.argv[1]
OUT = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
COMM = 2.60
files = sorted(glob.glob(os.path.join(ROOT, "harness_out", "t466", f"{TAG}_*.json")))


def bars_of(d):
    rows = read_all("""select ts, high h, low l, close c from v9_bars_5min_woodies where symbol='MES'
      and (ts at time zone 'Asia/Jerusalem')::date = :d and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by ts""", {"d": d})
    return [dict(ts=r["ts"], h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in rows]


def sim(after, short, ep, st):
    R = abs(ep - st); tgt = 1.5 * R
    for b in after:
        if (b["h"] >= st) if short else (b["l"] <= st):
            return -R
        if ((ep - b["l"]) if short else (b["h"] - ep)) >= tgt:
            return tgt
    return ((ep - after[-1]["c"]) if short else (after[-1]["c"] - ep)) if after else 0.0


def stat():
    return dict(n=0, w=0, usd=0.0, days=set(), ex=[])


def leaf_id(tv):
    """A leaf without an `id` reports its path as the id (e.g. the seed's take_with_hint) — label it readably."""
    i = str(tv.get("id") or "")
    if i and "/" not in i:
        return i
    parts = str(tv.get("path") or i).split("/")
    return "∅id:" + "/".join(p for p in parts[-2:])


buckets = collections.defaultdict(stat)     # (group, key) → stat
by_leaf_take = collections.defaultdict(lambda: collections.Counter())
day_pnl = {}
n_sessions = 0
cand_rows = []
for p in files:
    d = os.path.basename(p)[len(TAG) + 1:len(TAG) + 11]
    try:
        j = json.load(open(p))
    except Exception as e:
        print("bad", d, e); continue
    routes = [r for r in (j.get("routes") or []) if isinstance(r.get("tree_v3"), dict)]
    day_pnl[d] = float(j.get("daily_pnl_harness") or 0)
    if not routes:
        continue
    n_sessions += 1
    bs = bars_of(d)
    cands = collections.OrderedDict()
    for r in routes:
        k = (r.get("classification"), r.get("direction"), round(float(r.get("entry") or 0), 2), round(float(r.get("stop") or 0), 2))
        cands.setdefault(k, []).append(r)
    for k, occ in cands.items():
        takes = [r for r in occ if str(r["tree_v3"].get("leaf")).upper() == "TAKE"]
        res = lambda r: r.get("result") or {}
        if takes:
            if any(res(r).get("live") for r in takes):
                grp, key, first = "take", "live", next(r for r in takes if res(r).get("live"))
            elif any(res(r).get("shadow") for r in takes) or any(r.get("shadow_only") for r in takes):
                grp, key, first = "take", "shadow_only_producer", takes[0]
            else:
                first = takes[0]
                grp, key = "take", "gate:" + str(first.get("blocked_by") or res(first).get("blocked_by") or "?")
            by_leaf_take[leaf_id(first["tree_v3"])][key] += 1
        else:
            first = occ[0]
            tv = first["tree_v3"]
            grp = "shadow_leaf" if str(tv.get("leaf")).upper() == "SHADOW" else "refuse"
            key = "tree:" + leaf_id(tv)
        ep = float(first.get("entry") or 0); st = float(first.get("stop") or 0); short = first.get("direction") == "SHORT"
        R = abs(ep - st); pts = None
        clock = (first.get("_dbg_clock") or {}).get("sg_now")
        if bs and ep > 0 and st > 0 and 1.0 <= R <= 30 and clock:
            t0 = dt.datetime.fromisoformat(clock.replace(" ", "T"))
            after = [b for b in bs if b["ts"] > t0]
            if after:
                pts = sim(after, short, ep, st)
        vec = first["tree_v3"].get("vec") or {}
        cand_rows.append(dict(d=d, il=first.get("il"), cls=first.get("classification"), dir=first.get("direction"), sys=first.get("system"),
                              entry=ep, stop=st, grp=grp, key=key, leaf=leaf_id(first["tree_v3"]), pts=pts,
                              usd=None if pts is None else round(pts * 5 - COMM, 2),
                              **{f: vec.get(f) for f in ("opening_type", "phase", "day_type", "structure", "kind", "rel_bias", "zone",
                                                         "prior_zone", "edge", "hour")}))
        keys = [(grp, key)] + ([("take_leaf", leaf_id(first["tree_v3"]) + " → " + key)] if grp == "take" else [])
        for bk in keys:
            s = buckets[bk]
            if pts is not None:
                s["n"] += 1; s["w"] += pts > 0; s["usd"] += pts * 5 - COMM; s["days"].add(d)
                if len(s["ex"]) < 3 and pts > 0:
                    s["ex"].append(f"{d} {first.get('il')} {first.get('classification')} {first.get('direction')} {ep}")

print(f"{TAG}: {n_sessions} sessions with tree routes · harness day-total Σ{sum(day_pnl.values()):+.2f}$ over {len(day_pnl)} sessions")
for grp, title in (("take", "TREE SAID TAKE → what happened after the tree"), ("take_leaf", "TAKE leaf → disposition, Σ$"),
                   ("refuse", "TREE REFUSED (SKIP leaf)"), ("shadow_leaf", "TREE SHADOW leaf")):
    rows = sorted([(k, v) for (g, k), v in buckets.items() if g == grp], key=lambda kv: -kv[1]["usd"])
    if not rows:
        continue
    print(f"\n== {title}")
    print(f"{'bucket':44s} {'uniq':>5s} {'win%':>5s} {'Σ$ @1.5R':>10s} {'days':>5s}")
    for k, v in rows:
        win = round(100 * v["w"] / v["n"]) if v["n"] else 0
        print(f"{k:44s} {v['n']:5d} {win:5d} {v['usd']:+10.1f} {len(v['days']):5d}   {' | '.join(v['ex'][:2])}")
print("\n== TAKE leaf → disposition (unique candidates)")
for leaf, c in sorted(by_leaf_take.items(), key=lambda kv: -sum(kv[1].values())):
    print(f"{leaf:28s} " + " · ".join(f"{k}={v}" for k, v in c.most_common()))
if OUT:
    json.dump({"tag": TAG, "sessions": n_sessions, "day_total": round(sum(day_pnl.values()), 2),
               "buckets": [dict(group=g, key=k, n=v["n"], win=round(100 * v["w"] / v["n"]) if v["n"] else 0,
                                usd=round(v["usd"], 1), days=len(v["days"])) for (g, k), v in buckets.items()],
               "take_leaf_disposition": {k: dict(v) for k, v in by_leaf_take.items()}, "cands": cand_rows},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print("→", OUT)
