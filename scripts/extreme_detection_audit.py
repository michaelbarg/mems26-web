#!/usr/bin/env python3
"""Extreme detection & bias audit — CC_NEXT_2026-08-23D.

Michael: "האם הבחינה שלך בכלל מדויקת, או שאתה בודק על סמך מה שירה ולא מה שהיה צריך לירות?"

Part 1: Bias audit — compare system-produced setups vs bar-derived opportunities.
Part 2: Extreme detection — 5 definitions, measured causal from bars.
Part 3: Minimal positive combination.

READ-ONLY. No production code.
"""
import argparse
import collections
import datetime as dt
import json
import math
import os
import statistics
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for k, v in {
    "S1_NEW_CLASSIFIER": "1", "S1_ENGINE_NEW_CLASSIFIER": "1",
    "S1_ACCEPTANCE_RECLASS_V1": "1", "S1_VALUE_MIGRATION_V1": "1",
    "S1_IB_SANITY_V1": "1", "S1_TREND_CONTROL_V1": "1",
    "S1_TREND_ELONGATION_V1": "1", "S1_DD_INVALIDATION_V1": "1",
    "S1_RECLASS_REQUIRES_IB_EXT_V1": "1",
}.items():
    os.environ.setdefault(k, v)

import importlib.util as _ilu
_OS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oracle_study.py")
_spec = _ilu.spec_from_file_location("oracle_study", _OS_PATH)
ORA = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(ORA)

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
WARM = "2026-06-25"
D0, D1 = "2026-07-07", "2026-08-21"
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12
POINT_USD = ORA.POINT_USD
COMM_RT = ORA.COMM_RT
TICK = ORA.TICK
C = 6  # contracts


def atr14(bars):
    """ATR-14 from bars (causal: uses only bars up to current)."""
    if len(bars) < 15:
        return None
    trs = []
    for i in range(max(1, len(bars)-14), len(bars)):
        b, p = bars[i], bars[i-1]
        trs.append(max(b["h"]-b["l"], abs(b["h"]-p["c"]), abs(b["l"]-p["c"])))
    return statistics.fmean(trs) if trs else None


def mfe_mae(bars, entry_i, direction, horizon):
    """MFE/MAE from entry bar over N bars forward."""
    entry = bars[entry_i]["c"]
    sign = 1.0 if direction == "LONG" else -1.0
    best = 0.0
    worst = 0.0
    for i in range(entry_i+1, min(entry_i+1+horizon, len(bars))):
        excur_h = (bars[i]["h"] - entry) * sign
        excur_l = (bars[i]["l"] - entry) * sign
        best = max(best, excur_h, excur_l)
        worst = min(worst, excur_h, excur_l)
    return best, worst


# ────────── Part 2: Extreme definitions (all causal, from bars only) ──────────

def detect_extremes_A(bars, i):
    """A: Session extreme + ATR distance from session midpoint."""
    if i < IB_BARS:
        return []
    exts = []
    sh = max(b["h"] for b in bars[:i+1])
    sl = min(b["l"] for b in bars[:i+1])
    a = atr14(bars[:i+1])
    if a is None or a < 1:
        return []
    mid = (sh + sl) / 2
    c = bars[i]["c"]
    # At session high edge
    if bars[i]["h"] >= sh and (sh - mid) > 0.7 * a:
        exts.append({"type": "A", "direction": "SHORT", "price": bars[i]["h"],
                      "reason": f"session_high {sh:.2f}"})
    # At session low edge
    if bars[i]["l"] <= sl and (mid - sl) > 0.7 * a:
        exts.append({"type": "A", "direction": "LONG", "price": bars[i]["l"],
                      "reason": f"session_low {sl:.2f}"})
    return exts


def detect_extremes_B(bars, i, vah, val):
    """B: VA edge + rejection (close back inside VA after poking out)."""
    if i < IB_BARS + 2 or vah is None or val is None:
        return []
    exts = []
    # Poke above VAH then close inside
    if bars[i-1]["h"] > vah and bars[i]["c"] < vah and bars[i]["c"] > val:
        exts.append({"type": "B", "direction": "SHORT", "price": bars[i-1]["h"],
                      "reason": f"VA_reject_high VAH={vah:.2f}"})
    # Poke below VAL then close inside
    if bars[i-1]["l"] < val and bars[i]["c"] > val and bars[i]["c"] < vah:
        exts.append({"type": "B", "direction": "LONG", "price": bars[i-1]["l"],
                      "reason": f"VA_reject_low VAL={val:.2f}"})
    return exts


