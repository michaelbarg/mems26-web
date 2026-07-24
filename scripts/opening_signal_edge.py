#!/usr/bin/env python3
"""opening_signal_edge.py — which opening signals actually carry DIRECTION?

Tests Michael's hypothesis: does fusing level-crossing acceptance/rejection, volume,
prior-day close, gap and open-location identify the day direction better than the
current geometry-only detector (which scored ~53% at first commit)?

Per RTH day it computes each candidate signal's directional call and scores it against
the ACTUAL direction (RTH open→close, |move|<FLAT_PTS = range/excluded). Reports each
signal's hit-rate + how often it even fires (coverage).
"""
import os
import psycopg2

FLAT = 8.0


def load():
    c = psycopg2.connect(os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"))
    cur = c.cursor()
    cur.execute(
        "select (ts at time zone 'America/New_York')::date d from v9_bars_5min_woodies "
        "where symbol='MES' and (ts at time zone 'America/New_York')::time >= '09:30' "
        "and (ts at time zone 'America/New_York')::time < '16:00' group by d "
        "having count(*) >= 40 order by d")
    dates = [r[0] for r in cur.fetchall()]

    def rth(d):
        cur.execute(
            "select open,high,low,close,volume from v9_bars_5min_woodies where symbol='MES' "
            "and (ts at time zone 'America/New_York')::date=%s "
            "and (ts at time zone 'America/New_York')::time >= '09:30' "
            "and (ts at time zone 'America/New_York')::time < '16:00' order by ts", (d,))
        return [(float(o), float(h), float(l), float(cl), float(v or 0)) for o, h, l, cl, v in cur.fetchall()]

    rows = []
    vols_hist = []
    for d in dates:
        cur.execute("select max((ts at time zone 'America/New_York')::date) from v9_bars_5min_woodies "
                    "where symbol='MES' and (ts at time zone 'America/New_York')::date < %s", (d,))
        pd = cur.fetchone()[0]
        prev = rth(pd) if pd else None
        pvah = pval = None
        if pd:
            cur.execute("select vah_price,val_price from v9_tpo_sessions where trading_date=%s order by id desc limit 1",
                        (pd.isoformat(),))
            r = cur.fetchone()
            if r:
                pvah = float(r[0]) if r[0] is not None else None
                pval = float(r[1]) if r[1] is not None else None
        bars = rth(d)
        rows.append({"date": d.isoformat(), "bars": bars, "prev": prev,
                     "pvah": pvah, "pval": pval,
                     "pdh": max(b[1] for b in prev) if prev else None,
                     "pdl": min(b[2] for b in prev) if prev else None,
                     "opening_vol": sum(b[4] for b in bars[:6])})
        vols_hist.append(sum(b[4] for b in bars[:6]))
    c.close()
    med_openvol = sorted(vols_hist)[len(vols_hist) // 2]
    return rows, med_openvol


def sgn(x, thr=0.0):
    return "UP" if x > thr else ("DOWN" if x < -thr else None)


def main():
    rows, med_ov = load()
    signals = {}  # name -> [ (pred, actual) ]

    def rec(name, pred, actual):
        signals.setdefault(name, []).append((pred, actual))

    for r in rows:
        b = r["bars"]
        op = b[0][0]
        cl = b[-1][3]
        move = cl - op
        actual = sgn(move, FLAT)
        if actual is None:
            continue
        prev = r["prev"]
        b6c = b[5][3] if len(b) > 5 else b[-1][3]
        b6h = max(x[1] for x in b[:6]); b6l = min(x[2] for x in b[:6])

        # A) first-30min momentum (the geometry baseline)
        rec("A first-30m momentum", sgn(b6c - op, 2.0), actual)

        # B) gap vs prior close (gap-and-go)
        if prev:
            rec("B gap dir (open vs prev close)", sgn(op - prev[-1][3], 2.0), actual)

        # C) prior-day close momentum (continuation)
        if prev:
            rec("C prior-day direction", sgn(prev[-1][3] - prev[0][0], FLAT), actual)

        # D) open location: out-of-range -> take the break direction
        if r["pdh"] is not None and r["pdl"] is not None:
            if op > r["pdh"]:
                rec("D open beyond PDH/PDL", "UP", actual)
            elif op < r["pdl"]:
                rec("D open beyond PDH/PDL", "DOWN", actual)

        # E) level-break ACCEPTANCE in first 30m: closed & held beyond a key level
        refs_up = [x for x in (r["pdh"], r["pvah"]) if x is not None]
        refs_dn = [x for x in (r["pdl"], r["pval"]) if x is not None]
        acc = None
        if refs_up and b6c > max(refs_up) and b6l >= min(refs_up) - 1.0:
            acc = "UP"
        elif refs_dn and b6c < min(refs_dn) and b6h <= max(refs_dn) + 1.0:
            acc = "DOWN"
        if acc:
            rec("E level-break accepted (30m)", acc, actual)

        # F) opening volume conviction: high open-vol -> trust the 30m momentum; low -> skip
        if r["opening_vol"] >= med_ov:
            rec("F hi-vol + 30m momentum", sgn(b6c - op, 2.0), actual)
        else:
            rec("F' lo-vol + 30m momentum", sgn(b6c - op, 2.0), actual)

        # G) REFINED FUSION (Dalton conviction): trade the opening direction ONLY when
        #    volume confirms; direction = 30m momentum; if a level-break says the other
        #    way, it's a conflict -> SKIP. Low-vol = auction -> SKIP (no opening trade).
        mom = sgn(b6c - op, 2.0)
        hivol = r["opening_vol"] >= med_ov
        g = None
        if hivol and mom is not None and (acc is None or acc == mom):
            g = mom
        if g:                       # only the days it WOULD fire
            rec("G FUSION hi-vol+mom, accept-agrees", g, actual)

        # H) same but ALSO require prior-day continuation OR an accepted break (extra conviction)
        h = None
        if hivol and mom is not None and (acc == mom or (prev and sgn(prev[-1][3]-prev[0][0], FLAT) == mom)):
            h = mom
        if h:
            rec("H FUSION +prevday/accept confirm", h, actual)

    print(f"{'signal':34} {'hit-rate':>10} {'fires':>7}")
    print("-" * 54)
    for name in sorted(signals):
        pairs = [(p, a) for p, a in signals[name] if p is not None]
        if not pairs:
            print(f"{name:34} {'—':>10} {0:>7}")
            continue
        hit = sum(1 for p, a in pairs if p == a)
        print(f"{name:34} {hit}/{len(pairs)} = {100*hit/len(pairs):>3.0f}% {len(pairs):>7}")
    n_dir = sum(1 for r in rows if sgn(r['bars'][-1][3]-r['bars'][0][0], FLAT))
    print(f"\ndirectional days graded: {n_dir}  |  baseline (engine first-commit): 53%")


if __name__ == "__main__":
    main()
