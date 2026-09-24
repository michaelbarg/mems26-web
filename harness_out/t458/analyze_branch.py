#!/usr/bin/env python3
"""T-458(ג) — table of the opening-drive branch on the clean sessions (fwd_harness, real engine).
For each session: did a confirmed opening drive go live under flag=1, its outcome (T1 2.5R / STOP / EOD),
pnl (harness pnl_usd minus $2.60 RT), MFE, and the day total; plus flag=0 day totals where available."""
import glob, json, os, sys
D = os.path.dirname(os.path.abspath(__file__))
COMM = 2.60
rows = []
for p in sorted(glob.glob(os.path.join(D, "branch1_*.json"))):
    d = os.path.basename(p)[8:18]
    try: j = json.load(open(p))
    except Exception as e: print("bad", p, e); continue
    drives = [t for t in (j.get("trades") or []) if str(t.get("classification", "")).upper() in ("OPENING_DRIVE", "OPENING_TEST_DRIVE")]
    day1 = j.get("daily_pnl_harness")
    n_tr = len(j.get("trades") or [])
    p0 = os.path.join(D, f"branch0_{d}.json"); day0 = None; n0 = None
    if os.path.exists(p0):
        try: j0 = json.load(open(p0)); day0 = j0.get("daily_pnl_harness"); n0 = len(j0.get("trades") or [])
        except Exception: pass
    for t in drives:
        legs = t.get("legs") or []
        ex = legs[0].get("exit") if legs else None
        rows.append(dict(d=d, cls=t["classification"], dir=t["direction"], entry=t["entry"], stop=t.get("stop_initial"),
                         t1=t.get("t1_target"), t1_pts=t.get("t1_pts"), exit=ex, exit_il=t.get("exit_il"),
                         pnl=round((t.get("pnl_usd") or 0) - COMM, 2), mfe=t.get("mfe_pts"), mae=t.get("mae_pts"),
                         hold=t.get("hold_to_close_pts"), day1=day1, n1=n_tr, day0=day0, n0=n0))
    if not drives:
        rows.append(dict(d=d, cls=None, day1=day1, n1=n_tr, day0=day0, n0=n0))
sess = sorted({r["d"] for r in rows}); dr = [r for r in rows if r["cls"]]
print(f"sessions={len(sess)} · confirmed drives live (flag=1)={len(dr)}")
print(f"{'day':10} {'cls':19} {'dir':5} {'entry':8} {'stop':8} {'t1':8} {'R':5} {'exit':5} {'at':6} {'pnl$':8} {'mfe':6} {'hold':6} {'day1$':8} {'day0$':8}")
for r in dr:
    R = abs(r["entry"] - r["stop"]) if r.get("stop") else 0
    d0 = "" if r["day0"] is None else "%.2f" % r["day0"]
    print(f"{r['d']:10} {r['cls']:19} {r['dir']:5} {r['entry']:8.2f} {r['stop'] or 0:8.2f} {r['t1'] or 0:8.2f} {R:5.2f} {str(r['exit']):5} {str(r['exit_il'])[:5]:6} {r['pnl']:8.2f} {r['mfe'] or 0:6.1f} {r['hold'] or 0:6.1f} {r['day1'] or 0:8.2f} {d0:>8}")
w = [r for r in dr if r["pnl"] > 0]; s = sum(r["pnl"] for r in dr)
if dr:
    print(f"\nDRIVES: n={len(dr)} win={100*len(w)/len(dr):.0f}% Σ{s:+.2f}$ avg {s/len(dr):+.2f}$ · T1-hit={sum(1 for r in dr if r['exit']=='T1')} STOP={sum(1 for r in dr if r['exit']=='STOP')} EOD/other={sum(1 for r in dr if r['exit'] not in ('T1','STOP'))}")
    by = {}
    for r in dr: by.setdefault(r["cls"], []).append(r["pnl"])
    for k, v in by.items(): print(f"  {k}: n={len(v)} Σ{sum(v):+.2f}$ win={100*sum(1 for x in v if x>0)/len(v):.0f}%")
d1 = [r["day1"] for r in rows if r["day1"] is not None]; 
print(f"\nDAY TOTALS flag=1 (harness, no commissions): sessions={len(d1)} Σ{sum(d1):+.2f}$ · sessions with a drive: Σ{sum(r['day1'] for r in dr if r['day1'] is not None):+.2f}$")
both = [r for r in dr if r["day0"] is not None]
if both:
    print(f"flag=1 vs flag=0 on the {len(both)} drive sessions: Σday1 {sum(r['day1'] for r in both):+.2f}$ vs Σday0 {sum(r['day0'] for r in both):+.2f}$ ⇒ Δ {sum(r['day1']-r['day0'] for r in both):+.2f}$")
if "--sessions-with-drive" in sys.argv:
    print("\n".join(sorted({r["d"] for r in dr})))
