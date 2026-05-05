#!/bin/bash
#
# MEMS26 — Phase 3.2 EOD Data Collection
# ─────────────────────────────────────────
# Version: 2.0 (added Block 7 — Counterfactual Analysis)
#
# Run at end of each trading day (16:00 ET / 23:00 IL or later)
# Output: paste back to Claude chat for journal entry
#
# Usage:
#   bash EOD_DATA_COLLECT.sh
#   bash EOD_DATA_COLLECT.sh "2026-05-04"   # specific date (UTC)

# ─── CONFIG ────────────────────────────────────────────────
BACKEND="https://mems26-web.onrender.com"
PHASE_START_UTC="2026-05-01 13:30:00"
TODAY_UTC="${1:-$(date -u +%F)}"

# ─── HEADER ────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════"
echo "  PHASE 3.2 — EOD Snapshot v2.0"
echo "  UTC date:        $TODAY_UTC"
echo "  Phase start:     $PHASE_START_UTC UTC"
echo "  Generated:       $(date -u +%FT%TZ)"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ─── 1. SEQUENTIAL TODAY SUMMARY ───────────────────────────
echo "── 1. TODAY'S EXECUTED TRADES (sequential summary) ──"
curl -s "${BACKEND}/analytics/setups/sequential_today_summary" \
  | python3 -m json.tool 2>/dev/null
echo ""

# ─── 2. SCORE BUCKET BREAKDOWN ─────────────────────────────
echo "── 2. SCORE BUCKET BREAKDOWN (executed only) ──"
curl -s "${BACKEND}/analytics/by_score_bucket" \
  | python3 -m json.tool 2>/dev/null
echo ""

# ─── 3. RECENT SETUPS WITH FULL DATA (last 100) ────────────
echo "── 3. RECENT 100 SETUPS — STATS ──"
curl -s "${BACKEND}/analytics/setups/recent?limit=100" \
  | python3 -c "
import json, sys
from collections import Counter
from datetime import datetime, timezone

try:
    d = json.load(sys.stdin)
except Exception as e:
    print(f'ERROR parsing JSON: {e}')
    sys.exit(0)

setups = d.get('setups', [])
phase_start = datetime(2026, 5, 1, 13, 30, tzinfo=timezone.utc)

clean = []
for s in setups:
    ts = s.get('created_at') or s.get('detected_at')
    if not ts: continue
    try:
        try:
            t = datetime.fromisoformat(ts.replace('Z','+00:00'))
        except:
            t = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
            t = t.replace(tzinfo=timezone.utc)
        if t >= phase_start:
            clean.append(s)
    except Exception:
        clean.append(s)

print(f'Total in API:       {len(setups)}')
print(f'In Phase window:    {len(clean)}')
print()

if not clean:
    print('No clean-window setups found yet.')
    sys.exit(0)

dir_counts = Counter(s.get('direction','?') for s in clean)
print(f'Direction split:    LONG={dir_counts.get(\"LONG\",0)} '
      f'SHORT={dir_counts.get(\"SHORT\",0)}')

def bucket(s):
    sc = s.get('peak_score') or s.get('score') or 0
    if sc < 30: return '<30'
    if sc < 50: return '30-49'
    if sc < 70: return '50-69'
    return '70+'
sc_counts = Counter(bucket(s) for s in clean)
print(f'Score buckets:      <30={sc_counts.get(\"<30\",0)} '
      f'30-49={sc_counts.get(\"30-49\",0)} '
      f'50-69={sc_counts.get(\"50-69\",0)} '
      f'70+={sc_counts.get(\"70+\",0)}')

dt_counts = Counter(s.get('day_type','?') for s in clean)
print(f'Day types:          {dict(dt_counts)}')

st_counts = Counter(s.get('setup_type','?') for s in clean)
print(f'Setup types:        {dict(st_counts)}')

kz_counts = Counter(s.get('killzone','?') for s in clean)
print(f'Killzones:          {dict(kz_counts)}')

def has(s, k):
    return s.get(k) not in (None, '', 'NULL')

tag_keys = ['rel_vol_at_entry', 'cvd_direction_at_entry',
            'vwap_side', 'mtf_aligned']
print()
print('Strategic tags completeness:')
for k in tag_keys:
    n = sum(1 for s in clean if has(s, k))
    pct = 100.0 * n / len(clean) if clean else 0
    print(f'  {k:30} {n:3}/{len(clean)} = {pct:.0f}%')

shadow_count = 0
shadow_sources = Counter()
shadow_qualities = Counter()
for s in clean:
    extra = s.get('extra_json')
    if isinstance(extra, str):
        try: extra = json.loads(extra)
        except: extra = {}
    if not isinstance(extra, dict):
        continue
    ss = extra.get('shadow_structural_stop')
    if ss:
        shadow_count += 1
        shadow_sources[ss.get('structural_stop_source','?')] += 1
        shadow_qualities[ss.get('structural_stop_quality','?')] += 1

