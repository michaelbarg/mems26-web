#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-515 (29.09): every variant vs the SAME-DAY reference (history tables drift between days) — the day-total, the exits
(TURN = left because the turn flipped against it), the leaves the live trades came from, and 28.09 in full.
usage: report.py [--ref t515ref] TAG [TAG ...]"""
import collections, glob, json, os, sys
D = "harness_out/t466"; COMM = 2.60
args = sys.argv[1:]; REF = "t515ref"
if "--ref" in args:
    i = args.index("--ref"); REF = args[i + 1]; del args[i:i + 2]


def load(tag):
    out = {}
    for p in glob.glob(f"{D}/{tag}_2026-*.json"):
        d = os.path.basename(p)[len(tag) + 1:len(tag) + 11]
        try:
            out[d] = json.load(open(p))
        except Exception:
            continue
    return out


def pnl(j):
    return float(j.get("daily_pnl_harness") or 0)


ref = load(REF)
for tag in args:
    v = load(tag); common = sorted(set(v) & set(ref))
    if not common:
        print(tag, "— no common sessions with", REF); continue
    s0 = sum(pnl(ref[d]) for d in common); s1 = sum(pnl(v[d]) for d in common)
    n0 = sum(len(ref[d]["trades"]) for d in common); n1 = sum(len(v[d]["trades"]) for d in common)
    better = sum(1 for d in common if pnl(v[d]) > pnl(ref[d]) + .01); worse = sum(1 for d in common if pnl(v[d]) < pnl(ref[d]) - .01)
    w1 = sum(1 for d in common for t in v[d]["trades"] if float(t.get("pnl_usd") or 0) > 0)
    ex, exs = collections.Counter(), collections.defaultdict(float)
    lv, lvs = collections.Counter(), collections.defaultdict(float)
    for d in common:
        tid = {t["trade_id"]: t for t in v[d]["trades"]}
        for t in v[d]["trades"]:
            k = next((str(l.get("exit")) for l in t.get("legs", []) if str(l.get("exit", "")).startswith("TURN")), str(t.get("outcome")))
            ex[k] += 1; exs[k] += float(t.get("pnl_usd") or 0)
        for g in v[d]["gateway_decisions"]:
            if g.get("outcome") == "live" and g.get("trade_id") in tid:
                lid = str((g.get("tree_v3") or {}).get("id"))
                key = lid if lid.startswith("with_turn") or lid in ("against_turn", "range_mid", "range_edge") else "legacy"
                lv[key] += 1; lvs[key] += float(tid[g["trade_id"]].get("pnl_usd") or 0)
    miss = sorted(set(ref) - set(v))
    print(f"{tag} vs {REF}: {len(common)}d · trades {n1} (ref {n0}) · win {100 * w1 / max(1, n1):.0f}% · Σ {s1:+.2f}$ (ref {s0:+.2f}$) · "
          f"Δ gross {s1 - s0:+.2f}$ · Δ net {(s1 - COMM * n1) - (s0 - COMM * n0):+.2f}$ · better {better} / worse {worse}"
          + (f" · missing {' '.join(miss)}" if miss else ""))
    print("   exits:  " + " · ".join(f"{k} {ex[k]} {exs[k]:+.0f}$" for k in sorted(ex)))
    print("   leaves: " + " · ".join(f"{k} {lv[k]} {lvs[k]:+.0f}$" for k in sorted(lv)))
    for d in ("2026-09-28",):
        if d in v:
            print(f"   {d[5:]}: {pnl(v[d]):+.2f}$ (ref {pnl(ref.get(d, {})):+.2f}$)")
            for t in v[d]["trades"]:
                print(f"      {str(t.get('fired_il', ''))[:5]} {t.get('classification')} {t.get('direction')} @{t.get('entry')} "
                      f"{t.get('outcome')} {[l.get('exit') for l in t.get('legs', [])]} out {t.get('exit_il')} {float(t.get('pnl_usd') or 0):+.2f}$")
    print()
