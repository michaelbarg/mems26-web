"""
Phase 3.2 Day 1 — Multi-Track Strategy Optimization
Autonomous, read-only analysis on MDS dataset (~4,996 setups).
"""
import sys, os, json, time, itertools
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import polars as pl
from tools.multidim_sim.data_loader import get_dataset
from tools.multidim_sim.simulator_core import (
    simulate_outcomes, apply_sequential_filter, aggregate_metrics,
    COST_PER_CONTRACT, POINTS_TO_USD, RISK_PTS, compute_score_v2,
    _footprint_opposes, determine_qty
)

START = time.time()

# ── Load dataset ──
df_raw = get_dataset(os.environ['DATABASE_URL'])
# Add risk_pts column
df_raw = df_raw.with_columns([
    (pl.when(pl.col('direction') == 'LONG')
       .then(pl.col('entry_price') - pl.col('stop_price'))
       .otherwise(pl.col('stop_price') - pl.col('entry_price'))
    ).alias('risk_pts'),
])
df_raw = df_raw.filter(pl.col('risk_pts') > 0)
# Add MFE in R
df_raw = df_raw.with_columns([
    (pl.col('mfe_pts') / pl.col('risk_pts')).alias('mfe_R'),
    (pl.col('mae_pts') / pl.col('risk_pts')).alias('mae_R'),
])

print(f"Dataset: {len(df_raw)} setups with valid risk")

# ── Helper: run a config through simulate + sequential + metrics ──
def run_config(df, config, label=""):
    df_out = simulate_outcomes(df, config)
    df_seq = apply_sequential_filter(df_out)
    traded = df_seq.filter(pl.col('qty') > 0)
    m = aggregate_metrics(df_seq, config)
    return m, traded

# ── Helper: MFE-based PnL simulation (different exit strategies) ──
def mfe_pnl(traded_df, exit_strategy="current"):
    """Compute PnL using MFE data instead of DB outcome.

    Strategies:
    - current: all contracts at 1R or full stop
    - be_on_c1: move stop to BE after 1R touch; exit remaining at 2R or BE
    - partial_12: 2@1R + 1@2R, BE stop after 1R
    - partial_123: 1@1R + 1@2R + 1@3R, BE stop after each level
    - hold_2r: all contracts to 2R or full stop
    """
    results = []
    for row in traded_df.iter_rows(named=True):
        risk = row['risk_pts']
        mfe_r = row['mfe_R']
        qty = row['qty']
        cost = COST_PER_CONTRACT * qty

        if exit_strategy == "current":
            # All out at 1R or full stop
            if mfe_r >= 1.0:
                gross = risk * POINTS_TO_USD * qty
            else:
                gross = -risk * POINTS_TO_USD * qty

        elif exit_strategy == "be_on_c1":
            # After 1R touch, stop moves to BE. Hold for 2R.
            if mfe_r >= 2.0:
                gross = risk * POINTS_TO_USD * qty * 2  # all at 2R
            elif mfe_r >= 1.0:
                gross = 0  # touched 1R, BE'd out
            else:
                gross = -risk * POINTS_TO_USD * qty  # full stop

        elif exit_strategy == "partial_12":
            # 2 contracts at 1R, 1 runner to 2R (BE stop after 1R)
            if qty < 2:
                # Scale proportionally
                if mfe_r >= 2.0:
                    gross = risk * POINTS_TO_USD * qty * 1.5  # avg 1.5R
                elif mfe_r >= 1.0:
                    gross = risk * POINTS_TO_USD * qty * 0.67  # 2/3 at 1R, 1/3 BE
                else:
                    gross = -risk * POINTS_TO_USD * qty
            else:
                c12 = min(2, qty)
                runner = qty - c12
                if mfe_r >= 2.0:
                    gross = risk * POINTS_TO_USD * c12 + risk * POINTS_TO_USD * 2 * runner
                elif mfe_r >= 1.0:
                    gross = risk * POINTS_TO_USD * c12 + 0  # runner BE'd
                else:
                    gross = -risk * POINTS_TO_USD * qty

        elif exit_strategy == "partial_123":
            # Scale out 1@1R, 1@2R, 1@3R
            if qty >= 3:
                if mfe_r >= 3.0:
                    gross = risk * POINTS_TO_USD * (1 + 2 + 3)
                elif mfe_r >= 2.0:
                    gross = risk * POINTS_TO_USD * (1 + 2)  # 3rd at BE
                elif mfe_r >= 1.0:
                    gross = risk * POINTS_TO_USD * 1  # 2nd+3rd at BE
                else:
                    gross = -risk * POINTS_TO_USD * qty
            elif qty == 2:
                if mfe_r >= 2.0:
                    gross = risk * POINTS_TO_USD * (1 + 2)
                elif mfe_r >= 1.0:
                    gross = risk * POINTS_TO_USD * 1
                else:
                    gross = -risk * POINTS_TO_USD * qty
            else:
                if mfe_r >= 1.0:
                    gross = risk * POINTS_TO_USD * 1
                else:
                    gross = -risk * POINTS_TO_USD * qty

        elif exit_strategy == "hold_2r":
            if mfe_r >= 2.0:
                gross = risk * POINTS_TO_USD * qty * 2
            else:
                gross = -risk * POINTS_TO_USD * qty

        net = gross - cost
        results.append(net)

    return results

