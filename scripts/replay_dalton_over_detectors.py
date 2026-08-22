#!/usr/bin/env python3
"""Dalton V2 context layer OVER the existing S2 detectors.

Michael 23.08: "כן" — the value of Dalton is in SELECTION, not ENTRY.
Use the real detector setups (v9_five_min_setups), real stops/targets,
and filter through Dalton BALANCE/DISCOVERY + location.

Layers:
  (0) BOOKS    — what MEMS26 actually booked (v9_trades mode='live')
  (1) DETECTORS — all setups that the detectors produced, simulated with
                  their own stops/targets, ONE slot at a time
  (2) DALTON   — same setups, filtered by Dalton V2 context (acceptance +
                  value migration + non-return for DISCOVERY)
  (3) ORACLE   — best-2 swings (ceiling)

READ-ONLY. No production code, no .env, no restarts.
"""
import argparse
import collections
import datetime as dt
import json
import os
import statistics
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# S1 flags for classifier
for k, v in {
    "S1_NEW_CLASSIFIER": "1", "S1_ENGINE_NEW_CLASSIFIER": "1",
    "S1_OPEN_DRIVE_TREND": "1", "S1_COMMITTED_PROVISIONAL_V1": "1",
    "S1_CONFIDENCE_V2": "1", "S1_IB_SANITY_V1": "1",
    "S1_ACCEPTANCE_RECLASS_V1": "1", "S1_DD_INVALIDATION_V1": "1",
    "S1_VALUE_MIGRATION_V1": "1", "S1_TREND_CONTROL_V1": "1",
    "S1_TREND_ELONGATION_V1": "1", "S1_RECLASS_REQUIRES_IB_EXT_V1": "1",
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

# Dalton trade selection rules (same as replay_dalton_context.py)
BALANCE_LONG_LOCATIONS = {"BELOW_VAL", "AT_EDGE_LOW"}
BALANCE_SHORT_LOCATIONS = {"ABOVE_VAH", "AT_EDGE_HIGH"}
BALANCE_PATTERNS_LONG = {"REACTIVE_LONG", "DOUBLE_BOTTOM_EE_LONG", "INVERSE_HNS_LONG"}
BALANCE_PATTERNS_SHORT = {"REACTIVE_SHORT", "DOUBLE_TOP_AA_SHORT", "HNS_TOP_SHORT"}
DISCOVERY_PATTERNS_WITH = {"INITIATIVE_LONG", "INITIATIVE_SHORT", "BULL_FLAG_LONG",
                           "BEAR_FLAG_SHORT", "TREND_STEP"}


def dalton_allows(setup, dalton_state, dalton_location, discovery_dir):
    """Does Dalton V2 context allow this setup?"""
    pat = setup["pattern"]
    direction = setup["direction"]
    state = dalton_state

    if state == "UNKNOWN":
        return False, "pre_ib"

    if state == "BALANCE":
        if direction == "LONG" and dalton_location in BALANCE_LONG_LOCATIONS:
            if pat in BALANCE_PATTERNS_LONG or pat.endswith("_LONG"):
                return True, "balance_long_edge"
            return False, f"balance_wrong_pattern({pat})"
        if direction == "SHORT" and dalton_location in BALANCE_SHORT_LOCATIONS:
            if pat in BALANCE_PATTERNS_SHORT or pat.endswith("_SHORT"):
                return True, "balance_short_edge"
            return False, f"balance_wrong_pattern({pat})"
        if dalton_location == "IN_VALUE":
            return False, "balance_mid_value"
        return False, f"balance_wrong_loc({dalton_location})"

    if state == "DISCOVERY":
        if discovery_dir == "UP" and direction == "LONG":
            return True, "discovery_with_up"
        if discovery_dir == "DOWN" and direction == "SHORT":
            return True, "discovery_with_down"
        return False, f"discovery_against({discovery_dir}_{direction})"

    return False, "unknown"


def value_location(price, vah, val):
    """Where is price relative to value area."""
    if vah is None or val is None:
        return "UNKNOWN"
    va_range = max(vah - val, 1.0)
    edge = max(0.15 * va_range, 1.0)
    if price >= vah - edge and price <= vah + edge:
        return "AT_EDGE_HIGH"
    if price <= val + edge and price >= val - edge:
        return "AT_EDGE_LOW"
    if price > vah:
        return "ABOVE_VAH"
    if price < val:
        return "BELOW_VAL"
    return "IN_VALUE"


def sim_trade_bars(bars, entry_bar_idx, direction, entry_price, stop_price, t1_price, contracts):
    """Bar-by-bar trade sim with real stop/target prices."""
    sign = 1.0 if direction == "LONG" else -1.0

    for i in range(entry_bar_idx + 1, len(bars)):
        h, l = bars[i]["h"], bars[i]["l"]
        # Stop
        if (direction == "LONG" and l <= stop_price) or (direction == "SHORT" and h >= stop_price):
            pnl_pts = (stop_price - entry_price) * sign - TICK
            return pnl_pts * contracts * POINT_USD - COMM_RT * contracts, i, "STOP"
        # T1
        if t1_price and ((direction == "LONG" and h >= t1_price) or
                         (direction == "SHORT" and l <= t1_price)):
            pnl_pts = (t1_price - entry_price) * sign - TICK
            return pnl_pts * contracts * POINT_USD - COMM_RT * contracts, i, "T1"

    # EOD
    last_c = bars[-1]["c"]
    pnl_pts = (last_c - entry_price) * sign - TICK
    return pnl_pts * contracts * POINT_USD - COMM_RT * contracts, len(bars) - 1, "EOD"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/dalton_over_detectors.json")
    ap.add_argument("--contracts", type=int, default=6)
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

    # Load setups
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               pattern, direction, entry_price, stop_price, t1_price, t2_price,
               day_type_at_fire
        FROM v9_five_min_setups
        WHERE (ts AT TIME ZONE 'America/New_York')::date BETWEEN %s AND %s
        ORDER BY ts
    """, (D0, D1))
    setups_by_day = collections.defaultdict(list)
    for et, pat, dir_, entry, stop, t1, t2, dt_fire in cur.fetchall():
        d = et.date()
        setups_by_day[d].append({
            "ts": et, "pattern": pat, "direction": dir_,
            "entry_price": float(entry), "stop_price": float(stop),
            "t1_price": float(t1) if t1 else None,
            "t2_price": float(t2) if t2 else None,
            "day_type_at_fire": dt_fire,
        })

    # Load book trades
    cur.execute("""
        SELECT (entry_ts AT TIME ZONE 'America/New_York')::date AS d, pnl_usd
        FROM v9_trades WHERE mode = 'live'
          AND (entry_ts AT TIME ZONE 'America/New_York')::date BETWEEN %s AND %s
    """, (D0, D1))
    books_by_day = collections.defaultdict(float)
    books_count_by_day = collections.defaultdict(int)
    for d, pnl in cur.fetchall():
        books_by_day[d] += float(pnl or 0)
        books_count_by_day[d] += 1

    # Load TPO for value area
    cur.execute("""
        SELECT trading_date, vah_price, val_price
        FROM v9_tpo_sessions WHERE session_type = 'CASH' ORDER BY trading_date
    """)
    tpo = {}
    for td, vah, val in cur.fetchall():
        d = td if isinstance(td, dt.date) else dt.date.fromisoformat(str(td))
        tpo[d] = {"vah": float(vah) if vah else None, "val": float(val) if val else None}

    conn.close()

    from backend.v9.systems.day_type.classifier_core import classify_session

    study_dates = sorted(d for d in days if str(d) >= D0 and len(days[d]) >= 20)
    C = args.contracts

    print(f"Dalton V2 over detectors — {len(study_dates)} sessions, {C} contracts")
    print("=" * 100)

    all_results = {}
    # Aggregates for cross-tables
    pattern_stats = collections.defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0,
                                                      "dalton_n": 0, "dalton_wins": 0, "dalton_pnl": 0.0})
    loc_pat_stats = collections.defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0})

    for d in study_dates:
        bars = days[d]
        setups = setups_by_day.get(d, [])
        n = len(bars)
        if n < IB_BARS + 3:
            continue

        ibh = max(b["h"] for b in bars[:IB_BARS])
        ibl = min(b["l"] for b in bars[:IB_BARS])
        ibw = ibh - ibl

        # Previous day levels
        prev_dates = [k for k in tpo if k < d]
        pvah = pval = None
        if prev_dates:
            pd = max(prev_dates)
            pvah = tpo[pd].get("vah")
            pval = tpo[pd].get("val")
        prev_bar_dates = [k for k in days if k < d]
        pdh = pdl = None
        if prev_bar_dates:
            pb = days[max(prev_bar_dates)]
            pdh = max(b["h"] for b in pb)
            pdl = min(b["l"] for b in pb)

        # Today's TPO (developing VA)
        today_vah = tpo.get(d, {}).get("vah") or ibh
        today_val = tpo.get(d, {}).get("val") or ibl

        # Post-hoc day type
        eod = classify_session(
            bars=[{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]} for b in bars],
            ib_high=ibh, ib_low=ibl, open_price=bars[0]["o"],
            prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl, is_eod=True)
        day_type = eod.get("day_type", "UNKNOWN")

        # Per-bar Dalton state (using classify_session features)
        dalton_state = "UNKNOWN"
        discovery_dir = None
        prev_accepted = None
        prev_failed = False
        prev_migration = None
        prev_sides = 0
        accepted_dir = None
        accepted_count = 0
        dalton_transitions = []

        def _update_dalton(bar_idx):
            nonlocal dalton_state, discovery_dir, prev_accepted, prev_failed
            nonlocal prev_migration, prev_sides, accepted_dir, accepted_count

            if bar_idx == IB_BARS - 1:
                dalton_state = "BALANCE"
                dalton_transitions.append((bar_idx, "ib_lock", "BALANCE"))
                return

            if bar_idx < IB_BARS:
                return

            cls = classify_session(
                bars=[{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
                      for b in bars[:bar_idx+1]],
                ib_high=ibh, ib_low=ibl, open_price=bars[0]["o"],
                prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl, is_eod=False)

            ca = cls.get("accepted_break")
            cf = bool(cls.get("failed_break"))
            cm = (cls.get("measured") or {}).get("value_migration")
            cs = (cls.get("measured") or {}).get("sides", 0) or 0

            old_state = dalton_state

            if ca and ca != prev_accepted:
                accepted_dir = ca
                accepted_count = 0
                if cm in ("UP", "DOWN") and cm == ca and not cf:
                    dalton_state = "DISCOVERY"
                    discovery_dir = ca
                    dalton_transitions.append((bar_idx, f"discovery_{ca}", "DISCOVERY"))

            if accepted_dir:
                accepted_count += 1
                if dalton_state == "BALANCE" and accepted_count >= 3 and cm == accepted_dir and not cf:
                    dalton_state = "DISCOVERY"
                    discovery_dir = accepted_dir
                    dalton_transitions.append((bar_idx, f"delayed_discovery_{accepted_dir}", "DISCOVERY"))

            if cf and not prev_failed and dalton_state == "DISCOVERY":
                dalton_state = "BALANCE"
                discovery_dir = None
                accepted_dir = None
                dalton_transitions.append((bar_idx, "failed_break", "BALANCE"))

            if cs == 2 and prev_sides < 2 and dalton_state == "DISCOVERY":
                dalton_state = "BALANCE"
                discovery_dir = None
                dalton_transitions.append((bar_idx, "dual_break", "BALANCE"))

            prev_accepted = ca
            prev_failed = cf
            prev_migration = cm
            prev_sides = cs

        # Run Dalton state machine through all bars
        for i in range(n):
            _update_dalton(i)

        # Map setup timestamps to bar indices
        bar_times = {b["t"]: i for i, b in enumerate(bars)}

        # --- L1: All detector setups, one slot ---
        l1_trades = []
        l1_pnl = 0.0
        slot_free_at = 0
        for s in setups:
            # Find bar index for this setup
            s_time = s["ts"]
            s_bar = None
            for i, b in enumerate(bars):
                if b["t"] >= s_time:
                    s_bar = i
                    break
            if s_bar is None or s_bar >= n - 2:
                continue
            if s_bar < slot_free_at:
                continue  # slot occupied

            pnl, exit_i, reason = sim_trade_bars(
                bars, s_bar, s["direction"], s["entry_price"],
                s["stop_price"], s["t1_price"], C)
            l1_trades.append({
                "pattern": s["pattern"], "direction": s["direction"],
                "entry": s["entry_price"], "pnl": round(pnl, 2),
                "exit_reason": reason, "bar": s_bar,
            })
            l1_pnl += pnl
            slot_free_at = exit_i + 1

            ps = pattern_stats[s["pattern"]]
            ps["n"] += 1
            ps["pnl"] += pnl
            if pnl > 0:
                ps["wins"] += 1

        # --- L2: Dalton-filtered detector setups ---
        l2_trades = []
        l2_pnl = 0.0
        slot_free_at = 0

        # Re-run Dalton state machine and get state at each bar
        d_state_at = {}
        d_dir_at = {}
        _ds2 = "UNKNOWN"
        _dd2 = None
        _pa2 = None; _pf2 = False; _pm2 = None; _ps2 = 0; _ad2 = None; _ac2 = 0
        for i in range(n):
            if i == IB_BARS - 1:
                _ds2 = "BALANCE"
            elif i >= IB_BARS:
                cls = classify_session(
                    bars=[{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
                          for b in bars[:i+1]],
                    ib_high=ibh, ib_low=ibl, open_price=bars[0]["o"],
                    prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl, is_eod=False)
                ca = cls.get("accepted_break")
                cf = bool(cls.get("failed_break"))
                cm = (cls.get("measured") or {}).get("value_migration")
                cs = (cls.get("measured") or {}).get("sides", 0) or 0
                if ca and ca != _pa2:
                    _ad2 = ca; _ac2 = 0
                    if cm in ("UP", "DOWN") and cm == ca and not cf:
                        _ds2 = "DISCOVERY"; _dd2 = ca
                if _ad2:
                    _ac2 += 1
                    if _ds2 == "BALANCE" and _ac2 >= 3 and _pm2 == _ad2 and not cf:
                        _ds2 = "DISCOVERY"; _dd2 = _ad2
                if cf and not _pf2 and _ds2 == "DISCOVERY":
                    _ds2 = "BALANCE"; _dd2 = None; _ad2 = None
                if cs == 2 and _ps2 < 2 and _ds2 == "DISCOVERY":
                    _ds2 = "BALANCE"; _dd2 = None
                _pa2 = ca; _pf2 = cf; _pm2 = cm; _ps2 = cs
            d_state_at[i] = _ds2
            d_dir_at[i] = _dd2

        for s in setups:
            s_time = s["ts"]
            s_bar = None
            for i, b in enumerate(bars):
                if b["t"] >= s_time:
                    s_bar = i
                    break
            if s_bar is None or s_bar >= n - 2:
                continue
            if s_bar < slot_free_at:
                continue

            loc = value_location(s["entry_price"], today_vah, today_val)
            ds = d_state_at.get(s_bar, "UNKNOWN")
            dd = d_dir_at.get(s_bar)
            take, reason_d = dalton_allows(s, ds, loc, dd)

            if not take:
                continue

            pnl, exit_i, reason = sim_trade_bars(
                bars, s_bar, s["direction"], s["entry_price"],
                s["stop_price"], s["t1_price"], C)
            l2_trades.append({
                "pattern": s["pattern"], "direction": s["direction"],
                "entry": s["entry_price"], "pnl": round(pnl, 2),
                "exit_reason": reason, "dalton_reason": reason_d,
                "dalton_state": ds, "location": loc,
            })
            l2_pnl += pnl
            slot_free_at = exit_i + 1

            ps = pattern_stats[s["pattern"]]
            ps["dalton_n"] += 1
            ps["dalton_pnl"] += pnl
            if pnl > 0:
                ps["dalton_wins"] += 1

            lk = f"{loc}×{s['pattern']}"
            lps = loc_pat_stats[lk]
            lps["n"] += 1
            lps["pnl"] += pnl
            if pnl > 0:
                lps["wins"] += 1

        # Oracle
        thr = ORA.thr_for({d: bars}, d)
        piv = ORA.zigzag(bars, thr)
        legs = ORA.legs_from(bars, piv) if hasattr(ORA, "legs_from") else []
        oracle_pnl = 0.0
        if legs and len(legs) >= 2:
            lp = sorted([abs(l.get("pts", 0)) * C * POINT_USD - ORA.costs(C) for l in legs], reverse=True)
            oracle_pnl = sum(lp[:2])

        books = books_by_day.get(d, 0)
        books_n = books_count_by_day.get(d, 0)

        all_results[d] = {
            "day_type": day_type, "bars": n, "ib_width": round(ibw, 2),
            "transitions": len(dalton_transitions),
            "books_pnl": round(books, 2), "books_n": books_n,
            "l1_pnl": round(l1_pnl, 2), "l1_n": len(l1_trades),
            "l2_pnl": round(l2_pnl, 2), "l2_n": len(l2_trades),
            "oracle_pnl": round(oracle_pnl, 2),
            "l2_detail": l2_trades,
        }

        print(f"{d} {day_type:20s} IB={ibw:5.1f} tr={len(dalton_transitions)} | "
              f"books={books:>8.2f}({books_n}) | L1={l1_pnl:>8.2f}({len(l1_trades)}) | "
              f"L2={l2_pnl:>8.2f}({len(l2_trades)}) | oracle={oracle_pnl:>8.2f}")
        for t in l2_trades:
            print(f"  {t['pattern']:25s} {t['direction']:5s} @{t['entry']:.2f} "
                  f"→ ${t['pnl']:>7.2f} ({t['exit_reason']}) [{t['dalton_state']}/{t['location']}: {t['dalton_reason']}]")

    # ──────── Summary tables ────────
    print("\n" + "=" * 100)

    for label, subset in [("08-10..21 (main)", {d: r for d, r in all_results.items() if str(d) >= "2026-08-10"}),
                          ("07-07..08-09 (IS)", {d: r for d, r in all_results.items() if str(d) < "2026-08-10"}),
                          ("ALL 34", all_results)]:
        if not subset:
            continue
        print(f"\n{label} ({len(subset)} sessions):")
        for lbl, key in [("BOOKS", "books_pnl"), ("L1-DETECTORS", "l1_pnl"),
                         ("L2-DALTON", "l2_pnl"), ("ORACLE", "oracle_pnl")]:
            vals = [r[key] for r in subset.values()]
            total = sum(vals)
            pos = sum(1 for v in vals if v > 0)
            med = statistics.median(vals) if vals else 0
            worst = min(vals) if vals else 0
            n_key = key.replace("_pnl", "_n")
            avg_trades = statistics.mean(r.get(n_key, 0) for r in subset.values()) if n_key != "oracle_n" else "-"
            print(f"  {lbl:15s}: ${total:>9.2f} | {pos}/{len(subset)} days+ | "
                  f"median ${med:>7.2f} | worst ${worst:>8.2f} | avg trades/day {avg_trades}")

    # ──────── Q2: location × pattern table ────────
    print("\n" + "=" * 100)
    print("LOCATION × PATTERN (L2 Dalton trades, sorted by $):")
    for lk, st in sorted(loc_pat_stats.items(), key=lambda x: -x[1]["pnl"]):
        wr = st["wins"] / max(st["n"], 1) * 100
        print(f"  {lk:45s}: n={st['n']:3d} win={wr:5.1f}% ${st['pnl']:>8.2f}")

    # ──────── Q2b: per-pattern with/without Dalton ────────
    print("\nPER-PATTERN (all vs Dalton-filtered):")
    for pat in sorted(pattern_stats, key=lambda p: -pattern_stats[p]["pnl"]):
        ps = pattern_stats[pat]
        if ps["n"] == 0:
            continue
        wr1 = ps["wins"] / max(ps["n"], 1) * 100
        wr2 = ps["dalton_wins"] / max(ps["dalton_n"], 1) * 100
        delta = ps["dalton_pnl"] - ps["pnl"]
        print(f"  {pat:25s}: ALL n={ps['n']:3d} wr={wr1:5.1f}% ${ps['pnl']:>8.2f} | "
              f"DALTON n={ps['dalton_n']:3d} wr={wr2:5.1f}% ${ps['dalton_pnl']:>8.2f} | "
              f"delta ${delta:>8.2f}")

    # ──────── Honesty ────────
    print("\n" + "=" * 100)
    print("LIMITATIONS:")
    print("  - Single-slot sim: first-come-first-served, no priority/quality ranking")
    print("  - Value area: uses end-of-day TPO VAH/VAL (not developing intra-day)")
    print("  - Fills at bar close, 1 tick slip. Real fills vary")
    print("  - T1 only (no T2/T3 trail). Real system has scaled exits")
    print("  - Dalton state uses classify_session per bar (expensive; ~2s/session)")

    # ──────── JSON ────────
    out = {
        "meta": {"contracts": C, "sessions": len(all_results)},
        "sessions": {str(d): r for d, r in all_results.items()},
        "pattern_stats": {p: dict(s) for p, s in pattern_stats.items()},
        "location_pattern": {lk: dict(s) for lk, s in loc_pat_stats.items()},
    }
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nJSON → {args.json}")


if __name__ == "__main__":
    main()
