"""
MDS-V1.0.1 Analyzer — Composite Score + ranking + hot zone analysis.
"""

import polars as pl
import yaml
from pathlib import Path


def load_composite_config() -> dict:
    """Load composite_score config from parameter_space.yaml."""
    spec_path = Path(__file__).parent / "parameter_space.yaml"
    with open(spec_path) as f:
        spec = yaml.safe_load(f)
    return spec["composite_score"]


def compute_composite_score(metrics: dict, composite_cfg: dict = None) -> float:
    """
    Composite fitness score. Higher = better.
    Returns -inf if hard penalties triggered.
    """
    if composite_cfg is None:
        composite_cfg = load_composite_config()

    hp = composite_cfg["hard_penalties"]
    sw = composite_cfg["soft_weights"]

    # Hard penalties
    if metrics.get("win_rate", 0) < hp["win_rate_min"]:
        return float("-inf")
    if metrics.get("profit_factor", 0) < hp["profit_factor_min"]:
        return float("-inf")
    if metrics.get("n_trades", 0) < hp["n_trades_min"]:
        return float("-inf")
    if metrics.get("max_drawdown_usd", float("inf")) > hp["max_drawdown_max"]:
        return float("-inf")

    # Soft scoring
    base = sw["base_pnl_weight"] * metrics.get("net_pnl_usd", 0)
    penalty_dd = sw["drawdown_penalty"] * metrics.get("max_drawdown_usd", 0)
    bonus_pf = sw["profit_factor_bonus"] * max(0, metrics.get("profit_factor", 0) - 1.5)

    return base - penalty_dd + bonus_pf


def rank_configs(grid_df: pl.DataFrame) -> pl.DataFrame:
    """Sort by composite_score descending, add rank column."""
    return (
        grid_df
        .sort("composite_score", descending=True, nulls_last=True)
        .with_row_index("rank", offset=1)
    )


def top_n_configs(grid_df: pl.DataFrame, n: int = 10) -> pl.DataFrame:
    """Return top N configs (excluding -inf composite scores)."""
    valid = grid_df.filter(pl.col("composite_score") > float("-inf"))
    return rank_configs(valid).head(n)


def hot_zone_analysis(grid_df: pl.DataFrame) -> dict:
    """
    For each continuous dimension, find which value-bins
    correlate with high composite score.
    """
    valid = grid_df.filter(pl.col("composite_score") > float("-inf"))
    if len(valid) < 10:
        return {"error": f"Too few valid configs ({len(valid)}) for analysis"}

    hot_zones = {}
    for col in ["cfg_threshold", "cfg_vegas_weight", "cfg_tpo_weight", "cfg_fvg_weight"]:
        if col not in valid.columns:
            continue
        try:
            binned = valid.with_columns(
                pl.col(col).qcut(5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
                .alias(f"{col}_bin")
            )
            hot_zones[col] = (
                binned.group_by(f"{col}_bin").agg([
                    pl.col("composite_score").mean().round(1).alias("avg_composite"),
                    pl.col("net_pnl_usd").mean().round(0).alias("avg_net_pnl"),
                    pl.col("win_rate").mean().round(3).alias("avg_wr"),
                    pl.len().alias("n_configs"),
                ])
                .sort(f"{col}_bin")
                .to_dicts()
            )
        except Exception as e:
            hot_zones[col] = f"Error: {e}"

    return hot_zones


def categorical_analysis(grid_df: pl.DataFrame) -> dict:
    """For each categorical dimension, compute avg composite per value."""
    valid = grid_df.filter(pl.col("composite_score") > float("-inf"))
    if len(valid) < 10:
        return {"error": f"Too few valid configs ({len(valid)})"}

    cat_results = {}
    for col in ["cfg_footprint_logic", "cfg_day_filter",
                "cfg_direction_filter", "cfg_skip_overextended"]:
        if col not in valid.columns:
            continue
        cat_results[col] = (
            valid.group_by(col).agg([
                pl.col("composite_score").mean().round(1).alias("avg_composite"),
                pl.col("net_pnl_usd").mean().round(0).alias("avg_net_pnl"),
                pl.col("win_rate").mean().round(3).alias("avg_wr"),
                pl.len().alias("n_configs"),
            ])
            .sort("avg_composite", descending=True)
            .to_dicts()
        )

    return cat_results