def compute_mfe_metrics(pnls, label=""):
    if not pnls:
        return {"label": label, "trades": 0, "wr": 0, "net": 0, "pf": 0, "max_dd": 0, "avg": 0}
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    net = sum(pnls)
    wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    win_sum = sum(p for p in pnls if p > 0)
    loss_sum = abs(sum(p for p in pnls if p < 0))
    pf = win_sum / loss_sum if loss_sum > 0 else float('inf') if win_sum > 0 else 0
    # Max drawdown
    cum = []
    s = 0
    for p in pnls:
        s += p
        cum.append(s)
    peak = float('-inf')
    max_dd = 0
    for c in cum:
        if c > peak:
            peak = c
        dd = peak - c
        if dd > max_dd:
            max_dd = dd
    avg = net / len(pnls)
    avg_win = sum(p for p in pnls if p > 0) / max(wins, 1)
    avg_loss = sum(p for p in pnls if p < 0) / max(losses, 1)
    return {
        "label": label, "trades": len(pnls), "wins": wins, "losses": losses,
        "wr": round(wr, 1), "net": round(net, 2), "pf": round(pf, 2),
        "max_dd": round(max_dd, 2), "avg": round(avg, 2),
        "avg_win": round(avg_win, 2), "avg_loss": round(avg_loss, 2),
    }

# ══════════════════════════════════════════════════════
# TRACK A: ENTRY FILTER OPTIMIZATION
# ══════════════════════════════════════════════════════
print("\n" + "="*60)
print("  TRACK A: ENTRY FILTER OPTIMIZATION")
print("="*60)

track_a_results = []

# Dimension 1: Score thresholds
thresholds = [40, 50, 60, 70, 80]
# Dimension 2: Day filters
day_filters = [
    ("all_days", "all_days"),
    ("skip_DEV", "skip_DEVELOPING"),
    ("skip_DEV+NORM", "skip_DEVELOPING_NEUTRAL"),
    ("TREND_only", "TREND_only"),
]
# Dimension 3: Killzone (we'll implement via post-filter since simulator doesn't natively support)
kz_filters = [
    ("all_kz", None),
    ("skip_OFF", ["OFF_HOURS"]),
    ("skip_London", ["London"]),
    ("NY_only", ["OFF_HOURS", "London"]),  # skip these = keep NY
]
# Dimension 4: Direction
dir_filters = [
    ("both", "both"),
    ("SHORT_only", "SHORT_only"),
]
# Dimension 5: VWAP overextension
vwap_filters = [
    ("no_vwap", False),
    ("skip_overext", True),
]
# Dimension 6: Footprint logic
fp_logics = [
    ("fp_weighted", "weighted"),
    ("fp_veto", "veto"),
    ("fp_off", "off"),
]
# Dimension 7: Weight combos
weight_combos = [
    ("w_25_30_25", 25, 30, 25),  # V2 default
    ("w_30_25_25", 30, 25, 25),
    ("w_20_20_40", 20, 20, 40),  # FVG heavy
    ("w_30_30_20", 30, 30, 20),  # Vegas+TPO heavy
]

