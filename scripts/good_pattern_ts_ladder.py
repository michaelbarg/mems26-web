#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
good_pattern_ts_ladder.py — TREND_STEP measured with ITS OWN ladder.

good_pattern_fix.py manages every candidate with ORA.sim_ladder (the MEMS
1R/2R/3R + BE + structural trail).  TREND_STEP does NOT use that ladder live:
the ruling (RULED_FLAGS TREND_STEP_ENTRY_V1, fix 2026-08-18) ships a
LEG-RELATIVE model with the setup — stop = pause extreme +/- 10% of the impulse
clamped 2.5-9.0pt, targets 0.45/0.80/1.30 x impulse, stop_source=TREND_STEP_LEG.
Judging it on the MEMS ladder is therefore unfair in both directions.

This script re-measures TREND_STEP on its own numbers and splits IN-SAMPLE
(2026-07-15..08-12, the window the parameters were fitted on) from
OUT-OF-SAMPLE, at 4 and 6 contracts and 3 slippage levels.

Ladder: 6c = 2/2/2 across t1/t2/t3, 4c = 1/2/1.  Stop -> BE after t1 fills.
Same-bar ambiguity (stop and target both touched) resolves to the STOP.
EOD flatten on the last RTH bar.  $1.50/contract round-turn commission.

READ-ONLY.
"""
import collections
import datetime as dt
import importlib.util as _ilu
import json
import os
import statistics
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_s = _ilu.spec_from_file_location("gpf", os.path.join(ROOT, "scripts", "good_pattern_fix.py"))
M = _ilu.module_from_spec(_s)
_s.loader.exec_module(M)

from backend.v9.systems.trend_step import detector as TS   # noqa: E402

IS0, IS1 = dt.date(2026, 7, 15), dt.date(2026, 8, 12)
TICK, POINT_USD, COMM = 0.25, 5.0, 1.50
SPLIT = {6: (2, 2, 2), 4: (1, 2, 1)}


def sim_own(bars, i, d, contracts, slip):
    """One TREND_STEP trade on its own stop/targets. bars = ESR bar dicts."""
    sign = 1 if d["direction"] == "LONG" else -1
    entry = d["entry_price"] + sign * slip * TICK           # adverse fill
    stop = d["stop"]
    tg = [d["t1"], d["t2"], d["t3"]]
    alloc = SPLIT[contracts]
    left = list(alloc)
    pts = 0.0
    banked_first = False
    for j in range(i + 1, len(bars)):
        b = bars[j]
        hit_stop = (b["l"] <= stop) if sign > 0 else (b["h"] >= stop)
        if hit_stop:
            fill = stop - sign * slip * TICK
            pts += sum(left) * sign * (fill - entry)
            left = [0, 0, 0]
            break
        for k in range(3):
            if left[k] <= 0:
                continue
            hit = (b["h"] >= tg[k]) if sign > 0 else (b["l"] <= tg[k])
            if hit:
                pts += left[k] * sign * (tg[k] - entry)     # resting limit, no slip
                left[k] = 0
                if k == 0 and not banked_first:
                    banked_first = True
                    stop = entry                            # BE after T1
        if sum(left) == 0:
            break
    if sum(left) > 0:                                       # EOD flatten
        fill = bars[-1]["c"] - sign * slip * TICK
        pts += sum(left) * sign * (fill - entry)
    return pts * POINT_USD - COMM * contracts


def main():
    cn = psycopg2.connect("postgresql://localhost/mems26")
    cn.set_session(readonly=True)
    cur = cn.cursor()
    days = M.ESR.load_bars(cur)
    ds = M.ESR.live_days(days)
    cur.execute("""
        select (ts at time zone 'America/New_York') as et, open, high, low, close,
               coalesce(volume,0), lsma_value
        from v9_bars_5min_woodies
        where (ts at time zone 'America/New_York')::date between %s and %s
          and (ts at time zone 'America/New_York')::time >= %s
          and (ts at time zone 'America/New_York')::time <  %s
        order by ts""", (M.ESR.WARM, M.D1, M.ESR.RTH0, M.ESR.RTH1))
    tsd = collections.OrderedDict()
    for et, o, h, l, c, v, lr in cur.fetchall():
        tsd.setdefault(et.date(), []).append(dict(
            o=float(o), h=float(h), l=float(l), c=float(c), v=float(v),
            lsma=(float(lr) if lr is not None else None), hhmm=et.strftime("%H:%M")))

    p = TS._p()
    print(f"[params] {p}")
    print(f"[data] sessions={len(ds)}  IS={IS0}..{IS1}")
    out = {}
    for label, relax in (("LIVE", None),
                         ("TSB pause<=4", dict(PAUSE_MAX=4)),
                         ("TSD cutoff 15:30", dict(CUTOFF="15:30")),
                         ("TSB+TSD", dict(PAUSE_MAX=4, CUTOFF="15:30"))):
        pp = dict(p)
        if relax:
            pp.update(relax)
        for contracts in (4, 6):
            for slip in (0, 1, 2):
                perday, n, wins = {}, 0, 0
                for dd in ds:
                    bars = days[dd]
                    tb = tsd[dd]
                    seen, u = set(), 0.0
                    busy = -1
                    for i in range(5, len(tb)):
                        s = TS.detect_trend_step(tb, i, pp)
                        if not s or s["step_id"] in seen:
                            continue
                        seen.add(s["step_id"])
                        if i <= busy:
                            continue
                        val = sim_own(bars, i, s, contracts, slip)
                        u += val
                        n += 1
                        wins += 1 if val > 0 else 0
                        busy = i          # own-ladder trades are not slot-blocked
                                          # against each other beyond same-bar
                    perday[dd] = round(u, 2)
                tot = round(sum(perday.values()), 2)
                IS = round(sum(v for d, v in perday.items() if IS0 <= d <= IS1), 2)
                OOS = round(sum(v for d, v in perday.items() if not (IS0 <= d <= IS1)), 2)
                jul = round(sum(v for d, v in perday.items() if d.month == 7), 2)
                aug = round(sum(v for d, v in perday.items() if d.month == 8), 2)
                key = f"{label} c{contracts} s{slip}"
                out[key] = dict(n=n, total=tot, IS=IS, OOS=OOS, jul=jul, aug=aug,
                                win=round(100.0 * wins / max(1, n), 1),
                                median_day=round(statistics.median(perday.values()), 2),
                                since_flag=round(sum(v for d, v in perday.items()
                                                     if d >= dt.date(2026, 8, 14)), 2))
                r = out[key]
                print(f"  {key:<24} n={r['n']:4d} tot=${r['total']:>9.2f} "
                      f"IS=${r['IS']:>9.2f} OOS=${r['OOS']:>9.2f} win={r['win']:>5.1f}% "
                      f"med/d=${r['median_day']:>7.2f} Jul=${r['jul']:>8.2f} "
                      f"Aug=${r['aug']:>8.2f} since-flag(08-14+)=${r['since_flag']:>8.2f}")
    with open("/tmp/gpf_ts.json", "w") as f:
        json.dump(out, f, default=str)
    print("[out] /tmp/gpf_ts.json")


if __name__ == "__main__":
    main()
