#!/usr/bin/env python3
"""
Backtest Suffering Side Veto on historical setup attempts.

Per D-049, D-065. Validates the gate against existing setups in Postgres.

Usage:
    python tools/backtest_d049.py
    python tools/backtest_d049.py --output reports/d049_backtest.md
    python tools/backtest_d049.py --since 2026-04-01

Reports:
- Total setups analyzed
- How many would have been BLOCKED
- Of blocked: % that were losers (QC metric per D-062)
- Of allowed: win rate
- Per direction (LONG/SHORT) breakdown
- Per day_type breakdown
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from gates.suffering_side import check_suffering_side


async def main():
    parser = argparse.ArgumentParser(description="Backtest D-049 Suffering Side Veto")
    parser.add_argument("--output", default="reports/d049_backtest.md",
                        help="Output report path")
    parser.add_argument("--since", help="Filter setups since YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without DB connection")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY-RUN: Generating sample report with synthetic data")
        await _generate_sample_report(args.output)
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set.")
        print("  Set it with: export DATABASE_URL=postgres://...")
        print("  Or run with --dry-run for a sample report")
        sys.exit(1)

    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg not installed. Run: pip install asyncpg")
        sys.exit(1)

    conn = await asyncpg.connect(db_url)
    try:
        setups = await _fetch_setups(conn, args.since)
        print(f"Fetched {len(setups)} closed setup attempts")

        if not setups:
            print("No setups found. Nothing to backtest.")
            return

        stats = _run_backtest(setups)
        _write_report(stats, args.output)
        _print_summary(stats)
    finally:
        await conn.close()


async def _fetch_setups(conn, since=None):
    """Fetch closed setups with POC data from Postgres."""
    # Check which columns exist (day_poc may not exist yet)
    cols = await conn.fetch("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'setup_attempts'
    """)
    col_names = {r["column_name"] for r in cols}

    has_day_poc = "day_poc" in col_names
    has_pnl = "pnl_net_usd" in col_names

    # Build query based on available columns
    select_cols = ["id", "direction", "entry_price", "day_type", "created_at"]

    if has_day_poc:
        select_cols.append("day_poc")
    if has_pnl:
        select_cols.append("pnl_net_usd")
    elif "pnl_pts" in col_names:
        select_cols.append("pnl_pts")

    # Also try to get POC from market context if day_poc column doesn't exist
    if "market_context" in col_names and not has_day_poc:
        select_cols.append("market_context")

    if "close_reason" in col_names:
        select_cols.append("close_reason")
    if "setup_quality_score" in col_names:
        select_cols.append("setup_quality_score")

    query = f"SELECT {', '.join(select_cols)} FROM setup_attempts"
    conditions = []

    if "close_reason" in col_names:
        conditions.append("close_reason IS NOT NULL")
    conditions.append("entry_price IS NOT NULL")
    conditions.append("direction IS NOT NULL")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if since:
        query += f" AND created_at >= '{since}'"

    query += " ORDER BY created_at DESC"

    rows = await conn.fetch(query)
    return [dict(r) for r in rows]


def _extract_poc(setup):
    """Extract day POC from setup record, trying multiple sources."""
    # Direct column
    poc = setup.get("day_poc")
    if poc and float(poc) > 0:
        return float(poc)

    # From market_context JSONB
    ctx = setup.get("market_context")
    if ctx and isinstance(ctx, dict):
        poc = ctx.get("day_poc") or ctx.get("poc_price")
        if poc and float(poc) > 0:
            return float(poc)

    return None


def _extract_pnl(setup):
    """Extract PnL from setup, trying multiple columns."""
    for col in ("pnl_net_usd", "pnl_pts"):
        val = setup.get(col)
        if val is not None:
            return float(val)
    return 0


