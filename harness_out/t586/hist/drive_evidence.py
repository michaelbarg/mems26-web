#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The tree's drive family (WITH_DRIVE / PULLBACK TAKE leaves — the only family >= 0 in both samples, report s8.6) against
order-flow evidence known at fire time: Σ delta from the RTH open to the fire bar, signed by the trade direction
(E1: with the trade), and the fire bar's own delta (E2). Conditions fixed in advance; per sample (OOS 2025-10→2026-05 /
in-sample 2026-06→10). usage: drive_evidence.py <cand_alltake_all.csv> [--db=mems26_hist]"""
import sys, subprocess, collections, pandas as pd, numpy as np
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--")}
DB = opt.get("db", "mems26_hist")
def q(sql): return subprocess.run([PSQL, "-d", DB, "-Atc", sql], capture_output=True, text=True).stdout.strip().splitlines()
D = collections.defaultdict(list)       # session -> [(il, delta)] in RTH order
for line in q("select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), delta from v9_bars_cumulative_delta "
              "where (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts, case when source_version='hist' then 0 else 1 end"):
    d, il, dl = line.split("|")
    if dl in ("", "None") or (D[d] and D[d][-1][0] == il): continue
    D[d].append((il, float(dl)))
C = pd.read_csv(args[0])
U = C[(C.kind.isin(["WITH_DRIVE", "PULLBACK"])) & (C.fixed_leaf == "TAKE")].copy()
def ev(r):
    rows = D.get(r.session) or []; il = str(r.il)[:5]; sec = str(r.il)[6:8]
    upto = [dl for t, dl in rows if t < il]; bar = next((dl for t, dl in rows if t == il), None)   # bars closed before the fire bar; the fire bar itself
    sgn = 1 if str(r.direction).upper().startswith("L") else -1
    # known at fire time: a fire on the first push (:03) knows only the PREVIOUS bar's delta; a fire on the closing push (:58) knows (almost) the fire bar's
    known = (bar if sec >= "30" else (upto[-1] if upto else None))
    return pd.Series({"d_open": sum(upto) if upto else np.nan, "e1": (int(sgn * sum(upto) > 0) if upto else np.nan), "e2": (np.nan if bar is None else int(sgn * bar > 0)),
                      "e2k": (np.nan if known is None else int(sgn * known > 0)), "first_push": int(sec < "30")})
U = pd.concat([U, U.apply(ev, axis=1)], axis=1)
U["sample"] = np.where(U.session < "2026-06-01", "OOS", "in-sample"); U["t1"] = (U.exit == "T1").astype(int)
def row(g, name): return {"cond": name, "n": len(g), "taken": int(g.taken.sum()), "T1%": round(100 * g.t1.mean()) if len(g) else None, "E$": round(g.net.mean(), 1) if len(g) else None, "Σ$": round(g.net.sum()) if len(g) else None}
for smp, g in U.groupby("sample"):
    print(f"\n{smp}: drive-family TAKE candidates n={len(g)} (taken by the single slot {int(g.taken.sum())}), delta known for {int(g.e1.notna().sum())}")
    conds = [("all", g), (f"fired on the first push (:03) — fire-bar delta NOT known", g[g.first_push == 1]),
             ("E1 Σdelta open→fire with trade", g[g.e1 == 1]), ("¬E1 against", g[g.e1 == 0]),
             ("E2 fire-bar delta with trade (LOOKAHEAD on :03 fires)", g[g.e2 == 1]), ("¬E2", g[g.e2 == 0]),
             ("E2k last-CLOSED-bar delta with trade (known at fire)", g[g.e2k == 1]), ("¬E2k", g[g.e2k == 0]),
             ("E1 & E2k", g[(g.e1 == 1) & (g.e2k == 1)]), ("taken only", g[g.taken == 1]), ("taken & E2k", g[(g.taken == 1) & (g.e2k == 1)]), ("taken & ¬E2k", g[(g.taken == 1) & (g.e2k == 0)])]
    print(pd.DataFrame([row(x, n) for n, x in conds]).to_string(index=False))
