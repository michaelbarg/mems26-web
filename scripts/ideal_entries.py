#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ideal_entries.py — not our trades: for EVERY past session, the 2 biggest moves and
the entry that SHOULD have been taken to ride them (Michael 17.09 20:00: "לא של
העסקאות בפועל אלא על כל הימים שעברו … הסטאפים שהיו צריכים להיכנס כדי ליהנות
מהתנועות הארוכות — בכל יום יש לפחות 2 כאלה").

Per clean session: zigzag on closed 5-min bars (swing threshold 1.0*ATR), take the
2 largest legs (>= max(10 pts, 1.5*ATR)). For each leg, the IDEAL entry = the
earliest bar inside the first half of the leg from which a trade in the leg's
direction, with stop = that bar's opposite extreme (capped at 1.0*ATR), reaches
1.5*ATR before the stop and never gets stopped — i.e. the first bar a system could
have entered and held. Then record what was VISIBLE at that bar (same causal
features as winner_profile: location, context, sequence, trigger, volume/delta).
Output: how the ideal entries look, so the setups can be written from them.
Read-only, ~10s.  Run: python3 scripts/ideal_entries.py
"""
import os, sys, collections, statistics, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'scripts')); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, '.env'))
from backend.v9.db.read import read_all
import oracle_engine as oe
EXC = {'2026-06-09','2026-06-10','2026-06-11','2026-06-12','2026-06-17','2026-06-18','2026-06-19',
       '2026-06-26','2026-07-10','2026-07-24','2026-07-28','2026-07-29','2026-09-16','2026-09-17'}
bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.ts >= '2026-06-01' and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""")
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b['d'])].append(b)
days = [d for d in sorted(by_day) if d not in EXC and len(by_day[d]) >= 60]
prev_va = {}
alld = sorted(by_day)
for k, d in enumerate(alld):
    if k: pb = by_day[alld[k-1]]; prev_va[d] = oe.compute_developing_va(pb, len(pb)-1) if len(pb) > 5 else {}

def zigzag(bs, thr):
    """swing points (idx, price, kind) with reversal threshold thr (pts)."""
    piv = []; mode = None; ext_i = 0; ext_p = bs[0]['c']
    for i, b in enumerate(bs):
        if mode is None:
            if b['h'] - ext_p >= thr: mode = 'up'; ext_i, ext_p = i, b['h']; piv.append((0, bs[0]['l'], 'L'))
            elif ext_p - b['l'] >= thr: mode = 'down'; ext_i, ext_p = i, b['l']; piv.append((0, bs[0]['h'], 'H'))
            continue
        if mode == 'up':
            if b['h'] > ext_p: ext_i, ext_p = i, b['h']
            elif ext_p - b['l'] >= thr: piv.append((ext_i, ext_p, 'H')); mode = 'down'; ext_i, ext_p = i, b['l']
        else:
            if b['l'] < ext_p: ext_i, ext_p = i, b['l']
            elif b['h'] - ext_p >= thr: piv.append((ext_i, ext_p, 'L')); mode = 'up'; ext_i, ext_p = i, b['h']
    piv.append((ext_i, ext_p, 'H' if mode == 'up' else 'L'))
    return piv

def features(bs, i, short, d):
    atr = oe.compute_atr(bs, i) or 0
    if atr <= 0: return None
    b = bs[i]
    deltas = [abs(float(x['delta'])) for x in bs[:i] if x['delta'] is not None]
    med_d = statistics.median(deltas) if len(deltas) > 5 else None
    dr = (float(b['delta'])/med_d) if (b['delta'] is not None and med_d) else None
    dev = oe.compute_developing_va(bs, i-1) if i >= 4 else {}
    zone = oe.classify_zone_vs_developing_va(b['c'], dev) if dev else 'UNKNOWN'
    pv = prev_va.get(d) or {}
    near_prev = bool(pv) and (abs(b['c']-pv.get('val', 1e9)) <= 0.5*atr or abs(b['c']-pv.get('vah', 1e9)) <= 0.5*atr)
    hi_i = max(range(i+1), key=lambda k: bs[k]['h']); lo_i = min(range(i+1), key=lambda k: bs[k]['l'])
    bsh, bsl = i-hi_i, i-lo_i; at_extreme = (bsl == 0) if short else (bsh == 0)
    mo = (b['c']-bs[0]['o'])/atr; with_day = (mo <= -0.5) if short else (mo >= 0.5)
    ib_h = max(x['h'] for x in bs[:12]); ib_l = min(x['l'] for x in bs[:12]); ib_w = ib_h-ib_l
    ext = 'up' if b['c'] > ib_h else 'down' if b['c'] < ib_l else 'none'; with_ext = (ext == 'down' and short) or (ext == 'up' and not short)
    near_ib_edge = abs(b['c']-ib_l) <= 0.5*atr or abs(b['c']-ib_h) <= 0.5*atr
    rng = b['h']-b['l']; cp = ((b['c']-b['l'])/rng) if rng > 0 else 0.5
    trigger_ok = (cp >= 0.7) if not short else (cp <= 0.3); body = abs(b['c']-b['o'])/rng if rng > 0 else 0
    vols = [float(x['v'] or 0) for x in bs[max(0,i-5):i]]; vmed = statistics.median(vols) if vols else 0
    vr = (float(b['v'])/vmed) if vmed > 0 else None
    seq = bs[max(0,i-4):i]; pull = sum(1 for x in seq[-3:] if ((x['c'] < x['o']) if not short else (x['c'] > x['o'])))
    prev5 = bs[max(0,i-5):i]
    brk = (b['c'] < min(x['l'] for x in prev5)) if short else (b['c'] > max(x['h'] for x in prev5)) if prev5 else False
    return dict(atr=atr, hour=str(b['t'])[:5], ph=('A' if i < 3 else 'B' if i < 12 else 'C' if i < 54 else 'D'), zone=zone,
        near_prev_edge=near_prev, near_ib_edge=near_ib_edge, at_extreme=at_extreme, bars_from_extreme=(bsl if short else bsh),
        with_day=with_day, with_ext=with_ext, move_from_open_atr=round(mo, 2), trigger_ok=trigger_ok, body_ge_50=body >= 0.5,
        range_ge_08atr=rng >= 0.8*atr, vol_trig=(vr is not None and vr >= 1.3), vol_ratio=round(vr, 2) if vr else None,
        delta_with=(dr is not None and ((dr <= -1) if short else (dr >= 1))), delta_ratio=round(dr, 2) if dr is not None else None,
        pullback_before=pull >= 2, structure_break=brk)

