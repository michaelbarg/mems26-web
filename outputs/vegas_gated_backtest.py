import os; os.environ.setdefault('DATABASE_URL','postgresql://localhost/mems26')
from sqlalchemy import create_engine, text
from backend.v9.systems.woodies.patterns.vegas import _detect_cup_and_handle
from backend.v9.systems.woodies.schemas import WoodiesBar
c=create_engine('postgresql://localhost/mems26').connect()
cols=[r[0] for r in c.execute(text("select column_name from information_schema.columns where table_name='v9_bars_5min_woodies'"))]
lsma_col='lsma_value' if 'lsma_value' in cols else ('lsma' if 'lsma' in cols else None)
print('lsma col:', lsma_col)
days=[r[0] for r in c.execute(text("select distinct (ts AT TIME ZONE 'America/Chicago')::date d from v9_bars_5min_woodies where cci_14 is not null order by d desc limit 15"))]
ung=[]; gated=[]; blocked=0
for d in days:
    q="select cci_14,open,high,low,close,%s lv from v9_bars_5min_woodies where (ts AT TIME ZONE 'America/Chicago')::date=:d and (ts AT TIME ZONE 'America/Chicago')::time between '08:30' and '15:00' and cci_14 is not null order by ts" % (lsma_col or 'NULL')
    rows=c.execute(text(q),{'d':str(d)}).fetchall()
    closes=[float(r[4]) for r in rows]
    lsmas=[(float(r[5]) if r[5] is not None else None) for r in rows]
    bars=[WoodiesBar(cci_14=float(r[0]),open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4]),ts=float(i)) for i,r in enumerate(rows)]
    last=-99
    for i in range(20,len(bars)+1):
        res=_detect_cup_and_handle(bars[:i])
        if res and i-last>2:
            last=i; ent=closes[i-1]; sgn=1 if res['direction']=='LONG' else -1
            j=i-1+12
            if j>=len(closes): continue
            pnl=sgn*(closes[j]-ent); ung.append(pnl)
            ls=lsmas[i-1]
            if ls is None: continue
            ok=(res['direction']=='LONG' and ent>ls) or (res['direction']=='SHORT' and ent<ls)
            if ok: gated.append(pnl)
            else: blocked+=1
def rep(name,pts):
    if not pts: print('%s: 0 fires'%name); return
    w=sum(1 for p in pts if p>0)
    print('%s: n=%d total %+.1fpt ($%+.0f@1ct) win %d/%d (%.0f%%)'%(name,len(pts),sum(pts),sum(pts)*5,w,len(pts),100*w/len(pts)))
print('--- VEGAS cup-and-handle, 60min horizon, 15 shadow days ---')
rep('UNGATED   ', ung)
rep('LSMA-GATED', gated)
print('blocked by LSMA gate: %d'%blocked)
