#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""5-contract ladders on the tree's DRIVE family (WITH_DRIVE + PULLBACK TAKE leaves), per regime, from cand_sim rows
(mfe_r, t2_hit, be_after_t1, pts). The live ladder for 5 is (1@T0=3pts, 2@T1, 1@T2, 1@T3≈T2) with the stop moved to BE
only after T1 (as the harness). Alternatives, fixed in advance: all 5 at T1 · (3@T0, 2@T1) · (2@T0, 3@T1) · 1 contract.
usage: drive_ladder.py <cand.csv> [more.csv ...]"""
import sys, pandas as pd, numpy as np
PT, COMM, T0 = 5.0, 2.6, 3.0
for f in sys.argv[1:]:
    C = pd.read_csv(f)
    elig = C.blocked_by.fillna("").astype(str).isin(["", "nan"]) & (C.shadow_only == 0) & ((C.taken == 1) | (C.live_blocked_by.fillna("") == "live_slot_occupied"))
    U = C[(C.fixed_leaf == "TAKE") & elig & C.kind.isin(["WITH_DRIVE", "PULLBACK"]) & (C.r_pts > 0)].copy()
    U["mfe_pts"] = U.mfe_r * U.r_pts; U["t1hit"] = (U.exit == "T1").astype(int)
    U["t1_dist"] = np.maximum(np.abs(U.t1.fillna(U.entry) - U.entry), 1.5 * U.r_pts); U["t2_dist"] = 2 * U.t1_dist
    loss = U.pts * PT                                          # recorded 1-contract outcome (stop / EOD) in $
    c0 = np.where(U.mfe_pts >= T0, T0 * PT, loss)             # a contract targeting +3
    c1 = np.where(U.t1hit == 1, U.t1_dist * PT, loss)         # a contract targeting T1
    c2 = np.where(U.t1hit == 1, np.where(U.t2_hit == 1, U.t2_dist * PT, 0.0), loss)   # a contract targeting T2, BE after T1
    lad = {"1 contract @T1": c1 - COMM, "5 live ladder (1@T0,2@T1,1@T2,1@T3≈T2)": c0 + 2 * c1 + 2 * c2 - 5 * COMM,
           "5 all @T1": 5 * c1 - 5 * COMM, "5 = 3@T0 + 2@T1": 3 * c0 + 2 * c1 - 5 * COMM, "5 = 2@T0 + 3@T1": 2 * c0 + 3 * c1 - 5 * COMM, "5 all @T0 (scalp)": 5 * c0 - 5 * COMM}
    print(f"\n{f.split('/')[-1]}: drive-family live-eligible candidates n={len(U)} (taken {int(U.taken.sum())}), T0 {100 * (U.mfe_pts >= T0).mean():.0f}%, T1 {100 * U.t1hit.mean():.0f}%, "
          f"T2|T1 {100 * U[U.t1hit == 1].t2_hit.mean():.0f}%, R median {U.r_pts.median():.1f}")
    for k, v in lad.items():
        v = pd.Series(v, index=U.index); print(f"  {k:42s} E {v.mean():+7.1f}$/trade  Σ {v.sum():+8.0f}$  worst {v.min():+7.0f}$  taken-only Σ {v[U.taken == 1].sum():+8.0f}$")
