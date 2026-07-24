#!/usr/bin/env python3
"""direction_accuracy_replay.py — real-time direction-ID accuracy over all RTH days.

Re-runs the VALIDATED day-type engine (classify_session) bar-by-bar, NO lookahead,
with the SAME directional context the live engine gets (prior-day H/L + prior VAH/VAL
— the inputs that drive the early acceptance-reclass direction). Records dir_bias
(UP/DOWN) as it evolves and compares to the day's ACTUAL direction (RTH open→close).

Checkpoints: COMMIT (first UP/DOWN call + time) · @60m (bar12) · @2h (bar24) · FINAL.
Range days (|move| < FLAT_PTS) are bucketed separately.
"""
import os
import psycopg2
from backend.v9.systems.day_type.classifier_core import classify_session

FLAT_PTS = 8.0
DIRS = ("UP", "DOWN")


def _ctx_for(cur, d):
    """prior-day H/L (pdh/pdl) + prior-day TPO VAH/VAL (pvah/pval) — the directional
    context the live classify_replay feeds the engine."""
    cur.execute(
        "select max((ts at time zone 'America/New_York')::date) "
        "from v9_bars_5min_woodies where symbol='MES' "
        "and (ts at time zone 'America/New_York')::date < %s", (d,))
    pdte = cur.fetchone()[0]
    pdh = pdl = pvah = pval = None
    if pdte:
        cur.execute(
            "select max(high), min(low) from v9_bars_5min_woodies where symbol='MES' "
            "and (ts at time zone 'America/New_York')::date = %s", (pdte,))
        r = cur.fetchone()
        pdh, pdl = (float(r[0]) if r[0] is not None else None,
                    float(r[1]) if r[1] is not None else None)
        cur.execute(
            "select vah_price, val_price from v9_tpo_sessions where trading_date=%s "
            "order by id desc limit 1", (pdte.isoformat(),))
        r = cur.fetchone()
        if r:
            pvah = float(r[0]) if r[0] is not None else None
            pval = float(r[1]) if r[1] is not None else None
    return pdh, pdl, pvah, pval


def load_days():
    c = psycopg2.connect(os.environ.get("DATABASE_URL", "postgresql://localhost/mems26"))
    cur = c.cursor()
    cur.execute(
        "select (ts at time zone 'America/New_York')::date d "
        "from v9_bars_5min_woodies where symbol='MES' "
        "and (ts at time zone 'America/New_York')::time >= '09:30' "
        "and (ts at time zone 'America/New_York')::time < '16:00' "
        "group by d having count(*) >= 40 order by d")
    dates = [r[0] for r in cur.fetchall()]
    days = []
    for d in dates:
        cur.execute(
            "select ts, open, high, low, close from v9_bars_5min_woodies "
            "where symbol='MES' and (ts at time zone 'America/New_York')::date=%s "
            "and (ts at time zone 'America/New_York')::time >= '09:30' "
            "and (ts at time zone 'America/New_York')::time < '16:00' order by ts", (d,))
        bars = [{"ts": ts, "o": float(o), "h": float(h), "l": float(l), "c": float(cl)}
                for ts, o, h, l, cl in cur.fetchall()]
        days.append((d, bars, _ctx_for(cur, d)))
    c.close()
    return days


def actual_dir(move):
    return "RANGE" if abs(move) < FLAT_PTS else ("UP" if move > 0 else "DOWN")


def trajectory(bars, ctx):
    pdh, pdl, pvah, pval = ctx
    n = len(bars)
    op = bars[0]["o"]
    traj = []
    for i in range(6, n + 1):
        kk = min(i, 12)
        ibh = max(b["h"] for b in bars[:kk])
        ibl = min(b["l"] for b in bars[:kk])
        r = classify_session(bars=bars[:i], ib_high=ibh, ib_low=ibl, open_price=op,
                             prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl,
                             is_eod=(i == n))
        traj.append((i, bars[i - 1]["ts"], r.get("dir_bias"), r.get("day_type")))
    return traj


def hhmm(ts):
    try:
        return ts.astimezone().strftime("%H:%M")
    except Exception:
        return str(ts)[11:16]


def main():
    days = load_days()
    out = []
    for d, bars, ctx in days:
        move = round(bars[-1]["c"] - bars[0]["o"], 2)
        traj = trajectory(bars, ctx)
        by_i = {i: db for i, _, db, _ in traj}
        commit = next(((i, ts, db) for i, ts, db, _ in traj if db in DIRS), None)
        flips = 0
        prev = None
        for _, _, db, _ in traj:
            if db in DIRS:
                if prev and db != prev:
                    flips += 1
                prev = db
        out.append({"date": d.isoformat(), "move": move, "actual": actual_dir(move),
                    "commit_time": hhmm(commit[1]) if commit else None,
                    "commit_dir": commit[2] if commit else None,
                    "d12": by_i.get(12), "d24": by_i.get(24),
                    "final": traj[-1][2] if traj else None,
                    "flips": flips, "daytype": traj[-1][3] if traj else None})

    hdr = (f"{'date':11} {'move':>7} {'actual':6} {'commit(t)':13} {'@60m':5} "
           f"{'@2h':5} {'final':5} C? F? flips")
    print(hdr); print("-" * len(hdr))
    gc = gf = tot = held = g12 = g24 = n12 = n24 = 0
    for r in out:
        gr = r["actual"] in DIRS
        cok = gr and r["commit_dir"] == r["actual"]
        fok = gr and r["final"] == r["actual"]
        if gr:
            tot += 1; gc += cok; gf += fok
            if cok and r["flips"] == 0:
                held += 1
            if r["d12"] in DIRS:
                n12 += 1; g12 += (r["d12"] == r["actual"])
            if r["d24"] in DIRS:
                n24 += 1; g24 += (r["d24"] == r["actual"])
        cm = ("=" if cok else "x") if (gr and r["commit_dir"]) else "."
        fm = ("=" if fok else "x") if (gr and r["final"]) else "."
        print(f"{r['date']:11} {r['move']:>7} {r['actual']:6} "
              f"{(r['commit_dir'] or '-')+'@'+(r['commit_time'] or '-'):13} "
              f"{str(r['d12'] or '-'):5} {str(r['d24'] or '-'):5} "
              f"{str(r['final'] or '-'):5} {cm:2} {fm:2} {r['flips']}")

    n_range = sum(1 for r in out if r["actual"] == "RANGE")
    print("\n── SUMMARY (directional days only) ──")
    print(f"total days {len(out)} | directional {tot} | range/flat {n_range}")
    if tot:
        print(f"COMMIT  (first call ~30min)  correct: {gc}/{tot} = {100*gc/tot:.0f}%")
        print(f"@60min  (IB-lock)            correct: {g12}/{n12} = {100*g12/n12:.0f}%  (of {n12} that had a call)")
        print(f"@2h                          correct: {g24}/{n24} = {100*g24/n24:.0f}%  (of {n24} that had a call)")
        print(f"FINAL   (end-of-day)         correct: {gf}/{tot} = {100*gf/tot:.0f}%")
        print(f"committed correctly AND held (0 flips): {held}/{tot} = {100*held/tot:.0f}%")
        avg_flips = sum(r['flips'] for r in out if r['actual'] in DIRS) / tot
        print(f"avg direction flips/day (directional): {avg_flips:.1f}")


if __name__ == "__main__":
    main()
