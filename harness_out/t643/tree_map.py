#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-643 · the full tree map (Michael 24.10: "להבין ולראות את העץ שלנו במלואו, איך הוא מפסיד … האם הוא לא יודע להתפצל באופן חכם").

Every candidate of the 81-session live-config replay (harness_out/t640/days/live_*.json, gateway_decisions + routes,
the real tree path of each) is put in its leaf and labelled by what the price did next — management-independent:
  good = +1R before the candidate's own stop · bad = the stop first · flat = neither by the close
(5-min bars; in the entry bar only the stop counts; a bar that touches both = stop first). Candidates are de-duplicated:
per day and (pattern, direction) the first one in every 30 minutes. Read-only (JSON + SELECT).

Output: leaf families (n, good/bad/flat, good%) · mixed leaves (no edge vs the base rate) · for each mixed TAKE leaf the
single split that separates good from bad best, with ≥ MIN per side and the same sign on both halves of the period.
  python3 harness_out/t643/tree_map.py [--min 15] [--json harness_out/t643/tree_map.json]
"""
import os, sys, json, glob, argparse, collections, datetime as dt
ROOT = "/Users/michael/Downloads/mems26_web_git"
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York")

ap = argparse.ArgumentParser()
ap.add_argument("--variant", default="live")
ap.add_argument("--min", type=int, default=15)
ap.add_argument("--json", default=None)
ap.add_argument("--rows", default=None, help="dump every labelled candidate (features + label) for tree_check.py")
args = ap.parse_args()

files = sorted(glob.glob("harness_out/t640/days/%s_*.json" % args.variant))
cands = []
for f in files:
    d = json.load(open(f)); day = d["session"]
    for r, g in zip(d.get("routes") or [], d.get("gateway_decisions") or []):
        tv = g.get("tree_v3") or {}
        if not tv or (r.get("classification"), r.get("direction")) != (g.get("pattern"), g.get("direction")):
            continue
        ts = dt.datetime.fromisoformat(str(g["ts"]).replace("Z", "+00:00"))
        cands.append(dict(day=day, ts=ts, pat=g.get("pattern"), dir=g.get("direction"), entry=r.get("entry"), stop=r.get("stop"),
                          leaf=tv.get("leaf"), lid=str(tv.get("id") or ""), path=str(tv.get("path") or ""), vec=tv.get("vec") or {},
                          blocked=g.get("blocked_by"), outcome=g.get("outcome")))
cands.sort(key=lambda c: c["ts"])
last = {}; C = []
for c in cands:
    k = (c["day"], c["pat"], c["dir"])
    if k in last and (c["ts"] - last[k]).total_seconds() < 1800:
        continue
    last[k] = c["ts"]; C.append(c)
days = sorted(set(c["day"] for c in C))
a = dt.datetime.combine(dt.date.fromisoformat(days[0]), dt.time(0, 0), ET)
z = dt.datetime.combine(dt.date.fromisoformat(days[-1]) + dt.timedelta(days=1), dt.time(0, 0), ET)
bars = read_all("""select b.ts, b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd
 on cd.ts = b.ts where b.symbol = 'MES' and b.ts >= :a and b.ts < :z order by b.ts""", {"a": a, "z": z})
rth = collections.defaultdict(list)
for b in bars:
    e = b["ts"].astimezone(ET)
    if dt.time(9, 30) <= e.time() < dt.time(16, 0):
        for k in ("o", "h", "l", "c"): b[k] = float(b[k])
        b["delta"] = float(b["delta"]) if b["delta"] is not None else 0.0
        rth[e.date().isoformat()].append(b)


def label(c):
    bs = rth.get(c["day"]) or []
    if not bs or c["entry"] is None or c["stop"] is None:
        return None
    ep = float(c["entry"]); R = abs(ep - float(c["stop"]))
    if R < 0.5:
        return None
    short = c["dir"] == "SHORT"
    path = [b for b in bs if b["ts"] >= c["ts"] - dt.timedelta(seconds=30)]
    if not path:
        return None
    for k, b in enumerate(path):
        adv = (b["h"] - ep) if short else (ep - b["l"]); fav = (ep - b["l"]) if short else (b["h"] - ep)
        if adv >= R:
            return "bad"
        if k > 0 and fav >= R:
            return "good"
    return "flat"


def bar_features(c):
    """Rule A (accepted extension against the trade) and the position in the last hour's range, from closed bars."""
    bs = rth.get(c["day"]) or []
    seen = [b for b in bs if b["ts"] + dt.timedelta(minutes=5) <= c["ts"] + dt.timedelta(seconds=30)]
    out = {}
    short = c["dir"] == "SHORT"
    if len(seen) >= 12:
        ibh = max(b["h"] for b in seen[:12]); ibl = min(b["l"] for b in seen[:12])
        last6 = seen[12:][-6:]
        beyond = [b for b in last6 if (b["c"] > ibh if short else b["c"] < ibl)]
        ds = sum(b["delta"] for b in beyond)
        out["ruleA"] = "accepted_against" if (len(beyond) >= 3 and ((ds > 0) if short else (ds < 0))) else "no"
        with_ = [b for b in last6 if (b["c"] < ibl if short else b["c"] > ibh)]
        dw = sum(b["delta"] for b in with_)
        out["with_accepted"] = "yes" if (len(with_) >= 3 and ((dw < 0) if short else (dw > 0))) else "no"
    else:
        out["ruleA"] = "ib_forming"; out["with_accepted"] = "ib_forming"
    if seen and c["entry"] is not None:
        h12 = seen[-12:]; hh = max(b["h"] for b in h12); ll = min(b["l"] for b in h12); rg = max(hh - ll, 0.25)
        ep = float(c["entry"]); pos = ((hh - ep) / rg) if short else ((ep - ll) / rg)
        out["pos_hour"] = "edge" if pos <= 0.35 else ("middle" if pos <= 0.65 else "far")
        sb = seen[-1]
        out["tested"] = "yes" if ((sb["h"] >= hh - 0.5) if short else (sb["l"] <= ll + 0.5)) else "no"
    return out


