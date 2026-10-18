# -*- coding: utf-8 -*-
"""T-598 — where the Δ of BE_AFTER_MFE_R_V1 comes from: per trade (matched by classification+direction+fired_il
between t598be and t598ref), per month, train (≤ t−10) / holdout-10 / whole set; and the chain effect (trades that
exist only on one side because the slot freed at a different time). Read-only on harness_out/t466.
usage: python3 harness_out/t598/decompose.py [TAG=t598be] [REF=t598ref]"""
import collections, glob, json, os, sys
TAG = sys.argv[1] if len(sys.argv) > 1 else "t598be"
REF = sys.argv[2] if len(sys.argv) > 2 else "t598ref"
D = "harness_out/t466"
def load(tag, s):
    p = f"{D}/{tag}_{s}.json"
    return json.load(open(p)) if os.path.exists(p) else None
def key(t): return (t["classification"], t["direction"], t["fired_il"])
def pnl(ts): return sum(float(t.get("pnl_usd") or 0) for t in ts)
def exit_of(t): return "/".join(str(l["exit"]) for l in t["legs"])
sessions = sorted(os.path.basename(f)[len(TAG) + 1:][:10] for f in glob.glob(f"{D}/{TAG}_2026-*.json"))
common = [s for s in sessions if load(REF, s) is not None]
hold = common[-10:]; train = common[:-10]
cat = collections.Counter(); catn = collections.Counter(); rows = []
tot = collections.defaultdict(float); months = collections.Counter(); moved = checked = 0
for s in common:
    a, r = load(TAG, s), load(REF, s)
    ta, tr = {key(t): t for t in a["trades"]}, {key(t): t for t in r["trades"]}
    d = pnl(a["trades"]) - pnl(r["trades"])
    tot["all"] += d; tot["hold" if s in hold else "train"] += d; months[s[:7]] += d
    st = a.get("be_after_mfe") or {}; moved += st.get("moved", 0); checked += st.get("checked", 0)
    for k in set(ta) | set(tr):
        x, y = ta.get(k), tr.get(k)
        if x and y:
            dd = float(x["pnl_usd"] or 0) - float(y["pnl_usd"] or 0)
            if abs(dd) < 1e-9: continue
            ex, ey = exit_of(x), exit_of(y)
            c = ("BE-saved (ref STOP → BE)" if ex == "BE" and ey.startswith("STOP") else
                 "BE-cost (ref target → BE)" if ex == "BE" and ey.startswith("T") else
                 "BE-vs-EOD" if ex == "BE" else f"other {ey}→{ex}")
            cat[c] += dd; catn[c] += 1
            rows.append((s, k[0], k[1], k[2], ey, ex, round(float(y["pnl_usd"] or 0), 2), round(float(x["pnl_usd"] or 0), 2), round(dd, 2)))
        elif x:
            cat["chain: only in variant"] += float(x["pnl_usd"] or 0); catn["chain: only in variant"] += 1
            rows.append((s, k[0], k[1], k[2], "—", exit_of(x), None, round(float(x["pnl_usd"] or 0), 2), round(float(x["pnl_usd"] or 0), 2)))
        else:
            cat["chain: only in reference"] -= float(y["pnl_usd"] or 0); catn["chain: only in reference"] += 1
            rows.append((s, k[0], k[1], k[2], exit_of(y), "—", round(float(y["pnl_usd"] or 0), 2), None, round(-float(y["pnl_usd"] or 0), 2)))
print(f"{TAG} vs {REF}: {len(common)} common sessions · train {len(train)} ({train[0]}…{train[-1]}) · holdout {len(hold)} ({hold[0]}…{hold[-1]})")
print(f"Δ gross: all {tot['all']:+.2f}$ · train {tot['train']:+.2f}$ · holdout {tot['hold']:+.2f}$ · BE moves {moved} of {checked} pre-T1 bar-checks")
print("months: " + " · ".join(f"{m[-2:]} {v:+.2f}" for m, v in sorted(months.items())))
for c, v in sorted(cat.items(), key=lambda kv: -abs(kv[1])):
    print(f"  {c:34s} n={catn[c]:3d}  Δ {v:+.2f}$")
print("--- per-trade differences ---")
for r in rows:
    print("  " + " | ".join(str(x) for x in r))
