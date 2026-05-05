"""
Decision Layer V1.1 — Multi-Stage Setup Filter with Attribution.

Stages (sequential, each can REJECT):
  1. Tournament  — Score threshold + day_type + killzone gate
  2. VWAP        — Overextension veto (LONG above VWAP / SHORT below VWAP)
  3. Footprint   — FP delta opposes trade direction → veto

Each setup gets a decision_status: APPROVED | REJECTED
and a rejected_by field naming the first stage that rejected it.

All operations are vectorized Polars — no Python row loops.
"""

import polars as pl

from .simulator_core import compute_score_v2, V1_MAX

# ── Default V1.1 config ──
DEFAULT_CONFIG = {
    # Stage 1: Tournament
    "threshold": 50,
    "vegas_weight": 25,
    "tpo_weight": 30,
    "fvg_weight": 25,
    "footprint_weight": 20,
    "day_filter": "skip_DEVELOPING",       # skip DEVELOPING day_type
    "skip_killzones": ["London"],           # skip these killzones
    "direction_filter": "both",             # "both" | "SHORT_only"
    # Stage 2: VWAP
    "vwap_overextension_veto": True,        # reject LONG+above / SHORT+below
    # Stage 3: Footprint
    "fp_min_score": 10,                     # min footprint_score to pass (0 = disabled)
    "fp_opposes_veto": True,                # reject if FP delta opposes direction
}

# Day filter → skip list mapping
_DAY_SKIP_MAP = {
    "all_days": [],
    "skip_DEVELOPING": ["DEVELOPING"],
    "skip_DEVELOPING_NEUTRAL": ["DEVELOPING", "NORMAL"],
    "TREND_only": ["DEVELOPING", "NORMAL", "RANGE_DAY", "GAP_FILL"],
    "TREND_GAP_only": ["DEVELOPING", "NORMAL", "RANGE_DAY"],
}


def apply_decision_layer(df: pl.DataFrame, config: dict = None) -> pl.DataFrame:
    """
    Apply Decision Layer V1.1 to a DataFrame of setups.

    Returns df with added columns:
      - dl_score         (float)  — rescored total
      - dl_stage1_pass   (bool)   — Tournament pass
      - dl_stage2_pass   (bool)   — VWAP pass
      - dl_stage3_pass   (bool)   — Footprint pass
      - dl_decision      (str)    — "APPROVED" | "REJECTED"
      - dl_rejected_by   (str)    — stage name or null
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    # ── Stage 1: Tournament ──
    # Rescore with config weights
    new_scores = compute_score_v2(df, {
        "vegas_weight": cfg["vegas_weight"],
        "tpo_weight": cfg["tpo_weight"],
        "fvg_weight": cfg["fvg_weight"],
        "footprint_weight": cfg.get("footprint_weight", 20),
        "footprint_logic": "weighted",
    })

    threshold = cfg["threshold"]
    score_pass = new_scores >= threshold

    # Day type filter
    day_skip = _DAY_SKIP_MAP.get(cfg["day_filter"], [])
    if day_skip and "day_type" in df.columns:
        day_pass = ~df["day_type"].is_in(day_skip) | df["day_type"].is_null()
    else:
        day_pass = pl.Series("day_pass", [True] * len(df))

    # Killzone filter
    skip_kz = cfg.get("skip_killzones", [])
    if skip_kz and "killzone" in df.columns:
        kz_pass = ~df["killzone"].is_in(skip_kz) | df["killzone"].is_null()
    else:
        kz_pass = pl.Series("kz_pass", [True] * len(df))

    # Direction filter
    if cfg.get("direction_filter") == "SHORT_only":
        dir_pass = df["direction"] == "SHORT"
    else:
        dir_pass = pl.Series("dir_pass", [True] * len(df))

    stage1_pass = score_pass & day_pass & kz_pass & dir_pass

    # ── Stage 2: VWAP Overextension ──
    if cfg.get("vwap_overextension_veto", False) and "vwap_side" in df.columns:
        has_vwap = df["vwap_side"].is_not_null()
        overextended = (
            has_vwap
            & (
                ((df["direction"] == "LONG") & (df["vwap_side"] == "above"))
                | ((df["direction"] == "SHORT") & (df["vwap_side"] == "below"))
            )
        )
        stage2_pass = ~overextended
    else:
        stage2_pass = pl.Series("s2", [True] * len(df))

    # ── Stage 3: Footprint ──
    fp_min = cfg.get("fp_min_score", 0)
    fp_veto = cfg.get("fp_opposes_veto", False)

    # FP score gate
    if fp_min > 0 and "footprint_score" in df.columns:
        fp_score_pass = df["footprint_score"].fill_null(0) >= fp_min
    else:
        fp_score_pass = pl.Series("fp_s", [True] * len(df))

    # FP opposes veto
    if fp_veto and "score_reasons" in df.columns:
        reasons_lower = df["score_reasons"].fill_null("").str.to_lowercase()
        fp_opposes = reasons_lower.str.contains("opposes") & reasons_lower.str.contains("delta=")
        fp_opp_pass = ~fp_opposes
    else:
        fp_opp_pass = pl.Series("fp_o", [True] * len(df))

    stage3_pass = fp_score_pass & fp_opp_pass

    # ── Build decision columns ──
    # First failing stage determines rejected_by
    rejected_by = (
        pl.when(~stage1_pass).then(pl.lit("Tournament"))
        .when(~stage2_pass).then(pl.lit("VWAP"))
        .when(~stage3_pass).then(pl.lit("Footprint"))
        .otherwise(pl.lit(None))
    )

    decision = (
        pl.when(stage1_pass & stage2_pass & stage3_pass)
        .then(pl.lit("APPROVED"))
        .otherwise(pl.lit("REJECTED"))
    )

    return df.with_columns([
        new_scores.alias("dl_score"),
        stage1_pass.alias("dl_stage1_pass"),
        stage2_pass.alias("dl_stage2_pass"),
        stage3_pass.alias("dl_stage3_pass"),
        decision.alias("dl_decision"),
        rejected_by.alias("dl_rejected_by"),
    ])


def decision_summary(df: pl.DataFrame) -> dict:
    """Summarize decision distribution from a df that has dl_* columns."""
    total = len(df)
    approved = df.filter(pl.col("dl_decision") == "APPROVED")
    rejected = df.filter(pl.col("dl_decision") == "REJECTED")

    n_approved = len(approved)
    n_rejected = len(rejected)
    rate = n_approved / total * 100 if total > 0 else 0

    # Rejection breakdown by stage
    rej_by = {}
    if n_rejected > 0:
        for row in rejected.group_by("dl_rejected_by").len().to_dicts():
            rej_by[row["dl_rejected_by"]] = row["len"]

    return {
        "total": total,
        "approved": n_approved,
        "rejected": n_rejected,
        "approval_rate_pct": round(rate, 1),
        "rejected_by_stage": rej_by,
    }