print()
print(f'Shadow stop coverage: {shadow_count}/{len(clean)} '
      f'= {100.0*shadow_count/len(clean) if clean else 0:.0f}%')
print(f'  Sources:   {dict(shadow_sources)}')
print(f'  Qualities: {dict(shadow_qualities)}')
"
echo ""

# ─── 4. DATA QUALITY CHECK ─────────────────────────────────
echo "── 4. DATA QUALITY CHECK (system endpoint) ──"
curl -s "${BACKEND}/analytics/data_quality_check" \
  | python3 -m json.tool 2>/dev/null \
  | head -40
echo ""

# ─── 5. BRIDGE LOG TAIL ────────────────────────────────────
echo "── 5. BRIDGE LOG — LAST 30 LINES (filtered) ──"
if [ -f /tmp/bridge.log ]; then
    tail -30 /tmp/bridge.log | grep -iE "error|warn|push|setup|fail" \
      | head -30
else
    echo "/tmp/bridge.log NOT FOUND — bridge running?"
fi
echo ""

# ─── 6. ANOMALY HEURISTICS ─────────────────────────────────
echo "── 6. ANOMALY HEURISTICS ──"
curl -s "${BACKEND}/analytics/setups/recent?limit=20" \
  | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except:
    print('Could not parse setups')
    sys.exit(0)

setups = d.get('setups', [])
issues = []

for s in setups[:20]:
    sid = (s.get('setup_id') or '?')[:12]
    entry = s.get('entry')
    cp = s.get('current_price')
    if entry and cp and abs(float(entry)-float(cp)) > 30:
        issues.append(f'STALE_PRICE: {sid} entry={entry} curr={cp}')
    mae = s.get('mae_pts')
    if mae and float(mae) > 50:
        issues.append(f'MAE_OVER_50: {sid} mae={mae}pt')
    sc = s.get('peak_score') or s.get('score')
    if sc == 0:
        issues.append(f'SCORE_ZERO: {sid}')

if not issues:
    print('  ✓ No obvious anomalies in last 20 setups')
else:
    for i in issues[:10]:
        print(f'  ⚠ {i}')
"
echo ""

# ─── 7. SHADOW STOP COUNTERFACTUAL ANALYSIS (NEW!) ─────────
echo "── 7. SHADOW STOP COUNTERFACTUAL ANALYSIS ──"
echo "    (Compares hypothetical structural stops vs production fixed 5pt)"
echo ""
curl -s "${BACKEND}/analytics/setups/recent?limit=200" \
  | python3 -c "
import json, sys
from collections import defaultdict, Counter
from datetime import datetime, timezone

try:
    d = json.load(sys.stdin)
except:
    print('  ERROR: could not parse setups')
    sys.exit(0)

setups = d.get('setups', [])
phase_start = datetime(2026, 5, 1, 13, 30, tzinfo=timezone.utc)

# Filter to phase window AND with shadow stop
analyzed = []
for s in setups:
    ts = s.get('created_at') or s.get('detected_at')
    if not ts: continue
    try:
        try:
            t = datetime.fromisoformat(ts.replace('Z','+00:00'))
        except:
            t = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
            t = t.replace(tzinfo=timezone.utc)
        if t < phase_start:
            continue
    except:
        pass

    extra = s.get('extra_json')
    if isinstance(extra, str):
        try: extra = json.loads(extra)
        except: extra = {}
    if not isinstance(extra, dict):
        continue
    ss = extra.get('shadow_structural_stop')
    if not ss or not ss.get('structural_stop_valid'):
        continue
    analyzed.append((s, ss))

if not analyzed:
    print('  No setups with valid shadow stops in phase window yet.')
    sys.exit(0)

n = len(analyzed)
print(f'Setups analyzed:    {n} (with valid shadow stops)')
print()

# 7a. Aggregate diff
diffs = [float(ss.get('diff_pts') or 0) for _, ss in analyzed]
better_count = sum(1 for _, ss in analyzed if ss.get('structural_better'))
avg_diff = sum(diffs) / len(diffs) if diffs else 0
tighter_count = sum(1 for d in diffs if d < 0)
wider_count = sum(1 for d in diffs if d > 0)

print(f'7a. Aggregate vs fixed 5pt:')
print(f'    structural_better (tighter):  {better_count}/{n}'
      f' = {100.0*better_count/n:.0f}%')
print(f'    Avg diff_pts:                 {avg_diff:+.2f}'
      f' (negative = shadow tighter)')
print(f'    Tighter:                      {tighter_count}/{n}'
      f' = {100.0*tighter_count/n:.0f}%')
print(f'    Wider:                        {wider_count}/{n}'
      f' = {100.0*wider_count/n:.0f}%')
print()

# 7b. Per-source breakdown
print('7b. Per-source diff_pts breakdown:')
print(f'    {\"source\":<20} {\"n\":>5} {\"avg_pts\":>10} {\"avg_diff\":>10} {\"better%\":>10}')
print(f'    {\"-\"*20} {\"-\"*5} {\"-\"*10} {\"-\"*10} {\"-\"*10}')
by_source = defaultdict(list)
for s, ss in analyzed:
    src = ss.get('structural_stop_source','?')
    by_source[src].append(ss)

