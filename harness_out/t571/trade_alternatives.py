# -*- coding: utf-8 -*-
"""T-571 (08.10, Michael 15:5x): what would make one contract earn more in live — (1) which fired cells lose,
(2) smaller targets, (3) System-6-style early exits (time-stop / tight stop / stall-to-BE / label-change exit).
Read-only: re-simulates the 195 filled trades of the live-config replay (t564ref, 67 sessions) on
v9_bars_5min_woodies from the fill bar with the trade's own stop. Conservative bar order: stop before target.
Usage: LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8 python3 harness_out/t571/trade_alternatives.py [TAG]"""
import json, glob, subprocess, collections, sys, re
TAG = sys.argv[1] if len(sys.argv) > 1 else "t564ref"
PSQL = '/Applications/Postgres.app/Contents/Versions/latest/bin/psql'
COMM = 2.60; PT = 5.0
HOLD = {'2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-02','2026-10-05','2026-10-06'}
def q(sql):
    out = subprocess.run([PSQL, '-d', 'mems26', '-Atc', sql], capture_output=True, text=True).stdout
    return [l.split('|') for l in out.splitlines() if l]
BARS = collections.defaultdict(list)
for d, il, o, h, l, c in q("select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close from v9_bars_5min_woodies where symbol='MES' and ts>='2026-06-01' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts"):
    BARS[d].append((il, float(o), float(h), float(l), float(c)))
TR = []
for f in sorted(glob.glob(f'harness_out/t466/{TAG}_*.json')):
    d = json.load(open(f)); ses = d['session']
    labels = {s['il']: s.get('published') for s in d.get('s1') or []}
    paths = {}
    for g in d.get('gateway_decisions') or []:
        tid = str(g.get('trade_id'))
        if tid.startswith('FWD-live-') and g.get('tree_v3'):
            m = re.search(r"'id': '([^']*)'", str(g['tree_v3'])); paths[tid] = m.group(1) if m else ''
    for t in d['trades']:
        if not t.get('filled'): continue
        t = dict(t); t['session'] = ses; t['labels'] = labels; t['path'] = paths.get(str(t['trade_id']), '')
        t['exit_bar'] = t['legs'][-1]['bar_il']; TR.append(t)
print(f"{TAG}: {len(TR)} filled trades · sessions with bars {len(BARS)}")

def sim(t, start_off=1, t1_r=None, t1_abs=None, tstop=None, stop_r=None, stall_be=None, label_exit=False, be_after_mfe=None):
    """Walk bars from the fill bar + start_off. Returns (pts, exit_il, bars_held, exit_kind) or None if no bars."""
    bars = BARS.get(t['session']) or []
    fired = t['fired_il'][:5]
    idx = next((i for i, b in enumerate(bars) if b[0] >= fired), None)
    if idx is None: return None
    fill = float(t['fill_price'] or t['entry']); stop0 = float(t['stop_initial']); d = 1 if t['direction'] == 'LONG' else -1
    R = abs(fill - stop0) or 0.25
    stop = fill - d * (stop_r * R) if stop_r else stop0
    target = t1_abs if t1_abs is not None else (fill + d * t1_r * R if t1_r else float(t['t1_target']))
    lab0 = t['labels'].get(fired)
    mfe = 0.0; held = 0
    for i in range(idx + start_off, len(bars)):
        il, o, h, l, c = bars[i]; held += 1
        hit_stop = (l <= stop) if d == 1 else (h >= stop)
        hit_tgt = (h >= target) if d == 1 else (l <= target)
        if hit_stop: return (d * (stop - fill), il, held, 'STOP')
        if hit_tgt: return (d * (target - fill), il, held, 'T1')
        mfe = max(mfe, d * ((h if d == 1 else l) - fill))
        unreal = d * (c - fill)
        if label_exit and lab0 and t['labels'].get(il) and t['labels'][il] != lab0:
            return (unreal, il, held, 'LABEL')
        if tstop and held >= tstop and unreal <= 0: return (unreal, il, held, 'TIME')
        if stall_be and held >= stall_be and mfe >= 0.5 * R: stop = max(stop, fill) if d == 1 else min(stop, fill)
        if be_after_mfe and mfe >= be_after_mfe * R: stop = max(stop, fill) if d == 1 else min(stop, fill)
        if i == len(bars) - 1: return (unreal, il, held, 'EOD')
    return None

def run(name, **kw):
    rows = []
    for t in TR:
        r = sim(t, **kw)
        if r is None: continue
        pts, il, held, kind = r
        rows.append((t, pts * PT - COMM, il, held, kind))
    return rows
def summarize(name, rows, base=None):
    net = sum(r[1] for r in rows); wins = sum(1 for r in rows if r[1] > 0)
    hold = sum(r[1] for r in rows if r[0]['session'] in HOLD)
    months = collections.defaultdict(float)
    for r in rows: months[r[0]['session'][:7]] += r[1]
    line = f"{name:<28} Σnet {net:+9.2f}$ · win {wins/len(rows):4.0%} · holdout-10 {hold:+8.2f}$"
    if base is not None:
        bm = collections.defaultdict(float); bidx = {}
        for r in base: bm[r[0]['session'][:7]] += r[1]; bidx[r[0]['trade_id'] + r[0]['session']] = r
        dm = {m: months[m] - bm[m] for m in sorted(set(months) | set(bm))}
        bad = [m[5:] + f"{v:+.0f}" for m, v in dm.items() if v < -0.005]
        freed = 0; earlier = 0
        for r in rows:
            b = bidx.get(r[0]['trade_id'] + r[0]['session'])
            if b and r[3] < b[3]: freed += b[3] - r[3]; earlier += 1
        dh = hold - sum(r[1] for r in base if r[0]['session'] in HOLD)
        verdict = '✓' if (net - sum(r[1] for r in base) > 0 and dh >= 0 and not bad) else '✗'
        line += f" · Δ {net - sum(r[1] for r in base):+8.2f}$ · Δhold {dh:+7.2f}$ · months<0: {','.join(bad) or '—'} · earlier {earlier} ({freed} bars freed) {verdict}"
    print(line)
    return net
