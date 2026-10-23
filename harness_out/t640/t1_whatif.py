# -*- coding: utf-8 -*-
"""T-642 (23.10 night) — a what-if OUTSIDE the harness: closer targets + an early exit, on the harness's own trades.

Michael 23.10: "לקרב את T1 למקום ריאלי יותר … לקרב את t2 ואת t3 … שתרחיק אותם או תממש אותם אם המחיר לא פועל כפי שהניחה".
For every filled trade of <tag> (81 days) one simple, identical management model runs on the 5-min bars
(v9_bars_5min_woodies) for each variant, so the variants compare like for like (the harness's own P&L is NOT
the baseline — its management is richer). Model: 5 contracts 2-2-1 (or the trade's count, split 40/40/20);
entry = fill at the fired bar's open; a bar touching both stop and target counts as STOP (conservative);
after T1 the stop goes to BE+1 tick; T2/T3 legs then run to their target or BE; anything open at 22:55 exits
at that close. Variants: base · t1 caps (0.8R/1R/1.2R) · close (T1≤1R, T2≤1.8R, T3≤2.6R) · aa (before T1,
two consecutive 5-min closes ≥0.25R against ⇒ exit at that close) · close+aa.
usage: python3 harness_out/t640/t1_whatif.py <tag>
"""
import json, glob, os, subprocess, sys, collections

PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
TICK = 0.25
USD = 5.0
WEEK = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]


def bars_of(day):
    out = subprocess.run([PSQL, "-d", "mems26", "-At", "-F", "|", "-c",
                          "select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close "
                          "from v9_bars_5min_woodies where ts >= '%s 16:30+03' and ts < '%s 23:00+03' order by ts" % (day, day)],
                         capture_output=True, text=True).stdout
    return [dict(zip(("t", "o", "h", "l", "c"), [l.split("|")[0]] + [float(x) for x in l.split("|")[1:]]))
            for l in out.strip().split("\n") if l.strip()]


def split(c):
    c = int(c or 5)
    if c >= 5:
        return [2, 2, c - 4]
    if c == 4:
        return [2, 1, 1]
    if c == 3:
        return [1, 1, 1]
    if c == 2:
        return [1, 1, 0]
    return [1, 0, 0]


def sim(tr, bars, t1, t2, t3, aa):
    d = 1 if tr["direction"] == "LONG" else -1
    fill = float(tr.get("fill_price") or tr["entry"])
    stop = float(tr.get("stop_initial") or tr["stop"])
    R = abs(fill - stop)
    if R <= 0:
        return 0.0
    legs = split(tr.get("contracts"))
    tg = [t1, t2 or t1, t3 or t2 or t1]
    open_legs = [i for i in range(3) if legs[i] > 0]
    pnl = 0.0
    t_il = str(tr.get("fired_il", ""))[:5]
    seg = [b for b in bars if b["t"] >= t_il]
    t1_done = False
    against = 0
    for b in seg:
        fav_hi = b["h"] if d == 1 else b["l"]
        adv_lo = b["l"] if d == 1 else b["h"]
        # stop first (conservative)
        if (adv_lo - stop) * d <= 0:
            for i in open_legs:
                pnl += legs[i] * (stop - fill) * d
            return pnl * USD
        for i in list(open_legs):
            if (fav_hi - tg[i]) * d >= 0:
                pnl += legs[i] * (tg[i] - fill) * d
                open_legs.remove(i)
                if i == 0 and not t1_done:
                    t1_done = True
                    stop = fill + d * TICK
        if not open_legs:
            return pnl * USD
        if aa and not t1_done:
            if (fill - b["c"]) * d >= 0.25 * R:
                against += 1
                if against >= 2:
                    for i in open_legs:
                        pnl += legs[i] * (b["c"] - fill) * d
                    return pnl * USD
            else:
                against = 0
    last = seg[-1]["c"] if seg else fill
    for i in open_legs:
        pnl += legs[i] * (last - fill) * d
    return pnl * USD


def variants(tr):
    d = 1 if tr["direction"] == "LONG" else -1
    fill = float(tr.get("fill_price") or tr["entry"])
    stop = float(tr.get("stop_initial") or tr["stop"])
    R = abs(fill - stop) or TICK
    tg = []
    for l in tr.get("legs") or []:
        x = l.get("target")
        if x and x not in tg:
            tg.append(float(x))
    t1 = float(tr.get("t1_target") or (tg[0] if tg else fill + d * R))
    t2 = tg[1] if len(tg) > 1 else t1 + d * R
    t3 = tg[2] if len(tg) > 2 else t2 + d * R

    def cap(t, k):
        return fill + d * min(abs(t - fill), k * R)
    return {
        "base": (t1, t2, t3, False),
        "t1_08R": (cap(t1, 0.8), t2, t3, False),
        "t1_1R": (cap(t1, 1.0), t2, t3, False),
        "t1_12R": (cap(t1, 1.2), t2, t3, False),
        "close": (cap(t1, 1.0), cap(t2, 1.8), cap(t3, 2.6), False),
        "close_keep3": (cap(t1, 1.0), cap(t2, 1.8), t3, False),   # the runner keeps its far target (the "extend" half)
        "aa": (t1, t2, t3, True),
        "close_aa": (cap(t1, 1.0), cap(t2, 1.8), cap(t3, 2.6), True),
    }


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "live"
    files = sorted(glob.glob("harness_out/t640/days/%s_2026-*.json" % tag))
    tot = collections.defaultdict(float)
    months = collections.defaultdict(lambda: collections.defaultdict(float))
    week = collections.defaultdict(lambda: collections.defaultdict(float))
    n = 0
    for f in files:
        day = os.path.basename(f)[len(tag) + 1:-5]
        j = json.load(open(f))
        trs = [t for t in j.get("trades", []) if t.get("filled")]
        if not trs:
            continue
        bars = bars_of(day)
        for tr in trs:
            n += 1
            for k, (a, b, c, aa) in variants(tr).items():
                p = sim(tr, bars, a, b, c, aa)
                tot[k] += p
                months[k][day[:7]] += p
                if day in WEEK:
                    week[k][day] += p
    print("tag %s · %d days · %d trades (same simplified model for every variant)" % (tag, len(files), n))
    for k in ("base", "t1_08R", "t1_1R", "t1_12R", "close", "close_keep3", "aa", "close_aa"):
        print("%-9s total %9.2f  Δ %+9.2f  months %s  week %s (Σ %+.2f)" % (
            k, tot[k], tot[k] - tot["base"], {m: round(v) for m, v in sorted(months[k].items())},
            {d[5:]: round(v) for d, v in sorted(week[k].items())}, sum(week[k].values())))


if __name__ == "__main__":
    main()
