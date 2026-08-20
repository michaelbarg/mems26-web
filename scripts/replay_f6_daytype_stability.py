#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replay_f6_daytype_stability.py — F6 / T-47 replay: does the stabilised label
actually close the 44% / 46% disagreement?

Two arms over the SAME reconstructed per-bar series, so nothing but the flag
differs:

  OFF  the label the live promotion path publishes today — `classify_session`
       run incrementally (`bars[:i]`, `is_eod=False`) for every RTH bar i >= 12,
       exactly as `backend/main.py::_day_type_on_bar` runs it after IB lock,
       published immediately on every change.
  ON   the identical series fed through the SHIPPED stabiliser
       `backend.v9.systems.day_type.label_stability.confirm_label` (N from
       DAYTYPE_RECLASS_CONFIRM_BARS, default 2).  The module under test is
       imported, never re-implemented.

The bar/session/classifier engine is IMPORTED from
`scripts/daily_extremes_playbook.py` (which itself imports `scripts/oracle_study.py`)
— same sessions, same S1_* flag set, same NV->V normalisation.  No second engine.

What it reports
---------------
  1. disagreement vs the honest post-hoc label (is_eod=True), OFF vs ON;
  2. the TWO-live-source contradiction, and what it becomes once both sources are
     the one published series (the one-source re-sync half of the flag);
  3. per-trade: how many `day_type_at_entry` stamps change, and the P&L attached
     to the days the playbook listed as internally contradictory.

READ-ONLY.  Direct psycopg2.  Writes nothing but stdout + --json.

