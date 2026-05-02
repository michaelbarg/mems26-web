"""
MDS-V1.0.1 Grid Runner — Phase 1 Latin Hypercube sweep.

Generates ~8,000 configs (2,000 LHS × 4 categorical combos),
evaluates each via simulator_core, ranks by composite score.
"""

import hashlib
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import numpy as np
import polars as pl
import yaml
from joblib import Parallel, delayed
from scipy.stats import qmc

from .analyzer import compute_composite_score, load_composite_config
from .data_loader import get_dataset
from .simulator_core import run_single_config


def load_parameter_space() -> dict:
    """Load parameter_space.yaml."""
    spec_path = Path(__file__).parent / "parameter_space.yaml"
    with open(spec_path) as f:
        return yaml.safe_load(f)


def generate_lhs_samples(spec: dict, n_samples: int, seed: int = 42) -> list:
    """LHS for continuous dims + product for discrete weight values."""
    cont = spec.get("continuous", {})
    discrete = spec.get("discrete", {})

    # Continuous: LHS
    cont_names = list(cont.keys())
    if cont_names:
        lo = [cont[k]["range"][0] for k in cont_names]
        hi = [cont[k]["range"][1] for k in cont_names]
        sampler = qmc.LatinHypercube(d=len(cont_names), seed=seed)
        raw = sampler.random(n=n_samples)
        scaled = qmc.scale(raw, lo, hi)
        cont_samples = [
            {cont_names[i]: round(float(row[i]), 2) for i in range(len(cont_names))}
            for row in scaled
        ]
    else:
        cont_samples = [{}] * n_samples

    # Discrete: full product of weight combos
    disc_names = list(discrete.keys())
    if disc_names:
        disc_values = [discrete[k]["values"] for k in disc_names]
        disc_combos = list(product(*disc_values))
    else:
        disc_combos = [()]

    # Cross: each LHS sample × each discrete combo
    rng = np.random.default_rng(seed)
    samples = []
    for cs in cont_samples:
        # Sample a subset of discrete combos to control total size
        n_pick = min(4, len(disc_combos))
        idx = rng.choice(len(disc_combos), size=n_pick, replace=False)
        for i in idx:
            merged = {**cs}
            for j, name in enumerate(disc_names):
                merged[name] = disc_combos[i][j]
            samples.append(merged)

    return samples


def cross_with_categoricals(base_samples: list, spec: dict,
                             cat_subset_size: int = 4,
                             seed: int = 42) -> list:
    """Cross base samples with categorical combos."""
    cat_dims = spec.get("categorical", {})
    cat_keys = list(cat_dims.keys())
    cat_values = [cat_dims[k]["values"] if isinstance(cat_dims[k], dict) else cat_dims[k]
                  for k in cat_keys]
    all_cat_combos = list(product(*cat_values))

    rng = np.random.default_rng(seed)
    fixed = spec.get("fixed", {})

    configs = []
    for sample in base_samples:
        n_pick = min(cat_subset_size, len(all_cat_combos))
        idx = rng.choice(len(all_cat_combos), size=n_pick, replace=False)
        for i in idx:
            combo = dict(zip(cat_keys, all_cat_combos[i]))
            config = {**sample, **combo, **fixed}

            if not _check_constraints(config, spec):
                continue

            configs.append(config)

    return configs


def _check_constraints(config: dict, spec: dict) -> bool:
    """Check parameter_space.yaml constraints."""
    for constraint in spec.get("constraints", []):
        try:
            expr = constraint
            for key, value in config.items():
                if isinstance(value, (int, float)):
                    expr = expr.replace(key, str(value))
            if not eval(expr):  # noqa: S307 — constraints are from our own YAML
                return False
        except Exception:
            continue
    return True


