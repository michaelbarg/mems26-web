# -*- coding: utf-8 -*-
"""T-621 stage 3b — each root fix vs the base re-run with the same (faithful, T-620) harness, on the sessions both have.
Σ$ = the harness's settled trades (pnl_usd); net = gross − 2.60$ × Δtrades. Descriptive only — Michael decides.
usage: python3 harness_out/t621/compare_days.py [tag …]   → table + compare_days.json"""
import collections
import glob
import json
import os
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "days")
BASE = "base"
TAGS = sys.argv[1:] or ["fx1", "fx2", "fx3", "fx4", "fx5", "fx24", "fxall"]
RT = 2.60


def load(tag):
    res = {}
    for p in glob.glob(os.path.join(OUT, f"{tag}_*.json")):
        d = os.path.basename(p)[len(tag) + 1:-5]
        if len(d) != 10:
            continue
        try:
            j = json.load(open(p))
        except Exception:
            continue
        tr = [t for t in (j.get("trades") or []) if t.get("pnl_usd") is not None]
        res[d] = {"usd": round(sum(float(t["pnl_usd"]) for t in tr), 2), "n": len(tr),
                  "flips": (j.get("flip_runner") or {}).get("flipped", 0),
                  "trades": [(t.get("fired_il"), t.get("classification"), t.get("direction"), t.get("pnl_usd"))
                             for t in tr]}
    return res


base = load(BASE)
report = {"base": BASE, "sessions_base": len(base), "base_usd": round(sum(v["usd"] for v in base.values()), 2),
          "variants": {}}
print(f"base: {len(base)} sessions · Σ {report['base_usd']:+.2f}$ · trades {sum(v['n'] for v in base.values())}")
for tag in TAGS:
    var = load(tag)
    common = sorted(set(base) & set(var))
    if not common:
        print(f"{tag}: no common sessions yet")
        continue
    d_usd = {d: round(var[d]["usd"] - base[d]["usd"], 2) for d in common}
    d_n = sum(var[d]["n"] - base[d]["n"] for d in common)
    gross = round(sum(d_usd.values()), 2)
    net = round(gross - RT * d_n, 2)
    hold = common[-10:]
    by_month = collections.OrderedDict()
    for d in common:
        by_month[d[:7]] = round(by_month.get(d[:7], 0.0) + d_usd[d], 2)
    better = sum(1 for v in d_usd.values() if v > 0.005)
    worse = sum(1 for v in d_usd.values() if v < -0.005)
    top = sorted(d_usd.items(), key=lambda kv: kv[1])
    report["variants"][tag] = {
        "sessions": len(common), "base_usd": round(sum(base[d]["usd"] for d in common), 2),
        "var_usd": round(sum(var[d]["usd"] for d in common), 2), "gross": gross, "net": net, "d_trades": d_n,
        "last10": round(sum(d_usd[d] for d in hold), 2), "by_month": by_month, "better": better, "worse": worse,
        "same": len(common) - better - worse, "flips": sum(var[d]["flips"] for d in common),
        "worst5": top[:5], "best5": top[-5:][::-1], "d_2010": d_usd.get("2026-10-20")}
    print(f"{tag}: N={len(common)} · base {report['variants'][tag]['base_usd']:+.2f} → {report['variants'][tag]['var_usd']:+.2f} "
          f"· Δ {gross:+.2f}$ gross / {net:+.2f}$ net · Δtrades {d_n:+d} · last10 {report['variants'][tag]['last10']:+.2f} "
          f"· better {better} / worse {worse} · months " + " · ".join(f"{m[5:]} {v:+.0f}" for m, v in by_month.items()))
    print("   worst:", ", ".join(f"{d} {v:+.0f}" for d, v in top[:5]), "| best:",
          ", ".join(f"{d} {v:+.0f}" for d, v in top[-5:][::-1]))
json.dump(report, open(os.path.join(os.path.dirname(OUT), "compare_days.json"), "w"), indent=1, default=str)
