#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pattern_evidence_study.py — OUR patterns × (location · sequence · trigger · volume).

Michael 17.09 19:20: "אני צריך שתבחן את זה על תבניות שלנו שנוכל לתקן אותן — בעיקר
ריאקטיב ואיניאטיב … חשוב שנדייק את המערכת ולא נבנה דברים מחדש".

For every historical REACTIVE_* / INITIATIVE_* entry (live + shadow, June→), find
the entry bar, compute the evidence that was KNOWN at that bar (causal), evaluate
the trade with the fixed 2-leg model (T1, then T2 with BE; first touch; AMBIG=0;
EOD close), and print, per pattern-direction, win% and $/trade WITH vs WITHOUT
each piece of evidence. The refinement rules come from the cells that separate.
Reuses scripts/oracle_engine.py detectors (H&S, cup-handle, developing VA).
Read-only, ~10s.  Run: python3 scripts/pattern_evidence_study.py
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
days = sorted(by_day)
# previous-day VA (simplified, from closes) for location evidence
prev_va = {}
for k, d in enumerate(days):
    if k == 0: continue
    pb = by_day[days[k-1]]
    prev_va[d] = oe.compute_developing_va(pb, len(pb)-1) if len(pb) > 5 else {}

tr = read_all("""select id, mode, direction d, pattern_id_at_entry pat, entry_price ep, stop, t1, t2, entry_ts,
 (entry_ts at time zone 'Asia/Jerusalem') il from v9_trades
 where mode in ('live','shadow') and entry_ts >= '2026-06-01' and entry_price is not null and stop is not null and t1 is not null
 and (pattern_id_at_entry like 'REACTIVE%' or pattern_id_at_entry like 'INITIATIVE%')
 and (entry_ts at time zone 'Asia/Jerusalem')::time between '16:35' and '22:15' order by entry_ts""")

def evaluate(t, bs, i):
    ep, st, t1 = float(t['ep']), float(t['stop']), float(t['t1']); t2 = float(t['t2']) if t['t2'] else None
    short = t['d'] == 'SHORT'; r1 = None; be = False; pts = 0.0; mfe = 0.0
    for b in bs[i+1:]:
        mfe = max(mfe, (ep - b['l']) if short else (b['h'] - ep))
        stop_now = st if not be else ep
        hit_s = (b['h'] >= stop_now) if short else (b['l'] <= stop_now)
        if r1 is None:
            hit_t = (b['l'] <= t1) if short else (b['h'] >= t1)
            if hit_t and hit_s: r1 = 'AMBIG'; be = True; continue
            if hit_s: return 2 * (-abs(st - ep)), mfe
            if hit_t: r1 = 'T1'; pts += abs(t1 - ep); be = True
        else:
            if t2 is None: return pts, mfe
            hit_t2 = (b['l'] <= t2) if short else (b['h'] >= t2)
            if hit_t2 and hit_s: return pts, mfe
            if hit_s: return pts, mfe
            if hit_t2: return pts + abs(t2 - ep), mfe
    last = bs[-1]['c']; eod = (ep - last) if short else (last - ep)
    return (2 * eod if r1 is None else pts + eod), mfe

def double_bottom(win, atr):
    if len(win) < 8: return False
    lows = sorted(range(len(win)), key=lambda k: win[k]['l'])[:2]
    if abs(lows[0]-lows[1]) < 3 or abs(win[lows[0]]['l']-win[lows[1]]['l']) > 0.3*atr: return False
    neck = max(x['h'] for x in win[min(lows):max(lows)+1])
    return win[-1]['c'] > neck and (len(win)-1-max(lows)) <= 3
def double_top(win, atr):
    if len(win) < 8: return False
    highs = sorted(range(len(win)), key=lambda k: -win[k]['h'])[:2]
    if abs(highs[0]-highs[1]) < 3 or abs(win[highs[0]]['h']-win[highs[1]]['h']) > 0.3*atr: return False
    neck = min(x['l'] for x in win[min(highs):max(highs)+1])
    return win[-1]['c'] < neck and (len(win)-1-max(highs)) <= 3

