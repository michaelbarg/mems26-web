#!/usr/bin/env python3
"""Replay opening windows + drive location filter on historical sessions.

For each session: classify opening type from bars, evaluate the window
phase at each trade's entry time, and check if the drive location filter
would have modified conviction. Measures how many trades entered during
DEVELOPING vs CONFIRMED windows, and whether EXHAUSTION_RISK would have
filtered any losing trades.

Usage:
  DATABASE_URL=postgresql://localhost/mems26 python3 scripts/replay_opening_windows.py
"""

import os
import sys
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from scripts.flag_guard import parse_env
    for k, v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(k, v)
except Exception:
    pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2026-07-01")
    parser.add_argument("--until", default="2026-08-05")
    args = parser.parse_args()

    from backend.v9.db.read import read_all
    from backend.v9.systems.opening_windows import evaluate_window, evaluate_drive_location
    from backend.v9.systems.day_type.opening_detector_v2 import detect_opening_type as classify_opening
    from zoneinfo import ZoneInfo

    ET = ZoneInfo("America/New_York")

    print(f"Opening Windows Replay: {args.since} → {args.until}")

    # Get all session bars
    all_bars = read_all("""
        SELECT ts, open, high, low, close, volume
        FROM v9_bars_5min_woodies
        WHERE ts >= :since AND ts < :until_next
        ORDER BY ts
    """, {
        "since": f"{args.since}T00:00:00+00:00",
        "until_next": f"{args.until}T23:59:59+00:00",
    })

    # Get all trades
    trades = read_all("""
        SELECT id, mode, direction, entry_price, stop, t1,
               pnl_usd, outcome, entry_ts, exit_reason
        FROM v9_trades
        WHERE entry_ts >= :since AND entry_ts < :until_next
        AND state = 'CLOSED'
        ORDER BY entry_ts
    """, {
        "since": f"{args.since}T00:00:00+00:00",
        "until_next": f"{args.until}T23:59:59+00:00",
    })

    # Get balance7 data per day
    balance7_data = read_all("""
        SELECT DISTINCT ON ((ts AT TIME ZONE 'America/New_York')::date)
               ts, poc, vah, val
        FROM v9_tpo_history
        WHERE ts >= :since
        ORDER BY (ts AT TIME ZONE 'America/New_York')::date DESC, ts DESC
    """, {"since": f"{args.since}T00:00:00+00:00"})

    print(f"Total bars: {len(all_bars or [])}, trades: {len(trades or [])}")

    # Group bars by ET date, RTH only
    bars_by_date = defaultdict(list)
    for b in (all_bars or []):
        try:
            ts = b["ts"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            et_dt = ts.astimezone(ET)
            et_time = et_dt.time()
            if et_time.hour >= 9 and (et_time.hour > 9 or et_time.minute >= 30):
                bars_by_date[et_dt.date()].append(b)
        except Exception:
            pass

    # Group trades by ET date
    trades_by_date = defaultdict(list)
    for t in (trades or []):
        try:
            ts = t["entry_ts"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            et_date = ts.astimezone(ET).date()
            trades_by_date[et_date].append(t)
        except Exception:
            pass

    # Process each session
    sessions = sorted(bars_by_date.keys())
    total_developing = 0
    total_confirmed = 0
    developing_win = 0
    developing_loss = 0
    confirmed_win = 0
    confirmed_loss = 0
    exhaustion_saved = 0.0
    value_driven_extra = 0.0
    session_results = []

    for d in sessions:
        rth_bars = bars_by_date[d]
        if len(rth_bars) < 3:
            continue

        # Classify opening from first bars
        try:
            bar_dicts = [{"o": float(b["open"]), "h": float(b["high"]),
                          "l": float(b["low"]), "c": float(b["close"]),
                          "v": int(b.get("volume", 0))} for b in rth_bars[:6]]
            open_price = float(rth_bars[0]["open"])

            # Use prior day levels if available (simplified — use range from bars)
            prior_bars = bars_by_date.get(d - timedelta(days=1), [])
            pdh = max(float(b["high"]) for b in prior_bars) if prior_bars else None
            pdl = min(float(b["low"]) for b in prior_bars) if prior_bars else None

            opening_result = classify_opening(
                bar_dicts,
                open_price=open_price,
                pdh=pdh,
                pdl=pdl,
            )
            opening_type = opening_result.get("opening_type", "UNKNOWN")
        except Exception:
            opening_type = "UNKNOWN"

        # Simple balance7 approximation (use prior 7 days' range)
        b7 = None
        prior_7d_bars = []
        for dd in range(1, 8):
            prior_7d_bars.extend(bars_by_date.get(d - timedelta(days=dd), []))
        if prior_7d_bars:
            b7_highs = [float(b["high"]) for b in prior_7d_bars]
            b7_lows = [float(b["low"]) for b in prior_7d_bars]
            b7_range_h = max(b7_highs)
            b7_range_l = min(b7_lows)
            # Approximate value area as middle 70%
            b7_width = b7_range_h - b7_range_l
            b7_val = b7_range_l + 0.15 * b7_width
            b7_vah = b7_range_h - 0.15 * b7_width
            b7 = {"range": [b7_range_l, b7_range_h], "value": [b7_val, b7_vah]}

        day_trades = trades_by_date.get(d, [])
        session_info = {
            "date": d.isoformat(), "opening_type": opening_type,
            "n_bars": len(rth_bars), "n_trades": len(day_trades),
            "developing": 0, "confirmed": 0,
            "dev_win": 0, "dev_loss": 0, "conf_win": 0, "conf_loss": 0,
            "exhaustion_trades": 0, "value_driven_trades": 0,
        }

        for t in day_trades:
            entry_ts = t["entry_ts"]
            if isinstance(entry_ts, str):
                entry_ts = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))

            # Count bars since open at entry time
            bars_before = sum(1 for b in rth_bars
                              if (b["ts"] if not isinstance(b["ts"], str) else
                                  datetime.fromisoformat(b["ts"].replace("Z", "+00:00")))
                              <= entry_ts)

            ws = evaluate_window(
                opening_type=opening_type,
                bars_since_open=bars_before,
            )

            is_win = t["outcome"] == "WIN"
            is_loss = t["outcome"] == "LOSS"
            pnl = float(t["pnl_usd"] or 0)

            if ws.phase == "DEVELOPING":
                total_developing += 1
                session_info["developing"] += 1
                if is_win:
                    developing_win += 1
                    session_info["dev_win"] += 1
                elif is_loss:
                    developing_loss += 1
                    session_info["dev_loss"] += 1
            elif ws.phase == "CONFIRMED":
                total_confirmed += 1
                session_info["confirmed"] += 1
                if is_win:
                    confirmed_win += 1
                    session_info["conf_win"] += 1
                elif is_loss:
                    confirmed_loss += 1
                    session_info["conf_loss"] += 1

            # Drive location check
            if b7 and t.get("entry_price"):
                drive_loc = evaluate_drive_location(
                    opening_type=opening_type,
                    open_price=open_price,
                    current_price=float(t["entry_price"]),
                    balance7=b7,
                )
                if drive_loc == "EXHAUSTION_RISK" and is_loss:
                    exhaustion_saved += abs(pnl)
                    session_info["exhaustion_trades"] += 1
                elif drive_loc == "VALUE_DRIVEN" and is_win:
                    value_driven_extra += pnl
                    session_info["value_driven_trades"] += 1

        session_results.append(session_info)

    # Summary
    print(f"\n{'='*100}")
    print("OPENING WINDOWS REPLAY")
    print(f"{'='*100}")
    print(f"Sessions: {len(session_results)} | Trades: {total_developing + total_confirmed}")
    print(f"\n--- Window Phase at Entry ---")
    print(f"  DEVELOPING: {total_developing} ({developing_win}W / {developing_loss}L)")
    dev_wr = developing_win / max(developing_win + developing_loss, 1) * 100
    print(f"    Win rate: {dev_wr:.0f}%")
    print(f"  CONFIRMED:  {total_confirmed} ({confirmed_win}W / {confirmed_loss}L)")
    conf_wr = confirmed_win / max(confirmed_win + confirmed_loss, 1) * 100
    print(f"    Win rate: {conf_wr:.0f}%")
    delta_wr = conf_wr - dev_wr
    print(f"  Delta WR (CONFIRMED - DEVELOPING): {delta_wr:+.0f}pp")

    print(f"\n--- Drive Location Filter ---")
    print(f"  EXHAUSTION_RISK losses that would be filtered: ${exhaustion_saved:+.2f} saved")
    print(f"  VALUE_DRIVEN winners confirmed: ${value_driven_extra:+.2f}")

    go = delta_wr > 0 or exhaustion_saved > 0
    print(f"\nVERDICT: {'GO' if go else 'NO-GO'} (CONFIRMED WR > DEVELOPING: {delta_wr:+.0f}pp)")

    # Print per-session table
    print(f"\n{'Date':<12} {'Opening':<25} {'Bars':>4} {'Trades':>6} {'Dev':>4} {'Conf':>4} "
          f"{'DW':>3} {'DL':>3} {'CW':>3} {'CL':>3}")
    print("-" * 90)
    for s in session_results:
        if s["n_trades"] > 0:
            print(f"{s['date']:<12} {s['opening_type']:<25} {s['n_bars']:>4} {s['n_trades']:>6} "
                  f"{s['developing']:>4} {s['confirmed']:>4} "
                  f"{s['dev_win']:>3} {s['dev_loss']:>3} {s['conf_win']:>3} {s['conf_loss']:>3}")

    # Write report
    out = ROOT / "docs/reports/OPENING_WINDOWS_REPLAY.md"
    with open(out, "w") as f:
        f.write("# Opening Windows Replay (Dalton Step 2)\n\n")
        f.write(f"Period: {args.since} → {args.until}\n")
        f.write(f"Sessions: {len(session_results)} | Trades: {total_developing + total_confirmed}\n\n")
        f.write("## Window Phase at Entry\n\n")
        f.write(f"| Phase | Trades | Wins | Losses | Win Rate |\n|---|---|---|---|---|\n")
        f.write(f"| DEVELOPING | {total_developing} | {developing_win} | {developing_loss} | {dev_wr:.0f}% |\n")
        f.write(f"| CONFIRMED | {total_confirmed} | {confirmed_win} | {confirmed_loss} | {conf_wr:.0f}% |\n")
        f.write(f"| **Delta** | | | | **{delta_wr:+.0f}pp** |\n\n")
        f.write("## Drive Location Filter\n\n")
        f.write(f"- EXHAUSTION_RISK losses filtered: ${exhaustion_saved:+.2f}\n")
        f.write(f"- VALUE_DRIVEN winners confirmed: ${value_driven_extra:+.2f}\n\n")
        f.write(f"**VERDICT: {'GO' if go else 'NO-GO'}**\n\n")
        f.write("## Per-Session\n\n")
        f.write("| Date | Opening | Trades | Dev | Conf | DW | DL | CW | CL |\n|---|---|---|---|---|---|---|---|---|\n")
        for s in session_results:
            if s["n_trades"] > 0:
                f.write(f"| {s['date']} | {s['opening_type']} | {s['n_trades']} | "
                        f"{s['developing']} | {s['confirmed']} | "
                        f"{s['dev_win']} | {s['dev_loss']} | {s['conf_win']} | {s['conf_loss']} |\n")
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
