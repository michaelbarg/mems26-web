import os
os.environ.setdefault('DATABASE_URL','postgresql://localhost/mems26')
from sqlalchemy import create_engine, text
from backend.v9.systems.woodies.schemas import WoodiesBar
import backend.v9.systems.woodies.patterns.zlr as zlr
import statistics as st

c = create_engine('postgresql://localhost/mems26').connect()
days = [r[0] for r in c.execute(text(
    "select distinct (ts AT TIME ZONE 'America/Chicago')::date d "
    "from v9_bars_5min_woodies where cci_14 is not null order by d desc limit 15"))]

def load(d):
    rows = c.execute(text(
        "select cci_14,cci_6_tcci,ema_34,lsma_value,swi_value,czi_value,trend_state,"
        "open,high,low,close,extract(epoch from ts) e "
        "from v9_bars_5min_woodies where (ts AT TIME ZONE 'America/Chicago')::date=:d "
        "and (ts AT TIME ZONE 'America/Chicago')::time between '08:30' and '15:00' "
        "and cci_14 is not null order by ts"), {'d': str(d)}).fetchall()
    closes = [float(r[11-1]) for r in rows]
    bars = []
    for r in rows:
        bars.append(WoodiesBar(
            cci_14=float(r[0]), cci_6_tcci=float(r[1] or 0), ema_34=float(r[2] or 0),
            lsma_value=float(r[3] or 0), swi_value=float(r[4] or 0), czi_value=float(r[5] or 0),
            trend_state=(r[6] or ''), open=float(r[7]), high=float(r[8]),
            low=float(r[9]), close=float(r[10]), ts=float(r[11])))
    return bars, closes

def run(flag):
    os.environ['ZLR_SPEC_V2'] = flag
    pnl = []
    for d in days:
        bars, closes = load(d)
        last = -99
        for i in range(20, len(bars)+1):
            res = zlr.detect(bars[:i])
            if getattr(res, 'detected', False) and i-last > 2:
                last = i
                ent = closes[i-1]
                sgn = 1 if res.direction == 'LONG' else -1
                j = i-1+12
                if j < len(closes):
                    pnl.append(sgn*(closes[j]-ent))
    return pnl

def rep(name, pts):
    if not pts:
        print('%s: 0 fires' % name); return
    w = sum(1 for p in pts if p > 0)
    print('%s: n=%d total %+.1fpt ($%+.0f@1ct) | win %d/%d (%.0f%%) | avg %+.2fpt'
          % (name, len(pts), sum(pts), sum(pts)*5, w, len(pts), 100*w/len(pts), st.mean(pts)))

print('ZLR_SPEC_V2 backtest — real zlr.detect() replay, 15 shadow days, 60min forward')
rep('OFF (old CCI-only)  ', run('0'))
rep('ON  (V2 source-spec)', run('1'))
