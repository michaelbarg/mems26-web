# -*- coding: utf-8 -*-
"""Night 20→21.10 — T-616 variants vs the same-night base2010, on the sessions both have (BRIEF §2 acceptance rule:
holdout (last 10 sessions) ≥ 0 AND Δnet > 0 on the whole set AND every month ≥ 0; small N is a caveat).
Σ$ = the harness's settled trades (pnl_usd, 1 contract per the harness ladder); net = gross − 2.60$ × Δtrades.
usage: python3 harness_out/base2010/compare_t616.py [tag …]   → prints a table + writes compare_t616.json"""
import glob, json, os, sys, collections
OUT = os.path.dirname(os.path.abspath(__file__))
BASE = "base2010"
TAGS = sys.argv[1:] or ["t616saa", "t616drv", "t616edge", "t616nocap", "t617t2", "t616all", "t617all"]
RT = 2.60


def load(tag):
    res = {}
    for p in glob.glob(os.path.join(OUT, f"hist_{tag}_*.json")):
        d = os.path.basename(p)[len(f"hist_{tag}_"):-5]
        try:
            j = json.load(open(p))
        except Exception:
            continue
        tr = [t for t in (j.get("trades") or []) if t.get("pnl_usd") is not None]
        res[d] = {"usd": round(sum(float(t["pnl_usd"]) for t in tr), 2), "n": len(tr),
                  "ids": sorted((t.get("fired_il") or "", t.get("classification") or "", t.get("direction") or "")
                                for t in tr),
                  "be_rule": j.get("be_rule"), "t595": j.get("t595")}
    return res


base = load(BASE)
report = {"base": BASE, "sessions_base": len(base), "variants": {}}
print(f"base {BASE}: {len(base)} sessions · Σ {sum(v['usd'] for v in base.values()):+.2f}$ · "
      f"trades {sum(v['n'] for v in base.values())}")
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
    hold_usd = round(sum(d_usd[d] for d in hold), 2)
    by_month = collections.OrderedDict()
    for d in common:
        by_month[d[:7]] = round(by_month.get(d[:7], 0.0) + d_usd[d], 2)
    better = sum(1 for v in d_usd.values() if v > 0.005)
    worse = sum(1 for v in d_usd.values() if v < -0.005)
    accept = hold_usd >= 0 and net > 0 and all(v >= 0 for v in by_month.values())
    top = sorted(d_usd.items(), key=lambda kv: kv[1])
    report["variants"][tag] = {"sessions": len(common), "gross": gross, "net": net, "d_trades": d_n,
                               "holdout10": hold_usd, "by_month": by_month, "better": better, "worse": worse,
                               "same": len(common) - better - worse, "accept": accept,
                               "worst3": top[:3], "best3": top[-3:][::-1],
                               "base_usd": round(sum(base[d]["usd"] for d in common), 2),
                               "var_usd": round(sum(var[d]["usd"] for d in common), 2)}
    print(f"{tag}: N={len(common)} · Δ {gross:+.2f}$ gross / {net:+.2f}$ net · Δtrades {d_n:+d} · holdout10 "
          f"{hold_usd:+.2f} · better {better} / worse {worse} · months "
          + " · ".join(f"{m[5:]} {v:+.0f}" for m, v in by_month.items())
          + f" · {'PASS' if accept else 'FAIL'} the acceptance rule")
    print("   worst:", ", ".join(f"{d} {v:+.0f}" for d, v in top[:3]), "| best:",
          ", ".join(f"{d} {v:+.0f}" for d, v in top[-3:][::-1]))
json.dump(report, open(os.path.join(OUT, "compare_t616.json"), "w"), indent=1, default=str)
