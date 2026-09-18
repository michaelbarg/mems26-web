#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ideal_precision.py — F18 · T-413 — Signature precision on ideal-entry bars.

Answers: "how many bars that LOOK like ideal entries actually lead to good trades?"

Loads the golden ideal-C entries from ideal_entries_v0.json, defines 6 signatures,
then scans ALL clean-session bars to compute precision, recall, $/trade, OOS split,
Wilson CI, plateau sweep, walk-forward, family analysis, and golden examples.

CLI:
    python3 scripts/ideal_precision.py                          # all sessions
    python3 scripts/ideal_precision.py --session 2026-09-17     # single
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import statistics
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'scripts'))
os.chdir(_ROOT)

from backend.env_loader import load_dotenv_file
load_dotenv_file(os.path.join(_ROOT, '.env'), override=False)

from backend.v9.db.read import read_all
import oracle_engine as oe

# ---------------------------------------------------------------------------
# Excluded sessions (same as oracle_engine + ideal_entries)
# ---------------------------------------------------------------------------
EXC: Set[str] = {
    '2026-06-09', '2026-06-10', '2026-06-11', '2026-06-12',
    '2026-06-17', '2026-06-18', '2026-06-19', '2026-06-26',
    '2026-07-10', '2026-07-24', '2026-07-28', '2026-07-29',
    '2026-09-16', '2026-09-17',
}
ROLL_DATES = oe.ROLL_DATES

# OOS boundary
OOS_DISC_END = '2026-07-31'    # June-July = discovery
OOS_VAL_START = '2026-08-01'   # Aug-Sep = validation

# ---------------------------------------------------------------------------
# Data loading (reuse oracle_engine)
# ---------------------------------------------------------------------------
def load_data(session_date: Optional[str] = None
              ) -> Tuple[Dict[str, List[Dict]], List[str], Dict[str, Dict]]:
    """Load bars grouped by day, clean days list, prev_va map."""
    bars_raw = read_all(
        """SELECT b.ts,
               (b.ts AT TIME ZONE 'Asia/Jerusalem')::date d,
               (b.ts AT TIME ZONE 'Asia/Jerusalem')::time t,
               b.open o, b.high h, b.low l, b.close c, b.volume v,
               cd.delta
        FROM v9_bars_5min_woodies b
        LEFT JOIN (SELECT DISTINCT ON (ts) ts, delta
                   FROM v9_bars_cumulative_delta
                   ORDER BY ts, created_at DESC) cd ON cd.ts = b.ts
        WHERE b.ts >= '2026-06-01'
          AND (b.ts AT TIME ZONE 'Asia/Jerusalem')::time BETWEEN '16:30' AND '23:00'
        ORDER BY b.ts""",
        {'d': session_date} if session_date else {}
    )
    by_day: Dict[str, List[Dict]] = collections.defaultdict(list)
    for b in bars_raw:
        by_day[str(b['d'])].append(b)

    exc = EXC | ROLL_DATES
    if session_date:
        days = [session_date] if session_date not in exc and len(by_day.get(session_date, [])) >= 40 else []
    else:
        days = [d for d in sorted(by_day) if d not in exc and len(by_day[d]) >= 40]

    # Build prev_va
    prev_va: Dict[str, Dict] = {}
    alld = sorted(by_day)
    for k, d in enumerate(alld):
        if k:
            pb = by_day[alld[k - 1]]
            prev_va[d] = oe.compute_developing_va(pb, len(pb) - 1) if len(pb) > 5 else {}

    return by_day, days, prev_va


