import os
os.environ.setdefault('DATABASE_URL','postgresql://localhost/mems26')
from sqlalchemy import create_engine, text
c = create_engine('postgresql://localhost/mems26').connect()

# ALL fires (S2+S4) with direction + outcome
fires = c.execute(text("""
  select entry_ts, direction, pattern_id_at_entry, pnl_usd, firing_system
  from v9_trades where mode='shadow' and firing_system in (2,4) and entry_ts is not null
  order by entry_ts
""")).fetchall()

def sustained_side(entry_ts, k=3):
    rows = c.execute(text("""
      select close, lsma_value from v9_bars_5min_woodies
      where ts <= :e and lsma_value is not null order by ts desc limit :k
    """), {"e": entry_ts, "k": k}).fetchall()
    if len(rows) < k:
        return None
    sides = [1 if float(r[0])>float(r[1]) else -1 for r in rows]
    return sides[0] if all(s==sides[0] for s in sides) else 0  # 0 = chop/mixed

from collections import defaultdict
agg = defaultdict(lambda: [0,0.0])  # key -> [count, pnl]
blocked_by_pat = defaultdict(lambda: [0,0,0.0])  # pattern -> [blocked_count, blocked_WINS, blocked_pnl]
REV = ('VEGAS','GHOST','FAMIR','HTLB','HFE','DOUBLE','HNS','HEAD_SHOULDER')
for f in fires:
    d = 1 if f[1]=='LONG' else -1
    ss = sustained_side(f[0], 3)
    if ss is None: continue
    pat = (f[2] or '').upper()
    is_rev = any(r in pat for r in REV)
    aligned = (ss == d)               # trade direction matches the 3-bar sustained side
    chop = (ss == 0)
    pnl = float(f[3] or 0)
    if is_rev:                         # CONTINUATION-ONLY: reversals are EXEMPT (always kept)
        bucket = 'ALIGNED(kept)'
    else:
        bucket = 'CHOP(blocked)' if chop else ('ALIGNED(kept)' if aligned else 'COUNTER(blocked)')
    agg[bucket][0]+=1; agg[bucket][1]+=pnl
    if bucket != 'ALIGNED(kept)':
        bp = blocked_by_pat[(f[4], f[2])]
        bp[0]+=1; bp[1]+= (1 if pnl>0 else 0); bp[2]+=pnl
print("=== BLOCKED fires by system/pattern (watch: blocked WINNERS = risk) ===")
for (sysn,pat),(n,w,p) in sorted(blocked_by_pat.items(), key=lambda x:-x[1][1]):
    print("  S%s %-16s blocked=%-3d of-which-WINS=%-2d pnl=$%+.0f"%(sysn,pat,n,w,p))
print()

print("S2 fires under 3-bar sustained-LSMA trend filter:")
for k in ['ALIGNED(kept)','CHOP(blocked)','COUNTER(blocked)']:
    n,p = agg[k]
    print("  %-18s n=%-3d pnl=$%+.0f"%(k,n,p))
kept=agg['ALIGNED(kept)']; blocked_pnl=agg['CHOP(blocked)'][1]+agg['COUNTER(blocked)'][1]
print("  -> KEPT pnl=$%+.0f | BLOCKED pnl=$%+.0f (removing blocked changes total by $%+.0f)"%(kept[1],blocked_pnl,-blocked_pnl))
# Flag-specific
print("\nBULL_FLAG_LONG fires specifically:")
for f in fires:
    if f[2] and 'FLAG' in f[2] and f[1]=='LONG':
        ss=sustained_side(f[0],3)
        lab={1:'sust-UP',-1:'sust-DOWN',0:'CHOP',None:'n/a'}.get(ss)
        print("  %s LONG pnl=$%+.0f  3bar=%s %s"%(f[0].strftime('%m-%d %H:%M'), float(f[3] or 0), lab, '<-BLOCKED' if ss!=1 else 'kept'))
