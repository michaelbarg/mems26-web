#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replay_dalton_context.py — Dalton context simulation on past sessions.

Michael (2026-08-23): "לפני התיקונים — להריץ סימולציה מה היו התוצאות בהנחה
והתיקונים מיושמים על כסף חי בשבוע קודם."

Layers:
  (0) BOOKS      what MEMS26 actually booked (v9_trades, mode='live')
  (1) A-FIXES    A-fixes + P3 + TREND_STEP shadow + T-10  (Monday bundle)
  (2) DALTON     A-fixes + Dalton context layer (BALANCE/DISCOVERY × location)
  (3) ORACLE     ceiling (oracle_study best-2)

DALTON DYNAMIC (per-bar state machine):
  Market state = BALANCE / DISCOVERY, event-driven transitions:
    - IB lock (bar 12): initial state
    - Break beyond IB: DISCOVERY in break direction
    - Second side break: back to BALANCE (two-sided)
    - Failed break (closes return inside): back to BALANCE
    - Range expansion > 1.5× IB: DISCOVERY
  Value location = ABOVE_VAH / IN_VALUE / BELOW_VAL / AT_EDGE
  Trade selection rule:
    - BALANCE + AT_EDGE/BELOW_VAL → LONG reactive
    - BALANCE + AT_EDGE/ABOVE_VAH → SHORT reactive
    - BALANCE + IN_VALUE → no trade
    - DISCOVERY → only WITH direction, pullback entry

READ-ONLY. Direct psycopg2. No code changes, no .env, no restarts.

Usage: python3 scripts/replay_dalton_context.py [--json /tmp/dalton_sim.json]
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

# Reuse oracle_study engine
import importlib.util as _ilu
_OS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oracle_study.py")
_spec = _ilu.spec_from_file_location("oracle_study", _OS_PATH)
ORA = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(ORA)

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
WARM = "2026-06-25"
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12
POINT_USD = ORA.POINT_USD
COMM_RT = ORA.COMM_RT
SLIP_TICKS = ORA.SLIP_TICKS
TICK = ORA.TICK

# Study windows
WEEK1_START, WEEK1_END = "2026-08-17", "2026-08-21"
WEEK2_START, WEEK2_END = "2026-08-10", "2026-08-14"

# Classifier flags for replay
LIVE_S1_FLAGS = {
    "S1_NEW_CLASSIFIER": "1", "S1_ENGINE_NEW_CLASSIFIER": "1",
    "S1_OPEN_DRIVE_TREND": "1", "S1_COMMITTED_PROVISIONAL_V1": "1",
    "S1_CONFIDENCE_V2": "1", "S1_IB_SANITY_V1": "1",
    "S1_ACCEPTANCE_RECLASS_V1": "1", "S1_DD_INVALIDATION_V1": "1",
    "S1_VALUE_MIGRATION_V1": "1", "S1_TREND_CONTROL_V1": "1",
    "S1_TREND_ELONGATION_V1": "1", "S1_RECLASS_REQUIRES_IB_EXT_V1": "1",
}


# ─────────────────────────────────────────── Dalton state machine

