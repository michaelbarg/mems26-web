#!/usr/bin/env python3
"""K5 — EXCESS_COUNTER_ENTRY_V1 replay on historical bars (2026-08-09).

For each trading day (07-15 through 08-07), identifies bars where a
counter-trend REACTIVE entry during Variation EXPANSION would have been
blocked by the "fade only after rebalance" rule in daytype_playbook.py,
then tests whether the entry had EXCESS quality at the session extreme —
which would exempt it under the K5 flag.

Simulates P&L for exempted entries and counts correct blocks (non-EXCESS).

Usage:
  python3 scripts/replay_excess_counter.py [--since 2026-07-15] [--until 2026-08-07]
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Parse .env (same pattern as other replay scripts) ──
try:
    from scripts.flag_guard import parse_env
    for k, v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(k, v)
except Exception:
    pass

from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
MES_POINT_VALUE = 5.0   # $/pt/contract
EXCESS_PROXIMITY_PTS = 2.0  # entry must be within 2pt of the extreme
VARIATION_PHASE_STALL_BARS = int(os.getenv("VARIATION_PHASE_STALL_BARS", "6"))


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────

def classify_day(bars: List[Dict]) -> Dict[str, Any]:
    """Classify a full day's RTH bars using classifier_core (EOD mode)."""
    from backend.v9.systems.day_type.classifier_core import classify_session
    if len(bars) < 12:
        return {"day_type": "FORMING", "direction": None, "dir_bias": None}
    ib_bars = bars[:12]
    ib_h = max(float(b["high"]) for b in ib_bars)
    ib_l = min(float(b["low"]) for b in ib_bars)
    bar_dicts = [{"o": float(b["open"]), "h": float(b["high"]),
                  "l": float(b["low"]), "c": float(b["close"]),
                  "v": int(b.get("volume", 0))} for b in bars]
    return classify_session(
        bars=bar_dicts, ib_high=ib_h, ib_low=ib_l,
        open_price=float(bars[0]["open"]), is_eod=True,
    )


def compute_day_direction(bars: List[Dict]) -> Optional[str]:
    """Derive day direction from overall price movement (open vs last close)."""
    if not bars:
        return None
    first_open = float(bars[0]["open"])
    last_close = float(bars[-1]["close"])
    delta = last_close - first_open
    if abs(delta) < 2.0:
        return None
    return "UP" if delta > 0 else "DOWN"


def compute_variation_phase(
    bars_so_far: List[Dict],
    day_dir: str,
) -> Optional[str]:
    """Replay the gateway's variation_phase logic: EXPANSION while new
    session extremes are being made in the day direction, REBALANCED once
    no new extreme for >= STALL bars."""
    if len(bars_so_far) < 8 or day_dir not in ("UP", "DOWN"):
        return None
    run = None
    last_new = 0
    for i, b in enumerate(bars_so_far):
        val = float(b["high"]) if day_dir == "UP" else float(b["low"])
        if run is None or (val > run if day_dir == "UP" else val < run):
            run = val
            last_new = i
    bars_since = len(bars_so_far) - 1 - last_new
    return "EXPANSION" if bars_since < VARIATION_PHASE_STALL_BARS else "REBALANCED"


def simulate_trade(
    entry: float,
    stop: float,
    t1: float,
    direction: str,
    future_bars: List[Dict],
) -> Dict[str, Any]:
    """Simulate a trade to T1 or stop. Returns {pnl_pts, mae_pts, outcome, bars_held}."""
    sign = 1.0 if direction == "LONG" else -1.0
    mae = 0.0
    mfe = 0.0
    for i, b in enumerate(future_bars):
        h = float(b["high"])
        l = float(b["low"])
        # MAE (adverse excursion)
        adverse = (entry - l) if direction == "LONG" else (h - entry)
        mae = max(mae, adverse)
        # MFE (favorable excursion)
        favorable = (h - entry) if direction == "LONG" else (entry - l)
        mfe = max(mfe, favorable)
        # Stop check (stop hit before T1 within the bar — worst case)
        if direction == "LONG" and l <= stop:
            return {"pnl_pts": stop - entry, "mae_pts": mae, "mfe_pts": mfe,
                    "outcome": "STOP", "bars_held": i + 1}
        if direction == "SHORT" and h >= stop:
            return {"pnl_pts": entry - stop, "mae_pts": mae, "mfe_pts": mfe,
                    "outcome": "STOP", "bars_held": i + 1}
        # T1 check
        if direction == "LONG" and h >= t1:
            return {"pnl_pts": t1 - entry, "mae_pts": mae, "mfe_pts": mfe,
                    "outcome": "T1", "bars_held": i + 1}
        if direction == "SHORT" and l <= t1:
            return {"pnl_pts": entry - t1, "mae_pts": mae, "mfe_pts": mfe,
                    "outcome": "T1", "bars_held": i + 1}
    # Session ended without hitting stop or T1 — mark-to-market at last close
    last_c = float(future_bars[-1]["close"]) if future_bars else entry
    pnl = (last_c - entry) * sign
    return {"pnl_pts": pnl, "mae_pts": mae, "mfe_pts": mfe,
            "outcome": "MTM", "bars_held": len(future_bars)}