ideal = []; stats = collections.Counter()
for d in days:
    bs = by_day[d]
    atr0 = oe.compute_atr(bs, min(20, len(bs)-1)) or 6.0
    piv = zigzag(bs, max(4.0, 1.0*atr0))
    legs = []
    for (i0, p0, k0), (i1, p1, k1) in zip(piv, piv[1:]):
        if i1 <= i0: continue
        legs.append(dict(i0=i0, i1=i1, pts=abs(p1-p0), short=(p1 < p0)))
    legs = [l for l in legs if l['pts'] >= max(10.0, 1.5*atr0) and l['i0'] >= 3]
    legs.sort(key=lambda l: -l['pts']); legs = legs[:2]
    stats['sessions'] += 1; stats['legs'] += len(legs)
    for leg in legs:
        short = leg['short']; found = None
        half = leg['i0'] + max(1, (leg['i1']-leg['i0'])//2)
        for i in range(leg['i0'], half+1):
            atr = oe.compute_atr(bs, i) or atr0
            b = bs[i]; ep = b['c']
            stop = (min(b['h'] + 0.25, ep + 1.0*atr) if short else max(b['l'] - 0.25, ep - 1.0*atr))
            target = ep - 1.5*atr if short else ep + 1.5*atr
            ok = False
            for x in bs[i+1:leg['i1']+1]:
                hit_s = (x['h'] >= stop) if short else (x['l'] <= stop)
                hit_t = (x['l'] <= target) if short else (x['h'] >= target)
                if hit_s: break
                if hit_t: ok = True; break
            if ok:
                f = features(bs, i, short, d)
                if f:
                    captured = (ep - bs[leg['i1']]['l']) if short else (bs[leg['i1']]['h'] - ep)
                    found = dict(d=d, leg_pts=round(leg['pts'], 2), dir='S' if short else 'L', entry_il=str(b['t'])[:5],
                                 bars_into_leg=i-leg['i0'], leg_bars=leg['i1']-leg['i0'], captured_pts=round(captured, 2),
                                 stop_pts=round(abs(stop-ep), 2), **f)
                break
        if found: ideal.append(found); stats['entered'] += 1
        else: stats['no_entry'] += 1
print(f"sessions {stats['sessions']} · legs (top-2, >=max(10,1.5ATR)) {stats['legs']} · ideal entries found {stats['entered']} · legs with no holdable entry {stats['no_entry']}")
print(f"leg size: median {statistics.median([x['leg_pts'] for x in ideal]):.1f} pts · captured from ideal entry: median {statistics.median([x['captured_pts'] for x in ideal]):.1f} pts · bars into leg at entry: median {statistics.median([x['bars_into_leg'] for x in ideal])}")
flags = ['with_day','with_ext','at_extreme','near_ib_edge','near_prev_edge','trigger_ok','body_ge_50','range_ge_08atr','vol_trig','delta_with','pullback_before','structure_break']
print("\nWHAT THE IDEAL ENTRY BARS LOOKED LIKE (% of ideal entries with the feature):")
for f in flags: print(f"  {f:16} {100*sum(1 for x in ideal if x[f])/len(ideal):5.0f}%")
def dist(key, top=8):
    c = collections.Counter(x[key] for x in ideal); return ', '.join(f"{k}:{100*v/len(ideal):.0f}%" for k, v in c.most_common(top))
print("\n  phase:  ", dist('ph')); print("  zone:   ", dist('zone')); print("  hour:   ", dist('hour', 12))
print("  bars_from_extreme:", dist('bars_from_extreme', 8))
print(f"  median vol_ratio {statistics.median([x['vol_ratio'] for x in ideal if x['vol_ratio']]):.2f} · median |delta_ratio| {statistics.median([abs(x['delta_ratio']) for x in ideal if x['delta_ratio'] is not None]):.2f} · median stop {statistics.median([x['stop_pts'] for x in ideal]):.1f} pts · median move_from_open_atr {statistics.median([abs(x['move_from_open_atr']) for x in ideal]):.1f}")
print("\nCOMBOS among ideal entries:")
import itertools
for fs in [('with_day','trigger_ok'),('trigger_ok','vol_trig'),('with_day','trigger_ok','vol_trig'),('at_extreme','trigger_ok'),('structure_break','trigger_ok'),('structure_break','vol_trig'),('pullback_before','trigger_ok'),('with_ext','trigger_ok')]:
    print(f"  {' & '.join(fs):40} {100*sum(1 for x in ideal if all(x[f] for f in fs))/len(ideal):5.0f}%")
json.dump(ideal, open('harness_out/oracle/ideal_entries_v0.json', 'w'), default=str)
print("\nsample (last 6):")
for x in ideal[-6:]: print("  ", {k: x[k] for k in ('d','dir','entry_il','leg_pts','captured_pts','bars_into_leg','zone','at_extreme','trigger_ok','vol_ratio','delta_ratio','structure_break','pullback_before')})