# ---------------------------------------------------------------------------
# Features for a bar — reuse ideal_entries.features() logic
# ---------------------------------------------------------------------------
def compute_features(bs: List[Dict], i: int, short: bool, d: str,
                     prev_va: Dict[str, Dict]) -> Optional[Dict]:
    """Compute causal features for bar i in session bs.

    Same logic as ideal_entries.features() but standalone.
    """
    atr = oe.compute_atr(bs, i)
    if not atr or atr <= 0:
        return None
    b = bs[i]

    # Delta ratio
    deltas = [abs(float(x['delta'])) for x in bs[:i] if x['delta'] is not None]
    med_d = statistics.median(deltas) if len(deltas) > 5 else None
    dr = (float(b['delta']) / med_d) if (b['delta'] is not None and med_d) else None

    # Zone
    dev = oe.compute_developing_va(bs, i - 1) if i >= 4 else {}
    zone = oe.classify_zone_vs_developing_va(b['c'], dev) if dev else 'UNKNOWN'

    # Near prev VA edge
    pv = prev_va.get(d) or {}
    near_prev = bool(pv) and (
        abs(b['c'] - pv.get('val', 1e9)) <= 0.5 * atr or
        abs(b['c'] - pv.get('vah', 1e9)) <= 0.5 * atr
    )

    # Bars from extreme
    hi_i = max(range(i + 1), key=lambda k: bs[k]['h'])
    lo_i = min(range(i + 1), key=lambda k: bs[k]['l'])
    bsh, bsl = i - hi_i, i - lo_i
    bars_from_extreme = bsl if short else bsh
    at_extreme = (bsl == 0) if short else (bsh == 0)

    # Move from open
    mo = (b['c'] - bs[0]['o']) / atr
    with_day = (mo <= -0.5) if short else (mo >= 0.5)

    # IB
    ib_bars_count = min(12, len(bs))
    ib_h = max(x['h'] for x in bs[:ib_bars_count])
    ib_l = min(x['l'] for x in bs[:ib_bars_count])
    ext = 'up' if b['c'] > ib_h else 'down' if b['c'] < ib_l else 'none'
    with_ext = (ext == 'down' and short) or (ext == 'up' and not short)
    near_ib_edge = abs(b['c'] - ib_l) <= 0.5 * atr or abs(b['c'] - ib_h) <= 0.5 * atr

    # Bar shape
    rng = b['h'] - b['l']
    cp = ((b['c'] - b['l']) / rng) if rng > 0 else 0.5
    trigger_ok = (cp >= 0.7) if not short else (cp <= 0.3)
    body = abs(b['c'] - b['o']) / rng if rng > 0 else 0

    # Vol ratio
    vols = [float(x['v'] or 0) for x in bs[max(0, i - 5):i]]
    vmed = statistics.median(vols) if vols else 0
    vr = (float(b['v']) / vmed) if vmed > 0 else None

    # Pullback before
    seq = bs[max(0, i - 4):i]
    pull = sum(1 for x in seq[-3:] if ((x['c'] < x['o']) if not short else (x['c'] > x['o'])))

    # Structure break
    prev5 = bs[max(0, i - 5):i]
    brk = False
    if prev5:
        brk = (b['c'] < min(x['l'] for x in prev5)) if short else (b['c'] > max(x['h'] for x in prev5))

    return dict(
        atr=atr, hour=str(b['t'])[:5],
        ph=('A' if i < 3 else 'B' if i < 12 else 'C' if i < 54 else 'D'),
        zone=zone, near_prev_edge=near_prev, near_ib_edge=near_ib_edge,
        at_extreme=at_extreme, bars_from_extreme=bars_from_extreme,
        with_day=with_day, with_ext=with_ext, move_from_open_atr=round(mo, 2),
        trigger_ok=trigger_ok, body_ge_50=body >= 0.5,
        range_ge_08atr=rng >= 0.8 * atr,
        vol_trig=(vr is not None and vr >= 1.3),
        vol_ratio=round(vr, 2) if vr else None,
        delta_with=(dr is not None and ((dr <= -1) if short else (dr >= 1))),
        delta_ratio=round(dr, 2) if dr is not None else None,
        pullback_before=pull >= 2, structure_break=brk,
        rng=rng, cp=round(cp, 4),
        bar_o=b['o'], bar_h=b['h'], bar_l=b['l'], bar_c=b['c'],
        bar_v=b['v'], bar_delta=b['delta'],
    )


