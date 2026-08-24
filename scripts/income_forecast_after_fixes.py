#!/usr/bin/env python3
"""Session-block bootstrap income forecast from an integrated replay JSON.

This is a distributional estimate, not a promise. It resamples contiguous
5-session blocks so daily clustering/regime persistence is not treated as IID.
No production imports, DB writes, flags, or service actions.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from pathlib import Path


DEFAULT_SCENARIOS = {
    "current_all_6c_s1": ("arms", "CURRENT_ALL"),
    "conservative_4c_s2": ("sensitivity", "MAX_CONTEXT_c4_s2"),
    "base_4c_s1": ("sensitivity", "MAX_CONTEXT_c4_s1"),
    "base_6c_s1": ("sensitivity", "MAX_CONTEXT_c6_s1"),
    "two_slot_6c_s1_research": ("sensitivity", "MAX_2SLOT_c6_s1"),
    "two_slot_6c_s2_stress": ("sensitivity", "MAX_2SLOT_c6_s2"),
}


def percentile(values, p):
    xs = sorted(values)
    if not xs:
        return 0.0
    pos = (len(xs) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def drawdown(daily):
    equity = peak = 0.0
    worst = 0.0
    for value in daily:
        equity += value
        peak = max(peak, equity)
        worst = min(worst, equity - peak)
    return abs(worst)


def max_losing_streak(daily):
    best = cur = 0
    for value in daily:
        if value < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def moving_block_month(days, month_sessions, block, rng):
    n = len(days)
    sampled = []
    while len(sampled) < month_sessions:
        start = rng.randrange(n)
        sampled.extend(days[(start + j) % n] for j in range(block))
    return sampled[:month_sessions]


def summarize_scenario(per_day, iterations, seed, month_sessions, block):
    ordered = [float(per_day[d]) for d in sorted(per_day)]
    rng = random.Random(seed)
    monthly, dds, streaks, worst_days = [], [], [], []
    positive_days = []
    for _ in range(iterations):
        sample = moving_block_month(ordered, month_sessions, block, rng)
        monthly.append(sum(sample))
        dds.append(drawdown(sample))
        streaks.append(max_losing_streak(sample))
        worst_days.append(min(sample))
        positive_days.append(sum(1 for x in sample if x > 0))

    positives = [x for x in ordered if x > 0]
    gross_positive = sum(positives)
    top_day_share = (
        max(positives) / gross_positive if positives and gross_positive else 0.0)
    return {
        "history_sessions": len(ordered),
        "historical_total": round(sum(ordered), 2),
        "historical_mean_day": round(statistics.fmean(ordered), 2),
        "historical_median_day": round(statistics.median(ordered), 2),
        "historical_positive_days": sum(1 for x in ordered if x > 0),
        "historical_negative_days": sum(1 for x in ordered if x < 0),
        "top_positive_day_share": round(top_day_share, 4),
        "monthly": {
            "mean": round(statistics.fmean(monthly), 2),
            "p10": round(percentile(monthly, 0.10), 2),
            "p25": round(percentile(monthly, 0.25), 2),
            "p50": round(percentile(monthly, 0.50), 2),
            "p75": round(percentile(monthly, 0.75), 2),
            "p90": round(percentile(monthly, 0.90), 2),
            "prob_positive": round(
                sum(1 for x in monthly if x > 0) / len(monthly), 4),
            "prob_loss_gt_800": round(
                sum(1 for x in monthly if x <= -800) / len(monthly), 4),
        },
        "risk": {
            "drawdown_p50": round(percentile(dds, 0.50), 2),
            "drawdown_p90": round(percentile(dds, 0.90), 2),
            "drawdown_p95": round(percentile(dds, 0.95), 2),
            "worst_day_p50": round(percentile(worst_days, 0.50), 2),
            "worst_day_p10": round(percentile(worst_days, 0.10), 2),
            "losing_streak_p50": round(percentile(streaks, 0.50), 1),
            "losing_streak_p90": round(percentile(streaks, 0.90), 1),
            "positive_days_p50": round(percentile(positive_days, 0.50), 1),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--replay-json",
        default="/tmp/maximized_opportunity_20260823.json")
    parser.add_argument(
        "--json",
        default="/tmp/income_forecast_after_fixes_20260824.json")
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=260824)
    parser.add_argument("--month-sessions", type=int, default=20)
    parser.add_argument("--block", type=int, default=5)
    parser.add_argument(
        "--exclude-dates", default="",
        help="comma-separated YYYY-MM-DD sessions excluded for data quality")
    args = parser.parse_args()

    replay = json.loads(Path(args.replay_json).read_text())
    excluded = {x.strip() for x in args.exclude_dates.split(",") if x.strip()}
    output = {
        "meta": {
            "method": "circular moving-block bootstrap over session PnL",
            "iterations": args.iterations,
            "seed": args.seed,
            "month_sessions": args.month_sessions,
            "block_sessions": args.block,
            "source": args.replay_json,
            "excluded_dates": sorted(excluded),
            "warning": (
                "Retrospective 34-session estimate; not true forward evidence. "
                "P3/T10 management deltas are not naively added."),
        },
        "scenarios": {},
    }
    for name, (section, key) in DEFAULT_SCENARIOS.items():
        row = replay[section][key]
        per_day = {
            day: value for day, value in row["per_day"].items()
            if day not in excluded
        }
        output["scenarios"][name] = summarize_scenario(
            per_day, args.iterations, args.seed,
            args.month_sessions, args.block)

    Path(args.json).write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    print(f"[out] {args.json}")


if __name__ == "__main__":
    main()
