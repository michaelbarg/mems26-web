#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""replay_f5_runner_trail.py — what RUNNER_TRAIL_V2 (F5) would have produced.

Michael 2026-08-20, after ORACLE_STUDY_2026-08-20 §5 R-A.

WHAT IS MEASURED
----------------
Every live-era closed trade is replayed TWICE on its own session's real 5-min
bars, from its REAL entry price, REAL initial stop, REAL targets and REAL size.
The two arms differ in exactly one thing:

  ARM-A  (baseline)  every tranche exits at its fixed OCO target; stop -> BE+1T
                     after the T1 leg fills; a stop takes out whatever is left.
  ARM-B  (F5)        identical, except the LAST tranche carries NO target and is
                     taken out by the structural swing trail
                     (backend/v9/services/trade_manager/swing_trail.py — the same
                     module the live code calls, so this cannot drift from it).

ARM-B - ARM-A is therefore the F5 delta and nothing else: same entries, same
stops, same banked legs, same day. No hindsight — the trail only ever uses
CONFIRMED pivots, and the swing threshold comes from the PREVIOUS session's ATR.

ENGINE
------
Bars and trades come from scripts/oracle_study.py (load_bars / load_trades), the
engine that measured the +$2,315 — imported, not re-implemented.

READ-ONLY. Direct psycopg2. Writes stdout (+ --json).

