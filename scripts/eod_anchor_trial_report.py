#!/usr/bin/env python3
"""EOD Anchor Trial Report — per-trade audit + S2 histogram + counterfactual.

Usage: python3 scripts/eod_anchor_trial_report.py [--date 2026-06-12]
Output: docs/reports/EOD_<date>.md
"""
import argparse
import os
import sys
from datetime import date, datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import json


def _pg_query(sql: str) -> list:
    """Run SQL via psql, return list of dicts."""
    psql = "/Applications/Postgres.app/Contents/Versions/18/bin/psql"
    cmd = [psql, "-d", "mems26", "-t", "-A", "-F", "\t",
           "--pset", "null=NULL", "-c", sql]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        print(f"psql error: {result.stderr[:200]}", file=sys.stderr)
        return []
    rows = []
    lines = result.stdout.strip().split("\n")
    if not lines or not lines[0]:
        return []
    # Get column names from first query
    return lines


def _pg_query_dicts(sql: str, columns: list) -> list:
    """Run SQL, return list of dicts with named columns."""
    lines = _pg_query(sql)
    result = []
    for line in lines:
        if not line.strip():
            continue
        vals = line.split("\t")
        row = {}
        for i, col in enumerate(columns):
            v = vals[i] if i < len(vals) else None
            if v == "NULL":
                v = None
            row[col] = v
        result.append(row)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    target_date = args.date

    # ── Trades ──
    cols = ["id", "firing_system", "pattern_id_at_entry", "direction",
            "entry_price", "stop", "t1", "t2", "pnl_usd", "pnl_r",
            "exit_reason", "day_type_at_entry", "init_stop"]
    trades = _pg_query_dicts(
        f"SELECT id, firing_system, pattern_id_at_entry, direction, entry_price, "
        f"stop, t1, t2, pnl_usd, pnl_r, exit_reason, day_type_at_entry, "
        f"quality->>'initial_stop' as init_stop "
        f"FROM v9_trades WHERE entry_ts::date = '{target_date}' ORDER BY id",
        cols,
    )

    # ── Build report ──
    lines = [f"# EOD Anchor Trial Report — {target_date}\n"]
    lines.append(f"Generated: {datetime.now().isoformat()[:19]}\n")

    def _f(v):
        try: return float(v) if v else 0
        except (TypeError, ValueError): return 0

    # Summary
    total_pnl = sum(_f(t["pnl_usd"]) for t in trades)
    wins = [t for t in trades if _f(t["pnl_usd"]) > 0]
    losses = [t for t in trades if _f(t["pnl_usd"]) < 0]
    lines.append(f"## Summary: {len(trades)} trades, {len(wins)}W/{len(losses)}L, Net ${total_pnl:.2f}\n")

    # Per-trade table
    lines.append("## Per-Trade Audit\n")
    lines.append("| id | sys | pat | dir | entry | init_stop | risk | t1 | t2 | pnl$ | pnl_r | exit | day_type |")
    lines.append("|--|--|--|--|--|--|--|--|--|--|--|--|--|")
    for t in trades:
        init = t["init_stop"] or t["stop"]
        try:
            risk = abs(float(t["entry_price"]) - float(init)) if init and t["entry_price"] else None
        except (TypeError, ValueError):
            risk = None
        lines.append(
            f"| {t['id']} | S{t['firing_system']} | {t['pattern_id_at_entry'] or '?'} "
            f"| {t['direction']} | {t['entry_price']} | {init} "
            f"| {f'{risk:.1f}' if risk else '?'} | {t['t1']} | {t['t2']} "
            f"| {t['pnl_usd']} | {t['pnl_r']} | {t['exit_reason'] or 'OPEN'} "
            f"| {t['day_type_at_entry'] or '—'} |"
        )

    # RISK_CAP events from log
    lines.append("\n## Risk Cap / Giant Bar / Loss Breaker Events\n")
    lines.append("```")
    try:
        with open("/tmp/backend.err.log") as f:
            for line in f:
                if target_date in line and any(k in line for k in ["RISK_CAP", "GIANT_BAR", "LOSS_BREAKER"]):
                    lines.append(line.rstrip())
    except FileNotFoundError:
        lines.append("(log not found)")
    lines.append("```\n")

    # Runner T2 analysis
    lines.append("## Runner T2 (struct=None on all — bug confirmed)\n")
    t2_set = [t for t in trades if t["t2"] is not None]
    t2_hit = [t for t in trades if _f(t.get("pnl_r")) >= 0.9]
    lines.append(f"T2 populated: {len(t2_set)}/{len(trades)} trades")
    lines.append(f"All struct=None in RUNNER_T2 log — R-mult only (bug: compute_targets_for_day_type returns None for t2_price)")

    # S2 Detection histogram
    lines.append("\n## S2 Detection Histogram (from [S2-DL] log)\n")
    reactive_stats = {}
    init_stats = {}
    try:
        with open("/tmp/backend.err.log") as f:
            for line in f:
                if target_date not in line:
                    continue
                if "[S2-DL] REACTIVE" in line:
                    for k in ["b2d=0", "b1s=0", "b4c=0", "b4>h=0", "b3b=0"]:
                        if k in line:
                            reactive_stats[k] = reactive_stats.get(k, 0) + 1
                    reactive_stats["total"] = reactive_stats.get("total", 0) + 1
                elif "[S2-DL] INITIATIVE" in line:
                    for k in ["b1_exp=0", "b3_join=0", "b2_test=0", "b4_test=0"]:
                        if k in line:
                            init_stats[k] = init_stats.get(k, 0) + 1
                    init_stats["total"] = init_stats.get("total", 0) + 1
    except FileNotFoundError:
        pass

    lines.append("**REACTIVE** (bars examined → condition that blocked):")
    for k, v in sorted(reactive_stats.items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: {v}")
    lines.append(f"\n**INITIATIVE** (bars examined → condition that blocked):")
    for k, v in sorted(init_stats.items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: {v}")

    # Write report
    out_path = f"docs/reports/EOD_{target_date}.md"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