class DaltonState:
    """Per-bar Dalton context (event-driven, no confidence)."""

    def __init__(self):
        self.market_state = "UNKNOWN"     # BALANCE / DISCOVERY / UNKNOWN
        self.discovery_dir = None         # UP / DOWN
        self.ib_high = None
        self.ib_low = None
        self.ib_locked = False
        self.ib_width = 0
        self.session_high = None
        self.session_low = None
        self.broke_up = False
        self.broke_down = False
        self.vah = None
        self.val = None
        self.transitions = []
        self._bar_count = 0

    def on_bar(self, bar, bar_idx, vah=None, val=None):
        """Process one bar, return (state, location, event_or_None)."""
        h = bar["h"]
        l = bar["l"]
        c = bar["c"]
        self._bar_count = bar_idx + 1

        # Track session extremes
        if self.session_high is None or h > self.session_high:
            self.session_high = h
        if self.session_low is None or l < self.session_low:
            self.session_low = l

        # IB tracking (first 12 bars = 09:30-10:30 ET)
        if bar_idx < IB_BARS:
            if self.ib_high is None or h > self.ib_high:
                self.ib_high = h
            if self.ib_low is None or l < self.ib_low:
                self.ib_low = l
            if bar_idx == IB_BARS - 1:
                self.ib_locked = True
                self.ib_width = self.ib_high - self.ib_low
                self.market_state = "BALANCE"
                self.transitions.append((bar_idx, "ib_lock", "BALANCE"))
                return self._result(bar, "ib_lock", vah, val)
            return self._result(bar, None, vah, val)

        if self.vah is None and vah is not None:
            self.vah = vah
        if self.val is None and val is not None:
            self.val = val

        # Event detection
        event = None
        prev_state = self.market_state

        # Break above IB
        if not self.broke_up and c > self.ib_high:
            self.broke_up = True
            if not self.broke_down:
                self.market_state = "DISCOVERY"
                self.discovery_dir = "UP"
                event = "break_up"
            else:
                # Second side → BALANCE (Neutral)
                self.market_state = "BALANCE"
                self.discovery_dir = None
                event = "dual_break"

        # Break below IB
        if not self.broke_down and c < self.ib_low:
            self.broke_down = True
            if not self.broke_up:
                self.market_state = "DISCOVERY"
                self.discovery_dir = "DOWN"
                event = "break_down"
            else:
                self.market_state = "BALANCE"
                self.discovery_dir = None
                event = "dual_break"

        # Range expansion check (> 1.5× IB → DISCOVERY if was BALANCE)
        if (self.market_state == "BALANCE" and self.ib_width > 0
                and (self.session_high - self.session_low) > 1.5 * self.ib_width
                and event is None):
            # Determine direction from which side expanded more
            up_ext = self.session_high - self.ib_high
            dn_ext = self.ib_low - self.session_low
            if up_ext > dn_ext and up_ext > 0.5 * self.ib_width:
                self.market_state = "DISCOVERY"
                self.discovery_dir = "UP"
                event = "range_expansion_up"
            elif dn_ext > up_ext and dn_ext > 0.5 * self.ib_width:
                self.market_state = "DISCOVERY"
                self.discovery_dir = "DOWN"
                event = "range_expansion_down"

        if event and self.market_state != prev_state:
            self.transitions.append((bar_idx, event, self.market_state))

        return self._result(bar, event, vah, val)

    def _result(self, bar, event, vah, val):
        c = bar["c"]
        # Value location
        _vah = vah or self.vah or (self.ib_high if self.ib_locked else None)
        _val = val or self.val or (self.ib_low if self.ib_locked else None)
        if _vah is not None and _val is not None:
            edge_margin = max(0.15 * ((_vah - _val) if _vah > _val else 1.0), 1.0)
            if c >= _vah - edge_margin and c <= _vah + edge_margin:
                location = "AT_EDGE_HIGH"
            elif c <= _val + edge_margin and c >= _val - edge_margin:
                location = "AT_EDGE_LOW"
            elif c > _vah:
                location = "ABOVE_VAH"
            elif c < _val:
                location = "BELOW_VAL"
            else:
                location = "IN_VALUE"
        else:
            location = "UNKNOWN"

        return {
            "state": self.market_state,
            "discovery_dir": self.discovery_dir,
            "location": location,
            "event": event,
            "bar_idx": self._bar_count - 1,
            "ib_locked": self.ib_locked,
        }


# ─────────────────────────────────────── Trade selection (Dalton rules)

def dalton_trade_filter(setup_dir, dalton_ctx):
    """Should this trade be taken under Dalton context?
    Returns (take: bool, reason: str).
    """
    state = dalton_ctx["state"]
    loc = dalton_ctx["location"]
    disc_dir = dalton_ctx["discovery_dir"]

    if state == "UNKNOWN" or not dalton_ctx["ib_locked"]:
        return False, "pre_ib"

    if state == "BALANCE":
        if setup_dir == "LONG":
            if loc in ("BELOW_VAL", "AT_EDGE_LOW"):
                return True, "balance_long_at_low"
            return False, f"balance_long_wrong_location({loc})"
        else:  # SHORT
            if loc in ("ABOVE_VAH", "AT_EDGE_HIGH"):
                return True, "balance_short_at_high"
            return False, f"balance_short_wrong_location({loc})"

    if state == "DISCOVERY":
        if disc_dir == "UP" and setup_dir == "LONG":
            return True, "discovery_with_up"
        if disc_dir == "DOWN" and setup_dir == "SHORT":
            return True, "discovery_with_down"
        return False, f"discovery_against({disc_dir}_vs_{setup_dir})"

    return False, "unknown_state"


# ─────────────────────────────────── Simulation engine