# ────────────────────────────────────────────────────────────────────────
# Main replay
# ────────────────────────────────────────────────────────────────────────

def replay_day(
    day_bars: List[Dict],
    day_str: str,
) -> Tuple[List[Dict], List[Dict]]:
    """Walk through a day's bars, identify counter-trend blocks during
    Variation EXPANSION, and classify each as EXCESS-exempt or correct-block.

    Returns (excess_entries, correct_blocks).
    """
    from backend.v9.systems.extremes_quality import classify_session_extremes

    excess_entries: List[Dict] = []
    correct_blocks: List[Dict] = []

    if len(day_bars) < 14:
        return excess_entries, correct_blocks

    # Classify the day (EOD) to get the canonical day type
    cls = classify_day(day_bars)
    day_type = cls.get("day_type", "UNKNOWN")

    # Only Variation days are relevant for this rule
    if day_type not in ("Variation", "Normal_Variation"):
        return excess_entries, correct_blocks

    # Day direction from classifier or price action
    day_dir = cls.get("dir_bias") or cls.get("direction")
    if day_dir and isinstance(day_dir, str):
        # Extract direction from strings like "with_extension(DOWN)"
        for tag in ("UP", "DOWN"):
            if tag in day_dir.upper():
                day_dir = tag
                break
        else:
            day_dir = compute_day_direction(day_bars)
    else:
        day_dir = compute_day_direction(day_bars)

    if day_dir not in ("UP", "DOWN"):
        return excess_entries, correct_blocks

    # IB for reference
    ib_bars = day_bars[:12]
    ib_h = max(float(b["high"]) for b in ib_bars)
    ib_l = min(float(b["low"]) for b in ib_bars)
    ib_mid = (ib_h + ib_l) / 2.0

    # Walk bars starting after IB formation
    for bar_idx in range(12, len(day_bars)):
        bars_so_far = day_bars[:bar_idx + 1]
        bar = day_bars[bar_idx]
        bar_close = float(bar["close"])
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])

        # Check variation phase
        vphase = compute_variation_phase(bars_so_far, day_dir)
        if vphase != "EXPANSION":
            continue

        # During EXPANSION on an UP day: counter-trend = SHORT
        # During EXPANSION on a DOWN day: counter-trend = LONG
        if day_dir == "UP":
            counter_dir = "SHORT"
            # A counter-trend SHORT entry at the bar's close
            entry_price = bar_close
            session_high = max(float(b["high"]) for b in bars_so_far)
            # Only consider entries near the session extreme (within 5pt)
            if abs(entry_price - session_high) > 5.0:
                continue
        else:
            counter_dir = "LONG"
            entry_price = bar_close
            session_low = min(float(b["low"]) for b in bars_so_far)
            if abs(entry_price - session_low) > 5.0:
                continue

        # Classify extremes at this point in the session
        bar_dicts = [{"high": float(b["high"]), "low": float(b["low"]),
                      "open": float(b["open"]), "close": float(b["close"])}
                     for b in bars_so_far]
        extremes = classify_session_extremes(bar_dicts)
        if extremes is None:
            continue

        # Check the relevant edge
        if counter_dir == "SHORT":
            edge = extremes.high
            extreme_level = extremes.session_high
        else:
            edge = extremes.low
            extreme_level = extremes.session_low

        proximity = abs(entry_price - extreme_level)

        # Build the record
        record = {
            "date": day_str,
            "bar_idx": bar_idx,
            "bar_time": str(bar.get("ts", f"bar_{bar_idx}")),
            "day_type": day_type,
            "day_dir": day_dir,
            "vphase": vphase,
            "counter_dir": counter_dir,
            "entry_price": round(entry_price, 2),
            "extreme_level": round(extreme_level, 2),
            "proximity_pts": round(proximity, 2),
            "edge_quality": edge.quality,
            "edge_tail_pts": edge.tail_pts,
            "edge_detail": edge.detail,
        }

        is_excess = (edge.quality == "EXCESS" and proximity <= EXCESS_PROXIMITY_PTS)

        if is_excess:
            # This entry would be EXEMPTED by K5 — simulate the trade
            if counter_dir == "SHORT":
                # Stop above the excess tail
                stop = extreme_level + 1.0
                # T1 at IB-mid or 8pt away, whichever is closer
                t1_ib = ib_mid
                t1_fixed = entry_price - 8.0
                t1 = max(t1_ib, t1_fixed) if t1_ib < entry_price else t1_fixed
            else:
                stop = extreme_level - 1.0
                t1_ib = ib_mid
                t1_fixed = entry_price + 8.0
                t1 = min(t1_ib, t1_fixed) if t1_ib > entry_price else t1_fixed

            future_bars = day_bars[bar_idx + 1:]
            if future_bars:
                sim = simulate_trade(entry_price, stop, t1, counter_dir, future_bars)
            else:
                sim = {"pnl_pts": 0, "mae_pts": 0, "mfe_pts": 0,
                       "outcome": "NO_BARS", "bars_held": 0}

            record.update({
                "stop": round(stop, 2),
                "t1": round(t1, 2),
                "pnl_pts": round(sim["pnl_pts"], 2),
                "pnl_usd": round(sim["pnl_pts"] * MES_POINT_VALUE, 2),
                "mae_pts": round(sim["mae_pts"], 2),
                "mfe_pts": round(sim["mfe_pts"], 2),
                "outcome": sim["outcome"],
                "bars_held": sim["bars_held"],
            })
            excess_entries.append(record)
        else:
            # Correct block: non-EXCESS or too far from extreme
            record["block_reason"] = (
                f"quality={edge.quality}, proximity={proximity:.1f}pt"
                if edge.quality != "EXCESS"
                else f"EXCESS but too far ({proximity:.1f}pt > {EXCESS_PROXIMITY_PTS}pt)"
            )
            correct_blocks.append(record)

    return excess_entries, correct_blocks


