#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oracle_study.py — bar-by-bar "ORACLE vs FEASIBLE vs SYSTEM" study of every live-era
RTH session (2026-07-07 .. 2026-08-19).

Question it answers (Michael, 2026-08-20):
    "Go bar-by-bar over every past session, find where the RIGHT entry was, and what
     the day COULD have produced.  Thesis: on many days 2 trades held properly beat
     the system's many small trades."

Layers produced per session
---------------------------
  SWINGS      objective segmentation of the day into directional swings
              (ZigZag on 5-min bar highs/lows, threshold = max(1.0*ATR14_prev, 4.0pt))
  ORACLE-2    the 2 biggest swings, entered at the swing start price and exited at the
              swing end price  (perfect hindsight, minus commission + 1 tick/side slip)
  ORACLE-N    every swing, same mechanics                      (absolute ceiling)
  FEASIBLE-N  per swing, the EARLIEST *causal* rule-expressible trigger (no lookahead),
              structural stop, structural trailing exit         (realistic mechanics,
              hindsight ONLY in which swings are selected)
  FEASIBLE-2  the best 2 of FEASIBLE-N                          (= Michael's thesis ceiling)
  CAUSAL-ALL  fully blind: walk the session forward, take EVERY trigger, one position at
              a time, same stop/exit rules                      (NO hindsight at all)
  CAUSAL-2    the FIRST 2 triggers of the day only              (NO hindsight at all)
  SYSTEM      what MEMS26 actually booked that day (v9_trades, mode='live')

READ-ONLY.  Direct psycopg2 (never backend.v9.db.read — it can fall back to stale SQLite).
Writes nothing but stdout + the JSON dump given by --json.

Usage:  python3 scripts/oracle_study.py [--json /tmp/oracle_study.json]
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

# ---------------------------------------------------------------- constants
DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
D0, D1 = "2026-07-07", "2026-08-19"          # live era
WARM = "2026-06-25"                          # extra history for the prev-session ATR
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)  # ET

POINT_USD = 5.0        # MES: $5 per index point per contract (verified: #372 6.0pt/3c = $90)
TICK = 0.25
CONTRACTS = 4          # today's live size (MARGIN_FALLBACK 6->4)
COMM_RT = 1.50         # $ per contract, round turn
SLIP_TICKS = 1         # per side, applied against the trade

ZZ_ATR_MULT = 1.0
ZZ_MIN_PT = 4.0
ZZ_MAX_PT = 12.0       # cap so one wild session cannot blow the swing definition up

DEC_DIR = os.path.expanduser("~/SierraChart_Data/v9_export")


def money(pts, contracts=CONTRACTS):
    return pts * contracts * POINT_USD


def costs(contracts=CONTRACTS):
    return COMM_RT * contracts


# ---------------------------------------------------------------- data load
def load_bars(cur):
    cur.execute(
        """
        select (ts at time zone 'America/New_York') as et,
               open, high, low, close, volume
        from v9_bars_5min_woodies
        where (ts at time zone 'America/New_York')::date between %s and %s
          and (ts at time zone 'America/New_York')::time >= %s
          and (ts at time zone 'America/New_York')::time <  %s
        order by ts
        """,
        (WARM, D1, RTH0, RTH1),
    )
    days = collections.OrderedDict()
    for et, o, h, l, c, v in cur.fetchall():
        d = et.date()
        days.setdefault(d, []).append(
            dict(t=et, o=float(o), h=float(h), l=float(l), c=float(c),
                 v=float(v or 0))
        )
    return days


def atr_prev(days, d):
    """Mean true range over the PREVIOUS session's whole RTH -> known at 09:30 (causal).

    (The first version used only the last 14 bars of the prior session; those are the
    quietest bars of the day and produced a systematically too-small threshold.)
    """
    keys = [k for k in days if k < d]
    if not keys:
        return None
    prev = days[max(keys)]
    if len(prev) < 20:
        return None
    trs = []
    for i in range(1, len(prev)):
        b, p = prev[i], prev[i - 1]
        trs.append(max(b["h"] - b["l"], abs(b["h"] - p["c"]), abs(b["l"] - p["c"])))
    return statistics.fmean(trs)


def thr_for(days, d):
    a = atr_prev(days, d)
    raw = ZZ_MIN_PT if a is None else max(ZZ_ATR_MULT * a, ZZ_MIN_PT)
    return round(min(raw, ZZ_MAX_PT) * 4) / 4.0     # snap to tick