def _run_backtest(setups):
    """Run the gate against all setups and collect stats."""
    stats = {
        "total": 0,
        "with_poc": 0,
        "without_poc": 0,
        "blocked": 0,
        "passed": 0,
        "warning": 0,
        "blocked_losers": 0,
        "blocked_winners": 0,
        "blocked_breakeven": 0,
        "passed_winners": 0,
        "passed_losers": 0,
        "passed_breakeven": 0,
        "by_direction": defaultdict(lambda: {"blocked": 0, "passed": 0,
                                              "blocked_losers": 0, "blocked_winners": 0}),
        "by_day_type": defaultdict(lambda: {"blocked": 0, "passed": 0,
                                             "blocked_losers": 0, "blocked_winners": 0}),
        "by_reason": defaultdict(int),
        "blocked_pnl_saved": 0,
    }

    for setup in setups:
        stats["total"] += 1
        direction = setup.get("direction", "").upper()
        entry = float(setup.get("entry_price", 0) or 0)
        poc = _extract_poc(setup)
        pnl = _extract_pnl(setup)
        day_type = setup.get("day_type") or "unknown"

        if not poc:
            stats["without_poc"] += 1
            continue

        stats["with_poc"] += 1

        result = check_suffering_side(
            direction=direction, price=entry, day_poc=poc, mode="closed",
        )

        if result.result == "BLOCK":
            stats["blocked"] += 1
            stats["by_direction"][direction]["blocked"] += 1
            stats["by_day_type"][day_type]["blocked"] += 1
            stats["by_reason"][result.reason] += 1

            if pnl > 0:
                stats["blocked_winners"] += 1
                stats["by_direction"][direction]["blocked_winners"] += 1
                stats["by_day_type"][day_type]["blocked_winners"] += 1
            elif pnl < 0:
                stats["blocked_losers"] += 1
                stats["blocked_pnl_saved"] += abs(pnl)
                stats["by_direction"][direction]["blocked_losers"] += 1
                stats["by_day_type"][day_type]["blocked_losers"] += 1
            else:
                stats["blocked_breakeven"] += 1

        elif result.result == "PASS":
            stats["passed"] += 1
            stats["by_direction"][direction]["passed"] += 1
            stats["by_day_type"][day_type]["passed"] += 1

            if pnl > 0:
                stats["passed_winners"] += 1
            elif pnl < 0:
                stats["passed_losers"] += 1
            else:
                stats["passed_breakeven"] += 1

        else:
            stats["warning"] += 1

    return stats