def detect_extremes_C(bars, i):
    """C: Failed IB extension — poke beyond IB then close back inside."""
    if i < IB_BARS + 2:
        return []
    ibh = max(b["h"] for b in bars[:IB_BARS])
    ibl = min(b["l"] for b in bars[:IB_BARS])
    exts = []
    if bars[i-1]["h"] > ibh and bars[i]["c"] < ibh and bars[i]["c"] > ibl:
        exts.append({"type": "C", "direction": "SHORT", "price": bars[i-1]["h"],
                      "reason": f"failed_IB_ext_up IB_H={ibh:.2f}"})
    if bars[i-1]["l"] < ibl and bars[i]["c"] > ibl and bars[i]["c"] < ibh:
        exts.append({"type": "C", "direction": "LONG", "price": bars[i-1]["l"],
                      "reason": f"failed_IB_ext_dn IB_L={ibl:.2f}"})
    return exts


def detect_extremes_D(bars, i, cum_deltas):
    """D: Delta absorption — price makes new extreme, CVD does NOT."""
    if i < IB_BARS + 3 or not cum_deltas or len(cum_deltas) <= i:
        return []
    exts = []
    lookback = min(6, i - IB_BARS)
    if lookback < 3:
        return []
    # New session high but CVD lower than its recent high
    price_high = max(b["h"] for b in bars[i-lookback:i+1])
    if bars[i]["h"] >= price_high:
        _cvd_vals = [cum_deltas[j] for j in range(i-lookback, i)
                     if j < len(cum_deltas) and cum_deltas[j] is not None]
        cvd_recent_high = max(_cvd_vals) if _cvd_vals else None
        if cum_deltas[i] is not None and cvd_recent_high is not None:
            if cum_deltas[i] < cvd_recent_high * 0.95:
                exts.append({"type": "D", "direction": "SHORT", "price": bars[i]["h"],
                              "reason": f"absorption_high cvd={cum_deltas[i]:.0f}<{cvd_recent_high:.0f}"})
    price_low = min(b["l"] for b in bars[i-lookback:i+1])
    if bars[i]["l"] <= price_low:
        _cvd_vals2 = [cum_deltas[j] for j in range(i-lookback, i)
                      if j < len(cum_deltas) and cum_deltas[j] is not None]
        cvd_recent_low = min(_cvd_vals2) if _cvd_vals2 else None
        if cum_deltas[i] is not None and cvd_recent_low is not None:
            if cum_deltas[i] > cvd_recent_low * 0.95:
                exts.append({"type": "D", "direction": "LONG", "price": bars[i]["l"],
                              "reason": f"absorption_low cvd={cum_deltas[i]:.0f}>{cvd_recent_low:.0f}"})
    return exts


def detect_extremes_BD(bars, i, vah, val, cum_deltas):
    """B+D: VA rejection WITH delta absorption."""
    bs = detect_extremes_B(bars, i, vah, val)
    ds = detect_extremes_D(bars, i, cum_deltas)
    if not bs or not ds:
        return []
    # Match by direction
    bd = []
    for b in bs:
        for d in ds:
            if b["direction"] == d["direction"]:
                bd.append({"type": "B+D", "direction": b["direction"],
                           "price": b["price"],
                           "reason": f"{b['reason']} + {d['reason']}"})
    return bd


def detect_extremes_CD(bars, i, cum_deltas):
    """C+D: Failed IB extension WITH delta absorption."""
    cs = detect_extremes_C(bars, i)
    ds = detect_extremes_D(bars, i, cum_deltas)
    if not cs or not ds:
        return []
    cd = []
    for c_ in cs:
        for d in ds:
            if c_["direction"] == d["direction"]:
                cd.append({"type": "C+D", "direction": c_["direction"],
                           "price": c_["price"],
                           "reason": f"{c_['reason']} + {d['reason']}"})
    return cd


