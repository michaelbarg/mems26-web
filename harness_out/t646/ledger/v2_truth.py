#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-646 — opening-type truth = v2 (Michael 24.10: "כלל דלתון + 5 ימים שלך"; opening = v2 on closed bars).

Computes the v2 opening (OpeningLock over the first 12 closed RTH bars, exactly as scripts/opening_v2_study.py does)
for every RTH date in [since, until] and writes {date: {opening, direction, lock_bar, at6, revoked, n_bars, atr}}.
READ-ONLY (SELECT on v9_bars_5min_woodies). Used by scripts/day_dissect.py --truth-opening <this json>.

  python3 harness_out/t646/ledger/v2_truth.py 2026-06-01 2026-10-23 harness_out/t646/ledger/v2_truth.json
"""
import os, sys, json, statistics
ROOT = '/Users/michael/Downloads/mems26_web_git'
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, ROOT)
import opening_v2_study as S  # noqa: E402  (loads .env, DB read helpers, v2 classifier)
from backend.v9.systems.opening_classifier_v2 import OpeningLock  # noqa: E402


def main(since, until, out):
    dates = S.rth_dates(since, until)
    prev_bars, prev_d, full = None, None, []
    res = {}
    for d in dates:
        bars = S.rth_bars(d)
        if len(bars) < 12:                      # same bookkeeping as opening_v2_study.main
            prev_bars, prev_d = (bars if len(bars) >= 30 else prev_bars), d
            if len(bars) >= 60:
                full.append(statistics.mean(b["h"] - b["l"] for b in bars)); full = full[-3:]
            continue
        prev = S.profile(prev_bars) if prev_bars else None
        if prev and prev_d:
            oh, ol = S.overnight(d, prev_d)
            prev["on_high"], prev["on_low"] = oh, ol
        atr = S.unit_atr(full)
        lk = OpeningLock(); seq = []
        for k in range(1, 13):
            seq.append(lk.update(bars[:k], prev, atr))
        r12 = seq[11]
        used = lk.locked or r12
        res[str(d)] = dict(opening=used["type"], direction=used.get("direction"), lock_bar=lk.locked_bar,
                           at6=seq[5]["type"], revoked=[[b, t] for b, t in lk.revoked], n_bars=len(bars),
                           atr=(round(atr, 3) if atr else None), has_prev=bool(prev))
        prev_bars, prev_d = bars, d
        if len(bars) >= 60:
            full.append(statistics.mean(b["h"] - b["l"] for b in bars)); full = full[-3:]
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    from collections import Counter
    print("v2 truth: %d dates → %s · %s" % (len(res), out, dict(Counter(v["opening"] for v in res.values()))))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