def _write_report(stats, output_path):
    """Write markdown report."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    with open(output_path, "w") as f:
        f.write(f"# D-049 Suffering Side Veto — Backtest Report\n\n")
        f.write(f"**Generated:** {now}\n")
        f.write(f"**Source:** D-049, D-065\n")
        f.write(f"**Zone:** ±{check_suffering_side.__module__} NO_TRADE_ZONE_PT = 2.0\n\n")

        f.write(f"## Summary\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total setups | {stats['total']} |\n")
        f.write(f"| With day_poc | {stats['with_poc']} |\n")
        f.write(f"| Without day_poc (skipped) | {stats['without_poc']} |\n")
        f.write(f"| BLOCKED | {stats['blocked']} |\n")
        f.write(f"| PASSED | {stats['passed']} |\n")
        f.write(f"| WARNING | {stats['warning']} |\n\n")

        # QC metric
        if stats["blocked"] > 0:
            bl_pct = stats["blocked_losers"] / stats["blocked"] * 100
            bw_pct = stats["blocked_winners"] / stats["blocked"] * 100
            f.write(f"## QC Metric (D-062)\n\n")
            f.write(f"**Pass criteria:** ≥75% of blocked setups were losers\n\n")
            f.write(f"| Blocked category | Count | % |\n")
            f.write(f"|------------------|-------|---|\n")
            f.write(f"| Losers | {stats['blocked_losers']} | {bl_pct:.1f}% |\n")
            f.write(f"| Winners | {stats['blocked_winners']} | {bw_pct:.1f}% |\n")
            f.write(f"| Breakeven | {stats['blocked_breakeven']} | — |\n\n")
            f.write(f"| PnL saved by blocking losers | ${stats['blocked_pnl_saved']:.2f} |\n\n")

            if bl_pct >= 75:
                f.write(f"**Status:** PASS — gate correctly identifies losers\n\n")
            elif bl_pct >= 60:
                f.write(f"**Status:** MARGINAL — gate working but consider tuning zone size\n\n")
            else:
                f.write(f"**Status:** FAIL — gate blocking too many winners, revisit logic\n\n")

        # Allowed WR
        allowed_total = stats["passed_winners"] + stats["passed_losers"]
        if allowed_total > 0:
            wr = stats["passed_winners"] / allowed_total * 100
            f.write(f"## Allowed Trades Win Rate\n\n")
            f.write(f"- Winners: {stats['passed_winners']}/{allowed_total} ({wr:.1f}%)\n\n")

        # By direction
        f.write(f"## By Direction\n\n")
        f.write(f"| Direction | Blocked | Passed | Blocked Losers | Blocked Winners |\n")
        f.write(f"|-----------|---------|--------|----------------|------------------|\n")
        for d, c in sorted(stats["by_direction"].items()):
            f.write(f"| {d} | {c['blocked']} | {c['passed']} | {c['blocked_losers']} | {c['blocked_winners']} |\n")

        # By day type
        f.write(f"\n## By Day Type\n\n")
        f.write(f"| Day Type | Blocked | Passed | Blocked Losers | Blocked Winners |\n")
        f.write(f"|----------|---------|--------|----------------|------------------|\n")
        for dt, c in sorted(stats["by_day_type"].items()):
            f.write(f"| {dt} | {c['blocked']} | {c['passed']} | {c['blocked_losers']} | {c['blocked_winners']} |\n")

        # By reason
        f.write(f"\n## By Block Reason\n\n")
        f.write(f"| Reason | Count |\n")
        f.write(f"|--------|-------|\n")
        for reason, count in sorted(stats["by_reason"].items(), key=lambda x: -x[1]):
            f.write(f"| {reason} | {count} |\n")

    print(f"Report written to: {output_path}")


def _print_summary(stats):
    """Print key numbers to stdout."""
    print(f"\n{'='*50}")
    print(f"D-049 BACKTEST SUMMARY")
    print(f"{'='*50}")
    print(f"Total:        {stats['total']}")
    print(f"With POC:     {stats['with_poc']}")
    print(f"Blocked:      {stats['blocked']}")
    print(f"Passed:       {stats['passed']}")
    if stats["blocked"] > 0:
        bl_pct = stats["blocked_losers"] / stats["blocked"] * 100
        print(f"Blocked losers: {stats['blocked_losers']}/{stats['blocked']} ({bl_pct:.1f}%)")
        print(f"PnL saved:    ${stats['blocked_pnl_saved']:.2f}")
    print(f"{'='*50}")


async def _generate_sample_report(output_path):
    """Generate a sample report with synthetic data for testing."""
    # Synthetic test cases matching real market scenarios
    test_cases = [
        # (direction, price, poc, pnl) — simulates historical setups
        ("LONG", 5735.0, 5730.0, 25.0),    # PASS: above POC, winner
        ("LONG", 5725.0, 5730.0, -15.0),   # BLOCK: below POC, loser (correctly blocked)
        ("SHORT", 5725.0, 5730.0, 20.0),   # PASS: below POC, winner
        ("SHORT", 5735.0, 5730.0, -10.0),  # BLOCK: above POC, loser (correctly blocked)
        ("LONG", 5731.0, 5730.0, -8.0),    # BLOCK: in zone, loser
        ("SHORT", 5729.0, 5730.0, -12.0),  # BLOCK: in zone, loser
        ("LONG", 5728.0, 5730.0, 30.0),    # BLOCK: below POC, winner (false block)
        ("LONG", 5740.0, 5730.0, -5.0),    # PASS: above POC, loser
        ("SHORT", 5720.0, 5730.0, 15.0),   # PASS: below POC, winner
        ("LONG", 5732.25, 5730.0, 10.0),   # PASS: just past zone, winner
    ]

    stats = {
        "total": len(test_cases), "with_poc": len(test_cases), "without_poc": 0,
        "blocked": 0, "passed": 0, "warning": 0,
        "blocked_losers": 0, "blocked_winners": 0, "blocked_breakeven": 0,
        "passed_winners": 0, "passed_losers": 0, "passed_breakeven": 0,
        "by_direction": defaultdict(lambda: {"blocked": 0, "passed": 0,
                                              "blocked_losers": 0, "blocked_winners": 0}),
        "by_day_type": defaultdict(lambda: {"blocked": 0, "passed": 0,
                                             "blocked_losers": 0, "blocked_winners": 0}),
        "by_reason": defaultdict(int),
        "blocked_pnl_saved": 0,
    }

    for direction, price, poc, pnl in test_cases:
        result = check_suffering_side(direction=direction, price=price, day_poc=poc, mode="closed")

        if result.result == "BLOCK":
            stats["blocked"] += 1
            stats["by_direction"][direction]["blocked"] += 1
            stats["by_day_type"]["NORMAL"]["blocked"] += 1
            stats["by_reason"][result.reason] += 1
            if pnl > 0:
                stats["blocked_winners"] += 1
                stats["by_direction"][direction]["blocked_winners"] += 1
                stats["by_day_type"]["NORMAL"]["blocked_winners"] += 1
            elif pnl < 0:
                stats["blocked_losers"] += 1
                stats["blocked_pnl_saved"] += abs(pnl)
                stats["by_direction"][direction]["blocked_losers"] += 1
                stats["by_day_type"]["NORMAL"]["blocked_losers"] += 1
        else:
            stats["passed"] += 1
            stats["by_direction"][direction]["passed"] += 1
            stats["by_day_type"]["NORMAL"]["passed"] += 1
            if pnl > 0:
                stats["passed_winners"] += 1
            elif pnl < 0:
                stats["passed_losers"] += 1

    _write_report(stats, output_path)
    _print_summary(stats)
    print(f"\nNote: This is a DRY-RUN with synthetic data.")
    print(f"Run without --dry-run with DATABASE_URL set for real data.")


if __name__ == "__main__":
    asyncio.run(main())