def family(c):
    if c["leaf"] != "TAKE" or "/" not in c["lid"]:
        return "%s:%s" % (c["leaf"], c["lid"])
    segs = c["path"].split("/")
    ph = next((s.split("=")[1] for s in segs if s.startswith("phase=")), "?")
    last_seg = segs[-1]
    key, val = (last_seg.split("=", 1) + [""])[:2]
    if key == "rel_bias" and val == "with":
        nm = "with_hint"
    elif key == "edge":
        nm = "failed_ext"
    elif key == "kind":
        nm = "kind=" + val.replace("*(", "").replace(")", "")
    else:
        nm = last_seg
    return "TAKE:%s|phase=%s" % (nm, ph)


rows = []
for c in C:
    lb = label(c)
    if lb is None:
        continue
    f = dict(c["vec"]); f.update(bar_features(c))
    f.pop("R_atr", None)
    rows.append(dict(day=c["day"], ts=c["ts"].isoformat(), pat=c["pat"], dir=c["dir"], fam=family(c), leaf=c["leaf"], lid=c["lid"],
                     path=c["path"], lab=lb, f=f, blocked=c["blocked"], outcome=c["outcome"]))
half = days[len(days) // 2]
base = collections.Counter(r["lab"] for r in rows)
N = len(rows); base_good = base["good"] / N
print("candidates %d (deduped %d, labelled %d) · sessions %d (%s..%s) · base: good %.1f%% bad %.1f%% flat %.1f%%" % (
    len(cands), len(C), N, len(days), days[0], days[-1], 100 * base["good"] / N, 100 * base["bad"] / N, 100 * base["flat"] / N))
fam = collections.defaultdict(list)
for r in rows:
    fam[r["fam"]].append(r)


def st(rs):
    cc = collections.Counter(r["lab"] for r in rs); n = len(rs)
    return n, cc["good"], cc["bad"], cc["flat"], (cc["good"] / n if n else 0.0)


print("\n## leaf families (n ≥ 10), sorted by n")
print("| family | n | good | bad | flat | good% | vs base | real outcome (fired/blocked) |")
out_fam = []
for k, rs in sorted(fam.items(), key=lambda kv: -len(kv[1])):
    n, g, b, fl, gp = st(rs)
    if n < 10:
        continue
    fired = sum(1 for r in rs if r["outcome"] not in ("blocked",)); blk = n - fired
    print("| %s | %d | %d | %d | %d | %.0f%% | %+.0f | %d/%d |" % (k, n, g, b, fl, 100 * gp, 100 * (gp - base_good), fired, blk))
    out_fam.append(dict(family=k, n=n, good=g, bad=b, flat=fl, good_pct=round(100 * gp, 1), vs_base=round(100 * (gp - base_good), 1)))

FEATS = ["opening_type", "phase", "day_type", "structure", "pattern", "kind", "direction", "rel_bias", "zone", "prior_zone",
         "poc_side", "value_migration", "edge", "test", "volume", "delta", "turn", "turn_rel", "ruleA", "with_accepted",
         "pos_hour", "tested", "hour"]


def best_splits(rs, mn):
    res = []
    for ft in FEATS:
        vals = collections.Counter(str(r["f"].get(ft)) for r in rs)
        for v, cnt in vals.items():
            S = [r for r in rs if str(r["f"].get(ft)) == v]; T = [r for r in rs if str(r["f"].get(ft)) != v]
            if len(S) < mn or len(T) < mn:
                continue
            gs = st(S)[4]; gt = st(T)[4]
            # stability: the same sign of (gs - gt) on both halves, each half with ≥ 5 per side
            ok = True; halves = []
            for lo_, hi_ in ((None, half), (half, None)):
                S2 = [r for r in S if (lo_ is None or r["day"] >= lo_) and (hi_ is None or r["day"] < hi_)]
                T2 = [r for r in T if (lo_ is None or r["day"] >= lo_) and (hi_ is None or r["day"] < hi_)]
                if len(S2) < 5 or len(T2) < 5:
                    ok = False; break
                d2 = st(S2)[4] - st(T2)[4]; halves.append(round(100 * d2))
                if (d2 > 0) != (gs - gt > 0):
                    ok = False
            res.append(dict(feat=ft, val=v, nS=len(S), gS=round(100 * gs), nT=len(T), gT=round(100 * gt), diff=round(100 * (gs - gt)),
                            stable=ok, halves=halves))
    res.sort(key=lambda x: (-int(x["stable"]), -abs(x["diff"])))
    return res


print("\n## mixed TAKE leaves (n ≥ 30, good%% within ±10 of the base %.0f%%) — the best stable single split" % (100 * base_good))
out_split = {}
for k, rs in sorted(fam.items(), key=lambda kv: -len(kv[1])):
    n, g, b, fl, gp = st(rs)
    if not k.startswith("TAKE") or n < 30 or abs(gp - base_good) > 0.10:
        continue
    sp = best_splits(rs, args.min)
    out_split[k] = sp[:5]
    print("\n%s  n=%d good=%.0f%%" % (k, n, 100 * gp))
    for x in sp[:4]:
        print("   %s=%s: n=%d good=%d%% · rest n=%d good=%d%% · Δ%+d · halves %s · %s" % (
            x["feat"], x["val"], x["nS"], x["gS"], x["nT"], x["gT"], x["diff"], x["halves"], "STABLE" if x["stable"] else "unstable"))

print("\n## SKIP leaves that hold good candidates (good%% ≥ base+5, n ≥ 30) — the best stable split inside")
for k, rs in sorted(fam.items(), key=lambda kv: -len(kv[1])):
    n, g, b, fl, gp = st(rs)
    if not k.startswith("SKIP") or n < 30 or gp < base_good + 0.05:
        continue
    sp = best_splits(rs, args.min)
    out_split[k] = sp[:5]
    print("\n%s  n=%d good=%.0f%%" % (k, n, 100 * gp))
    for x in sp[:3]:
        print("   %s=%s: n=%d good=%d%% · rest n=%d good=%d%% · Δ%+d · halves %s · %s" % (
            x["feat"], x["val"], x["nS"], x["gS"], x["nT"], x["gT"], x["diff"], x["halves"], "STABLE" if x["stable"] else "unstable"))

print("\n## rule A on all TAKE candidates")
T = [r for r in rows if r["leaf"] == "TAKE"]
for v in ("accepted_against", "no", "ib_forming"):
    S = [r for r in T if r["f"].get("ruleA") == v]
    if S:
        n, g, b, fl, gp = st(S); print("ruleA=%s: n=%d good=%d bad=%d flat=%d good%%=%.0f" % (v, n, g, b, fl, 100 * gp))
if args.json:
    json.dump(dict(base=dict(n=N, good=base["good"], bad=base["bad"], flat=base["flat"]), families=out_fam, splits=out_split,
                   sessions=[days[0], days[-1], len(days)]), open(args.json, "w"), ensure_ascii=False, indent=1, default=str)
if args.rows:
    json.dump(dict(days=days, rows=rows), open(args.rows, "w"), ensure_ascii=False, default=str)
