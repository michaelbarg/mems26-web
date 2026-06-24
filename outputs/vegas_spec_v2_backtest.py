import os; os.environ.setdefault('DATABASE_URL','postgresql://localhost/mems26')
from sqlalchemy import create_engine, text
from backend.v9.systems.woodies.patterns.vegas import _detect_cup_and_handle
from backend.v9.systems.woodies.schemas import WoodiesBar
import statistics as st
c=create_engine('postgresql://localhost/mems26').connect()
days=[r[0] for r in c.execute(text("select distinct (ts AT TIME ZONE 'America/Chicago')::date d from v9_bars_5min_woodies where cci_14 is not null order by d desc limit 15"))]
trades=[]
for d in days:
    rows=c.execute(text("select cci_14,open,high,low,close,extract(epoch from ts) e from v9_bars_5min_woodies where (ts AT TIME ZONE 'America/Chicago')::date=:d and (ts AT TIME ZONE 'America/Chicago')::time between '08:30' and '15:00' and cci_14 is not null order by ts"),{'d':str(d)}).fetchall()
    closes=[float(r[4]) for r in rows]
    bars=[WoodiesBar(cci_14=float(r[0]),open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4]),ts=float(r[5])) for r in rows]
    last=-99
    for i in range(20,len(bars)+1):
        res=_detect_cup_and_handle(bars[:i])
        if res and i-last>2:
            last=i; ent=closes[i-1]; sgn=1 if res['direction']=='LONG' else -1
            for k in (6,12):
                j=i-1+k
                if j<len(closes): trades.append((res['direction'],k,sgn*(closes[j]-ent)))
print("VEGAS_SPEC_V2 (cup-and-handle) backtest — 15 recent shadow days, forward-move proxy")
for k in (6,12):
    pts=[t[2] for t in trades if t[1]==k]
    if not pts: continue
    wins=sum(1 for p in pts if p>0)
    dollar=sum(pts)*5
    print("k=%dbars(%dmin) n=%d: total %+.1fpt ($%+.0f @1ct) | avg %+.2fpt | win %d/%d (%.0f%%)"%(k,k*5,len(pts),sum(pts),dollar,st.mean(pts),wins,len(pts),100*wins/len(pts)))