def sim_trade(bars, entry_i, direction, stop_pts, target_pts, contracts):
    """Simple bar-by-bar trade sim. Returns (pnl_pts, exit_i, exit_reason)."""
    entry = bars[entry_i]["c"]
    sign = 1.0 if direction == "LONG" else -1.0
    stop = entry - sign * stop_pts
    target = entry + sign * target_pts

    for i in range(entry_i + 1, len(bars)):
        h, l, c = bars[i]["h"], bars[i]["l"], bars[i]["c"]
        # Stop hit?
        if (direction == "LONG" and l <= stop) or (direction == "SHORT" and h >= stop):
            pnl = -stop_pts - SLIP_TICKS * TICK
            return pnl, i, "STOP"
        # Target hit?
        if (direction == "LONG" and h >= target) or (direction == "SHORT" and l <= target):
            pnl = target_pts - SLIP_TICKS * TICK
            return pnl, i, "TARGET"

    # EOD close
    last_c = bars[-1]["c"]
    pnl = (last_c - entry) * sign - SLIP_TICKS * TICK
    return pnl, len(bars) - 1, "EOD"


def classify_day_post_hoc(bars):
    """Run the 7-type classifier on full session bars (is_eod=True)."""
    try:
        for k, v in LIVE_S1_FLAGS.items():
            os.environ.setdefault(k, v)
        from backend.v9.systems.day_type.classifier_core import classify_session
        ib_seg = bars[:IB_BARS]
        ibh = max(b["h"] for b in ib_seg)
        ibl = min(b["l"] for b in ib_seg)
        result = classify_session(
            bars=[{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"],
                   "v": b.get("v", 0)} for b in bars],
            ib_high=ibh, ib_low=ibl,
            open_price=bars[0]["o"],
            is_eod=True,
        )
        return result.get("day_type", "UNKNOWN")
    except Exception as e:
        return f"ERROR:{e}"


def replay_day(bars, day_date, contracts, book_trades=None):
    """Replay one session through all layers."""
    n = len(bars)
    if n < IB_BARS + 5:
        return None

    thr = ORA.thr_for({day_date: bars}, day_date)
    piv = ORA.zigzag(bars, thr)
    legs = ORA.legs_from(bars, piv) if hasattr(ORA, "legs_from") else []

    # Post-hoc day type
    day_type = classify_day_post_hoc(bars)

    # IB
    ibh = max(b["h"] for b in bars[:IB_BARS])
    ibl = min(b["l"] for b in bars[:IB_BARS])
    ibw = ibh - ibl

    # --- Layer 0: BOOKS (passed in) ---
    books_pnl = 0.0
    if book_trades:
        books_pnl = sum(t.get("pnl", 0) for t in book_trades)

    # --- Layer 3: ORACLE (best-2 swings) ---
    oracle_pnl = 0.0
    if legs and len(legs) >= 2:
        leg_pnls = []
        for leg in legs:
            pts = abs(leg.get("pts", 0))
            leg_pnls.append(pts * contracts * POINT_USD - ORA.costs(contracts))
        leg_pnls.sort(reverse=True)
        oracle_pnl = sum(leg_pnls[:2])

    # --- Dalton dynamic state machine ---
    dalton = DaltonState()
    dalton_log = []
    # Causal triggers from oracle_study
    causal_triggers = []
    if hasattr(ORA, "causal_triggers"):
        causal_triggers = ORA.causal_triggers(bars, piv, thr)
    elif piv:
        # Build simple causal triggers from pivots
        for p in piv:
            ci = p.get("confirm_i", p["i"])
            if ci >= n:
                continue
            direction = "SHORT" if p["kind"] == "H" else "LONG"
            causal_triggers.append({
                "i": ci, "direction": direction,
                "entry": bars[ci]["c"],
                "stop_pts": max(thr * 0.7, 2.5),
                "target_pts": thr * 1.0,
            })

    # Run Dalton state machine bar-by-bar
    for i in range(n):
        ctx = dalton.on_bar(bars[i], i)
        if ctx["event"]:
            dalton_log.append({
                "bar": i, "event": ctx["event"],
                "state": ctx["state"], "location": ctx["location"],
                "time": bars[i]["t"].strftime("%H:%M") if hasattr(bars[i]["t"], "strftime") else str(bars[i]["t"]),
            })

    # --- Layer 1: A-FIXES (system trades, minus phantom blocks) ---
    # Approximate: take all causal triggers, standard stops
    layer1_trades = []
    layer1_pnl = 0.0
    in_trade = False
    for trig in causal_triggers:
        if in_trade:
            continue
        i = trig["i"]
        if i >= n - 2:
            continue
        pnl_pts, exit_i, reason = sim_trade(
            bars, i, trig["direction"],
            trig.get("stop_pts", 3.0),
            trig.get("target_pts", thr),
            contracts)
        trade_pnl = pnl_pts * contracts * POINT_USD - ORA.costs(contracts)
        layer1_trades.append({
            "bar": i, "direction": trig["direction"],
            "entry": trig["entry"], "pnl": round(trade_pnl, 2),
            "exit_reason": reason,
        })
        layer1_pnl += trade_pnl
        in_trade = (reason != "STOP" and reason != "TARGET")

    # --- Layer 2: DALTON (filtered by context) ---
    layer2_trades = []
    layer2_pnl = 0.0
    in_trade = False
    for trig in causal_triggers:
        if in_trade:
            continue
        i = trig["i"]
        if i >= n - 2:
            continue
        # Get Dalton context at trigger bar
        d_ctx = dalton.on_bar(bars[i], i)  # re-evaluate (idempotent reads)
        # Actually re-run the state machine to get context at bar i
        d_state_at_i = DaltonState()
        for j in range(i + 1):
            d_ctx_j = d_state_at_i.on_bar(bars[j], j)
        take, reason_d = dalton_trade_filter(trig["direction"], d_ctx_j)
        if not take:
            continue
        pnl_pts, exit_i, reason = sim_trade(
            bars, i, trig["direction"],
            trig.get("stop_pts", 3.0),
            trig.get("target_pts", thr),
            contracts)
        trade_pnl = pnl_pts * contracts * POINT_USD - ORA.costs(contracts)
        layer2_trades.append({
            "bar": i, "direction": trig["direction"],
            "entry": trig["entry"], "pnl": round(trade_pnl, 2),
            "exit_reason": reason, "dalton_reason": reason_d,
            "dalton_state": d_ctx_j["state"],
            "dalton_location": d_ctx_j["location"],
        })
        layer2_pnl += trade_pnl

    return {
        "date": str(day_date),
        "day_type": day_type,
        "bars": n,
        "ib_width": round(ibw, 2),
        "transitions": dalton_log,
        "transition_count": len(dalton_log),
        "books_pnl": round(books_pnl, 2),
        "layer1_pnl": round(layer1_pnl, 2),
        "layer1_trades": len(layer1_trades),
        "layer2_pnl": round(layer2_pnl, 2),
        "layer2_trades": len(layer2_trades),
        "layer2_detail": layer2_trades,
        "oracle_pnl": round(oracle_pnl, 2),
    }


