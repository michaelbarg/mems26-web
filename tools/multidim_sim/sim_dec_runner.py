"""
SIM-DEC Runner — Decision Layer V1.1 Backtest Suite.

SIM-DEC-01: Baseline backtest on full dataset
SIM-DEC-02: A/B Counterfactual (today only)
SIM-DEC-03: Threshold sensitivity sweep
SIM-DEC-04: Stage-by-stage attribution
SIM-DEC-05: Day-type × Decision interaction

Usage:
    python -m tools.multidim_sim.sim_dec_runner
"""

import json
import time
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import polars as pl

from .decision_layer import apply_decision_layer, decision_summary, DEFAULT_CONFIG
from .simulator_core import (
    simulate_outcomes, apply_sequential_filter, aggregate_metrics,
    COST_PER_CONTRACT, POINTS_TO_USD, RISK_PTS,
)

CACHE_DIR = Path(__file__).parent / "cache"
RESULTS_DIR = Path(__file__).parent / "results" / "decision_layer"


def _load_dataset() -> pl.DataFrame:
    """Load cached parquet (avoids DB dependency)."""
    candidates = sorted(CACHE_DIR.glob("setups_clean_*_full.parquet"))
    if not candidates:
        raise FileNotFoundError("No cached dataset found in cache/")
    path = candidates[-1]
    print(f"  Dataset: {path.name}")
    df = pl.read_parquet(path)
    # Add risk_pts
    df = df.with_columns([
        (pl.when(pl.col("direction") == "LONG")
           .then(pl.col("entry_price") - pl.col("stop_price"))
           .otherwise(pl.col("stop_price") - pl.col("entry_price"))
        ).alias("risk_pts"),
    ])
    df = df.filter(pl.col("risk_pts") > 0)
    df = df.with_columns([
        (pl.col("mfe_pts") / pl.col("risk_pts")).alias("mfe_R"),
        (pl.col("mae_pts") / pl.col("risk_pts")).alias("mae_R"),
    ])
    return df


def _pnl_for_group(group_df: pl.DataFrame) -> dict:
    """Compute PnL metrics using ACTUAL OUTCOME column (not MFE proxy).

    FIX (V8.4.0-RESEARCH-3): Previous version used mfe_R >= 1.0 as win,
    which inflated WR by 19pp. 948/4996 setups touch 1R then reverse to stop.
    Now uses the 'outcome' column: HIT_C1 = win, HIT_STOP = loss, TIMEOUT = flat.
    """
    if len(group_df) == 0:
        return {"trades": 0, "wins": 0, "losses": 0, "timeouts": 0,
                "wr": 0.0, "gross_pnl": 0.0, "net_pnl": 0.0, "avg_trade": 0.0}
    wins = 0
    losses = 0
    timeouts = 0
    total_gross = 0.0
    for row in group_df.iter_rows(named=True):
        risk = row["risk_pts"]
        outcome = row.get("outcome", "TIMEOUT")
        qty = 2  # standard 2-contract sizing for Decision Layer
        if outcome == "HIT_C1":
            total_gross += risk * POINTS_TO_USD * qty
            wins += 1
        elif outcome == "HIT_STOP":
            total_gross -= risk * POINTS_TO_USD * qty
            losses += 1
        else:  # TIMEOUT — flat exit, no PnL
            timeouts += 1
    n = wins + losses + timeouts
    # WR = wins / decisive trades (exclude timeouts from denominator)
    decisive = wins + losses
    wr = wins / decisive * 100 if decisive > 0 else 0.0
    costs = n * COST_PER_CONTRACT * 2
    net = total_gross - costs
    return {
        "trades": n, "wins": wins, "losses": losses, "timeouts": timeouts,
        "wr": round(wr, 1),
        "gross_pnl": round(total_gross, 2),
        "net_pnl": round(net, 2),
        "avg_trade": round(net / n, 2) if n > 0 else 0.0,
    }


