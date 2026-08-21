#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""replay_target_spacing.py — what TARGET_MIN_SPACING_V1 would have done.

Michael 2026-08-21 ~11:30 IL: "לבנות ולהפעיל בשדואו ולבדוק איך זה פותר".

WHAT IS MEASURED
----------------
Every live-era closed trade is replayed TWICE on its own session's real 5-min
bars, from its REAL entry, REAL initial stop, REAL ladder and REAL size. The two
arms differ in exactly one thing:

  ARM-A  (books)    the ladder as it was actually placed.
  ARM-B  (spacing)  the same ladder after `target_spacing.enforce_spacing`
                    — legs that violate min_gap = max(k×ATR14, m×risk) are
                    PUSHed to a real level or DROPped; a dropped leg carries no
                    target and rides on (stop / trail / EOD), exactly as the
                    DLL treats tN=0.

ENGINES — NOT RE-IMPLEMENTED
----------------------------
Bars come from `scripts/oracle_study.load_bars`; the bar-by-bar trade simulator,
the DLL ladder split and the tranche→target mapping are imported from
`scripts/replay_f5_runner_trail` (the engine that measured F5's +$538.75). The
spacing rule itself is imported from the SHIPPING module
`backend/v9/systems/target_spacing.py`, so the replay cannot drift from live.

CAUSALITY
---------
ATR14 is computed from the 14 bars strictly BEFORE the entry bar. The IB edges
offered as PUSH candidates come from 09:30–10:30 ET of the same session and are
only offered to entries after 10:30. No look-ahead anywhere.

READ-ONLY. Writes stdout (+ --json, --md).

Usage:
    python3 scripts/replay_target_spacing.py [--mode live|shadow|all]
                                             [--trail] [--json P] [--md P]
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import importlib.util
import json
import os
import statistics
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)                      # target_spacing reads config/targets.yaml

from backend.v9.systems import target_spacing as TSP   # noqa: E402
from backend.v9.services.trade_manager.swing_trail import (  # noqa: E402
    swing_rev_threshold,
)

D_END = "2026-08-20"                # include #756's session


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


OR = _load("oracle_study", "scripts/oracle_study.py")
OR.D1 = D_END                       # extend the window to 08-20
F5 = _load("replay_f5_runner_trail", "scripts/replay_f5_runner_trail.py")

POINT_USD = OR.POINT_USD
TICK = OR.TICK


def atr14_before(bars, i0):
    """Mean TR of the 14 bars strictly before index i0 — causal by construction."""
    win = bars[max(0, i0 - 15):i0]
    if len(win) < 6:
        return 0.0
    trs, prev = [], None
    for b in win:
        trs.append(b["h"] - b["l"] if prev is None
                   else max(b["h"] - b["l"], abs(b["h"] - prev), abs(b["l"] - prev)))
        prev = b["c"]
    return sum(trs) / len(trs) if trs else 0.0