# ---------------------------------------------------------------- swings
def zigzag(bars, thr):
    """Alternating H/L pivots, computed on 5-min CLOSES.

    Closes (not intrabar H/L) because a 5-min MES bar is ~1x ATR wide: a high/low
    ZigZag with a ~1x ATR threshold flips inside single wide bars and shreds the day
    into dozens of fake 'swings' (measured: 49 legs / 520pt on 2026-07-07).

    A pivot is *confirmed* at the first bar whose close retraced `thr` from the running
    extreme close -> `confirm_i` is lookahead-free.  `i` (where the extreme printed) is
    hindsight and is used only by the ORACLE layer.  `price` is the bar's actual
    high/low at the pivot = the best price that ever traded there (true ceiling).
    """
    n = len(bars)
    if n < 3:
        return []
    C = [b["c"] for b in bars]
    piv = []
    hi = lo = C[0]
    hi_i = lo_i = 0
    dirn = 0
    for i in range(1, n):
        c = C[i]
        if dirn >= 0 and c > hi:
            hi, hi_i = c, i
        if dirn <= 0 and c < lo:
            lo, lo_i = c, i
        flip = None
        if dirn == 0:
            if hi - c >= thr and hi_i < i:
                flip = "H"
            elif c - lo >= thr and lo_i < i:
                flip = "L"
        elif dirn > 0 and hi - c >= thr:
            flip = "H"
        elif dirn < 0 and c - lo >= thr:
            flip = "L"
        if flip == "H":
            piv.append(dict(i=hi_i, kind="H", price=bars[hi_i]["h"], confirm_i=i))
            dirn = -1
            seg = C[hi_i:i + 1]
            lo = min(seg); lo_i = hi_i + seg.index(lo)
        elif flip == "L":
            piv.append(dict(i=lo_i, kind="L", price=bars[lo_i]["l"], confirm_i=i))
            dirn = 1
            seg = C[lo_i:i + 1]
            hi = max(seg); hi_i = lo_i + seg.index(hi)
    # terminal provisional pivot (a trend that ran into the close is real money)
    if piv:
        last = piv[-1]
        if dirn > 0 and last["kind"] == "L" and hi - C[last["i"]] >= thr:
            piv.append(dict(i=hi_i, kind="H", price=bars[hi_i]["h"], confirm_i=n - 1))
        elif dirn < 0 and last["kind"] == "H" and C[last["i"]] - lo >= thr:
            piv.append(dict(i=lo_i, kind="L", price=bars[lo_i]["l"], confirm_i=n - 1))
    return piv


def legs_from(bars, piv):
    """Swing legs = consecutive pivots, plus the opening leg (session open -> 1st pivot)."""
    if not piv:
        return []
    seq = [dict(i=0, kind=("L" if piv[0]["kind"] == "H" else "H"),
                price=bars[0]["o"], confirm_i=0, seed=True)] + piv
    out = []
    for a, b in zip(seq, seq[1:]):
        if b["i"] <= a["i"] or a["kind"] == b["kind"]:
            continue
        d = 1 if b["kind"] == "H" else -1
        out.append(dict(
            i0=a["i"], i1=b["i"], dir=d, p0=a["price"], p1=b["price"],
            pts=round(abs(b["price"] - a["price"]), 2),
            t0=bars[a["i"]]["t"], t1=bars[b["i"]]["t"],
            confirm_i=b["confirm_i"], seed=bool(a.get("seed")),
        ))
    return out


