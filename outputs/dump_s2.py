import os; os.environ.setdefault('DATABASE_URL','postgresql://localhost/mems26')
from sqlalchemy import create_engine, text
from collections import defaultdict
import csv
c=create_engine('postgresql://localhost/mems26').connect()
cols=['id','pattern_id_at_entry','direction','day_type_at_entry','session_at_entry','entry_ts',
      'entry_price','stop','t1','t2','t3','t1_hit_ts','t2_hit_ts','t3_hit_ts','stop_hit_ts',
      'exit_ts','exit_price','exit_reason','pnl_usd','pnl_r','outcome','quality']
rows=c.execute(text("select %s from v9_trades where firing_system=2 and mode='shadow' order by entry_ts" % ','.join(cols))).fetchall()
with open('outputs/s2_trades_dump.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(cols)
    for r in rows: w.writerow(list(r))
print('dumped %d S2 shadow trades -> outputs/s2_trades_dump.csv' % len(rows))
agg=defaultdict(lambda:[0,0,0.0])
for r in rows:
    p=r[1] or '?'; agg[p][0]+=1; agg[p][2]+=(r[18] or 0)
    if str(r[20] or '').upper().startswith('WIN') or (r[18] or 0)>0: agg[p][1]+=1
print('--- S2 fired patterns (by pnl) ---')
for p,(n,w,pl) in sorted(agg.items(), key=lambda x:x[1][2]):
    print('  %-20s n=%-3d W=%-3d $%+.0f (win %.0f%%)' % (p,n,w,pl,100*w/n if n else 0))
# date span
if rows: print('span:', rows[0][5], '->', rows[-1][5])
