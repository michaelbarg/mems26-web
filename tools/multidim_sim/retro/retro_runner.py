"""
Retro-Runner — backfill setup outcomes from Sierra Chart .scid tick data.

Reads setup_attempts from PG, computes exact outcomes using tick-by-tick
temporal ordering, stores results as local Parquet (for MDS consumption)
and optionally updates setup_attempts extra_json in DB.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import psycopg2

from .outcome_calculator import compute_outcome_multi_target
from .scid_reader import ScidReader, get_default_scid_path

RESULTS_DIR = Path(__file__).parent.parent / "cache"


def get_setup_attempts_for_retro(database_url: str, limit: int = None) -> list:
    """
    Fetch setup_attempts that have entry/stop/c1 and are candidates for retro.
    Returns list of dicts.
    """
    conn = psycopg2.connect(
        database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgres://") else database_url
    )
    cur = conn.cursor()

    sql = """
        SELECT id, ts, direction,
               entry_price_hypothetical, stop_hypothetical,
               c1_target, c2_target, c3_target, c3_enabled,
               day_type, killzone, setup_quality_score,
               vegas_score, tpo_score, fvg_score, footprint_score,
               score_reasons, vwap_side
        FROM setup_attempts
        WHERE entry_price_hypothetical IS NOT NULL
          AND stop_hypothetical IS NOT NULL
          AND c1_target IS NOT NULL
          AND c2_target IS NOT NULL
          AND direction IN ('LONG', 'SHORT')
        ORDER BY ts ASC
    """
    if limit:
        sql += f" LIMIT {limit}"

    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def get_known_setups_for_validation(database_url: str, limit: int = 10) -> list:
    """
    Get CLOSED setups with Worker-computed outcomes for validation.
    Derives outcome from t1_hit_ts / stop_hit_ts since outcome column is NULL.
    """
    conn = psycopg2.connect(
        database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgres://") else database_url
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT setup_id, first_detected_ts, closed_ts,
               t1_hit_ts, stop_hit_ts,
               initial_entry, initial_stop, c1_target, direction,
               mae_pts, mfe_pts
        FROM setups
        WHERE status = 'CLOSED'
          AND closed_ts IS NOT NULL
          AND initial_entry IS NOT NULL
          AND initial_stop IS NOT NULL
          AND c1_target IS NOT NULL
        ORDER BY first_detected_ts DESC
        LIMIT %s
    """, (limit,))

    rows = []
    for r in cur.fetchall():
        # Derive outcome from hit timestamps
        if r[4] is not None:  # stop_hit_ts
            outcome = "HIT_STOP"
        elif r[3] is not None:  # t1_hit_ts
            outcome = "HIT_C1"
        else:
            outcome = "TIMEOUT"

        rows.append({
            "setup_id": r[0],
            "first_detected_ts": r[1],  # unix epoch bigint
            "closed_ts": r[2],
            "expected_outcome": outcome,
            "t1_hit_ts": r[3],
            "stop_hit_ts": r[4],
            "entry_price": float(r[5]),
            "stop_price": float(r[6]),
            "c1_target": float(r[7]),
            "direction": r[8],
            "expected_mae": float(r[9]) if r[9] else 0,
            "expected_mfe": float(r[10]) if r[10] else 0,
        })

    cur.close()
    conn.close()
    return rows


