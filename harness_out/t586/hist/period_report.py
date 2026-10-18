#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-586 — out-of-sample report of a harness tag by period (quarter/month), rolling windows, by kind.
usage: period_report.py <TAG> [--by=quarter|month] [--vs=<REF_TAG>]"""
import json, glob, sys, os, collections
TAG = next(a for a in sys.argv[1:] if not a.startswith("--"))
BY = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--by=")), "quarter")
VS = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--vs=")), None)
COMM = 2.60
def load(tag):
    out = {}
    for f in sorted(glob.glob(f"harness_out/t466/{tag}_20*.json")):
        j = json.load(open(f)); n = len(j.get("trades") or [])
        out[j["session"]] = (float(j.get("daily_pnl_harness") or 0) - COMM * n, n, j.get("trades") or [], j)
    return out
A = load(TAG); B = load(VS) if VS else None
def period(s):
    y, m = s[:4], int(s[5:7]); return s[:7] if BY == "month" else f"{y}-Q{(m - 1) // 3 + 1}"
nets = [A[s][0] for s in sorted(A)]; ses = sorted(A)
print(f"{TAG}: {len(A)} sessions {ses[0]}..{ses[-1]} · Σ net {sum(nets):+.2f}$ · {sum(A[s][1] for s in A)} trades · "
      f"{sum(1 for n in nets if n > 0)}+/{sum(1 for n in nets if n < 0)}− · mean/day {sum(nets)/len(nets):+.2f}$")
per = collections.defaultdict(lambda: [0, 0.0, 0, 0])
for s in ses:
    p = per[period(s)]; p[0] += 1; p[1] += A[s][0]; p[2] += A[s][1]; p[3] += sum(1 for t in A[s][2] if float(t.get("pnl_usd") or 0) > 0)
print(f"{'period':9s} {'days':>4s} {'Σnet':>9s} {'$/day':>7s} {'trades':>6s} {'win%':>5s}" + (f"  | {VS} Σnet   Δ" if B else ""))
for k in sorted(per):
    d, n, tr, w = per[k]
    extra = ""
    if B:
        bn = sum(B[s][0] for s in ses if period(s) == k and s in B); extra = f"  | {bn:+9.2f} {n - bn:+8.2f}"
    print(f"{k:9s} {d:4d} {n:+9.2f} {n/d:+7.2f} {tr:6d} {100*w/max(1,tr):5.0f}{extra}")
for W in (5, 10, 20):
    w = [sum(nets[i:i + W]) for i in range(len(nets) - W + 1)]
    if w:
        print(f"rolling {W:2d}: negative {sum(1 for x in w if x < 0)}/{len(w)} ({100*sum(1 for x in w if x < 0)/len(w):.0f}%) · min {min(w):+.0f} · median {sorted(w)[len(w)//2]:+.0f}")
eq = pk = dd = 0.0
for n in nets:
    eq += n; pk = max(pk, eq); dd = max(dd, pk - eq)
print(f"max closed-day DD {dd:.2f}$ · final {eq:+.2f}$")
kind = collections.defaultdict(lambda: [0, 0.0, 0])
for s in ses:
    j = A[s][3]; rt = {str(((r.get("exec") or {}).get("live") or {}).get("trade_id")): r for r in j.get("routes") or []}
    for t in A[s][2]:
        v = ((rt.get(str(t["trade_id"])) or {}).get("tree_v3") or {}).get("vec") or {}
        k = kind[v.get("kind") or "?"]; k[0] += 1; k[1] += float(t.get("pnl_usd") or 0); k[2] += 1 if float(t.get("pnl_usd") or 0) > 0 else 0
print("by kind (gross): " + " · ".join(f"{k} {v[0]} {v[1]:+.0f}$ {100*v[2]/v[0]:.0f}%" for k, v in sorted(kind.items(), key=lambda kv: -kv[1][1])))
