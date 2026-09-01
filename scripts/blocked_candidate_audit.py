#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""What did the gates BLOCK — and would it have won?

Michael, 2026-09-01: *"אולי אתה בכלל לא עשית שום דבר כמו שצריך כי המערכת מנעה
בנקודות הנכונות להיכנס לעסקאות מנצחות."*

He is right that this was never measured. Every analysis so far has looked at
what the system DID. A gate can only be judged by what it REFUSED.

`gateway_decisions.jsonl` carries, for every blocked candidate:
    ts · pattern · direction · entry · blocked_by
    mfe_track = {stop, t1, t2, t3}      ← the bracket it WOULD have had

That last field is what makes an honest counterfactual possible. The test is
NOT "how far did price go" (MFE) — that measure misled this project twice in
one day, by factors of 4 and 7. The test is the one the trade itself would
have faced:

    walk 5-min bars forward from the signal;
    whichever comes first — t1 or stop — is the answer.

`t1_first` is a fact about the trade that was refused. MFE is not.

Honest-failure rules:
  * no stop or no t1 in mfe_track      -> NOT_JUDGEABLE, excluded, counted
  * neither level touched in the window -> UNRESOLVED, excluded, counted
  * bars missing for the window         -> NO_BARS, excluded, counted
Nothing is imputed. A gate with too few judgeable rows gets no verdict.

    python3 scripts/blocked_candidate_audit.py
    python3 scripts/blocked_candidate_audit.py --window 90
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

for _ln in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    _ln = _ln.strip()
    if _ln and not _ln.startswith("#") and "=" in _ln:
        _k, _v = _ln.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.split("#")[0].strip())

if "postgres" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("DATABASE_URL is not Postgres — refusing to report from a stale "
             "SQLite mirror (T-161).")

from backend.v9.db.read import read_all  # noqa: E402

LEDGER = os.path.expanduser(
    "~/SierraChart_Data/v9_export/gateway_decisions.jsonl")


def judge(bars, entry, stop, t1, direction):
    """t1 or stop — whichever the price reaches FIRST. None if neither."""
    long = (direction or "").upper() == "LONG"
    for b in bars:
        hi, lo = float(b["high"]), float(b["low"])
        if long:
            hit_t1, hit_st = hi >= t1, lo <= stop
        else:
            hit_t1, hit_st = lo <= t1, hi >= stop
        # both inside one 5-min bar: we cannot order them from OHLC alone.
        # Call it a STOP — the pessimistic reading. Saying "t1 first" here
        # would be exactly the wishful arithmetic this script exists to avoid.
        if hit_st:
            return False
        if hit_t1:
            return True
    return None


def mfe_points(bars, entry, direction):
    """Max favourable excursion in POINTS inside the window.

    UPPER BOUND ON THE CLAIM, NOT A PROFIT. It says how far price travelled
    the refused trade's way; it says nothing about whether the order would
    have filled at that level (that is T-213, still open), nor about size,
    runner or any exit rule. Reported next to t1_first, never instead of it.
    """
    long = (direction or "").upper() == "LONG"
    best = None
    for b in bars:
        v = (float(b["high"]) - entry) if long else (entry - float(b["low"]))
        if best is None or v > best:
            best = v
    return best