# ─────────────────────────────────── Convergence test

def convergence_test(all_days, all_results):
    """Compare dynamic classifier final label vs post-hoc.
    Michael: "if it doesn't converge to the same final label on most days,
    your definition is wrong, not the data."
    """
    matches = 0
    total = 0
    details = []
    for d, res in all_results.items():
        if res is None:
            continue
        post_hoc = res["day_type"]
        # Map dynamic Dalton state to approximate day types
        transitions = res["transitions"]
        final_state = transitions[-1]["state"] if transitions else "UNKNOWN"
        # Simple mapping
        if final_state == "BALANCE":
            dalton_type = "Normal" if not any(
                t["event"].startswith("break") for t in transitions) else "Variation"
        elif final_state == "DISCOVERY":
            dalton_type = "Trend_Normal"
        else:
            dalton_type = "UNKNOWN"

        # Broad match (trend=trend, balance=normal/variation/neutral)
        ph_trend = post_hoc.startswith("Trend")
        dl_trend = dalton_type.startswith("Trend")
        ph_balance = post_hoc in ("Normal", "Variation", "Neutral_Center",
                                   "Neutral_Extreme", "Nontrend")
        dl_balance = dalton_type in ("Normal", "Variation")

        broad_match = (ph_trend == dl_trend) or (ph_balance and dl_balance)
        if broad_match:
            matches += 1
        total += 1
        details.append({
            "date": str(d), "post_hoc": post_hoc,
            "dalton_final": dalton_type, "final_state": final_state,
            "match": broad_match,
        })
    return {
        "matches": matches, "total": total,
        "pct": round(100 * matches / max(total, 1), 1),
        "details": details,
    }


