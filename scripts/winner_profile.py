#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""winner_profile.py — what did the WINNING trades have in common? (Michael 17.09 19:45:
"תבדוק איך אתה מגיע רק לעסקאות טובות שניצחו ומה אפיין אותן — רשימה מלאה של כל מה שהן כללו")

Every historical live+shadow entry (all producers, June→), evaluated with the fixed
2-leg model (T1, then T2 with BE; first touch; AMBIG=0; EOD close). WINNER = pts > 0.
For each entry ~20 causal features known at the entry bar (location · context ·
sequence · trigger · volume/delta). Output: prevalence of every feature among
winners vs losers, the winners' distribution over phase/day-type/direction/pattern,
and the feature combinations with the highest win rate (N >= 15).
Read-only, ~15s.  Run: python3 scripts/winner_profile.py
"""
import os, sys, collections, statistics, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'scripts')); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, '.env'))
from backend.v9.db.read import read_all
import oracle_engine as oe

EXC = {'2026-06-09','2026-06-10','2026-06-11','2026-06-12','2026-06-17','2026-06-18','2026-06-19',
       '2026-06-26','2026-07-10','2026-07-24','2026-07-28','2026-07-29','2026-09-16','2026-09-17'}

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

bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.ts >= '2026-06-01' and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""")
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b['d'])].append(b)
days = sorted(by_day)
prev_va = {}
for k, d in enumerate(days):
    if k == 0: continue
    pb = by_day[days[k-1]]
    prev_va[d] = oe.compute_developing_va(pb, len(pb)-1) if len(pb) > 5 else {}

tr = read_all("""select id, mode, direction d, pattern_id_at_entry pat, firing_system sysid, entry_price ep, stop, t1, t2, entry_ts,
 (entry_ts at time zone 'Asia/Jerusalem') il, day_type_at_entry dtype,
 cross_context->0->'systems'->'day_type_machine'->>'opening_type' ot
 from v9_trades where mode in ('live','shadow') and entry_ts >= '2026-06-01' and entry_price is not null and stop is not null and t1 is not null
 and (entry_ts at time zone 'Asia/Jerusalem')::time between '16:35' and '22:15' order by entry_ts""")

def evaluate(t, bs, i):
    ep, st, t1 = float(t['ep']), float(t['stop']), float(t['t1']); t2 = float(t['t2']) if t['t2'] else None
    short = t['d'] == 'SHORT'; r1 = None; be = False; pts = 0.0; mfe = 0.0; mae = 0.0
    for b in bs[i+1:]:
        mfe = max(mfe, (ep - b['l']) if short else (b['h'] - ep)); mae = max(mae, (b['h'] - ep) if short else (ep - b['l']))
        stop_now = st if not be else ep
        hit_s = (b['h'] >= stop_now) if short else (b['l'] <= stop_now)
        if r1 is None:
            hit_t = (b['l'] <= t1) if short else (b['h'] >= t1)
            if hit_t and hit_s: r1 = 'AMBIG'; be = True; continue
            if hit_s: return 2 * (-abs(st - ep)), 'STOP', mfe, mae
            if hit_t: r1 = 'T1'; pts += abs(t1 - ep); be = True
        else:
            if t2 is None: return pts, r1, mfe, mae
            hit_t2 = (b['l'] <= t2) if short else (b['h'] >= t2)
            if hit_t2 and hit_s: return pts, r1 + '+AMBIG', mfe, mae
            if hit_s: return pts, r1 + '+BE', mfe, mae
            if hit_t2: return pts + abs(t2 - ep), r1 + '+T2', mfe, mae
    last = bs[-1]['c']; eod = (ep - last) if short else (last - ep)
    return (2 * eod if r1 is None else pts + eod), (r1 or 'NONE') + '+EOD', mfe, mae