# ------------------------------------------------- causal (no-lookahead) triggers
def find_triggers(bars, piv, thr):
    """Every bar i is evaluated using ONLY bars[0..i] and pivots with confirm_i <= i.

    Four families, all rule-expressible in the live engine:
      BREAK  break of the last confirmed swing extreme, close-confirmed
      REJ    session-extreme rejection bar, taken out by the next bar's close
      STAIR  impulse >= thr, 1-3 bar pause holding >= 50%, close beyond the pause
      PB     impulse >= 0.8*thr, 1-3 bar pullback holding >= 38.2%, close beyond it
    """
    n = len(bars)
    out = []
    used_break = set()
    C = [b["c"] for b in bars]
    H = [b["h"] for b in bars]
    L = [b["l"] for b in bars]
    for i in range(3, n):
        conf = [p for p in piv if p["confirm_i"] <= i and p["i"] < i]
        # ---- BREAK
        lastH = next((p for p in reversed(conf) if p["kind"] == "H"), None)
        lastL = next((p for p in reversed(conf) if p["kind"] == "L"), None)
        if lastH and C[i] > lastH["price"] + TICK and C[i] > C[i - 1] \
                and ("H", lastH["i"]) not in used_break:
            used_break.add(("H", lastH["i"])); out.append(dict(i=i, dir=1, kind="BREAK"))
        if lastL and C[i] < lastL["price"] - TICK and C[i] < C[i - 1] \
                and ("L", lastL["i"]) not in used_break:
            used_break.add(("L", lastL["i"])); out.append(dict(i=i, dir=-1, kind="BREAK"))
        # ---- REJ (extreme rejection bar j = i-1, taken out at i)
        j = i - 1
        rng = H[j] - L[j]
        if rng >= 0.6 * thr:
            if L[j] < min(L[:j]) and C[j] >= L[j] + 0.6 * rng and C[i] > H[j]:
                out.append(dict(i=i, dir=1, kind="REJ"))
            if H[j] > max(H[:j]) and C[j] <= H[j] - 0.6 * rng and C[i] < L[j]:
                out.append(dict(i=i, dir=-1, kind="REJ"))
        # ---- STAIR / PB
        done = False
        for m in (1, 2, 3):                       # pause bars
            a, b = i - m, i                       # pause = bars[a..b-1]
            if a < 2:
                continue
            for w in (2, 3, 4, 5):                # impulse bars
                s = a - w
                if s < 0:
                    continue
                imp_lo = min(L[s:a]); imp_hi = max(H[s:a])
                imp = imp_hi - imp_lo
                if imp < 0.8 * thr:
                    continue
                up = C[a - 1] > C[s]
                pull_lo = min(L[a:b]); pull_hi = max(H[a:b])
                if up and C[i] > pull_hi and C[i] > C[i - 1] and pull_hi <= imp_hi + TICK:
                    hold = (pull_lo - imp_lo) / imp
                    kind = "STAIR" if (imp >= thr and hold >= 0.5) else \
                           ("PB" if hold >= 0.382 else None)
                    if kind:
                        out.append(dict(i=i, dir=1, kind=kind)); done = True; break
                if (not up) and C[i] < pull_lo and C[i] < C[i - 1] and pull_lo >= imp_lo - TICK:
                    hold = (imp_hi - pull_hi) / imp
                    kind = "STAIR" if (imp >= thr and hold >= 0.5) else \
                           ("PB" if hold >= 0.382 else None)
                    if kind:
                        out.append(dict(i=i, dir=-1, kind=kind)); done = True; break
            if done:
                break
    # de-dup: one trigger per (bar, direction), priority BREAK > STAIR > REJ > PB
    pr = {"BREAK": 0, "STAIR": 1, "REJ": 2, "PB": 3}
    best = {}
    for t in out:
        k = (t["i"], t["dir"])
        if k not in best or pr[t["kind"]] < pr[best[k]["kind"]]:
            best[k] = t
    return sorted(best.values(), key=lambda t: (t["i"], -t["dir"]))


# ---------------------------------------------------------------- trade mechanics
def sim_trade(bars, i, dirn, thr, contracts=CONTRACTS):
    """Enter on the CLOSE of trigger bar i (1 tick adverse slip).

    Stop  = structural: extreme of the last 3 bars incl. the trigger, +/- 1 tick
            (Michael's 5-min-candle-structure ruling), floored at 1.5pt.
    Exit  = 'held properly': trail on structure - out on the first close that gives
            back `thr` from the running extreme; otherwise stop; otherwise 15:55 close.
    Stop is checked before the trail inside a bar (conservative).
    """
    n = len(bars)
    entry = bars[i]["c"] + dirn * SLIP_TICKS * TICK
    if dirn > 0:
        stop = min(b["l"] for b in bars[max(0, i - 2):i + 1]) - TICK
    else:
        stop = max(b["h"] for b in bars[max(0, i - 2):i + 1]) + TICK
    risk = abs(entry - stop)
    if risk < 1.5:
        stop = entry - dirn * 1.5
        risk = 1.5
    if risk > 2.5 * thr:
        return None                              # setup too loose to be tradable
    ext = entry
    exit_p = exit_i = None
    reason = "EOD"
    for k in range(i + 1, n):
        b = bars[k]
        if dirn > 0 and b["l"] <= stop:
            exit_p, exit_i, reason = stop - SLIP_TICKS * TICK, k, "STOP"; break
        if dirn < 0 and b["h"] >= stop:
            exit_p, exit_i, reason = stop + SLIP_TICKS * TICK, k, "STOP"; break
        ext = max(ext, b["h"]) if dirn > 0 else min(ext, b["l"])
        if dirn > 0 and b["c"] <= ext - thr:
            exit_p, exit_i, reason = b["c"] - SLIP_TICKS * TICK, k, "TRAIL"; break
        if dirn < 0 and b["c"] >= ext + thr:
            exit_p, exit_i, reason = b["c"] + SLIP_TICKS * TICK, k, "TRAIL"; break
    if exit_p is None:
        exit_p, exit_i = bars[-1]["c"] - dirn * SLIP_TICKS * TICK, n - 1
    pts = dirn * (exit_p - entry)
    return dict(i=i, exit_i=exit_i, dir=dirn, entry=round(entry, 2), stop=round(stop, 2),
                exit=round(exit_p, 2), pts=round(pts, 2), reason=reason,
                risk=round(risk, 2), mfe=round(dirn * (ext - entry), 2),
                usd=round(money(pts, contracts) - costs(contracts), 2),
                t_in=bars[i]["t"], t_out=bars[exit_i]["t"])


