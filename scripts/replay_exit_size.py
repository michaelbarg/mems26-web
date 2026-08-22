#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""replay_exit_size.py — X1..X4: every proposed EXIT-side and SIZING change,
replayed separately and combined, over every live-era session (2026-07-07 .. 08-21).

Michael 2026-08-22: "stop answering yes/no — replay it and show tables."

WHAT THIS IS (and is NOT)
-------------------------
It is a POLICY SWITCHBOARD on top of the engines that already exist. Nothing here
re-implements bars, swings, trades, ladders or scratch thresholds:

  scripts/oracle_study.py                       load_bars / load_trades / constants
                                                (the engine that measured +$2,315)
  scripts/replay_f5_runner_trail.py             ladder() / tranche_targets() /
                                                be_trigger_index()  (the DLL's ladder)
  scripts/week_replay.py                        scratch_threshold() / fixed_threshold() /
                                                atr_threshold()  (S6 MAE-scratch, read
                                                from config/mae_scratch.yaml)
  backend/v9/services/trade_manager/swing_trail confirmed pivots + rev threshold
  backend/v9/services/trade_manager/scale_in    should_scale_in()  (the LIVE rule)

Every arm runs the SAME bar loop with the SAME real entries / real initial stops /
real targets / real size, so an arm-to-arm delta is the policy and nothing else.

ARMS
----
X1  exit rules       LADDER (pre-F5) · BASE (today) · -scratch · +TAR · struct-break
                     runner · struct-break + no-scratch (= X1 as specced) · all-legs
X2  last-10-minutes  baseline · flatten at T-10 · tighten to BE+structure at T-10
X3  scale-in         live rule vs 0.5xATR trigger / >=1.5R room / extreme-guard /
                     ONE structural stop on the AVERAGED position / all combined
X4  S2xS4 confluence add +2c when the OTHER system produces a gate-passing
                     candidate in the same direction while a trade is open

3 slippage levels (0 / 1 / 2 ticks, adverse on every market-type fill; resting
limit targets fill at their price). Commission $1.50/contract round-turn is in
every number.

READ-ONLY. Direct psycopg2 (never backend.v9.db.read). Writes stdout + --json only.

Usage:
    python3 scripts/replay_exit_size.py --json /tmp/replay_exit_size.json
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import glob
import importlib.util
import json
import os
import statistics
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.v9.services.trade_manager.swing_trail import (  # noqa: E402
    swing_rev_threshold, last_confirmed_swing, swing_trail_stop,
)
from backend.v9.services.trade_manager.scale_in import (  # noqa: E402
    ScaleInCfg, should_scale_in,
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


OR = _load("oracle_study")            # bars + trades + constants
F5 = _load("replay_f5_runner_trail")  # the DLL ladder + tranche->target map
WR = _load("week_replay")             # the S6 MAE-scratch thresholds (from yaml)

POINT_USD = OR.POINT_USD              # $5 / point / contract (MES)
TICK = OR.TICK                        # 0.25
COMM_RT = OR.COMM_RT                  # $1.50 / contract round-turn

D0, D1 = "2026-07-07", "2026-08-21"   # live era, incl. yesterday
RTH_CLOSE = dt.time(16, 0)
EOD_BAR = dt.time(15, 55)             # last bar; its close IS 16:00 (EOD_FLATTEN_V1)
T10_BAR = dt.time(15, 45)             # this bar's close is 15:50 = T-10min exactly
DEC_DIR = os.path.expanduser("~/SierraChart_Data/v9_export")


# ─────────────────────────────────────────────────────────────── helpers
def atr14(bars):
    """ATR14 per bar index — week_replay.atr_series on the oracle bar shape."""
    return WR.atr_series([dict(high=b["h"], low=b["l"], close=b["c"]) for b in bars])


def struct_dir_bias(bars, k, rev):
    """Causal structural trend proxy for scale_in's `dir_bias`.

    The live value comes from direction_compass (not reconstructible offline).
    The honest offline stand-in: the last CONFIRMED pivot on closes up to bar k.
    A confirmed LOW means the market is in an up-leg -> UP. Same object the trail
    uses, so both sides of every X3 delta see the identical bias.
    """
    lo = last_confirmed_swing(bars[:k + 1], "LONG", rev)
    hi = last_confirmed_swing(bars[:k + 1], "SHORT", rev)
    if lo is None and hi is None:
        return None
    if hi is None:
        return "UP"
    if lo is None:
        return "DOWN"
    return "UP" if lo["i"] > hi["i"] else "DOWN"


def next_struct_level(bars, k, dirn, rev):
    """The next structural level standing in the way, or None when there is none.

    LONG  -> the nearest confirmed swing HIGH / session high ABOVE price.
    SHORT -> the nearest confirmed swing LOW  / session low  BELOW price.

    **None means open air, not zero room.** Price at a new session extreme has no
    overhead structure at all — that is the most room possible, not the least.
    (The first version returned `px + 1 tick` there, which inverted the test and
    blocked every add in a trend day; caught by the 08-03/08-04 arms reading 0.)
    """
    piv_hi = last_confirmed_swing(bars[:k + 1], "SHORT", rev)   # a confirmed H
    piv_lo = last_confirmed_swing(bars[:k + 1], "LONG", rev)    # a confirmed L
    px = bars[k]["c"]
    if dirn > 0:
        cand = [p["price"] for p in (piv_hi,) if p and p["price"] > px]
        hi = max(b["h"] for b in bars[:k + 1])
        if hi > px:
            cand.append(hi)
        return min(cand) if cand else None
    cand = [p["price"] for p in (piv_lo,) if p and p["price"] < px]
    lo = min(b["l"] for b in bars[:k + 1])
    if lo < px:
        cand.append(lo)
    return max(cand) if cand else None


def dist_from_session_extreme(bars, k, dirn):
    """How far the current bar's extreme is from the session extreme in the
    direction we would be ADDING into (0 = we are adding exactly at the edge)."""
    if dirn > 0:
        hi = max(b["h"] for b in bars[:k + 1])
        return round(hi - bars[k]["h"], 2)
    lo = min(b["l"] for b in bars[:k + 1])
    return round(bars[k]["l"] - lo, 2)


def structural_break_close(bars, k, dirn, rev):
    """True when bar k CLOSES beyond the last confirmed swing that must hold.

    LONG  -> close < last confirmed swing LOW.  SHORT -> close > swing HIGH.
    Confirmed pivots only => lookahead-free. Close-only => a wick does not exit
    (that is the whole point of 'structural', vs the stop which is intrabar).
    """
    sw = last_confirmed_swing(bars[:k + 1], "LONG" if dirn > 0 else "SHORT", rev)
    if sw is None or sw["i"] >= k:
        return False
    c = bars[k]["c"]
    return (c < sw["price"]) if dirn > 0 else (c > sw["price"])


# ─────────────────────────────────────────────────── the one bar loop
def simulate(bars, i0, dirn, entry, stop0, targets, qtys, *, rev, slip_ticks=1,
             pattern="", atrs=None,
             mae_mode="atr",          # "off" | "fixed" | "atr"  (S6 MAE scratch)
             tar=False,               # S6_TARGET_APPROACH_REALIZE_V1
             trail="f5",              # None | "f5" (stop-trail) | "struct" (close-break)
             trail_legs=1,            # how many tranches from the end are target-less
             t10=None,                # None | "flatten" | "tighten"
             stop_override=None,      # (from_bar_index, price) — X3/X4 combined stop
             ):
    """One trade, bar by bar, from i0 = the first FULL bar after the entry.

    Order inside a bar (mirrors bar_level_detector): MAE-scratch -> stop -> targets
    -> TAR -> trail -> T-10 -> EOD.  Stop before target = conservative.
    Slippage is charged on every market-type fill (stop / scratch / flatten /
    close-exit); a resting limit target fills at its price.
    """
    n = len(bars)
    slip = slip_ticks * TICK
    left = list(qtys)
    tg = list(targets)
    total = sum(qtys)
    if trail:
        for j in range(1, min(int(trail_legs), max(1, len(tg) - 1)) + 1):
            tg[-j] = None
    stop = stop0
    be = entry + dirn * TICK
    be_idx = F5.be_trigger_index(len(qtys))
    stop_dist = abs(entry - stop0)
    banked = 0.0
    mfe = 0.0
    exit_i = n - 1
    reasons = []
    t1_done = False
    approach_bars = 0
    n_tighten = 0

    for k in range(i0, n):
        b = bars[k]
        mfe = max(mfe, dirn * ((b["h"] if dirn > 0 else b["l"]) - entry))

        # 0. S6 MAE scratch — pre-T1 only, evaluated before the stop (live order)
        if mae_mode != "off" and not t1_done and any(left):
            a = atrs[k] if atrs and k < len(atrs) else 0.0
            thr = WR.scratch_threshold(mae_mode, pattern, a, stop_dist)
            if thr is not None:
                mae = (entry - b["l"]) if dirn > 0 else (b["h"] - entry)
                if mae >= thr:
                    fill = b["c"] - dirn * slip
                    for gi, q in enumerate(left):
                        if q:
                            banked += q * dirn * (fill - entry); left[gi] = 0
                    reasons.append("MAE_SCRATCH"); exit_i = k
                    break

        # 1. stop
        if (dirn > 0 and b["l"] <= stop) or (dirn < 0 and b["h"] >= stop):
            fill = stop - dirn * slip
            for gi, q in enumerate(left):
                if q:
                    banked += q * dirn * (fill - entry); left[gi] = 0
            reasons.append("STOP"); exit_i = k
            break

        # 2. targets (resting limits — fill at price)
        for gi, q in enumerate(left):
            if not q or tg[gi] is None:
                continue
            t = float(tg[gi])
            if (dirn > 0 and b["h"] >= t) or (dirn < 0 and b["l"] <= t):
                banked += q * dirn * (t - entry)
                left[gi] = 0
                reasons.append("T%d" % gi)
                if gi >= be_idx:
                    t1_done = True
                    if (dirn > 0 and be > stop) or (dirn < 0 and be < stop):
                        stop = be
        if not any(left):
            exit_i = k
            break

        # 3. TARGET_APPROACH_REALIZE — within 1.0pt of the pending target for
        #    >=2 bars and the bar closes back toward entry -> flatten the rest.
        if tar:
            pend = next((float(tg[gi]) for gi, q in enumerate(left)
                         if q and tg[gi] is not None), None)
            if pend is not None:
                close_px = b["h"] if dirn > 0 else b["l"]
                near = (0 <= dirn * (pend - close_px) <= 1.0)
                approach_bars = approach_bars + 1 if near else 0
                reject = dirn * (b["c"] - b["o"]) < 0
                if near and approach_bars >= 2 and reject:
                    fill = b["c"] - dirn * slip
                    for gi, q in enumerate(left):
                        if q:
                            banked += q * dirn * (fill - entry); left[gi] = 0
                    reasons.append("TARGET_APPROACH_REALIZE"); exit_i = k
                    break

        # 4. runner exit policy (only after the T1 leg banked — runner-only)
        if trail and not any(left[:be_idx + 1]):
            if trail == "f5":
                anchor = swing_trail_stop(bars[:k + 1],
                                          "LONG" if dirn > 0 else "SHORT",
                                          rev=rev, offset_ticks=1)
                if anchor is not None:
                    cand = max(anchor, be) if dirn > 0 else min(anchor, be)
                    if (dirn > 0 and cand > stop) or (dirn < 0 and cand < stop):
                        stop = round(cand, 2)
            elif trail == "struct":
                if structural_break_close(bars, k, dirn, rev):
                    fill = b["c"] - dirn * slip
                    for gi, q in enumerate(left):
                        if q:
                            banked += q * dirn * (fill - entry); left[gi] = 0
                    reasons.append("STRUCT_BREAK"); exit_i = k
                    break

        # 4b. an externally imposed combined stop (X3 C4 / X4)
        if stop_override and k >= stop_override[0]:
            cand = float(stop_override[1])
            if (dirn > 0 and cand > stop) or (dirn < 0 and cand < stop):
                stop = round(cand, 2)

        # 5. last-10-minutes rule
        if t10 and b["t"].time() >= T10_BAR and any(left):
            if t10 == "flatten":
                fill = b["c"] - dirn * slip
                for gi, q in enumerate(left):
                    if q:
                        banked += q * dirn * (fill - entry); left[gi] = 0
                reasons.append("T10_FLATTEN"); exit_i = k
                break
            if t10 in ("tighten", "tighten3"):
                if t10 == "tighten":
                    # BE + last CONFIRMED swing, never widen
                    anchor = swing_trail_stop(bars[:k + 1],
                                              "LONG" if dirn > 0 else "SHORT",
                                              rev=rev, offset_ticks=1)
                    cand = be if anchor is None else (max(anchor, be) if dirn > 0
                                                      else min(anchor, be))
                else:
                    # BE + the last 3 bars' structure (a T-10 chandelier)
                    w = bars[max(0, k - 2):k + 1]
                    cand = (min(b2["l"] for b2 in w) - TICK) if dirn > 0 \
                        else (max(b2["h"] for b2 in w) + TICK)
                    cand = max(cand, be) if dirn > 0 else min(cand, be)
                if (dirn > 0 and cand > stop) or (dirn < 0 and cand < stop):
                    stop = round(cand, 2)
                    n_tighten += 1
                    reasons.append("T10_TIGHTEN")

        # 6. EOD flatten (EOD_FLATTEN_V1)
        if b["t"].time() >= EOD_BAR and any(left):
            fill = b["c"] - dirn * slip
            for gi, q in enumerate(left):
                if q:
                    banked += q * dirn * (fill - entry); left[gi] = 0
            reasons.append("EOD"); exit_i = k
            break

    if any(left):                                   # feed gap — close on last bar
        fill = bars[-1]["c"] - dirn * slip
        for gi, q in enumerate(left):
            if q:
                banked += q * dirn * (fill - entry); left[gi] = 0
        reasons.append("FEED_END"); exit_i = n - 1

    return dict(usd=round(banked * POINT_USD - COMM_RT * total, 2),
                pts=round(banked / total, 4), exit_i=exit_i, mfe=round(mfe, 2),
                reason="+".join(dict.fromkeys(reasons)) or "-", contracts=total,
                n_tighten=n_tighten)


# ─────────────────────────────────────────────────────────── trade universe
def load_universe(cur, days, size=0):
    cur.execute("""
        select id, (entry_ts at time zone 'America/New_York'),
               (exit_ts at time zone 'America/New_York'),
               direction, entry_price, stop, t1, t2, t3, t4, pnl_usd, exit_reason,
               quality, pattern_id_at_entry, firing_system
        from v9_trades
        where mode='live' and state='CLOSED' and entry_ts is not null
          and (entry_ts at time zone 'America/New_York')::date between %s and %s
        order by entry_ts
    """, (D0, D1))
    out, skips = [], collections.Counter()
    for (tid, ein, eout, d, ep, st, t1, t2, t3, t4, pnl, xr, q, pat, sysn) in cur.fetchall():
        q = q or {}
        meta = q.get("metadata") or {}
        day = ein.date()
        bars = days.get(day)
        if not bars or ep is None:
            skips["no_bars_or_entry"] += 1; continue
        try:
            contracts = int(size or q.get("contracts") or 0)
        except (TypeError, ValueError):
            contracts = 0
        if contracts <= 0:
            skips["no_size"] += 1; continue
        # initial stop: quality.initial_stop -> metadata.stop_initial -> stop column
        s0 = q.get("initial_stop")
        if s0 is None:
            s0 = meta.get("stop_initial")
        if s0 is None:
            s0 = st
        if s0 is None:
            skips["no_stop"] += 1; continue
        entry, stop0 = float(ep), float(s0)
        dirn = 1 if str(d).upper() == "LONG" else -1
        if (dirn > 0 and stop0 >= entry) or (dirn < 0 and stop0 <= entry):
            skips["stop_wrong_side"] += 1; continue
        i0 = next((i for i, b in enumerate(bars) if b["t"] > ein), None)
        if i0 is None:
            skips["entry_after_last_bar"] += 1; continue
        prev = max([k for k in days if k < day], default=None)
        rev = swing_rev_threshold(days.get(prev))
        if rev is None:
            skips["no_prev_atr"] += 1; continue
        qtys = F5.ladder(contracts)
        tr = dict(t0=q.get("t0"), t1=t1, t2=t2, t3=t3, t4=t4)
        if len(qtys) >= 4 and tr["t0"] is None:
            tr["t0"] = round(round((entry + dirn * 3.0) / TICK) * TICK, 2)
        tgts = F5.tranche_targets(tr, len(qtys))
        tgts = [None if t is None else float(t) for t in tgts]
        if tgts[0] is None:
            skips["no_first_target"] += 1; continue
        if size and any(t is None for t in tgts):
            skips["incomplete_ladder_at_forced_size"] += 1; continue
        out.append(dict(id=tid, day=day, t_in=ein, t_out=eout, dirn=dirn, entry=entry,
                        stop0=stop0, tgts=tgts, qtys=qtys, contracts=contracts,
                        rev=rev, i0=i0, bars=bars, atrs=atr14(bars),
                        pat=(pat or q.get("classification") or ""),
                        sys=sysn, books=float(pnl or 0), book_reason=xr or "-",
                        scaled=bool(q.get("scaled_in")),
                        is_child=(str(q.get("classification") or "").upper() == "SCALE_IN"),
                        parent=(meta.get("scale_in_parent"))))
    return out, skips


# ─────────────────────────────────────────────────────────── arm runner
def run_arm(univ, slip, **policy):
    rows = []
    for t in univ:
        r = simulate(t["bars"], t["i0"], t["dirn"], t["entry"], t["stop0"],
                     t["tgts"], t["qtys"], rev=t["rev"], slip_ticks=slip,
                     pattern=t["pat"], atrs=t["atrs"], **policy)
        r["id"] = t["id"]; r["day"] = str(t["day"]); r["books"] = t["books"]
        r["pat"] = t["pat"]; r["c"] = t["contracts"]
        rows.append(r)
    return rows


def agg(rows):
    per_day = collections.Counter()
    for r in rows:
        per_day[r["day"]] += r["usd"]
    return dict(total=round(sum(r["usd"] for r in rows), 2), n=len(rows),
                per_day=dict(per_day),
                win=sum(1 for r in rows if r["usd"] > 0))


def compare(base_rows, arm_rows):
    """Δ total, MEDIAN-day Δ, days improved/hurt, worst single day,
    MFE-capture, n held longer, n gave back more."""
    b = {r["id"]: r for r in base_rows}
    a = {r["id"]: r for r in arm_rows}
    ids = sorted(set(b) & set(a))
    dd = collections.Counter()
    held = giveback = 0
    cap_num = cap_den = 0.0
    for i in ids:
        dd[b[i]["day"]] += a[i]["usd"] - b[i]["usd"]
        if a[i]["exit_i"] > b[i]["exit_i"]:
            held += 1
        gb_b = b[i]["mfe"] - b[i]["pts"]
        gb_a = a[i]["mfe"] - a[i]["pts"]
        if gb_a > gb_b + 1e-9:
            giveback += 1
        if a[i]["mfe"] > 0:
            cap_num += a[i]["pts"]; cap_den += a[i]["mfe"]
    dv = [round(v, 2) for v in dd.values()]
    worst_day = min(dd.items(), key=lambda kv: kv[1]) if dd else ("-", 0.0)
    best_day = max(dd.items(), key=lambda kv: kv[1]) if dd else ("-", 0.0)
    return dict(
        total=round(sum(dv), 2),
        # MFE-capture = SUM(realised pts) / SUM(MFE pts) over the arm. Aggregate,
        # not a mean of per-trade ratios: a stopped trade's ratio is unbounded
        # below and would swamp the average.
        capture_avg=round(100.0 * cap_num / cap_den, 1) if cap_den else 0.0,
        tightened=sum(r.get("n_tighten", 0) for r in arm_rows),
        median_day=round(statistics.median(dv), 2) if dv else 0.0,
        median_changed=round(statistics.median([x for x in dv if abs(x) >= 0.01]), 2)
        if any(abs(x) >= 0.01 for x in dv) else 0.0,
        improved=sum(1 for x in dv if x > 0.01), hurt=sum(1 for x in dv if x < -0.01),
        flat=sum(1 for x in dv if abs(x) <= 0.01), n_days=len(dv),
        worst_day="%s %+.2f" % (worst_day[0], worst_day[1]),
        best_day="%s %+.2f" % (best_day[0], best_day[1]),
        capture=round(100.0 * cap_num / cap_den, 1) if cap_den else 0.0,
        held_longer=held, gave_back_more=giveback,
        changed=sum(1 for i in ids if abs(a[i]["usd"] - b[i]["usd"]) > 0.01))


# ─────────────────────────────────────────────────────────── X3 · scale-in
def scale_moments(t, cfg, *, atr_k=None, min_rr=None, extreme_k=None):
    """Every bar at which a scale-in would fire for parent trade `t`.

    Reuses the LIVE rule (backend...scale_in.should_scale_in) and only layers the
    proposed extra gates on top, so the baseline arm is production behaviour.
    Causal: bar k is judged with bars[:k+1] only.
    """
    bars, dirn, rev = t["bars"], t["dirn"], t["rev"]
    entry = t["entry"]
    # T1 = the first bar at which the T1-leg target traded (same map as the sim)
    be_idx = F5.be_trigger_index(len(t["qtys"]))
    t1p = t["tgts"][be_idx] if be_idx < len(t["tgts"]) else None
    if t1p is None:
        return []
    t1_bar = None
    out = []
    for k in range(t["i0"], len(bars)):
        b = bars[k]
        if t1_bar is None:
            if (dirn > 0 and b["h"] >= t1p) or (dirn < 0 and b["l"] <= t1p):
                t1_bar = k
            continue
        if b["t"].time() >= EOD_BAR:
            break
        a = t["atrs"][k] if k < len(t["atrs"]) else 0.0
        c = ScaleInCfg(min_profit_pts=(round(atr_k * a, 2) if (atr_k and a > 0)
                                       else cfg.min_profit_pts),
                       add_contracts=cfg.add_contracts,
                       max_total_contracts=cfg.max_total_contracts,
                       require_with_trend=cfg.require_with_trend,
                       add_stop_at_entry=cfg.add_stop_at_entry)
        dec = should_scale_in(direction="LONG" if dirn > 0 else "SHORT",
                              entry_price=entry, t1_hit=True, already_scaled=False,
                              n_contracts_open=max(1, t["contracts"] - 1),
                              bar_high=b["h"], bar_low=b["l"],
                              dir_bias=struct_dir_bias(bars, k, rev), cfg=c)
        if dec is None:
            continue
        add_entry = dec.entry
        risk = abs(add_entry - dec.stop) or 1.0
        blocked = None
        if min_rr is not None:
            lvl = next_struct_level(bars, k, dirn, rev)
            if lvl is not None:                       # None = open air = infinite room
                room = dirn * (lvl - add_entry)
                if room < min_rr * risk:
                    blocked = "room<%.1fR (%.2fpt vs %.2f)" % (min_rr, room,
                                                               min_rr * risk)
        if blocked is None and extreme_k is not None and a > 0:
            dist = dist_from_session_extreme(bars, k, dirn)
            if dist < extreme_k * a:
                blocked = "%.2fpt from session extreme (<%.2f=%.1fxATR)" % (
                    dist, extreme_k * a, extreme_k)
        out.append(dict(k=k, entry=add_entry, stop=dec.stop, blocked=blocked,
                        atr=round(a, 2), t1_bar=t1_bar,
                        dist_extreme=dist_from_session_extreme(bars, k, dirn)))
        if blocked is None:
            break                       # once per parent (live: already_scaled)
    return out


def sim_child(t, mom, slip, *, combined_stop=False, exit_regime="struct"):
    """The +2c add-on.

    exit_regime="live"   reproduce the child as it is actually placed today:
                         stop at the parent entry, ONE fixed target at
                         +1.5 x (add_entry - stop), no structural exit.
    exit_regime="struct" the X1 regime: stop / structural break on a closed bar /
                         EOD. This is the regime every C-arm is measured in, so
                         the C-to-C delta is the ENTRY GATE and the STOP only.

    combined_stop=True   Michael's item: ONE structural stop for the whole
                         AVERAGED position instead of the child's own stop at
                         the parent's entry (which is wrong after averaging).
    """
    bars, dirn = t["bars"], t["dirn"]
    k = mom["k"]
    qtys = [1, 1]
    stop = mom["stop"]
    avg_entry = None
    if combined_stop:
        anchor = swing_trail_stop(bars[:k + 1], "LONG" if dirn > 0 else "SHORT",
                                  rev=t["rev"], offset_ticks=1)
        # the stop protects the AVERAGE of parent-remaining + child, so it is the
        # averaged position that must survive the structural level
        avg_entry = round((t["entry"] + mom["entry"]) / 2.0, 2)
        if anchor is not None:
            stop = anchor
    if (dirn > 0 and stop >= mom["entry"]) or (dirn < 0 and stop <= mom["entry"]):
        stop = mom["entry"] - dirn * max(1.5, 0.5 * (mom["atr"] or 3.0))
    tg = [None, None]
    kw = dict(mae_mode="off", trail="struct", trail_legs=2)
    if exit_regime == "live":
        risk = abs(mom["entry"] - stop) or 2.0
        tgt = round(round((mom["entry"] + dirn * 1.5 * risk) / TICK) * TICK, 2)
        tg = [tgt, tgt]
        kw = dict(mae_mode="off", trail=None)
    r = simulate(bars, k + 1, dirn, mom["entry"], stop, tg, qtys,
                 rev=t["rev"], slip_ticks=slip, pattern="SCALE_IN",
                 atrs=t["atrs"], **kw)
    r["parent"] = t["id"]; r["day"] = str(t["day"]); r["k"] = k
    r["entry"] = mom["entry"]; r["stop"] = round(stop, 2)
    r["avg_entry"] = avg_entry
    r["dist_extreme"] = mom["dist_extreme"]
    return r


# ─────────────────────────────────────────────────────────── X4 · confluence
# gateway_decisions.jsonl is polluted with pytest fixtures — 791 of 9,880 lines
# (8.0%), root-caused in docs/reports/DEAD_SYSTEMS_AUDIT_2026-08-22.md finding-1
# (tests/v9/conftest.py does not redirect GATEWAY_DECISIONS_PATH). These pattern
# names are emitted by no detector; HFE rows additionally all carry entry
# 7595/7600. Dropped before anything reads the feed.
SYNTHETIC_PATTERNS = {"HFE", "STRATEGIC", "NO_SUCH_PATTERN", "TLB_LONG"}


def load_decisions():
    files = sorted(glob.glob(DEC_DIR + "/decisions_archive/*.jsonl")) + \
            sorted(glob.glob(DEC_DIR + "/gateway_decisions*"))
    seen, out = set(), []
    dropped = 0
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
                key = (o.get("ts"), o.get("system"), o.get("pattern"),
                       o.get("direction"), o.get("entry"), o.get("blocked_by"))
                if key in seen:
                    continue
                seen.add(key)
                if str(o.get("pattern") or "").upper() in SYNTHETIC_PATTERNS:
                    dropped += 1
                    continue
                try:
                    ts = dt.datetime.fromisoformat(o["ts"])
                except Exception:
                    continue
                et = ts.astimezone(dt.timezone(dt.timedelta(hours=-4))).replace(tzinfo=None)
                out.append(dict(t=et, day=et.date(), sys=o.get("system"),
                                pat=o.get("pattern") or "-",
                                dirn=(1 if (o.get("direction") or "") == "LONG" else -1),
                                entry=o.get("entry"), blocked=o.get("blocked_by"),
                                outcome=o.get("outcome"),
                                tag=o.get("confluence_tag")))
    print("  decision feed: %d rows kept, %d pytest-fixture rows dropped "
          "(%s)" % (len(out), dropped, ",".join(sorted(SYNTHETIC_PATTERNS))))
    return out


def confluence_moments(t, decs, base_exit_i, *, min_rr=1.5, extreme_k=0.5,
                       max_per_parent=1):
    """Gate-passing candidates from the OTHER system, same direction, while open."""
    bars, dirn = t["bars"], t["dirn"]
    lo_t = bars[t["i0"]]["t"]
    hi_t = bars[min(base_exit_i, len(bars) - 1)]["t"]
    out = []
    for d in decs:
        if d["day"] != t["day"] or d["dirn"] != dirn:
            continue
        if str(d["sys"]) == str(t["sys"]):
            continue
        if d["blocked"]:
            continue
        if not (lo_t <= d["t"] <= hi_t):
            continue
        k = next((i for i, b in enumerate(bars) if b["t"] > d["t"]), None)
        if k is None or k <= t["i0"]:
            continue
        k -= 1                                    # the bar the decision landed in
        b = bars[k]
        px = d["entry"]
        if px is None or not (b["l"] - 1.0 <= float(px) <= b["h"] + 1.0):
            px = b["c"]
        px = float(px)
        a = t["atrs"][k] if k < len(t["atrs"]) else 0.0
        anchor = swing_trail_stop(bars[:k + 1], "LONG" if dirn > 0 else "SHORT",
                                  rev=t["rev"], offset_ticks=1)
        stop = anchor if anchor is not None else px - dirn * max(1.5, 0.5 * (a or 3.0))
        if (dirn > 0 and stop >= px) or (dirn < 0 and stop <= px):
            stop = px - dirn * max(1.5, 0.5 * (a or 3.0))
        risk = abs(px - stop) or 1.0
        blocked = None
        lvl = next_struct_level(bars, k, dirn, t["rev"])
        room = None if lvl is None else round(dirn * (lvl - px), 2)
        if min_rr is not None and room is not None and room < min_rr * risk:
            blocked = "room<%.1fR" % min_rr
        if blocked is None and extreme_k is not None and a > 0 \
                and dist_from_session_extreme(bars, k, dirn) < extreme_k * a:
            blocked = "at session extreme"
        out.append(dict(k=k, entry=px, stop=round(stop, 2), blocked=blocked,
                        pat=d["pat"], sys=d["sys"], t=str(d["t"])[11:16],
                        tag=bool(d["tag"]), room=room, risk=round(risk, 2),
                        atr=a, dist_extreme=dist_from_session_extreme(bars, k, dirn)))
    # one add per parent — the first that passes
    ok = [m for m in out if m["blocked"] is None]
    return out, (ok[0] if ok else None)


# ─────────────────────────────────────────────────────────────────── main
# Sessions whose 5-min feed died before 15:55 (bars < 78). Any "held to the end"
# number on these days is a FEED artefact, not a trading result — every headline
# below is therefore also reported ex-truncated.
def truncated_days(days):
    return {d for d, b in days.items() if len(b) < 78}


def fmt_arm_table(title, arms, res, base_name, slip, trunc):
    base = res[base_name]
    print("\n slip=%d tick | %s" % (slip, title))
    print("   %-32s %10s %10s %10s %9s %9s %-18s %7s %6s %6s"
          % ("arm", "total$", "d vs BASE", "ex-trunc", "medDay", "medChg",
             "worst day", "capt%", "held+", "gave+"))
    for name in arms:
        rows = res[name]
        c = compare(base, rows)
        ex = sum(r["usd"] - {x["id"]: x for x in base}[r["id"]]["usd"]
                 for r in rows if r["day"] not in trunc)
        print("   %-32s %+10.2f %+10.2f %+10.2f %+9.2f %+9.2f %-18s %7.1f %6d %6d"
              % (name, sum(r["usd"] for r in rows), c["total"], ex,
                 c["median_day"], c["median_changed"], c["worst_day"],
                 c["capture_avg"], c["held_longer"], c["gave_back_more"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/replay_exit_size.json")
    ap.add_argument("--size", type=int, default=0,
                    help="force every trade to N contracts (0 = as traded)")
    a = ap.parse_args()

    OR.D1 = D1                      # extend the oracle bar window to yesterday
    cn = psycopg2.connect(os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26"))
    cn.set_session(readonly=True, autocommit=True)
    cur = cn.cursor()
    days = OR.load_bars(cur)
    univ, skips = load_universe(cur, days, size=a.size)
    cn.close()
    decs = load_decisions()
    trunc = {str(d) for d in truncated_days(days)}

    parents = [t for t in univ if not t["is_child"]]
    sess = sorted({str(t["day"]) for t in univ})
    print("UNIVERSE  live-era %s..%s  sessions=%d  trades replayed=%d "
          "(parents=%d, scale-in children=%d)  size=%s  skipped=%s"
          % (D0, D1, len(sess), len(univ), len(parents), len(univ) - len(parents),
             a.size or "as-traded", dict(skips)))
    print("  books on the replayed subset: %+.2f   |   truncated-feed sessions in "
          "the set: %s" % (sum(t["books"] for t in univ),
                           ", ".join(sorted(set(sess) & trunc)) or "none"))

    # ---------------------------------------------------------------- X1
    ARMS = [
        ("A-1 LADDER-ONLY (pre-F5)",      dict(mae_mode="atr", trail=None)),
        ("A0  BASE = live today",         dict(mae_mode="atr", trail="f5")),
        ("A1  BASE - MAE-scratch",        dict(mae_mode="off", trail="f5")),
        ("A2  BASE + TARGET_APPROACH",    dict(mae_mode="atr", trail="f5", tar=True)),
        ("A3  struct-break runner",       dict(mae_mode="atr", trail="struct")),
        ("A4  X1 = struct + no-scratch",  dict(mae_mode="off", trail="struct")),
        ("A5  X1, 2 legs structural",     dict(mae_mode="off", trail="struct",
                                               trail_legs=2)),
        ("A6  X1, all legs structural",   dict(mae_mode="off", trail="struct",
                                               trail_legs=3)),
        ("A7  no-scratch + f5 x2 legs",   dict(mae_mode="off", trail="f5",
                                               trail_legs=2)),
    ]
    names = [n for n, _ in ARMS]
    res = {}
    print("\n=== X1 · EXIT RULES " + "=" * 78)
    for slip in (0, 1, 2):
        res[slip] = {n: run_arm(univ, slip, **kw) for n, kw in ARMS}
        fmt_arm_table("exit rule -> $", names, res[slip], "A0  BASE = live today",
                      slip, trunc)
    print("\n  per-day delta of A4 (X1 as specced) vs A0, slip=1:")
    b1 = {r["id"]: r for r in res[1]["A0  BASE = live today"]}
    pd = collections.Counter()
    for r in res[1]["A4  X1 = struct + no-scratch"]:
        pd[r["day"]] += r["usd"] - b1[r["id"]]["usd"]
    for d in sorted(pd):
        if abs(pd[d]) >= 0.01:
            print("     %s %+9.2f%s" % (d, pd[d], "  (truncated feed)" if d in trunc else ""))

    # ---------------------------------------------------------------- X2
    print("\n=== X2 · LAST-10-MINUTES " + "=" * 73)
    X2 = [("V0 do nothing (EOD flatten)", dict(mae_mode="atr", trail="f5")),
          ("V1 close all at T-10",        dict(mae_mode="atr", trail="f5",
                                               t10="flatten")),
          ("V2 tighten BE+swing at T-10", dict(mae_mode="atr", trail="f5",
                                               t10="tighten")),
          ("V2b tighten BE+3-bar at T-10", dict(mae_mode="atr", trail="f5",
                                                t10="tighten3"))]
    x2 = {}
    for slip in (0, 1, 2):
        x2[slip] = {n: run_arm(univ, slip, **kw) for n, kw in X2}
        base = x2[slip]["V0 do nothing (EOD flatten)"]
        print("\n slip=%d   %-30s %10s %9s %8s %8s %9s %-18s"
              % (slip, "variant", "total$", "delta", "n affect", "medDay",
                 "n tighten", "worst day"))
        for n, _ in X2:
            rows = x2[slip][n]
            c = compare(base, rows)
            print("         %-30s %+10.2f %+9.2f %8d %+8.2f %9d %-18s"
                  % (n, sum(r["usd"] for r in rows), c["total"], c["changed"],
                     c["median_day"], c["tightened"], c["worst_day"]))
    idx = {u["id"]: u for u in univ}
    late = [r for r in x2[0]["V0 do nothing (EOD flatten)"]
            if idx[r["id"]]["bars"][r["exit_i"]]["t"].time() >= T10_BAR]
    print("\n  population at risk — still open at T-10 in the baseline: %d of %d"
          % (len(late), len(univ)))
    v1 = {r["id"]: r for r in x2[1]["V1 close all at T-10"]}
    v0 = {r["id"]: r for r in x2[1]["V0 do nothing (EOD flatten)"]}
    for r in sorted(late, key=lambda x: x["day"]):
        i = r["id"]
        print("     #%-4s %s  base %-16s %+8.2f -> T10-flat %+8.2f  (delta %+7.2f)"
              % (i, r["day"], v0[i]["reason"], v0[i]["usd"], v1[i]["usd"],
                 v1[i]["usd"] - v0[i]["usd"]))

    # ---------------------------------------------------------------- X3
    print("\n=== X3 · SCALE-IN " + "=" * 80)
    live_cfg = ScaleInCfg(min_profit_pts=6.0, add_contracts=2, max_total_contracts=8)
    X3 = [
        ("C0-live  live rule, live child exit", dict(), False, "live"),
        ("C0  live rule (6pt, stop@parent)",    dict(), False, "struct"),
        ("C1  trigger 0.5xATR",                 dict(atr_k=0.5), False, "struct"),
        ("C1b trigger 1.0xATR",                 dict(atr_k=1.0), False, "struct"),
        ("C1c trigger 1.5xATR",                 dict(atr_k=1.5), False, "struct"),
        ("C2  require >=1.5R room",             dict(min_rr=1.5), False, "struct"),
        ("C3  extreme-guard 0.5xATR",           dict(extreme_k=0.5), False, "struct"),
        ("C3b extreme-guard 1.0xATR",           dict(extreme_k=1.0), False, "struct"),
        ("C4  ONE struct stop (averaged)",      dict(), True, "struct"),
        ("P1  C1c+C4 (1.5xATR + one stop)",     dict(atr_k=1.5), True, "struct"),
        ("P2  C1c+C3b+C4",                      dict(atr_k=1.5, extreme_k=1.0),
                                                True, "struct"),
        ("P3  C1c+C2+C4",                       dict(atr_k=1.5, min_rr=1.5),
                                                True, "struct"),
        ("ALL C1+C2+C3+C4",                     dict(atr_k=0.5, min_rr=1.5,
                                                     extreme_k=0.5), True, "struct"),
        ("ALL-noC1  C2+C3+C4 (keep 6pt)",       dict(min_rr=1.5, extreme_k=0.5),
                                                True, "struct"),
        ("ALL-b  C1b+C2+C3b+C4",                dict(atr_k=1.0, min_rr=1.5,
                                                     extreme_k=1.0), True, "struct"),
    ]
    x3 = {}
    for slip in (0, 1, 2):
        x3[slip] = {}
        for name, kw, comb, regime in X3:
            childs = []
            for t in parents:
                for m in scale_moments(t, live_cfg, **kw):
                    if m["blocked"] is None:
                        childs.append(sim_child(t, m, slip, combined_stop=comb,
                                                exit_regime=regime))
                        break
            x3[slip][name] = childs
    for slip in (0, 1, 2):
        b = sum(r["usd"] for r in x3[slip]["C0  live rule (6pt, stop@parent)"])
        print("\n slip=%d   %-38s %6s %6s %10s %10s %10s %9s"
              % (slip, "condition", "n adds", "win%", "total$", "d vs C0",
                 "ex-trunc$", "medDay$"))
        for name, _, _, _ in X3:
            rows = x3[slip][name]
            tot = sum(r["usd"] for r in rows)
            ex = sum(r["usd"] for r in rows if r["day"] not in trunc)
            wr = 100.0 * sum(1 for r in rows if r["usd"] > 0) / len(rows) if rows else 0.0
            pd = collections.Counter()
            for r in rows:
                pd[r["day"]] += r["usd"]
            med = statistics.median(pd.values()) if pd else 0.0
            print("         %-38s %6d %6.1f %+10.2f %+10.2f %+10.2f %+9.2f"
                  % (name, len(rows), wr, tot, tot - b, ex, med))
    for tag in ("C0  live rule (6pt, stop@parent)", "ALL-noC1  C2+C3+C4 (keep 6pt)"):
        print("\n  %s — every add (slip=1):" % tag)
        for r in x3[1][tag]:
            print("     parent #%-4s %s  add@%8.2f stop %8.2f  %-12s %+9.2f  "
                  "(%5.2fpt from session extreme)%s"
                  % (r["parent"], r["day"], r["entry"], r["stop"], r["reason"],
                     r["usd"], r["dist_extreme"],
                     "  [truncated feed]" if r["day"] in trunc else ""))

    # ---------------------------------------------------------------- X4
    print("\n=== X4 · S2xS4 CONFLUENCE ADD " + "=" * 68)
    print("  decision-feed coverage: %s .. %s (%d sessions) — before that there is "
          "no feed, so X4 is measured only inside it."
          % (min(d["day"] for d in decs), max(d["day"] for d in decs),
             len({d["day"] for d in decs})))
    X4GATES = [("K0 raw (no safety gate)",        dict(min_rr=None, extreme_k=None)),
               ("K1 + extreme-guard 0.5xATR",     dict(min_rr=None, extreme_k=0.5)),
               ("K2 + >=1.5R room",               dict(min_rr=1.5, extreme_k=None)),
               ("K2b + >=1.0R room",              dict(min_rr=1.0, extreme_k=None)),
               ("K3 X3 safety rules (both)",      dict(min_rr=1.5, extreme_k=0.5))]
    x4 = {}
    for slip in (0, 1, 2):
        base = {r["id"]: r for r in res[slip]["A0  BASE = live today"]}
        x4[slip] = {}
        for gname, gkw in X4GATES:
            adds, allm, blocked, tagged, rooms = [], 0, collections.Counter(), 0, []
            for t in parents:
                br = base.get(t["id"])
                if not br:
                    continue
                moments, first = confluence_moments(t, decs, br["exit_i"], **gkw)
                allm += len(moments)
                for m in moments:
                    if m["blocked"]:
                        blocked[m["blocked"]] += 1
                    if m["tag"]:
                        tagged += 1
                if first:
                    r = sim_child(t, first, slip, combined_stop=True)
                    r["pat"] = first["pat"]; r["osys"] = first["sys"]
                    r["tag"] = first["tag"]; r["time"] = first["t"]
                    adds.append(r)
            x4[slip][gname] = dict(adds=adds, moments=allm,
                                   blocked=dict(blocked), tagged=tagged)
        print("\n slip=%d   %-30s %8s %7s %6s %10s %10s %10s %10s"
              % (slip, "gate", "moments", "n adds", "win%", "total$", "ex-trunc$",
                 "median-add", "median-day"))
        for gname, _ in X4GATES:
            v = x4[slip][gname]
            adds = v["adds"]
            pd = collections.Counter()
            for r in adds:
                pd[r["day"]] += r["usd"]
            print("         %-30s %8d %7d %6.1f %+10.2f %+10.2f %+10.2f %+10.2f"
                  % (gname, v["moments"], len(adds),
                     100.0 * sum(1 for r in adds if r["usd"] > 0) / len(adds)
                     if adds else 0.0,
                     sum(r["usd"] for r in adds),
                     sum(r["usd"] for r in adds if r["day"] not in trunc),
                     statistics.median([r["usd"] for r in adds]) if adds else 0.0,
                     statistics.median(pd.values()) if pd else 0.0))
    print("\n  why the gated arms are empty — blocks on the %d moments: %s"
          % (x4[1]["K3 X3 safety rules (both)"]["moments"],
             x4[1]["K3 X3 safety rules (both)"]["blocked"]))
    print("  K4 confluence_tag present on %d of the moments"
          % x4[1]["K0 raw (no safety gate)"]["tagged"])
    print("\n  K0 raw adds (slip=1):")
    for r in x4[1]["K0 raw (no safety gate)"]["adds"]:
        print("     parent #%-4s %s %s  other=S%-2s %-18s add@%8.2f stop %8.2f  "
              "%-12s %+9.2f  K4tag=%s%s"
              % (r["parent"], r["day"], r["time"], r["osys"], r["pat"], r["entry"],
                 r["stop"], r["reason"], r["usd"], r["tag"],
                 "  [truncated feed]" if r["day"] in trunc else ""))

    # ---------------------------------------------------------------- COMBINED
    print("\n=== COMBINED " + "=" * 85)
    COMBOS = [
        ("CO-1  X1(A4) only",
         dict(exit=dict(mae_mode="off", trail="struct"), x3=None, x4=None)),
        ("CO-2  X1(A5, 2 legs) only",
         dict(exit=dict(mae_mode="off", trail="struct", trail_legs=2),
              x3=None, x4=None)),
        ("CO-3  X1(A5) + X2-V1",
         dict(exit=dict(mae_mode="off", trail="struct", trail_legs=2, t10="flatten"),
              x3=None, x4=None)),
        ("CO-4  X1(A5) + X2-V1 + X3-P1",
         dict(exit=dict(mae_mode="off", trail="struct", trail_legs=2, t10="flatten"),
              x3="P1  C1c+C4 (1.5xATR + one stop)", x4=None)),
        ("CO-5  everything (+X4 K0)",
         dict(exit=dict(mae_mode="off", trail="struct", trail_legs=2, t10="flatten"),
              x3="P1  C1c+C4 (1.5xATR + one stop)", x4="K0 raw (no safety gate)")),
        ("CO-6  A6 all-struct + V1 + P1 + K0",
         dict(exit=dict(mae_mode="off", trail="struct", trail_legs=3, t10="flatten"),
              x3="P1  C1c+C4 (1.5xATR + one stop)", x4="K0 raw (no safety gate)")),
        ("CO-7  BASE + V1 + P1 + K0 (exits unchanged)",
         dict(exit=dict(mae_mode="atr", trail="f5", t10="flatten"),
              x3="P1  C1c+C4 (1.5xATR + one stop)", x4="K0 raw (no safety gate)")),
        ("CO-8  BASE + A3 + V1 + P3 + K0  <-- SHIP",
         dict(exit=dict(mae_mode="atr", trail="struct", t10="flatten"),
              x3="P3  C1c+C2+C4", x4="K0 raw (no safety gate)")),
        ("CO-9  = CO-8 without X4",
         dict(exit=dict(mae_mode="atr", trail="struct", t10="flatten"),
              x3="P3  C1c+C2+C4", x4=None)),
    ]
    combined = {}
    for slip in (0, 1, 2):
        base = res[slip]["A0  BASE = live today"]
        bmap = {r["id"]: r for r in base}
        combined[slip] = {}
        print("\n slip=%d   %-32s %10s %10s %9s %9s %10s %10s %9s"
              % (slip, "combination", "d total$", "ex-trunc$", "medDay", "medChg",
                 "worst day", "best day", "$/session"))
        for cname, spec in COMBOS:
            combo = run_arm(univ, slip, **spec["exit"])
            extra = []
            if spec["x3"]:
                extra += x3[slip][spec["x3"]]
            if spec["x4"]:
                extra += x4[slip][spec["x4"]]["adds"]
            pd = collections.Counter()
            for r in combo:
                pd[r["day"]] += r["usd"] - bmap[r["id"]]["usd"]
            for r in extra:
                pd[r["day"]] += r["usd"]
            dv = sorted(round(v, 2) for v in pd.values())
            nz = [x for x in dv if abs(x) >= 0.01]
            tot = round(sum(dv), 2)
            ex = round(sum(v for d, v in pd.items() if d not in trunc), 2)
            combined[slip][cname] = dict(
                total=tot, ex_trunc=ex,
                per_day={k: round(v, 2) for k, v in pd.items()})
            print("         %-32s %+10.2f %+10.2f %+9.2f %+9.2f %+10.2f %+10.2f %+9.2f"
                  % (cname, tot, ex, statistics.median(dv) if dv else 0.0,
                     statistics.median(nz) if nz else 0.0,
                     min(dv) if dv else 0.0, max(dv) if dv else 0.0,
                     tot / max(1, len(sess))))

    if a.json:
        def slim(rows):
            return [{k: v for k, v in r.items() if k != "bars"} for r in rows]
        with open(a.json, "w") as fh:
            json.dump(dict(
                universe=dict(n=len(univ), parents=len(parents), skips=dict(skips),
                              books=round(sum(t["books"] for t in univ), 2),
                              sessions=sess, truncated=sorted(set(sess) & trunc)),
                x1={str(s): {n: slim(r) for n, r in res[s].items()} for s in res},
                x2={str(s): {n: slim(r) for n, r in x2[s].items()} for s in x2},
                x3={str(s): {n: slim(r) for n, r in x3[s].items()} for s in x3},
                x4={str(s): {g: dict(moments=v["moments"], tagged=v["tagged"],
                                     blocked=v["blocked"], adds=slim(v["adds"]))
                             for g, v in x4[s].items()} for s in x4},
                combined={str(s): combined[s] for s in combined},
            ), fh, indent=1, default=str)
        print("\njson ->", a.json)


if __name__ == "__main__":
    main()
