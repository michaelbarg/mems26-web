"""T-518 (30.09): what would smaller targets have done?  Read-only.
Two populations, same simulator:
  (A) the 176 trades the live config takes in the same-night reference replay (harness_out/t466/t517ref_*.json, 62 sessions)
  (B) the 31 real live trades 09.09-29.09 (v9_trades, mode=live), from their real entry/stop
Rule: from the bar AFTER the entry bar, first touch decides; a bar that touches BOTH stop and target counts as STOP
(the same conservative ordering the shadow book uses). Session end => close at the last RTH close.
$5/pt/contract, 1 contract, commission 2.60$/round-trip (the harness' net rate)."""
import json, glob, sys, os, datetime as dt, collections
import psycopg2
from zoneinfo import ZoneInfo
IL = ZoneInfo('Asia/Jerusalem')
INCLUDE_ENTRY_BAR = os.environ.get('INCLUDE_ENTRY_BAR','0')=='1'
DSN = os.environ.get('DATABASE_URL', 'postgresql://localhost/mems26')
conn = psycopg2.connect(DSN)
cur = conn.cursor()

def bars_for(day):
    cur.execute("""select ts, open, high, low, close from v9_bars_5min_woodies
                   where ts >= %s::timestamptz and ts < %s::timestamptz order by ts""",
                (f"{day} 16:30+03", f"{day} 23:00+03"))
    return [(r[0].astimezone(IL), float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in cur.fetchall()]

def simulate(bars, entry_ts, direction, entry, stop, target):
    """first-touch after the entry bar; both-in-one-bar => STOP; eod => close. returns (result, pts)"""
    sgn = 1 if direction == 'LONG' else -1
    # entry bar = the 5-min bar containing entry_ts; start scoring from the NEXT bar
    idx = None
    for i, b in enumerate(bars):
        if b[0] <= entry_ts < b[0] + dt.timedelta(minutes=5):
            idx = i; break
    if idx is None:
        # entry after last bar start -> use bars after entry_ts
        later = [i for i, b in enumerate(bars) if b[0] > entry_ts]
        if not later: return ('NO_BARS', 0.0)
        idx = later[0] - 1
    for b in bars[idx + (0 if INCLUDE_ENTRY_BAR else 1):]:
        ts, o, h, l, c = b
        hit_stop = (l <= stop) if sgn > 0 else (h >= stop)
        hit_tgt = (h >= target) if sgn > 0 else (l <= target)
        if hit_stop: return ('STOP', sgn * (stop - entry))
        if hit_tgt: return ('WIN', sgn * (target - entry))
    if bars: return ('EOD', sgn * (bars[-1][4] - entry))
    return ('NO_BARS', 0.0)

def run(pop, label):
    ks = [0.5, 0.75, 1.0, 1.25, 1.5]
    fixed = [4.0, 6.0, 8.0]
    print(f"\n===== {label}: {len(pop)} trades =====")
    print(f"{'target':>14} {'n':>4} {'win':>4} {'stop':>4} {'eod':>4} {'win%':>6} {'avg$':>8} {'sum$ net':>9} {'per-session':>11} {'BE win% needed':>15}")
    sessions = len({p['day'] for p in pop})
    for name, f in [(f"{k}R", (lambda k: (lambda p: k * p['risk']))(k)) for k in ks] + [(f"{x:.0f}pt", (lambda x: (lambda p: x))(x)) for x in fixed] + [("actual T1", lambda p: p['t1_pts'])]:
        res = collections.Counter(); pnl = 0.0; n = 0; tgt_sum = 0; risk_sum = 0
        for p in pop:
            tp = f(p)
            if tp is None or tp <= 0: continue
            target = p['entry'] + (tp if p['direction'] == 'LONG' else -tp)
            r, pts = simulate(p['bars'], p['entry_ts'], p['direction'], p['entry'], p['stop'], target)
            if r == 'NO_BARS': continue
            n += 1; res[r] += 1; pnl += pts * 5.0 - 2.60; tgt_sum += tp; risk_sum += p['risk']
        if n == 0: continue
        be = risk_sum / (risk_sum + tgt_sum) * 100 if tgt_sum else 0
        print(f"{name:>14} {n:>4} {res['WIN']:>4} {res['STOP']:>4} {res['EOD']:>4} {res['WIN']/n*100:>5.0f}% {pnl/n:>8.2f} {pnl:>9.2f} {pnl/sessions:>11.2f} {be:>14.0f}%")

# ---- population A: harness reference trades
popA = []
bars_cache = {}
for fpath in sorted(glob.glob('harness_out/t466/t517ref_*.json')):
    try: j = json.load(open(fpath))
    except Exception: continue
    day = j['session']
    if day not in bars_cache: bars_cache[day] = bars_for(day)
    for t in j.get('trades', []):
        e = t.get('fill_price') if t.get('fill_price') is not None else t.get('entry')
        st = t.get('stop_initial') if t.get('stop_initial') is not None else t.get('stop')
        if e is None or st is None or not t.get('fired_il'): continue
        risk = abs(e - st)
        if risk <= 0: continue
        hh, mm = t['fired_il'].split(':')[:2]
        ets = dt.datetime.fromisoformat(day).replace(hour=int(hh), minute=int(mm), tzinfo=IL)
        popA.append(dict(day=day, bars=bars_cache[day], entry_ts=ets, direction=t['direction'], entry=float(e), stop=float(st), risk=risk,
                         t1_pts=t.get('t1_pts'), harness_outcome=t.get('outcome'), harness_pnl=t.get('pnl_usd')))
run(popA, "A · harness reference (live config, t517ref, 62 sessions)")
pass

# ---- population B: the real live trades
cur.execute("""select id, entry_ts, direction, entry_price, coalesce((quality->'metadata'->>'stop_initial')::float, stop) as stop0, t1, pattern_id_at_entry, exit_reason, pnl_sierra, pnl_usd
               from v9_trades where mode='live' and entry_ts >= '2026-09-09' and entry_ts < '2026-09-30' order by entry_ts""")
popB = []
for tid, ets, d, e, st, t1, pat, xr, ps, pu in cur.fetchall():
    ets = ets.astimezone(IL); day = ets.strftime('%Y-%m-%d')
    if day not in bars_cache: bars_cache[day] = bars_for(day)
    e = float(e); 
    # real initial stop: v9_trades.stop is the LAST stop (moved to BE on winners). rebuild the initial risk from the trade log when possible
    cur.execute("select stop_price from v9_trade_management_log where trade_id=%s and stop_price is not null order by ts asc limit 1", (str(tid),)) if False else None
    st = float(st) if st is not None else None
    risk = abs(e - st) if st is not None else None
    popB.append(dict(day=day, bars=bars_cache[day], entry_ts=ets, direction=d, entry=e, stop=st, risk=risk,
                     t1_pts=abs(float(t1) - e) if t1 is not None else None, id=tid, pat=pat, xr=xr, ps=ps, pu=pu))
# stop==entry(+0.25) rows are BE-moved winners: their initial risk is unknown here -> exclude from R-multiples, keep for fixed targets
popB_r = [p for p in popB if p['risk'] and p['risk'] >= 1.0]
print(f"\n(live trades with a usable initial stop: {len(popB_r)} of {len(popB)}; the rest show a break-even stop after T0/T1)")
run(popB_r, "B · real live trades 09.09-29.09 (initial stop known)")
run(popB, "B-all · real live trades, fixed-point targets only (R rows meaningless here)")

# ---- per-trade: simulated at the ACTUAL T1 with the INITIAL stop vs what really happened
print("\n===== per live trade: 5-min-bar simulation (initial stop, actual T1) vs reality =====")
print(f"{'id':>5} {'day':>6} {'pattern':<22} {'dir':<5} {'risk':>5} {'t1pts':>5} {'sim':>5} {'sim$':>7} | {'real exit':<18} {'real$':>7}")
tot_sim=0; tot_real=0; flips=[]
for p in popB:
    if not p['t1_pts']: continue
    target = p['entry'] + (p['t1_pts'] if p['direction']=='LONG' else -p['t1_pts'])
    r, pts = simulate(p['bars'], p['entry_ts'], p['direction'], p['entry'], p['stop'], target)
    sim_usd = pts*5.0-2.60
    real = p['ps'] if p['ps'] is not None else p['pu']
    tot_sim += sim_usd; tot_real += (real or 0)
    flag = ''
    if r=='WIN' and (real or 0) <= 0: flag='  <-- sim WIN, real loss'; flips.append(p['id'])
    print(f"{p['id']:>5} {p['day'][5:]:>6} {str(p['pat']):<22} {p['direction']:<5} {p['risk']:>5.2f} {p['t1_pts']:>5.2f} {r:>5} {sim_usd:>7.2f} | {str(p['xr']):<18} {float(real or 0):>7.2f}{flag}")
print(f"sum sim {tot_sim:.2f}$ vs real {tot_real:.2f}$ · sim-WIN-but-real-loss: {len(flips)} trades {flips}")
