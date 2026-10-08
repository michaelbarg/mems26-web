# -*- coding: utf-8 -*-
"""T-576 (08.10, Michael 18:1x): "maximize day 1, write it into the tree, move to day 2" — measured walk-forward.
Two layers, both on the 195 live-config replay trades (t564ref) with the T-571 engine (own stop, bars from DB):
 (1) ENTRY lesson per cell (tree leaf without the hour segment): TAKE/SKIP decided by the cell's realized sign so far;
 (2) SYSTEM-6 lesson per cell: management menu {own T1, 1.0R, 2.0R} x {no time-stop, time-stop 12 bars} chosen by the
     cell's realized Σ so far.
Expanding walk-forward: for session k, lessons are learned on sessions 1..k-1 and applied to k (never to itself).
Read-only, no harness. Usage: LC_ALL=en_US.UTF-8 PYTHONIOENCODING=utf-8 python3 harness_out/t576/cell_mgmt_wf.py"""
import sys, collections
sys.argv = ['x']
_src = open('harness_out/t571/trade_alternatives.py', encoding='utf-8').read()
exec(_src.split('# calibration:')[0])          # BARS, TR, sim(), COMM, PT, HOLD
MENU = [dict(), dict(t1_r=1.0), dict(t1_r=2.0), dict(tstop=12), dict(t1_r=1.0, tstop=12), dict(t1_r=2.0, tstop=12)]
NAMES = ['own', '1.0R', '2.0R', 'own+ts12', '1.0R+ts12', '2.0R+ts12']
def cell(t): return '/'.join(s for s in t['path'].split('/') if not s.startswith('hour=')) or '(no path)'
sessions = sorted({t['session'] for t in TR}); by_s = collections.defaultdict(list)
for t in TR: by_s[t['session']].append(t)
res = {}
for t in TR:
    for mi, kw in enumerate(MENU):
        r = sim(t, start_off=0, **kw); res[(t['trade_id'], t['session'], mi)] = (r[0] * PT - COMM) if r else None
def net(t, mi): return res[(t['trade_id'], t['session'], mi)]
MIN_N = 6
hist = collections.defaultdict(list)
tot = dict(base=0.0, entry=0.0, s6=0.0, both=0.0); hold = dict(base=0.0, entry=0.0, s6=0.0, both=0.0)
skipped = 0; changed = 0; n_wf = 0; chosen = collections.Counter()
for k, s in enumerate(sessions):
    for t in by_s[s]:
        c = cell(t); own = net(t, 0)
        if own is None: continue
        h = hist[c]; n_wf += 1
        skip = len(h) >= MIN_N and sum(x[1] for x in h) < 0
        if len(h) >= MIN_N:
            sums = [sum((x[2][mi] if x[2][mi] is not None else 0) for x in h) for mi in range(len(MENU))]
            best = max(range(len(MENU)), key=lambda mi: sums[mi])
        else: best = 0
        v_entry = 0.0 if skip else own; v_s6 = net(t, best) if net(t, best) is not None else own
        v_both = 0.0 if skip else v_s6
        skipped += skip; changed += (best != 0); chosen[NAMES[best]] += 1
        for key, v in (('base', own), ('entry', v_entry), ('s6', v_s6), ('both', v_both)):
            tot[key] += v; hold[key] += v if s in HOLD else 0
        h.append((s, own, [net(t, mi) for mi in range(len(MENU))]))
print(f"walk-forward over {len(sessions)} sessions · {n_wf} trades · lessons learned only from earlier sessions (MIN_N={MIN_N})")
for key, label in (('base', 'BASE (live tree, own mgmt)'), ('entry', 'entry lesson: SKIP cells negative so far'), ('s6', 'system-6 lesson: best mgmt per cell so far'), ('both', 'both lessons')):
    print(f"  {label:<46} Σnet {tot[key]:+9.2f}$ · holdout-10 {hold[key]:+8.2f}$ · Δ {tot[key]-tot['base']:+8.2f}$ · Δhold {hold[key]-hold['base']:+7.2f}$")
print(f"  decisions changed by the lessons: skipped {skipped} · mgmt≠own {changed} · mgmt chosen {dict(chosen)}")
hs = sum(max(0.0, max(v for v in (net(t, mi) for mi in range(len(MENU))) if v is not None)) for t in TR if net(t, 0) is not None)
print(f"  HINDSIGHT (lesson learned from the same day: best mgmt per trade, losers skipped): Σ {hs:+.2f}$ — the ceiling that does not transfer")
# per-month Δ of the walk-forward lessons vs base (the acceptance rule's third number)
mon = collections.defaultdict(lambda: dict(base=0.0, entry=0.0, s6=0.0, both=0.0)); hist = collections.defaultdict(list)
for s in sessions:
    for t in by_s[s]:
        c = cell(t); own = net(t, 0)
        if own is None: continue
        h = hist[c]; skip = len(h) >= MIN_N and sum(x[1] for x in h) < 0
        best = max(range(len(MENU)), key=lambda mi: sum((x[2][mi] or 0) for x in h)) if len(h) >= MIN_N else 0
        v_s6 = net(t, best) if net(t, best) is not None else own
        m = mon[s[:7]]; m['base'] += own; m['entry'] += 0.0 if skip else own; m['s6'] += v_s6; m['both'] += 0.0 if skip else v_s6
        h.append((s, own, [net(t, mi) for mi in range(len(MENU))]))
for key in ('entry', 's6', 'both'):
    print(f"  months Δ ({key}): " + ' · '.join(f"{m[5:]} {v[key]-v['base']:+.0f}" for m, v in sorted(mon.items())))
