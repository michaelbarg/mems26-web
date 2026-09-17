#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oracle_study.py — what the BARS say would have worked (cowork 17.09 18:05).

Michael 17.09 17:58: "לייצר תרחיש על כל הזמן-עבר שלנו לפיו תתבצע כניסה שבוחנת את
המחיר, מיקום, ווליום … להיכנס לברים ולראות מה היה יכול לעבוד … ולייצר תבנית שתעבוד
עם זה — תקרה כפולה, רצפה כפולה, ראש-כתפיים, ספל-ידית".

Method (no producers, no gates — bars, volume, delta only):
  1. Label every closed RTH 5-min bar by what happened NEXT within K=12 bars:
     GOOD_SHORT = fell max(8, 1.5*ATR) before rising max(5, 1.0*ATR) above the close
     (symmetric for LONG). AMBIG when both in one bar. Causal ATR14 on closed bars.
  2. Compute CAUSAL features at the bar: vol_ratio (bar volume / median of the same
     minute over the prior 10 sessions), delta_ratio (bar delta / session median |delta|
     so far), close position in range, 5-bar structure break, bars since session
     high/low, move from open in ATR, double-bottom/top with neckline break.
  3. Print the GOOD-rate of candidate conditions vs the base rate (lift in pp).
Sessions flagged SUSPECT/ROLL by the gap report are excluded. Read-only; ~5s.
Run:  python3 scripts/oracle_study.py            (writes harness_out/oracle/oracle_v0.json)
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, '.env'))
from backend.v9.db.read import read_all
import collections, statistics, json, os
bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join v9_bars_cumulative_delta cd on cd.ts=b.ts
 where b.ts >= '2026-06-01' and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""")
by_day=collections.defaultdict(list)
for b in bars: by_day[str(b['d'])].append(b)
days=sorted(by_day)
EXC={'2026-06-09','2026-06-10','2026-06-11','2026-06-12','2026-06-17','2026-06-18','2026-06-19','2026-06-26','2026-07-10','2026-07-24','2026-07-28','2026-07-29','2026-09-16','2026-09-17'}
K=12
def label(bs,i,atr):
    c=bs[i]['c']; T=max(8.0,1.5*atr); S=max(5.0,1.0*atr)
    res_s=res_l='NONE'
    for j in range(i+1,min(i+1+K,len(bs))):
        hi,lo=bs[j]['h'],bs[j]['l']
        if res_s=='NONE':
            if hi>=c+S and lo<=c-T: res_s='AMBIG'
            elif hi>=c+S: res_s='BAD'
            elif lo<=c-T: res_s='GOOD'
        if res_l=='NONE':
            if lo<=c-S and hi>=c+T: res_l='AMBIG'
            elif lo<=c-S: res_l='BAD'
            elif hi>=c+T: res_l='GOOD'
        if res_s!='NONE' and res_l!='NONE': break
    return res_s,res_l
rows=[]; prior_vol={}
for d in days:
    bs=by_day[d]
    if d in EXC or len(bs)<40:
        for b in bs: prior_vol.setdefault(str(b['t'])[:5],[]).append(float(b['v'] or 0))
        continue
    deltas=[]
    for i,b in enumerate(bs):
        atr=None
        if i>=14:
            trs=[max(bs[k]['h']-bs[k]['l'],abs(bs[k]['h']-bs[k-1]['c']),abs(bs[k]['l']-bs[k-1]['c'])) for k in range(i-13,i+1)]
            atr=sum(trs)/14
        dl=b['delta']
        if dl is not None: deltas.append(abs(float(dl)))
        if atr is None or i<5 or i>len(bs)-3: continue
        m=str(b['t'])[:5]; pv=prior_vol.get(m,[])
        vol_ratio=(float(b['v'])/statistics.median(pv[-10:])) if len(pv)>=5 and statistics.median(pv[-10:])>0 else None
        med_d=statistics.median(deltas[:-1]) if len(deltas)>5 else None
        delta_ratio=(float(dl)/med_d) if (dl is not None and med_d) else None
        rng=b['h']-b['l']; close_pos=((b['c']-b['l'])/rng) if rng>0 else 0.5
        prev5=bs[i-5:i]
        break_dn = b['c'] < min(x['l'] for x in prev5); break_up = b['c'] > max(x['h'] for x in prev5)
        hi_i=max(range(i+1), key=lambda k: bs[k]['h']); lo_i=min(range(i+1), key=lambda k: bs[k]['l'])
        bsh=i-hi_i; bsl=i-lo_i
        move_open=(b['c']-bs[0]['o'])/atr
        win=bs[max(0,i-15):i+1]; dbl_b=dbl_t=False
        lows=sorted(range(len(win)), key=lambda k: win[k]['l'])[:2]; highs=sorted(range(len(win)), key=lambda k: -win[k]['h'])[:2]
        if len(win)>=8 and abs(lows[0]-lows[1])>=3 and abs(win[lows[0]]['l']-win[lows[1]]['l'])<=0.3*atr:
            neck=max(x['h'] for x in win[min(lows):max(lows)+1]); dbl_b = b['c']>neck and (len(win)-1-max(lows))<=3
        if len(win)>=8 and abs(highs[0]-highs[1])>=3 and abs(win[highs[0]]['h']-win[highs[1]]['h'])<=0.3*atr:
            neck=min(x['l'] for x in win[min(highs):max(highs)+1]); dbl_t = b['c']<neck and (len(win)-1-max(highs))<=3
        ls,ll=label(bs,i,atr)
        ph='A' if i<3 else 'B' if i<12 else 'C' if i<54 else 'D'
        rows.append(dict(d=d,t=m,ph=ph,atr=atr,vr=vol_ratio,dr=delta_ratio,cp=close_pos,bdn=break_dn,bup=break_up,bsh=bsh,bsl=bsl,mo=move_open,dbl_b=dbl_b,dbl_t=dbl_t,ls=ls,ll=ll))
    for b in bs: prior_vol.setdefault(str(b['t'])[:5],[]).append(float(b['v'] or 0))
print("sessions", len([d for d in days if d not in EXC]), "bars labeled", len(rows))
def rate(sel, side):
    sub=[r for r in rows if sel(r)]; lab='ls' if side=='S' else 'll'
    g=sum(1 for r in sub if r[lab]=='GOOD'); b=sum(1 for r in sub if r[lab]=='BAD'); a=sum(1 for r in sub if r[lab]=='AMBIG')
    n=len(sub); dec=g+b
    return n, (100*g/dec if dec else 0), g, b, a
base_s=rate(lambda r: True,'S'); base_l=rate(lambda r: True,'L')
print(f"BASE  short: N={base_s[0]} good={base_s[1]:.0f}% (G{base_s[2]}/B{base_s[3]}/A{base_s[4]})   long: good={base_l[1]:.0f}% (G{base_l[2]}/B{base_l[3]})")
conds = {
 'break_dn':            (lambda r: r['bdn'],'S'),
 'break_dn+delta<=-2':  (lambda r: r['bdn'] and r['dr'] is not None and r['dr']<=-2,'S'),
 'break_dn+delta<=-2+vol>=1.3': (lambda r: r['bdn'] and r['dr'] is not None and r['dr']<=-2 and r['vr'] and r['vr']>=1.3,'S'),
 'break_dn+delta+vol+close_pos<=0.3': (lambda r: r['bdn'] and r['dr'] is not None and r['dr']<=-2 and r['vr'] and r['vr']>=1.3 and r['cp']<=0.3,'S'),
 'break_dn+delta+vol NOT fresh(bsl>=2)': (lambda r: r['bdn'] and r['dr'] is not None and r['dr']<=-2 and r['vr'] and r['vr']>=1.3 and r['bsl']>=2,'S'),
 'break_dn at fresh low(bsl==0) & move>=3atr': (lambda r: r['bdn'] and r['bsl']==0 and r['mo']<=-3,'S'),
 'pullback short: bsl 2-6, mo<=-1.5, close_pos<=0.35': (lambda r: 2<=r['bsl']<=6 and r['mo']<=-1.5 and r['cp']<=0.35,'S'),
 'double_top break':    (lambda r: r['dbl_t'],'S'),
 'break_up':            (lambda r: r['bup'],'L'),
 'break_up+delta>=2':   (lambda r: r['bup'] and r['dr'] is not None and r['dr']>=2,'L'),
 'break_up+delta>=2+vol>=1.3': (lambda r: r['bup'] and r['dr'] is not None and r['dr']>=2 and r['vr'] and r['vr']>=1.3,'L'),
 'break_up+delta+vol NOT fresh(bsh>=2)': (lambda r: r['bup'] and r['dr'] is not None and r['dr']>=2 and r['vr'] and r['vr']>=1.3 and r['bsh']>=2,'L'),
 'break_up at fresh high(bsh==0) & move>=3atr': (lambda r: r['bup'] and r['bsh']==0 and r['mo']>=3,'L'),
 'pullback long: bsh 2-6, mo>=1.5, close_pos>=0.65': (lambda r: 2<=r['bsh']<=6 and r['mo']>=1.5 and r['cp']>=0.65,'L'),
 'double_bottom break': (lambda r: r['dbl_b'],'L'),
}
print(f"\n{'condition':48} {'side':4} {'N':>5} {'good%':>6} {'G/B/A':>12}  {'lift vs base':>12}")
for k,(f,side) in conds.items():
    n,g,G,B,A=rate(f,side); base=base_s[1] if side=='S' else base_l[1]
    print(f"{k:48} {side:4} {n:5d} {g:6.0f} {str(G)+'/'+str(B)+'/'+str(A):>12}  {g-base:+11.0f}pp")
print("\nby phase, break+delta+vol (short):")
for ph in 'ABCD':
    n,g,G,B,A=rate(lambda r,ph=ph: r['ph']==ph and r['bdn'] and r['dr'] is not None and r['dr']<=-2 and r['vr'] and r['vr']>=1.3,'S')
    print(f"  {ph}: N={n} good={g:.0f}%")
os.makedirs('harness_out/oracle', exist_ok=True)
json.dump(rows, open('harness_out/oracle/oracle_v0.json','w'), default=str)