# ══════════════════════════════════════════════════════════════
# SIM-DEC-01: Baseline Backtest
# ══════════════════════════════════════════════════════════════

def sim_dec_01(df: pl.DataFrame) -> dict:
    """Decision Layer V1.1 on all historical setups."""
    print("\n" + "=" * 60)
    print("  SIM-DEC-01: Decision Layer V1.1 Baseline Backtest")
    print("=" * 60)

    # Apply Decision Layer with default config
    df_dl = apply_decision_layer(df, DEFAULT_CONFIG)
    summary = decision_summary(df_dl)

    approved = df_dl.filter(pl.col("dl_decision") == "APPROVED")
    rejected = df_dl.filter(pl.col("dl_decision") == "REJECTED")

    # PnL for approved vs rejected (what we'd trade vs what we'd skip)
    pnl_approved = _pnl_for_group(approved)
    pnl_rejected = _pnl_for_group(rejected)
    pnl_all = _pnl_for_group(df_dl)  # V1 baseline (trade everything)

    # Score distribution for approved
    if len(approved) > 0:
        score_stats = {
            "mean": round(float(approved["dl_score"].mean()), 1),
            "median": round(float(approved["dl_score"].median()), 1),
            "min": round(float(approved["dl_score"].min()), 1),
            "max": round(float(approved["dl_score"].max()), 1),
        }
    else:
        score_stats = {}

    result = {
        "sim": "SIM-DEC-01",
        "config": DEFAULT_CONFIG,
        "decision_summary": summary,
        "pnl_approved": pnl_approved,
        "pnl_rejected": pnl_rejected,
        "pnl_v1_all": pnl_all,
        "pnl_delta_vs_v1": round(pnl_approved["net_pnl"] - pnl_all["net_pnl"], 2),
        "approved_score_stats": score_stats,
    }

    # Print
    print(f"\n  Dataset: {summary['total']} setups")
    print(f"  APPROVED: {summary['approved']} ({summary['approval_rate_pct']:.1f}%)")
    print(f"  REJECTED: {summary['rejected']}")
    print(f"  Rejection breakdown:")
    for stage, count in sorted(summary["rejected_by_stage"].items(),
                                key=lambda x: -x[1]):
        pct = count / summary["total"] * 100
        print(f"    {stage:<15} {count:>5} ({pct:.1f}%)")

    print(f"\n  PnL Comparison:")
    print(f"    V1 (all setups):   {pnl_all['trades']:>4} trades  "
          f"WR={pnl_all['wr']:>5.1f}%  Net=${pnl_all['net_pnl']:>10.2f}  "
          f"Avg=${pnl_all['avg_trade']:>7.2f}")
    print(f"    DL APPROVED:       {pnl_approved['trades']:>4} trades  "
          f"WR={pnl_approved['wr']:>5.1f}%  Net=${pnl_approved['net_pnl']:>10.2f}  "
          f"Avg=${pnl_approved['avg_trade']:>7.2f}")
    print(f"    DL REJECTED:       {pnl_rejected['trades']:>4} trades  "
          f"WR={pnl_rejected['wr']:>5.1f}%  Net=${pnl_rejected['net_pnl']:>10.2f}  "
          f"Avg=${pnl_rejected['avg_trade']:>7.2f}")
    print(f"\n  Delta vs V1: ${result['pnl_delta_vs_v1']:>+.2f}")
    print(f"  Money saved by rejecting: ${-pnl_rejected['net_pnl']:>+.2f}")

    # Acceptance criteria: APPROVED rate 5-20%
    rate = summary["approval_rate_pct"]
    if 5 <= rate <= 20:
        print(f"\n  ✅ PASS: Approval rate {rate:.1f}% is within 5-20% target")
    else:
        print(f"\n  ⚠️  OUTSIDE TARGET: Approval rate {rate:.1f}% "
              f"(target: 5-20%)")

    return result


# ══════════════════════════════════════════════════════════════
# SIM-DEC-02: A/B Counterfactual (Today)
# ══════════════════════════════════════════════════════════════