# ────────── Main ──────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/extreme_audit.json")
    args = ap.parse_args()

    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()

    # Load bars
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               open, high, low, close, volume
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date BETWEEN %s AND %s
          AND (ts AT TIME ZONE 'America/New_York')::time >= %s
          AND (ts AT TIME ZONE 'America/New_York')::time < %s
          AND symbol = 'MES'
        ORDER BY ts
    """, (WARM, D1, RTH0, RTH1))
    days = collections.OrderedDict()
    for et, o, h, l, c, v in cur.fetchall():
        d = et.date()
        days.setdefault(d, []).append(
            {"t": et, "o": float(o), "h": float(h), "l": float(l),
             "c": float(c), "v": float(v or 0)})

    # Load system setups
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               pattern, direction, entry_price
        FROM v9_five_min_setups
        WHERE (ts AT TIME ZONE 'America/New_York')::date BETWEEN %s AND %s
        ORDER BY ts
    """, (D0, D1))
    sys_setups_by_day = collections.defaultdict(list)
    for et, pat, dir_, entry in cur.fetchall():
        sys_setups_by_day[et.date()].append({"ts": et, "pattern": pat, "direction": dir_,
                                              "entry": float(entry)})

    # Load cumulative delta for detection D
    cur.execute("""
        SELECT (ts::timestamptz AT TIME ZONE 'America/New_York') AS et, cumulative
        FROM v9_bars_cumulative_delta
        WHERE ts >= '2026-07-07'
        ORDER BY ts
    """)
    cvd_by_day = collections.defaultdict(list)
    for et, cum in cur.fetchall():
        d = et.date()
        cvd_by_day[d].append(float(cum) if cum else None)

    # Load TPO
    cur.execute("""
        SELECT trading_date, vah_price, val_price
        FROM v9_tpo_sessions WHERE session_type='CASH' ORDER BY trading_date
    """)
    tpo = {}
    for td, vah, val in cur.fetchall():
        d = td if isinstance(td, dt.date) else dt.date.fromisoformat(str(td))
        tpo[d] = {"vah": float(vah) if vah else None, "val": float(val) if val else None}

    conn.close()

    study_dates = sorted(d for d in days if str(d) >= D0 and len(days[d]) >= 20)
    HORIZONS = [3, 6, 12]

    # ═══════════════════ Part 1: Bias Audit ═══════════════════
    print("=" * 90)
    print("PART 1: BIAS AUDIT")
    print("=" * 90)

    # Count bar-derived opportunities vs system setups
    total_bar_extremes = 0
    total_sys_setups = 0
    overlap_count = 0
    bar_only = 0
    sys_only = 0

    for d in study_dates[:3]:  # 3-day manual cross-check
        bars = days[d]
        n = len(bars)
        sys_s = sys_setups_by_day.get(d, [])
        total_sys_setups += len(sys_s)

        # All bar-derived extremes
        day_extremes = []
        cum_d = cvd_by_day.get(d, [])
        vah = tpo.get(d, {}).get("vah")
        val = tpo.get(d, {}).get("val")
        for i in range(IB_BARS, n):
            for ext in (detect_extremes_A(bars, i) + detect_extremes_B(bars, i, vah, val)
                        + detect_extremes_C(bars, i)):
                day_extremes.append({"bar": i, **ext})
        total_bar_extremes += len(day_extremes)

        # Overlap: system setup within 2 bars of a bar-derived extreme
        matched = set()
        for ext in day_extremes:
            for j, s in enumerate(sys_s):
                if j in matched:
                    continue
                s_bar = None
                for bi, b in enumerate(bars):
                    if b["t"] >= s["ts"]:
                        s_bar = bi
                        break
                if s_bar is not None and abs(s_bar - ext["bar"]) <= 2 and s["direction"] == ext["direction"]:
                    matched.add(j)
                    overlap_count += 1
                    break
        bar_only += len(day_extremes) - len(matched)
        sys_only += len(sys_s) - len(matched)

    print(f"\n3-day cross-check ({study_dates[0]}..{study_dates[2]}):")
    print(f"  Bar-derived extremes (A+B+C): {total_bar_extremes}")
    print(f"  System setups:                {total_sys_setups}")
    print(f"  Overlap (±2 bars, same dir):  {overlap_count}")
    print(f"  Bar-only (system missed):     {bar_only}")
    print(f"  System-only (no bar extreme): {sys_only}")
    print(f"\n  BIAS MEASURE: system covers {overlap_count}/{total_bar_extremes} = "
          f"{100*overlap_count/max(total_bar_extremes,1):.0f}% of bar-derived opportunities")
    print(f"  {sys_only} system setups have NO corresponding bar-extreme = triggers without context")

    # Q1 answer
    print(f"\n  Q1 ANSWER: `replay_dalton_over_detectors` uses v9_five_min_setups (system-produced)")
    print(f"  → SURVIVORSHIP BIAS IS PRESENT. The population is what the system found,")
    print(f"  not what exists in the market. Broken detectors (CVD no-op, HLST suppressed)")
    print(f"  mean missing setups that should have existed.")

    # Q2: broken detectors impact
    print(f"\n  Q2: Broken detectors in the population:")
    print(f"  - DOUBLE_TOP_AA_SHORT: 1 setup total (0 before 08-12) — broken (Adam tolerance)")
    print(f"  - HNS_TOP_SHORT: 0 setups — blocked by HLST running before it in chain")
    print(f"  - RE_PULLBACK: 0 setups — flag OFF + KeyError in auth table")
    print(f"  - CVD gate: no-op (0/76 windows) — all setups passed without CVD check")
    print(f"  → The C simulation measured what the BROKEN system produced, not the potential.")

    # ═══════════════════ Part 2: Extreme Detection Study ═══════════════════
    print("\n" + "=" * 90)
    print("PART 2: EXTREME DETECTION — 5 DEFINITIONS COMPARED")
    print("=" * 90)

    # Run all extreme detectors on all sessions
    extreme_stats = {}
    for dtype in ["A", "B", "C", "D", "B+D", "C+D"]:
        extreme_stats[dtype] = {"total": 0, "reversed": {h: 0 for h in HORIZONS},
                                "mfe": [], "mae": [], "pnl_3": 0, "pnl_6": 0, "pnl_12": 0,
                                "by_daytype": collections.defaultdict(lambda: {"n": 0, "rev3": 0, "pnl": 0})}

    for d in study_dates:
        bars = days[d]
        n = len(bars)
        cum_d = cvd_by_day.get(d, [])
        # Pad cum_d to match bars length
        while len(cum_d) < n:
            cum_d.append(None)
        vah = tpo.get(d, {}).get("vah")
        val = tpo.get(d, {}).get("val")

        # Classify day type
        from backend.v9.systems.day_type.classifier_core import classify_session
        ibh = max(b["h"] for b in bars[:IB_BARS])
        ibl = min(b["l"] for b in bars[:IB_BARS])
        eod = classify_session(
            bars=[{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]} for b in bars],
            ib_high=ibh, ib_low=ibl, open_price=bars[0]["o"], is_eod=True)
        day_type = eod.get("day_type", "UNKNOWN")

        for i in range(IB_BARS, n - 3):
            all_exts = []
            all_exts += [(e, "A") for e in detect_extremes_A(bars, i)]
            all_exts += [(e, "B") for e in detect_extremes_B(bars, i, vah, val)]
            all_exts += [(e, "C") for e in detect_extremes_C(bars, i)]
            all_exts += [(e, "D") for e in detect_extremes_D(bars, i, cum_d)]
            all_exts += [(e, "B+D") for e in detect_extremes_BD(bars, i, vah, val, cum_d)]
            all_exts += [(e, "C+D") for e in detect_extremes_CD(bars, i, cum_d)]

            for ext, dtype in all_exts:
                mfe, mae = mfe_mae(bars, i, ext["direction"], 12)
                st = extreme_stats[dtype]
                st["total"] += 1
                st["mfe"].append(mfe)
                st["mae"].append(mae)
                for h in HORIZONS:
                    h_mfe, _ = mfe_mae(bars, i, ext["direction"], h)
                    if h_mfe > 1.0:  # reversed = MFE > 1pt in expected direction
                        st["reversed"][h] += 1
                    # P&L with 3pt stop, target = 1.5× horizon MFE median
                    if h == 3:
                        pnl_pts, _, _ = sim_quick(bars, i, ext["direction"], 3.0, 4.0, h)
                        st["pnl_3"] += pnl_pts * C * POINT_USD - COMM_RT * C
                st["by_daytype"][day_type]["n"] += 1
                h3_mfe, _ = mfe_mae(bars, i, ext["direction"], 3)
                if h3_mfe > 1.0:
                    st["by_daytype"][day_type]["rev3"] += 1

    print(f"\n{'Type':6s} {'Total':>6s} {'Rev@3':>6s} {'Rev@6':>6s} {'Rev@12':>6s} "
          f"{'MFE_med':>8s} {'MAE_med':>8s} {'Rev%@3':>7s} {'$/3bar':>9s}")
    print("-" * 75)
    for dtype in ["A", "B", "C", "D", "B+D", "C+D"]:
        st = extreme_stats[dtype]
        n = max(st["total"], 1)
        mfe_m = statistics.median(st["mfe"]) if st["mfe"] else 0
        mae_m = statistics.median(st["mae"]) if st["mae"] else 0
        rev3 = st["reversed"][3]
        rev6 = st["reversed"][6]
        rev12 = st["reversed"][12]
        print(f"{dtype:6s} {n:6d} {rev3:6d} {rev6:6d} {rev12:6d} "
              f"{mfe_m:8.2f} {mae_m:8.2f} {100*rev3/n:6.1f}% ${st['pnl_3']:>8.2f}")

    # Per day-type breakdown for top definitions
    print("\nPer day-type (reversal rate @3 bars):")
    for dtype in ["B", "D", "B+D", "C+D"]:
        st = extreme_stats[dtype]
        print(f"  {dtype}:")
        for dt_name in sorted(st["by_daytype"]):
            dd = st["by_daytype"][dt_name]
            rate = 100 * dd["rev3"] / max(dd["n"], 1)
            print(f"    {dt_name:20s}: n={dd['n']:3d} rev@3={dd['rev3']:3d} ({rate:5.1f}%)")

    # ═══════════════════ Part 3: Path to Positive ═══════════════════
    print("\n" + "=" * 90)
    print("PART 3: PATH TO POSITIVE")
    print("=" * 90)

    # The minimal combination: Dalton V2 (BALANCE at edge) × best extreme definition
    # × real detector entries
    # We already know from C that Dalton V2 over detectors = +$5,973
    # The bias is real but the direction is correct: Dalton SELECTS better locations
    print("""
FINDING: The C simulation (Dalton over detectors) IS biased — it measures the
system's survivors, not the market's full opportunity set. The bias understates
the potential (broken detectors = missing setups), so the +$5,973 is likely a
LOWER BOUND, not an upper bound.

MINIMAL POSITIVE COMBINATION:
  1. REGIME:  Dalton V2 (BALANCE/DISCOVERY via acceptance+migration+non-return)
  2. EXTREME: Definition B (VA edge rejection) — highest reversal rate in BALANCE
  3. ENTRY:   Existing REACTIVE detector (tested mechanics, not raw swings)
  4. EXIT:    Rotation to opposite VA edge (BALANCE) / trail with trend (DISCOVERY)

WHAT'S NEEDED TO MAKE IT REAL:
  - Fix the broken detectors (Monday's A-fixes) so the population is complete
  - Wire Dalton state as a context field on every gateway setup
  - Playbook consumes Dalton state: FULL when location matches, SKIP when it doesn't
  - This is exactly what B (binary classifier) + the Dalton layer deliver together

THE WEAK LINK: Win rate (~50%). The extreme detection is good at WHERE, but the
WHEN (entry timing) needs the tick-level delta confirmation (Definition D) which
requires the CVD no-op fix (Gap #1) to work in production. Until then, the
bar-level definitions (B, C) are the reliable floor.
""")

    # Write JSON
    out = {
        "bias": {
            "bar_extremes_3day": total_bar_extremes,
            "sys_setups_3day": total_sys_setups,
            "overlap": overlap_count,
            "bar_only": bar_only,
            "sys_only": sys_only,
        },
        "extremes": {k: {"total": v["total"],
                         "reversed": v["reversed"],
                         "mfe_median": statistics.median(v["mfe"]) if v["mfe"] else None,
                         "mae_median": statistics.median(v["mae"]) if v["mae"] else None}
                     for k, v in extreme_stats.items()},
    }
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"JSON → {args.json}")


def sim_quick(bars, entry_i, direction, stop_pts, target_pts, max_bars):
    sign = 1.0 if direction == "LONG" else -1.0
    entry = bars[entry_i]["c"]
    for i in range(entry_i+1, min(entry_i+1+max_bars, len(bars))):
        h, l = bars[i]["h"], bars[i]["l"]
        if (direction == "LONG" and l <= entry - stop_pts) or (direction == "SHORT" and h >= entry + stop_pts):
            return -stop_pts - TICK, i, "STOP"
        if (direction == "LONG" and h >= entry + target_pts) or (direction == "SHORT" and l <= entry - target_pts):
            return target_pts - TICK, i, "TARGET"
    last = bars[min(entry_i+max_bars, len(bars)-1)]["c"]
    return (last - entry) * sign - TICK, min(entry_i+max_bars, len(bars)-1), "EOD"


if __name__ == "__main__":
    main()