def run_retro(test_mode: bool = False, scid_path: Path = None,
              timeout_minutes: int = 60) -> dict:
    """
    Main retro runner. Computes exact outcomes for setup_attempts.

    Results stored as Parquet at cache/retro_outcomes_<ts>.parquet
    for MDS data_loader to consume.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return {"error": "no DATABASE_URL"}

    limit = 10 if test_mode else None
    print(f"=== Retro-Runner {'TEST' if test_mode else 'FULL'} Mode ===")

    setups = get_setup_attempts_for_retro(db_url, limit=limit)
    print(f"  Setups to process: {len(setups)}")

    if not setups:
        print("  No setups found.")
        return {"processed": 0}

    if scid_path is None:
        scid_path = get_default_scid_path()
    reader = ScidReader(scid_path)
    print(f"  SCID file: {scid_path.name} ({reader.n_records:,} records)")

    outcome_counts = {}
    stats = {"processed": 0, "no_ticks": 0, "errors": 0}
    results = []

    for i, setup in enumerate(setups):
        try:
            ticks = reader.read_ticks_after(
                float(setup["ts"]), max_minutes=timeout_minutes
            )

            if not ticks:
                stats["no_ticks"] += 1
                continue

            c3_target = setup.get("c3_target")
            c3_enabled = bool(setup.get("c3_enabled"))
            if c3_target is not None:
                c3_target = float(c3_target)
            elif c3_enabled:
                # Synthetic C3 at 3R from entry
                entry = float(setup["entry_price_hypothetical"])
                stop = float(setup["stop_hypothetical"])
                r_dist = abs(entry - stop)
                if setup["direction"] == "LONG":
                    c3_target = entry + r_dist * 3.0
                else:
                    c3_target = entry - r_dist * 3.0

            oc = compute_outcome_multi_target(
                ticks,
                entry_ts=datetime.fromtimestamp(setup["ts"], tz=timezone.utc),
                entry_price=float(setup["entry_price_hypothetical"]),
                stop_price=float(setup["stop_hypothetical"]),
                c1_target=float(setup["c1_target"]),
                c2_target=float(setup["c2_target"]),
                c3_target=c3_target,
                c3_enabled=c3_enabled,
                direction=setup["direction"],
                timeout_minutes=timeout_minutes,
            )

            results.append({
                "attempt_id": setup["id"],
                "ts": setup["ts"],
                "direction": setup["direction"],
                "entry_price": float(setup["entry_price_hypothetical"]),
                "stop_price": float(setup["stop_hypothetical"]),
                "c1_target": float(setup["c1_target"]),
                "c2_target": float(setup["c2_target"]),
                "c3_target": c3_target,
                "c3_enabled": c3_enabled,
                "day_type": setup.get("day_type"),
                "killzone": setup.get("killzone"),
                "score": setup.get("setup_quality_score"),
                "vegas_score": setup.get("vegas_score"),
                "tpo_score": setup.get("tpo_score"),
                "fvg_score": setup.get("fvg_score"),
                "footprint_score": setup.get("footprint_score"),
                "score_reasons": setup.get("score_reasons"),
                "vwap_side": setup.get("vwap_side"),
                # Multi-target outcome fields
                "retro_outcome": oc["outcome"],
                "retro_c1_filled": oc["c1_filled"],
                "retro_c2_filled": oc["c2_filled"],
                "retro_c3_filled": oc["c3_filled"],
                "retro_c1_pnl_pts": oc["c1_pnl_pts"],
                "retro_c2_pnl_pts": oc["c2_pnl_pts"],
                "retro_c3_pnl_pts": oc["c3_pnl_pts"],
                "retro_total_pnl_pts": oc["total_pnl_pts"],
                "retro_total_pnl_usd": oc["total_pnl_usd"],
                "retro_mae_pts": oc["mae_pts"],
                "retro_mfe_pts": oc["mfe_pts"],
                "retro_duration_sec": oc["duration_seconds"],
                "retro_n_ticks": oc["n_ticks_walked"],
                "retro_closed_ts": oc["closed_ts"].isoformat()
                    if oc["closed_ts"] and hasattr(oc["closed_ts"], "isoformat") else None,
            })

            stats["processed"] += 1
            outcome_counts[oc["outcome"]] = outcome_counts.get(oc["outcome"], 0) + 1

        except Exception as e:
            stats["errors"] += 1
            if test_mode:
                print(f"  Error on attempt {setup['id']}: {e}")

        # Progress
        if (i + 1) % 500 == 0 or (i + 1) == len(setups):
            print(f"  {i+1}/{len(setups)} processed={stats['processed']} "
                  f"no_ticks={stats['no_ticks']} errors={stats['errors']}")

    # Save results as Parquet
    if results:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = RESULTS_DIR / f"retro_outcomes_{ts_str}.parquet"
        df = pl.DataFrame(results, infer_schema_length=None)
        df.write_parquet(out_path)
        print(f"\n  Results saved: {out_path} ({len(df)} rows)")

    print(f"\n=== Retro Complete (Multi-Target) ===")
    print(f"  Processed:  {stats['processed']}")
    print(f"  No ticks:   {stats['no_ticks']}")
    print(f"  Errors:     {stats['errors']}")
    print(f"  Outcomes:")
    for oc_name in ["HIT_C1", "HIT_C2", "HIT_C3", "PARTIAL", "HIT_STOP", "TIMEOUT"]:
        n = outcome_counts.get(oc_name, 0)
        if n > 0:
            print(f"    {oc_name}: {n}")

    wins = outcome_counts.get("HIT_C1", 0) + outcome_counts.get("HIT_C2", 0) + outcome_counts.get("HIT_C3", 0)
    losses = outcome_counts.get("HIT_STOP", 0)
    if wins + losses > 0:
        print(f"  WR (C1+C2+C3 / wins+losses): {wins/(wins+losses):.1%}")

    if results:
        total_pnl = sum(r["retro_total_pnl_usd"] for r in results)
        print(f"  Total PnL (all setups): ${total_pnl:,.0f}")

    return {**stats, **outcome_counts}