def sim_dec_02(df: pl.DataFrame) -> dict:
    """What would have happened today with Decision Layer active?"""
    print("\n" + "=" * 60)
    print("  SIM-DEC-02: A/B Counterfactual (Today)")
    print("=" * 60)

    # Filter to today's setups
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_ts = int(today_start.timestamp())

    today_df = df.filter(pl.col("ts") >= today_ts)

    if len(today_df) == 0:
        # Fall back to most recent day with data
        max_ts = df["ts"].max()
        day_start = int(max_ts) - (int(max_ts) % 86400)
        today_df = df.filter(pl.col("ts") >= day_start)
        day_label = datetime.fromtimestamp(day_start, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"  No setups today, using most recent day: {day_label}")
    else:
        day_label = now.strftime("%Y-%m-%d")

    print(f"  Date: {day_label}, {len(today_df)} setups")

    # Without Decision Layer (V1 = trade all)
    pnl_actual = _pnl_for_group(today_df)

    # With Decision Layer
    today_dl = apply_decision_layer(today_df, DEFAULT_CONFIG)
    approved = today_dl.filter(pl.col("dl_decision") == "APPROVED")
    rejected = today_dl.filter(pl.col("dl_decision") == "REJECTED")
    pnl_dl = _pnl_for_group(approved)
    pnl_rej = _pnl_for_group(rejected)
    summary = decision_summary(today_dl)

    delta = pnl_dl["net_pnl"] - pnl_actual["net_pnl"]

    result = {
        "sim": "SIM-DEC-02",
        "date": day_label,
        "n_setups": len(today_df),
        "decision_summary": summary,
        "pnl_actual_v1": pnl_actual,
        "pnl_with_dl": pnl_dl,
        "pnl_rejected": pnl_rej,
        "shadow_delta": round(delta, 2),
    }

    print(f"\n  Without DL (V1): {pnl_actual['trades']} trades, "
          f"WR={pnl_actual['wr']:.1f}%, Net=${pnl_actual['net_pnl']:.2f}")
    print(f"  With DL:         {pnl_dl['trades']} trades, "
          f"WR={pnl_dl['wr']:.1f}%, Net=${pnl_dl['net_pnl']:.2f}")
    print(f"  Rejected:        {pnl_rej['trades']} trades, "
          f"WR={pnl_rej['wr']:.1f}%, Net=${pnl_rej['net_pnl']:.2f}")
    print(f"\n  Shadow Delta: ${delta:>+.2f}")

    if delta > 0:
        print(f"  ✅ DL would have IMPROVED PnL by ${delta:.2f}")
    elif delta == 0:
        print(f"  ➖ DL would have had NO EFFECT")
    else:
        print(f"  ❌ DL would have REDUCED PnL by ${abs(delta):.2f}")

    return result


# ══════════════════════════════════════════════════════════════
# SIM-DEC-03: Threshold Sensitivity Sweep
# ══════════════════════════════════════════════════════════════

