"""
MDS-V1.0.0 CLI — single entry point.

Usage:
    python -m tools.multidim_sim load [--refresh]
    python -m tools.multidim_sim simulate --config v1_production
    python -m tools.multidim_sim sanity
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

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


def cmd_sanity(args):
    """Run sanity test suite (GATE for Commit 2)."""
    repo_root = Path(__file__).parent.parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v",
         "tools/multidim_sim/tests/test_sanity.py"],
        cwd=repo_root,
    )
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(prog="mds", description="MDS-V1.0.0 CLI")
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

    p_san = sub.add_parser("sanity", help="Run sanity test suite")
    p_san.set_defaults(func=cmd_sanity)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
