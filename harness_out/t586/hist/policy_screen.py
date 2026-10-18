#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-registered DOCTRINE policies (charter s4b, 18.10 19:5x) screened at the candidate level with a single-slot
re-simulation, per regime. A screen, not a verdict: the harness (hist_*) is the only number for a ruling — hist_k showed
the candidate level is optimistic because a freed slot takes other trades. Policies are fixed here, not fitted:
  base  the live tree as it is (fixed_leaf TAKE)
  P1    BREAK only on an initiative opening (OPEN_DRIVE / OPEN_TEST_DRIVE)
  P3    no BREAK in phase D (after 13:00 ET)
  P4    REVERSAL only at a value reference (zone in near_val / near_vah / above_value / below_value)
  P5    EDGE_FADE only under a balance label (Normal / Neutral_* / Nontrend)
  D     drive-only (WITH_DRIVE + PULLBACK)                 K  no REVERSAL / EDGE_FADE
  P1+P4+P5, D+P1
usage: policy_screen.py <cand.csv> [more.csv ...]"""
import sys, pandas as pd, numpy as np, collections
POL = {
    "base": lambda r: True,
    "P1 BREAK only on initiative opening": lambda r: r.kind != "BREAK" or r.opening_type in ("OPEN_DRIVE", "OPEN_TEST_DRIVE"),
    "P3 no BREAK in phase D": lambda r: not (r.kind == "BREAK" and r.phase == "D"),
    "P4 REVERSAL only at a value reference": lambda r: r.kind != "REVERSAL" or r.zone in ("near_val", "near_vah", "above_value", "below_value"),
    "P5 EDGE_FADE only under balance label": lambda r: r.kind != "EDGE_FADE" or str(r.day_type).split("_")[0] in ("Normal", "Neutral", "Nontrend"),
    "D drive-only": lambda r: r.kind in ("WITH_DRIVE", "PULLBACK"),
    "K no REVERSAL/EDGE_FADE": lambda r: r.kind not in ("REVERSAL", "EDGE_FADE"),
}
POL["P1+P4+P5"] = lambda r: POL["P1 BREAK only on initiative opening"](r) and POL["P4 REVERSAL only at a value reference"](r) and POL["P5 EDGE_FADE only under balance label"](r)
POL["D+P1 (drive-only + initiative breaks)"] = lambda r: r.kind in ("WITH_DRIVE", "PULLBACK") or (r.kind == "BREAK" and r.opening_type in ("OPEN_DRIVE", "OPEN_TEST_DRIVE"))
def slot_sim(df):
    """single slot per session in time order: a candidate is taken when no trade is open (open = fire il .. exit il)."""
    out = {}
    for s, g in df.groupby("session"):
        busy = ""; net = 0.0; n = 0
        for r in g.sort_values("il").itertuples():
            if str(r.il) < busy: continue
            net += float(r.net); n += 1; busy = str(r.exit_il) if isinstance(r.exit_il, str) else "99:99"
        out[s] = (net, n)
    return out
def stats(days, all_sessions):
    nets = [days.get(s, (0.0, 0))[0] for s in all_sessions]; months = collections.defaultdict(float)
    for s, v in zip(all_sessions, nets): months[s[:7]] += v
    eq = peak = dd = 0.0
    for v in nets: eq += v; peak = max(peak, eq); dd = max(dd, peak - eq)
    w10 = min(sum(nets[i:i + 10]) for i in range(max(1, len(nets) - 9)))
    return dict(net=sum(nets), trades=sum(days.get(s, (0, 0))[1] for s in all_sessions), per_day=sum(nets) / len(nets), m_ok=sum(1 for v in months.values() if v >= 0), m=len(months), dd=dd, w10=w10)
for f in sys.argv[1:]:
    C = pd.read_csv(f); sessions = sorted(C.session.unique())
    # live-eligible universe (as t1_cells.py): tree TAKE, no gate block, not shadow-only, taken or blocked only by the slot
    elig = C.blocked_by.fillna("").astype(str).isin(["", "nan"]) & (C.shadow_only == 0) & ((C.taken == 1) | (C.live_blocked_by.fillna("") == "live_slot_occupied"))
    C = C[(C.fixed_leaf == "TAKE") & elig].copy()
    print(f"\n{f.split('/')[-1]}: {len(sessions)} sessions with TAKE candidates, {len(C)} TAKE candidates")
    print(f"{'policy':44s} {'trades':>6s} {'Σnet$':>9s} {'$/day':>6s} {'mon≥0':>6s} {'maxDD':>7s} {'w10':>7s}")
    for name, fn in POL.items():
        st = stats(slot_sim(C[C.apply(fn, axis=1)]), sessions)
        print(f"{name:44s} {st['trades']:6d} {st['net']:+9.0f} {st['per_day']:+6.1f} {st['m_ok']:3d}/{st['m']:<2d} {st['dd']:7.0f} {st['w10']:+7.0f}")
