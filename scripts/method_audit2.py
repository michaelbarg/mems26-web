#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""method_audit2.py — which layer carries the edge (tree vs the gates after it), and label-free context cuts. Read-only."""
import collections, glob, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "t529b"
COMM = 2.60; PT = 5.0; RR = 1.5


def q(sql):
    out = subprocess.run('%s -d mems26 -Atc "%s"' % (PSQL, sql.replace('"', '\\"')), shell=True, capture_output=True, text=True, timeout=180).stdout
    return [r.split("|") for r in out.splitlines() if r]


def fl(x):
    try:
        return float(x)
    except Exception:
        return None


bars = collections.defaultdict(list)
for r in q("select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), high, low, close "
           "from v9_bars_5min_woodies where symbol='MES' and ts>='2026-06-01' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts"):
    if len(r) == 5:
        bars[r[0]].append((r[1], fl(r[2]), fl(r[3]), fl(r[4])))


def score(day, t_il, direction, entry, stop):
    risk = abs(entry - stop); tgt = entry + RR * risk if direction == "LONG" else entry - RR * risk
    seq = [b for b in bars.get(day, []) if b[0] > t_il]
    if not seq:
        return None
    for _, h, l, c in seq:
        if direction == "LONG":
            if l <= stop: return (stop - entry) * PT - COMM
            if h >= tgt: return (tgt - entry) * PT - COMM
        else:
            if h >= stop: return (entry - stop) * PT - COMM
            if l <= tgt: return (entry - tgt) * PT - COMM
    c = seq[-1][3]
    return ((c - entry) if direction == "LONG" else (entry - c)) * PT - COMM


cands = []
for p in sorted(glob.glob("harness_out/t466/%s_2026-*.json" % TAG)):
    d = os.path.basename(p)[len(TAG) + 1:len(TAG) + 11]
    try:
        j = json.load(open(p))
    except Exception:
        continue
    trades_d = j.get("trades", [])
    for r in (j.get("routes") or []):
        tv = r.get("tree_v3")
        if not isinstance(tv, dict):
            continue
        ep = fl(r.get("entry")); stp = fl(r.get("stop")); direction = r.get("direction")
        if not (ep and stp and 1.0 <= abs(ep - stp) <= 30):
            continue
        sc = score(d, (r.get("il") or "00:00:00")[:5], direction, ep, stp)
        if sc is None:
            continue
        tr = None
        if (r.get("result") or {}).get("live"):
            for t in trades_d:
                if t.get("classification") == r.get("classification") and t.get("direction") == direction and abs((fl(t.get("entry")) or 0) - ep) < 0.01:
                    tr = t; break
        v = tv.get("vec") or {}
        later = r.get("live_blocked_by") or (r.get("result") or {}).get("blocked_by") or ""
        cands.append({"day": d, "hour": (r.get("il") or "00")[:2], "pattern": r.get("classification"), "system": r.get("system"), "leaf": str(tv.get("leaf") or "SKIP").upper(),
                      "score": sc, "fired": bool(tr), "trade_pnl": (fl(tr.get("pnl_usd")) if tr else None), "later": later if not tr else "FIRED",
                      "structure": v.get("structure"), "edge": v.get("edge"), "kind": v.get("kind"), "test": v.get("test"), "volume": v.get("volume"), "delta": v.get("delta"),
                      "shadow_only": bool(r.get("shadow_only"))})


def show(title, rows, key, top=14, minn=20):
    g = collections.defaultdict(list)
    for c in rows:
        g[key(c)].append(c)
    print("-- %s" % title)
    for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))[:top]:
        s = [c["score"] for c in v]
        if len(s) < minn:
            continue
        tr = [c["trade_pnl"] for c in v if c["trade_pnl"] is not None]
        print("   %-34s n=%4d win %3.0f%% S %+7.0f$ per %+6.1f$ | fired %3d S %+6.0f$" % (str(k)[:34], len(s), sum(1 for x in s if x > 0) / len(s) * 100, sum(s), sum(s) / len(s), len(tr), sum(tr)))


take = [c for c in cands if c["leaf"] == "TAKE"]
print("== F · which layer carries the edge? (TAKE candidates: the tree said yes) ==")
show("TAKE by what happened after the tree", take, lambda c: c["later"] or "(passed, no trade)", 12, 10)
print("   TAKE fired: n=%d Scand %+.0f$ realized %+.0f$ | TAKE not fired: n=%d Scand %+.0f$" % (
    sum(1 for c in take if c["fired"]), sum(c["score"] for c in take if c["fired"]), sum(c["trade_pnl"] or 0 for c in take if c["fired"]),
    sum(1 for c in take if not c["fired"]), sum(c["score"] for c in take if not c["fired"])))
show("TAKE by shadow_only producer", take, lambda c: "shadow producer" if c["shadow_only"] else "live producer", 4, 1)
print("\n== G · label-free context (all candidates) ==")
show("by structure (what price did to the IB)", cands, lambda c: c["structure"])
show("by edge", cands, lambda c: c["edge"])
show("by kind", cands, lambda c: c["kind"])
show("by test", cands, lambda c: c["test"])
show("by volume", cands, lambda c: c["volume"])
show("by delta", cands, lambda c: c["delta"])
show("by hour (IL)", cands, lambda c: c["hour"])
show("by system", cands, lambda c: c["system"], 4, 1)
print("\n== H · the robust core: pattern x phase with n>=25, sorted by per-candidate $ ==")
g = collections.defaultdict(list)
for c in cands:
    g[(c["pattern"], c["hour"] <= "17")].append(c["score"])
rows = [(k, len(v), sum(1 for x in v if x > 0) / len(v) * 100, sum(v) / len(v), sum(v)) for k, v in g.items() if len(v) >= 25]
for (pat, early), n, w, per, s in sorted(rows, key=lambda x: -x[3])[:12]:
    print("   %-26s %-8s n=%4d win %3.0f%% per %+6.1f$ S %+7.0f$" % (pat, "<=17h" if early else ">17h", n, w, per, s))
print("   ... worst:")
for (pat, early), n, w, per, s in sorted(rows, key=lambda x: x[3])[:8]:
    print("   %-26s %-8s n=%4d win %3.0f%% per %+6.1f$ S %+7.0f$" % (pat, "<=17h" if early else ">17h", n, w, per, s))
