"""
MDS-V1.0.1 CLI — single entry point.

Usage:
    python -m tools.multidim_sim load [--refresh]
    python -m tools.multidim_sim simulate --config v1_production
    python -m tools.multidim_sim grid [--n 2000] [--test]
    python -m tools.multidim_sim sanity
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import polars as pl
import yaml

from .data_loader import get_dataset, get_dataset_stats
from .simulator_core import run_single_config


def cmd_load(args):
    """Fetch + cache dataset."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    df = get_dataset(db_url, force_refresh=args.refresh,
                     filter_post_v814=args.post_v814)
    stats = get_dataset_stats(df)
    print(f"\n✓ Loaded {len(df)} setups")
    for k, v in stats.items():
        print(f"  {k}: {v}")


def cmd_simulate(args):
    """Run single config simulation."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    df = get_dataset(db_url, filter_post_v814=args.post_v814)

    # Load config from parameter_space.yaml baselines
    spec_path = Path(__file__).parent / "parameter_space.yaml"
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    if args.config not in spec.get("baselines", {}):
        print(f"ERROR: config '{args.config}' not in baselines", file=sys.stderr)
        available = list(spec.get("baselines", {}).keys())
        print(f"Available: {available}", file=sys.stderr)
        sys.exit(1)

    config = spec["baselines"][args.config]
    metrics = run_single_config(df, config)

    print(f"\n=== Simulation: {args.config} ({len(df)} setups) ===")
    for k, v in metrics.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for k2, v2 in v.items():
                print(f"    {k2}: {v2}")
        else:
            print(f"  {k}: {v}")


def cmd_grid(args):
    """Run Phase 1 Grid sweep."""
    from .grid_runner import run_grid, save_grid_results
    from .analyzer import top_n_configs, hot_zone_analysis, categorical_analysis

    n = 200 if args.test else args.n

    print(f"\n=== Phase 1 Grid Run ===")
    print(f"  LHS samples: {n}")
    print(f"  Mode: {'TEST' if args.test else 'FULL'}")

    grid_df = run_grid(n_lhs_samples=n, n_jobs=args.jobs)

    out_path = save_grid_results(grid_df)

    # Summary
    valid_count = int((grid_df["composite_score"] > float("-inf")).sum())
    print(f"\n=== Summary ===")
    print(f"  Total configs evaluated: {len(grid_df)}")
    print(f"  Valid (passed hard penalties): {valid_count} ({valid_count/len(grid_df)*100:.1f}%)")

    if valid_count > 0:
        top = top_n_configs(grid_df, n=10)

        display_cols = [c for c in [
            "rank", "composite_score", "win_rate", "n_trades",
            "net_pnl_usd", "profit_factor",
            "cfg_threshold", "cfg_vegas_weight", "cfg_tpo_weight", "cfg_fvg_weight",
            "cfg_footprint_logic", "cfg_day_filter", "cfg_skip_overextended",
        ] if c in top.columns]

        print(f"\n=== Top 10 Configs ===")
        with pl.Config(tbl_cols=15, tbl_width_chars=160, fmt_float="mixed"):
            print(top.select(display_cols))

        print(f"\n=== V1 Comparison ===")
        print(f"  V1 baseline: WR 42.86%, n_trades 3,158, NetPnL -$46,914")
        best = top.row(0, named=True)
        print(f"  Best V2:     WR {best['win_rate']:.2%}, "
              f"n_trades {best['n_trades']}, "
              f"NetPnL ${best['net_pnl_usd']:,.0f}")
        improvement = best["net_pnl_usd"] - (-46914)
        print(f"  Improvement: ${improvement:+,.0f}")

        # Hot zone summary
        if not args.test:
            print(f"\n=== Categorical Analysis ===")
            for dim, rows in categorical_analysis(grid_df).items():
                print(f"\n  {dim}:")
                for r in rows:
                    val = r[dim]
                    print(f"    {val}: avg_composite={r['avg_composite']}, "
                          f"avg_wr={r['avg_wr']:.3f}, n={r['n_configs']}")
    else:
        print("  No configs passed hard penalties.")


def cmd_sanity(args):
    """Run sanity test suite."""
    repo_root = Path(__file__).parent.parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v",
         "tools/multidim_sim/tests/test_sanity.py"],
        cwd=repo_root,
    )
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(prog="mds", description="MDS-V1.0.1 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_load = sub.add_parser("load", help="Fetch + cache dataset")
    p_load.add_argument("--refresh", action="store_true", help="Force re-fetch from PG")
    p_load.add_argument("--post-v814", action="store_true", dest="post_v814",
                        help="Only include post-V8.1.4 data")
    p_load.set_defaults(func=cmd_load)

    p_sim = sub.add_parser("simulate", help="Run single config simulation")
    p_sim.add_argument("--config", required=True, help="Baseline config name")
    p_sim.add_argument("--post-v814", action="store_true", dest="post_v814")
    p_sim.set_defaults(func=cmd_simulate)

    p_grid = sub.add_parser("grid", help="Run Phase 1 Grid sweep")
    p_grid.add_argument("--n", type=int, default=2000,
                        help="LHS samples (default 2000 → ~8000 configs)")
    p_grid.add_argument("--test", action="store_true",
                        help="Small test grid (200 samples → ~800 configs)")
    p_grid.add_argument("--jobs", type=int, default=1,
                        help="Parallel jobs (1=sequential, -1=all cores)")
    p_grid.set_defaults(func=cmd_grid)

    p_retro_test = sub.add_parser("retro-test",
                                    help="Retro-Runner test mode (10 setups)")
    p_retro_test.set_defaults(func=lambda a: _cmd_retro(test_mode=True))

    p_retro = sub.add_parser("retro",
                              help="Retro-Runner full mode (all setups)")
    p_retro.set_defaults(func=lambda a: _cmd_retro(test_mode=False))

    p_retro_validate = sub.add_parser("retro-validate",
                                       help="Validate retro vs Worker outcomes")
    p_retro_validate.set_defaults(func=_cmd_retro_validate)

    p_san = sub.add_parser("sanity", help="Run sanity test suite")
    p_san.set_defaults(func=cmd_sanity)

    args = parser.parse_args()
    args.func(args)


def _cmd_retro(test_mode: bool):
    from .retro.retro_runner import run_retro
    run_retro(test_mode=test_mode)


def _cmd_retro_validate(args):
    repo_root = Path(__file__).parent.parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "-s",
         "tools/multidim_sim/retro/tests/test_retro_validation.py"],
        cwd=repo_root,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