def ib_edges(bars, entry_time):
    """Session IB (09:30–10:30 ET) — a real structural level, offered only once
    it is locked (i.e. to entries after 10:30), never before."""
    if entry_time.time() < dt.time(10, 30):
        return None, None
    ib = [b for b in bars if dt.time(9, 30) <= b["t"].time() < dt.time(10, 30)]
    if not ib:
        return None, None
    return max(b["h"] for b in ib), min(b["l"] for b in ib)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="live", choices=["live", "shadow", "all"])
    ap.add_argument("--trail", action="store_true",
                    help="run both arms under the F5 swing trail (today's live "
                         "management) instead of a pure fixed ladder")
    ap.add_argument("--json")
    ap.add_argument("--md")
    args = ap.parse_args()

    conn = psycopg2.connect(os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26"))
    cur = conn.cursor()
    days = OR.load_bars(cur)

    modes = ("live", "shadow") if args.mode == "all" else (args.mode,)
    cur.execute("""
        select id, (entry_ts at time zone 'America/New_York'), direction,
               entry_price, stop, t1, t2, t3, t4, pnl_usd, pnl_sierra,
               exit_reason, quality, pattern_id_at_entry, day_type_at_entry, mode
        from v9_trades
        where mode = any(%s) and state='CLOSED' and entry_ts is not null
          and (entry_ts at time zone 'America/New_York')::date between %s and %s
        order by entry_ts
    """, (list(modes), OR.D0, D_END))
    rows = cur.fetchall()
    conn.close()

    cfg = TSP.load_cfg()
    tot_a = tot_b = 0.0
    tot_books = tot_sierra = 0.0
    n_used = n_skip = n_violate = n_changed_pnl = 0
    n_drop = n_push = 0
    per_day = {}
    detail = []
    skips = collections.Counter()

    for (tid, ein, d, ep, st, t1, t2, t3, t4, pnl, psier, xr, q, pat, dtyp, md) in rows:
        q = q or {}
        day = ein.date()
        bars = days.get(day)
        if not bars or ep is None or st is None:
            skips["no_bars_or_prices"] += 1
            n_skip += 1
            continue
        try:
            contracts = int(q.get("contracts") or 0)
        except (TypeError, ValueError):
            contracts = 0
        if contracts <= 0:
            skips["no_size"] += 1
            n_skip += 1
            continue
        stop0 = float(q.get("initial_stop", st))
        entry = float(ep)
        dirn = 1 if str(d).upper() == "LONG" else -1
        if (dirn > 0 and stop0 >= entry) or (dirn < 0 and stop0 <= entry):
            skips["stop_wrong_side"] += 1
            n_skip += 1
            continue
        i0 = next((i for i, b in enumerate(bars) if b["t"] > ein), None)
        if i0 is None:
            skips["entry_after_last_bar"] += 1
            n_skip += 1
            continue

        risk = abs(entry - stop0)
        atr = atr14_before(bars, i0)
        ibh, ibl = ib_edges(bars, ein)

        # ── the spacing rule, from the shipping module ────────────────────
        cands = TSP.build_candidates(
            entry=entry, risk=risk,
            tpo_ctx={"ib_high": ibh, "ib_low": ibl},
            producer_levels=[("t4", t4)], cfg=cfg)
        rec = TSP.enforce_spacing(
            direction=str(d).upper(), entry=entry, t1=t1, t2=t2, t3=t3,
            risk=risk, atr14=atr, candidates=cands, cfg=cfg)

        branches = {b["leg"]: b["branch"] for b in rec["branches"]}
        violated = rec.get("changed", False)
        if violated:
            n_violate += 1
            n_drop += sum(1 for v in branches.values() if v == "DROP")
            n_push += sum(1 for v in branches.values() if v == "PUSH")

        # ── both arms, identical in everything else ──────────────────────
        qtys = F5.ladder(contracts)
        rev = swing_rev_threshold(days.get(max([k for k in days if k < day], default=None)))
        if args.trail and rev is None:
            skips["no_prev_atr"] += 1
            n_skip += 1
            continue

        def _tgts(_t1, _t2, _t3):
            tr = dict(t0=q.get("t0"), t1=_t1, t2=_t2, t3=_t3, t4=t4)
            if len(qtys) >= 4 and tr["t0"] is None:
                _p = float(os.getenv("T0_TARGET_PTS", "3.0") or 3.0)
                tr["t0"] = round(round((entry + dirn * _p) / TICK) * TICK, 2)
            return F5.tranche_targets(tr, len(qtys))

        tg_a = _tgts(t1, t2, t3)
        af = rec["after"]
        tg_b = _tgts(af.get("t1"), af.get("t2"), af.get("t3"))
        if tg_a[0] is None:
            skips["no_first_target"] += 1
            n_skip += 1
            continue

        eligible = args.trail and str(pat or "").upper() != "ZLR"
        a = F5.simulate(bars, i0, dirn, entry, stop0, tg_a, qtys,
                        runner_stop_only=eligible, rev=rev)
        b = F5.simulate(bars, i0, dirn, entry, stop0, tg_b, qtys,
                        runner_stop_only=eligible, rev=rev)

        n_used += 1
        if a["usd"] != b["usd"]:
            n_changed_pnl += 1
        tot_a += a["usd"]
        tot_b += b["usd"]
        tot_books += float(pnl or 0)
        tot_sierra += float(psier if psier is not None else (pnl or 0))
        pd = per_day.setdefault(str(day), dict(a=0.0, b=0.0, books=0.0, n=0, v=0))
        pd["a"] += a["usd"]; pd["b"] += b["usd"]
        pd["books"] += float(pnl or 0); pd["n"] += 1
        pd["v"] += 1 if violated else 0

        gaps = []
        legs = [x for x in (t1, t2, t3) if x]
        dists = [dirn * (float(x) - entry) for x in legs]
        for i in range(len(dists) - 1):
            gaps.append(round(dists[i + 1] - dists[i], 2))

        detail.append(dict(
            id=tid, mode=md, day=str(day), dir=str(d), pat=pat, day_type=dtyp,
            c=contracts, entry=entry, stop=round(stop0, 2), risk=round(risk, 2),
            atr=round(atr, 2), min_gap=rec.get("min_gap"), basis=rec.get("basis"),
            before=[t1, t2, t3], after=[af.get("t1"), af.get("t2"), af.get("t3")],
            gaps=gaps, worst_gap=(min(gaps) if gaps else None),
            branches=branches, violated=violated,
            books=float(pnl or 0),
            sierra=(float(psier) if psier is not None else None),
            base=a["usd"], spaced=b["usd"], delta=round(b["usd"] - a["usd"], 2),
            exit_reason=xr))

    # ── report ───────────────────────────────────────────────────────────
    day_deltas = [round(v["b"] - v["a"], 2) for v in per_day.values()]
    out = []
    def P(s=""):
        out.append(s)
        print(s)

    P(f"TARGET_MIN_SPACING replay   mode={args.mode}   "
      f"management={'F5 trail' if args.trail else 'fixed ladder'}   "
      f"k={cfg['k_atr']} m={cfg['m_risk']}")
    P(f"  window {OR.D0} .. {D_END}")
    P(f"  trades replayed n={n_used}   skipped={n_skip} {dict(skips)}")
    P(f"  ladders VIOLATING the spacing rule            {n_violate:5d}"
      f"   ({(100.0*n_violate/n_used if n_used else 0):.1f}%)"
      f"   legs: {n_drop} DROP / {n_push} PUSH")
    P(f"  BOOKS   pnl_usd (as recorded)                 {tot_books:+10.2f}")
    P(f"  BOOKS   pnl_sierra where F2 populated it      {tot_sierra:+10.2f}")
    P(f"  ARM-A   books ladder, simulated               {tot_a:+10.2f}")
    P(f"  ARM-B   spacing-corrected ladder              {tot_b:+10.2f}")
    P(f"  DELTA   ARM-B - ARM-A                         {tot_b - tot_a:+10.2f}"
      f"   ({n_changed_pnl} trades changed P&L)")
    if day_deltas:
        P(f"  per-day delta: median {statistics.median(day_deltas):+.2f}   "
          f"mean {statistics.mean(day_deltas):+.2f}   "
          f"days {len(day_deltas)} (+{sum(1 for x in day_deltas if x > 0)}"
          f"/-{sum(1 for x in day_deltas if x < 0)}"
          f"/={sum(1 for x in day_deltas if x == 0)})")

    P("")
    P("  worst offenders (smallest step in the ladder)")
    worst = sorted([d for d in detail if d["worst_gap"] is not None],
                   key=lambda x: x["worst_gap"])[:15]
    for t in worst:
        P(f"    #{t['id']:<4d} {t['day']} {t['mode']:<6s} {t['dir']:5s} "
          f"{t['c']}c {str(t['pat'] or '-'):<14s} risk={t['risk']:5.2f} "
          f"atr={t['atr']:5.2f} gap_min={t['worst_gap']:+6.2f} "
          f"need={t['min_gap']} | {t['before']} -> {t['after']} | "
          f"books {t['books']:+8.2f} base {t['base']:+8.2f} "
          f"spaced {t['spaced']:+8.2f} delta {t['delta']:+8.2f}")

    P("")
    P("  largest P&L movers")
    for t in sorted(detail, key=lambda x: -abs(x["delta"]))[:15]:
        if not t["delta"]:
            continue
        P(f"    #{t['id']:<4d} {t['day']} {t['mode']:<6s} {t['dir']:5s} "
          f"{t['c']}c {str(t['pat'] or '-'):<14s} {str(t['day_type'] or '-'):<16s} "
          f"branches={t['branches']} base {t['base']:+8.2f} "
          f"spaced {t['spaced']:+8.2f} delta {t['delta']:+8.2f} ({t['exit_reason']})")

    P("")
    P("  day          n  viol     books      base    spaced     delta")
    for dstr in sorted(per_day):
        v = per_day[dstr]
        P(f"  {dstr} {v['n']:4d} {v['v']:5d} {v['books']:+9.2f} {v['a']:+9.2f} "
          f"{v['b']:+9.2f} {v['b']-v['a']:+9.2f}")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(dict(summary=dict(
                n=n_used, skipped=n_skip, violate=n_violate, drop=n_drop,
                push=n_push, books=tot_books, sierra=tot_sierra,
                arm_a=tot_a, arm_b=tot_b, delta=tot_b - tot_a,
                k=cfg["k_atr"], m=cfg["m_risk"], mode=args.mode,
                trail=args.trail), detail=detail, per_day=per_day), f, indent=1)
        print(f"\n  json -> {args.json}")
    if args.md:
        with open(args.md, "w") as f:
            f.write("```\n" + "\n".join(out) + "\n```\n")
        print(f"  md   -> {args.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
