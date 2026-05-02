"""
MDS-V1.0.2 Simulator Core — Option C + Retro Tick Outcomes.

Uses Retro-Runner tick-level outcomes when available, falls back to
DB outcome. Sequential filter ensures one trade at a time.

All operations are vectorized Polars (no Python row loops).
Performance target: < 1 second for ~5,000 rows.
"""

import hashlib
import json
from pathlib import Path

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
            "TREND_GAP_only": ["DEVELOPING", "NORMAL", "RANGE_DAY"],
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

    # --- Use retro outcome if available, else DB outcome ---
    if "retro_outcome" in work.columns:
        work = work.with_columns(
            pl.when(pl.col("retro_outcome").is_not_null())
            .then(pl.col("retro_outcome"))
            .otherwise(pl.col("outcome").fill_null("TIMEOUT"))
            .alias("sim_outcome")
        )
    else:
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
    # Use retro multi-target PnL if available (already includes all contracts)
    if "retro_total_pnl_usd" in work.columns:
        work = work.with_columns(
            pl.when(pl.col("qty") > 0)
            .then(
                pl.when(pl.col("retro_total_pnl_usd").is_not_null())
                .then(pl.col("retro_total_pnl_usd"))
                .otherwise(pl.lit(0.0))
            )
            .otherwise(pl.lit(0.0))
            .alias("gross_usd"),
        )
    else:
        # Fallback: single-outcome PnL (pre-retro mode)
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
            "n_hit_c1": 0, "n_hit_c2": 0, "n_hit_c3": 0, "n_partial": 0,
            "n_hit_stop": 0, "n_timeout": 0, "n_forced_eod": 0,
            "win_rate": 0.0,
            "gross_pnl_usd": 0.0, "total_costs_usd": 0.0, "net_pnl_usd": 0.0,
            "profit_factor": 0.0, "avg_trade_usd": 0.0, "max_drawdown_usd": 0.0,
            "breakdown_by_day_type": {}, "breakdown_by_direction": {},
        }

    # Outcome counts from sim_outcome (multi-target aware)
    outcomes = traded.group_by("sim_outcome").len().to_dicts()
    outcome_map = {r["sim_outcome"]: r["len"] for r in outcomes}

    n_hit_c1 = outcome_map.get("HIT_C1", 0)
    n_hit_c2 = outcome_map.get("HIT_C2", 0)
    n_hit_c3 = outcome_map.get("HIT_C3", 0)
    n_partial = outcome_map.get("PARTIAL", 0)
    n_hit_stop = outcome_map.get("HIT_STOP", 0)
    n_timeout = outcome_map.get("TIMEOUT", 0)
    n_forced_eod = outcome_map.get("FORCED_EOD", 0)

    # Win rate: any positive outcome / (positive + full stop)
    n_wins = n_hit_c1 + n_hit_c2 + n_hit_c3 + n_partial  # PARTIAL = C1 hit + BE = net positive
    denom = n_wins + n_hit_stop
    win_rate = n_wins / denom if denom > 0 else 0.0

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
            (pl.col("sim_outcome").is_in(["HIT_C1", "HIT_C2", "HIT_C3", "PARTIAL"])).sum().alias("wins"),
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
        (pl.col("sim_outcome").is_in(["HIT_C1", "HIT_C2", "HIT_C3", "PARTIAL"])).sum().alias("wins"),
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
        "n_hit_c2": n_hit_c2,
        "n_hit_c3": n_hit_c3,
        "n_partial": n_partial,
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


def load_retro_outcomes() -> pl.DataFrame | None:
    """Load newest retro outcomes parquet from cache/."""
    cache_dir = Path(__file__).parent / "cache"
    retro_files = sorted(cache_dir.glob("retro_outcomes_*.parquet"))
    if not retro_files:
        return None
    newest = retro_files[-1]
    return pl.read_parquet(newest)