def oracle_trade(leg, contracts=CONTRACTS):
    pts = leg["pts"] - 2 * SLIP_TICKS * TICK
    return round(money(pts, contracts) - costs(contracts), 2)


def sim_ladder(bars, i, dirn, thr, contracts=CONTRACTS):
    """MEMS-style management for the same entry: 1/4 at 1R, 1/4 at 2R, 1/4 at 3R,
    stop->BE after T1, runner on the structural trail.  Used to isolate how much of the
    gap is ENTRY/SELECTION vs EXIT MANAGEMENT ('held properly' vs 'many small trades')."""
    base = sim_trade(bars, i, dirn, thr, contracts)
    if not base:
        return None
    entry, stop0, R = base["entry"], base["stop"], base["risk"]
    q = contracts / 4.0
    tg = [entry + dirn * R * k for k in (1, 2, 3)]
    stop = stop0
    left = contracts
    pts = 0.0
    hit = 0
    ext = entry
    for k in range(i + 1, len(bars)):
        b = bars[k]
        if (dirn > 0 and b["l"] <= stop) or (dirn < 0 and b["h"] >= stop):
            pts += left * dirn * (stop - dirn * SLIP_TICKS * TICK - entry)
            left = 0
            break
        while hit < 3 and ((dirn > 0 and b["h"] >= tg[hit]) or (dirn < 0 and b["l"] <= tg[hit])):
            pts += q * dirn * (tg[hit] - entry)
            left -= q
            hit += 1
            if hit == 1:
                stop = entry
        ext = max(ext, b["h"]) if dirn > 0 else min(ext, b["l"])
        if left > 0 and ((dirn > 0 and b["c"] <= ext - thr) or (dirn < 0 and b["c"] >= ext + thr)):
            pts += left * dirn * (b["c"] - dirn * SLIP_TICKS * TICK - entry)
            left = 0
            break
    if left > 0:
        pts += left * dirn * (bars[-1]["c"] - dirn * SLIP_TICKS * TICK - entry)
    out = dict(base)
    out["usd"] = round(pts * POINT_USD - costs(contracts), 2)
    out["pts"] = round(pts / contracts, 2)
    return out


def causal_sequence(bars, trigs, thr, limit=None, cutoff=None, drift=False,
                    kinds=None, mode="trail"):
    """Fully blind: take triggers in time order, one position at a time.

    limit   max number of trades for the day (Michael's 'as few as 2')
    cutoff  only trigger bars strictly before this ET time
    drift   only take triggers that agree with the session's move-so-far (causal)
    kinds   restrict to these trigger families
    mode    'trail' = held properly · 'ladder' = MEMS-style 1R/2R/3R scale-out
    """
    out, busy = [], -1
    sim = sim_trade if mode == "trail" else sim_ladder
    op = bars[0]["o"]
    for t in trigs:
        if t["i"] <= busy:
            continue
        if kinds and t["kind"] not in kinds:
            continue
        if cutoff and bars[t["i"]]["t"].time() >= cutoff:
            continue
        if drift and (bars[t["i"]]["c"] - op) * t["dir"] <= 0:
            continue
        r = sim(bars, t["i"], t["dir"], thr)
        if not r:
            continue
        r["kind"] = t["kind"]
        out.append(r)
        busy = r["exit_i"]
        if limit and len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- system side
def load_trades(cur):
    cur.execute(
        """
        select id, pattern_id_at_entry, firing_system, direction,
               (entry_ts at time zone 'America/New_York'),
               (exit_ts   at time zone 'America/New_York'),
               entry_price, exit_price, stop, pnl_usd, pnl_r, exit_reason,
               day_type_at_entry
        from v9_trades
        where mode='live' and state='CLOSED' and entry_ts is not null
        order by entry_ts
        """
    )
    out = []
    for (tid, pat, sysn, d, ein, eout, ep, xp, st, pnl, pr, xr, dtype) in cur.fetchall():
        c = None
        try:
            risk = abs(float(ep) - float(st))
            if pr and risk >= 1.0:
                raw = float(pnl) / (float(pr) * risk * POINT_USD)
                if 0.9 <= raw <= 6.3 and abs(raw - round(raw)) <= 0.08:
                    c = int(round(raw))
        except Exception:
            pass
        out.append(dict(id=tid, pat=pat or "-", sys=sysn, dir=(1 if d == "LONG" else -1),
                        t_in=ein, t_out=eout, entry=float(ep) if ep is not None else None,
                        exit=float(xp) if xp is not None else None,
                        pnl=float(pnl or 0), reason=xr or "-", contracts=c,
                        day=ein.date(), day_type=dtype))
    return out