# ---------------------------------------------------------------------------
# Step 1: Load golden ideal-C entries
# ---------------------------------------------------------------------------
def load_golden_entries() -> List[Dict]:
    """Load ideal entries and filter to variant C criteria."""
    path = os.path.join(_ROOT, 'harness_out', 'oracle', 'ideal_entries_v0.json')
    with open(path) as f:
        all_entries = json.load(f)

    # Variant C: trigger_ok AND (delta_with OR vol_trig) AND range_ge_08atr
    golden = [
        e for e in all_entries
        if e.get('trigger_ok') and
           (e.get('delta_with') or e.get('vol_trig')) and
           e.get('range_ge_08atr')
    ]
    return golden


# ---------------------------------------------------------------------------
# Step 2: Signature checks
# ---------------------------------------------------------------------------
def check_s1(feat: Dict) -> bool:
    """S1 = trigger_ok AND range >= 0.8*ATR AND (delta_with OR vol_trig)"""
    return (feat['trigger_ok'] and feat['range_ge_08atr'] and
            (feat['delta_with'] or feat['vol_trig']))

def check_s2(feat: Dict) -> bool:
    """S2 = S1 AND structure_break"""
    return check_s1(feat) and feat['structure_break']

def check_s3(feat: Dict) -> bool:
    """S3 = S1 AND pullback_before"""
    return check_s1(feat) and feat['pullback_before']

def check_s4(feat: Dict) -> bool:
    """S4 = S1 AND near_ib_edge"""
    return check_s1(feat) and feat['near_ib_edge']

def check_s5(feat: Dict) -> bool:
    """S5 = S1 AND zone != 'IN_VA'"""
    return check_s1(feat) and feat['zone'] != 'IN_VA'

def check_s6(feat: Dict) -> bool:
    """S6 = S1 AND with_day"""
    return check_s1(feat) and feat['with_day']


SIGNATURES = {
    'S1': check_s1,
    'S2': check_s2,
    'S3': check_s3,
    'S4': check_s4,
    'S5': check_s5,
    'S6': check_s6,
}


# ---------------------------------------------------------------------------
# Step 3: Oracle GOOD label
# ---------------------------------------------------------------------------
def is_oracle_good(bs: List[Dict], i: int, atr: float, direction: str,
                   K: int = 12) -> bool:
    """GOOD = reaches 1.5*ATR target before 1*ATR stop within K bars."""
    c = bs[i]['c']
    T = max(8.0, 1.5 * atr)
    S = max(5.0, 1.0 * atr)
    for j in range(i + 1, min(i + 1 + K, len(bs))):
        hi, lo = bs[j]['h'], bs[j]['l']
        if direction == 'SHORT':
            if hi >= c + S and lo <= c - T:
                return False  # AMBIG
            if hi >= c + S:
                return False  # BAD
            if lo <= c - T:
                return True   # GOOD
        else:
            if lo <= c - S and hi >= c + T:
                return False  # AMBIG
            if lo <= c - S:
                return False  # BAD
            if hi >= c + T:
                return True   # GOOD
    return False  # NONE


# ---------------------------------------------------------------------------
# Wilson 90% CI
# ---------------------------------------------------------------------------
def wilson_ci(n_success: int, n_total: int, z: float = 1.645) -> Tuple[float, float]:
    """Wilson score interval at 90% confidence."""
    if n_total == 0:
        return (0.0, 0.0)
    p_hat = n_success / n_total
    denom = 1 + z * z / n_total
    center = (p_hat + z * z / (2 * n_total)) / denom
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n_total)) / n_total) / denom
    lo = max(0.0, center - spread)
    hi = min(1.0, center + spread)
    return (round(lo, 3), round(hi, 3))


