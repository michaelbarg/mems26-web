"""
MDS-V1.0.0 Data Loader — fetch setup_attempts from PG (primary) or API (fallback),
rename columns to canonical names, filter, cache to Parquet.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl

CACHE_DIR = Path(__file__).parent / "cache"
V8_1_4_DEPLOY_TS = datetime(2026, 4, 30, 18, 0, 0, tzinfo=timezone.utc)
DEFAULT_API_URL = "https://mems26-web.onrender.com"

# DB → canonical column rename (applied immediately after fetch)
COLUMN_RENAME = {
    "hypothetical_mae_60min_pts": "mae_pts",
    "hypothetical_mfe_60min_pts": "mfe_pts",
    "entry_price_hypothetical": "entry_price",
    "stop_hypothetical": "stop_price",
    "setup_quality_score": "score",
}

REQUIRED_COLUMNS = [
    "id", "direction", "day_type",
    "entry_price", "stop_price", "mae_pts", "mfe_pts",
    "vegas_score", "tpo_score", "fvg_score", "footprint_score",
    "score", "score_reasons",
]


# ---------------------------------------------------------------------------
# PostgreSQL loader (primary)
# ---------------------------------------------------------------------------

def fetch_raw_from_pg(database_url: str, filter_post_v814: bool = False) -> pl.DataFrame:
    """Fetch setup_attempts from PostgreSQL. Returns raw DataFrame with canonical names."""
    import psycopg2

    url = database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    # Base query — fetch ALL with MAE/MFE + component scores
    where_clauses = [
        "hypothetical_mae_60min_pts IS NOT NULL",
        "hypothetical_mfe_60min_pts IS NOT NULL",
        "(vegas_score IS NOT NULL OR tpo_score IS NOT NULL "
        "OR fvg_score IS NOT NULL OR footprint_score IS NOT NULL)",
    ]

    if filter_post_v814:
        cutoff_ts = int(V8_1_4_DEPLOY_TS.timestamp())
        where_clauses.append(f"ts > {cutoff_ts}")

    where_sql = " AND ".join(where_clauses)

    cur.execute(f"""
        SELECT
            id, ts, direction, setup_type, day_type, killzone,
            vegas_score, tpo_score, fvg_score, footprint_score,
            setup_quality_score,
            score_reasons,
            hypothetical_mae_60min_pts,
            hypothetical_mfe_60min_pts,
            entry_price_hypothetical,
            stop_hypothetical,
            vwap_side,
            extra_json,
            created_at
        FROM setup_attempts
        WHERE {where_sql}
        ORDER BY ts ASC
    """)

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise RuntimeError("PG returned 0 rows matching filters")

    print(f"  PG returned {len(rows)} raw rows")

    # Build dicts and flatten extra_json → outcome
    records = []
    for row in rows:
        d = dict(zip(columns, row))

        # Flatten outcome from extra_json
        extra = d.pop("extra_json", None)
        if extra:
            if isinstance(extra, str):
                try:
                    extra = json.loads(extra)
                except (json.JSONDecodeError, TypeError):
                    extra = {}
            if isinstance(extra, dict):
                # Extract outcome (stored by Phase 6.5 worker)
                d["outcome"] = extra.get("outcome")
                # Extract shadow structural stop
                d["shadow_structural_stop"] = extra.get("shadow_structural_stop")

        records.append(d)

    # infer_schema_length=None scans all rows to avoid mixed-type errors
    df = pl.DataFrame(records, infer_schema_length=None)

    # Rename DB columns → canonical names IMMEDIATELY
    rename_map = {k: v for k, v in COLUMN_RENAME.items() if k in df.columns}
    if rename_map:
        df = df.rename(rename_map)

    return df


# ---------------------------------------------------------------------------
# API loader (fallback)
# ---------------------------------------------------------------------------

def _api_get(base_url: str, path: str, params: dict = None) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{qs}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())


def fetch_raw_from_api(api_url: str = DEFAULT_API_URL) -> pl.DataFrame:
    """Fetch setup_attempts via API endpoints. Returns DataFrame with canonical names."""
    print("  Fetching attempts with outcomes from API...")
    data = _api_get(api_url, "/analytics/attempts/with_outcomes", {"limit": "10000"})
    attempts = data.get("attempts", [])

    if not attempts:
        raise RuntimeError("API returned 0 attempts with outcomes")

    # Also fetch scored attempts to fill missing component scores
    print("  Fetching attempts with scores from API...")
    scored = _api_get(api_url, "/analytics/attempts/recent_with_score", {"limit": "10000"})
    scored_attempts = scored.get("attempts", [])

    # Merge: outcome attempts + score data
    merged = {}
    for a in attempts:
        aid = a.get("id")
        if aid is not None:
            merged[aid] = dict(a)

    for a in scored_attempts:
        aid = a.get("id")
        if aid is None:
            continue
        if aid in merged:
            for k in ["vegas_score", "tpo_score", "fvg_score", "footprint_score",
                       "score_reasons", "setup_quality_score"]:
                if k not in merged[aid] or merged[aid][k] is None:
                    merged[aid][k] = a.get(k)

    rows = list(merged.values())
    print(f"  Merged: {len(rows)} attempts")

    df = pl.DataFrame(rows)

    # Rename to canonical names
    rename_map = {k: v for k, v in COLUMN_RENAME.items() if k in df.columns}
    if rename_map:
        df = df.rename(rename_map)

    return df


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def filter_dataset(df: pl.DataFrame) -> pl.DataFrame:
    """Apply Spec Section 4.4 filters. Returns clean DataFrame."""
    valid_day_types = ["TREND_DAY", "RANGE_DAY", "DEVELOPING", "NORMAL", "GAP_FILL"]
    valid_directions = ["LONG", "SHORT"]

    initial_count = len(df)

    df = df.filter(
        pl.col("mae_pts").is_not_null()
        & pl.col("mfe_pts").is_not_null()
        & pl.col("direction").is_in(valid_directions)
        & pl.col("entry_price").is_not_null()
        & pl.col("stop_price").is_not_null()
        & (pl.col("entry_price") > 0)
        & (pl.col("stop_price") > 0)
        & (pl.col("mae_pts") < 50)
        & (pl.col("mfe_pts") < 50)
    )

    # Day type filter
    if "day_type" in df.columns:
        df = df.filter(
            pl.col("day_type").is_in(valid_day_types)
            | pl.col("day_type").is_null()
        )

    # Add duration_minutes column
    # setup_attempts uses a 60-min forward measurement window for MAE/MFE
    if "duration_minutes" not in df.columns:
        df = df.with_columns(pl.lit(60.0).alias("duration_minutes"))

    filtered_count = len(df)
    print(f"  Filtered: {initial_count} → {filtered_count} rows "
          f"({initial_count - filtered_count} removed)")

    if filtered_count < 800:
        print(f"  WARNING: Dataset small ({filtered_count} rows). "
              f"Spec recommends >= 800. Proceeding with caveat.")

    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_dataset(database_url: str = None, force_refresh: bool = False,
                filter_post_v814: bool = False,
                api_url: str = DEFAULT_API_URL) -> pl.DataFrame:
    """
    Main entry point. Returns clean, filtered dataset with canonical column names.

    Args:
        database_url: PostgreSQL connection string (primary). Falls back to API if None.
        force_refresh: Bypass Parquet cache.
        filter_post_v814: If True, only include data after V8.1.4 deploy (2026-04-30 18:00 UTC).
                          Default False = full dataset for sanity test.
        api_url: Fallback API URL.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "_post_v814" if filter_post_v814 else "_full"
    cache_file = CACHE_DIR / f"setups_clean_{datetime.now().strftime('%Y-%m-%d')}{suffix}.parquet"

    # Check cache
    if not force_refresh and cache_file.exists():
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < 86400:  # 24h TTL
            print(f"  Using cached dataset: {cache_file.name}")
            return pl.read_parquet(cache_file)

    # Fetch raw data
    if database_url:
        print("  Loading from PostgreSQL...")
        try:
            df_raw = fetch_raw_from_pg(database_url, filter_post_v814=filter_post_v814)
        except Exception as e:
            print(f"  PG failed ({e}), falling back to API...")
            df_raw = fetch_raw_from_api(api_url)
    else:
        print("  DATABASE_URL not set, loading from API...")
        df_raw = fetch_raw_from_api(api_url)

    # Filter
    df_clean = filter_dataset(df_raw)

    # Verify required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df_clean.columns]
    if missing:
        raise RuntimeError(
            f"Required columns missing: {missing}. "
            f"Available: {sorted(df_clean.columns)}"
        )

    # Cache
    df_clean.write_parquet(cache_file)
    print(f"  Cached to: {cache_file}")

    return df_clean