# Run systematic grid (pruned — skip combos that would produce < 5 trades)
total_combos = 0
for thresh in thresholds:
    for day_label, day_val in day_filters:
        for kz_label, kz_skip in kz_filters:
            for dir_label, dir_val in dir_filters:
                for vwap_label, vwap_val in vwap_filters:
                    for fp_label, fp_val in fp_logics:
                        for w_label, vw, tw, fw in weight_combos:
                            config = {
                                'threshold': thresh,
                                'vegas_weight': vw,
                                'tpo_weight': tw,
                                'fvg_weight': fw,
                                'footprint_logic': fp_val,
                                'day_filter': day_val,
                                'direction_filter': dir_val,
                                'duration_max_minutes': 720,
                                'duration_penalty_factor': 0.0,
                                'skip_overextended': vwap_val,
                            }

                            label = f"t{thresh}|{day_label}|{kz_label}|{dir_label}|{vwap_label}|{fp_label}|{w_label}"

                            # Run simulator
                            m, traded = run_config(df_raw, config, label)

                            # Apply killzone post-filter if needed
                            if kz_skip and m['n_trades'] > 0:
                                # Re-run with kz filter applied to dataset
                                df_filtered = df_raw.filter(
                                    ~pl.col('killzone').is_in(kz_skip) | pl.col('killzone').is_null()
                                )
                                m, traded = run_config(df_filtered, config, label)

                            total_combos += 1

                            if m['n_trades'] >= 5:
                                # Also compute MFE-based PnL for "be_on_c1" strategy
                                if len(traded) > 0:
                                    mfe_pnls = mfe_pnl(traded, "be_on_c1")
                                    mfe_m = compute_mfe_metrics(mfe_pnls)
                                    be_net = mfe_m['net']
                                else:
                                    be_net = 0

                                track_a_results.append({
                                    'label': label,
                                    'config': config,
                                    'kz_skip': kz_skip,
                                    'trades': m['n_trades'],
                                    'wr': round(m['win_rate'] * 100, 1),
                                    'net_pnl': round(m['net_pnl_usd'], 2),
                                    'pf': round(m['profit_factor'], 2),
                                    'max_dd': round(m['max_drawdown_usd'], 2),
                                    'avg_trade': round(m['avg_trade_usd'], 2),
                                    'be_on_c1_net': round(be_net, 2),
                                })

print(f"  Tested {total_combos} combinations, {len(track_a_results)} with >= 5 trades")

# Sort by net_pnl
by_pnl = sorted(track_a_results, key=lambda x: x['net_pnl'], reverse=True)
by_pf = sorted([r for r in track_a_results if r['trades'] >= 30], key=lambda x: x['pf'], reverse=True)
by_dd = sorted([r for r in track_a_results if r['trades'] >= 30], key=lambda x: x['max_dd'])
by_be = sorted(track_a_results, key=lambda x: x['be_on_c1_net'], reverse=True)

print("\n  TOP 10 BY NET PNL:")
for i, r in enumerate(by_pnl[:10]):
    print(f"    {i+1}. {r['label'][:60]:<60} trades={r['trades']:>3} WR={r['wr']:>5.1f}% PnL=${r['net_pnl']:>8.2f} PF={r['pf']:>5.2f} DD=${r['max_dd']:>8.2f} BE_PnL=${r['be_on_c1_net']:>8.2f}")

print("\n  TOP 5 BY PROFIT FACTOR (min 30 trades):")
for i, r in enumerate(by_pf[:5]):
    print(f"    {i+1}. {r['label'][:60]:<60} trades={r['trades']:>3} PF={r['pf']:>5.2f} PnL=${r['net_pnl']:>8.2f}")

print("\n  TOP 5 BY LOWEST MAX DD (min 30 trades):")
for i, r in enumerate(by_dd[:5]):
    print(f"    {i+1}. {r['label'][:60]:<60} trades={r['trades']:>3} DD=${r['max_dd']:>8.2f} PnL=${r['net_pnl']:>8.2f}")

print("\n  TOP 10 BY BE-ON-C1 NET PNL:")
for i, r in enumerate(by_be[:10]):
    print(f"    {i+1}. {r['label'][:60]:<60} trades={r['trades']:>3} BE_PnL=${r['be_on_c1_net']:>8.2f} (orig=${r['net_pnl']:>8.2f})")