# ---------------------------------------------------------------------------
# $/trade using oracle_engine
# ---------------------------------------------------------------------------
def dollar_per_trade(bs: List[Dict], i: int, atr: float, direction: str) -> Optional[float]:
    """Compute $/trade using oracle_engine's walk-forward model."""
    result = oe.compute_dollar_per_trade(bs, i, atr, direction)
    if result and not result.get('skip'):
        return result['pnl_usd']
    return None


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------
def analyze(session_date: Optional[str] = None) -> Dict[str, Any]:
    """Run the full ideal_precision analysis."""

    by_day, days, prev_va = load_data(session_date)
    golden = load_golden_entries()
    golden_keys = {(e['d'], e['entry_il'], e['dir']) for e in golden}
    print(f"Loaded {len(golden)} golden ideal-C entries across {len(set(e['d'] for e in golden))} sessions")
    print(f"Clean sessions: {len(days)}")

    # -----------------------------------------------------------------------
    # Scan all bars in clean sessions, compute features + signatures
    # -----------------------------------------------------------------------
    all_bars_feats: List[Dict] = []  # each: {d, bar_idx, dir, feat, sig_matches, is_golden, is_good}

    for d in days:
        bs = by_day[d]
        for i in range(len(bs)):
            atr = oe.compute_atr(bs, i)
            if atr is None or i < 5 or i > len(bs) - 3:
                continue

            for short in [True, False]:
                direction = 'SHORT' if short else 'LONG'
                dir_code = 'S' if short else 'L'
                feat = compute_features(bs, i, short, d, prev_va)
                if feat is None:
                    continue

                # Check trigger_ok direction alignment
                rng = bs[i]['h'] - bs[i]['l']
                cp = ((bs[i]['c'] - bs[i]['l']) / rng) if rng > 0 else 0.5
                if short and cp > 0.30:
                    continue  # SHORT needs cp <= 0.30
                if not short and cp < 0.70:
                    continue  # LONG needs cp >= 0.70

                # Only process bars where trigger_ok is True
                if not feat['trigger_ok']:
                    continue

                sig_matches = {
                    name: fn(feat)
                    for name, fn in SIGNATURES.items()
                }
                is_golden = (d, str(bs[i]['t'])[:5], dir_code) in golden_keys
                is_good = is_oracle_good(bs, i, atr, direction)

                dollar = dollar_per_trade(bs, i, atr, direction)

                all_bars_feats.append({
                    'd': d, 'bar_idx': i, 'dir': dir_code,
                    'hour': str(bs[i]['t'])[:5],
                    'feat': feat, 'sig_matches': sig_matches,
                    'is_golden': is_golden, 'is_good': is_good,
                    'atr': atr, 'dollar': dollar,
                    'bar': bs[i],
                })

    print(f"Total bars with trigger_ok: {len(all_bars_feats)} "
          f"(S: {sum(1 for x in all_bars_feats if x['dir']=='S')}, "
          f"L: {sum(1 for x in all_bars_feats if x['dir']=='L')})")

    # -----------------------------------------------------------------------
    # Step 3: Signature precision table
    # -----------------------------------------------------------------------
    sig_table = {}
    for sname in SIGNATURES:
        matched_s = [x for x in all_bars_feats if x['sig_matches'][sname] and x['dir'] == 'S']
        matched_l = [x for x in all_bars_feats if x['sig_matches'][sname] and x['dir'] == 'L']
        matched_all = matched_s + matched_l

        n_s = len(matched_s)
        n_l = len(matched_l)

        # Recall: what fraction of golden entries are caught
        golden_caught = sum(1 for x in matched_all if x['is_golden'])
        recall = golden_caught / len(golden) if golden else 0

        # Precision
        good_s = sum(1 for x in matched_s if x['is_good'])
        good_l = sum(1 for x in matched_l if x['is_good'])
        prec_s = good_s / n_s if n_s else 0
        prec_l = good_l / n_l if n_l else 0
        total_good = good_s + good_l
        total_n = n_s + n_l
        prec_all = total_good / total_n if total_n else 0

        # $/trade
        dollars = [x['dollar'] for x in matched_all if x['dollar'] is not None]
        avg_dollar = statistics.mean(dollars) if dollars else 0

        # OOS split
        disc = [x for x in matched_all if x['d'] <= OOS_DISC_END]
        val = [x for x in matched_all if x['d'] >= OOS_VAL_START]
        good_disc = sum(1 for x in disc if x['is_good'])
        good_val = sum(1 for x in val if x['is_good'])
        prec_disc = good_disc / len(disc) if disc else 0
        prec_val = good_val / len(val) if val else 0

        # Wilson CI
        ci_lo, ci_hi = wilson_ci(total_good, total_n)

        sig_table[sname] = {
            'N_S': n_s, 'N_L': n_l, 'recall': round(recall, 3),
            'prec_S': round(prec_s, 3), 'prec_L': round(prec_l, 3),
            'prec_all': round(prec_all, 3),
            'dollar_per_trade': round(avg_dollar, 2),
            'oos_disc': round(prec_disc, 3), 'oos_val': round(prec_val, 3),
            'ci_lo': ci_lo, 'ci_hi': ci_hi,
            'n_good': total_good, 'n_total': total_n,
        }

    # -----------------------------------------------------------------------
    # Plateau sweep on delta and vol thresholds
    # -----------------------------------------------------------------------
    plateau_results = {}
    delta_thresholds = [1.0, 1.5, 2.0]
    vol_thresholds = [1.2, 1.3, 1.5]

    for dt in delta_thresholds:
        for vt in vol_thresholds:
            key = f'd{dt}_v{vt}'
            matched = []
            for x in all_bars_feats:
                f = x['feat']
                # S1 with custom thresholds
                dr = f.get('delta_ratio')
                vr = f.get('vol_ratio')
                delta_ok = dr is not None and (
                    (dr <= -dt if x['dir'] == 'S' else dr >= dt)
                )
                vol_ok = vr is not None and vr >= vt
                if f['trigger_ok'] and f['range_ge_08atr'] and (delta_ok or vol_ok):
                    matched.append(x)
            n = len(matched)
            good = sum(1 for x in matched if x['is_good'])
            prec = good / n if n else 0
            plateau_results[key] = {
                'N': n, 'good': good, 'prec': round(prec, 3),
                'delta_thr': dt, 'vol_thr': vt,
            }

    # -----------------------------------------------------------------------
    # Step 4: Walk-forward (best signature by precision x recall)
    # -----------------------------------------------------------------------
    best_sig = max(sig_table, key=lambda s: sig_table[s]['prec_all'] * sig_table[s]['recall'])
    best_check = SIGNATURES[best_sig]

    wf_days: Dict[str, List[Dict]] = collections.defaultdict(list)
    for x in all_bars_feats:
        if x['sig_matches'][best_sig]:
            wf_days[x['d']].append(x)

    equity = 0.0
    equity_curve = []
    trades_per_day = []
    days_ge_200 = 0
    max_dd = 0.0
    peak = 0.0

    for d in sorted(wf_days):
        day_entries = sorted(wf_days[d], key=lambda x: x['bar_idx'])
        # 1 slot per day, 2 contracts; first matching bar per direction
        taken_s = False
        taken_l = False
        day_pnl = 0.0
        n_trades = 0

        for x in day_entries:
            if x['dir'] == 'S' and not taken_s:
                if x['dollar'] is not None:
                    day_pnl += x['dollar']
                    taken_s = True
                    n_trades += 1
            elif x['dir'] == 'L' and not taken_l:
                if x['dollar'] is not None:
                    day_pnl += x['dollar']
                    taken_l = True
                    n_trades += 1
            if taken_s and taken_l:
                break

        equity += day_pnl
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)
        equity_curve.append({'d': d, 'equity': round(equity, 2), 'pnl': round(day_pnl, 2)})
        trades_per_day.append(n_trades)
        if day_pnl >= 200:
            days_ge_200 += 1

    n_wf_days = len(equity_curve)
    avg_trades_day = statistics.mean(trades_per_day) if trades_per_day else 0
    pct_days_ge_200 = (days_ge_200 / n_wf_days * 100) if n_wf_days else 0

    walk_forward = {
        'best_sig': best_sig,
        'equity_final': round(equity, 2),
        'max_dd': round(max_dd, 2),
        'avg_trades_per_day': round(avg_trades_day, 2),
        'pct_days_ge_200': round(pct_days_ge_200, 1),
        'n_days': n_wf_days,
        'curve': equity_curve,
    }

    # -----------------------------------------------------------------------
    # Step 5: Family analysis
    # -----------------------------------------------------------------------
    family_a = []  # Leg start: bars_from_extreme >= 5
    family_b = []  # Continuation at extreme: at_extreme AND vol_trig AND stop_atr <= 1.0

    for x in all_bars_feats:
        if not x['sig_matches']['S1']:
            continue
        f = x['feat']
        if f['bars_from_extreme'] >= 5:
            family_a.append(x)
        if f['at_extreme'] and f['vol_trig']:
            # stop_atr <= 1.0 check: stop_pts = rng or atr-based, approximate
            stop_atr = f['rng'] / f['atr'] if f['atr'] > 0 else 999
            if stop_atr <= 1.0:
                family_b.append(x)

    def family_stats(members: List[Dict]) -> Dict:
        n = len(members)
        good = sum(1 for x in members if x['is_good'])
        prec = good / n if n else 0
        golden_in = sum(1 for x in members if x['is_golden'])
        recall = golden_in / len(golden) if golden else 0
        dollars = [x['dollar'] for x in members if x['dollar'] is not None]
        avg_d = statistics.mean(dollars) if dollars else 0

        # Walk-forward for family
        fam_days: Dict[str, List[Dict]] = collections.defaultdict(list)
        for x in members:
            fam_days[x['d']].append(x)
        fam_eq = 0.0
        fam_peak = 0.0
        fam_dd = 0.0
        for fd in sorted(fam_days):
            entries = sorted(fam_days[fd], key=lambda x: x['bar_idx'])
            taken_s = taken_l = False
            dpnl = 0.0
            for x in entries:
                if x['dir'] == 'S' and not taken_s and x['dollar'] is not None:
                    dpnl += x['dollar']; taken_s = True
                elif x['dir'] == 'L' and not taken_l and x['dollar'] is not None:
                    dpnl += x['dollar']; taken_l = True
                if taken_s and taken_l:
                    break
            fam_eq += dpnl
            fam_peak = max(fam_peak, fam_eq)
            fam_dd = max(fam_dd, fam_peak - fam_eq)

        return {
            'N': n, 'n_good': good, 'prec': round(prec, 3),
            'recall': round(recall, 3),
            'dollar_per_trade': round(avg_d, 2),
            'wf_equity': round(fam_eq, 2),
            'wf_max_dd': round(fam_dd, 2),
        }

    families = {
        'A_leg_start': family_stats(family_a),
        'B_continuation': family_stats(family_b),
    }

    # -----------------------------------------------------------------------
    # Step 6: Golden examples (10)
    # -----------------------------------------------------------------------
    golden_examples = []
    golden_bars = [x for x in all_bars_feats if x['is_golden']]
    for x in golden_bars[:10]:
        f = x['feat']
        sigs = [s for s, v in x['sig_matches'].items() if v]
        golden_examples.append({
            'd': x['d'], 'il': x['hour'], 'dir': x['dir'],
            'entry': x['bar']['c'],
            'stop': round(x['bar']['c'] + x['atr'] if x['dir'] == 'S'
                          else x['bar']['c'] - x['atr'], 2),
            'T1': round(x['bar']['c'] - 1.5 * x['atr'] if x['dir'] == 'S'
                        else x['bar']['c'] + 1.5 * x['atr'], 2),
            'delta': x['bar'].get('delta'),
            'volume': x['bar'].get('v'),
            'atr': round(x['atr'], 2),
            'features': {
                'trigger_ok': f['trigger_ok'],
                'range_ge_08atr': f['range_ge_08atr'],
                'delta_with': f['delta_with'],
                'vol_trig': f['vol_trig'],
                'structure_break': f['structure_break'],
                'pullback_before': f['pullback_before'],
                'near_ib_edge': f['near_ib_edge'],
                'with_day': f['with_day'],
                'zone': f['zone'],
            },
            'signatures': sigs,
        })

    return {
        'sig_table': sig_table,
        'plateau': plateau_results,
        'walk_forward': walk_forward,
        'families': families,
        'golden_examples': golden_examples,
        'n_golden': len(golden),
        'n_clean_sessions': len(days),
        'n_bars_scanned': len(all_bars_feats),
    }


