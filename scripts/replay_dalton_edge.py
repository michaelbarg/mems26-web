#!/usr/bin/env python3
"""Read-only DALTON_EDGE replay over v9_bars_5min_woodies (T-118).

Walks the continuous 5-min feed (globex + RTH — the same window shape the
live wiring queries) and lists every raw detect_dalton_edge() detection with
MFE/MAE over the following 12 bars, plus a first-touch T1(1R)-vs-stop call.
Also marks which detections the live one-per-side-per-IL-day rule would keep,
and tags each with its session (live wiring only evaluates during RTH modes,
~16:30→23:00 IL — globex rows are analysis-only).

Read-only: SELECTs via backend.v9.db.read. No writes, no routing, no env
flags consulted (thresholds come from CLI args, defaults = the code defaults).

Opening-bars guard (mirrors live DALTON_EDGE_SKIP_OPEN_BARS): candidates in
the first K RTH slots after the 9:30-ET cash open are skipped BEFORE
detection (default 3 like the wiring; --skip-open-bars 0 reproduces the
unguarded replay). Same anchor + formula as _maybe_dalton_edge — the
candidate bar's own ts, not a session counter — so replay == live.

Usage:
  python3 scripts/replay_dalton_edge.py --start 2026-08-25 --end 2026-08-28 \
      [--vol-mult 2.0] [--lookback 12] [--stop-buffer 2.0] [--skip-open-bars 3]
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.v9.db.read import read_all  # noqa: E402
from backend.v9.systems.dalton_edge import (  # noqa: E402
    VOL_SMA_WINDOW, detect_dalton_edge)

IL = ZoneInfo("Asia/Jerusalem")
ET = ZoneInfo("America/New_York")   # opening-bars guard anchor (9:30 cash open)
FWD_BARS = 12


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="first IL date YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="last IL date YYYY-MM-DD")
    ap.add_argument("--vol-mult", type=float, default=2.0)
    ap.add_argument("--lookback", type=int, default=12)
    ap.add_argument("--stop-buffer", type=float, default=2.0)
    ap.add_argument("--skip-open-bars", type=int, default=3,
                    help="skip candidates in the first K RTH slots after the "
                         "9:30-ET open (live DALTON_EDGE_SKIP_OPEN_BARS "
                         "default; 0 = guard off)")
    args = ap.parse_args()

    d0 = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=IL)
    d1 = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=IL) + timedelta(days=1)
    warmup = d0 - timedelta(hours=4)  # history for SMA20/lookback before day 1

    rows = read_all(
        "SELECT extract(epoch from ts) ets, open o, high h, low l, close c, "
        "volume v FROM v9_bars_5min_woodies WHERE ts >= :t0 AND ts < :t1 "
        "ORDER BY ts",
        {"t0": warmup.astimezone(timezone.utc), "t1": d1.astimezone(timezone.utc)})
    rows = list(rows or [])
    print("bars loaded: %d (%s → %s IL, incl. 4h warmup)" % (
        len(rows), args.start, args.end))
    if not rows:
        return 1

    cfg = {"lookback_n": args.lookback, "vol_mult": args.vol_mult,
           "stop_buffer_pts": args.stop_buffer}
    need = max(args.lookback, VOL_SMA_WINDOW + 1)
    per_day = {}
    kept = set()  # (il_date, side) — live dedup simulation
    hits = []

    for i in range(need - 1, len(rows)):
        dt_il = datetime.fromtimestamp(float(rows[i]["ets"]), tz=timezone.utc).astimezone(IL)
        day = dt_il.date().isoformat()
        if day < args.start or day > args.end:
            continue
        # opening-bars guard — SAME formula as _maybe_dalton_edge (candidate
        # bar's own ts vs the 9:30-ET open), applied BEFORE detection so the
        # dedup simulation matches live exactly.
        if args.skip_open_bars > 0:
            dt_et = datetime.fromtimestamp(
                float(rows[i]["ets"]), tz=timezone.utc).astimezone(ET)
            open_min = (dt_et.hour * 60 + dt_et.minute) - (9 * 60 + 30)
            if 0 <= open_min < 5 * args.skip_open_bars:
                continue
        trig = detect_dalton_edge(rows[max(0, i - 39):i + 1], cfg)
        if not trig:
            continue
        per_day[day] = per_day.get(day, 0) + 1
        live_key = (day, trig["type"])
        is_live_kept = live_key not in kept
        if is_live_kept:
            kept.add(live_key)
        sess = "RTH " if (dt_il.hour, dt_il.minute) >= (16, 30) and dt_il.hour < 23 else "glbx"
        entry, stop = trig["entry"], trig["stop"]
        risk = abs(entry - stop)
        sign = 1.0 if trig["direction"] == "LONG" else -1.0
        t1 = round(entry + sign * risk, 2)
        fwd = rows[i + 1:i + 1 + FWD_BARS]
        if fwd:
            if sign > 0:
                mfe = max(float(b["h"]) for b in fwd) - entry
                mae = entry - min(float(b["l"]) for b in fwd)
            else:
                mfe = entry - min(float(b["l"]) for b in fwd)
                mae = max(float(b["h"]) for b in fwd) - entry
            t1_bar = stop_bar = None
            for j, b in enumerate(fwd):
                bh, bl = float(b["h"]), float(b["l"])
                if t1_bar is None and ((sign > 0 and bh >= t1) or (sign < 0 and bl <= t1)):
                    t1_bar = j
                if stop_bar is None and ((sign > 0 and bl <= stop) or (sign < 0 and bh >= stop)):
                    stop_bar = j
            if t1_bar is None and stop_bar is None:
                outcome = "open"
            elif stop_bar is None or (t1_bar is not None and t1_bar < stop_bar):
                outcome = "T1@+%d" % t1_bar
            elif t1_bar is None or stop_bar < t1_bar:
                outcome = "STOP@+%d" % stop_bar
            else:
                outcome = "AMBIG@+%d" % t1_bar
            fwd_note = "" if len(fwd) == FWD_BARS else " (only %d fwd bars)" % len(fwd)
        else:
            mfe = mae = float("nan")
            outcome, fwd_note = "no-fwd", ""
        hits.append((dt_il, trig, sess, is_live_kept))
        print("%s %s IL %s %-17s entry=%.2f stop=%.2f T1=%.2f  vol=%-5d x%.2f  "
              "MFE=%+.2f MAE=%-6.2f %s%s%s" % (
                  day, dt_il.strftime("%H:%M"), sess, trig["type"], entry, stop,
                  t1, int(trig["volume"]), trig["vol_ratio"], mfe, mae, outcome,
                  fwd_note, "" if is_live_kept else "  [dedup'd live]"))

    print("\nper-day raw detections (vol_mult=%.2f, lookback=%d, "
          "skip_open_bars=%d):" % (args.vol_mult, args.lookback,
                                   args.skip_open_bars))
    for day in sorted(per_day):
        print("  %s: %d" % (day, per_day[day]))
    if not per_day:
        print("  none")
    n_rth = sum(1 for h in hits if h[2].strip() == "RTH")
    print("total=%d (glbx=%d, RTH=%d), live-kept=%d" % (
        len(hits), len(hits) - n_rth, n_rth,
        sum(1 for h in hits if h[3])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