# ══════════════════════════════════════════════════════
# TRACK B: TRADE MANAGEMENT OPTIMIZATION
# ══════════════════════════════════════════════════════
print("\n" + "="*60)
print("  TRACK B: TRADE MANAGEMENT OPTIMIZATION")
print("="*60)

# Use V2 base config for entry
v2_base = {
    'threshold': 50, 'vegas_weight': 25, 'tpo_weight': 30,
    'fvg_weight': 25, 'footprint_logic': 'weighted',
    'day_filter': 'skip_DEVELOPING',
    'direction_filter': 'both',
    'duration_max_minutes': 720,
    'duration_penalty_factor': 0.0,
    'skip_overextended': False,
}

# Get V2 traded setups
_, v2_traded = run_config(df_raw, v2_base)
print(f"  V2 base traded setups: {len(v2_traded)}")

# Also get for threshold=70 and skip OFF_HOURS
v2_strict = {**v2_base, 'threshold': 70}
_, strict_traded = run_config(
    df_raw.filter(~pl.col('killzone').is_in(['OFF_HOURS']) | pl.col('killzone').is_null()),
    v2_strict
)
print(f"  Strict (t70, no OFF) traded: {len(strict_traded)}")

exit_strategies = ["current", "be_on_c1", "partial_12", "partial_123", "hold_2r"]

track_b_results = []

for strat in exit_strategies:
    for label_suffix, traded_set in [("v2_base", v2_traded), ("strict", strict_traded)]:
        if len(traded_set) == 0:
            continue
        pnls = mfe_pnl(traded_set, strat)
        m = compute_mfe_metrics(pnls, f"{strat}|{label_suffix}")
        m['strategy'] = strat
        m['entry_set'] = label_suffix
        track_b_results.append(m)

print(f"\n  TRADE MANAGEMENT RESULTS:")
print(f"  {'Strategy':<20} {'Entry':<10} {'Trades':>6} {'WR':>6} {'Net':>10} {'PF':>6} {'MaxDD':>8} {'AvgWin':>8} {'AvgLoss':>8}")
for r in track_b_results:
    print(f"  {r['strategy']:<20} {r['entry_set']:<10} {r['trades']:>6} {r['wr']:>5.1f}% ${r['net']:>9.2f} {r['pf']:>5.2f} ${r['max_dd']:>7.2f} ${r['avg_win']:>7.2f} ${r['avg_loss']:>7.2f}")

# BE Rescue Analysis
print(f"\n  BE RESCUE ANALYSIS (V2 base, {len(v2_traded)} trades):")
if len(v2_traded) > 0:
    losers = v2_traded.filter(pl.col('sim_outcome') == 'HIT_STOP')
    winners = v2_traded.filter(pl.col('sim_outcome') == 'HIT_C1')

    # Losers that touched 1R (would be saved by BE)
    losers_touched_1r = losers.filter(pl.col('mfe_R') >= 1.0)
    saved_value = len(losers_touched_1r) * RISK_PTS * POINTS_TO_USD * 3  # approx avg 3 contracts

    # But some losers had qty=2, so let's be precise
    saved_value_precise = 0
    for row in losers_touched_1r.iter_rows(named=True):
        saved_value_precise += row['risk_pts'] * POINTS_TO_USD * row['qty']

    # Winners that would have been stopped early (touched 1R but MFE < 2R)
    # These would exit at BE (0) instead of +1R
    winners_be_only = winners.filter((pl.col('mfe_R') >= 1.0) & (pl.col('mfe_R') < 2.0))
    lost_value = 0
    for row in winners_be_only.iter_rows(named=True):
        lost_value += row['risk_pts'] * POINTS_TO_USD * row['qty']  # lost the 1R profit

    # Winners that would have gotten MORE (2R+ instead of 1R)
    winners_2r = winners.filter(pl.col('mfe_R') >= 2.0)
    gained_value = 0
    for row in winners_2r.iter_rows(named=True):
        gained_value += row['risk_pts'] * POINTS_TO_USD * row['qty']  # extra 1R

    print(f"    Losers total:               {len(losers)}")
    print(f"    Losers that touched 1R:      {len(losers_touched_1r)} ({100*len(losers_touched_1r)/max(len(losers),1):.1f}%)")
    print(f"    Value saved (BE):            ${saved_value_precise:.2f}")
    print(f"    Winners total:               {len(winners)}")
    print(f"    Winners BE'd at 0 (1R<MFE<2R): {len(winners_be_only)} — lost value: ${lost_value:.2f}")
    print(f"    Winners reaching 2R+:        {len(winners_2r)} — extra gained: ${gained_value:.2f}")
    print(f"    NET RESCUE VALUE:            ${saved_value_precise - lost_value + gained_value:.2f}")

