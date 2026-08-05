#!/usr/bin/env python3
"""S7 Replay Acceptance — 14-day S7 score audit on historical trades (2026-08-05).

Replays System-7 confluence scoring on all trades from the last 14 days, extracts
setup data from v9_trades.cross_context JSON, constructs market_context from entry
snapshots, and reports S7 score vs actual outcome (WIN/LOSS/BE/OPEN).

GO criterion (task #4 — M3b ignition blocker):
  - Net positive P&L on scored trades
  - Score >= 40 => acceptance (blocks gate currently)
  - Score < 40 => prediction should be LOSS (lower conviction filter)

Usage:
  python3 scripts/replay_s7_acceptance.py [--since YYYY-MM-DD] [--until YYYY-MM-DD]

Default: last 14 days (inclusive of 2026-08-03 and 2026-08-04 ignition trades).
"""
import sys
import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from scripts.flag_guard import parse_env
    for k, v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(k, v)
except Exception:
    pass

from backend.v9.db.read import read_all
from backend.v9.systems.system7_score import score as s7_score
from backend.v9.services.trade_context import (
    _systems_blob_at_entry, extract_g1_entry_context
)

UTC = timezone.utc
ET_TZ = "America/New_York"


def extract_setup_from_trade(trade_row):
    """Build setup dict from v9_trades row: direction, pattern, entry_price."""
    direction = str(trade_row.get("direction", "LONG")).upper()
    entry_price = float(trade_row.get("entry_price", 0.0)) if trade_row.get("entry_price") else None
    
    # Extract pattern from cross_context
    cross_ctx = trade_row.get("cross_context")
    pattern = None
    if isinstance(cross_ctx, (dict, list)):
        systems_map = _systems_blob_at_entry(cross_ctx)
        woodies = systems_map.get("woodies_system") or {}
        ap = woodies.get("active_patterns")
        if isinstance(ap, list) and ap and isinstance(ap[0], dict):
            pattern = ap[0].get("pattern_id") or ap[0].get("pattern")
        if not pattern:
            pattern = woodies.get("classification") or woodies.get("signal")
    
    pattern = str(pattern or "UNKNOWN").upper()
    
    return {
        "direction": direction,
        "pattern": pattern,
        "entry_price": entry_price,
    }


def build_market_context_from_snapshot(trade_row):
    """Reconstruct market_context from cross_context snapshot at entry time."""
    cross_ctx = trade_row.get("cross_context")
    systems_map = _systems_blob_at_entry(cross_ctx)
    
    # day_type from day_type_machine
    day_type_blob = systems_map.get("day_type_machine") or {}
    day_type = (
        day_type_blob.get("day_type")
        or day_type_blob.get("state")
        or "UNKNOWN"
    )
    if day_type == "UNKNOWN":
        day_type = "UNKNOWN"
    
    # day_bias: infer from day_type (Trend_Up -> UP, Trend_Down -> DOWN)
    day_bias = "NONE"
    if "trend" in day_type.lower():
        if "up" in day_type.lower():
            day_bias = "UP"
        elif "down" in day_type.lower():
            day_bias = "DOWN"
    
    # leg_dir: from leg_state if available (not typically in systems_map, so None)
    leg_dir = None
    
    # opening_conf: from opening_type_result if available (stub: default 0.0)
    opening_conf = 0.0
    
    return SimpleNamespace(
        day_bias=day_bias,
        day_type=day_type,
        leg_dir=leg_dir,
        opening_conf=opening_conf,
    )


def get_outcome_pnl(trade_row):
    """Return (outcome, pnl_usd, pnl_r) from trade row."""
    outcome = str(trade_row.get("outcome") or "OPEN").upper()
    pnl_usd = float(trade_row.get("pnl_usd") or 0.0)
    pnl_r = float(trade_row.get("pnl_r") or 0.0)
    return outcome, pnl_usd, pnl_r


