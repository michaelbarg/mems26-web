#!/usr/bin/env python3
"""rebuild_bar_truth.py — Read Sierra .scid files and build 5-min truth bars.

Sierra .scid format: fixed-size records, each 40 bytes:
  - SCDateTime (8 bytes, double): Excel serial date (days since 1899-12-30)
  - Open (4 bytes, float)
  - High (4 bytes, float)
  - Low (4 bytes, float)
  - Close (4 bytes, float)
  - NumTrades (4 bytes, int)
  - TotalVolume (4 bytes, int)
  - BidVolume (4 bytes, int)
  - AskVolume (4 bytes, int)

The timestamps are in the chart's timezone (America/Chicago for MES).

Usage:
  python3 scripts/rebuild_bar_truth.py --scid ~/SierraChart/Data/MESU26_FUT_CME.scid --date 2026-07-29
  python3 scripts/rebuild_bar_truth.py --scid ~/SierraChart/Data/MESU26_FUT_CME.scid --all

Output: docs/reports/BAR_TRUTH_<date>.md or FIRE_MATRIX_ALL_DAYS.md
"""
import argparse
import os
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CT = ZoneInfo("America/Chicago")
RECORD_SIZE = 40
SC_EPOCH = datetime(1899, 12, 30, tzinfo=timezone.utc)
PRICE_SCALE = 100.0  # .scid prices are ×100 (e.g., 750325 = 7503.25)


def read_scid(filepath, start_date=None, end_date=None):
    """Read .scid file and return list of (ts_utc, o, h, l, c, vol) tuples.

    Sierra .scid format (version 1, 40 bytes/record):
      - int64: SCDateTime in microseconds since 1899-12-30 00:00 UTC
      - float32 × 4: Open, High, Low, Close (prices × 100)
      - int32 × 4: NumTrades, TotalVolume, BidVolume, AskVolume

    Open field has garbage (-1.99e38) on tick records — ignored, only H/L/C
    are reliable per-tick. Aggregation reconstructs Open from first tick.
    """
    bars = []
    with open(filepath, "rb") as f:
        # Read header
        header = f.read(56)
        if len(header) < 56:
            print(f"ERROR: file too small ({len(header)} bytes)")
            return bars

        hdr_size = struct.unpack('<I', header[4:8])[0]
        rec_size = struct.unpack('<I', header[8:12])[0]
        if rec_size != RECORD_SIZE:
            print(f"WARNING: record size {rec_size} != expected {RECORD_SIZE}")

        f.seek(hdr_size)

        while True:
            rec = f.read(rec_size)
            if len(rec) < rec_size:
                break

            ts_us = struct.unpack('<q', rec[:8])[0]
            o, h, l, c = struct.unpack('<ffff', rec[8:24])
            num_trades, total_vol, bid_vol, ask_vol = struct.unpack('<iiii', rec[24:40])

            if ts_us <= 0:
                continue

            # Convert microseconds since SC epoch to datetime
            try:
                utc_dt = SC_EPOCH + timedelta(microseconds=ts_us)
            except (OverflowError, ValueError):
                continue

            if start_date and utc_dt.date() < start_date:
                continue
            if end_date and utc_dt.date() > end_date:
                continue

            # Scale prices (÷100) and filter garbage Open values
            h_real = h / PRICE_SCALE
            l_real = l / PRICE_SCALE
            c_real = c / PRICE_SCALE
            o_real = o / PRICE_SCALE if abs(o) < 1e10 else c_real  # garbage Open → use Close

            if h_real < 1000 or h_real > 50000:
                continue  # not MES range

            bars.append((utc_dt, o_real, h_real, l_real, c_real, int(total_vol)))

    return bars