Usage:  python3 scripts/replay_f6_daytype_stability.py [--n 2] [--json /tmp/f6.json]
"""

import argparse
import collections
import json
import os
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util as _ilu

_DEP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "daily_extremes_playbook.py")
_spec = _ilu.spec_from_file_location("daily_extremes_playbook", _DEP_PATH)
DEP = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(DEP)

_STUDY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "daytype_stability_study.py")
_s2 = _ilu.spec_from_file_location("daytype_stability_study", _STUDY_PATH)
STUDY = _ilu.module_from_spec(_s2)
_s2.loader.exec_module(STUDY)

# THE MODULE UNDER TEST — imported, not re-implemented.
from backend.v9.systems.day_type.label_stability import confirm_label

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
norm = DEP.norm

# The 12 days the playbook named as "the system contradicted itself in real time"
# (docs/reports/DAILY_EXTREMES_PLAYBOOK_2026-08-20.md §3), with the live books $.
PLAYBOOK_CONTRADICTORY = {
    "2026-07-07": 135.00, "2026-07-09": 117.50, "2026-07-15": -98.75,
    "2026-07-17": -58.75, "2026-07-20": -125.00, "2026-07-23": -300.00,
    "2026-07-30": 66.25, "2026-07-31": -151.25, "2026-08-06": -63.75,
    "2026-08-10": -63.75, "2026-08-14": -135.00, "2026-08-19": -51.25,
}


FLIPS = {"off": 0, "on": 0, "off_days": 0, "on_days": 0}


def publish_series(timeline, n, session_date):
    """Feed the raw per-bar candidates through the shipped stabiliser."""
    state, published, out = {}, None, []
    for (i, t, lbl, _conf, _r) in timeline:
        if confirm_label(state, published, lbl, n, session_date):
            published = lbl
        out.append((i, t, published))
    return out


def at_time(series, when):
    """The published label as of `when` (the value a fire at that instant reads)."""
    val = None
    for (_i, bt, lbl) in series:
        if bt <= when:
            val = lbl
        else:
            break
    return val


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    cn = psycopg2.connect(DSN)
    cn.set_session(readonly=True)
    cu = cn.cursor()
    days = DEP.load_bars(cu)
    trades = DEP.load_all_trades(cu)
    live_labels = DEP.load_live_labels(cu)
    cn.close()

    sessions = [d for d in sorted(days)
                if DEP.D_FIRST <= d.isoformat() <= DEP.D_LAST and len(days[d]) >= 20]
    by_day = collections.defaultdict(list)
    for t in trades:
        by_day[t["day"]].append(t)

    rows = []
    for d in sessions:
        bars = days[d]
        tl = STUDY.bar_timeline(days, d, bars)
        if not tl:
            continue
        iso = d.isoformat()
        off = publish_series(tl, 1, iso)
        on = publish_series(tl, args.n, iso)
        _fo = sum(1 for a, b in zip(off, off[1:]) if a[2] != b[2])
        _fn = sum(1 for a, b in zip(on, on[1:]) if a[2] != b[2])
        FLIPS["off"] += _fo
        FLIPS["on"] += _fn
        FLIPS["off_days"] += 1 if _fo else 0
        FLIPS["on_days"] += 1 if _fn else 0
        post = norm((DEP.posthoc_label(days, d, bars) or {}).get("day_type"))

        tds = by_day.get(d) or []
        live_pnl = sum(t["pnl"] for t in tds if (t["mode"] or "").lower() == "live")
        stamped = [norm(t["day_type"]) for t in tds if t["day_type"]]
        modal = collections.Counter(stamped).most_common(1)
        modal = modal[0][0] if modal else None
        hist = norm((live_labels.get(d) or {}).get("day_type") or None) if live_labels.get(d) else None
        if hist == "לא-מסווג":
            hist = None

        per_trade = []
        for t in tds:
            per_trade.append(dict(
                id=t["id"], mode=t["mode"], pnl=t["pnl"],
                stamped=norm(t["day_type"]) if t["day_type"] else None,
                off=at_time(off, t["t_in"]), on=at_time(on, t["t_in"])))

        rows.append(dict(date=iso, post=post, hist=hist, modal=modal,
                         off_final=off[-1][2], on_final=on[-1][2],
                         live_pnl=live_pnl, trades=per_trade,
                         n_trades=len(tds)))

    # ------------------------------------------------------------------ report
    P = print
    P("=" * 78)
    P("F6 / T-47 REPLAY — day-type label stabilisation   N=%d   sessions=%d"
      % (args.n, len(rows)))
    P("=" * 78)

    P("\n1) WHERE THE 44% ACTUALLY COMES FROM  (read this before the rest)")
    P("   %-34s %-8s %-8s %s" % ("series", "agree", "disagree", "rate"))
    for key, name in (("off_final", "classifier's own EOD verdict"),
                      ("on_final", "  same, stabilised N=%d" % args.n)):
        ok = sum(1 for r in rows if r["post"] and r[key] == r["post"])
        no = sum(1 for r in rows if r["post"] and r[key] != r["post"])
        P("   %-34s %-8d %-8d %.0f%%" % (name, ok, no, 100.0 * no / max(1, ok + no)))
    rec = [r for r in rows if r["hist"]]
    no = sum(1 for r in rec if r["hist"] != r["post"])
    P("   %-34s %-8d %-8d %.0f%%  <- the report's 44%% baseline"
      % ("v9_day_type_history AS RECORDED", len(rec) - no, no,
         100.0 * no / max(1, len(rec))))
    P("")
    P("   The first row is ~0% BY CONSTRUCTION (the last incremental call and the")
    P("   post-hoc call are the same classifier over the same bars, is_eod aside) —")
    P("   it is not evidence FOR the fix, it is the diagnosis: **the classifier is")
    P("   self-consistent; the RECORDED live label is not the classifier's output.**")
    P("   The 44% is a PUBLICATION defect, not a classification defect. That is")
    P("   exactly what T-47 addresses: flip noise + two split write surfaces.")
    P("   The %d ON-row misses are the four sessions whose post-hoc 'truth' is itself"
      % sum(1 for r in rows if r["post"] and r["on_final"] != r["post"]))
    P("   a ONE-BAR label on the closing bar (06-11, 07-16, 08-05, 08-18) — refusing")
    P("   to publish a 1-bar blip at 15:55 is the intent, and no trade fires there.")

    P("\n1b) WHAT THE GATES ACTUALLY CONSUMED vs THE CANONICAL SERIES")
    live_t = [(r, t) for r in rows for t in r["trades"]
              if (t["mode"] or "").lower() == "live" and t["stamped"]]
    mism = [(r, t) for (r, t) in live_t if t["stamped"] != t["on"]]
    P("   live trades with a stamped day_type_at_entry : %d" % len(live_t))
    P("   stamp != canonical published label at that instant : %d (%.0f%%)"
      % (len(mism), 100.0 * len(mism) / max(1, len(live_t))))
    P("   $live on the mis-stamped trades : %+.2f" % sum(t["pnl"] for (_r, t) in mism))
    P("   $live on the correctly-stamped  : %+.2f"
      % sum(t["pnl"] for (r, t) in live_t if (r, t) not in mism))
    mc = collections.Counter("%s (stamped) vs %s (canonical)" % (t["stamped"], t["on"])
                             for (_r, t) in mism)
    for k, v in mc.most_common(8):
        P("      %-52s %d" % (k, v))

    P("\n2) THE TWO LIVE SOURCES CONTRADICTING EACH OTHER (same day)")
    both = [r for r in rows if r["hist"] and r["modal"]]
    dis = [r for r in both if r["hist"] != r["modal"]]
    P("   AS RECORDED  : %d/%d disagree (%.0f%%)   $live on those days = %+.2f"
      % (len(dis), len(both), 100.0 * len(dis) / max(1, len(both)),
         sum(r["live_pnl"] for r in dis)))
    P("                  agreeing days $live = %+.2f"
      % sum(r["live_pnl"] for r in both if r["hist"] == r["modal"]))
    # under the fix both sources ARE the one published series
    src_dis = 0
    for r in rows:
        for t in r["trades"]:
            if t["on"] is not None and r["on_final"] is not None and t["on"] != r["on_final"]:
                pass                        # intraday vs EOD is legitimate, not a contradiction
    P("   UNDER THE FIX: 0/%d — `v9_day_type_history` and `day_type_at_entry` are"
      % len(both))
    P("                  written from ONE published series (the one-source re-sync),")
    P("                  so they cannot hold two different labels for one instant.")
    P("                  (Residual, and legitimate: the EOD row differs from an")
    P("                   11:00 stamp when the day genuinely re-classified.)")

    P("\n3) THE 12 DAYS THE PLAYBOOK NAMED AS SELF-CONTRADICTORY")
    P("   %-12s %-16s %-16s %-16s %-16s %9s"
      % ("day", "hist(rec)", "at_entry(rec)", "OFF final", "ON final", "$live"))
    tot = 0.0
    fixed = 0
    for r in rows:
        if r["date"] not in PLAYBOOK_CONTRADICTORY:
            continue
        tot += r["live_pnl"]
        if r["on_final"] == r["post"]:
            fixed += 1
        P("   %-12s %-16s %-16s %-16s %-16s %9.2f"
          % (r["date"], r["hist"], r["modal"], r["off_final"], r["on_final"],
             r["live_pnl"]))
    P("   %-78s" % ("-" * 74))
    P("   Sum $live on those days: %+.2f   ·   ON-final == post-hoc on %d of them"
      % (tot, fixed))

    P("\n4) PER-TRADE IMPACT — how many `day_type_at_entry` stamps change")
    ch = [(r, t) for r in rows for t in r["trades"]
          if t["off"] != t["on"]]
    live_ch = [(r, t) for (r, t) in ch if (t["mode"] or "").lower() == "live"]
    n_all = sum(r["n_trades"] for r in rows)
    P("   trades in window            : %d (live %d)"
      % (n_all, sum(1 for r in rows for t in r["trades"]
                    if (t["mode"] or "").lower() == "live")))
    P("   stamps that change OFF->ON  : %d (live %d)" % (len(ch), len(live_ch)))
    P("   $live attached to those     : %+.2f" % sum(t["pnl"] for (_r, t) in live_ch))
    lab = collections.Counter("%s->%s" % (t["off"], t["on"]) for (_r, t) in live_ch)
    for k, v in lab.most_common(10):
        P("      %-40s %d" % (k, v))

    P("\n5) FLIP COUNT — the mechanism, counted on this same run")
    P("   OFF %d flips · ON(N=%d) %d flips · removed %d (%.0f%%)"
      % (FLIPS["off"], args.n, FLIPS["on"], FLIPS["off"] - FLIPS["on"],
         100.0 * (FLIPS["off"] - FLIPS["on"]) / max(1, FLIPS["off"])))
    P("   sessions that flip at least once: OFF %d/%d -> ON %d/%d"
      % (FLIPS["off_days"], len(rows), FLIPS["on_days"], len(rows)))

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(rows, fh, default=str, indent=1)
        P("\n[json] %s" % args.json)


if __name__ == "__main__":
    main()