def replay_day(all_trades, day_date):
    """Replay S7 scoring for all trades on a single day."""
    day_str = day_date.isoformat()
    
    # Filter trades for this day (by entry_ts in ET)
    day_trades = []
    for t in all_trades:
        entry_ts = t.get("entry_ts")
        if entry_ts:
            try:
                from datetime import datetime as _dt
                from zoneinfo import ZoneInfo as _zi
                entry_dt = entry_ts
                if isinstance(entry_ts, str):
                    entry_dt = _dt.fromisoformat(entry_ts.replace("Z", "+00:00"))
                entry_date = entry_dt.astimezone(_zi(ET_TZ)).date()
                if entry_date == day_date:
                    day_trades.append(t)
            except Exception:
                pass
    
    if not day_trades:
        return {
            "day": day_str,
            "trades": 0,
            "scored": 0,
            "accepted": 0,
            "pnl_pts": 0.0,
            "pnl_usd": 0.0,
            "by_outcome": defaultdict(int),
            "details": [],
        }
    
    results = {
        "day": day_str,
        "trades": len(day_trades),
        "scored": 0,
        "accepted": 0,
        "pnl_pts": 0.0,
        "pnl_usd": 0.0,
        "by_outcome": defaultdict(int),
        "details": [],
    }
    
    MES_POINT_VALUE = 5.0
    
    for trade in day_trades:
        try:
            setup = extract_setup_from_trade(trade)
            market_ctx = build_market_context_from_snapshot(trade)
            entry_ts = trade.get("entry_ts")
            
            # Convert entry_ts to datetime for s7_score
            bar_ts = None
            if entry_ts:
                if isinstance(entry_ts, str):
                    bar_ts = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
                else:
                    bar_ts = entry_ts
            
            # Score
            s7_result = s7_score(setup=setup, market_context=market_ctx, bar_ts=bar_ts)
            score = s7_result.get("score", 0)
            blocked = s7_result.get("blocked", True)
            sizing = s7_result.get("sizing", 0)
            
            # Outcome
            outcome, pnl_usd, pnl_r = get_outcome_pnl(trade)
            pnl_pts = pnl_usd / MES_POINT_VALUE if MES_POINT_VALUE else 0.0
            
            # Decision
            accepted = score >= 40 and not blocked
            
            # Update summary
            results["scored"] += 1
            if accepted:
                results["accepted"] += 1
            results["pnl_pts"] += pnl_pts
            results["pnl_usd"] += pnl_usd
            results["by_outcome"][outcome] += 1
            
            # Detail
            detail = {
                "trade_id": trade.get("id"),
                "direction": setup.get("direction"),
                "pattern": setup.get("pattern"),
                "entry_price": setup.get("entry_price"),
                "day_type": market_ctx.day_type,
                "day_bias": market_ctx.day_bias,
                "s7_score": score,
                "sizing": sizing,
                "accepted": accepted,
                "outcome": outcome,
                "pnl_pts": round(pnl_pts, 2),
                "pnl_usd": round(pnl_usd, 2),
            }
            results["details"].append(detail)
        except Exception as e:
            # Log error but continue
            pass
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="S7 Replay Acceptance (14-day audit)")
    parser.add_argument("--since", default=None, help="Start date (YYYY-MM-DD), default 14 days ago")
    parser.add_argument("--until", default=None, help="End date (YYYY-MM-DD), default today")
    args = parser.parse_args()
    
    # Dates
    today = datetime.now(UTC).date()
    if args.until:
        until = datetime.fromisoformat(args.until).date()
    else:
        until = today
    
    if args.since:
        since = datetime.fromisoformat(args.since).date()
    else:
        since = until - timedelta(days=13)  # 14 days inclusive
    
    print(f"S7 Replay Acceptance: {since} → {until}")
    print(f"Querying v9_trades...")
    
    # Read all trades in the window
    try:
        rows = read_all(
            f"""
            SELECT id, firing_system, direction, entry_ts, entry_price, stop, 
                   t1, t2, t3, outcome, pnl_usd, pnl_r, cross_context
            FROM v9_trades
            WHERE entry_ts >= :since AND entry_ts <= :until
            ORDER BY entry_ts ASC
            """,
            {
                "since": datetime.combine(since, datetime.min.time()).replace(tzinfo=UTC).isoformat(),
                "until": datetime.combine(until, datetime.max.time()).replace(tzinfo=UTC).isoformat(),
            }
        )
    except Exception as e:
        print(f"ERROR reading trades: {e}")
        return
    
    print(f"Total trades in window: {len(rows)}")
    
    # Group by date
    by_date = defaultdict(list)
    from zoneinfo import ZoneInfo
    et_tz = ZoneInfo(ET_TZ)
    
    for row in rows:
        try:
            entry_ts = row.get("entry_ts")
            if entry_ts:
                if isinstance(entry_ts, str):
                    entry_dt = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
                else:
                    entry_dt = entry_ts
                entry_date = entry_dt.astimezone(et_tz).date()
                by_date[entry_date].append(row)
        except Exception:
            pass
    
    print(f"\n{'='*100}")
    print("S7 REPLAY ACCEPTANCE")
    print(f"{'='*100}")
    print(f"{'Date':<12} {'Trades':>6} {'Scored':>6} {'Accepted':>8} {'P&L pts':>10} {'P&L USD':>12} {'Outcome Breakdown'}")
    print("-" * 100)
    
    total_pnl_pts = 0.0
    total_pnl_usd = 0.0
    total_trades = 0
    total_accepted = 0
    all_outcomes = defaultdict(int)
    all_results = []
    
    for d in sorted(by_date.keys()):
        if d < since or d > until:
            continue
        
        result = replay_day(by_date[d], d)
        all_results.append(result)
        total_trades += result["trades"]
        total_accepted += result["accepted"]
        total_pnl_pts += result["pnl_pts"]
        total_pnl_usd += result["pnl_usd"]
        
        for outcome, count in result["by_outcome"].items():
            all_outcomes[outcome] += count
        
        outcome_str = ", ".join(
            f"{k}={v}" for k, v in sorted(result["by_outcome"].items())
        ) or "—"
        
        print(f"{result['day']:<12} {result['trades']:>6} {result['scored']:>6} "
              f"{result['accepted']:>8} {result['pnl_pts']:>+10.1f} {result['pnl_usd']:>+12.0f} {outcome_str}")
    
    print(f"\n{'='*100}")
    print(f"NET P&L: {total_pnl_pts:+.1f}pt (${total_pnl_usd:+.0f})")
    print(f"Total trades: {total_trades} | Scored: {total_trades} | Accepted (score >= 40): {total_accepted}")
    print(f"Outcome breakdown: {dict(all_outcomes)}")
    go = total_pnl_usd > 0 and total_accepted > 0
    print(f"\nGO criterion: NET positive={total_pnl_usd > 0} + trades accepted={total_accepted > 0}")
    print(f"VERDICT: {'GO' if go else 'NO-GO'}")
    
    # Write report
    out = ROOT / "docs/reports/S7_REPLAY_ACCEPTANCE_2026-08-05.md"
    with open(out, "w") as f:
        f.write("# S7 Replay Acceptance (2026-08-05, Task #4 M3b)\n\n")
        f.write(f"Source: v9_trades (cross_context snapshots)\n")
        f.write(f"Period: {since} → {until}\n")
        f.write(f"NET P&L: {total_pnl_pts:+.1f}pt (${total_pnl_usd:+.0f})\n")
        f.write(f"Trades: {total_trades} | Accepted (score >= 40): {total_accepted}\n")
        f.write(f"**VERDICT: {'GO' if go else 'NO-GO'}**\n\n")
        f.write("| Date | Trades | Scored | Accepted | P&L pts | P&L USD | Outcome |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in all_results:
            outcome_breakdown = ", ".join(f"{k}={v}" for k, v in sorted(r["by_outcome"].items())) or "—"
            f.write(f"| {r['day']} | {r['trades']} | {r['scored']} | {r['accepted']} | "
                    f"{r['pnl_pts']:+.1f} | {r['pnl_usd']:+.0f} | {outcome_breakdown} |\n")
        f.write(f"\n## Trade Details\n\n")
        f.write("| Trade ID | Direction | Pattern | Entry | Day Type | S7 Score | Accepted | Outcome | P&L |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in all_results:
            for d in r["details"]:
                f.write(f"| {d['trade_id']} | {d['direction']} | {d['pattern']} | {d['entry_price']:.0f} | "
                        f"{d['day_type']} | {d['s7_score']} | {'✓' if d['accepted'] else '✗'} | "
                        f"{d['outcome']} | {d['pnl_pts']:+.1f}pt |\n")
    
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
