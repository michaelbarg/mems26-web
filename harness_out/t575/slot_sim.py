# -*- coding: utf-8 -*-
"""T-575 (08.10, Michael 18:0x): one-slot sequential simulation of System-6 alternatives WITH the candidates that the
slot blocked — release-when-stuck, release-when-negative, swap-for-a-new-candidate, entry SKIPs — on the live-config
replay (t564ref, 67 sessions). Candidates = routes that fired live (outcome live) + routes blocked ONLY by the slot
(live_blocked_by=live_slot_occupied). Management engine = own stop / own T1 on v9_bars_5min_woodies (conservative bar
order: stop before target). Read-only; no harness. Caveat: a slot-freed candidate bypasses the gates the harness evaluates
after the slot (dedup/cooldown) — the full harness run (T-567c tonight) is the confirmation.
Usage: LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8 python3 harness_out/t575/slot_sim.py [TAG]"""
import json, glob, subprocess, collections, sys, re
TAG = sys.argv[1] if len(sys.argv) > 1 else "t564ref"
PSQL = '/Applications/Postgres.app/Contents/Versions/latest/bin/psql'
COMM = 2.60; PT = 5.0
HOLD = {'2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-02','2026-10-05','2026-10-06'}
def q(sql):
    out = subprocess.run([PSQL, '-d', 'mems26', '-Atc', sql], capture_output=True, text=True).stdout
    return [l.split('|') for l in out.splitlines() if l]
BARS = collections.defaultdict(list); IDX = {}
for d, il, o, h, l, c in q("select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close from v9_bars_5min_woodies where symbol='MES' and ts>='2026-06-01' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts"):
    BARS[d].append((il, float(o), float(h), float(l), float(c)))
for d, bl in BARS.items(): IDX[d] = {b[0]: i for i, b in enumerate(bl)}
SESS = {}
for f in sorted(glob.glob(f'harness_out/t466/{TAG}_*.json')):
    d = json.load(open(f)); ses = d['session']
    filled = {str(t['trade_id']): bool(t.get('filled')) for t in d['trades']}
    cands = []
    for r in d['routes']:
        m = re.search(r"FWD-live-\d+", str(r.get('exec'))); tid = m.group(0) if m else None
        live = tid is not None; slotblk = (not live) and 'live_slot_occupied' in str(r.get('live_blocked_by'))
        if not (live or slotblk): continue
        mp = re.search(r"'id': '([^']*)'", str(r.get('tree_v3'))); path = '/'.join(s for s in (mp.group(1) if mp else '').split('/') if not s.startswith('hour='))
        try: entry, stop, t1 = float(r['entry']), float(r['stop']), float(r['t1'])
        except (TypeError, ValueError): continue
        cands.append(dict(il=r['il'][:5], ts=r['il'], cls=r['classification'], dir=r['direction'], entry=entry, stop=stop, t1=t1,
                          kind='live' if live else 'slotblk', filled_h=(filled.get(tid) if live else None), path=path, tid=tid))
    cands.sort(key=lambda c: c['ts'])
    SESS[ses] = dict(cands=cands, labels={s['il']: s.get('published') for s in d.get('s1') or []})
print(f"{TAG}: sessions {len(SESS)} · live candidates {sum(1 for s in SESS.values() for c in s['cands'] if c['kind']=='live')} · slot-blocked candidates {sum(1 for s in SESS.values() for c in s['cands'] if c['kind']=='slotblk')}")

def walk(ses, c, rel_mfe=None, rel_neg=None, stop_il=None, swap_chk=None):
    """Manage candidate c from its fire bar. rel_mfe=(N,R): exit at close of bar N if MFE < R·risk. rel_neg=N: exit at
    close of bar N if unrealized ≤ 0. stop_il: (il, N, R) — at bar il, if held ≥ N and MFE < R·risk → exit at close ('SWAP').
    Returns (pts, exit_il, held, kind) or None (no bars)."""
    bars = BARS.get(ses) or []; i0 = IDX.get(ses, {}).get(c['il'])
    if i0 is None:
        i0 = next((i for i, b in enumerate(bars) if b[0] >= c['il']), None)
        if i0 is None: return None
    fill = c['entry']; stop = c['stop']; target = c['t1']; d = 1 if c['dir'] == 'LONG' else -1
    R = abs(fill - stop) or 0.25; mfe = 0.0; held = 0
    for i in range(i0, len(bars)):
        il, o, h, l, cl = bars[i]; held += 1
        if (l <= stop) if d == 1 else (h >= stop): return (d * (stop - fill), il, held, 'STOP')
        if (h >= target) if d == 1 else (l <= target): return (d * (target - fill), il, held, 'T1')
        mfe = max(mfe, d * ((h if d == 1 else l) - fill)); unreal = d * (cl - fill)
        if stop_il and il == stop_il[0] and held >= stop_il[1] and mfe < stop_il[2] * R: return (unreal, il, held, 'SWAP')
        if rel_mfe and held >= rel_mfe[0] and mfe < rel_mfe[1] * R: return (unreal, il, held, 'STUCK')
        if rel_neg and held >= rel_neg and unreal <= 0: return (unreal, il, held, 'TIME')
        if i == len(bars) - 1: return (unreal, il, held, 'EOD')
    return None
def fills(ses, c):
    """Fill model for slot-freed candidates: price must trade through the entry on the fire bar or the next one."""
    bars = BARS.get(ses) or []; i0 = IDX.get(ses, {}).get(c['il'])
    if i0 is None: return False
    return any(b[3] <= c['entry'] <= b[2] for b in bars[i0:i0 + 2])
