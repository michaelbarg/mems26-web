"""
MDS-V1.0.0 Simulator Core — Option C Hybrid Architecture.

Uses DB outcome directly (HIT_C1/HIT_STOP/TIMEOUT) for trade results.
The simulator decides WHICH setups to take via scoring/filtering,
but does NOT reconstruct outcomes from MFE/MAE.

Trade management optimization (stop_type, T2 cap, C3 mode) is
deferred to Phase 3.5 bar-by-bar simulator.

All operations are vectorized Polars (no Python row loops).
Performance target: < 1 second for ~5,000 rows.
"""

import hashlib
import json

import polars as pl

# Constants (Spec Section 7.2)
COMMISSION_PER_CONTRACT = 1.50   # USD round-trip
SLIPPAGE_PER_CONTRACT = 1.25     # USD avg
COST_PER_CONTRACT = COMMISSION_PER_CONTRACT + SLIPPAGE_PER_CONTRACT  # $2.75
POINTS_TO_USD = 5.0              # $5 per point for MES
RISK_PTS = 5.0                   # Fixed 5pt stop (V1 production)

# PnL per outcome (USD per contract, before costs)
# HIT_C1 = +1R = +5pt × $5/pt = +$25
# HIT_STOP = -1R = -5pt × $5/pt = -$25
# TIMEOUT = $0 (flat exit)
# FORCED_EOD = $0 (conservative)
PNL_PER_OUTCOME = {
    "HIT_C1": RISK_PTS * POINTS_TO_USD,      # +$25
    "HIT_STOP": -RISK_PTS * POINTS_TO_USD,    # -$25
    "TIMEOUT": 0.0,
    "FORCED_EOD": 0.0,
}

# V1 production max weights (used to normalize DB component scores)
V1_MAX = {"vegas": 30.0, "tpo": 25.0, "fvg": 25.0, "footprint": 20.0}


