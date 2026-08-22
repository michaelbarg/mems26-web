#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
good_pattern_gates.py — gate-side census for the money-making patterns.

For every GOOD pattern: which gates blocked it, how many DISTINCT opportunities
(deduped to one row per pattern+direction+5-min bar), and what the block cost or
saved measured as MFE / MAE after the block over the rest of the session.

MFE-after-block is a CEILING, never a realizable P&L — declared, not implied.

Feed coverage is 2026-07-22 .. 2026-08-21 (28 sessions) — the archive does not
exist before that.  pytest-fixture rows are filtered exactly as
DEAD_SYSTEMS_AUDIT_2026-08-22 finding-1 requires.

READ-ONLY. psycopg2 read-only session + the on-disk decisions feed.
"""
import argparse
import collections
import datetime as dt
import glob
import json
import os
import statistics
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DSN = "postgresql://localhost/mems26"
EXPORT = os.path.expanduser("~/SierraChart_Data/v9_export")
BAD_PATTERNS = {"HFE", "STRATEGIC", "NO_SUCH_PATTERN", "TLB_LONG"}
GOOD = ["REACTIVE_LONG", "REACTIVE_SHORT", "INITIATIVE_LONG", "INITIATIVE_SHORT",
        "GB100", "TREND_STEP", "ZLR", "DOUBLE_BOTTOM_EE_LONG", "HTLB",
        "CONFLUENCE_RI_ZLR"]
POINT_USD = 5.0


def load_rows():
    fs = sorted(glob.glob(EXPORT + "/decisions_archive/*.jsonl")) + \
        sorted(glob.glob(EXPORT + "/gateway_decisions*.jsonl"))
    out, dropped = [], 0
    for f in fs:
        for l in open(f, errors="ignore"):
            l = l.strip()
            if not l:
                continue
            try:
                o = json.loads(l)
            except Exception:
                continue
            if o.get("pattern") in BAD_PATTERNS:
                dropped += 1
                continue
            out.append(o)
    return out, dropped, len(fs)


def load_bars(cur):
    cur.execute("""
        select (ts at time zone 'America/New_York') as et, high, low, close
        from v9_bars_5min_woodies
        where (ts at time zone 'America/New_York')::date between '2026-07-07' and '2026-08-21'
          and (ts at time zone 'America/New_York')::time >= '09:30'
          and (ts at time zone 'America/New_York')::time <  '16:00'
        order by ts""")
    days = collections.OrderedDict()
    for et, h, l, c in cur.fetchall():
        days.setdefault(et.date(), []).append(
            dict(t=et, h=float(h), l=float(l), c=float(c)))
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/gpg.json")
    ap.add_argument("--horizon", type=int, default=12, help="bars after the block")
    a = ap.parse_args()

    rows, dropped, nfiles = load_rows()
    print(f"[feed] files={nfiles} rows={len(rows)} pytest-fixture rows dropped={dropped}")
    ds = sorted({r.get("ts", "")[:10] for r in rows if r.get("ts")})
    print(f"[feed] span {ds[0]}..{ds[-1]}  days={len(ds)}")

    cn = psycopg2.connect(DSN)
    cn.set_session(readonly=True)
    cur = cn.cursor()
    days = load_bars(cur)

    # ---- dedup to one OPPORTUNITY per (pattern, direction, 5-min bar)
    def bar_key(ts_iso):
        try:
            t = dt.datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        except Exception:
            return None
        t = t.astimezone(dt.timezone(dt.timedelta(hours=-4)))  # ET during the era
        return t.replace(second=0, microsecond=0,
                         minute=(t.minute // 5) * 5).replace(tzinfo=None)

    opps = {}
    for r in rows:
        bk = bar_key(r.get("ts", ""))
        if bk is None:
            continue
        k = (r.get("pattern"), r.get("direction"), bk)
        # first decision of that bar wins; a later PASS upgrades it
        cur_r = opps.get(k)
        if cur_r is None:
            opps[k] = r
        elif cur_r.get("blocked_by") and not r.get("blocked_by"):
            opps[k] = r
    print(f"[dedup] raw rows={len(rows)} -> distinct opportunities={len(opps)}")

    def bar_index(d, t):
        bl = days.get(d)
        if not bl:
            return None
        for i, b in enumerate(bl):
            if b["t"].replace(tzinfo=None) == t:
                return i
        return None

    out = {"coverage": {"span": [ds[0], ds[-1]], "days": len(ds),
                        "raw_rows": len(rows), "opportunities": len(opps),
                        "fixture_rows_dropped": dropped},
           "per_pattern": {}}

    for p in GOOD:
        sub = [(k, v) for k, v in opps.items() if k[0] == p]
        if not sub:
            continue
        blocked = [(k, v) for k, v in sub if v.get("blocked_by")]
        passed = [(k, v) for k, v in sub if not v.get("blocked_by")]
        cnt = collections.Counter(str(v.get("blocked_by")) for k, v in blocked)
        row = {"opportunities": len(sub), "passed": len(passed),
               "blocked": len(blocked), "top_gates": {}}
        for gate, n in cnt.most_common(6):
            mfe_pts, mae_pts, used, unmatched, bad = [], [], 0, 0, 0
            for k, v in blocked:
                if str(v.get("blocked_by")) != gate:
                    continue
                ent = v.get("entry")
                if ent in (None, 0):
                    unmatched += 1
                    continue
                d = k[2].date()
                i = bar_index(d, k[2])
                if i is None:
                    unmatched += 1          # bar is outside RTH (hydration/pre-open)
                    continue
                seg = days[d][i + 1:i + 1 + a.horizon]
                if not seg:
                    unmatched += 1
                    continue
                # sanity: the decision's entry must sit on the tape of that bar.
                # Stale/garbage entries (feed_watchdog, restart rows) are 100s of
                # points away and would otherwise dominate every MFE sum.
                if abs(float(ent) - days[d][i]["c"]) > 15.0:
                    bad += 1
                    continue
                used += 1
                if k[1] == "LONG":
                    mfe_pts.append(max(b["h"] for b in seg) - float(ent))
                    mae_pts.append(float(ent) - min(b["l"] for b in seg))
                else:
                    mfe_pts.append(float(ent) - min(b["l"] for b in seg))
                    mae_pts.append(max(b["h"] for b in seg) - float(ent))
            row["top_gates"][gate] = dict(
                n=n, measured=used, unmatched_offRTH=unmatched, stale_entry=bad,
                mfe_pts_sum=round(sum(mfe_pts), 2),
                mfe_pts_med=round(statistics.median(mfe_pts), 2) if mfe_pts else 0.0,
                mae_pts_med=round(statistics.median(mae_pts), 2) if mae_pts else 0.0,
                mfe_usd_6c=round(sum(mfe_pts) * POINT_USD * 6, 2),
                mae_usd_6c=round(sum(mae_pts) * POINT_USD * 6, 2),
                # crude "who wins" read: opportunities whose MFE beat MAE
                mfe_gt_mae=sum(1 for x, y in zip(mfe_pts, mae_pts) if x > y),
            )
        out["per_pattern"][p] = row
        print(f"\n== {p}  opportunities={len(sub)}  passed={len(passed)}  blocked={len(blocked)}")
        for g, r in row["top_gates"].items():
            print(f"   {g:<26} n={r['n']:<4} meas={r['measured']:<4} "
                  f"offRTH={r['unmatched_offRTH']:<4} stale={r['stale_entry']:<3} "
                  f"MFE={r['mfe_pts_sum']:>7.2f}pt (${r['mfe_usd_6c']:>8.2f} @6c) "
                  f"medMFE={r['mfe_pts_med']:>6.2f} medMAE={r['mae_pts_med']:>6.2f} "
                  f"MFE>MAE {r['mfe_gt_mae']}/{r['measured']}")

    with open(a.json, "w") as f:
        json.dump(out, f, default=str)
    print("\n[out]", a.json)


if __name__ == "__main__":
    main()