def sim_dec_03(df: pl.DataFrame) -> dict:
    """Sweep FP_MIN_SCORE and threshold to find sweet spot."""
    print("\n" + "=" * 60)
    print("  SIM-DEC-03: Threshold Sensitivity Sweep")
    print("=" * 60)

    thresholds = [30, 40, 50, 60, 70, 80]
    fp_min_scores = [0, 5, 8, 10, 12, 15]

    grid_results = []

    for thresh, fp_min in product(thresholds, fp_min_scores):
        cfg = {**DEFAULT_CONFIG, "threshold": thresh, "fp_min_score": fp_min}
        df_dl = apply_decision_layer(df, cfg)
        summary = decision_summary(df_dl)

        approved = df_dl.filter(pl.col("dl_decision") == "APPROVED")
        pnl = _pnl_for_group(approved)

        grid_results.append({
            "threshold": thresh,
            "fp_min_score": fp_min,
            "approved": summary["approved"],
            "approval_rate": summary["approval_rate_pct"],
            "trades": pnl["trades"],
            "wr": pnl["wr"],
            "net_pnl": pnl["net_pnl"],
            "avg_trade": pnl["avg_trade"],
        })

    # Find sweet spot: best net_pnl with approval_rate 5-20%
    in_range = [r for r in grid_results if 5 <= r["approval_rate"] <= 20]
    best = max(in_range, key=lambda x: x["net_pnl"]) if in_range else None

    result = {
        "sim": "SIM-DEC-03",
        "grid": grid_results,
        "sweet_spot": best,
        "monotonic_check": _check_monotonic(grid_results),
    }

    # Print grid
    print(f"\n  {'Thresh':>6} {'FP_MIN':>6} {'Appr':>5} {'Rate%':>6} "
          f"{'Trades':>6} {'WR%':>6} {'Net$':>10} {'Avg$':>8}")
    print(f"  {'-'*60}")
    for r in grid_results:
        marker = " ◀ BEST" if best and r == best else ""
        print(f"  {r['threshold']:>6} {r['fp_min_score']:>6} "
              f"{r['approved']:>5} {r['approval_rate']:>5.1f}% "
              f"{r['trades']:>6} {r['wr']:>5.1f}% "
              f"${r['net_pnl']:>9.2f} ${r['avg_trade']:>7.2f}{marker}")

    if best:
        print(f"\n  ✅ Sweet spot: threshold={best['threshold']}, "
              f"fp_min={best['fp_min_score']}, "
              f"Net=${best['net_pnl']:.2f}, "
              f"WR={best['wr']:.1f}%, "
              f"Rate={best['approval_rate']:.1f}%")
    else:
        print(f"\n  ⚠️  No config in 5-20% approval range")

    return result


def _check_monotonic(grid: list) -> dict:
    """Check if net_pnl is monotonically increasing with threshold."""
    by_thresh = {}
    for r in grid:
        t = r["threshold"]
        if t not in by_thresh:
            by_thresh[t] = []
        by_thresh[t].append(r["net_pnl"])

    avg_by_thresh = {t: sum(v) / len(v) for t, v in by_thresh.items()}
    sorted_vals = [avg_by_thresh[t] for t in sorted(avg_by_thresh.keys())]

    is_mono_inc = all(a <= b for a, b in zip(sorted_vals, sorted_vals[1:]))
    is_mono_dec = all(a >= b for a, b in zip(sorted_vals, sorted_vals[1:]))

    return {
        "avg_pnl_by_threshold": {str(k): round(v, 2) for k, v in avg_by_thresh.items()},
        "is_monotonic": is_mono_inc or is_mono_dec,
        "has_sweet_spot": not (is_mono_inc or is_mono_dec),
    }


# ══════════════════════════════════════════════════════════════
# SIM-DEC-04: Stage-by-Stage Attribution
# ══════════════════════════════════════════════════════════════