def _mins(il): h, m = il.split(':'); return int(h) * 60 + int(m)
BASEWIN = {}
def simulate(skip=None, rel_mfe=None, rel_neg=None, swap=None, allow_freed=True):
    """One slot per session, candidates in time order. The slot frees one full bar after the exit bar (harness order).
    A slot-blocked candidate may enter only when (a) the slot is free here and (b) it fell inside a BASELINE trade window
    (i.e. the variant's early exit / skip is what freed it). swap=(N,R): when a candidate arrives while the open trade has
    held >= N bars with MFE < R*risk, close the open trade at that bar's close and take the candidate."""
    rows = []
    for ses, S in SESS.items():
        open_t = None
        for c in S['cands']:
            if open_t and _mins(c['il']) - _mins(open_t['exit_il']) >= 10: open_t = None
            if open_t and swap:
                r = walk(ses, open_t['c'], rel_mfe=rel_mfe, rel_neg=rel_neg, stop_il=(c['il'], swap[0], swap[1]))
                if r and r[3] == 'SWAP':
                    open_t['res'] = r; open_t['exit_il'] = r[1]; open_t = None
            if open_t: continue
            if c['kind'] == 'live' and c['filled_h'] is False: continue
            if c['kind'] == 'slotblk':
                if not allow_freed or not fills(ses, c): continue
                if not any(a <= c['il'] <= b for a, b in BASEWIN.get(ses, [])): continue
            if skip and skip(c): continue
            r = walk(ses, c, rel_mfe=rel_mfe, rel_neg=rel_neg)
            if r is None: continue
            open_t = dict(c=c, res=r, exit_il=r[1]); rows.append(open_t)
    return [(o['c'], o['res'][0] * PT - COMM, o['res'][1], o['res'][2], o['res'][3]) for o in rows]
def summarize(name, rows, base=None):
    net = sum(r[1] for r in rows); wins = sum(1 for r in rows if r[1] > 0)
    hold = sum(r[1] for r in rows if r[0]['ts'] and ses_of(r) in HOLD)
    months = collections.defaultdict(float)
    for r in rows: months[ses_of(r)[:7]] += r[1]
    added = sum(1 for r in rows if r[0]['kind'] == 'slotblk')
    line = f"{name:<34} Σnet {net:+9.2f}$ · n {len(rows):3d} (+{added} freed-slot) · win {wins/max(1,len(rows)):4.0%} · hold-10 {hold:+8.2f}$"
    if base is not None:
        bnet = sum(r[1] for r in base); bm = collections.defaultdict(float)
        for r in base: bm[ses_of(r)[:7]] += r[1]
        bad = [m[5:] + f"{months[m]-bm[m]:+.0f}" for m in sorted(set(months) | set(bm)) if months[m] - bm[m] < -0.005]
        dh = hold - sum(r[1] for r in base if ses_of(r) in HOLD)
        v = '✓' if (net - bnet > 0 and dh >= 0 and not bad) else '✗'
        kinds = collections.Counter(r[4] for r in rows)
        line += f" · Δ {net-bnet:+8.2f}$ · Δhold {dh:+7.2f}$ · months<0: {','.join(bad) or '—'} · exits {dict(kinds)} {v}"
    print(line); return net
_SES = {}
for ses, S in SESS.items():
    for c in S['cands']: _SES[id(c)] = ses
def ses_of(r): return _SES[id(r[0])]
is_B = lambda c: c['path'] == 'auction_B_reversal'
skipA = lambda c: is_B(c) and c['cls'] == 'OPENING_EXTREME_REJECT' and c['dir'] == 'LONG'
skipB = lambda c: is_B(c)
print("\n== one-slot sequential simulation (rule: Δnet>0 & Δhold≥0 & no month<0 vs base) ==")
base = simulate(allow_freed=False)
for r in base: BASEWIN.setdefault(ses_of(r), []).append((r[0]['il'], r[2]))
summarize('BASE (harness entries, own mgmt)', base)
print(f"   harness filled trades for comparison: 195 · Σnet +2,023.50$ (t564ref)")
for N in (6, 9, 12): summarize(f'release if stuck: {N} bars & MFE<1R', simulate(rel_mfe=(N, 1.0)), base)
for N in (6, 9, 12): summarize(f'release if stuck: {N} bars & MFE<0.5R', simulate(rel_mfe=(N, 0.5)), base)
for N in (6, 12): summarize(f'release if negative after {N} bars', simulate(rel_neg=N), base)
for N in (3, 6, 9): summarize(f'swap on new cand: held≥{N} & MFE<0.5R', simulate(swap=(N, 0.5)), base)
summarize('swap on new cand: held≥6 & MFE<1R', simulate(swap=(6, 1.0)), base)
summarize('SKIP A: ext-reject LONG in auction_B', simulate(skip=skipA), base)
summarize('SKIP B: whole auction_B_reversal', simulate(skip=skipB), base)
summarize('SKIP B + release stuck 9/1R', simulate(skip=skipB, rel_mfe=(9, 1.0)), base)
summarize('SKIP B + swap 6/0.5R', simulate(skip=skipB, swap=(6, 0.5)), base)
summarize('SKIP A + swap 6/0.5R', simulate(skip=skipA, swap=(6, 0.5)), base)
print("\n== freed-slot candidates that entered under 'swap 6/0.5R' (what the slot was hiding) ==")
rows = simulate(swap=(6, 0.5)); fr = [r for r in rows if r[0]['kind'] == 'slotblk']
pc = collections.defaultdict(list)
for r in fr: pc[(r[0]['cls'], r[0]['dir'])].append(r[1])
for k, v in sorted(pc.items(), key=lambda kv: -sum(kv[1]))[:12]:
    print(f"  {sum(v):+8.2f}$ · n={len(v):2d} · win {sum(1 for x in v if x>0)/len(v):4.0%} · {k[0]} {k[1]}")