# ══════════════════════════════════════════════════════
# TRACK C: COMBINED OPTIMIZATION
# ══════════════════════════════════════════════════════
print("\n" + "="*60)
print("  TRACK C: COMBINED OPTIMIZATION")
print("="*60)

# Top 5 entry configs from Track A (by net_pnl)
top5_entries = by_pnl[:5]
# Top 5 exit strategies
top5_exits = exit_strategies  # all 5

track_c_results = []

for entry_cfg in top5_entries:
    config = entry_cfg['config'].copy()
    kz_skip = entry_cfg.get('kz_skip')

    df_work = df_raw.clone()
    if kz_skip:
        df_work = df_work.filter(~pl.col('killzone').is_in(kz_skip) | pl.col('killzone').is_null())

    _, traded = run_config(df_work, config)

    if len(traded) == 0:
        continue

    for exit_strat in top5_exits:
        pnls = mfe_pnl(traded, exit_strat)
        m = compute_mfe_metrics(pnls, f"{entry_cfg['label'][:40]}|{exit_strat}")

        # Walk-forward: 70/30 split by timestamp
        ts_sorted = sorted(traded['ts'].to_list())
        if len(ts_sorted) >= 10:
            split_idx = int(len(ts_sorted) * 0.7)
            split_ts = ts_sorted[split_idx]

            is_traded = traded.sort('ts')
            is_data = is_traded.head(split_idx)
            oos_data = is_traded.tail(len(is_traded) - split_idx)

            is_pnls = mfe_pnl(is_data, exit_strat)
            oos_pnls = mfe_pnl(oos_data, exit_strat)

            is_m = compute_mfe_metrics(is_pnls, "IS")
            oos_m = compute_mfe_metrics(oos_pnls, "OOS")
        else:
            is_m = {'net': 0, 'wr': 0, 'trades': 0}
            oos_m = {'net': 0, 'wr': 0, 'trades': 0}

        track_c_results.append({
            'label': m['label'],
            'entry': entry_cfg['label'][:40],
            'exit': exit_strat,
            **m,
            'is_net': is_m['net'],
            'is_wr': is_m.get('wr', 0),
            'is_trades': is_m['trades'],
            'oos_net': oos_m['net'],
            'oos_wr': oos_m.get('wr', 0),
            'oos_trades': oos_m['trades'],
        })

# Sort by OOS net
by_oos = sorted(track_c_results, key=lambda x: x['oos_net'], reverse=True)

print(f"\n  TOP 10 COMBINED CONFIGS BY OOS NET PNL:")
print(f"  {'Label':<50} {'Trades':>6} {'Net':>8} {'IS_Net':>8} {'OOS_Net':>8} {'OOS_WR':>6}")
for i, r in enumerate(by_oos[:10]):
    print(f"  {r['label'][:50]:<50} {r['trades']:>6} ${r['net']:>7.0f} ${r['is_net']:>7.0f} ${r['oos_net']:>7.0f} {r['oos_wr']:>5.1f}%")

# ══════════════════════════════════════════════════════
# TRACK D: ENTRY TYPE DEEP-DIVE
# ══════════════════════════════════════════════════════
print("\n" + "="*60)
print("  TRACK D: ENTRY TYPE DEEP-DIVE")
print("="*60)

# With available data, we can test:
# 1. Score timing: initial_score vs peak analysis (we only have 'score' = initial)
# 2. VWAP alignment
# 3. Footprint opposes as entry filter
# 4. Component score patterns

_, v2_traded_full = run_config(df_raw, v2_base)