def load_decisions():
    """gateway decisions (archive + live + .bak), de-duped.  Coverage starts 2026-07-22."""
    files = sorted(glob.glob(DEC_DIR + "/decisions_archive/*.jsonl")) + \
            sorted(glob.glob(DEC_DIR + "/gateway_decisions*"))
    seen, out = set(), []
    for p in files:
        try:
            fh = open(p, errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                key = (o.get("ts"), o.get("pattern"), o.get("direction"),
                       o.get("entry"), o.get("blocked_by"), o.get("outcome"))
                if key in seen:
                    continue
                seen.add(key)
                try:
                    t = dt.datetime.fromisoformat(o["ts"])
                except Exception:
                    continue
                et = t.astimezone(dt.timezone(dt.timedelta(hours=-4))).replace(tzinfo=None)
                out.append(dict(t=et, day=et.date(), pat=o.get("pattern") or "-",
                                dir=(1 if (o.get("direction") or "") == "LONG" else -1),
                                entry=o.get("entry"), blocked=o.get("blocked_by"),
                                outcome=o.get("outcome") or "-"))
    return out


# ---------------------------------------------------------------- per-day study
def mfe_after(bars, from_t, until_t, ref, dirn):
    """Best excursion in trade direction between two wall-clock times (pts, >=0)."""
    best = 0.0
    for b in bars:
        if b["t"] < from_t or b["t"] > until_t:
            continue
        p = b["h"] if dirn > 0 else b["l"]
        best = max(best, dirn * (p - ref))
    return round(best, 2)


def price_at(bars, t):
    cand = [b for b in bars if b["t"] <= t]
    return (cand[-1]["c"] if cand else bars[0]["o"])


def study_day(d, bars, trades, decs, thr):
    piv = zigzag(bars, thr)
    legs = legs_from(bars, piv)
    trigs = find_triggers(bars, piv, thr)

    # --- ORACLE
    for lg in legs:
        lg["oracle_usd"] = oracle_trade(lg)
    big = sorted(legs, key=lambda x: -x["pts"])
    oracle2 = round(sum(l["oracle_usd"] for l in big[:2]), 2)
    oracleN = round(sum(l["oracle_usd"] for l in legs), 2)

    # --- FEASIBLE per leg: earliest causal trigger inside the leg window
    for lg in legs:
        cand = [t for t in trigs if t["dir"] == lg["dir"] and lg["i0"] <= t["i"] <= lg["i1"]]
        lg["feas"] = None
        for t in cand:
            r = sim_trade(bars, t["i"], t["dir"], thr)
            if r:
                r["kind"] = t["kind"]
                r["late_pts"] = round(lg["dir"] * (r["entry"] - lg["p0"]), 2)
                lg["feas"] = r
                break
    feas = [l["feas"] for l in legs if l["feas"]]
    feas2 = round(sum(sorted((f["usd"] for f in feas), reverse=True)[:2]), 2)
    feasN = round(sum(f["usd"] for f in feas), 2)

    # --- fully blind layers
    call = causal_sequence(bars, trigs, thr)
    c2 = causal_sequence(bars, trigs, thr, limit=2)
    causal_all = round(sum(t["usd"] for t in call), 2)
    causal2 = round(sum(t["usd"] for t in c2), 2)

    sysu = round(sum(t["pnl"] for t in trades), 2)
    return dict(day=str(d), thr=thr, n_bars=len(bars), legs=legs, trigs=trigs,
                n_legs=len(legs), n_feas=len(feas), n_trigs=len(trigs),
                oracle2=oracle2, oracleN=oracleN, feas2=feas2, feasN=feasN,
                causal_all=causal_all, causal2=causal2, n_causal=len(call),
                sys=sysu, n_sys=len(trades), causal_trades=call)


# ---------------------------------------------------------------- cause attribution
def attribute(res, bars, trades, decs, thr):
    """Split the FEASIBLE-vs-SYSTEM gap into causes, $ each.

    (a) never-detected        no gateway decision at all in the leg window
    (b) detected-but-blocked  decision blocked -> gate named
    (b2) shadow-only          decision fired but never became a live order
    (c) entered-late          live trade in the leg, entry worse than the feasible entry
    (d) exited-early          live trade in the leg, price kept going after the exit
    (e) size-too-small        live trade in the leg with < CONTRACTS contracts
    (f) noise                 live trade that maps to NO major swing
    """
    causes = collections.Counter()
    gates = collections.Counter()
    detail = []
    have_arch = any(x["day"] == res_day(res) for x in decs)
    used_trades = set()
    for lg in res["legs"]:
        f = lg["feas"]
        if not f:
            continue
        t0, t1 = lg["t0"], lg["t1"] + dt.timedelta(minutes=15)
        mine = [t for t in trades if t["dir"] == lg["dir"] and t0 <= t["t_in"] <= t1]
        if mine:
            tr = min(mine, key=lambda t: t["t_in"])
            used_trades.add(tr["id"])
            c = tr["contracts"] or CONTRACTS
            late = 0.0 if tr["entry"] is None else \
                max(0.0, lg["dir"] * (tr["entry"] - f["entry"]))
            if late >= 1.0:
                causes["c_late"] += money(late, c); detail.append(
                    (lg["t0"], "late", tr["id"], round(money(late, c), 2), f"{late:.2f}pt"))
            xt = tr["t_out"] or bars[-1]["t"]
            xref = tr["exit"] if tr["exit"] is not None else price_at(bars, xt)
            add = mfe_after(bars, xt, lg["t1"], xref, lg["dir"])
            if add >= 1.0 and tr["pnl"] > -1e-9:
                causes["d_early_exit"] += money(add, c); detail.append(
                    (lg["t0"], "early_exit", tr["id"], round(money(add, c), 2), f"{add:.2f}pt"))
            if c < CONTRACTS and f["usd"] > 0:
                causes["e_size"] += f["usd"] * (CONTRACTS - c) / CONTRACTS
                detail.append((lg["t0"], "size", tr["id"],
                               round(f["usd"] * (CONTRACTS - c) / CONTRACTS, 2), f"{c}c"))
            continue
        if f["usd"] <= 0:
            causes["skip_saved"] += f["usd"]      # not taking it SAVED money
            continue
        dd = [x for x in decs if x["dir"] == lg["dir"] and t0 <= x["t"] <= t1]
        if not have_arch:
            causes["z_no_archive"] += f["usd"]
            detail.append((lg["t0"], "no_archive", "-", f["usd"], f["kind"]))
        elif not dd:
            causes["a_never_detected"] += f["usd"]
            detail.append((lg["t0"], "never_detected", "-", f["usd"], f["kind"]))
        else:
            blk = [x for x in dd if x["blocked"]]
            if blk:
                g = collections.Counter(x["blocked"] for x in blk).most_common(1)[0][0]
                causes["b_blocked"] += f["usd"]; gates[g] += f["usd"]
                detail.append((lg["t0"], "blocked:" + g, "-", f["usd"], f["kind"]))
            else:
                causes["b2_shadow_only"] += f["usd"]
                detail.append((lg["t0"], "shadow_only", "-", f["usd"], f["kind"]))
    noise = [t for t in trades if t["id"] not in used_trades]
    causes["f_noise_trades"] += sum(t["pnl"] for t in noise)
    return causes, gates, detail, len(noise)


def res_day(res):
    return dt.date.fromisoformat(res["day"])


# ---------------------------------------------------------------- sensitivity grid
VARIANTS = [
    ("N=1  trail",                dict(limit=1)),
    ("N=2  trail",                dict(limit=2)),
    ("N=3  trail",                dict(limit=3)),
    ("N=4  trail",                dict(limit=4)),
    ("N=inf trail",               dict()),
    ("N=2  ladder(MEMS mgmt)",    dict(limit=2, mode="ladder")),
    ("N=inf ladder(MEMS mgmt)",   dict(mode="ladder")),
    ("N=2  trail  cutoff12:30",   dict(limit=2, cutoff=dt.time(12, 30))),
    ("N=inf trail cutoff12:30",   dict(cutoff=dt.time(12, 30))),
    ("N=inf trail cutoff11:30",   dict(cutoff=dt.time(11, 30))),
    ("N=2  trail  +drift",        dict(limit=2, drift=True)),
    ("N=inf trail +drift",        dict(drift=True)),
    ("N=2  trail  +drift c12:30", dict(limit=2, drift=True, cutoff=dt.time(12, 30))),
    ("N=inf trail +drift c12:30", dict(drift=True, cutoff=dt.time(12, 30))),
    ("N=2  BREAK/STAIR only",     dict(limit=2, kinds={"BREAK", "STAIR"})),
    ("N=inf BREAK/STAIR only",    dict(kinds={"BREAK", "STAIR"})),
    ("N=inf STAIR only",          dict(kinds={"STAIR"})),
    ("N=2  STAIR only",           dict(limit=2, kinds={"STAIR"})),
    ("N=inf STAIR only c12:30",   dict(kinds={"STAIR"}, cutoff=dt.time(12, 30))),
    ("N=1  STAIR only",           dict(limit=1, kinds={"STAIR"})),
    ("N=1  trail cutoff12:30",    dict(limit=1, cutoff=dt.time(12, 30))),
    ("N=2  ladder c12:30",        dict(limit=2, mode="ladder", cutoff=dt.time(12, 30))),
]

# variants carried per-day into the report table
HEAD = [
    ("c1", dict(limit=1)),
    ("c2", dict(limit=2)),
    ("c2cut", dict(limit=2, cutoff=dt.time(12, 30))),
    ("c2lad", dict(limit=2, mode="ladder")),
    ("stair", dict(kinds={"STAIR"})),
]


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/oracle_study.json")
    ap.add_argument("--verbose-day", default=None)
    a = ap.parse_args()

    cn = psycopg2.connect(DSN); cn.set_session(readonly=True, autocommit=True)
    cur = cn.cursor()
    days = load_bars(cur)
    trades = load_trades(cur)
    decs = load_decisions()
    cn.close()

    lo, hi = dt.date.fromisoformat(D0), dt.date.fromisoformat(D1)
    tot = collections.Counter()
    causes = collections.Counter()
    gates = collections.Counter()
    rows, alldetail = [], []
    print("day        thr  bars sw  sysN  sys$     causal2  causalAll  feas2    feasN    "
          "orc2     orcN")
    for d in sorted(days):
        if not (lo <= d <= hi):
            continue
        bars = days[d]
        if len(bars) < 20:
            continue
        thr = thr_for(days, d)
        td = [t for t in trades if t["day"] == d]
        dd = [x for x in decs if x["day"] == d]
        r = study_day(d, bars, td, dd, thr)
        c, g, det, nnoise = attribute(r, bars, td, dd, thr)
        causes.update(c); gates.update(g)
        alldetail += [(str(d),) + x[1:] for x in det]
        r["causes"] = dict(c); r["noise_n"] = nnoise
        for nm, kw in HEAD:
            r[nm] = round(sum(t["usd"] for t in
                              causal_sequence(bars, r["trigs"], thr, **kw)), 2)
        r["swing_top"] = [dict(t0=str(l["t0"])[11:16], t1=str(l["t1"])[11:16],
                               dir=l["dir"], pts=l["pts"],
                               late=(l["feas"]["late_pts"] if l["feas"] else None),
                               kind=(l["feas"]["kind"] if l["feas"] else None),
                               feas=(l["feas"]["usd"] if l["feas"] else None))
                          for l in sorted(r["legs"], key=lambda x: -x["pts"])[:3]]
        rows.append(r)
        for k in ("sys", "causal2", "causal_all", "feas2", "feasN", "oracle2", "oracleN",
                  "c1", "c2cut", "c2lad", "stair"):
            tot[k] += r[k]
        print(f"{d}  {thr:4.2f} {len(bars):4d} {len(r['legs']):2d} {r['n_sys']:5d} "
              f"{r['sys']:8.2f} {r['causal2']:8.2f} {r['causal_all']:9.2f} "
              f"{r['feas2']:8.2f} {r['feasN']:8.2f} {r['oracle2']:8.2f} {r['oracleN']:8.2f}")
        if a.verbose_day and str(d) == a.verbose_day:
            for lg in r["legs"]:
                f = lg["feas"]
                print("   leg", lg["t0"].strftime("%H:%M"), "->", lg["t1"].strftime("%H:%M"),
                      f"{'LONG' if lg['dir'] > 0 else 'SHORT':5s}", f"{lg['pts']:6.2f}pt",
                      f"orc={lg['oracle_usd']:8.2f}",
                      ("feas=%8.2f %-5s late=%5.2fpt in=%s out=%s %s" % (
                          f["usd"], f["kind"], f["late_pts"], f["t_in"].strftime("%H:%M"),
                          f["t_out"].strftime("%H:%M"), f["reason"])) if f else "feas=   none")

    print("\nTOTAL  n=%d  sys=%.2f  causal2=%.2f  causalAll=%.2f  feas2=%.2f  feasN=%.2f  "
          "orc2=%.2f  orcN=%.2f" % (len(rows), tot["sys"], tot["causal2"], tot["causal_all"],
                                    tot["feas2"], tot["feasN"], tot["oracle2"], tot["oracleN"]))
    print("\nCAUSES ($):")
    for k, v in sorted(causes.items(), key=lambda kv: -abs(kv[1])):
        print(f"   {k:18s} {v:10.2f}")
    print("\nGATES that blocked feasible money ($):")
    for k, v in gates.most_common():
        print(f"   {k:28s} {v:9.2f}")

    # ---- swing anatomy
    allpts = [l["pts"] for r in rows for l in r["legs"]]
    late = [l["feas"]["late_pts"] for r in rows for l in r["legs"] if l["feas"]]
    nfeas = sum(1 for r in rows for l in r["legs"] if l["feas"])
    print("\nSWING ANATOMY  swings=%d (%.1f/day)  median %.2fpt  mean %.2fpt  "
          "top-2/day median %.2fpt" % (
              len(allpts), len(allpts) / len(rows), statistics.median(allpts),
              statistics.fmean(allpts),
              statistics.median([l["pts"] for r in rows
                                 for l in sorted(r["legs"], key=lambda x: -x["pts"])[:2]])))
    print("   swings with a causal trigger: %d/%d (%.0f%%)   lateness median %.2fpt  "
          "mean %.2fpt  (= how much of the swing the earliest honest signal gives away)" % (
              nfeas, len(allpts), 100.0 * nfeas / len(allpts),
              statistics.median(late), statistics.fmean(late)))
    trg = [l for r in rows for l in r["legs"] if l["feas"]]
    ratio = [l["feas"]["late_pts"] / l["pts"] for l in trg if l["pts"] > 0]
    fus = [l["feas"]["usd"] for l in trg]
    print("   on those swings: median size %.2fpt · median lateness %.0f%% of the swing · "
          "median left %.2fpt · feasible $ median %.2f · %.0f%% positive" % (
              statistics.median([l["pts"] for l in trg]), 100 * statistics.median(ratio),
              statistics.median([l["pts"] - l["feas"]["late_pts"] for l in trg]),
              statistics.median(fus), 100.0 * sum(1 for x in fus if x > 0) / len(fus)))
    print("   system live trades: %d (%.2f/day)  avg $/trade %.2f" % (
        sum(r["n_sys"] for r in rows), sum(r["n_sys"] for r in rows) / len(rows),
        tot["sys"] / max(1, sum(r["n_sys"] for r in rows))))

    # ---- sensitivity grid (all layers are fully causal / no-lookahead)
    print("\nSENSITIVITY (blind, no-lookahead variants)   total$   n   win%  green-days")
    kindstat = collections.Counter(); kindn = collections.Counter()
    for name, kw in VARIANTS:
        s = n = w = g = 0
        for r in rows:
            bars = days[res_day(r)]
            tr = causal_sequence(bars, r["trigs"], r["thr"], **kw)
            v = sum(t["usd"] for t in tr)
            s += v; n += len(tr); w += sum(1 for t in tr if t["usd"] > 0); g += (1 if v > 0 else 0)
            if name == "N=inf trail":
                for t in tr:
                    kindstat[t["kind"]] += t["usd"]; kindn[t["kind"]] += 1
        print(f"   {name:28s} {s:10.2f} {n:4d} {(100.0*w/n if n else 0):5.1f}  {g:2d}/{len(rows)}")
    print("\nBY TRIGGER FAMILY (N=inf trail):")
    for k, v in kindstat.most_common():
        print(f"   {k:8s} n={kindn[k]:4d}  {v:9.2f}   avg {v/kindn[k]:7.2f}")

    # ---- robustness of the headline layers
    print("\nROBUSTNESS (per-day $ distribution)")
    jul = [r for r in rows if r["day"] < "2026-08-01"]
    aug = [r for r in rows if r["day"] >= "2026-08-01"]
    for nm in ("sys", "c1", "causal2", "c2cut", "c2lad", "stair", "causal_all"):
        v = sorted(r[nm] for r in rows)
        best = max(v); worst = min(v)
        print(f"   {nm:10s} tot {sum(v):9.2f}  med {statistics.median(v):8.2f}  "
              f"green {sum(1 for x in v if x > 0):2d}/{len(v)}  best {best:8.2f}  "
              f"worst {worst:8.2f}  ex-best {sum(v)-best:9.2f}  ex-worst {sum(v)-worst:9.2f}  "
              f"JUL {sum(r[nm] for r in jul):8.2f}  AUG {sum(r[nm] for r in aug):8.2f}")

    with open(a.json, "w") as fh:
        json.dump(dict(rows=[{k: v for k, v in r.items()
                              if k not in ("legs", "trigs", "causal_trades")} for r in rows],
                       detail=alldetail, causes=dict(causes), gates=dict(gates),
                       totals=dict(tot)), fh, indent=1, default=str)
    print("\njson ->", a.json)


if __name__ == "__main__":
    main()