def main():
    parser = argparse.ArgumentParser(
        description="K5 EXCESS_COUNTER_ENTRY_V1 replay")
    parser.add_argument("--since", default="2026-07-15",
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--until", default="2026-08-07",
                        help="End date inclusive (YYYY-MM-DD)")
    parser.add_argument("--report", default=None,
                        help="Override output report path")
    args = parser.parse_args()

    from backend.v9.db.read import read_all

    print(f"=== K5 EXCESS_COUNTER_ENTRY_V1 Replay ===")
    print(f"Period: {args.since} -> {args.until}")
    print()

    # ── Fetch all RTH bars for the period ──
    all_bars = read_all(
        "SELECT ts, open, high, low, close, volume "
        "FROM v9_bars_5min_woodies "
        "WHERE ts >= :since AND ts < :until_next "
        "ORDER BY ts",
        {
            "since": f"{args.since}T00:00:00+00:00",
            "until_next": f"{args.until}T23:59:59+00:00",
        },
    )

    if not all_bars:
        print("ERROR: No bars found in v9_bars_5min_woodies for this period.")
        return

    print(f"Total bars fetched: {len(all_bars)}")

    # ── Group bars by ET trading date (RTH 09:30-16:00) ──
    bars_by_date: Dict[str, List[Dict]] = defaultdict(list)
    for b in all_bars:
        ts = b["ts"]
        if hasattr(ts, "astimezone"):
            et_dt = ts.astimezone(ET)
        elif hasattr(ts, "replace"):
            from datetime import timezone as _tz
            et_dt = ts.replace(tzinfo=_tz.utc).astimezone(ET)
        else:
            continue
        et_time = et_dt.time()
        # RTH window: 09:30 - 16:00 ET
        from datetime import time as _time
        if _time(9, 30) <= et_time < _time(16, 15):
            day_key = et_dt.strftime("%Y-%m-%d")
            bars_by_date[day_key].append(b)

    trading_days = sorted(bars_by_date.keys())
    print(f"Trading days: {len(trading_days)}")
    print()

    # ── Replay each day ──
    all_excess_entries: List[Dict] = []
    all_correct_blocks: List[Dict] = []
    day_summaries: List[Dict] = []

    for day_str in trading_days:
        day_bars = bars_by_date[day_str]
        excess_entries, correct_blocks = replay_day(day_bars, day_str)

        cls = classify_day(day_bars)
        day_type = cls.get("day_type", "UNKNOWN")
        day_dir = compute_day_direction(day_bars)

        if excess_entries or correct_blocks:
            day_pnl = sum(e.get("pnl_pts", 0) for e in excess_entries)
            day_summaries.append({
                "date": day_str,
                "day_type": day_type,
                "day_dir": day_dir,
                "n_bars": len(day_bars),
                "excess_entries": len(excess_entries),
                "correct_blocks": len(correct_blocks),
                "net_pnl_pts": round(day_pnl, 2),
                "net_pnl_usd": round(day_pnl * MES_POINT_VALUE, 2),
            })

        all_excess_entries.extend(excess_entries)
        all_correct_blocks.extend(correct_blocks)

    # ── Print summary ──
    _print_summary(trading_days, day_summaries, all_excess_entries,
                   all_correct_blocks)

    # ── Write report ──
    report_path = args.report or str(
        ROOT / "docs" / "reports" / "EXCESS_COUNTER_REPLAY_2026-08-09.md")
    _write_report(report_path, args, trading_days, day_summaries,
                  all_excess_entries, all_correct_blocks)


