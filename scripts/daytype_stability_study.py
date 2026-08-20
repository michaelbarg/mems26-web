#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daytype_stability_study.py — measure the day-type label instability (T-47 / F6).

WHY
---
`docs/reports/DAILY_EXTREMES_PLAYBOOK_2026-08-20.md` §3 measured 44% disagreement
between the live label and the honest post-hoc classification, and 46% between the
TWO live sources on the same day.  Days where the sources disagreed netted
-$728.75; agreeing days netted +$1,048.75.  This script quantifies the mechanism
so `DAYTYPE_RECLASS_STABILITY_V1`'s N can be chosen FROM DATA, not from taste.

WHAT IT MEASURES
----------------
1. The LIVE per-bar promotion sequence, reproduced exactly as `backend/main.py`
   `_day_type_on_bar` runs it: for every RTH bar i >= 12 (i.e. once the IB has
   locked) call `classifier_core.classify_session(bars[:i], is_eod=False)`.
   That is the same one code path the live engine and classify_replay share.
2. Flip statistics: how many label changes per session, and the RUN LENGTH (in
   5-min bars) each new label survived before changing again.
3. An N-consecutive-bar confirmation simulation for N = 1..6: how many flips it
   removes, how many bars of delay it adds to the day's FINAL label, and whether
   it ever changes the final label (it must not - that would be blocking a real
   regime change, not damping noise).
4. Which of the two live sources is which: the timeline value AT EACH TRADE'S
   ENTRY TIMESTAMP vs the stamped `v9_trades.day_type_at_entry`, and vs the
   single `v9_day_type_history` row for the date.

READ-ONLY.  Direct psycopg2, no backend.v9.db.read (stale-SQLite fallback).
Writes nothing but stdout + the JSON dump given by --json.