def sim_dec_04(df: pl.DataFrame) -> dict:
    """Which stage saves the most money?"""
    print("\n" + "=" * 60)
    print("  SIM-DEC-04: Stage-by-Stage Attribution")
    print("=" * 60)

    # Baseline: no Decision Layer (all traded)
    pnl_baseline = _pnl_for_group(df)

    # Full DL
    df_dl = apply_decision_layer(df, DEFAULT_CONFIG)
    approved_full = df_dl.filter(pl.col("dl_decision") == "APPROVED")
    pnl_full_dl = _pnl_for_group(approved_full)

    # Stage-only runs: enable ONLY one stage at a time
    stage_configs = {
        "Tournament_only": {
            **DEFAULT_CONFIG,
            "vwap_overextension_veto": False,
            "fp_min_score": 0,
            "fp_opposes_veto": False,
        },
        "VWAP_only": {
            **DEFAULT_CONFIG,
            "threshold": 0,
            "day_filter": "all_days",
            "skip_killzones": [],
            "direction_filter": "both",
            "fp_min_score": 0,
            "fp_opposes_veto": False,
        },
        "Footprint_only": {
            **DEFAULT_CONFIG,
            "threshold": 0,
            "day_filter": "all_days",
            "skip_killzones": [],
            "direction_filter": "both",
            "vwap_overextension_veto": False,
        },
    }

    stage_results = {}
    for stage_name, cfg in stage_configs.items():
        df_stage = apply_decision_layer(df, cfg)
        approved = df_stage.filter(pl.col("dl_decision") == "APPROVED")
        rejected = df_stage.filter(pl.col("dl_decision") == "REJECTED")

        pnl_approved = _pnl_for_group(approved)
        pnl_rejected = _pnl_for_group(rejected)

        savings = -pnl_rejected["net_pnl"]  # money saved = negative PnL of rejected setups

        stage_results[stage_name] = {
            "rejected_count": len(rejected),
            "pnl_approved": pnl_approved,
            "pnl_rejected": pnl_rejected,
            "savings_usd": round(savings, 2),
        }

    # Also compute: what each stage rejects that others don't (marginal)
    rej_tournament = set(df_dl.filter(pl.col("dl_rejected_by") == "Tournament")["id"].to_list())
    rej_vwap = set(df_dl.filter(pl.col("dl_rejected_by") == "VWAP")["id"].to_list())
    rej_fp = set(df_dl.filter(pl.col("dl_rejected_by") == "Footprint")["id"].to_list())

    result = {
        "sim": "SIM-DEC-04",
        "pnl_baseline_v1": pnl_baseline,
        "pnl_full_dl": pnl_full_dl,
        "full_dl_savings": round(pnl_full_dl["net_pnl"] - pnl_baseline["net_pnl"], 2),
        "stage_results": stage_results,
        "marginal_rejections": {
            "Tournament": len(rej_tournament),
            "VWAP": len(rej_vwap),
            "Footprint": len(rej_fp),
        },
    }

    print(f"\n  Baseline (V1, all): {pnl_baseline['trades']} trades, "
          f"Net=${pnl_baseline['net_pnl']:.2f}")
    print(f"  Full DL:           {pnl_full_dl['trades']} trades, "
          f"Net=${pnl_full_dl['net_pnl']:.2f}")
    print(f"  Full DL savings:   ${pnl_full_dl['net_pnl'] - pnl_baseline['net_pnl']:>+.2f}")

    print(f"\n  Per-Stage Attribution (solo):")
    print(f"  {'Stage':<20} {'Rejected':>8} {'Savings$':>10} {'Approved WR':>12}")
    for name, sr in stage_results.items():
        print(f"  {name:<20} {sr['rejected_count']:>8} "
              f"${sr['savings_usd']:>9.2f} "
              f"{sr['pnl_approved']['wr']:>10.1f}%")

    print(f"\n  Marginal rejections (in full DL pipeline):")
    for stage, count in result["marginal_rejections"].items():
        print(f"    {stage:<15} {count:>5} setups rejected at this stage")

    # Check: each stage saves > $0?
    all_positive = all(sr["savings_usd"] > 0 for sr in stage_results.values())
    if all_positive:
        print(f"\n  ✅ All stages save money — none redundant")
    else:
        for name, sr in stage_results.items():
            if sr["savings_usd"] <= 0:
                print(f"\n  ⚠️  {name} does NOT save money "
                      f"(${sr['savings_usd']:.2f}) — consider removing")

    return result


# ══════════════════════════════════════════════════════════════
# SIM-DEC-05: Day-Type × Decision Interaction
# ══════════════════════════════════════════════════════════════