def _print_summary(
    trading_days: List[str],
    day_summaries: List[Dict],
    excess_entries: List[Dict],
    correct_blocks: List[Dict],
):
    """Print the replay summary to stdout."""
    print("=" * 72)
    print("SUMMARY: K5 EXCESS_COUNTER_ENTRY_V1 Replay")
    print("=" * 72)
    print()

    print(f"Trading days scanned:        {len(trading_days)}")
    print(f"Variation days with events:  {len(day_summaries)}")
    print()

    # Per-day table
    if day_summaries:
        print(f"{'Date':<12} {'DayType':<20} {'Dir':<5} "
              f"{'Excess':>7} {'Blocked':>8} {'NetPnL':>8} {'NetUSD':>8}")
        print("-" * 72)
        for ds in day_summaries:
            print(f"{ds['date']:<12} {ds['day_type']:<20} "
                  f"{ds['day_dir'] or '?':<5} "
                  f"{ds['excess_entries']:>7} {ds['correct_blocks']:>8} "
                  f"{ds['net_pnl_pts']:>+8.2f} {ds['net_pnl_usd']:>+8.0f}")
        print("-" * 72)

    total_excess = len(excess_entries)
    total_blocked = len(correct_blocks)
    total_pnl_pts = sum(e.get("pnl_pts", 0) for e in excess_entries)
    total_pnl_usd = total_pnl_pts * MES_POINT_VALUE

    print()
    print(f"EXCESS entries (K5 would ADD):    {total_excess}")
    print(f"Correct blocks (K5 keeps out):   {total_blocked}")
    print(f"NET P&L from added entries:      {total_pnl_pts:+.2f} pts "
          f"(${total_pnl_usd:+.0f})")
    print()

    # Outcome breakdown for excess entries
    if excess_entries:
        outcomes = defaultdict(int)
        for e in excess_entries:
            outcomes[e.get("outcome", "?")] += 1
        print("Outcome breakdown (EXCESS entries):")
        for outcome, count in sorted(outcomes.items()):
            pnl = sum(e["pnl_pts"] for e in excess_entries
                      if e.get("outcome") == outcome)
            print(f"  {outcome:<8}: {count:>3} entries, "
                  f"{pnl:+.2f} pts (${pnl * MES_POINT_VALUE:+.0f})")
        print()

        # Detail each excess entry
        print("EXCESS entry details:")
        print(f"  {'Date':<12} {'Bar#':>4} {'Dir':<6} {'Entry':>8} "
              f"{'Extreme':>8} {'Prox':>5} {'Tail':>5} "
              f"{'Stop':>8} {'T1':>8} {'PnL':>7} {'Out':<5}")
        print("  " + "-" * 90)
        for e in excess_entries:
            print(f"  {e['date']:<12} {e['bar_idx']:>4} {e['counter_dir']:<6} "
                  f"{e['entry_price']:>8.2f} {e['extreme_level']:>8.2f} "
                  f"{e['proximity_pts']:>5.1f} {e['edge_tail_pts']:>5.1f} "
                  f"{e['stop']:>8.2f} {e['t1']:>8.2f} "
                  f"{e['pnl_pts']:>+7.2f} {e['outcome']:<5}")
        print()

    # Sample of correct blocks
    if correct_blocks:
        print(f"Correct block samples (first 10 of {total_blocked}):")
        print(f"  {'Date':<12} {'Bar#':>4} {'Dir':<6} {'Entry':>8} "
              f"{'Quality':<8} {'Reason'}")
        print("  " + "-" * 80)
        for cb in correct_blocks[:10]:
            print(f"  {cb['date']:<12} {cb['bar_idx']:>4} "
                  f"{cb['counter_dir']:<6} {cb['entry_price']:>8.2f} "
                  f"{cb['edge_quality']:<8} {cb.get('block_reason', '')}")
        print()


