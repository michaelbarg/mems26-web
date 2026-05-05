"""
Daily Discrepancy Check — re-runnable script for Day 3-5 trend analysis.

Compares MDS baseline with production daily metrics.
Run: python3 -m tools.multidim_sim.discrepancy_research.daily_discrepancy_check
"""

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

CACHE_DIR = Path(__file__).parent.parent / "cache"
BACKEND_URL = "https://mems26-web.onrender.com"


def load_mds_baseline():
    """Load MDS dataset, dedup, compute outcome-based metrics."""
    candidates = sorted(CACHE_DIR.glob("setups_clean_*_full.parquet"))
    if not candidates:
        raise FileNotFoundError("No cached dataset")
    df = pl.read_parquet(candidates[-1])
    df = df.with_columns([
        (pl.when(pl.col("direction") == "LONG")
           .then(pl.col("entry_price") - pl.col("stop_price"))
           .otherwise(pl.col("stop_price") - pl.col("entry_price"))
        ).alias("risk_pts"),
    ])
    df = df.filter(pl.col("risk_pts") > 0)

    # Outcome-based WR (correct method)
    total = len(df)
    hit_c1 = len(df.filter(pl.col("outcome") == "HIT_C1"))
    hit_stop = len(df.filter(pl.col("outcome") == "HIT_STOP"))
    timeout = len(df.filter(pl.col("outcome") == "TIMEOUT"))

    wr_outcome = hit_c1 / (hit_c1 + hit_stop) * 100 if (hit_c1 + hit_stop) > 0 else 0

    # Day-type breakdown
    day_type_wr = {}
    for row in df.group_by("day_type").agg([
        (pl.col("outcome") == "HIT_C1").sum().alias("wins"),
        (pl.col("outcome") == "HIT_STOP").sum().alias("losses"),
        pl.len().alias("count"),
    ]).to_dicts():
        dt = row["day_type"] or "NONE"
        w, l = row["wins"], row["losses"]
        day_type_wr[dt] = {
            "count": row["count"],
            "wr": round(w / (w + l) * 100, 1) if (w + l) > 0 else 0,
        }

    return {
        "total": total,
        "wr_outcome": round(wr_outcome, 1),
        "hit_c1": hit_c1,
        "hit_stop": hit_stop,
        "timeout": timeout,
        "day_type_wr": day_type_wr,
    }


def get_production_today():
    """Fetch today's production metrics from backend API."""
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/analytics/setups/today_summary")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data
    except Exception as e:
        return {"error": str(e)}


def run():
    print("=" * 60)
    print(f"  Daily Discrepancy Check — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # MDS Baseline
    mds = load_mds_baseline()
    print(f"\n  MDS Baseline (outcome-based):")
    print(f"    Total: {mds['total']} setups")
    print(f"    WR: {mds['wr_outcome']}% (HIT_C1 / (HIT_C1 + HIT_STOP))")
    print(f"    HIT_C1: {mds['hit_c1']}, HIT_STOP: {mds['hit_stop']}, TIMEOUT: {mds['timeout']}")
    print(f"    Day-type WR:")
    for dt, info in sorted(mds["day_type_wr"].items()):
        print(f"      {dt:<15} {info['count']:>5} setups  WR={info['wr']:.1f}%")

    # Production Today
    prod = get_production_today()
    if "error" in prod:
        print(f"\n  Production: ERROR — {prod['error']}")
        return

    prod_wr = prod.get("win_rate", 0)
    prod_closed = prod.get("closed", 0)
    prod_wins = prod.get("wins", 0)
    prod_losses = prod.get("losses", 0)
    prod_be = prod.get("breakeven", 0)
    prod_pnl = prod.get("total_pnl_net_usd", 0)

    print(f"\n  Production Today ({prod.get('date', 'unknown')}):")
    print(f"    Closed: {prod_closed} trades")
    print(f"    Wins: {prod_wins}, Losses: {prod_losses}, BE: {prod_be}")
    print(f"    WR: {prod_wr}%")
    print(f"    Net PnL: ${prod_pnl:.2f}")
    print(f"    Avg/trade: ${prod.get('avg_pnl_per_trade', 0):.2f}")

    # Gap Analysis
    gap = mds["wr_outcome"] - prod_wr
    print(f"\n  Gap Analysis:")
    print(f"    MDS outcome WR:    {mds['wr_outcome']}%")
    print(f"    Production WR:     {prod_wr}%")
    print(f"    Gap:               {gap:+.1f}pp")

    if gap > 20:
        print(f"    ⚠️  LARGE GAP — investigate day type + sample size")
    elif gap > 10:
        print(f"    ⚡ MODERATE GAP — likely day-type effect")
    else:
        print(f"    ✅ WITHIN EXPECTED VARIANCE")


if __name__ == "__main__":
    run()