def _config_hash(config: dict) -> str:
    canonical = json.dumps(config, sort_keys=True, default=str)
    return hashlib.md5(canonical.encode()).hexdigest()[:12]


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def _evaluate_single(config: dict, df: pl.DataFrame,
                     composite_cfg: dict, run_meta: dict) -> dict:
    """Evaluate one config. Returns flat dict for CSV row."""
    try:
        metrics = run_single_config(df, config)
        composite = compute_composite_score(metrics, composite_cfg)

        return {
            **run_meta,
            "config_hash": _config_hash(config),
            # Config values (prefixed)
            "cfg_threshold": config.get("threshold"),
            "cfg_vegas_weight": config.get("vegas_weight"),
            "cfg_tpo_weight": config.get("tpo_weight"),
            "cfg_fvg_weight": config.get("fvg_weight"),
            "cfg_footprint_logic": config.get("footprint_logic"),
            "cfg_day_filter": config.get("day_filter"),
            "cfg_direction_filter": config.get("direction_filter"),
            "cfg_skip_overextended": config.get("skip_overextended"),
            # Metrics
            "n_setups_total": metrics["n_setups_total"],
            "n_trades": metrics["n_trades"],
            "n_hit_c1": metrics["n_hit_c1"],
            "n_hit_stop": metrics["n_hit_stop"],
            "n_timeout": metrics["n_timeout"],
            "win_rate": metrics["win_rate"],
            "net_pnl_usd": metrics["net_pnl_usd"],
            "gross_pnl_usd": metrics["gross_pnl_usd"],
            "total_costs_usd": metrics["total_costs_usd"],
            "profit_factor": metrics["profit_factor"],
            "max_drawdown_usd": metrics["max_drawdown_usd"],
            "avg_trade_usd": metrics["avg_trade_usd"],
            "composite_score": composite,
            "error": None,
        }
    except Exception as e:
        return {
            **run_meta,
            "config_hash": _config_hash(config),
            "cfg_threshold": config.get("threshold"),
            "cfg_vegas_weight": config.get("vegas_weight"),
            "cfg_tpo_weight": config.get("tpo_weight"),
            "cfg_fvg_weight": config.get("fvg_weight"),
            "cfg_footprint_logic": config.get("footprint_logic"),
            "cfg_day_filter": config.get("day_filter"),
            "cfg_direction_filter": config.get("direction_filter"),
            "cfg_skip_overextended": config.get("skip_overextended"),
            "n_setups_total": 0, "n_trades": 0,
            "n_hit_c1": 0, "n_hit_stop": 0, "n_timeout": 0,
            "win_rate": 0, "net_pnl_usd": 0, "gross_pnl_usd": 0,
            "total_costs_usd": 0, "profit_factor": 0,
            "max_drawdown_usd": 0, "avg_trade_usd": 0,
            "composite_score": float("-inf"),
            "error": str(e)[:200],
        }


def run_grid(n_lhs_samples: int = 2000, cat_subset_size: int = 4,
             n_jobs: int = 1, seed: int = 42) -> pl.DataFrame:
    """
    Run full Phase 1 Grid.

    Args:
        n_lhs_samples: Latin Hypercube samples (continuous)
        cat_subset_size: Categorical combos per LHS sample
        n_jobs: parallel jobs (1 = sequential, -1 = all cores)
        seed: random seed

    Returns: pl.DataFrame with all results
    """
    spec = load_parameter_space()
    composite_cfg = load_composite_config()
    db_url = os.environ.get("DATABASE_URL")
    df = get_dataset(db_url)

    # Generate configs
    print(f"  Generating {n_lhs_samples} LHS samples × {cat_subset_size} categorical combos...")
    cont_samples = generate_lhs_samples(spec, n_lhs_samples, seed)
    configs = cross_with_categoricals(cont_samples, spec, cat_subset_size, seed)
    print(f"  Total configs to evaluate: {len(configs)}")

    run_meta = {
        "run_id": str(uuid.uuid4())[:8],
        "mds_version": spec.get("mds_version", "1.0.1"),
        "git_sha": _git_sha(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_size": len(df),
        "phase": "grid",
    }

    # Evaluate
    print(f"  Evaluating (n_jobs={n_jobs})...")
    start = time.time()

    if n_jobs == 1:
        # Sequential — simpler, avoids joblib serialization overhead on small runs
        rows = []
        for i, cfg in enumerate(configs):
            rows.append(_evaluate_single(cfg, df, composite_cfg, run_meta))
            if (i + 1) % 500 == 0 or (i + 1) == len(configs):
                elapsed = time.time() - start
                rate = (i + 1) / elapsed
                print(f"    {i+1}/{len(configs)} ({rate:.0f} configs/s)")
    else:
        rows = Parallel(n_jobs=n_jobs, verbose=5)(
            delayed(_evaluate_single)(cfg, df, composite_cfg, run_meta)
            for cfg in configs
        )

    elapsed = time.time() - start
    print(f"  Completed {len(rows)} configs in {elapsed:.1f}s "
          f"({len(rows)/elapsed:.0f} configs/s)")

    grid_df = pl.DataFrame(rows, infer_schema_length=None)
    return grid_df


def save_grid_results(grid_df: pl.DataFrame) -> Path:
    """Save grid results to results/experiments/ with timestamp."""
    out_dir = Path(__file__).parent / "results" / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"grid_{ts}.csv"
    grid_df.write_csv(out_path)
    print(f"  Saved: {out_path} ({len(grid_df)} rows)")
    return out_path