# calibration: does the re-simulation reproduce the harness? (start on the fired bar vs the next bar)
for off in (0, 1):
    rows = run('cal', start_off=off)
    match = sum(1 for r in rows if abs(r[1] - (float(r[0]['pnl_usd']) - COMM)) < 0.01)
    exits = sum(1 for r in rows if r[2] == r[0]['exit_bar'])
    print(f"calibration start_off={off}: pnl match {match}/{len(rows)} · exit-bar match {exits}/{len(rows)} · Σnet re-sim {sum(r[1] for r in rows):+.2f}$ vs harness {sum(float(r[0]['pnl_usd']) - COMM for r in rows):+.2f}$")

print("\n== alternatives (same engine, start_off=0; Δ vs re-simulated base; rule = Δnet>0 & Δholdout≥0 & no month<0) ==")
base = run('base', start_off=0); summarize('BASE own stop / own T1', base)
for r_ in (0.75, 1.0, 1.25, 2.0):
    summarize(f'T1 = {r_:.2f}R (own stop)', run('t1', start_off=0, t1_r=r_), base)
for k in (3, 6, 9, 12):
    summarize(f'time-stop {k} bars if ≤0', run('ts', start_off=0, tstop=k), base)
for s_ in (0.5, 0.75):
    summarize(f'tight stop {s_:.2f}R', run('st', start_off=0, stop_r=s_), base)
summarize('stall→BE after 6 bars+0.5R', run('sb', start_off=0, stall_be=6), base)
summarize('BE once MFE ≥ 0.75R', run('be', start_off=0, be_after_mfe=0.75), base)
summarize('BE once MFE ≥ 1.0R', run('be', start_off=0, be_after_mfe=1.0), base)
summarize('exit on S1 label change', run('lb', start_off=0, label_exit=True), base)
summarize('time-stop 6 + T1 1.0R', run('cb', start_off=0, tstop=6, t1_r=1.0), base)
summarize('time-stop 6 + BE≥0.75R', run('cb', start_off=0, tstop=6, be_after_mfe=0.75), base)
print("\n== where the fired trades lose (base, n≥6): cell = tree leaf id without the hour segment ==")
cells = collections.defaultdict(list)
for t, net, il, held, kind in base:
    key = '/'.join(s for s in t['path'].split('/') if not s.startswith('hour=')) or '(no path)'
    cells[key].append((t['session'], net))
rows = sorted(((k, v) for k, v in cells.items() if len(v) >= 6), key=lambda kv: sum(x[1] for x in kv[1]))
for k, v in rows:
    hold = sum(n for s, n in v if s in HOLD); w = sum(1 for s, n in v if n > 0)
    print(f"  {sum(x[1] for x in v):+8.2f}$ · n={len(v):3d} · win {w/len(v):4.0%} · holdout {hold:+7.2f}$ · {k}")
print("\n== by pattern × direction (base, n≥6) ==")
pc = collections.defaultdict(list)
for t, net, il, held, kind in base: pc[(t['classification'], t['direction'])].append((t['session'], net))
for k, v in sorted(((k, v) for k, v in pc.items() if len(v) >= 6), key=lambda kv: sum(x[1] for x in kv[1])):
    print(f"  {sum(x[1] for x in v):+8.2f}$ · n={len(v):3d} · win {sum(1 for s,n in v if n>0)/len(v):4.0%} · holdout {sum(n for s,n in v if s in HOLD):+7.2f}$ · {k[0]} {k[1]}")
print("\n== exit kinds (base) ==", collections.Counter(r[4] for r in base))
print("\n== losing leaves / patterns — per-month Σ (what a SKIP would remove; a positive month = a month the SKIP would cost) ==")
def months_of(sel):
    m = collections.defaultdict(float); n = 0
    for t, net, il, held, kind in base:
        if sel(t): m[t['session'][5:7]] += net; n += 1
    return n, ' '.join(f"{k}:{v:+.0f}" for k, v in sorted(m.items()))
for name, sel in (('leaf auction_B_reversal', lambda t: t['path'].split('/')[-1] == 'auction_B_reversal' or t['path'] == 'auction_B_reversal'),
                  ('leaf take_location', lambda t: t['path'] == 'take_location'),
                  ('OPENING_EXTREME_REJECT LONG', lambda t: t['classification'] == 'OPENING_EXTREME_REJECT' and t['direction'] == 'LONG'),
                  ('REACTIVE_LONG', lambda t: t['classification'] == 'REACTIVE_LONG'),
                  ('INITIATIVE_SHORT', lambda t: t['classification'] == 'INITIATIVE_SHORT')):
    n, s = months_of(sel); print(f"  {name:<30} n={n:3d} · {s}")
print("\n== auction_B_reversal trades (base) ==")
for t, net, il, held, kind in base:
    if 'auction_B_reversal' in t['path']:
        print(f"  {t['session']} {t['fired_il'][:5]} {t['classification']:<24} {t['direction']:<5} {net:+8.2f} {kind:<4} held {held:2d} · {t['path']}")