# ---------------------------------------------------------------------------
# Report output
# ---------------------------------------------------------------------------
def write_report(result: Dict, out_path: str) -> None:
    """Write the markdown report."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    lines = ['# Ideal Entry Precision Report (F18 · T-413)\n']
    lines.append(f'Golden ideal-C entries: {result["n_golden"]}  ')
    lines.append(f'Clean sessions: {result["n_clean_sessions"]}  ')
    lines.append(f'Bars scanned (trigger_ok): {result["n_bars_scanned"]}\n')

    # Signature table
    lines.append('## Signature Precision Table\n')
    lines.append('| Signature | N(S) | N(L) | Recall | Prec(S) | Prec(L) | $/trade | OOS-disc | OOS-val | CI [lo-hi] |')
    lines.append('|-----------|------|------|--------|---------|---------|---------|----------|---------|------------|')
    for sname in ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']:
        s = result['sig_table'][sname]
        lines.append(
            f'| {sname} | {s["N_S"]} | {s["N_L"]} | {s["recall"]:.3f} | '
            f'{s["prec_S"]:.3f} | {s["prec_L"]:.3f} | ${s["dollar_per_trade"]:.2f} | '
            f'{s["oos_disc"]:.3f} | {s["oos_val"]:.3f} | [{s["ci_lo"]:.3f}-{s["ci_hi"]:.3f}] |'
        )

    # Plateau
    lines.append('\n## Plateau Sweep (delta x vol thresholds)\n')
    lines.append('| delta_thr | vol_thr | N | good | prec |')
    lines.append('|-----------|---------|---|------|------|')
    for key in sorted(result['plateau']):
        p = result['plateau'][key]
        lines.append(f'| {p["delta_thr"]} | {p["vol_thr"]} | {p["N"]} | {p["good"]} | {p["prec"]:.3f} |')

    # Walk-forward
    wf = result['walk_forward']
    lines.append(f'\n## Walk-Forward (best signature: {wf["best_sig"]})\n')
    lines.append(f'- Final equity: ${wf["equity_final"]:.2f}')
    lines.append(f'- Max drawdown: ${wf["max_dd"]:.2f}')
    lines.append(f'- Avg trades/day: {wf["avg_trades_per_day"]:.2f}')
    lines.append(f'- % days >= $200: {wf["pct_days_ge_200"]:.1f}%')
    lines.append(f'- Trading days: {wf["n_days"]}')
    lines.append('\n### Equity curve (last 10 days)\n')
    lines.append('| Date | Equity | Day P&L |')
    lines.append('|------|--------|---------|')
    for row in wf['curve'][-10:]:
        lines.append(f'| {row["d"]} | ${row["equity"]:.2f} | ${row["pnl"]:.2f} |')

    # Families
    lines.append('\n## Family Analysis\n')
    lines.append('| Family | N | Prec | Recall | $/trade | WF Equity | WF MaxDD |')
    lines.append('|--------|---|------|--------|---------|-----------|----------|')
    for fname, fdata in result['families'].items():
        lines.append(
            f'| {fname} | {fdata["N"]} | {fdata["prec"]:.3f} | {fdata["recall"]:.3f} | '
            f'${fdata["dollar_per_trade"]:.2f} | ${fdata["wf_equity"]:.2f} | ${fdata["wf_max_dd"]:.2f} |'
        )

    # Golden examples
    lines.append('\n## Golden Examples (10)\n')
    lines.append('| # | Date | Time | Dir | Entry | Stop | T1 | Delta | Vol | ATR | Signatures |')
    lines.append('|---|------|------|-----|-------|------|----|-------|-----|-----|------------|')
    for idx, g in enumerate(result['golden_examples'], 1):
        lines.append(
            f'| {idx} | {g["d"]} | {g["il"]} | {g["dir"]} | {g["entry"]} | '
            f'{g["stop"]} | {g["T1"]} | {g["delta"]} | {g["volume"]} | '
            f'{g["atr"]} | {", ".join(g["signatures"])} |'
        )

    with open(out_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"\nWrote report: {out_path}")


def print_summary(result: Dict) -> None:
    """Print summary table to stdout."""
    print(f"\n{'='*80}")
    print(f"IDEAL PRECISION REPORT — F18 · T-413")
    print(f"Golden entries: {result['n_golden']} | "
          f"Sessions: {result['n_clean_sessions']} | "
          f"Bars scanned: {result['n_bars_scanned']}")
    print(f"{'='*80}\n")

    print(f"{'Sig':4} {'N(S)':>5} {'N(L)':>5} {'Recall':>7} {'Prec(S)':>8} "
          f"{'Prec(L)':>8} {'$/trade':>9} {'OOS-D':>6} {'OOS-V':>6} {'CI':>16}")
    print('-' * 80)
    for sname in ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']:
        s = result['sig_table'][sname]
        print(f"{sname:4} {s['N_S']:5d} {s['N_L']:5d} {s['recall']:7.3f} "
              f"{s['prec_S']:8.3f} {s['prec_L']:8.3f} "
              f"${s['dollar_per_trade']:8.2f} {s['oos_disc']:6.3f} {s['oos_val']:6.3f} "
              f"[{s['ci_lo']:.3f}-{s['ci_hi']:.3f}]")

    print(f"\nPlateau sweep:")
    print(f"{'d_thr':>6} {'v_thr':>6} {'N':>5} {'good':>5} {'prec':>6}")
    for key in sorted(result['plateau']):
        p = result['plateau'][key]
        print(f"{p['delta_thr']:6.1f} {p['vol_thr']:6.1f} {p['N']:5d} {p['good']:5d} {p['prec']:6.3f}")

    wf = result['walk_forward']
    print(f"\nWalk-forward ({wf['best_sig']}): equity=${wf['equity_final']:.2f} "
          f"DD=${wf['max_dd']:.2f} trades/day={wf['avg_trades_per_day']:.2f} "
          f"days>=$200={wf['pct_days_ge_200']:.1f}%")

    print(f"\nFamilies:")
    for fname, fdata in result['families'].items():
        print(f"  {fname}: N={fdata['N']} prec={fdata['prec']:.3f} "
              f"recall={fdata['recall']:.3f} $/trade=${fdata['dollar_per_trade']:.2f} "
              f"WF=${fdata['wf_equity']:.2f} DD=${fdata['wf_max_dd']:.2f}")

    if result['golden_examples']:
        print(f"\nGolden examples ({len(result['golden_examples'])}):")
        for g in result['golden_examples']:
            print(f"  {g['d']} {g['il']} {g['dir']} entry={g['entry']} "
                  f"sigs={','.join(g['signatures'])}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="F18 Ideal Precision — T-413")
    parser.add_argument("--session", type=str, default=None,
                        help="Single session date (YYYY-MM-DD)")
    args = parser.parse_args()

    result = analyze(session_date=args.session)

    # Write JSON
    out_dir = os.path.join(_ROOT, 'harness_out', 'oracle')
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, 'ideal_precision_v0.json')
    with open(json_path, 'w') as f:
        json.dump(result, f, default=str, indent=2)
    print(f"Wrote {json_path}")

    # Write report
    report_path = os.path.join(_ROOT, 'docs', 'reports', 'IDEAL_ENTRIES_2026-09-18.md')
    write_report(result, report_path)

    # Print summary
    print_summary(result)


if __name__ == '__main__':
    main()
