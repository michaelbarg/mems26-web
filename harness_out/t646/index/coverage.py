import collections
def rd(n): return [l.strip() for l in open(n) if l.strip()]
h=set(rd('h81.txt')); bars=set(rd('bars_full.txt')); hist=set(rd('hist_dates.txt')); st=set(rd('state_dates.txt'))
dec=set(rd('dec_dates.txt')); bv=set(rd('bar_vec_dates.txt')); demo=set(rd('demo_dates.txt')); live=set(rd('live_dates.txt'))
sh=set(rd('shadow_dates.txt')); ts=set(rd('treeshadow_dates.txt'))
print('harness days',len(h),min(h),max(h))
print('bars_full',len(bars),min(bars),max(bars))
print('harness with full RTH bars',len(h&bars),'| harness w/o full bars',sorted(h-bars))
print('full-RTH bar days not in harness',len(bars-h), sorted(bars-h))
for name,s in [('EOD hist row',hist),('DECISION vec w/ live day_type',dec),('BAR vectors',bv),('state series',st),('demo trades',demo),('live trades',live),('shadow trades',sh),('TREE_SHADOW',ts)]:
    print(f'{name:32s} total={len(s):3d}  in harness={len(s&h):3d}  range={min(s)}..{max(s)}')
bym=collections.OrderedDict()
for d in sorted(h):
    bym.setdefault(d[:7],[0,0]); bym[d[:7]][0]+=1
for d in sorted(bars):
    if d>= '2026-06-15': bym.setdefault(d[:7],[0,0]); bym[d[:7]][1]+=1
print('month: harness days / full-RTH bar days (>=2026-06-15)')
for k,v in bym.items(): print(k,v)
# weekdays 2026-06-15..2026-10-23 not in harness
import datetime as dt
d0=dt.date(2026,6,15); d1=dt.date(2026,10,23); miss=[]
d=d0
while d<=d1:
    if d.weekday()<5 and d.isoformat() not in h: miss.append(d.isoformat())
    d+=dt.timedelta(days=1)
print('weekdays 06-15..10-23 not in harness:',len(miss),miss)
print('...of which have full RTH bars:',[m for m in miss if m in bars])
print('...of which have a hist EOD row:',len([m for m in miss if m in hist]))
# hist rows on weekends
wk=[x for x in hist if dt.date.fromisoformat(x).weekday()>=5]
print('hist weekend rows',len(wk))
# harness days lacking each layer
print('harness days lacking EOD row:',sorted(h-hist))
print('harness days with demo trades',len(h&demo),'live trades',len(h&live),'both',len(h&demo&live))
print('first 10-23 DECISION dates:',sorted(dec)[:3],sorted(dec)[-3:])
print('dec dates',sorted(dec))
print('state dates',sorted(st))
