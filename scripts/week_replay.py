#!/usr/bin/env python3
"""Week Replay: per-day simulation of Aug 11-14 with today's code.

Reads bars + historical signals from the local Postgres DB, replays each day
with today's parameters (4 contracts, T0=3.0, ladder 1/1/1/1), bar-by-bar
stop/target checking, one-trade-at-a-time.

Output: docs/reports/WEEK_REPLAY_2026-08-17.md

What IS replicated:
  - Signal stream from v9_trades (shadow + live) = what the detectors actually fired
  - One-trade-at-a-time constraint (slot logic)
  - Bar-by-bar stop/target with stop-before-target priority
  - 3 slippage levels (0/1/2 ticks, 1 tick = 0.25 pts)
  - T0 fast-take (entry +/- T0_TARGET_PTS)
  - Current 4-contract 1/1/1/1 ladder

What is NOT replicated (declared limitations):
  - Gateway gate changes (dedup_fire_guard, opening_type_gate, etc.)
  - SCALE_IN (new feature, too complex for offline replay)
  - Smart BE / dynamic trails (trades use original stop/targets from DB)
  - Target realism adjustments
  - Any signal that did NOT fire (we can't see what today's S2/S4 would detect
    differently — the detection code depends on live state)

Usage: python3 scripts/week_replay.py
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# ── DB connection ──
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    sys.exit("psycopg2 not installed. Run: pip install psycopg2-binary")

DB_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")

# ── Parameters (today's code) ──
CONTRACTS = 4
LADDER = (1, 1, 1, 1)  # C1→T0, C2→T1, C3→T2, C4→T3
T0_TARGET_PTS = 3.0
PTS_PER_DOLLAR = 5.0    # MES: $5 per point per contract
TICK_SIZE = 0.25
SLIPPAGE_LEVELS = [0, 1, 2]  # in ticks

# RTH window (CT)
RTH_START = "08:30"
RTH_END = "15:00"

# Trading days to replay (10.08 = Mon, included per handoff "if full bars")
REPLAY_DATES = ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14"]


def connect():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def get_bars(conn, date_str: str) -> List[Dict]:
    """Get RTH bars for a trading day from the canonical table."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ts, open, high, low, close, trend_state, zlr_detected, hfe_detected
            FROM v9_bars_5min_woodies
            WHERE symbol = 'MES'
              AND (ts AT TIME ZONE 'America/Chicago')::date = %s
              AND (ts AT TIME ZONE 'America/Chicago')::time >= '08:30'
              AND (ts AT TIME ZONE 'America/Chicago')::time < '15:05'
            ORDER BY ts ASC
        """, (date_str,))
        return [dict(r) for r in cur.fetchall()]


def get_signals(conn, date_str: str) -> List[Dict]:
    """Get ALL signals (shadow + live) that fired on a trading day."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, mode, firing_system, direction, entry_price, stop, t1, t2, t3, t4,
                   entry_ts, pnl_usd, outcome, exit_reason, state,
                   pattern_id_at_entry, day_type_at_entry
            FROM v9_trades
            WHERE (entry_ts AT TIME ZONE 'America/Chicago')::date = %s
              AND state = 'CLOSED'
            ORDER BY entry_ts ASC
        """, (date_str,))
        return [dict(r) for r in cur.fetchall()]


def get_actual_trades(conn, date_str: str) -> List[Dict]:
    """Get only the LIVE trades (what actually happened)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, mode, firing_system, direction, entry_price, stop, t1, t2, t3, t4,
                   entry_ts, exit_ts, pnl_usd, outcome, exit_reason,
                   pattern_id_at_entry, day_type_at_entry
            FROM v9_trades
            WHERE (entry_ts AT TIME ZONE 'America/Chicago')::date = %s
              AND mode IN ('live', 'demo')
              AND state = 'CLOSED'
            ORDER BY entry_ts ASC
        """, (date_str,))
        return [dict(r) for r in cur.fetchall()]


def get_day_type(conn, date_str: str) -> str:
    """Get the day-type classification for a date."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT day_type_at_entry FROM v9_trades
            WHERE (entry_ts AT TIME ZONE 'America/Chicago')::date = %s
              AND day_type_at_entry IS NOT NULL AND day_type_at_entry != ''
            ORDER BY entry_ts DESC LIMIT 1
        """, (date_str,))
        row = cur.fetchone()
        return row["day_type_at_entry"] if row else "unknown"


def compute_t0(entry: float, direction: str) -> float:
    """Compute T0 fast-take target."""
    if direction == "LONG":
        return round(round((entry + T0_TARGET_PTS) / TICK_SIZE) * TICK_SIZE, 2)
    else:
        return round(round((entry - T0_TARGET_PTS) / TICK_SIZE) * TICK_SIZE, 2)


def simulate_trade(signal: Dict, bars_after_entry: List[Dict],
                   slippage_ticks: int) -> Dict:
    """Simulate a single trade bar-by-bar with given slippage.

    Returns: {outcome, pnl_usd, exit_bar_idx, exit_reason, per_contract_detail}
    """
    direction = signal["direction"].upper()
    entry = float(signal["entry_price"])
    stop = float(signal["stop"])
    t1 = float(signal["t1"]) if signal["t1"] else None
    t2 = float(signal["t2"]) if signal["t2"] else None
    t3 = float(signal["t3"]) if signal["t3"] else None

    # Apply T0 from today's code
    t0 = compute_t0(entry, direction)

    # Slippage: worsens both entries and exits
    slip = slippage_ticks * TICK_SIZE

    # Target sequence for 4 contracts: C1→T0, C2→T1, C3→T2, C4→T3
    targets = [
        ("T0", t0, LADDER[0]),
        ("T1", t1, LADDER[1]),
        ("T2", t2, LADDER[2]),
        ("T3", t3, LADDER[3]),
    ]
    # Filter out None targets
    targets = [(name, price, qty) for name, price, qty in targets if price is not None]

    # Track which targets have been hit
    hit = {name: False for name, _, _ in targets}
    pnl_pts = 0.0
    contracts_out = 0
    detail = []
    exit_reason = None
    exit_bar_idx = None

    for bar_idx, bar in enumerate(bars_after_entry):
        h = float(bar["high"])
        l = float(bar["low"])

        # 1. Stop check FIRST (adverse fill priority)
        stop_hit = False
        if direction == "LONG" and l <= stop:
            stop_hit = True
        elif direction == "SHORT" and h >= stop:
            stop_hit = True

        if stop_hit:
            # All remaining contracts stopped out
            remaining = CONTRACTS - contracts_out
            if remaining > 0:
                stop_fill = stop - slip if direction == "LONG" else stop + slip
                pts = (stop_fill - entry) if direction == "LONG" else (entry - stop_fill)
                pnl_pts += pts * remaining
                detail.append(f"STOP @{stop_fill:.2f} x{remaining} = {pts*remaining:.2f}pts")
                contracts_out = CONTRACTS
            exit_reason = "STOP"
            exit_bar_idx = bar_idx
            break

        # 2. Target checks in order
        for name, price, qty in targets:
            if hit[name]:
                continue
            tgt_hit = False
            if direction == "LONG" and h >= price:
                tgt_hit = True
            elif direction == "SHORT" and l <= price:
                tgt_hit = True

            if tgt_hit:
                tgt_fill = price - slip if direction == "SHORT" else price - slip if direction == "LONG" and slip > 0 else price
                # For targets: LONG gets worse fill (price - slip), SHORT gets worse fill (price + slip)
                if direction == "LONG":
                    tgt_fill = price - slip
                else:
                    tgt_fill = price + slip

                pts = (tgt_fill - entry) if direction == "LONG" else (entry - tgt_fill)
                pnl_pts += pts * qty
                detail.append(f"{name} @{tgt_fill:.2f} x{qty} = {pts*qty:.2f}pts")
                hit[name] = True
                contracts_out += qty

                # After all contracts out, we're done
                if contracts_out >= CONTRACTS:
                    exit_reason = name
                    exit_bar_idx = bar_idx
                    break

        if contracts_out >= CONTRACTS:
            break

    # If day ended with open position, mark as EOD
    if contracts_out < CONTRACTS:
        remaining = CONTRACTS - contracts_out
        if bars_after_entry:
            last_close = float(bars_after_entry[-1]["close"])
            pts = (last_close - entry) if direction == "LONG" else (entry - last_close)
            pnl_pts += pts * remaining
            detail.append(f"EOD @{last_close:.2f} x{remaining} = {pts*remaining:.2f}pts")
        exit_reason = "EOD"
        exit_bar_idx = len(bars_after_entry) - 1 if bars_after_entry else 0

    pnl_usd = pnl_pts * PTS_PER_DOLLAR
    outcome = "WIN" if pnl_usd > 0 else ("BE" if pnl_usd == 0 else "LOSS")

    return {
        "outcome": outcome,
        "pnl_usd": round(pnl_usd, 2),
        "pnl_pts": round(pnl_pts, 2),
        "exit_reason": exit_reason,
        "exit_bar_idx": exit_bar_idx,
        "detail": detail,
        "contracts_out": contracts_out,
    }


def deduplicate_signals(signals: List[Dict]) -> List[Dict]:
    """Remove duplicate signals (same entry_ts, different modes).
    Keep one signal per (entry_ts rounded to minute, direction)."""
    seen = {}
    deduped = []
    for s in signals:
        key = (str(s["entry_ts"])[:16], s["direction"])
        if key not in seen:
            seen[key] = True
            deduped.append(s)
    return deduped


def replay_day(conn, date_str: str) -> Dict:
    """Replay one trading day. Returns the full analysis."""
    bars = get_bars(conn, date_str)
    all_signals = get_signals(conn, date_str)
    actual_trades = get_actual_trades(conn, date_str)
    day_type = get_day_type(conn, date_str)

    # Deduplicate signals (shadow + live often fire at same time)
    signals = deduplicate_signals(all_signals)

    results = {}  # slippage -> list of trade results
    for slip in SLIPPAGE_LEVELS:
        trades = []
        position_open = False
        current_trade_close_bar_idx = -1

        for sig in signals:
            sig_ts = sig["entry_ts"]
            # Find the bar index for this signal's entry
            entry_bar_idx = None
            for i, bar in enumerate(bars):
                if bar["ts"] >= sig_ts:
                    entry_bar_idx = i
                    break

            if entry_bar_idx is None:
                continue

            # One-trade-at-a-time: skip if position is still open
            if position_open and entry_bar_idx <= current_trade_close_bar_idx:
                continue
            position_open = False

            # Bars after entry (bar-close rule: use bars STARTING from entry bar + 1)
            # The entry bar is the one the signal fires on; the NEXT bar is the first
            # that can hit a stop or target (bar-close-only rule).
            bars_after = bars[entry_bar_idx + 1:]

            if not bars_after:
                continue

            result = simulate_trade(sig, bars_after, slip)
            result["signal_id"] = sig["id"]
            result["direction"] = sig["direction"]
            result["entry_price"] = sig["entry_price"]
            result["stop"] = sig["stop"]
            result["t1"] = sig["t1"]
            result["pattern"] = sig.get("pattern_id_at_entry", "")
            result["entry_time"] = sig["entry_ts"]
            result["system"] = sig["firing_system"]
            trades.append(result)

            # Mark position as open until the trade closes
            position_open = True
            close_idx = entry_bar_idx + 1 + (result["exit_bar_idx"] or 0)
            current_trade_close_bar_idx = close_idx

        net_pnl = sum(t["pnl_usd"] for t in trades)
        results[slip] = {
            "trades": trades,
            "net_pnl": round(net_pnl, 2),
            "n_trades": len(trades),
            "wins": sum(1 for t in trades if t["outcome"] == "WIN"),
            "losses": sum(1 for t in trades if t["outcome"] == "LOSS"),
        }

    return {
        "date": date_str,
        "day_type": day_type,
        "n_bars": len(bars),
        "n_signals_total": len(all_signals),
        "n_signals_deduped": len(signals),
        "actual_trades": actual_trades,
        "results": results,
    }


def to_ct(ts) -> str:
    """Convert a timestamp to Chicago time string HH:MM."""
    if ts is None:
        return "?"
    try:
        from zoneinfo import ZoneInfo
        ct = ts.astimezone(ZoneInfo("America/Chicago"))
        return ct.strftime("%H:%M")
    except Exception:
        return ts.strftime("%H:%M") if ts else "?"


def format_actual(actual_trades: List[Dict]) -> str:
    """Format actual trade results."""
    if not actual_trades:
        return "No live trades"
    lines = []
    total = 0.0
    for t in actual_trades:
        pnl = t["pnl_usd"] or 0
        total += pnl
        pat = t.get("pattern_id_at_entry", "?") or "?"
        ct_time = to_ct(t["entry_ts"])
        lines.append(f"  #{t['id']} {ct_time}CT S{t['firing_system']} {t['direction']} "
                      f"{pat}: ${pnl:+.0f} ({t['outcome']})")
    lines.append(f"  **Net: ${total:+.0f}**")
    return "\n".join(lines)


def format_simulated(day_result: Dict, slip: int) -> str:
    """Format simulated trade results for one slippage level."""
    r = day_result["results"][slip]
    if not r["trades"]:
        return "No trades taken"
    lines = []
    for t in r["trades"]:
        ct_time = to_ct(t["entry_time"])
        lines.append(f"  #{t['signal_id']} {ct_time}CT S{t['system']} {t['direction']} "
                      f"{t['pattern']}: ${t['pnl_usd']:+.0f} ({t['outcome']}) "
                      f"[{t['exit_reason']}]")
    lines.append(f"  **Net: ${r['net_pnl']:+.0f}** ({r['n_trades']} trades, "
                  f"{r['wins']}W/{r['losses']}L)")
    return "\n".join(lines)


def generate_report(days: List[Dict]) -> str:
    """Generate the full markdown report."""
    lines = []
    lines.append("# Week Replay: Aug 11-14, 2026 — Today's Code vs Actual")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Parameters:** {CONTRACTS} contracts, ladder {LADDER}, "
                 f"T0={T0_TARGET_PTS}pts, $5/pt/contract")
    lines.append(f"**Slippage levels:** {', '.join(str(s) + ' ticks' for s in SLIPPAGE_LEVELS)}")
    lines.append("")
    lines.append("## Limitations (declared)")
    lines.append("")
    lines.append("- Signal stream = historical v9_trades (what S2/S4 actually fired then)")
    lines.append("- Gateway gates NOT re-evaluated (signals taken as-is)")
    lines.append("- SCALE_IN not replayed")
    lines.append("- Smart BE / dynamic trails not replayed (original stop/targets used)")
    lines.append("- Trades use bar-close-only fill rule (entry bar skipped)")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Day | Type | Actual $ | Sim 0-slip | Sim 1-tick | Sim 2-tick | Gap (0-slip) | Why |")
    lines.append("|-----|------|----------|------------|------------|------------|--------------|-----|")

    for day in days:
        actual_pnl = sum((t["pnl_usd"] or 0) for t in day["actual_trades"])
        sim0 = day["results"][0]["net_pnl"]
        sim1 = day["results"][1]["net_pnl"]
        sim2 = day["results"][2]["net_pnl"]
        gap = sim0 - actual_pnl
        n_actual = len(day["actual_trades"])
        n_sim = day["results"][0]["n_trades"]

        why = []
        if n_sim != n_actual:
            why.append(f"{n_sim} vs {n_actual} trades")
        if abs(gap) > 10:
            if n_sim > n_actual:
                why.append("sim took more signals (slot freed earlier)")
            elif n_sim < n_actual:
                why.append("sim skipped signals (slot occupied)")
        if not why:
            why.append("fill timing / slippage")

        lines.append(f"| {day['date']} | {day['day_type']} | ${actual_pnl:+.0f} "
                      f"| ${sim0:+.0f} | ${sim1:+.0f} | ${sim2:+.0f} "
                      f"| ${gap:+.0f} | {'; '.join(why)} |")

    total_actual = sum(sum((t["pnl_usd"] or 0) for t in d["actual_trades"]) for d in days)
    total_sim0 = sum(d["results"][0]["net_pnl"] for d in days)
    total_sim1 = sum(d["results"][1]["net_pnl"] for d in days)
    total_sim2 = sum(d["results"][2]["net_pnl"] for d in days)
    lines.append(f"| **TOTAL** | | **${total_actual:+.0f}** | **${total_sim0:+.0f}** "
                  f"| **${total_sim1:+.0f}** | **${total_sim2:+.0f}** "
                  f"| **${total_sim0-total_actual:+.0f}** | |")

    lines.append("")

    # Per-day detail
    for day in days:
        lines.append(f"---")
        lines.append("")
        lines.append(f"## {day['date']} — {day['day_type']}")
        lines.append(f"Bars: {day['n_bars']} | Signals fired: {day['n_signals_total']} "
                      f"({day['n_signals_deduped']} unique)")
        lines.append("")

        lines.append("### What actually happened")
        lines.append(format_actual(day["actual_trades"]))
        lines.append("")

        for slip in SLIPPAGE_LEVELS:
            lines.append(f"### Simulation ({slip}-tick slippage)")
            lines.append(format_simulated(day, slip))
            lines.append("")

        # Gap analysis
        actual_pnl = sum((t["pnl_usd"] or 0) for t in day["actual_trades"])
        sim0 = day["results"][0]["net_pnl"]
        gap = sim0 - actual_pnl
        lines.append("### Gap analysis")
        lines.append(f"Actual: ${actual_pnl:+.0f} | Sim (0-slip): ${sim0:+.0f} | "
                      f"Gap: ${gap:+.0f}")

        # Check which sim trades differ from actual
        actual_ids = {t["id"] for t in day["actual_trades"]}
        sim_ids = {t["signal_id"] for t in day["results"][0]["trades"]}
        only_actual = actual_ids - sim_ids
        only_sim = sim_ids - actual_ids
        if only_actual:
            lines.append(f"- Trades in actual but not sim: {only_actual}")
        if only_sim:
            lines.append(f"- Trades in sim but not actual: {only_sim}")

        # Check if surviving at 0 but not at 2
        if day["results"][0]["net_pnl"] > 0 and day["results"][2]["net_pnl"] <= 0:
            lines.append(f"- **WARNING:** positive at 0-slip but negative at 2-tick — "
                          f"result does not survive slippage")
        lines.append("")

    # Honesty section
    lines.append("---")
    lines.append("")
    lines.append("## Honesty notes")
    lines.append("")
    for day in days:
        n = day["results"][0]["n_trades"]
        lines.append(f"- {day['date']}: n={n} trades"
                      + (" — **small sample, evidence is thin**" if n < 10 else ""))
    lines.append(f"- Total sample across 4 days: n="
                  f"{sum(d['results'][0]['n_trades'] for d in days)}")
    lines.append("- Gateway gate re-evaluation NOT done — signal acceptance may differ")
    lines.append("- Target/stop levels from original signals, not recomputed")
    lines.append("")

    return "\n".join(lines)


def main():
    print("Connecting to DB...")
    conn = connect()
    print("Connected.\n")

    days = []
    for date_str in REPLAY_DATES:
        print(f"Replaying {date_str}...")
        day = replay_day(conn, date_str)
        days.append(day)
        r0 = day["results"][0]
        actual_pnl = sum((t["pnl_usd"] or 0) for t in day["actual_trades"])
        print(f"  {day['day_type']} | {day['n_signals_deduped']} signals | "
              f"sim: {r0['n_trades']} trades, ${r0['net_pnl']:+.0f} | "
              f"actual: ${actual_pnl:+.0f}")

    report = generate_report(days)
    out_path = os.path.join(os.path.dirname(__file__), "..",
                            "docs", "reports", "WEEK_REPLAY_2026-08-17.md")
    out_path = os.path.normpath(out_path)
    with open(out_path, "w") as f:
        f.write(report)
    print(f"\nReport written to {out_path}")

    conn.close()


if __name__ == "__main__":
    main()