for src in sorted(by_source.keys()):
    items = by_source[src]
    avg_pts_src = sum(float(x.get('structural_stop_pts') or 0)
                      for x in items) / len(items)
    avg_diff_src = sum(float(x.get('diff_pts') or 0)
                       for x in items) / len(items)
    better_pct = 100.0 * sum(1 for x in items
                             if x.get('structural_better')) / len(items)
    print(f'    {src:<20} {len(items):>5} {avg_pts_src:>10.2f}'
          f' {avg_diff_src:>+10.2f} {better_pct:>9.0f}%')
print()

# 7c. Per-quality
print('7c. Per-quality breakdown:')
print(f'    {\"quality\":<20} {\"n\":>5} {\"avg_pts\":>10} {\"avg_diff\":>10}')
print(f'    {\"-\"*20} {\"-\"*5} {\"-\"*10} {\"-\"*10}')
by_qual = defaultdict(list)
for s, ss in analyzed:
    q = ss.get('structural_stop_quality','?')
    by_qual[q].append(ss)

for q in ['tight','normal','wide','fallback_atr','out_of_range']:
    items = by_qual.get(q, [])
    if not items:
        continue
    avg_pts_q = sum(float(x.get('structural_stop_pts') or 0)
                    for x in items) / len(items)
    avg_diff_q = sum(float(x.get('diff_pts') or 0)
                     for x in items) / len(items)
    print(f'    {q:<20} {len(items):>5} {avg_pts_q:>10.2f}'
          f' {avg_diff_q:>+10.2f}')
print()

# 7d. Counterfactual outcomes
print('7d. Counterfactual outcomes (executed setups with MAE):')

executed_with_mae = []
for s, ss in analyzed:
    mae = s.get('mae_pts')
    outcome = s.get('outcome')
    if mae is None or outcome is None:
        continue
    try:
        mae_val = float(mae)
        struct_pts = float(ss.get('structural_stop_pts') or 0)
        executed_with_mae.append({
            'sid': (s.get('setup_id') or '?')[:12],
            'mae': mae_val,
            'struct_pts': struct_pts,
            'fixed_pts': 5.0,
            'outcome': outcome,
            'pnl': s.get('net_pnl_usd'),
            'source': ss.get('structural_stop_source'),
            'quality': ss.get('structural_stop_quality'),
        })
    except:
        continue

if not executed_with_mae:
    print('    No executed setups with MAE data yet (need outcomes).')
else:
    saved_count = 0
    earlier_stop = 0
    same = 0

    for t in executed_with_mae:
        mae = t['mae']
        struct = t['struct_pts']
        fixed = t['fixed_pts']
        fixed_stopped = mae >= fixed
        shadow_stopped = mae >= struct

        if fixed_stopped and not shadow_stopped:
            saved_count += 1
        elif not fixed_stopped and shadow_stopped:
            earlier_stop += 1
        else:
            same += 1

    n_exec = len(executed_with_mae)
    print(f'    Executed analyzed:            {n_exec}')
    print(f'    Saved by shadow (wider):      {saved_count}'
          f' = {100.0*saved_count/n_exec:.0f}%')
    print(f'    Stopped earlier (tighter):    {earlier_stop}'
          f' = {100.0*earlier_stop/n_exec:.0f}%')
    print(f'    Same outcome:                 {same}'
          f' = {100.0*same/n_exec:.0f}%')

    if saved_count > 0:
        print()
        print('    🟢 Trades shadow would have SAVED:')
        for t in executed_with_mae:
            if t['mae'] >= t['fixed_pts'] and t['mae'] < t['struct_pts']:
                print(f'      • {t["sid"]}  mae={t["mae"]:.1f}pt'
                      f'  fixed_stopped@{t["fixed_pts"]:.1f}'
                      f'  shadow@{t["struct_pts"]:.1f}'
                      f'  ({t["source"]}, {t["quality"]})')

    if earlier_stop > 0:
        print()
        print('    🔴 Trades shadow would have stopped EARLIER:')
        for t in executed_with_mae:
            if t['mae'] < t['fixed_pts'] and t['mae'] >= t['struct_pts']:
                print(f'      • {t["sid"]}  mae={t["mae"]:.1f}pt'
                      f'  fixed_held@{t["fixed_pts"]:.1f}'
                      f'  shadow_stopped@{t["struct_pts"]:.1f}'
                      f'  ({t["source"]}, {t["quality"]})')

print()
print('    📋 Verdict guide:')
print('       structural_better < 30%  → V1 (fixed) is fine, no urgent change')
print('       structural_better 30-60% → V2 marginally better, A/B needed')
print('       structural_better > 60%  → V2 clearly better, plan activation 3.5')
"
echo ""

# ─── FOOTER ────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════"
echo "  END OF SNAPSHOT — paste this entire output to Claude chat"
echo "═══════════════════════════════════════════════════════════"