def _config_hash(config: dict) -> str:
    raw = json.dumps(config, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def compute_score_v2(df: pl.DataFrame, config: dict) -> pl.Series:
    """
    Vectorized: compute new total score per row given config weights.

    Normalizes DB component scores (stored under V1 max weights) then
    re-scales to config weights.

    Returns: pl.Series of float scores, same length as df.
    """
    vegas_w = config.get("vegas_weight", 30)
    tpo_w = config.get("tpo_weight", 25)
    fvg_w = config.get("fvg_weight", 25)
    fp_logic = config.get("footprint_logic", "weighted")
    fp_w = config.get("footprint_weight", 20)

    new_vegas = (pl.col("vegas_score").fill_null(0).cast(pl.Float64) / V1_MAX["vegas"]).clip(0, 1) * vegas_w
    new_tpo = (pl.col("tpo_score").fill_null(0).cast(pl.Float64) / V1_MAX["tpo"]).clip(0, 1) * tpo_w
    new_fvg = (pl.col("fvg_score").fill_null(0).cast(pl.Float64) / V1_MAX["fvg"]).clip(0, 1) * fvg_w

    if fp_logic == "off":
        new_fp = pl.lit(0.0)
    elif fp_logic == "veto":
        new_fp = pl.lit(float(fp_w))
    else:  # "weighted"
        new_fp = (pl.col("footprint_score").fill_null(0).cast(pl.Float64) / V1_MAX["footprint"]).clip(0, 1) * fp_w

    total = new_vegas + new_tpo + new_fvg + new_fp
    return df.select(total.alias("new_score")).to_series()


def _footprint_opposes(df: pl.DataFrame) -> pl.Series:
    """Vectorized: detect if footprint delta opposes direction from score_reasons."""
    reasons_lower = pl.col("score_reasons").fill_null("").str.to_lowercase()
    return df.select(
        (reasons_lower.str.contains("opposes") & reasons_lower.str.contains("delta="))
        .alias("fp_opposes")
    ).to_series()


def determine_qty(scores: pl.Series, config: dict) -> pl.Series:
    """
    Position sizing:
      score >= 70 → 3 contracts
      score >= threshold → 2 contracts
      else → 0 (reject)
    """
    threshold = config.get("threshold", 50)
    return (
        pl.when(scores >= 70).then(3)
        .when(scores >= threshold).then(2)
        .otherwise(0)
    ).alias("qty")


def simulate_outcomes(df: pl.DataFrame, config: dict) -> pl.DataFrame:
    """
    Option C: Use DB outcome directly. Apply scoring/filtering + duration override.

    The simulator decides WHICH setups to take (via score, filters, qty).
    Outcomes come from the DB's pre-computed outcome column.
    """
    # --- Score ---
    new_scores = compute_score_v2(df, config)

    # --- Footprint veto ---
    if config.get("footprint_logic") == "veto":
        fp_opposes = _footprint_opposes(df)
        new_scores = pl.when(fp_opposes).then(0.0).otherwise(new_scores)

    # --- Day filter ---
    day_filter = config.get("day_filter", "all_days")
    if day_filter != "all_days":
        skip_map = {
            "skip_DEVELOPING": ["DEVELOPING"],
            "skip_DEVELOPING_NEUTRAL": ["DEVELOPING", "NORMAL"],
            "TREND_only": ["DEVELOPING", "NORMAL", "RANGE_DAY", "GAP_FILL"],
        }
        skip_types = skip_map.get(day_filter, [])
        if skip_types:
            day_blocked = df["day_type"].is_in(skip_types)
            new_scores = pl.when(day_blocked).then(0.0).otherwise(new_scores)

    # --- Direction filter ---
    if config.get("direction_filter") == "SHORT_only":
        new_scores = pl.when(df["direction"] == "LONG").then(0.0).otherwise(new_scores)

    # --- VWAP overextension veto ---
    if config.get("skip_overextended", False) and "vwap_side" in df.columns:
        # LONG + above VWAP = overbought, SHORT + below VWAP = oversold
        # Only filter rows with non-null vwap_side; NULL passes through
        has_vwap = df["vwap_side"].is_not_null()
        overextended = (
            has_vwap
            & (
                ((df["direction"] == "LONG") & (df["vwap_side"] == "above"))
                | ((df["direction"] == "SHORT") & (df["vwap_side"] == "below"))
            )
        )
        new_scores = pl.when(overextended).then(0.0).otherwise(new_scores)

    # --- Qty ---
    qty = determine_qty(new_scores, config)

    # --- Build working DataFrame ---
    work = df.with_columns([
        new_scores.alias("new_score"),
        qty,
    ])

    # --- Use DB outcome directly ---
    work = work.with_columns(
        pl.col("outcome").fill_null("TIMEOUT").alias("sim_outcome")
    )

    # --- Duration override: FORCED_EOD if too long ---
    duration_max = config.get("duration_max_minutes", 720)
    if "duration_minutes" in work.columns:
        work = work.with_columns(
            pl.when(
                pl.col("duration_minutes").is_not_null()
                & (pl.col("duration_minutes") > duration_max)
                & (pl.col("sim_outcome") != "HIT_STOP")
            )
            .then(pl.lit("FORCED_EOD"))
            .otherwise(pl.col("sim_outcome"))
            .alias("sim_outcome")
        )

    # --- PnL computation ---
    gross_per_contract = (
        pl.when(pl.col("sim_outcome") == "HIT_C1").then(pl.lit(PNL_PER_OUTCOME["HIT_C1"]))
        .when(pl.col("sim_outcome") == "HIT_STOP").then(pl.lit(PNL_PER_OUTCOME["HIT_STOP"]))
        .when(pl.col("sim_outcome") == "TIMEOUT").then(pl.lit(PNL_PER_OUTCOME["TIMEOUT"]))
        .when(pl.col("sim_outcome") == "FORCED_EOD").then(pl.lit(PNL_PER_OUTCOME["FORCED_EOD"]))
        .otherwise(pl.lit(0.0))
    )

    work = work.with_columns(
        (gross_per_contract * pl.col("qty").cast(pl.Float64)).alias("gross_usd"),
    )
    work = work.with_columns(
        pl.when(pl.col("qty") > 0)
        .then(pl.lit(COST_PER_CONTRACT) * pl.col("qty").cast(pl.Float64))
        .otherwise(0.0)
        .alias("costs_usd"),
    )
    work = work.with_columns(
        (pl.col("gross_usd") - pl.col("costs_usd")).alias("net_usd")
    )

    return work


def aggregate_metrics(df: pl.DataFrame, config: dict = None) -> dict:
    """Compute aggregate metrics from per-trade DataFrame."""
    n_total = len(df)
    traded = df.filter(pl.col("qty") > 0)
    n_trades = len(traded)

    if n_trades == 0:
        return {
            "config_hash": _config_hash(config) if config else "none",
            "n_setups_total": n_total, "n_trades": 0,
            "n_hit_c1": 0, "n_hit_stop": 0, "n_timeout": 0, "n_forced_eod": 0,
            "win_rate": 0.0,
            "gross_pnl_usd": 0.0, "total_costs_usd": 0.0, "net_pnl_usd": 0.0,
            "profit_factor": 0.0, "avg_trade_usd": 0.0, "max_drawdown_usd": 0.0,
            "breakdown_by_day_type": {}, "breakdown_by_direction": {},
        }

    # Outcome counts from sim_outcome (= DB outcome + duration override)
    outcomes = traded.group_by("sim_outcome").len().to_dicts()
    outcome_map = {r["sim_outcome"]: r["len"] for r in outcomes}

    n_hit_c1 = outcome_map.get("HIT_C1", 0)
    n_hit_stop = outcome_map.get("HIT_STOP", 0)
    n_timeout = outcome_map.get("TIMEOUT", 0)
    n_forced_eod = outcome_map.get("FORCED_EOD", 0)

    # Win rate: HIT_C1 / (HIT_C1 + HIT_STOP)
    denom = n_hit_c1 + n_hit_stop
    win_rate = n_hit_c1 / denom if denom > 0 else 0.0

    # PnL aggregates
    gross_pnl = float(traded["gross_usd"].sum())
    total_costs = float(traded["costs_usd"].sum())
    net_pnl = float(traded["net_usd"].sum())
    avg_trade = net_pnl / n_trades

    # Profit factor
    win_gross = float(traded.filter(pl.col("gross_usd") > 0)["gross_usd"].sum())
    loss_gross = abs(float(traded.filter(pl.col("gross_usd") < 0)["gross_usd"].sum()))
    profit_factor = win_gross / loss_gross if loss_gross > 0 else (float("inf") if win_gross > 0 else 0.0)

    # Max drawdown (peak-to-trough on cumulative net_usd)
    cum_pnl = traded["net_usd"].cum_sum()
    drawdown = cum_pnl - cum_pnl.cum_max()
    max_dd = abs(float(drawdown.min())) if len(drawdown) > 0 else 0.0

    # Duration stats
    dur_stats = {}
    if "duration_minutes" in traded.columns:
        dur_col = traded["duration_minutes"].drop_nulls()
        if len(dur_col) > 0:
            dur_stats = {
                "mean": round(float(dur_col.mean()), 1),
                "median": round(float(dur_col.median()), 1),
                "max": round(float(dur_col.max()), 1),
                "coverage_pct": round(len(dur_col) / n_trades * 100, 1),
            }

    # Breakdown by day_type
    day_breakdown = {}
    if "day_type" in traded.columns:
        for row in traded.group_by("day_type").agg([
            pl.col("sim_outcome").eq("HIT_C1").sum().alias("wins"),
            pl.col("sim_outcome").eq("HIT_STOP").sum().alias("losses"),
            pl.col("net_usd").sum().alias("pnl"),
            pl.len().alias("count"),
        ]).to_dicts():
            dt = row["day_type"] or "UNKNOWN"
            w, l = row["wins"], row["losses"]
            day_breakdown[dt] = {
                "count": row["count"],
                "wr": round(w / (w + l), 3) if (w + l) > 0 else 0.0,
                "pnl": round(row["pnl"], 2),
            }

    # Breakdown by direction
    dir_breakdown = {}
    for row in traded.group_by("direction").agg([
        pl.col("sim_outcome").eq("HIT_C1").sum().alias("wins"),
        pl.col("sim_outcome").eq("HIT_STOP").sum().alias("losses"),
        pl.col("net_usd").sum().alias("pnl"),
        pl.len().alias("count"),
    ]).to_dicts():
        d = row["direction"]
        w, l = row["wins"], row["losses"]
        dir_breakdown[d] = {
            "count": row["count"],
            "wr": round(w / (w + l), 3) if (w + l) > 0 else 0.0,
            "pnl": round(row["pnl"], 2),
        }

    return {
        "config_hash": _config_hash(config) if config else "none",
        "n_setups_total": n_total,
        "n_trades": n_trades,
        "n_hit_c1": n_hit_c1,
        "n_hit_stop": n_hit_stop,
        "n_timeout": n_timeout,
        "n_forced_eod": n_forced_eod,
        "win_rate": round(win_rate, 4),
        "gross_pnl_usd": round(gross_pnl, 2),
        "total_costs_usd": round(total_costs, 2),
        "net_pnl_usd": round(net_pnl, 2),
        "profit_factor": round(profit_factor, 3),
        "avg_trade_usd": round(avg_trade, 2),
        "max_drawdown_usd": round(max_dd, 2),
        "duration_stats": dur_stats,
        "breakdown_by_day_type": day_breakdown,
        "breakdown_by_direction": dir_breakdown,
    }


def run_single_config(df: pl.DataFrame, config: dict) -> dict:
    """End-to-end: dataset + config → metrics."""
    df_out = simulate_outcomes(df, config)
    return aggregate_metrics(df_out, config)