Usage:
    python3 scripts/replay_f5_runner_trail.py [--json /tmp/f5_replay.json]
                                              [--size N] [--min-contracts N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.v9.services.trade_manager.swing_trail import (  # noqa: E402
    swing_rev_threshold, swing_trail_stop,
)


def _load_oracle():
    """Import scripts/oracle_study.py by path (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "oracle_study", os.path.join(ROOT, "scripts", "oracle_study.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


OR = _load_oracle()

POINT_USD = OR.POINT_USD      # $5 / point / contract (MES)
TICK = OR.TICK
COMM_RT = OR.COMM_RT          # $1.50 / contract round turn
SLIP_TICKS = OR.SLIP_TICKS    # 1 tick, charged on STOP fills only (limits fill at price)
EOD_ET = dt.time(15, 55)


# ── the DLL's ladder (MES_AI_DataExport_merged.cpp:2901-2907) ──────────────
def ladder(contracts: int):
    """Per-OCO-group quantities, exactly as the deployed DLL builds them."""
    c = int(contracts)
    if c >= 6:
        return [1, 2, 2, 1]        # Michael ruling 2026-08-16
    if c == 5:
        return [1, 2, 1, 1]
    if c == 4:
        return [1, 1, 1, 1]
    if c == 3:
        return [1, 1, 1]
    if c == 2:
        return [1, 1]
    return [1]


def tranche_targets(tr, n_groups: int):
    """Targets per group as command_from_setup wires them.

    With the T0 shift live (T0_TARGET_PTS=3.0, contracts>=4) the ladder walks out
    one leg: C1->T0, C2->T1, C3->T2, C4->T3(runner). Below 4 contracts there is no
    T0 leg: C1->T1, C2->T2, C3->T3.
    """
    if n_groups >= 4:
        return [tr.get("t0"), tr.get("t1"), tr.get("t2"), tr.get("t3")][:n_groups]
    return [tr.get("t1"), tr.get("t2"), tr.get("t3")][:n_groups]


def be_trigger_index(n_groups: int) -> int:
    """Which group's fill is 'T1 hit' (the BE / trail trigger) — the T1 leg."""
    return 1 if n_groups >= 4 else 0


def simulate(bars, i0, dirn, entry, stop0, targets, qtys, *,
             runner_stop_only, rev, offset_ticks=1, trail_legs=1):
    """One trade, bar by bar, from bar index i0 (the first FULL bar after entry).

    Conventions (both arms identical so the delta is clean):
      * within a bar the STOP is checked FIRST (conservative);
      * a target fills at its exact price (resting limit, no slippage);
      * a stop fills 1 tick beyond (adverse);
      * BE+1T after the T1 leg fills;
      * F5 only: from that same moment the stop also trails the last CONFIRMED
        swing, never widening, floored at BE+1T; the last tranche has no target
        and therefore leaves only by stop/trail/EOD.
    """
    n = len(bars)
    tick = TICK
    left = list(qtys)
    tg = list(targets)
    if runner_stop_only:
        # the last `trail_legs` tranches carry no fixed target (never the T0/T1 legs)
        for _j in range(1, min(int(trail_legs), max(1, len(tg) - 1)) + 1):
            tg[-_j] = None
    stop = stop0
    be = entry + dirn * tick
    be_idx = be_trigger_index(len(qtys))
    banked_pts = 0.0
    legs = []
    trailed = False

    for k in range(i0, n):
        b = bars[k]
        # 1. stop (adverse first)
        if (dirn > 0 and b["l"] <= stop) or (dirn < 0 and b["h"] >= stop):
            fill = stop - dirn * SLIP_TICKS * tick
            for gi, q in enumerate(left):
                if q:
                    banked_pts += q * dirn * (fill - entry)
                    legs.append((gi, "STOP", round(fill, 2), q))
                    left[gi] = 0
            break
        # 2. targets
        for gi, q in enumerate(left):
            if not q or tg[gi] is None:
                continue
            t = float(tg[gi])
            if (dirn > 0 and b["h"] >= t) or (dirn < 0 and b["l"] <= t):
                banked_pts += q * dirn * (t - entry)
                legs.append((gi, "T%d" % gi, round(t, 2), q))
                left[gi] = 0
                if gi >= be_idx:
                    nb = be if dirn > 0 else be
                    if (dirn > 0 and nb > stop) or (dirn < 0 and nb < stop):
                        stop = nb
        if not any(left):
            break
        # 3. F5 trail — only once the T1 leg has banked (runner-only), on CLOSED bars
        if runner_stop_only and not any(left[:be_idx + 1]):
            anchor = swing_trail_stop(bars[:k + 1],
                                      "LONG" if dirn > 0 else "SHORT",
                                      rev=rev, offset_ticks=offset_ticks)
            if anchor is not None:
                cand = max(anchor, be) if dirn > 0 else min(anchor, be)
                if (dirn > 0 and cand > stop) or (dirn < 0 and cand < stop):
                    stop = round(cand, 2)
                    trailed = True
        # 4. EOD (EOD_FLATTEN_V1 sends CANCEL at RTH close)
        if b["t"].time() >= EOD_ET and any(left):
            fill = b["c"] - dirn * SLIP_TICKS * tick
            for gi, q in enumerate(left):
                if q:
                    banked_pts += q * dirn * (fill - entry)
                    legs.append((gi, "EOD", round(fill, 2), q))
                    left[gi] = 0
            break

    if any(left):                       # session data ended early (feed gap)
        fill = bars[-1]["c"] - dirn * SLIP_TICKS * tick
        for gi, q in enumerate(left):
            if q:
                banked_pts += q * dirn * (fill - entry)
                legs.append((gi, "EOD", round(fill, 2), q))
                left[gi] = 0

    total = sum(qtys)
    return dict(usd=round(banked_pts * POINT_USD - COMM_RT * total, 2),
                pts=round(banked_pts, 2), legs=legs, trailed=trailed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--size", type=int, default=0,
                    help="force every trade to N contracts (0 = the size actually traded)")
    ap.add_argument("--min-contracts", type=int, default=3,
                    help="RUNNER_TRAIL_V2_MIN_CONTRACTS (default 3)")
    ap.add_argument("--trail-legs", type=int, default=1,
                    help="how many tranches from the end trail instead of taking a "
                         "fixed target (1 = F5 as built; >1 = what a wider ruling "
                         "would be worth — measurement only, NOT what ships)")
    args = ap.parse_args()

    conn = psycopg2.connect(os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26"))
    cur = conn.cursor()
    days = OR.load_bars(cur)

    cur.execute("""
        select id, (entry_ts at time zone 'America/New_York'), direction,
               entry_price, stop, t1, t2, t3, t4, pnl_usd, exit_reason, quality,
               pattern_id_at_entry, firing_system
        from v9_trades
        where mode='live' and state='CLOSED' and entry_ts is not null
          and (entry_ts at time zone 'America/New_York')::date between %s and %s
        order by entry_ts
    """, (OR.D0, OR.D1))
    rows = cur.fetchall()
    conn.close()

    tot_a = tot_b = tot_books = 0.0
    n_used = n_skip = n_changed = 0
    per_day = {}
    detail = []
    skips = {}

    for (tid, ein, d, ep, st, t1, t2, t3, t4, pnl, xr, q, pat, sysn) in rows:
        tot_books += float(pnl or 0)
        q = q or {}
        day = ein.date()
        bars = days.get(day)
        if not bars or ep is None:
            skips["no_bars"] = skips.get("no_bars", 0) + 1
            n_skip += 1
            continue

        # size: the books' contracts, else the ruled default; --size overrides
        try:
            contracts = int(args.size or q.get("contracts") or 0)
        except (TypeError, ValueError):
            contracts = 0
        if contracts <= 0:
            skips["no_size"] = skips.get("no_size", 0) + 1
            n_skip += 1
            continue

        stop0 = q.get("initial_stop", st)
        if stop0 is None:
            skips["no_stop"] = skips.get("no_stop", 0) + 1
            n_skip += 1
            continue
        stop0 = float(stop0)
        entry = float(ep)
        dirn = 1 if str(d).upper() == "LONG" else -1
        if (dirn > 0 and stop0 >= entry) or (dirn < 0 and stop0 <= entry):
            skips["stop_wrong_side"] = skips.get("stop_wrong_side", 0) + 1
            n_skip += 1
            continue

        # first FULL bar after the entry (no intrabar hindsight)
        i0 = next((i for i, b in enumerate(bars) if b["t"] > ein), None)
        if i0 is None:
            skips["entry_after_last_bar"] = skips.get("entry_after_last_bar", 0) + 1
            n_skip += 1
            continue

        rev = swing_rev_threshold(days.get(max([k for k in days if k < day], default=None)))
        if rev is None:
            skips["no_prev_atr"] = skips.get("no_prev_atr", 0) + 1
            n_skip += 1
            continue

        qtys = ladder(contracts)
        tr = dict(t0=q.get("t0"), t1=t1, t2=t2, t3=t3, t4=t4)
        if len(qtys) >= 4 and tr["t0"] is None:
            # the T0 leg price is not always journalled; reconstruct the ruled offset
            _t0p = float(os.getenv("T0_TARGET_PTS", "3.0") or 3.0)
            tr["t0"] = round(round((entry + dirn * _t0p) / TICK) * TICK, 2)
        tgts = tranche_targets(tr, len(qtys))
        if tgts[0] is None:
            skips["no_first_target"] = skips.get("no_first_target", 0) + 1
            n_skip += 1
            continue
        # At the size actually traded a missing target is a REAL historical shape
        # (that leg went out stop-only) and is kept. Under a FORCED --size it is
        # not: the record simply never carried that many legs, and pretending the
        # leg was intentionally target-less hands ARM-A a free EOD ride it never
        # had. Extrapolating the missing target would be synthesis (Rule 1), so
        # the trade is skipped instead.
        if args.size and any(t is None for t in tgts):
            skips["incomplete_ladder_at_forced_size"] = \
                skips.get("incomplete_ladder_at_forced_size", 0) + 1
            n_skip += 1
            continue

        eligible = (contracts >= max(2, args.min_contracts)
                    and str(pat or "").upper() != "ZLR"
                    and str(q.get("classification") or "").upper() != "ZLR")

        a = simulate(bars, i0, dirn, entry, stop0, tgts, qtys,
                     runner_stop_only=False, rev=rev)
        b = simulate(bars, i0, dirn, entry, stop0, tgts, qtys,
                     runner_stop_only=eligible, rev=rev, trail_legs=args.trail_legs)
        n_used += 1
        if a["usd"] != b["usd"]:
            n_changed += 1
        tot_a += a["usd"]
        tot_b += b["usd"]
        pd = per_day.setdefault(str(day), dict(a=0.0, b=0.0, books=0.0, n=0))
        pd["a"] += a["usd"]; pd["b"] += b["usd"]
        pd["books"] += float(pnl or 0); pd["n"] += 1
        detail.append(dict(id=tid, day=str(day), dir=d, pat=pat, c=contracts,
                           books=float(pnl or 0), base=a["usd"], f5=b["usd"],
                           delta=round(b["usd"] - a["usd"], 2), rev=rev,
                           eligible=eligible, trailed=b["trailed"],
                           base_legs=a["legs"], f5_legs=b["legs"]))

    print(f"F5 REPLAY  size={args.size or 'as-traded'}  "
          f"min_contracts={args.min_contracts}  trail_legs={args.trail_legs}")
    print(f"  trades replayed n={n_used}   skipped={n_skip} {skips}")
    print(f"  BOOKS (all live rows incl. skipped)          {tot_books:+10.2f}")
    print(f"  ARM-A  baseline (fixed ladder, simulated)    {tot_a:+10.2f}")
    print(f"  ARM-B  F5 (runner stop-only + swing trail)   {tot_b:+10.2f}")
    print(f"  DELTA  ARM-B - ARM-A                         {tot_b - tot_a:+10.2f}"
          f"   ({n_changed} trades changed)")
    print()
    print("  day        n   books      base       f5      delta")
    for dstr in sorted(per_day):
        v = per_day[dstr]
        print(f"  {dstr}  {v['n']:3d} {v['books']:+9.2f} {v['a']:+9.2f} "
              f"{v['b']:+9.2f} {v['b']-v['a']:+9.2f}")
    tops = sorted(detail, key=lambda x: -abs(x["delta"]))[:12]
    print("\n  largest movers")
    for t in tops:
        if not t["delta"]:
            continue
        print(f"    #{t['id']} {t['day']} {t['dir']:5s} {t['c']}c {t['pat'] or '-':<16s} "
              f"books {t['books']:+8.2f} base {t['base']:+8.2f} f5 {t['f5']:+8.2f} "
              f"delta {t['delta']:+8.2f}")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(dict(n=n_used, skipped=n_skip, skips=skips, books=tot_books,
                           arm_a=tot_a, arm_b=tot_b, delta=tot_b - tot_a,
                           per_day=per_day, detail=detail), fh, indent=1, default=str)
        print(f"\n  json -> {args.json}")


if __name__ == "__main__":
    main()