if len(v2_traded_full) > 0:
    print(f"\n  V2 traded: {len(v2_traded_full)} setups")

    # Test: VWAP side alignment (LONG+below=good, SHORT+above=good)
    aligned = v2_traded_full.filter(
        ((pl.col('direction') == 'LONG') & (pl.col('vwap_side') == 'below'))
        | ((pl.col('direction') == 'SHORT') & (pl.col('vwap_side') == 'above'))
    )
    misaligned = v2_traded_full.filter(
        ((pl.col('direction') == 'LONG') & (pl.col('vwap_side') == 'above'))
        | ((pl.col('direction') == 'SHORT') & (pl.col('vwap_side') == 'below'))
    )

    for group_label, group_df in [("VWAP aligned", aligned), ("VWAP misaligned", misaligned)]:
        if len(group_df) > 0:
            pnls = mfe_pnl(group_df, "current")
            m = compute_mfe_metrics(pnls)
            be_pnls = mfe_pnl(group_df, "be_on_c1")
            be_m = compute_mfe_metrics(be_pnls)
            print(f"    {group_label:<20} trades={m['trades']:>3} WR={m['wr']:>5.1f}% Net=${m['net']:>8.2f} (BE: ${be_m['net']:>8.2f})")

    # Test: Footprint opposes flag
    reasons = v2_traded_full['score_reasons'].to_list()
    fp_opposes_mask = ['opposes' in (r or '').lower() for r in reasons]
    fp_aligned_mask = [not x for x in fp_opposes_mask]

    fp_opp = v2_traded_full.filter(pl.Series(fp_opposes_mask))
    fp_ali = v2_traded_full.filter(pl.Series(fp_aligned_mask))

    for group_label, group_df in [("FP aligned", fp_ali), ("FP opposes", fp_opp)]:
        if len(group_df) > 0:
            pnls = mfe_pnl(group_df, "current")
            m = compute_mfe_metrics(pnls)
            print(f"    {group_label:<20} trades={m['trades']:>3} WR={m['wr']:>5.1f}% Net=${m['net']:>8.2f}")

    # Test: Score bands on V2 traded
    print(f"\n  Score band analysis (V2 traded):")
    for lo, hi, label in [(50, 60, "50-59"), (60, 70, "60-69"), (70, 80, "70-79"), (80, 90, "80-89"), (90, 101, "90-100")]:
        band = v2_traded_full.filter((pl.col('new_score') >= lo) & (pl.col('new_score') < hi))
        if len(band) > 0:
            pnls = mfe_pnl(band, "current")
            m = compute_mfe_metrics(pnls)
            be_pnls = mfe_pnl(band, "be_on_c1")
            be_m = compute_mfe_metrics(be_pnls)
            avg_mfe = band['mfe_R'].mean()
            print(f"    {label:<8} trades={m['trades']:>3} WR={m['wr']:>5.1f}% Net=${m['net']:>8.2f} BE=${be_m['net']:>8.2f} avgMFE={avg_mfe:.2f}R")

    # Test: Component dominance
    print(f"\n  Which component drives winners?")
    winners = v2_traded_full.filter(pl.col('sim_outcome') == 'HIT_C1')
    losers = v2_traded_full.filter(pl.col('sim_outcome') == 'HIT_STOP')
    for comp in ['vegas_score', 'tpo_score', 'fvg_score', 'footprint_score']:
        w_avg = winners[comp].mean() if len(winners) > 0 else 0
        l_avg = losers[comp].mean() if len(losers) > 0 else 0
        delta = w_avg - l_avg
        print(f"    {comp:<18} win_avg={w_avg:>5.1f}  loss_avg={l_avg:>5.1f}  delta={delta:>+5.1f}")

    # Test: Day of week (from ts)
    print(f"\n  By day of week:")
    from datetime import datetime, timezone
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    v2_with_dow = v2_traded_full.with_columns([
        pl.col('ts').map_elements(
            lambda x: datetime.fromtimestamp(x, tz=timezone.utc).weekday(),
            return_dtype=pl.Int64
        ).alias('dow')
    ])
    for dow in range(7):
        day_df = v2_with_dow.filter(pl.col('dow') == dow)
        if len(day_df) > 0:
            pnls = mfe_pnl(day_df, "current")
            m = compute_mfe_metrics(pnls)
            print(f"    {dow_names[dow]:<4} trades={m['trades']:>3} WR={m['wr']:>5.1f}% Net=${m['net']:>8.2f}")

