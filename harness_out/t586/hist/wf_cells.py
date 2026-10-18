#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-586 — walk-forward CELL policy on the candidate dataset (cand_sim.py output), slot-aware (one trade at a time per
session, a candidate is admitted only when no simulated trade is open). For each month M the policy is learned on
every candidate BEFORE M (cells with n >= N_MIN: TAKE iff mean net > 0; smaller cells: the fixed tree's own leaf) and
applied to M — so every month's number is out-of-sample for the policy. Universe = candidates that passed every
post-tree gate (the gates stay as they are). Printed next to FIXED (the live tree's own TAKE leaves = the system) and
ALL (every gate-passed candidate regardless of the tree), all slot-aware with the same simulator.
usage: wf_cells.py <cand.csv> [--nmin=20] [--key=opening_type,phase,day_type,kind,rel_bias]"""
import sys, pandas as pd, numpy as np, collections
f = next(a for a in sys.argv[1:] if not a.startswith("--"))
NMIN = int(next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--nmin=")), "20"))
KEY = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--key=")), "opening_type,phase,day_type,kind,rel_bias").split(",")
df = pd.read_csv(f).fillna({"kind": "?", "opening_type": "?", "phase": "?", "day_type": "?", "rel_bias": "?", "zone": "?"})
df["cell"] = df[KEY].astype(str).agg("|".join, axis=1); df["month"] = df["session"].str[:7]
df["m"] = df["il"].str[:2].astype(int) * 60 + df["il"].str[3:5].astype(int)
df["xm"] = df["exit_il"].astype(str).str[:2].astype(int) * 60 + df["exit_il"].astype(str).str[3:5].astype(int)
df["gate_ok"] = df["blocked_by"].fillna("").astype(str).isin(["", "nan"]) & (df.get("shadow_only", 0) == 0) & ((df.taken == 1) | (df.get("live_blocked_by", pd.Series("", index=df.index)).fillna("") == "live_slot_occupied"))
if "r_pts" in df: df = df[(df.r_pts > 0) & (df.r_pts <= 20)]
df = df.sort_values(["session", "m"]).reset_index(drop=True)
def slot_sum(sub, admit):
    """sequential one-slot simulation: admit(row) -> bool; returns (net, n) per session summed."""
    tot = 0.0; n = 0
    for s, g in sub.groupby("session", sort=True):
        busy_until = -1
        for r in g.itertuples():
            if r.m < busy_until: continue
            if not admit(r): continue
            tot += r.net; n += 1; busy_until = max(r.xm, r.m + 5)
    return tot, n
months = sorted(df["month"].unique())
print(f"{len(df)} candidates · {df.session.nunique()} sessions · months {months[0]}..{months[-1]} · key={KEY} nmin={NMIN}")
print(f"{'month':8s} {'sess':>4s} | {'FIXED tree':>14s} | {'WF cells':>14s} | {'ALL':>14s} | cells learned")
tot = collections.defaultdict(float)
for M in months:
    train = df[df["month"] < M]; test = df[df["month"] == M]
    st = train.groupby("cell")["net"].agg(["count", "mean"])
    good = set(st[(st["count"] >= NMIN) & (st["mean"] > 0)].index); known = set(st[st["count"] >= NMIN].index)
    # universe = candidates that passed every post-tree gate (blocked only by the slot, or not at all); the gates stay.
    fx = slot_sum(test, lambda r: (getattr(r, "fixed_leaf", r.leaf) == "TAKE") and r.gate_ok)
    wf = slot_sum(test, lambda r: r.gate_ok and ((r.cell in good) if r.cell in known else (r.leaf == "TAKE")))
    al = slot_sum(test, lambda r: r.gate_ok)
    tot["fx"] += fx[0]; tot["wf"] += wf[0]; tot["al"] += al[0]
    print(f"{M:8s} {test.session.nunique():4d} | {fx[0]:+8.0f} ({fx[1]:3d}) | {wf[0]:+8.0f} ({wf[1]:3d}) | {al[0]:+8.0f} ({al[1]:3d}) | {len(known)} known, {len(good)} TAKE")
print(f"TOTAL          | {tot['fx']:+8.0f}       | {tot['wf']:+8.0f}       | {tot['al']:+8.0f}")