def _write_report(
    path: str,
    args,
    trading_days: List[str],
    day_summaries: List[Dict],
    excess_entries: List[Dict],
    correct_blocks: List[Dict],
):
    """Write the Markdown report."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    total_excess = len(excess_entries)
    total_blocked = len(correct_blocks)
    total_pnl_pts = sum(e.get("pnl_pts", 0) for e in excess_entries)
    total_pnl_usd = total_pnl_pts * MES_POINT_VALUE

    lines = [
        "# K5 EXCESS_COUNTER_ENTRY_V1 Replay Report",
        f"**Generated:** 2026-08-09  ",
        f"**Period:** {args.since} to {args.until}  ",
        f"**Trading days scanned:** {len(trading_days)}  ",
        f"**Variation days with events:** {len(day_summaries)}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| EXCESS entries (K5 would ADD) | {total_excess} |",
        f"| Correct blocks (K5 keeps out) | {total_blocked} |",
        f"| NET P&L from added entries | {total_pnl_pts:+.2f} pts (${total_pnl_usd:+.0f}) |",
        "",
    ]

    # Outcome breakdown
    if excess_entries:
        outcomes = defaultdict(lambda: {"count": 0, "pnl": 0.0})
        for e in excess_entries:
            o = e.get("outcome", "?")
            outcomes[o]["count"] += 1
            outcomes[o]["pnl"] += e.get("pnl_pts", 0)
        lines.append("## Outcome Breakdown (EXCESS Entries)")
        lines.append("")
        lines.append("| Outcome | Count | P&L (pts) | P&L (USD) |")
        lines.append("|---------|-------|-----------|-----------|")
        for outcome in sorted(outcomes):
            d = outcomes[outcome]
            lines.append(
                f"| {outcome} | {d['count']} | "
                f"{d['pnl']:+.2f} | ${d['pnl'] * MES_POINT_VALUE:+.0f} |")
        lines.append("")

    # Per-day table
    if day_summaries:
        lines.append("## Per-Day Summary")
        lines.append("")
        lines.append("| Date | Day Type | Dir | Excess | Blocked | Net PnL |")
        lines.append("|------|----------|-----|--------|---------|---------|")
        for ds in day_summaries:
            lines.append(
                f"| {ds['date']} | {ds['day_type']} | {ds['day_dir'] or '?'} | "
                f"{ds['excess_entries']} | {ds['correct_blocks']} | "
                f"{ds['net_pnl_pts']:+.2f} pts |")
        lines.append("")

    # Excess entry details
    if excess_entries:
        lines.append("## EXCESS Entry Details")
        lines.append("")
        lines.append("| Date | Bar | Dir | Entry | Extreme | Prox | Tail | "
                     "Stop | T1 | PnL | Out |")
        lines.append("|------|-----|-----|-------|---------|------|------|"
                     "------|----|----|-----|")
        for e in excess_entries:
            lines.append(
                f"| {e['date']} | {e['bar_idx']} | {e['counter_dir']} | "
                f"{e['entry_price']:.2f} | {e['extreme_level']:.2f} | "
                f"{e['proximity_pts']:.1f} | {e['edge_tail_pts']:.1f} | "
                f"{e['stop']:.2f} | {e['t1']:.2f} | "
                f"{e['pnl_pts']:+.2f} | {e['outcome']} |")
        lines.append("")

    # Correct blocks sample
    if correct_blocks:
        lines.append(f"## Correct Blocks (sample, {min(20, total_blocked)} "
                     f"of {total_blocked})")
        lines.append("")
        lines.append("| Date | Bar | Dir | Entry | Quality | Reason |")
        lines.append("|------|-----|-----|-------|---------|--------|")
        for cb in correct_blocks[:20]:
            lines.append(
                f"| {cb['date']} | {cb['bar_idx']} | {cb['counter_dir']} | "
                f"{cb['entry_price']:.2f} | {cb['edge_quality']} | "
                f"{cb.get('block_reason', '')} |")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by `scripts/replay_excess_counter.py`*")
    lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    print(f"Report written to: {path}")


if __name__ == "__main__":
    main()
