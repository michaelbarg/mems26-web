#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-586 — candidate-level outcomes for every routed setup of a harness tag (taken or blocked), simulated on the
session's RTH bars exactly like the harness settles a trade (fill at entry if inside the fire bar else at its open;
stop before target on the same bar; EOD at the last close; T1 raised to the 1.5R floor as the live flag does).
Writes <out.csv>: session, il, pattern, direction, kind, opening_type, phase, day_type, rel_bias, zone, leaf, blocked_by,
taken, pts, net, exit. usage: cand_sim.py <out.csv> <TAG> [<TAG> ...]   (bars from mems26_hist)"""
import sys, json, glob, subprocess, io, collections, pandas as pd
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"; import os; DB = os.environ.get("CAND_DB", "mems26_hist")
COMM = 2.60; PT = 5.0; FLOOR_R = 1.5
out = sys.argv[1]; tags = [a for a in sys.argv[2:] if not a.startswith("--")]
# --tree=<yaml>: re-walk THAT tree on every candidate's stored vector → column fixed_leaf (the live tree's own decision,
# needed on an all_take universe where tree_v3.leaf is TAKE for everyone). Default: config/decision_tree_v3.yaml.
TREE_PATH = next((a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("--tree=")), "config/decision_tree_v3.yaml")
sys.path.insert(0, "."); from backend.v9.services import decision_tree as _dt
_TREE = _dt.load_tree(TREE_PATH)
def fixed_leaf(vec):
    try:
        leaf, _ = _dt.walk(_TREE, dict(vec or {})); a = str(leaf.get("leaf") or "SKIP").upper()
        a, leaf = _dt.kind_policy(a, leaf, (vec or {}).get("kind"), os.getenv("TREE_SKIP_KINDS")); return a, str(leaf.get("id") or "")
    except Exception as e:
        return "ERR", str(e)[:40]
raw = subprocess.run([PSQL, "-d", DB, "-Atc", "select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close "
                      "from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts"],
                     capture_output=True, text=True).stdout
BARS = collections.defaultdict(list)
for line in raw.splitlines():
    d, il, o, h, l, c = line.split("|"); BARS[d].append((il, float(o), float(h), float(l), float(c)))
def mins(s): return int(s[:2]) * 60 + int(s[3:5])
def sim(bars, il, direction, entry, stop, t1, floor=True):
    fm = (mins(il) // 5) * 5          # the fired bar = the 5-min bar of the fire minute (second-push fires belong to the bar that just closed, as in the harness)
    idx = next((i for i, b in enumerate(bars) if mins(b[0]) >= fm), None)
    if idx is None: return None
    d = 1 if direction == "LONG" else -1
    o, h, l = bars[idx][1], bars[idx][2], bars[idx][3]
    fill = entry if l <= entry <= h else o
    R = abs(fill - stop) or 0.25
    tgt = fill + d * (max(abs(t1 - fill) if t1 else 0.0, FLOOR_R * R) if floor else (abs(t1 - fill) if t1 else FLOOR_R * R))
    MFE["r"] = 0.0                    # max favorable excursion in R before the stop bar (stop-before-target: the stop bar does not count)
    for i in range(idx, len(bars)):
        _, o, h, l, c = bars[i]
        if (l <= stop) if d == 1 else (h >= stop): return (d * (stop - fill), "STOP", bars[i][0])
        MFE["r"] = max(MFE["r"], d * ((h if d == 1 else l) - fill) / R)
        if (h >= tgt) if d == 1 else (l <= tgt): return (d * (tgt - fill), "T1", bars[i][0])
    return (d * (bars[-1][4] - fill), "EOD", bars[-1][0])
MFE = {"r": 0.0}
rows = []
for tag in tags:
    for f in sorted(glob.glob(f"harness_out/t466/{tag}_20*.json")):
        j = json.load(open(f)); s = j["session"]; bars = BARS.get(s) or []
        if len(bars) < 20: continue
        taken = {str(((r.get("exec") or {}).get("live") or {}).get("trade_id")) for r in j.get("routes") or []}
        pnl_by_tid = {str(t["trade_id"]): float(t.get("pnl_usd") or 0) for t in j.get("trades") or []}
        tr_by_tid = {str(t["trade_id"]): t for t in j.get("trades") or []}
        for r in j.get("routes") or []:
            tv = r.get("tree_v3") or {}; v = tv.get("vec") or {}
            try: entry, stop = float(r.get("entry") or 0), float(r.get("stop") or 0)
            except (TypeError, ValueError): continue
            if entry <= 0 or stop <= 0 or not r.get("direction"): continue
            t1 = float(r.get("t1")) if r.get("t1") not in (None, "", 0) else None
            tid = str(((r.get("exec") or {}).get("live") or {}).get("trade_id"))
            if tid in tr_by_tid:      # taken: the gateway's final stop / T1 (arbitration, floor, structural chain) — exact
                t = tr_by_tid[tid]; entry = float(t.get("fill_price") or t["entry"]); stop = float(t["stop_initial"])
                t1 = float(t.get("t1_target") or 0) or None
            res = sim(bars, r["il"][:5], r["direction"].upper(), entry, stop, t1, floor=(tid not in tr_by_tid))
            if res is None: continue
            rows.append(dict(session=s, il=r["il"][:5], pattern=r.get("classification"), direction=r["direction"], kind=v.get("kind"),
                             opening_type=v.get("opening_type"), phase=v.get("phase"), day_type=v.get("day_type"), rel_bias=v.get("rel_bias"),
                             zone=v.get("zone"), leaf=tv.get("leaf"), leaf_id=tv.get("id"), fixed_leaf=fixed_leaf(v)[0], fixed_id=fixed_leaf(v)[1], blocked_by=r.get("blocked_by") or "",
                             live_blocked_by=r.get("live_blocked_by") or "", taken=int(tid in pnl_by_tid), harness_pnl=pnl_by_tid.get(tid),
                             pts=round(res[0], 2), net=round(res[0] * PT - COMM, 2), exit=res[1], exit_il=res[2], tag=tag,
                             entry=entry, stop=stop, t1=t1, r_pts=round(abs(entry - stop), 2), system=r.get("system"), mfe_r=round(MFE["r"], 2),
                             shadow_only=int(bool(r.get("shadow_only"))), routed_shadow=int(bool((r.get("result") or {}).get("shadow")))))
df = pd.DataFrame(rows); df.to_csv(out, index=False)
tk = df[df.taken == 1]
print(f"{len(df)} candidates · taken {len(tk)} · sim-vs-harness on taken: exact {((tk.net + COMM - tk.harness_pnl).abs() < 0.01).mean()*100:.0f}% "
      f"· Σ sim {tk.pts.sum()*PT:+.0f}$ vs Σ harness {tk.harness_pnl.sum():+.0f}$")
