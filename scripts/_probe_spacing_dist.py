#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Derivation probe for TARGET_MIN_SPACING_V1's k/m — ladder-gap distribution
vs ATR14 and vs risk, over the live era. READ-ONLY.

Answers the only question that fixes k/m honestly: how big IS a ladder step
today, in ATR units and in R units, and where does the "degenerate" cluster sit?
The p25 columns it prints are what `config/targets.yaml: target_spacing` cites —
k=0.25 and m=0.33 are both set BELOW the bottom quartile of a real ladder step,
so the rule is a tail-catcher by construction. Re-run it to re-derive.

Referenced by: config/RULED_FLAGS.yaml (TARGET_MIN_SPACING_V1) and
docs/reports/REPLAY_TARGET_SPACING_2026-08-21.md §2.
"""
import os
import statistics as st
import psycopg2

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
conn = psycopg2.connect(DSN)
cur = conn.cursor()

# ATR14 (Wilder-free simple mean TR over 14 closed 5-min bars) at entry time
cur.execute("""
    select ts, high, low, close from v9_bars_5min_woodies order by ts
""")
bars = [(t, float(h), float(l), float(c)) for (t, h, l, c) in cur.fetchall()
        if h is not None and l is not None and c is not None]


def atr14_at(ts):
    """Mean true range of the 14 bars strictly BEFORE ts (no look-ahead)."""
    prior = [b for b in bars if b[0] < ts][-15:]
    if len(prior) < 15:
        return None
    trs = []
    for i in range(1, len(prior)):
        _, h, l, _c = prior[i]
        pc = prior[i - 1][3]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / len(trs)


cur.execute("""
    select id, mode, entry_ts, direction, entry_price, stop, t1, t2, t3,
           pattern_id_at_entry, day_type_at_entry, pnl_usd, exit_reason
    from v9_trades
    where entry_ts >= '2026-07-07' and entry_price is not null and stop is not null
    order by entry_ts
""")
rows = cur.fetchall()
conn.close()

recs = []
for (tid, mode, ets, d, ep, sp, t1, t2, t3, pat, dt_, pnl, xr) in rows:
    ep, sp = float(ep), float(sp)
    risk = abs(ep - sp)
    if risk <= 0:
        continue
    a = atr14_at(ets)
    sign = 1.0 if str(d).upper() == "LONG" else -1.0
    legs = [x for x in (t1, t2, t3) if x is not None and float(x) != 0.0]
    legs = [float(x) for x in legs]
    # distance from entry, in trade direction
    dists = [sign * (x - ep) for x in legs]
    gaps = [round(dists[i + 1] - dists[i], 4) for i in range(len(dists) - 1)]
    recs.append(dict(id=tid, mode=mode, pat=pat, dt=dt_, risk=risk, atr=a,
                     gaps=gaps, dists=dists, pnl=pnl, xr=xr, n=len(legs)))

allgaps = [g for r in recs for g in r["gaps"]]
print(f"trades={len(recs)}  gaps={len(allgaps)}")
print(f"gap pts: min={min(allgaps):.2f} p10={st.quantiles(allgaps, n=10)[0]:.2f} "
      f"p25={st.quantiles(allgaps, n=4)[0]:.2f} median={st.median(allgaps):.2f} "
      f"p75={st.quantiles(allgaps, n=4)[2]:.2f} max={max(allgaps):.2f}")

gr = [(g / r["atr"]) for r in recs if r["atr"] for g in r["gaps"]]
gk = [(g / r["risk"]) for r in recs for g in r["gaps"]]
print(f"gap/ATR14: p10={st.quantiles(gr, n=10)[0]:.3f} p25={st.quantiles(gr, n=4)[0]:.3f} "
      f"median={st.median(gr):.3f} p75={st.quantiles(gr, n=4)[2]:.3f}")
print(f"gap/risk : p10={st.quantiles(gk, n=10)[0]:.3f} p25={st.quantiles(gk, n=4)[0]:.3f} "
      f"median={st.median(gk):.3f} p75={st.quantiles(gk, n=4)[2]:.3f}")

atrs = [r["atr"] for r in recs if r["atr"]]
print(f"ATR14 at entry: min={min(atrs):.2f} median={st.median(atrs):.2f} max={max(atrs):.2f}")
risks = [r["risk"] for r in recs]
print(f"risk: min={min(risks):.2f} median={st.median(risks):.2f} max={max(risks):.2f}")

print("\n-- violation counts per (k,m) on LIVE trades --")
live = [r for r in recs if r["mode"] == "live"]
print(f"live trades with >=2 legs: {sum(1 for r in live if r['n'] >= 2)}")
for k in (0.15, 0.20, 0.25, 0.30, 0.40):
    for m in (0.25, 0.33, 0.50, 0.75):
        nv = 0
        nlegs = 0
        for r in live:
            if not r["atr"]:
                continue
            mg = max(k * r["atr"], m * r["risk"])
            bad = sum(1 for g in r["gaps"] if g < mg - 1e-9)
            if bad:
                nv += 1
                nlegs += bad
        print(f"  k={k:.2f} m={m:.2f} -> {nv:3d} trades violate, {nlegs:3d} legs")

print("\n-- worst offenders (live, smallest min-gap) --")
worst = sorted([r for r in live if r["gaps"]], key=lambda r: min(r["gaps"]))[:12]
for r in worst:
    print(f"  #{r['id']} {r['pat']:<12} {r['dt']:<16} risk={r['risk']:.2f} "
          f"atr={(r['atr'] or 0):.2f} gaps={r['gaps']} dists={[round(x,2) for x in r['dists']]} "
          f"pnl={r['pnl']} {r['xr']}")