rows = []
for t in tr:
    d = str(t['il'].date())
    if d in EXC or d not in by_day: continue
    bs = by_day[d]; ets = t['entry_ts']; idx = None
    for i, b in enumerate(bs):
        if b['ts'] <= ets and (i + 1 == len(bs) or bs[i+1]['ts'] > ets): idx = i; break
    if idx is None or idx < 15 or idx > len(bs) - 3: continue
    atr = oe.compute_atr(bs, idx) or 0
    if atr <= 0: continue
    b = bs[idx]; short = t['d'] == 'SHORT'; sgn = -1 if short else 1
    pts, res, mfe, mae = evaluate(t, bs, idx)
    deltas = [abs(float(x['delta'])) for x in bs[:idx] if x['delta'] is not None]
    med_d = statistics.median(deltas) if len(deltas) > 5 else None
    dr = (float(b['delta'])/med_d) if (b['delta'] is not None and med_d) else None
    prev2 = bs[idx-2:idx]
    # absorption (fixed def): >=1 of the 2 prior bars has |delta| >= 1.5x median AGAINST the trade, with <= 1 ATR progress against
    against = [x for x in prev2 if x['delta'] is not None and med_d and abs(float(x['delta'])) >= 1.5*med_d and ((float(x['delta']) < 0) if not short else (float(x['delta']) > 0))]
    prog = (bs[idx-3]['l'] - min(x['l'] for x in prev2)) if not short else (max(x['h'] for x in prev2) - bs[idx-3]['h'])
    absorption = bool(against) and prog <= 1.0*atr
    dev = oe.compute_developing_va(bs, idx-1); zone = oe.classify_zone_vs_developing_va(b['c'], dev)
    pv = prev_va.get(d) or {}
    lower_edge = bool(dev) and abs(b['c'] - dev.get('val', 1e9)) <= 0.5*atr; upper_edge = bool(dev) and abs(b['c'] - dev.get('vah', 1e9)) <= 0.5*atr
    at_edge_for = (lower_edge or (bool(pv) and abs(b['c']-pv.get('val',1e9)) <= 0.5*atr)) if not short else (upper_edge or (bool(pv) and abs(b['c']-pv.get('vah',1e9)) <= 0.5*atr))
    beyond_value = (b['c'] < dev.get('val', -1e9)) if not short else (b['c'] > dev.get('vah', 1e9)) if dev else False
    hi_i = max(range(idx+1), key=lambda k: bs[k]['h']); lo_i = min(range(idx+1), key=lambda k: bs[k]['l'])
    bsh, bsl = idx-hi_i, idx-lo_i; at_extreme = (bsl == 0) if short else (bsh == 0)
    mo = (b['c'] - bs[0]['o'])/atr; with_day = (mo <= -1.0) if short else (mo >= 1.0); against_day = (mo >= 1.0) if short else (mo <= -1.0)
    chase = at_extreme and (abs(mo) >= 3) and with_day
    ib_h = max(x['h'] for x in bs[:12]); ib_l = min(x['l'] for x in bs[:12])
    ext = 'up' if b['c'] > ib_h else 'down' if b['c'] < ib_l else 'none'
    with_ext = (ext == 'down' and short) or (ext == 'up' and not short)
    win15 = bs[max(0, idx-15):idx+1]; shape = (double_bottom(win15, atr) if not short else double_top(win15, atr))
    try: hs = oe.detect_head_shoulders_long(bs, idx, atr) if not short else oe.detect_head_shoulders_short(bs, idx, atr)
    except Exception: hs = False
    try: cup = oe.detect_cup_handle_long(bs, idx, atr) if not short else False
    except Exception: cup = False
    vols = [float(x['v'] or 0) for x in bs[idx-5:idx]]; vmed = statistics.median(vols) if vols else 0
    vr_seq = (float(b['v'])/vmed) if vmed > 0 else None
    rng = b['h']-b['l']; cp = ((b['c']-b['l'])/rng) if rng > 0 else 0.5
    trigger_ok = (cp >= 0.7) if not short else (cp <= 0.3)
    body = abs(b['c']-b['o'])/rng if rng > 0 else 0
    delta_with = dr is not None and ((dr >= 1.0) if not short else (dr <= -1.0))
    # sequence: pullback before entry = 2-6 bars against the trade direction just before the trigger
    seq = bs[idx-6:idx]; pull = sum(1 for x in seq[-3:] if ((x['c'] < x['o']) if not short else (x['c'] > x['o'])))
    pullback_seq = pull >= 2
    contracting = len(seq) >= 4 and (seq[-1]['h']-seq[-1]['l']) < (seq[0]['h']-seq[0]['l'])
    stop_atr = abs(float(t['ep'])-float(t['stop']))/atr; t1_atr = abs(float(t['t1'])-float(t['ep']))/atr
    rows.append(dict(id=t['id'], pat=t['pat'] or '?', sysid=t['sysid'], mode=t['mode'], side='S' if short else 'L', pts=pts, res=res, mfe=mfe, mae=mae,
        win=pts > 0, ph=('B' if idx < 12 else 'C' if idx < 54 else 'D'), dtype=(t['dtype'] or 'None'), ot=(t['ot'] or 'NA'),
        hour=str(b['t'])[:2], zone=zone, ext=ext,
        f_at_edge_for=at_edge_for, f_beyond_value=beyond_value, f_in_value=(zone=='IN_VA'),
        f_with_day=with_day, f_against_day=against_day, f_with_ext=with_ext, f_at_extreme=at_extreme, f_chase=chase,
        f_pullback_seq=pullback_seq, f_contracting=contracting, f_shape=(shape or hs or cup), f_absorption=absorption,
        f_trigger_ok=trigger_ok, f_body_ge_50=(body >= 0.5), f_range_ge_08atr=(rng >= 0.8*atr), f_delta_with=delta_with,
        f_vol_trig=(vr_seq is not None and vr_seq >= 1.3), f_stop_le_1atr=(stop_atr <= 1.0), f_stop_gt_2atr=(stop_atr > 2.0), f_t1_ge_1atr=(t1_atr >= 1.0)))