def get_dataset_stats(df: pl.DataFrame) -> dict:
    """Return summary stats for sanity reporting."""
    n = len(df)
    if n == 0:
        return {"total_rows": 0}

    dir_counts = df.group_by("direction").len().to_dicts()
    dir_balance = {r["direction"]: round(r["len"] / n * 100, 1) for r in dir_counts}

    day_counts = df.group_by("day_type").len().to_dicts()
    day_breakdown = {r["day_type"]: r["len"] for r in day_counts}

    kz_counts = df.group_by("killzone").len().to_dicts() if "killzone" in df.columns else []
    kz_breakdown = {r["killzone"]: r["len"] for r in kz_counts}

    score_col = df["score"].drop_nulls()

    return {
        "total_rows": n,
        "direction_balance": dir_balance,
        "day_type_breakdown": day_breakdown,
        "killzone_breakdown": kz_breakdown,
        "mae_mfe_completeness_pct": 100.0,  # already filtered
        "avg_mfe": round(float(df["mfe_pts"].mean()), 2),
        "avg_mae": round(float(df["mae_pts"].mean()), 2),
        "score_range": f"{score_col.min()}-{score_col.max()}" if len(score_col) > 0 else "N/A",
        "score_mean": round(float(score_col.mean()), 1) if len(score_col) > 0 else 0,
    }
