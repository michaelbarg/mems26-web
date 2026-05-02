#!/usr/bin/env python3
"""
MEMS26 Backtest Framework V1 — Run alternative scoring scenarios against
historical setup_attempts data via the API.

Usage:
    python3 run_scenarios.py --scenarios scenarios.yaml
    python3 run_scenarios.py --only baseline,combined_v2
    python3 run_scenarios.py --api-url https://mems26-web.onrender.com

Reads: API endpoints (read-only).
Writes: CSV reports to tools/backtest/output/
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

import yaml

DEFAULT_API = "https://mems26-web.onrender.com"


# ---------------------------------------------------------------------------
# API data loading
# ---------------------------------------------------------------------------

def api_get(base_url: str, path: str, params: dict = None) -> dict:
    """GET request to API, return parsed JSON."""
    url = f"{base_url.rstrip('/')}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{qs}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  API error {e.code} on {path}: {e.read().decode()[:200]}")
        return {}
    except urllib.error.URLError as e:
        print(f"  Connection error on {path}: {e}")
        return {}


def load_data_from_api(base_url: str):
    """Load setup data via API endpoints.

    Returns (attempts, setups) where:
      - attempts: list of dicts from setup_attempts (with component scores + MAE/MFE)
      - setups: list of dicts from setups (with outcomes)
    """
    # 1) Attempts with component scores (large limit to get all recent)
    print("  Fetching attempts with scores...")
    scored = api_get(base_url, "/analytics/attempts/recent_with_score",
                     {"limit": "10000"})
    scored_attempts = scored.get("attempts", [])
    print(f"    → {len(scored_attempts)} attempts with scores")

    # 2) Attempts with MAE/MFE outcomes
    print("  Fetching attempts with outcomes (MAE/MFE)...")
    outcomes = api_get(base_url, "/analytics/attempts/with_outcomes",
                       {"limit": "10000"})
    outcome_attempts = outcomes.get("attempts", [])
    print(f"    → {len(outcome_attempts)} attempts with MAE/MFE")

    # 3) Merge: outcome_attempts have full data (SELECT * + extra_json flattened)
    # Build lookup by id from outcome data
    outcome_by_id = {}
    for a in outcome_attempts:
        aid = a.get("id")
        if aid is not None:
            outcome_by_id[aid] = a

    # Merge scored_attempts with outcome data
    merged = []
    for a in scored_attempts:
        aid = a.get("id")
        row = dict(a)
        if aid in outcome_by_id:
            oa = outcome_by_id[aid]
            # Add MAE/MFE and extra fields from outcome query
            row["hypothetical_mae_60min_pts"] = oa.get("hypothetical_mae_60min_pts")
            row["hypothetical_mfe_60min_pts"] = oa.get("hypothetical_mfe_60min_pts")
            row["entry_price_hypothetical"] = oa.get("entry_price_hypothetical")
            row["stop_hypothetical"] = oa.get("stop_hypothetical")
            # shadow_structural_stop is flattened from extra_json by _row_to_dict
            row["shadow_structural_stop"] = oa.get("shadow_structural_stop")
        merged.append(row)

    # Also add outcome_attempts that weren't in scored (they may have scores too)
    scored_ids = {a.get("id") for a in scored_attempts}
    for a in outcome_attempts:
        if a.get("id") not in scored_ids:
            # Check if it has component scores
            if any(a.get(k) for k in ["vegas_score", "tpo_score", "fvg_score", "footprint_score"]):
                merged.append(a)

    # 4) Setups with actual outcomes
    print("  Fetching closed setups...")
    closed = api_get(base_url, "/analytics/setups/recent",
                     {"limit": "10000", "status": "CLOSED"})
    setups = closed.get("setups", [])
    print(f"    → {len(setups)} closed setups")

    return merged, setups


# ---------------------------------------------------------------------------
# Scenario engine
# ---------------------------------------------------------------------------

def rescore_setup(attempt: dict, scenario: dict) -> dict:
    """Re-score a single setup attempt using scenario weights.

    Returns dict with: new_score, would_execute, vetoed, skip_reason,
                       size_multiplier, structural_stop_info
    """
    weights = scenario["weights"]
    result = {
        "new_score": 0,
        "would_execute": False,
        "vetoed": False,
        "skip_reason": None,
        "size_multiplier": 1.0,
        "structural_stop_pts": None,
        "structural_better": False,
    }

    # Raw component scores
    vegas_raw = attempt.get("vegas_score") or 0
    tpo_raw = attempt.get("tpo_score") or 0
    fvg_raw = attempt.get("fvg_score") or 0
    fp_raw = attempt.get("footprint_score") or 0

    # --- Day type filter ---
    day_filter = scenario.get("day_type_filter")
    if day_filter:
        block_list = day_filter.get("block", [])
        if attempt.get("day_type") in block_list:
            result["skip_reason"] = f"day_type_blocked:{attempt.get('day_type')}"
            return result

    # --- Re-score ---
    # Production weights (NORMAL day): vegas=30, tpo=25, fvg=25, footprint=20
    # Component scores were computed with those max values.
    # Normalize each component to 0-1, then apply new weight.
    prod_max = {"vegas": 30, "tpo": 25, "fvg": 25, "footprint": 20}

    vegas_norm = min(vegas_raw / prod_max["vegas"], 1.0) if prod_max["vegas"] else 0
    tpo_norm = min(tpo_raw / prod_max["tpo"], 1.0) if prod_max["tpo"] else 0
    fvg_norm = min(fvg_raw / prod_max["fvg"], 1.0) if prod_max["fvg"] else 0
    fp_norm = min(fp_raw / prod_max["footprint"], 1.0) if prod_max["footprint"] else 0

    if scenario.get("score_above_30_uniform"):
        # Binary qualifier: any component > 0 → score = 100
        has_any = (vegas_raw > 0 or tpo_raw > 0 or fvg_raw > 0 or fp_raw > 0)
        new_score = 100 if has_any else 0
    else:
        # Weighted sum (weights should sum to 100)
        new_score = (vegas_norm * weights["vegas"]
                     + tpo_norm * weights["tpo"]
                     + fvg_norm * weights["fvg"]
                     + fp_norm * weights["footprint"])
        new_score = int(round(new_score))

    result["new_score"] = new_score

    # --- Score max threshold (Design B: skip score 90+ death trap) ---
    score_max = scenario.get("score_max_threshold")
    if score_max is not None:
        # For binary mode, check original score instead (new_score is always 100)
        check_score = (attempt.get("setup_quality_score") or new_score) if scenario.get("score_above_30_uniform") else new_score
        if check_score > score_max:
            result["skip_reason"] = f"score_above_max:{check_score}>{score_max}"
            return result

    # --- Execution threshold ---
    threshold = scenario.get("execution_threshold", 50)
    if new_score < threshold:
        result["skip_reason"] = f"below_threshold:{new_score}<{threshold}"
        return result

    # --- Footprint veto ---
    if scenario.get("footprint_veto"):
        reasons = attempt.get("score_reasons") or ""
        if "opposes" in reasons.lower() and "delta=" in reasons.lower():
            result["vetoed"] = True
            result["skip_reason"] = "footprint_veto"
            return result

    # --- Direction size bias ---
    dir_bias = scenario.get("direction_size_bias")
    if dir_bias:
        direction = attempt.get("direction", "LONG")
        result["size_multiplier"] = dir_bias.get(direction, 1.0)

    # --- Structural stop ---
    if scenario.get("use_structural_stop"):
        # API flattens extra_json, so shadow_structural_stop is top-level
        shadow = attempt.get("shadow_structural_stop") or {}
        if isinstance(shadow, str):
            try:
                shadow = json.loads(shadow)
            except (json.JSONDecodeError, TypeError):
                shadow = {}
        if shadow.get("structural_stop_valid"):
            result["structural_stop_pts"] = shadow.get("structural_stop_pts")
            result["structural_better"] = shadow.get("structural_better", False)

    result["would_execute"] = True
    return result


def compute_pnl(attempt: dict, score_result: dict) -> dict:
    """Compute hypothetical PnL for a single setup.

    Uses hypothetical MAE/MFE from setup_attempts.
    Returns: {outcome, pnl_pts, pnl_usd}
    """
    mae = attempt.get("hypothetical_mae_60min_pts") or 0
    mfe = attempt.get("hypothetical_mfe_60min_pts") or 0
    size_mult = score_result.get("size_multiplier", 1.0)

    # Default stop = 5pt fixed
    stop_pts = 5.0

    # Structural stop override
    if score_result.get("structural_stop_pts") is not None:
        struct_pts = score_result["structural_stop_pts"]
        if score_result.get("structural_better"):
            stop_pts = struct_pts

    # Determine outcome (R = stop_pts, C1 at 1:1 R:R)
    target_pts = stop_pts

    if mfe >= target_pts:
        outcome = "hit_c1"
        pnl_pts = target_pts
    elif mae >= stop_pts:
        outcome = "hit_stop"
        pnl_pts = -stop_pts
    else:
        outcome = "timeout"
        pnl_pts = (mfe - mae) * 0.5  # conservative estimate

    pnl_usd = pnl_pts * 5.0 * size_mult  # MES = $5/pt

    return {
        "outcome": outcome,
        "pnl_pts": round(pnl_pts, 2),
        "pnl_usd": round(pnl_usd, 2),
        "stop_pts_used": stop_pts,
        "size_multiplier": size_mult,
    }


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

def run_scenario(name: str, scenario: dict, attempts: list, setups: list) -> dict:
    """Run a single scenario against all attempts. Returns summary + details."""

    details = []
    totals = {
        "total": len(attempts),
        "would_execute": 0,
        "wins": 0, "losses": 0, "timeouts": 0,
        "total_pnl_usd": 0.0,
        "skipped_threshold": 0, "skipped_veto": 0,
        "skipped_day_type": 0, "skipped_score_max": 0,
        "buckets": {
            "<30": _empty_bucket(),
            "30-49": _empty_bucket(),
            "50-69": _empty_bucket(),
            "70+": _empty_bucket(),
        },
        "directions": {
            "LONG": _empty_bucket(),
            "SHORT": _empty_bucket(),
        },
    }

    for att in attempts:
        sr = rescore_setup(att, scenario)

        # Classify skip reason
        skip = sr.get("skip_reason") or ""
        if "below_threshold" in skip:
            totals["skipped_threshold"] += 1
        elif "footprint_veto" in skip:
            totals["skipped_veto"] += 1
        elif "day_type_blocked" in skip:
            totals["skipped_day_type"] += 1
        elif "score_above_max" in skip:
            totals["skipped_score_max"] += 1

        if not sr["would_execute"]:
            details.append({
                "id": att.get("id"),
                "direction": att.get("direction"),
                "day_type": att.get("day_type"),
                "orig_score": att.get("setup_quality_score"),
                "new_score": sr["new_score"],
                "would_execute": False,
                "skip_reason": sr.get("skip_reason"),
                "outcome": None,
                "pnl_usd": 0,
            })
            continue

        # Has MAE/MFE data?
        mae = att.get("hypothetical_mae_60min_pts")
        mfe = att.get("hypothetical_mfe_60min_pts")
        if mae is None and mfe is None:
            totals["would_execute"] += 1
            details.append({
                "id": att.get("id"),
                "direction": att.get("direction"),
                "day_type": att.get("day_type"),
                "orig_score": att.get("setup_quality_score"),
                "new_score": sr["new_score"],
                "would_execute": True,
                "skip_reason": None,
                "outcome": "no_data",
                "pnl_usd": 0,
            })
            continue

        pnl = compute_pnl(att, sr)
        totals["would_execute"] += 1
        totals["total_pnl_usd"] += pnl["pnl_usd"]

        if pnl["outcome"] == "hit_c1":
            totals["wins"] += 1
        elif pnl["outcome"] == "hit_stop":
            totals["losses"] += 1
        else:
            totals["timeouts"] += 1

        # Bucket by ORIGINAL score (to show which buckets each scenario picks)
        orig = att.get("setup_quality_score") or sr["new_score"]
        bucket = _score_bucket(orig)
        b = totals["buckets"][bucket]
        b["count"] += 1
        if pnl["outcome"] == "hit_c1":
            b["wins"] += 1
        elif pnl["outcome"] == "hit_stop":
            b["losses"] += 1
        else:
            b["timeouts"] += 1
        b["pnl_usd"] += pnl["pnl_usd"]

        # Direction breakdown
        direction = att.get("direction", "LONG")
        if direction in totals["directions"]:
            d = totals["directions"][direction]
            d["count"] += 1
            if pnl["outcome"] == "hit_c1":
                d["wins"] += 1
            elif pnl["outcome"] == "hit_stop":
                d["losses"] += 1
            else:
                d["timeouts"] += 1
            d["pnl_usd"] += pnl["pnl_usd"]

        details.append({
            "id": att.get("id"),
            "direction": att.get("direction"),
            "day_type": att.get("day_type"),
            "orig_score": att.get("setup_quality_score"),
            "new_score": sr["new_score"],
            "would_execute": True,
            "skip_reason": None,
            "outcome": pnl["outcome"],
            "pnl_pts": pnl["pnl_pts"],
            "pnl_usd": pnl["pnl_usd"],
            "stop_pts": pnl["stop_pts_used"],
            "size_mult": pnl["size_multiplier"],
            "mae": mae,
            "mfe": mfe,
        })

    # Compute derived stats
    executed_with_data = totals["wins"] + totals["losses"] + totals["timeouts"]
    totals["executed_with_data"] = executed_with_data
    totals["wr_pct"] = round(
        100.0 * totals["wins"] / executed_with_data, 1
    ) if executed_with_data > 0 else 0.0
    totals["avg_pnl"] = round(
        totals["total_pnl_usd"] / executed_with_data, 2
    ) if executed_with_data > 0 else 0.0

    return {"name": name, "config": scenario, "totals": totals, "details": details}


def _empty_bucket():
    return {"count": 0, "wins": 0, "losses": 0, "timeouts": 0, "pnl_usd": 0.0}


def _score_bucket(score: int) -> str:
    if score < 30:
        return "<30"
    elif score < 50:
        return "30-49"
    elif score < 70:
        return "50-69"
    else:
        return "70+"


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_summary_table(results: list):
    """Print side-by-side comparison table."""
    print()
    print("=" * 90)
    print("  MEMS26 BACKTEST — SCENARIO COMPARISON")
    print("=" * 90)
    print()
    hdr = f"  {'Scenario':<24} {'Total':>6} {'Exec':>6} {'W/Data':>7} {'WR%':>6} {'PnL($)':>9} {'Avg/tr':>8}"
    print(hdr)
    print("  " + "─" * 86)

    best_pnl = -999999
    best_name = ""
    best_wr = 0

    for r in results:
        t = r["totals"]
        line = (
            f"  {r['name']:<24} "
            f"{t['total']:>6} "
            f"{t['would_execute']:>6} "
            f"{t['executed_with_data']:>7} "
            f"{t['wr_pct']:>5.1f}% "
            f"${t['total_pnl_usd']:>8.2f} "
            f"${t['avg_pnl']:>7.2f}"
        )
        print(line)
        if t["total_pnl_usd"] > best_pnl and t["executed_with_data"] > 0:
            best_pnl = t["total_pnl_usd"]
            best_name = r["name"]
            best_wr = t["wr_pct"]

    print("  " + "─" * 86)
    if best_name:
        baseline_pnl = 0
        baseline_wr = 0
        for r in results:
            if r["name"] == "baseline":
                baseline_pnl = r["totals"]["total_pnl_usd"]
                baseline_wr = r["totals"]["wr_pct"]
                break
        improvement = best_pnl - baseline_pnl
        wr_diff = best_wr - baseline_wr
        print(f"\n  Best scenario: {best_name}")
        print(f"    PnL: ${best_pnl:+.2f} total (${improvement:+.2f} vs baseline)")
        print(f"    WR:  {best_wr:.1f}% ({wr_diff:+.1f}% vs baseline)")
    print()


def print_bucket_breakdown(results: list):
    """Print per-bucket and per-direction breakdowns."""
    for r in results:
        t = r["totals"]
        print(f"\n  --- {r['name']}: {r['config'].get('description', '')} ---")

        # Skip reasons
        skips = []
        if t["skipped_threshold"]:
            skips.append(f"threshold={t['skipped_threshold']}")
        if t["skipped_veto"]:
            skips.append(f"fp_veto={t['skipped_veto']}")
        if t["skipped_day_type"]:
            skips.append(f"day_type={t['skipped_day_type']}")
        if t["skipped_score_max"]:
            skips.append(f"score_max={t['skipped_score_max']}")
        if skips:
            print(f"  Skipped: {', '.join(skips)}")

        # Per-bucket (by original score)
        print(f"\n  {'Bucket':<10} {'Count':>6} {'Wins':>6} {'Loss':>6} {'T/O':>5} {'WR%':>7} {'PnL($)':>9}")
        print(f"  {'─' * 55}")
        for bname in ["<30", "30-49", "50-69", "70+"]:
            b = t["buckets"][bname]
            total_b = b["wins"] + b["losses"] + b["timeouts"]
            wr = round(100 * b["wins"] / total_b, 1) if total_b else 0
            print(f"  {bname:<10} {b['count']:>6} {b['wins']:>6} {b['losses']:>6} "
                  f"{b['timeouts']:>5} {wr:>6.1f}% ${b['pnl_usd']:>8.2f}")

        # Per-direction
        print(f"\n  {'Direction':<10} {'Count':>6} {'Wins':>6} {'Loss':>6} {'T/O':>5} {'WR%':>7} {'PnL($)':>9}")
        print(f"  {'─' * 55}")
        for dname in ["LONG", "SHORT"]:
            d = t["directions"][dname]
            total_d = d["wins"] + d["losses"] + d["timeouts"]
            wr = round(100 * d["wins"] / total_d, 1) if total_d else 0
            print(f"  {dname:<10} {d['count']:>6} {d['wins']:>6} {d['losses']:>6} "
                  f"{d['timeouts']:>5} {wr:>6.1f}% ${d['pnl_usd']:>8.2f}")
    print()


def export_csv(result: dict, output_dir: Path):
    """Export detailed results to CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = output_dir / f"{result['name']}_{ts}.csv"

    fieldnames = [
        "id", "direction", "day_type", "orig_score", "new_score",
        "would_execute", "skip_reason", "outcome", "pnl_pts", "pnl_usd",
        "stop_pts", "size_mult", "mae", "mfe",
    ]

    with open(fname, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in result["details"]:
            writer.writerow(row)

    return fname


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MEMS26 Backtest Framework V1")
    parser.add_argument("--scenarios", default="scenarios.yaml",
                        help="Path to scenarios YAML file")
    parser.add_argument("--only", default=None,
                        help="Comma-separated list of scenario names to run")
    parser.add_argument("--api-url", default=DEFAULT_API,
                        help=f"API base URL (default: {DEFAULT_API})")
    parser.add_argument("--no-csv", action="store_true",
                        help="Skip CSV export")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print per-bucket and per-direction breakdowns")
    args = parser.parse_args()

    # Load scenarios
    yaml_path = Path(args.scenarios)
    if not yaml_path.exists():
        print(f"ERROR: Scenarios file not found: {yaml_path}")
        sys.exit(1)

    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    all_scenarios = config.get("scenarios", {})
    if args.only:
        selected = [s.strip() for s in args.only.split(",")]
        all_scenarios = {k: v for k, v in all_scenarios.items() if k in selected}

    if not all_scenarios:
        print("ERROR: No scenarios to run.")
        sys.exit(1)

    print(f"\nLoading data from API: {args.api_url}")
    attempts, setups = load_data_from_api(args.api_url)
    print(f"\n  Total merged attempts: {len(attempts)}")

    with_fwd = sum(1 for a in attempts
                   if a.get("hypothetical_mae_60min_pts") is not None
                   or a.get("hypothetical_mfe_60min_pts") is not None)
    print(f"  With hypothetical MAE/MFE: {with_fwd}")
    print(f"  Running {len(all_scenarios)} scenarios...")

    # Run scenarios
    results = []
    output_dir = Path(__file__).parent / "output"

    for name, scenario in all_scenarios.items():
        print(f"\n  Running: {name}...")
        r = run_scenario(name, scenario, attempts, setups)
        results.append(r)

        if not args.no_csv:
            csv_path = export_csv(r, output_dir)
            print(f"    → {csv_path}")

    # Output
    print_summary_table(results)

    if args.verbose or len(all_scenarios) <= 8:
        print_bucket_breakdown(results)

    print("Done.\n")


if __name__ == "__main__":
    main()
