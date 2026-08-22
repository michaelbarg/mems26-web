#!/usr/bin/env python3
"""Test structural binary classifier convergence against post-hoc.

Runs classify_session per bar (is_eod=False) through the structural binary
state machine for each session, then compares the final held label to
classify_session(is_eod=True).  Target: ≥80% convergence.

READ-ONLY. No production code changes.
"""
import collections
import datetime as dt
import os
import sys
import statistics

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set S1 flags for the classifier
for k, v in {
    "S1_NEW_CLASSIFIER": "1", "S1_ENGINE_NEW_CLASSIFIER": "1",
    "S1_OPEN_DRIVE_TREND": "1", "S1_COMMITTED_PROVISIONAL_V1": "1",
    "S1_CONFIDENCE_V2": "1", "S1_IB_SANITY_V1": "1",
    "S1_ACCEPTANCE_RECLASS_V1": "1", "S1_DD_INVALIDATION_V1": "1",
    "S1_VALUE_MIGRATION_V1": "1", "S1_TREND_CONTROL_V1": "1",
    "S1_TREND_ELONGATION_V1": "1", "S1_RECLASS_REQUIRES_IB_EXT_V1": "1",
}.items():
    os.environ.setdefault(k, v)

from backend.v9.systems.day_type.classifier_core import classify_session
from backend.v9.systems.day_type.structural_binary_v1 import StructuralBinaryClassifier

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
D0, D1 = "2026-07-07", "2026-08-21"
WARM = "2026-06-25"
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12

# Broad match: trend=trend, balance=balance
TREND_TYPES = {"Trend_Normal", "Trend_DD"}
BALANCE_TYPES = {"Normal", "Normal_Variation", "Variation", "Neutral_Center",
                 "Neutral_Extreme", "Nontrend", "Nonconviction"}


def broad_match(a, b):
    """True if both are in the same broad category (trend vs balance)."""
    if a == b:
        return True
    a_trend = a in TREND_TYPES
    b_trend = b in TREND_TYPES
    if a_trend == b_trend:
        return True  # both trend or both balance
    return False


def main():
    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()

    # Load bars
    cur.execute("""
        select (ts at time zone 'America/New_York') as et,
               open, high, low, close, volume
        from v9_bars_5min_woodies
        where (ts at time zone 'America/New_York')::date between %s and %s
          and (ts at time zone 'America/New_York')::time >= %s
          and (ts at time zone 'America/New_York')::time < %s
          and symbol = 'MES'
        order by ts
    """, (WARM, D1, RTH0, RTH1))

    days = collections.OrderedDict()
    for et, o, h, l, c, v in cur.fetchall():
        d = et.date()
        days.setdefault(d, []).append(
            {"o": float(o), "h": float(h), "l": float(l), "c": float(c),
             "v": float(v or 0), "t": et})

    # Load prior day levels for each session
    cur.execute("""
        select trading_date, vah_price, val_price
        from v9_tpo_sessions
        where session_type = 'CASH'
        order by trading_date
    """)
    tpo_by_date = {}
    for td, vah, val in cur.fetchall():
        d = td if isinstance(td, dt.date) else dt.date.fromisoformat(str(td))
        tpo_by_date[d] = {"vah": float(vah) if vah else None,
                          "val": float(val) if val else None}

    conn.close()

    study_dates = sorted(d for d in days if str(d) >= D0 and len(days[d]) >= 20)
    print(f"Testing convergence on {len(study_dates)} sessions")
    print("=" * 90)

    exact_matches = 0
    broad_matches = 0
    total = 0
    first_determined_bars = []

    for d in study_dates:
        bars = days[d]
        if len(bars) < IB_BARS + 3:
            continue

        # IB from first 12 bars
        ibh = max(b["h"] for b in bars[:IB_BARS])
        ibl = min(b["l"] for b in bars[:IB_BARS])

        # Previous day levels
        prev_dates = [k for k in tpo_by_date if k < d]
        pvah = pval = pdh = pdl = None
        if prev_dates:
            prev_d = max(prev_dates)
            pvah = tpo_by_date[prev_d].get("vah")
            pval = tpo_by_date[prev_d].get("val")
        prev_bar_dates = [k for k in days if k < d]
        if prev_bar_dates:
            prev_bars = days[max(prev_bar_dates)]
            pdh = max(b["h"] for b in prev_bars)
            pdl = min(b["l"] for b in prev_bars)

        # Post-hoc (reference)
        eod_result = classify_session(
            bars=[{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                   "v": b["v"]} for b in bars],
            ib_high=ibh, ib_low=ibl,
            open_price=bars[0]["o"],
            prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl,
            is_eod=True,
        )
        eod_type = eod_result.get("day_type", "UNKNOWN")

        # Per-bar structural binary
        sbc = StructuralBinaryClassifier()
        sbc.reset(str(d))
        first_determined_bar = None

        for i in range(IB_BARS, len(bars)):
            cls_result = classify_session(
                bars=[{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                       "v": b["v"]} for b in bars[:i+1]],
                ib_high=ibh, ib_low=ibl,
                open_price=bars[0]["o"],
                prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl,
                is_eod=False,
            )
            out = sbc.on_bar(cls_result, i + 1)
            if first_determined_bar is None and out["determined"] and out["label"] not in ("NOT_YET", None):
                first_determined_bar = i + 1

        final_label = sbc._label or "NOT_YET"
        exact = (final_label == eod_type)
        broad = broad_match(final_label, eod_type)

        if exact:
            exact_matches += 1
        if broad:
            broad_matches += 1
        total += 1

        if first_determined_bar:
            first_determined_bars.append(first_determined_bar)

        mark = "✓" if exact else ("~" if broad else "✗")
        print(f"  {mark} {d}: binary={final_label:20s} eod={eod_type:20s} "
              f"transitions={sbc._transitions} "
              f"first_det={first_determined_bar or '-':>3}")

    print("\n" + "=" * 90)
    print(f"EXACT:  {exact_matches}/{total} = {100*exact_matches/max(total,1):.1f}%")
    print(f"BROAD:  {broad_matches}/{total} = {100*broad_matches/max(total,1):.1f}%")
    if first_determined_bars:
        print(f"Median first-determined bar: {statistics.median(first_determined_bars):.0f}")
    print(f"\nTarget: ≥80% broad convergence")
    if broad_matches / max(total, 1) >= 0.80:
        print("PASS ✓")
    else:
        print("FAIL ✗ — definition needs refinement")


if __name__ == "__main__":
    main()