Usage:  python3 scripts/daytype_stability_study.py [--json /tmp/dts.json]
"""

import argparse
import collections
import json
import os
import statistics
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Reuse the playbook's loaders / value-area / normalisation verbatim.  This study
# must not introduce a second definition of "the session" or "the label".
import importlib.util as _ilu

_DEP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "daily_extremes_playbook.py")
_spec = _ilu.spec_from_file_location("daily_extremes_playbook", _DEP_PATH)
DEP = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(DEP)

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
IB_BARS = DEP.IB_BARS
norm = DEP.norm


# ------------------------------------------------------------------ timeline
def bar_timeline(days, d, bars):
    """The LIVE promotion sequence: classify_session(bars[:i], is_eod=False) for
    every i >= IB_BARS, exactly as backend/main.py:467-492 runs it after IB lock.

    Returns [(i, et_time, label, confidence, reason), ...] - one entry per bar.
    """
    for k, v in DEP.LIVE_S1_FLAGS.items():
        os.environ[k] = v
    from backend.v9.systems.day_type.classifier_core import classify_session

    keys = sorted([k for k in days if k < d])
    prev = days[keys[-1]] if keys else None
    pdh = max(b["h"] for b in prev) if prev else None
    pdl = min(b["l"] for b in prev) if prev else None
    pvah = pval = None
    if prev:
        pvah, pval, _ = DEP.value_area(prev)
    ib_hist = []
    for k in keys[-40:]:
        bb = days[k]
        if len(bb) >= IB_BARS:
            ib = bb[:IB_BARS]
            ib_hist.append(max(x["h"] for x in ib) - min(x["l"] for x in ib))
    vols = [sum(x["v"] for x in days[k]) for k in keys[-20:] if len(days[k]) >= 40]
    vol_med = statistics.median(vols) if vols else None

    ib = bars[:IB_BARS]
    ibh, ibl = max(x["h"] for x in ib), min(x["l"] for x in ib)
    _, _, poc_ib = DEP.value_area(ib)

    out = []
    n = len(bars)
    for i in range(IB_BARS, n + 1):
        sub = bars[:i]
        vr = None
        if vol_med and vol_med > 0:
            vr = round(sum(b["v"] for b in sub) / vol_med, 3)
        _, _, poc_now = DEP.value_area(sub)
        try:
            r = classify_session(
                bars=[dict(o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"]) for b in sub],
                ib_high=ibh, ib_low=ibl, open_price=sub[0]["o"],
                ib_width_hist=ib_hist, profile_shape=None, vol_ratio=vr,
                prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl,
                poc_now=poc_now, poc_at_ib=poc_ib, is_eod=False,
            )
        except Exception as e:                          # honest failure (Rule 1)
            out.append((i, sub[-1]["t"], None, None, "ERR:%r" % (e,)))
            continue
        lbl = r.get("day_type")
        # FORMING / UNKNOWN are not a published label - the live getter excludes
        # them explicitly (trade_context.py:565).  Keep them as None.
        if lbl in ("FORMING", "UNKNOWN", "INDETERMINATE", None, ""):
            lbl = None
        out.append((i, sub[-1]["t"], norm(lbl) if lbl else None,
                    r.get("confidence"), r.get("reason")))
    return out


# ------------------------------------------------------------------ flip stats
def runs_of(tl):
    """Consecutive equal-label runs over the timeline (None counts as its own)."""
    runs = []
    for (_i, t, lbl, conf, _r) in tl:
        if runs and runs[-1]["label"] == lbl:
            runs[-1]["bars"] += 1
            runs[-1]["confs"].append(conf)
        else:
            runs.append(dict(label=lbl, bars=1, start_t=t, confs=[conf]))
    return runs


def simulate_n(tl, n):
    """Publish-with-N-consecutive-agreeing-bars.

    A candidate label different from the published one must repeat on N
    consecutive bars before it is published.  N=1 == today's behaviour
    (publish immediately) and MUST reproduce the raw timeline byte-for-byte.
    """
    published = None
    cand = None
    cand_run = 0
    out = []
    for (i, t, lbl, conf, _r) in tl:
        if published is None:
            published = lbl                     # first-ever value: nothing to protect
            cand, cand_run = None, 0
        elif lbl == published:
            cand, cand_run = None, 0
        else:
            if lbl == cand:
                cand_run += 1
            else:
                cand, cand_run = lbl, 1
            if cand_run >= n:
                published = cand
                cand, cand_run = None, 0
        out.append((i, t, published))
    return out


def flips(seq):
    """Count label changes in a published sequence (ignoring the initial set)."""
    c = 0
    prev = None
    first = True
    for (_i, _t, lbl) in seq:
        if first:
            prev, first = lbl, False
            continue
        if lbl != prev:
            c += 1
        prev = lbl
    return c


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--max-n", type=int, default=6)
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

    by_day_trades = collections.defaultdict(list)
    for t in trades:
        by_day_trades[t["day"]].append(t)

    rows = []
    for d in sessions:
        bars = days[d]
        tl = bar_timeline(days, d, bars)
        if not tl:
            continue
        rs = runs_of(tl)
        raw_seq = simulate_n(tl, 1)
        final_raw = raw_seq[-1][2] if raw_seq else None

        # per-N simulation
        per_n = {}
        for n in range(1, args.max_n + 1):
            sq = simulate_n(tl, n)
            fin = sq[-1][2] if sq else None
            # delay to the FINAL label: first bar index at which the final label
            # became published, compared with the raw sequence.
            def first_idx(seq, lbl):
                for (i, _t, l) in seq:
                    if l == lbl:
                        return i
                return None
            per_n[n] = dict(flips=flips(sq), final=fin,
                            final_same=(fin == final_raw),
                            idx_final=first_idx(sq, final_raw),
                            idx_final_raw=first_idx(raw_seq, final_raw))

        # the two live sources, on this date
        hist = (live_labels.get(d) or {}).get("day_type")
        hist_n = norm(hist) if hist else None
        tds = by_day_trades.get(d) or []
        stamped = [t["day_type"] for t in tds if t["day_type"]]
        modal = collections.Counter(norm(s) for s in stamped).most_common(1)
        modal = modal[0][0] if modal else None

        # timeline value AT EACH TRADE'S ENTRY TIME (what a correct
        # "label at entry" read should have produced)
        tl_at_entry = []
        for t in tds:
            want = t["t_in"]
            val = None
            for (_i, bt, lbl, _c, _r) in tl:
                if bt <= want:
                    val = lbl
                else:
                    break
            tl_at_entry.append((t["id"], val, norm(t["day_type"]) if t["day_type"] else None,
                                t["pnl"], t["mode"]))

        pnl_day = sum(t["pnl"] for t in tds if (t["mode"] or "").lower() == "live")
        rows.append(dict(
            date=d.isoformat(), bars=len(bars), tl_bars=len(tl),
            runs=[dict(label=r["label"], bars=r["bars"]) for r in rs],
            n_runs=len(rs), raw_flips=flips(raw_seq), final_raw=final_raw,
            per_n=per_n, hist=hist_n, modal_at_entry=modal,
            tl_at_entry=tl_at_entry, pnl_live=pnl_day,
            n_trades=len(tds),
        ))

    # ---------------------------------------------------------------- report
    print("=" * 78)
    print("DAY-TYPE STABILITY STUDY  (T-47 / F6)   sessions=%d" % len(rows))
    print("=" * 78)

    tot_flips = sum(r["raw_flips"] for r in rows)
    print("\n1) RAW per-bar promotion sequence (today's behaviour, post-IB-lock)")
    print("   sessions with >=1 flip : %d / %d"
          % (sum(1 for r in rows if r["raw_flips"] > 0), len(rows)))
    print("   total flips            : %d   (mean %.2f/session)"
          % (tot_flips, tot_flips / max(1, len(rows))))

    # run-length histogram for runs that are NOT the final run
    rl = collections.Counter()
    short_runs = []
    for r in rows:
        rr = r["runs"]
        for k, run in enumerate(rr):
            if k == len(rr) - 1:
                continue                      # the surviving final run
            rl[run["bars"]] += 1
            if run["bars"] <= 6:
                short_runs.append((r["date"], run["label"], run["bars"]))
    print("\n2) RUN LENGTH of every NON-final label (bars it survived)")
    print("   %-8s %-6s %-8s" % ("bars", "count", "cum%"))
    tot_rl = sum(rl.values())
    cum = 0
    for b in sorted(rl):
        cum += rl[b]
        print("   %-8d %-6d %.1f%%" % (b, rl[b], 100.0 * cum / max(1, tot_rl)))

    print("\n3) N-CONFIRMATION SIMULATION  (N=1 is today's behaviour)")
    print("   %-4s %-8s %-9s %-14s %-16s" %
          ("N", "flips", "removed", "final changed", "median delay(bars)"))
    base = sum(r["per_n"][1]["flips"] for r in rows)
    for n in range(1, args.max_n + 1):
        f = sum(r["per_n"][n]["flips"] for r in rows)
        chg = sum(1 for r in rows if not r["per_n"][n]["final_same"])
        delays = []
        for r in rows:
            a, b = r["per_n"][n]["idx_final"], r["per_n"][n]["idx_final_raw"]
            if a is not None and b is not None:
                delays.append(a - b)
        med = statistics.median(delays) if delays else 0
        mx = max(delays) if delays else 0
        print("   %-4d %-8d %-9d %-14d %s (max %s)"
              % (n, f, base - f, chg, med, mx))

    print("\n4) THE TWO LIVE SOURCES")
    both = [r for r in rows if r["hist"] and r["modal_at_entry"]]
    dis = [r for r in both if r["hist"] != r["modal_at_entry"]]
    print("   days with both sources : %d" % len(both))
    print("   disagree               : %d  (%.0f%%)"
          % (len(dis), 100.0 * len(dis) / max(1, len(both))))
    print("   $ live on disagreeing  : %+.2f" % sum(r["pnl_live"] for r in dis))
    print("   $ live on agreeing     : %+.2f"
          % sum(r["pnl_live"] for r in both if r["hist"] == r["modal_at_entry"]))

    # is `hist` the EOD value of the timeline?  is `at_entry` the entry-time value?
    hist_eq_final = sum(1 for r in both if r["hist"] == r["final_raw"])
    print("\n   hist == timeline FINAL (EOD) : %d / %d" % (hist_eq_final, len(both)))
    ok = bad = 0
    for r in rows:
        for (_tid, tlv, stamped, _p, _m) in r["tl_at_entry"]:
            if stamped is None:
                continue
            if tlv == stamped:
                ok += 1
            else:
                bad += 1
    print("   stamped day_type_at_entry == timeline AT ENTRY TIME : %d match / %d differ"
          % (ok, bad))

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(rows, fh, default=str, indent=1)
        print("\n[json] %s" % args.json)


if __name__ == "__main__":
    main()