W = [r for r in rows if r['win']]; L = [r for r in rows if not r['win']]
print(f"entries {len(rows)} · winners {len(W)} ({100*len(W)/len(rows):.0f}%) · losers {len(L)}")
print(f"winners: $/trade {5*sum(r['pts'] for r in W)/len(W):+.1f} · median MFE {statistics.median([r['mfe'] for r in W]):.1f} · median MAE {statistics.median([r['mae'] for r in W]):.1f}")
print(f"losers : $/trade {5*sum(r['pts'] for r in L)/len(L):+.1f} · median MFE {statistics.median([r['mfe'] for r in L]):.1f} · median MAE {statistics.median([r['mae'] for r in L]):.1f}")
feats = [k for k in rows[0] if k.startswith('f_')]
print(f"\n{'feature':20} {'win%':>6} {'lose%':>6} {'ratio':>6}  {'N win':>5} {'N lose':>6}   (win rate when feature present)")
for f in feats:
    pw = 100*sum(1 for r in W if r[f])/len(W); pl = 100*sum(1 for r in L if r[f])/len(L)
    n_w = sum(1 for r in W if r[f]); n_l = sum(1 for r in L if r[f]); wr = 100*n_w/(n_w+n_l) if n_w+n_l else 0
    print(f"{f:20} {pw:6.0f} {pl:6.0f} {pw/max(pl,0.1):6.2f}  {n_w:5d} {n_l:6d}   wr={wr:.0f}%")
def dist(key, sub, top=8):
    c = collections.Counter(r[key] for r in sub); tot = len(sub)
    return ', '.join(f"{k}:{100*v/tot:.0f}%" for k, v in c.most_common(top))
print("\nWINNERS by phase:   ", dist('ph', W)); print("LOSERS  by phase:   ", dist('ph', L))
print("WINNERS by day type:", dist('dtype', W)); print("LOSERS  by day type:", dist('dtype', L))
print("WINNERS by opening: ", dist('ot', W)); print("LOSERS  by opening: ", dist('ot', L))
print("WINNERS by hour IL: ", dist('hour', W, 10)); print("LOSERS  by hour IL: ", dist('hour', L, 10))
print("WINNERS by zone:    ", dist('zone', W)); print("LOSERS  by zone:    ", dist('zone', L))
print("WINNERS by pattern: ", dist('pat', W, 10)); print("LOSERS  by pattern: ", dist('pat', L, 10))
print("WINNERS by result:  ", dist('res', W)); print("LOSERS  by result:  ", dist('res', L))
# best combinations (pairs and triples of features), N>=15
import itertools
combos = []
for k in (1, 2, 3):
    for fs in itertools.combinations(feats, k):
        sub = [r for r in rows if all(r[f] for f in fs)]
        if len(sub) >= 15:
            wr = sum(1 for r in sub if r['win'])/len(sub); usd = 5*sum(r['pts'] for r in sub)/len(sub)
            combos.append((wr, usd, len(sub), fs))
combos.sort(key=lambda x: -x[0])
print(f"\nTOP feature combinations (N>=15), base win rate {100*len(W)/len(rows):.0f}%:")
for wr, usd, n, fs in combos[:15]:
    print(f"  win {100*wr:3.0f}%  ${usd:+6.1f}/tr  N={n:3d}  {' & '.join(f[2:] for f in fs)}")
print("\nWORST combinations:")
for wr, usd, n, fs in sorted(combos, key=lambda x: x[0])[:6]:
    print(f"  win {100*wr:3.0f}%  ${usd:+6.1f}/tr  N={n:3d}  {' & '.join(f[2:] for f in fs)}")
json.dump(rows, open('harness_out/oracle/winner_profile_v0.json', 'w'), default=str)
