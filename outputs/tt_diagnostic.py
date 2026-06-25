import os
os.environ.setdefault('DATABASE_URL','postgresql://localhost/mems26')
from sqlalchemy import create_engine, text
from backend.v9.systems.woodies.schemas import WoodiesBar
import backend.v9.systems.woodies.patterns.tt as tt

c = create_engine('postgresql://localhost/mems4'.replace('mems4','mems26')).connect()
# 1. trend_state distribution
print('=== trend_state distribution (all woodies bars) ===')
for r in c.execute(text("select coalesce(trend_state,'<null>') t, count(*) n from v9_bars_5min_woodies group by 1 order by 2 desc")):
    print('  %-10s %d' % (r[0], r[1]))

days = [r[0] for r in c.execute(text(
    "select distinct (ts AT TIME ZONE 'America/Chicago')::date d from v9_bars_5min_woodies where cci_14 is not null order by d desc limit 15"))]

precond = 0   # bars where trend BLUE&cci>0 or RED&cci<0 (TT precondition)
fires = 0
total = 0
for d in days:
    rows = c.execute(text(
        "select cci_14,cci_6_tcci,trend_state,open,high,low,close,extract(epoch from ts) e "
        "from v9_bars_5min_woodies where (ts AT TIME ZONE 'America/Chicago')::date=:d "
        "and (ts AT TIME ZONE 'America/Chicago')::time between '08:30' and '15:00' and cci_14 is not null order by ts"),
        {'d': str(d)}).fetchall()
    bars = [WoodiesBar(cci_14=float(r[0]), cci_6_tcci=float(r[1] or 0), trend_state=(r[2] or ''),
                       open=float(r[3]), high=float(r[4]), low=float(r[5]), close=float(r[6]), ts=float(r[7])) for r in rows]
    for i in range(5, len(bars)+1):
        total += 1
        b = bars[i-1]
        if (b.trend_state == 'BLUE' and b.cci_14 > 0) or (b.trend_state == 'RED' and b.cci_14 < 0):
            precond += 1
        res = tt.detect(bars[:i])
        if getattr(res, 'detected', False):
            fires += 1
print('=== TT over 15 days ===')
print('  bars scanned:', total)
print('  TT precondition met (BLUE&cci>0 / RED&cci<0): %d (%.1f%%)' % (precond, 100*precond/max(total,1)))
print('  TT detect() fires:', fires)
print('  => if precond>0 but fires=0 → TCCI-touch/bounce is the blocker; if precond~0 → trend stuck')