def sim_dec_05(df: pl.DataFrame) -> dict:
    """Does Decision Layer work better in TREND vs RANGE?"""
    print("\n" + "=" * 60)
    print("  SIM-DEC-05: Day-Type × Decision Interaction")
    print("=" * 60)

    df_dl = apply_decision_layer(df, DEFAULT_CONFIG)

    day_types = df["day_type"].unique().drop_nulls().sort().to_list()

    matrix = {}
    for dt in day_types:
        dt_df = df_dl.filter(pl.col("day_type") == dt)
        if len(dt_df) < 5:
            continue

        approved = dt_df.filter(pl.col("dl_decision") == "APPROVED")
        rejected = dt_df.filter(pl.col("dl_decision") == "REJECTED")

        pnl_all = _pnl_for_group(dt_df)
        pnl_approved = _pnl_for_group(approved)
        pnl_rejected = _pnl_for_group(rejected)

        summary = decision_summary(dt_df)

        matrix[dt] = {
            "total": len(dt_df),
            "approved": len(approved),
            "rejected": len(rejected),
            "approval_rate": summary["approval_rate_pct"],
            "v1_all": pnl_all,
            "dl_approved": pnl_approved,
            "dl_rejected": pnl_rejected,
            "dl_savings": round(pnl_approved["net_pnl"] - pnl_all["net_pnl"], 2),
        }

    result = {
        "sim": "SIM-DEC-05",
        "matrix": matrix,
    }

    print(f"\n  {'Day Type':<15} {'Total':>5} {'Appr':>5} {'Rate%':>6} "
          f"{'V1 Net$':>10} {'DL Net$':>10} {'Delta$':>10} {'V1 WR':>6} {'DL WR':>6}")
    print(f"  {'-'*80}")
    for dt in sorted(matrix.keys()):
        m = matrix[dt]
        v1 = m["v1_all"]
        dl = m["dl_approved"]
        print(f"  {dt:<15} {m['total']:>5} {m['approved']:>5} "
              f"{m['approval_rate']:>5.1f}% "
              f"${v1['net_pnl']:>9.2f} ${dl['net_pnl']:>9.2f} "
              f"${m['dl_savings']:>9.2f} "
              f"{v1['wr']:>5.1f}% {dl['wr']:>5.1f}%")

    # Analyze: does DL help more in certain day types?
    best_dt = max(matrix.items(), key=lambda x: x[1]["dl_savings"])[0] if matrix else None
    worst_dt = min(matrix.items(), key=lambda x: x[1]["dl_savings"])[0] if matrix else None

    if best_dt:
        print(f"\n  Best DL impact:  {best_dt} (saves ${matrix[best_dt]['dl_savings']:+.2f})")
        print(f"  Worst DL impact: {worst_dt} (${matrix[worst_dt]['dl_savings']:+.2f})")

    # Check: playbook-per-day-type hypothesis
    all_positive = all(m["dl_savings"] >= 0 for m in matrix.values())
    if all_positive:
        print(f"\n  ✅ DL improves or matches V1 across ALL day types")
    else:
        negative_dts = [dt for dt, m in matrix.items() if m["dl_savings"] < 0]
        print(f"\n  ⚠️  DL HURTS in: {', '.join(negative_dts)}")
        print(f"      Consider day-type-adaptive DL config")

    return result


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def run_all():
    start = time.time()

    print("=" * 60)
    print("  SIM-DEC: Decision Layer V1.1 Backtest Suite")
    print(f"  Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    df = _load_dataset()
    print(f"  Loaded: {len(df)} setups with valid risk")

    results = {}
    results["01_baseline"] = sim_dec_01(df)
    results["02_counterfactual"] = sim_dec_02(df)
    results["03_threshold_sweep"] = sim_dec_03(df)
    results["04_stage_attribution"] = sim_dec_04(df)
    results["05_day_type_interaction"] = sim_dec_05(df)

    elapsed = time.time() - start

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"sim_dec_{ts}.json"

    # Sanitize for JSON
    def sanitize(obj):
        if isinstance(obj, float):
            if obj != obj:  # NaN
                return 0
            if obj == float("inf"):
                return 999999
            return obj
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        return obj

    with open(out_path, "w") as f:
        json.dump(sanitize(results), f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  COMPLETE — {elapsed:.1f}s")
    print(f"  Results: {out_path}")
    print(f"{'='*60}")

    return results


if __name__ == "__main__":
    run_all()