# ══════════════════════════════════════════════════════
# TRACK E: STRESS TEST & ROBUSTNESS
# ══════════════════════════════════════════════════════
print("\n" + "="*60)
print("  TRACK E: STRESS TEST & ROBUSTNESS")
print("="*60)

# Use best combined config from Track C
if by_oos:
    best = by_oos[0]
    print(f"\n  Best config: {best['label']}")
    print(f"  Full sample: {best['trades']} trades, ${best['net']:.2f} net")

    # Find the corresponding entry config and exit strategy
    best_entry = None
    for ec in top5_entries:
        if ec['label'][:40] == best['entry']:
            best_entry = ec
            break

    if best_entry:
        config = best_entry['config'].copy()
        kz_skip = best_entry.get('kz_skip')
        exit_strat = best['exit']

        df_work = df_raw.clone()
        if kz_skip:
            df_work = df_work.filter(~pl.col('killzone').is_in(kz_skip) | pl.col('killzone').is_null())

        _, traded = run_config(df_work, config)

        if len(traded) > 0:
            # 1. Random subset 50% — 10 iterations
            import random
            random.seed(42)
            subset_results = []
            indices = list(range(len(traded)))
            for trial in range(10):
                sample = random.sample(indices, len(indices) // 2)
                sample_df = traded[sample]
                pnls = mfe_pnl(sample_df, exit_strat)
                m = compute_mfe_metrics(pnls)
                subset_results.append(m['net'])

            mean_sub = sum(subset_results) / len(subset_results)
            stddev = (sum((x - mean_sub)**2 for x in subset_results) / len(subset_results)) ** 0.5
            print(f"\n  Random 50% subset (10 trials):")
            print(f"    Mean PnL: ${mean_sub:.2f}")
            print(f"    StdDev:   ${stddev:.2f}")
            print(f"    Range:    ${min(subset_results):.2f} to ${max(subset_results):.2f}")

            # 2. Walk-forward 5 splits
            print(f"\n  Walk-forward 5 splits:")
            sorted_traded = traded.sort('ts')
            n = len(sorted_traded)
            split_size = n // 5
            for fold in range(5):
                start = fold * split_size
                end = min((fold + 1) * split_size, n)
                fold_df = sorted_traded[start:end]
                pnls = mfe_pnl(fold_df, exit_strat)
                m = compute_mfe_metrics(pnls)
                # Get date range
                ts_start = fold_df['ts'][0]
                ts_end = fold_df['ts'][-1]
                d1 = datetime.fromtimestamp(ts_start, tz=timezone.utc).strftime('%m/%d')
                d2 = datetime.fromtimestamp(ts_end, tz=timezone.utc).strftime('%m/%d')
                print(f"    Fold {fold+1} ({d1}-{d2}): {m['trades']} trades, WR={m['wr']:.1f}%, ${m['net']:.2f}")

            # 3. By-date analysis
            print(f"\n  By-date PnL:")
            traded_with_date = traded.with_columns([
                pl.col('ts').map_elements(
                    lambda x: datetime.fromtimestamp(x, tz=timezone.utc).strftime('%Y-%m-%d'),
                    return_dtype=pl.Utf8
                ).alias('date_str')
            ])

            daily_pnls = {}
            for date_str in traded_with_date.select('date_str').unique().sort('date_str').to_series().to_list():
                day_df = traded_with_date.filter(pl.col('date_str') == date_str)
                pnls = mfe_pnl(day_df, exit_strat)
                daily_net = sum(pnls)
                daily_pnls[date_str] = (daily_net, len(pnls))

            for date_str in sorted(daily_pnls.keys()):
                net, cnt = daily_pnls[date_str]
                flag = " ← MAX LOSS" if net < -200 else (" ← BEST" if net == max(v for v, _ in daily_pnls.values()) else "")
                print(f"    {date_str}: {cnt:>3} trades, ${net:>8.2f}{flag}")

            # 4. Worst/best days
            sorted_days = sorted(daily_pnls.items(), key=lambda x: x[1][0])
            print(f"\n  Worst 3 days:")
            for d, (pnl, cnt) in sorted_days[:3]:
                print(f"    {d}: ${pnl:.2f} ({cnt} trades)")
            print(f"  Best 3 days:")
            for d, (pnl, cnt) in sorted_days[-3:]:
                print(f"    {d}: ${pnl:.2f} ({cnt} trades)")

# ══════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════
elapsed = time.time() - START
print(f"\n{'='*60}")
print(f"  FINAL SUMMARY (runtime: {elapsed:.1f}s)")
print(f"{'='*60}")

# V1 baseline (current production: no filters, all trades)
v1_config = {
    'threshold': 0, 'vegas_weight': 30, 'tpo_weight': 25,
    'fvg_weight': 25, 'footprint_logic': 'weighted',
    'day_filter': 'all_days', 'direction_filter': 'both',
    'duration_max_minutes': 720, 'skip_overextended': False,
}
m_v1, v1_traded = run_config(df_raw, v1_config)
v1_current_pnls = mfe_pnl(v1_traded, "current")
v1_m = compute_mfe_metrics(v1_current_pnls, "V1_current")

# V2 baseline
m_v2, v2t = run_config(df_raw, v2_base)
v2_current_pnls = mfe_pnl(v2t, "current")
v2_m = compute_mfe_metrics(v2_current_pnls, "V2_current")
v2_be_pnls = mfe_pnl(v2t, "be_on_c1")
v2_be_m = compute_mfe_metrics(v2_be_pnls, "V2_be")

# Best entry
best_entry_r = by_pnl[0] if by_pnl else None
# Best combined
best_combined = by_oos[0] if by_oos else None

# Store for report
summary_rows = [
    ("V1 (no filters, current exits)", v1_m),
    ("V2 (skip_DEV, current exits)", v2_m),
    ("V2 + BE-on-C1 exits", v2_be_m),
]

if best_entry_r:
    # Run best entry with current exit
    bc = best_entry_r['config'].copy()
    kzs = best_entry_r.get('kz_skip')
    dfw = df_raw
    if kzs:
        dfw = dfw.filter(~pl.col('killzone').is_in(kzs) | pl.col('killzone').is_null())
    _, bt = run_config(dfw, bc)
    bp = mfe_pnl(bt, "current")
    bm = compute_mfe_metrics(bp, "BestEntry_current")
    bp2 = mfe_pnl(bt, "be_on_c1")
    bm2 = compute_mfe_metrics(bp2, "BestEntry_BE")
    summary_rows.append((f"Best Entry ({best_entry_r['label'][:30]})", bm))
    summary_rows.append((f"Best Entry + BE-on-C1", bm2))

if best_combined:
    summary_rows.append((f"Best Combined OOS ({best_combined['label'][:30]})", best_combined))

print(f"\n  {'Config':<45} {'Trades':>6} {'WR':>6} {'Net':>10} {'PF':>6} {'MaxDD':>8}")
for label, m in summary_rows:
    trades = m.get('trades', 0)
    wr = m.get('wr', 0)
    net = m.get('net', 0)
    pf = m.get('pf', 0)
    dd = m.get('max_dd', 0)
    print(f"  {label:<45} {trades:>6} {wr:>5.1f}% ${net:>9.2f} {pf:>5.2f} ${dd:>7.2f}")

print(f"\n  Total runtime: {elapsed:.1f}s")
print(f"  Dataset: {len(df_raw)} setups")
print(f"  Track A configs tested: {total_combos}")
print(f"  Track A configs with >= 5 trades: {len(track_a_results)}")

# Save all results to JSON for report generation
output = {
    'track_a': {
        'total_tested': total_combos,
        'valid': len(track_a_results),
        'top20_pnl': by_pnl[:20],
        'top10_pf': by_pf[:10],
        'top5_dd': by_dd[:5],
        'top10_be': by_be[:10],
    },
    'track_b': track_b_results,
    'track_c': {
        'top10_oos': [dict(r) for r in by_oos[:10]],
    },
    'summary_rows': [(l, dict(m) if isinstance(m, dict) else m) for l, m in summary_rows],
    'runtime': elapsed,
}

output_path = os.path.join(os.path.dirname(__file__), 'results.json')
# Serialize carefully (some values may not be JSON-serializable)
def sanitize(obj):
    if isinstance(obj, float):
        if obj == float('inf'):
            return 999999
        if obj != obj:  # NaN
            return 0
        return obj
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [sanitize(v) for v in obj]
    return obj

with open(output_path, 'w') as f:
    json.dump(sanitize(output), f, indent=2, default=str)
print(f"\n  Results saved to: {output_path}")