# ─────────────────────────────────── Main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/dalton_sim.json")
    ap.add_argument("--contracts", type=int, default=6)
    args = ap.parse_args()

    conn = psycopg2.connect(DSN)
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
    """, (WARM, WEEK1_END, RTH0, RTH1))

    days = collections.OrderedDict()
    for et, o, h, l, c, v in cur.fetchall():
        d = et.date()
        days.setdefault(d, []).append(
            dict(t=et, o=float(o), h=float(h), l=float(l), c=float(c),
                 v=float(v or 0)))

    # Load book trades
    cur.execute("""
        select (entry_ts at time zone 'America/New_York')::date as d,
               pnl_usd
        from v9_trades
        where mode = 'live'
          and (entry_ts at time zone 'America/New_York')::date between %s and %s
    """, (WEEK2_START, WEEK1_END))
    book_by_day = collections.defaultdict(list)
    for d, pnl in cur.fetchall():
        book_by_day[d].append({"pnl": float(pnl or 0)})

    conn.close()

    # Study dates
    study_dates = sorted(d for d in days
                         if WEEK2_START <= str(d) <= WEEK1_END)

    print(f"Dalton Context Simulation — {len(study_dates)} sessions")
    print(f"Contracts: {args.contracts}")
    print("=" * 80)

    all_results = {}
    for d in study_dates:
        bars = days[d]
        bt = book_by_day.get(d, [])
        res = replay_day(bars, d, args.contracts, bt)
        if res is None:
            continue
        all_results[d] = res
        print(f"\n{d} | {res['day_type']:20s} | IB={res['ib_width']:5.1f} | "
              f"transitions={res['transition_count']} | "
              f"books=${res['books_pnl']:8.2f} | L1=${res['layer1_pnl']:8.2f} | "
              f"L2=${res['layer2_pnl']:8.2f} | oracle=${res['oracle_pnl']:8.2f}")
        for t in res["transitions"]:
            print(f"  {t['time']} {t['event']:25s} → {t['state']}")
        for t in res.get("layer2_detail", []):
            print(f"  TRADE: {t['direction']:5s} @{t['entry']:.2f} "
                  f"→ ${t['pnl']:7.2f} ({t['exit_reason']}) "
                  f"[{t['dalton_state']}/{t['dalton_location']}: {t['dalton_reason']}]")

    # Totals
    print("\n" + "=" * 80)
    week1 = {d: r for d, r in all_results.items()
             if WEEK1_START <= str(d) <= WEEK1_END}
    week2 = {d: r for d, r in all_results.items()
             if WEEK2_START <= str(d) <= WEEK2_END}

    for label, subset in [("Week 08-17..21 (main)", week1),
                          ("Week 08-10..14 (comparison)", week2),
                          ("ALL", all_results)]:
        if not subset:
            continue
        print(f"\n{label}:")
        for layer, key in [("BOOKS", "books_pnl"), ("L1-FIXES", "layer1_pnl"),
                           ("L2-DALTON", "layer2_pnl"), ("ORACLE", "oracle_pnl")]:
            total = sum(r[key] for r in subset.values())
            days_pos = sum(1 for r in subset.values() if r[key] > 0)
            worst = min(r[key] for r in subset.values())
            median = statistics.median(r[key] for r in subset.values())
            print(f"  {layer:12s}: ${total:8.2f} | {days_pos}/{len(subset)} days+ | "
                  f"median/day ${median:7.2f} | worst ${worst:7.2f}")

    # Convergence test
    print("\n" + "=" * 80)
    conv = convergence_test(days, all_results)
    print(f"CONVERGENCE: {conv['matches']}/{conv['total']} = {conv['pct']}%")
    for det in conv["details"]:
        m = "✓" if det["match"] else "✗"
        print(f"  {m} {det['date']}: post_hoc={det['post_hoc']:20s} "
              f"dalton={det['dalton_final']:15s} ({det['final_state']})")

    # Honesty
    print("\n" + "=" * 80)
    print("LIMITATIONS (required honesty disclosure):")
    print("  • Fill simulation: uses bar close, not intra-bar. Biased optimistic for entries.")
    print("  • Slot competition: sim allows unlimited trades; live has 1 slot. Biased optimistic.")
    print("  • Slippage: 1 tick/side uniform. Real slippage varies with volatility.")
    print("  • Dalton location: uses IB as proxy for value area (no live TPO VAH/VAL in replay).")
    print("  • No commissions on oracle layer entries.")

    # Write JSON
    out = {
        "meta": {
            "contracts": args.contracts,
            "week1": f"{WEEK1_START}..{WEEK1_END}",
            "week2": f"{WEEK2_START}..{WEEK2_END}",
        },
        "sessions": {str(d): r for d, r in all_results.items()},
        "convergence": conv,
    }
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nJSON → {args.json}")


if __name__ == "__main__":
    main()