rows = []
for t in tr:
    d = str(t['il'].date())
    if d in EXC or d not in by_day: continue
    bs = by_day[d]
    # entry bar = bar containing entry_ts (floor to 5 min)
    ets = t['entry_ts']
    idx = None
    for i, b in enumerate(bs):
        if b['ts'] <= ets and (i + 1 == len(bs) or bs[i+1]['ts'] > ets): idx = i; break
    if idx is None or idx < 15 or idx > len(bs) - 3: continue
    atr = oe.compute_atr(bs, idx) or 0
    if atr <= 0: continue
    b = bs[idx]; short = t['d'] == 'SHORT'
    pts, mfe = evaluate(t, bs, idx)
    deltas = [abs(float(x['delta'])) for x in bs[:idx] if x['delta'] is not None]
    med_d = statistics.median(deltas) if len(deltas) > 5 else None
    dr = (float(b['delta'])/med_d) if (b['delta'] is not None and med_d) else None
    # absorption in the 2 bars before the trigger: heavy delta AGAINST the trade direction with little progress
    prev2 = bs[idx-2:idx]
    heavy = all(x['delta'] is not None and med_d and abs(float(x['delta'])) >= 1.5*med_d for x in prev2)
    prog = (min(x['l'] for x in prev2) - bs[idx-3]['l']) if not short else (bs[idx-3]['h'] - max(x['h'] for x in prev2))
    absorption = heavy and abs(prog) <= 1.0*atr and all(((float(x['delta']) < 0) if not short else (float(x['delta']) > 0)) for x in prev2)
    dev = oe.compute_developing_va(bs, idx-1)
    zone = oe.classify_zone_vs_developing_va(b['c'], dev)
    pv = prev_va.get(d) or {}
    near_prev_edge = bool(pv) and (abs(b['c'] - pv.get('val', 1e9)) <= 0.5*atr or abs(b['c'] - pv.get('vah', 1e9)) <= 0.5*atr)
    hi_i = max(range(idx+1), key=lambda k: bs[k]['h']); lo_i = min(range(idx+1), key=lambda k: bs[k]['l'])
    bsh, bsl = idx-hi_i, idx-lo_i
    at_extreme = (bsl == 0) if short else (bsh == 0)
    mo = (b['c'] - bs[0]['o'])/atr
    chase = at_extreme and ((mo <= -3) if short else (mo >= 3))
    win15 = bs[max(0, idx-15):idx+1]
    shape = (double_bottom(win15, atr) if not short else double_top(win15, atr))
    try:
        hs = oe.detect_head_shoulders_long(bs, idx, atr) if not short else oe.detect_head_shoulders_short(bs, idx, atr)
    except Exception: hs = False
    try:
        cup = oe.detect_cup_handle_long(bs, idx, atr) if not short else False
    except Exception: cup = False
    vols = [float(x['v'] or 0) for x in bs[idx-5:idx]]
    vr_seq = (float(b['v'])/statistics.median(vols)) if vols and statistics.median(vols) > 0 else None
    rng = b['h']-b['l']; cp = ((b['c']-b['l'])/rng) if rng > 0 else 0.5
    trigger_ok = (cp >= 0.7) if not short else (cp <= 0.3)
    delta_with = dr is not None and ((dr >= 1.0) if not short else (dr <= -1.0))
    rows.append(dict(pat=t['pat'], side='S' if short else 'L', pts=pts, mfe=mfe,
                     loc_edge=(zone == ('BELOW_VA' if not short else 'ABOVE_VA')) or near_prev_edge,
                     zone=zone, absorption=absorption, at_extreme=at_extreme, chase=chase,
                     shape=shape or hs or cup, delta_with=delta_with, vol_trig=(vr_seq is not None and vr_seq >= 1.3),
                     trigger_ok=trigger_ok, ph='B' if idx < 12 else 'C' if idx < 54 else 'D'))
print("entries evaluated:", len(rows), "| by pattern:", dict(collections.Counter(r['pat'] for r in rows)))

def cell(sel):
    sub = [r for r in rows if sel(r)]; n = len(sub)
    if n == 0: return (0, 0, 0)
    w = sum(1 for r in sub if r['pts'] > 0); return (n, 100*w/n, 5*sum(r['pts'] for r in sub)/n)
flags = ['loc_edge', 'absorption', 'shape', 'delta_with', 'vol_trig', 'trigger_ok', 'at_extreme', 'chase']
for fam in ('REACTIVE', 'INITIATIVE'):
    for side in ('L', 'S'):
        base = cell(lambda r: r['pat'].startswith(fam) and r['side'] == side)
        if base[0] < 8: continue
        print(f"\n== {fam} {side}  N={base[0]} win={base[1]:.0f}% $/tr={base[2]:+.1f}")
        for f in flags:
            w = cell(lambda r: r['pat'].startswith(fam) and r['side'] == side and r[f])
            wo = cell(lambda r: r['pat'].startswith(fam) and r['side'] == side and not r[f])
            print(f"   {f:11}  with: N={w[0]:3d} win={w[1]:3.0f}% $={w[2]:+6.1f}   without: N={wo[0]:3d} win={wo[1]:3.0f}% $={wo[2]:+6.1f}")
        combo = cell(lambda r: r['pat'].startswith(fam) and r['side'] == side and r['loc_edge'] and r['delta_with'] and r['trigger_ok'] and not r['chase'])
        print(f"   COMBO loc_edge+delta_with+trigger_ok+not chase:  N={combo[0]} win={combo[1]:.0f}% $={combo[2]:+.1f}")
        combo2 = cell(lambda r: r['pat'].startswith(fam) and r['side'] == side and (r['shape'] or r['absorption']) and r['delta_with'])
        print(f"   COMBO (shape or absorption)+delta_with:            N={combo2[0]} win={combo2[1]:.0f}% $={combo2[2]:+.1f}")
json.dump(rows, open('harness_out/oracle/pattern_evidence_v0.json', 'w'), default=str)