def _median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=60,
                    help="minutes to walk forward (default 60)")
    ap.add_argument("--archives", action="store_true",
                    help="also read ~/SierraChart_Data/v9_export/"
                         "decisions_archive/gateway_decisions.*.jsonl "
                         "(multi-session measurement, not just today)")
    a = ap.parse_args()

    import glob as _glob
    files = [LEDGER]
    if a.archives:
        files = sorted(_glob.glob(os.path.expanduser(
            "~/SierraChart_Data/v9_export/decisions_archive/"
            "gateway_decisions.*.jsonl"))) + [LEDGER]

    rows = []
    for path in files:
        if not os.path.exists(path):
            continue
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except Exception:
                continue
            if d.get("blocked_by") and d.get("entry"):
                rows.append(d)
    print(f"[ledger] {len(files)} file(s), {len(rows)} blocked rows with an entry")

    if not rows:
        print("no blocked candidates with an entry price in the ledger")
        return 1

    bars = read_all(
        "SELECT ts, high, low FROM v9_bars_5min_woodies "
        "WHERE ts >= (SELECT min(ts) FROM v9_bars_5min_woodies) ORDER BY ts", {}) or []
    if not bars:
        sys.exit("no bars — refusing to report zero (this is not an empty day)")

    from datetime import datetime, timezone
    stats = defaultdict(lambda: {"win": 0, "loss": 0, "unresolved": 0,
                                 "nojudge": 0, "nobars": 0, "blocks": 0,
                                 "mfe": []})
    days = set()

    for d in rows:
        g = d["blocked_by"]
        stats[g]["blocks"] += 1
        if isinstance(d.get("ts"), str):
            days.add(d["ts"][:10])
        mt = d.get("mfe_track") or {}
        stop, t1 = mt.get("stop"), mt.get("t1")
        if stop is None or t1 is None:
            stats[g]["nojudge"] += 1
            continue
        try:
            t0 = datetime.fromisoformat(d["ts"])
        except Exception:
            stats[g]["nojudge"] += 1
            continue
        if t0.tzinfo is None:
            t0 = t0.replace(tzinfo=timezone.utc)
        t_end = t0 + timedelta(minutes=a.window)
        w = [b for b in bars
             if b["ts"] is not None and t0 <= b["ts"] <= t_end]
        if not w:
            stats[g]["nobars"] += 1
            continue
        _m = mfe_points(w, float(d["entry"]), d.get("direction"))
        if _m is not None:
            stats[g]["mfe"].append(_m)
        v = judge(w, float(d["entry"]), float(stop), float(t1), d.get("direction"))
        if v is True:
            stats[g]["win"] += 1
        elif v is False:
            stats[g]["loss"] += 1
        else:
            stats[g]["unresolved"] += 1

    print(f"\n{'='*104}")
    print(f" What the gates REFUSED — t1-before-stop, {a.window}min window")
    print(f" (t1_first is a fact about the refused trade. MFE is an UPPER BOUND, not a profit.)")
    print(f" sessions covered: {len(days)}  ({min(days) if days else '—'} → {max(days) if days else '—'})")
    print(f"{'='*104}")
    print(f" {'gate':<26} {'blocks':>6} {'judged':>7} {'t1 first':>9} "
          f"{'stop first':>11} {'t1 %':>6} {'med MFE':>8}   excluded")
    tot_w = tot_l = tot_b = 0
    for g, s in sorted(stats.items(), key=lambda kv: -kv[1]["blocks"]):
        j = s["win"] + s["loss"]
        exc = f"unres {s['unresolved']} · nojudge {s['nojudge']} · nobars {s['nobars']}"
        pct = f"{100*s['win']/j:.0f}%" if j else "  —"
        med = _median(s["mfe"])
        meds = f"{med:+.2f}" if med is not None else "    —"
        print(f" {g[:26]:<26} {s['blocks']:>6} {j:>7} {s['win']:>9} {s['loss']:>11} "
              f"{pct:>6} {meds:>8}   {exc}")
        tot_w += s["win"]
        tot_l += s["loss"]
        tot_b += s["blocks"]
    if tot_w + tot_l:
        print(f"\n {'ALL GATES':<26} {tot_b:>6} {tot_w+tot_l:>7} {tot_w:>9} {tot_l:>11} "
              f"{100*tot_w/(tot_w+tot_l):>5.0f}%")
    print(f"""
 HOW TO READ THIS — and how NOT to:
   A gate whose refusals reach t1 far MORE often than the live win rate is
   costing money. One whose refusals mostly stop out is earning its keep.
   But t1-before-stop is NOT profit: it ignores position size, the runner,
   and every exit rule after t1. It answers one question only — *was the
   refused setup a good setup* — and that is the question a gate is for.
   A bar that touches both levels is scored STOP, deliberately.
{'='*80}
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