def merge_retro_outcomes(df: pl.DataFrame, retro_df: pl.DataFrame) -> pl.DataFrame:
    """Merge retro outcomes into dataset by attempt_id → id join."""
    # retro has: attempt_id, retro_outcome, retro_mae_pts, retro_mfe_pts, retro_closed_ts, retro_duration_sec
    # Select all retro_ columns + the join key
    retro_col_names = [c for c in retro_df.columns if c.startswith("retro_")]
    retro_cols = retro_df.select(["attempt_id"] + retro_col_names)
    return df.join(retro_cols, left_on="id", right_on="attempt_id", how="left")


def apply_stale_entry_filter(df: pl.DataFrame, max_distance_pts: float = 2.0) -> pl.DataFrame:
    """
    Reject trades where market has already moved too far from entry.
    Uses retro first-tick data: if retro_mae_pts or retro_mfe_pts on first tick
    already exceeds threshold, the entry price was stale.

    Placeholder: full implementation requires first-tick price comparison.
    Current approximation: if retro_duration_sec == 0 and outcome is a win,
    it's likely a look-ahead artifact.
    """
    if "retro_duration_sec" not in df.columns:
        return df

    # Flag instant wins (duration 0s with positive PnL) as stale
    stale = (
        (pl.col("retro_duration_sec") == 0)
        & (pl.col("gross_usd") > 0)
        & (pl.col("qty") > 0)
    )
    return df.with_columns(
        pl.when(stale).then(0).otherwise(pl.col("qty")).alias("qty")
    )


def apply_sequential_filter(df: pl.DataFrame) -> pl.DataFrame:
    """
    Reality constraint: only one trade open at a time.
    Sort by ts (entry time). Skip setups that overlap with the previous trade.

    Uses retro_closed_ts if available, else assumes 60-min duration.
    Only applies to trades that passed scoring (qty > 0).
    """
    if len(df) == 0:
        return df

    # Sort by entry timestamp
    sorted_df = df.sort("ts")

    # Build mask: for each row, check if it's accepted
    ts_col = sorted_df["ts"].to_list()
    qty_col = sorted_df["qty"].to_list()

    # Get close timestamps (retro_closed_ts is ISO string or null)
    has_retro_close = "retro_closed_ts" in sorted_df.columns
    if has_retro_close:
        close_col = sorted_df["retro_closed_ts"].to_list()
    else:
        close_col = [None] * len(sorted_df)

    accepted = []
    last_close_ts = 0  # unix epoch of last accepted trade's close

    for i in range(len(sorted_df)):
        if qty_col[i] == 0:
            accepted.append(True)  # rejected setups pass through (won't affect PnL)
            continue

        entry_ts = ts_col[i]
        if entry_ts is None:
            accepted.append(False)
            continue

        # Convert entry_ts to comparable value
        entry_val = float(entry_ts) if isinstance(entry_ts, (int, float)) else 0

        if entry_val >= last_close_ts:
            accepted.append(True)
            # Determine close time
            close_str = close_col[i] if has_retro_close else None
            if close_str and isinstance(close_str, str):
                try:
                    from datetime import datetime
                    close_dt = datetime.fromisoformat(close_str)
                    last_close_ts = close_dt.timestamp()
                except (ValueError, TypeError):
                    last_close_ts = entry_val + 3600  # fallback 60min
            else:
                last_close_ts = entry_val + 3600
        else:
            accepted.append(False)

    # Apply mask: set qty=0 for rejected overlapping trades
    mask = pl.Series("seq_accepted", accepted)
    return sorted_df.with_columns(
        pl.when(mask).then(pl.col("qty")).otherwise(0).alias("qty")
    )


def run_single_config(df: pl.DataFrame, config: dict,
                      use_retro: bool = True,
                      sequential: bool = True) -> dict:
    """
    End-to-end: dataset + config → metrics.

    Args:
        use_retro: merge retro tick outcomes if available
        sequential: apply one-trade-at-a-time filter
    """
    # Merge retro outcomes if available
    work_df = df
    if use_retro:
        retro = load_retro_outcomes()
        if retro is not None:
            work_df = merge_retro_outcomes(df, retro)

    df_out = simulate_outcomes(work_df, config)

    if sequential:
        df_out = apply_sequential_filter(df_out)

    return aggregate_metrics(df_out, config)
