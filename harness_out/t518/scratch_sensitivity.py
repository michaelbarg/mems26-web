"""T-518: what does the MAE scratch do to the 176 trades the live config takes in replay (t517ref, 62 sessions)?
The harness does not model S6_MAE_SCRATCH (live has it ON since 02.08). Same 5-min-bar simulator as target_sensitivity.py:
stop first, then scratch (adverse excursion >= per-pattern threshold from config/mae_scratch.yaml, fixed path), then target.
Scratch fill = threshold + 0.5pt slippage (the live scratches filled 0.2-1.2pt past the threshold). 1 contract, 2.60$/RT."""
import json, glob, os, datetime as dt, collections
import psycopg2, yaml
from zoneinfo import ZoneInfo
IL = ZoneInfo('Asia/Jerusalem')
conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://localhost/mems26')); cur = conn.cursor()
cfg = yaml.safe_load(open('config/mae_scratch.yaml'))
DEF = float(cfg.get('default_threshold_pts', 8.0)); MULT = float(cfg.get('responsive_multiplier', 1.5))
RESP = set(cfg.get('responsive_patterns', [])); OVR = cfg.get('pattern_thresholds', {}) or {}
def threshold(pat):
    p = (pat or '').upper()
    for k, v in OVR.items():
        if p.startswith(k.upper()): return float(v)
    for r in RESP:
        if r.upper() in p: return DEF * MULT
    return DEF
def bars_for(day):
    cur.execute("select ts, open, high, low, close from v9_bars_5min_woodies where ts >= %s::timestamptz and ts < %s::timestamptz order by ts",
                (f"{day} 16:30+03", f"{day} 23:00+03"))
    return [(r[0].astimezone(IL), float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in cur.fetchall()]
def atr14(bars, idx):
    seg = bars[max(0, idx-14):idx+1]
    if len(seg) < 2: return None
    trs = []
    for k in range(1, len(seg)):
        h, l, pc = seg[k][2], seg[k][3], seg[k-1][4]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs)/len(trs)
def sim(bars, ets, d, e, stop, target, thr, atr_k=None):
    sgn = 1 if d == 'LONG' else -1
    idx = next((i for i, b in enumerate(bars) if b[0] <= ets < b[0] + dt.timedelta(minutes=5)), None)
    if idx is None: return ('NO_BARS', 0.0)
    if atr_k is not None:
        a = atr14(bars, idx)
        thr = max(atr_k * a, 4.0) if a else thr
    for ts, o, h, l, c in bars[idx:]:
        adverse = (e - l) if sgn > 0 else (h - e)
        hit_stop = (l <= stop) if sgn > 0 else (h >= stop)
        hit_tgt = (h >= target) if sgn > 0 else (l <= target)
        if hit_stop: return ('STOP', sgn * (stop - e))
        if thr is not None and adverse >= thr: return ('SCRATCH', -(thr + 0.5))
        if hit_tgt: return ('WIN', sgn * (target - e))
    return ('EOD', sgn * (bars[-1][4] - e))
pop = []; cache = {}
for f in sorted(glob.glob('harness_out/t466/t517ref_*.json')):
    try: j = json.load(open(f))
    except Exception: continue
    day = j['session']; cache.setdefault(day, bars_for(day))
    for t in j.get('trades', []):
        e = t.get('fill_price') if t.get('fill_price') is not None else t.get('entry'); st = t.get('stop_initial') or t.get('stop')
        if e is None or st is None or not t.get('fired_il') or not t.get('t1_pts'): continue
        hh, mm = t['fired_il'].split(':')[:2]
        pop.append(dict(day=day, bars=cache[day], ets=dt.datetime.fromisoformat(day).replace(hour=int(hh), minute=int(mm), tzinfo=IL),
                        d=t['direction'], e=float(e), st=float(st), t1=float(t['t1_pts']), pat=t.get('classification')))
res = {}
for mode in ('no_scratch', 'scratch', 'scratch_atr'):
    c = collections.Counter(); pnl = 0.0; n = 0; per = {}
    for i, p in enumerate(pop):
        tgt = p['e'] + (p['t1'] if p['d'] == 'LONG' else -p['t1'])
        thr = threshold(p['pat']) if mode != 'no_scratch' else None
        r, pts = sim(p['bars'], p['ets'], p['d'], p['e'], p['st'], tgt, thr, atr_k=(threshold(p['pat'])/6.0 if mode == 'scratch_atr' else None))
        if r == 'NO_BARS': continue
        n += 1; c[r] += 1; usd = pts * 5 - 2.60; pnl += usd; per[i] = (r, usd)
    res[mode] = (n, c, pnl, per)
    print(f"{mode:>11}: n={n} {dict(c)} Σ={pnl:.2f}$  per-session={pnl/62:.2f}$")
for _m in ('scratch', 'scratch_atr'):
  a, b = res['no_scratch'][3], res[_m][3]
  print('==', _m)
  killed = [(i, a[i], b[i]) for i in a if i in b and a[i][0] == 'WIN' and b[i][0] == 'SCRATCH']
  saved = [(i, a[i], b[i]) for i in a if i in b and a[i][0] == 'STOP' and b[i][0] == 'SCRATCH']
  print(f"scratch effect: Δ = {res[_m][2]-res['no_scratch'][2]:.2f}$ · winners killed {len(killed)} (Σ {sum(x[1][1]-x[2][1] for x in killed):.2f}$ lost) · stops shortened {len(saved)} (Σ {sum(x[2][1]-x[1][1] for x in saved):.2f}$ saved)")
  byp = collections.defaultdict(lambda: [0, 0, 0.0])
  for i, (ra, ua) in a.items():
      rb, ub = b[i]; k = pop[i]['pat']; byp[k][0] += 1; byp[k][1] += (rb == 'SCRATCH'); byp[k][2] += ub - ua
  print("by pattern: n, scratched, Δ$")
  for k, v in sorted(byp.items(), key=lambda x: x[1][2]):
      if v[1]: print(f"  {k:<24} n={v[0]:>3} scratched={v[1]:>3} Δ={v[2]:>8.2f}$ (thr {threshold(k)})")
