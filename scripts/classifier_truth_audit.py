#!/usr/bin/env python3
"""D1 — Classifier truth audit: compare labels vs Dalton on .scid truth bars.

Runs classify_session on each day's truth bars and reports the label.
The Dalton truth is determined from structural features: IB extension,
value migration, VA overlap, sides, rib.

Usage:
  python3 scripts/classifier_truth_audit.py --scid ~/SierraChart/Data/MESU26_FUT_CME.scid
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from scripts.flag_guard import parse_env
    for k, v in parse_env(str(ROOT / ".env")).items():
        os.environ.setdefault(k, v)
except Exception:
    pass

from scripts.rebuild_bar_truth import read_scid, aggregate_5min, rth_bars

ET = ZoneInfo("America/New_York")


def classify_day(bars):
    """Classify a day from its RTH 5-min bars."""
    try:
        from backend.v9.systems.day_type.classifier_core import classify_session
        ib_bars = bars[:12] if len(bars) >= 12 else bars
        ib_h = max(b["h"] for b in ib_bars)
        ib_l = min(b["l"] for b in ib_bars)
        bar_dicts = [{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                      "v": b.get("vol", 0)} for b in bars]
        result = classify_session(bars=bar_dicts, ib_high=ib_h, ib_low=ib_l,
                                  open_price=bars[0]["o"], is_eod=True)
        return result
    except Exception as e:
        return {"day_type": f"ERROR({e})", "status": "ERROR"}


def dalton_features(bars):
    """Compute Dalton-relevant structural features from bars."""
    if len(bars) < 12:
        return {}
    ib_bars = bars[:12]
    ib_h = max(b["h"] for b in ib_bars)
    ib_l = min(b["l"] for b in ib_bars)
    ib_w = ib_h - ib_l

    # Session range
    day_h = max(b["h"] for b in bars)
    day_l = min(b["l"] for b in bars)
    day_range = day_h - day_l

    # IB extension
    ext_up = day_h > ib_h + 0.5
    ext_dn = day_l < ib_l - 0.5
    sides = (1 if ext_up else 0) + (1 if ext_dn else 0)

    # RIB (range / IB)
    rib = round(day_range / ib_w, 2) if ib_w > 0 else 0

    # Close position
    close = bars[-1]["c"]
    close_pos = round((close - day_l) / day_range, 2) if day_range > 0 else 0.5

    # Open price + return through open
    open_price = bars[0]["o"]
    returned = False
    above = False
    below = False
    for b in bars[1:]:
        if b["c"] > open_price + 0.5:
            above = True
        if b["c"] < open_price - 0.5:
            below = True
        if above and below:
            returned = True
            break

    return {
        "ib_width": round(ib_w, 2),
        "day_range": round(day_range, 2),
        "rib": rib,
        "sides": sides,
        "ext_up": ext_up,
        "ext_dn": ext_dn,
        "close_pos": close_pos,
        "returned_through_open": returned,
        "open": round(open_price, 2),
        "close": round(close, 2),
        "day_high": round(day_h, 2),
        "day_low": round(day_l, 2),
    }


def dalton_expected(feat):
    """Determine Dalton-expected day type from features.

    Simplified rules:
    - sides=2 → Neutral
    - sides=1 + rib >= 2.5 + close at extreme → Trend
    - sides=1 + returned_through_open + close mid → Neutral (V-reversal)
    - sides=1 + rib < 2.5 → Normal_Variation
    - sides=0 + rib <= 1.3 → Normal
    """
    sides = feat.get("sides", 0)
    rib = feat.get("rib", 0)
    cp = feat.get("close_pos", 0.5)
    returned = feat.get("returned_through_open", False)

    if sides == 2:
        if cp >= 0.85 or cp <= 0.15:
            return "Neutral_Extreme"
        return "Neutral_Center"
    if sides == 1:
        if rib >= 2.5 and (cp >= 0.85 or cp <= 0.15):
            return "Trend_Normal"
        if returned and 0.33 <= cp <= 0.67:
            return "Neutral_Center"  # V-reversal
        return "Normal_Variation"
    # sides == 0
    if rib <= 1.3:
        return "Normal"
    return "Normal"  # 0-sided catch-all


def main():
    parser = argparse.ArgumentParser(description="D1: Classifier truth audit")
    parser.add_argument("--scid", required=True)
    parser.add_argument("--since", default="2026-07-15")
    parser.add_argument("--until", default="2026-08-01")
    args = parser.parse_args()

    start = date.fromisoformat(args.since)
    end = date.fromisoformat(args.until)

    print(f"Reading {args.scid}...")
    raw = read_scid(os.path.expanduser(args.scid), start_date=start, end_date=end)
    all_bars = aggregate_5min(raw)

    by_date = defaultdict(list)
    for b in all_bars:
        d = b["ts"].astimezone(ET).date()
        by_date[d].append(b)

    print(f"\n{'='*90}")
    print("CLASSIFIER TRUTH AUDIT")
    print(f"{'='*90}")
    print(f"{'Date':<12} {'Classifier':<20} {'Dalton Expected':<20} {'Match':>5} {'IB':>5} {'Range':>6} {'RIB':>5} {'Sides':>5} {'CP':>5}")
    print("-" * 90)

    matches = 0
    total = 0
    mismatches = []

    for d in sorted(by_date):
        if d < start or d > end or d.weekday() >= 5:
            continue
        rth = rth_bars(all_bars, d)
        if len(rth) < 12:
            continue

        result = classify_day(rth)
        feat = dalton_features(rth)
        expected = dalton_expected(feat)
        classifier_type = result.get("day_type", "?")

        # Balance match: both balance or both directional
        balance_types = {"Normal", "Neutral_Center", "Neutral_Extreme"}
        directional_types = {"Trend_Normal", "Trend_DD", "Normal_Variation"}
        cls_is_balance = classifier_type in balance_types
        exp_is_balance = expected in balance_types
        match = cls_is_balance == exp_is_balance

        total += 1
        if match:
            matches += 1
            match_str = "OK"
        else:
            match_str = "MISS"
            mismatches.append((d, classifier_type, expected, feat))

        print(f"{d.isoformat():<12} {classifier_type:<20} {expected:<20} {match_str:>5} "
              f"{feat.get('ib_width', 0):>5.1f} {feat.get('day_range', 0):>6.1f} "
              f"{feat.get('rib', 0):>5.2f} {feat.get('sides', 0):>5} {feat.get('close_pos', 0):>5.2f}")

    print(f"\n{'='*90}")
    print(f"Balance/Directional accuracy: {matches}/{total} = {matches/total*100:.0f}%")
    if mismatches:
        print(f"\nMISMATCHES (classifier says directional, Dalton says balance or vice versa):")
        for d, cls, exp, feat in mismatches:
            print(f"  {d}: classifier={cls} expected={exp} "
                  f"(rib={feat.get('rib')}, sides={feat.get('sides')}, "
                  f"returned={feat.get('returned_through_open')}, cp={feat.get('close_pos')})")

    # Write report
    out = ROOT / "docs/reports/CLASSIFIER_TRUTH_AUDIT_2026-08-03.md"
    with open(out, "w") as f:
        f.write(f"# Classifier Truth Audit (D1, 2026-08-03)\n\n")
        f.write(f"Balance/Directional accuracy: {matches}/{total} = {matches/total*100:.0f}%\n\n")
        f.write(f"Mismatches: {len(mismatches)}\n\n")
        for d, cls, exp, feat in mismatches:
            f.write(f"- {d}: **{cls}** → should be **{exp}** "
                    f"(rib={feat.get('rib')}, sides={feat.get('sides')}, "
                    f"returned={feat.get('returned_through_open')})\n")
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