def aggregate_5min(tick_bars):
    """Aggregate tick/1-min bars into 5-min OHLCV bars."""
    buckets = {}
    for ts, o, h, l, c, vol in tick_bars:
        # 5-min bucket: floor to nearest 5 min
        bucket_min = (ts.minute // 5) * 5
        bucket_ts = ts.replace(minute=bucket_min, second=0, microsecond=0)
        key = bucket_ts

        if key not in buckets:
            buckets[key] = {"ts": bucket_ts, "o": o, "h": h, "l": l, "c": c, "vol": vol}
        else:
            b = buckets[key]
            b["h"] = max(b["h"], h)
            b["l"] = min(b["l"], l)
            b["c"] = c  # last close wins
            b["vol"] += vol

    return sorted(buckets.values(), key=lambda b: b["ts"])


def rth_bars(bars_5min, date):
    """Filter to RTH bars (09:30-16:00 ET) for a specific date."""
    ET = ZoneInfo("America/New_York")
    rth = []
    for b in bars_5min:
        et = b["ts"].astimezone(ET)
        if et.date() != date:
            continue
        et_min = et.hour * 60 + et.minute
        if 9 * 60 + 30 <= et_min < 16 * 60:
            rth.append(b)
    return rth


def integrity_check(bars_5min):
    """Check for seams (>15pt gaps between adjacent bars)."""
    seams = []
    for i in range(1, len(bars_5min)):
        prev_h, prev_l = bars_5min[i-1]["h"], bars_5min[i-1]["l"]
        cur_h, cur_l = bars_5min[i]["h"], bars_5min[i]["l"]
        gap = max(cur_l - prev_h, prev_l - cur_h)
        if gap > 15:
            seams.append((bars_5min[i-1]["ts"], bars_5min[i]["ts"], gap))
    return seams


def compare_to_db(truth_bars, date_str):
    """Compare truth bars to DB bars and report discrepancies."""
    try:
        from backend.v9.db.read import read_all
        db_rows = read_all(
            "SELECT ts, high, low, close FROM v9_bars_5min_woodies "
            "WHERE (ts AT TIME ZONE 'America/New_York')::date = :d ORDER BY ts",
            {"d": date_str},
        )
    except Exception as e:
        return {"error": str(e), "matches": 0, "mismatches": 0}

    # Build DB lookup by ts (minute-precision)
    db_by_ts = {}
    for r in db_rows:
        ts = r["ts"]
        if hasattr(ts, "strftime"):
            key = ts.strftime("%H:%M")
        else:
            key = str(ts)[11:16]
        db_by_ts[key] = r

    matches = 0
    mismatches = []
    for b in truth_bars:
        ET = ZoneInfo("America/New_York")
        key = b["ts"].astimezone(ET).strftime("%H:%M")
        db = db_by_ts.get(key)
        if db is None:
            mismatches.append(f"{key}: truth exists, DB missing")
        else:
            db_c = float(db["close"])
            truth_c = b["c"]
            if abs(db_c - truth_c) > 0.5:
                mismatches.append(f"{key}: truth={truth_c:.2f} DB={db_c:.2f} Δ={abs(db_c-truth_c):.2f}")
            else:
                matches += 1

    return {"matches": matches, "mismatches_count": len(mismatches),
            "mismatches": mismatches[:20], "db_bars": len(db_rows),
            "truth_bars": len(truth_bars)}


def main():
    parser = argparse.ArgumentParser(description="Rebuild bar truth from .scid")
    parser.add_argument("--scid", required=True, help="Path to .scid file")
    parser.add_argument("--date", help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="Process all available dates")
    parser.add_argument("--since", default="2026-07-15", help="Start date for --all")
    args = parser.parse_args()

    print(f"Reading {args.scid}...")
    scid_path = os.path.expanduser(args.scid)

    if args.date:
        from datetime import date
        d = date.fromisoformat(args.date)
        print(f"Filtering for {d}...")
        raw = read_scid(scid_path, start_date=d, end_date=d)
        bars = aggregate_5min(raw)
        rth = rth_bars(bars, d)
        seams = integrity_check(rth)

        print(f"\n{'='*60}")
        print(f"BAR TRUTH — {args.date}")
        print(f"{'='*60}")
        print(f"Raw records: {len(raw)}")
        print(f"5-min bars: {len(bars)}")
        print(f"RTH bars: {len(rth)}")
        print(f"Seams (>15pt): {len(seams)}")
        for s in seams:
            print(f"  {s[0]} → {s[1]}: {s[2]:.1f}pt")

        if rth:
            print(f"\nFirst bar: {rth[0]['ts']} O={rth[0]['o']:.2f} H={rth[0]['h']:.2f} L={rth[0]['l']:.2f} C={rth[0]['c']:.2f}")
            print(f"Last bar:  {rth[-1]['ts']} O={rth[-1]['o']:.2f} H={rth[-1]['h']:.2f} L={rth[-1]['l']:.2f} C={rth[-1]['c']:.2f}")
            print(f"Range: {max(b['h'] for b in rth):.2f} - {min(b['l'] for b in rth):.2f}")

        # Compare to DB
        cmp = compare_to_db(rth, args.date)
        print(f"\nDB comparison: {cmp.get('matches', 0)} match, {cmp.get('mismatches_count', 0)} mismatch")
        for m in cmp.get("mismatches", [])[:10]:
            print(f"  {m}")

        # Write report
        out = ROOT / f"docs/reports/BAR_TRUTH_{args.date}.md"
        with open(out, "w") as f:
            f.write(f"# Bar Truth — {args.date}\n\n")
            f.write(f"Source: {args.scid}\n")
            f.write(f"Raw records: {len(raw)} | 5-min: {len(bars)} | RTH: {len(rth)}\n")
            f.write(f"Seams: {len(seams)} | DB match: {cmp.get('matches',0)}/{cmp.get('truth_bars',0)}\n\n")
            if rth:
                f.write("## RTH Bars (first 5)\n\n")
                f.write("| Time | O | H | L | C | Vol |\n|---|---|---|---|---|---|\n")
                for b in rth[:5]:
                    f.write(f"| {b['ts'].astimezone(ZoneInfo('America/New_York')):%H:%M} | {b['o']:.2f} | {b['h']:.2f} | {b['l']:.2f} | {b['c']:.2f} | {b['vol']} |\n")
        print(f"\nReport: {out}")

    elif args.all:
        from datetime import date, timedelta as td
        start = date.fromisoformat(args.since)
        today = date.today()
        print(f"Processing all dates from {start} to {today}...")

        raw = read_scid(scid_path, start_date=start, end_date=today)
        bars = aggregate_5min(raw)
        print(f"Total: {len(raw)} raw, {len(bars)} 5-min bars")

        # Group by date
        from collections import defaultdict
        by_date = defaultdict(list)
        ET = ZoneInfo("America/New_York")
        for b in bars:
            d = b["ts"].astimezone(ET).date()
            by_date[d].append(b)

        matrix = []
        for d in sorted(by_date):
            day_bars = rth_bars(by_date[d], d)
            if len(day_bars) < 5:
                continue
            seams = integrity_check(day_bars)
            cmp = compare_to_db(day_bars, d.isoformat())
            matrix.append({
                "date": d.isoformat(),
                "rth_bars": len(day_bars),
                "seams": len(seams),
                "db_match": cmp.get("matches", 0),
                "db_mismatch": cmp.get("mismatches_count", 0),
                "judgeable": len(seams) == 0,
            })
            status = "CLEAN" if len(seams) == 0 else f"SEAM({len(seams)})"
            match_pct = round(cmp.get("matches",0) / len(day_bars) * 100) if day_bars else 0
            print(f"  {d}: {len(day_bars)} RTH bars, {status}, DB match {match_pct}%")

        # Write matrix report
        out = ROOT / "docs/reports/FIRE_MATRIX_ALL_DAYS.md"
        with open(out, "w") as f:
            f.write("# Fire Matrix — All Days Bar Truth\n\n")
            f.write(f"Source: {args.scid}\n")
            f.write(f"Period: {args.since} → {today}\n\n")
            f.write("| Date | RTH Bars | Seams | DB Match | Judgeable |\n")
            f.write("|---|---|---|---|---|\n")
            for m in matrix:
                j = "YES" if m["judgeable"] else "NO"
                f.write(f"| {m['date']} | {m['rth_bars']} | {m['seams']} | {m['db_match']}/{m['rth_bars']} | {j} |\n")
            not_j = sum(1 for m in matrix if not m["judgeable"])
            f.write(f"\n**{len(matrix)} days, {not_j} not-judgeable (seams)**\n")
        print(f"\nMatrix: {out}")


if __name__ == "__main__":
    main()
