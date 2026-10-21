# -*- coding: utf-8 -*-
"""Harness noise check: days where two runs differ although the variant's switch could not have acted.
usage: python3 harness_out/t621/t622_noise.py <ref> <var> <mode>
  mode dt   : the variant only touches DOUBLE_TOP*/DOUBLE_BOTTOM* setups (DOUBLE_TOP_STRUCT_STOP_V1=dt)
  mode leaf:<id> : the variant only acts where a route took tree leaf <id> (e.g. leaf:normal_failed_ext_far)"""
import json
import os
import sys

D = "/Users/michael/Downloads/mems26_web_git/harness_out/t621/days"
ref, var, mode = sys.argv[1], sys.argv[2], sys.argv[3]


def load(tag, day):
    p = os.path.join(D, f"{tag}_{day}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def sig(d):
    return [(t["fired_il"][:5], t["classification"], t["direction"], t["entry"], t["pnl_usd"])
            for t in d["trades"] if t.get("pnl_usd") is not None]


days = sorted(f[len(ref) + 1:-5] for f in os.listdir(D) if f.startswith(ref + "_2026") and f.endswith(".json"))
n_diff = n_noise = 0
noise_usd = 0.0
for day in days:
    a, b = load(ref, day), load(var, day)
    if not a or not b:
        continue
    sa, sb = sig(a), sig(b)
    if sa == sb:
        continue
    n_diff += 1
    if mode == "dt":
        touched = any(str(r.get("classification", "")).startswith(("DOUBLE_TOP", "DOUBLE_BOTTOM"))
                      for d in (a, b) for r in d["routes"] if not r.get("blocked_by"))
    else:
        lid = mode.split(":", 1)[1]
        touched = any((r.get("tree_v3") or {}).get("id") == lid for r in b["routes"])
    if not touched:
        n_noise += 1
        da = sum(x[4] for x in sa)
        db = sum(x[4] for x in sb)
        noise_usd += db - da
        print(f"NOISE? {day} Δ {db - da:+.2f}")
        print("   ", ref, [x for x in sa if x not in sb])
        print("   ", var, [x for x in sb if x not in sa])
print(f"{ref} vs {var}: {n_diff} days differ · {n_noise} with no possible cause · Σ noise {noise_usd:+.2f}$")
