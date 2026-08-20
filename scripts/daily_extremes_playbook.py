#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_extremes_playbook.py — per-session "extremes & day-type playbook" study.

Michael (2026-08-20):
    "For EVERY past session: the day's extremes (when/where they formed), the day
     type, which trades the system COULD have identified that day, and concretely
     how to reach maximum profit on a day of that shape."

What this produces per session
------------------------------
  EXTREMES   session high/low + the exact 5-min bar each printed on, the phase it
             formed in (first hour / after IB lock / late), the IB range (computed
             from the bars, 09:30-10:30 ET = the definitional IB) vs the IB the
             live engine exported, and where the close sat relative to both
             extremes (did the extreme HOLD or did the day EXTEND through it).
  DAY TYPE   (a) the label the system had LIVE  -> v9_day_type_history.day_type
                 + the modal `day_type_at_entry` actually stamped on that day's
                 trades (what the gates really consumed).
             (b) the honest POST-HOC label -> the repo's own 7-type classifier
                 (backend.v9.systems.day_type.classifier_core.classify_session)
                 fed the WHOLE session with is_eod=True.
             Disagreements are flagged (defect class T-47).
  TRADES     the swing segmentation (ZigZag on 5-min closes, threshold =
             1.0 x prev-session ATR, clamped 4..12pt) -> for each major leg the
             earliest CAUSAL trigger (no lookahead), its entry/stop/realistic
             target, and the cross-check against what the system did:
             detected+taken / detected+blocked(gate) / shadow-only / never-detected.
  LAYERS     per-day $: books (v9_trades live) · same-entries-held (structural
             trail instead of the ladder) · CAUSAL-2 (blind, 2 triggers) ·
             FEASIBLE-2 (best 2 legs, realistic mechanics).

The swing/trigger/mechanics engine is IMPORTED from scripts/oracle_study.py —
it is not re-implemented (same thresholds, same $/pt, same costs, same slippage).

READ-ONLY.  Direct psycopg2 (never backend.v9.db.read - stale-SQLite fallback).
Writes nothing but stdout + the JSON dump given by --json.

Usage:  python3 scripts/daily_extremes_playbook.py [--json /tmp/dep.json]
"""

import argparse
import collections
import datetime as dt
import json
import os
import statistics
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- reuse the ORACLE_STUDY engine verbatim (no re-implementation) ----------
import importlib.util as _ilu

_OS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oracle_study.py")
_spec = _ilu.spec_from_file_location("oracle_study", _OS_PATH)
ORA = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(ORA)

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
D_FIRST = "2026-06-05"          # first session with enough bars (shadow era)
D_LIVE0 = "2026-07-07"          # first live-trading session
D_LAST = "2026-08-19"
WARM = "2026-06-01"

RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12                    # 09:30 -> 10:30 ET = the Initial Balance
CONTRACTS = ORA.CONTRACTS       # 4
POINT_USD = ORA.POINT_USD       # 5.0

# The S1_* flag set that was LIVE on 2026-08-20 (read from .env, documented in
# the report).  DELTA_FEATURES_V1 is deliberately left OFF: it reads TODAY's
# cumulative_delta.json snapshot, which would contaminate a historical replay
# (Rule 1 - better a missing feature than a wrong one).
LIVE_S1_FLAGS = {
    "S1_NEW_CLASSIFIER": "1", "S1_ENGINE_NEW_CLASSIFIER": "1",
    "S1_OPEN_DRIVE_TREND": "1", "S1_COMMITTED_PROVISIONAL_V1": "1",
    "S1_CONFIDENCE_V2": "1", "S1_TREND_CONTROL_V1": "1",
    "S1_NONCONVICTION_V1": "1", "S1_DD_INVALIDATION_V1": "1",
    "S1_ACCEPTANCE_RECLASS_V1": "1", "S1_VALUE_MIGRATION_V1": "1",
    "S1_IB_SANITY_V1": "1", "S1_NEUTRAL_PRECEDENCE_V1": "1",
    "S1_CONF_SMOOTH_V1": "1", "S1_RECLASS_REQUIRES_IB_EXT_V1": "1",
    "S1_TREND_ELONGATION_V1": "1", "S1_CVD_OPENING": "true",
    "S1_IB_WIDTH_ATR": "true", "S1_DAYTYPE_STAGING": "true",
    "S1_DYNAMIC_RECLASS": "true", "S1_LIVE_RECLASS": "true",
    "S1_PROVISIONAL_DAYTYPE": "1",
    "DELTA_FEATURES_V1": "0", "MULTIDAY_CONTEXT_V1": "0",
}


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
        (WARM, D_LAST, RTH0, RTH1),
    )
    days = collections.OrderedDict()
    for et, o, h, l, c, v in cur.fetchall():
        days.setdefault(et.date(), []).append(
            dict(t=et, o=float(o), h=float(h), l=float(l), c=float(c), v=float(v or 0))
        )
    return days


def load_all_trades(cur):
    """live AND shadow closed trades (shadow gives the pre-07-07 era a signal stream)."""
    cur.execute(
        """
        select id, pattern_id_at_entry, firing_system, direction, mode,
               (entry_ts at time zone 'America/New_York'),
               (exit_ts   at time zone 'America/New_York'),
               entry_price, exit_price, stop, pnl_usd, pnl_r, exit_reason,
               day_type_at_entry
        from v9_trades
        where state='CLOSED' and entry_ts is not null
        order by entry_ts
        """
    )
    out = []
    for (tid, pat, sysn, d, mode, ein, eout, ep, xp, st, pnl, pr, xr, dtype) in cur.fetchall():
        c = None
        try:
            risk = abs(float(ep) - float(st))
            if pr and risk >= 1.0:
                raw = float(pnl) / (float(pr) * risk * POINT_USD)
                if 0.9 <= raw <= 6.3 and abs(raw - round(raw)) <= 0.08:
                    c = int(round(raw))
        except Exception:
            pass
        out.append(dict(id=tid, pat=pat or "-", sys=sysn, mode=mode,
                        dir=(1 if d == "LONG" else -1), t_in=ein, t_out=eout,
                        entry=float(ep) if ep is not None else None,
                        exit=float(xp) if xp is not None else None,
                        pnl=float(pnl or 0), reason=xr or "-", contracts=c,
                        day=ein.date(), day_type=dtype))
    return out


def load_live_labels(cur):
    """The day-type label the LIVE engine recorded for that date."""
    cur.execute(
        "select date, day_type, status, ib_high, ib_low, opening_type, confidence "
        "from v9_day_type_history where date >= %s order by date", (WARM,)
    )
    out = {}
    for d, dtp, st, ibh, ibl, op, conf in cur.fetchall():
        out[d] = dict(day_type=dtp, status=st,
                      ib_high=float(ibh) if ibh is not None else None,
                      ib_low=float(ibl) if ibl is not None else None,
                      opening_type=op, confidence=float(conf) if conf is not None else None)
    return out


# ---------------------------------------------------------------- profile helpers
def value_area(bars, pct=0.70):
    """70% value area + POC from 5-min bars (volume spread over the bar's range at
    0.25 granularity).  A documented APPROXIMATION of the TPO/volume profile - the
    Sierra tpo_sessions VA columns are demonstrably inconsistent with their own IB
    on several days, so they are NOT used (Rule 2: verify before you trust)."""
    hist = collections.Counter()
    for b in bars:
        lo, hi = b["l"], b["h"]
        n = max(1, int(round((hi - lo) / 0.25)) + 1)
        share = (b["v"] or 1.0) / n
        for k in range(n):
            hist[round(lo + k * 0.25, 2)] += share
    if not hist:
        return None, None, None
    tot = sum(hist.values())
    poc = max(hist.items(), key=lambda kv: kv[1])[0]
    prices = sorted(hist)
    i = prices.index(poc)
    lo_i = hi_i = i
    acc = hist[poc]
    while acc < pct * tot and (lo_i > 0 or hi_i < len(prices) - 1):
        up = hist[prices[hi_i + 1]] if hi_i < len(prices) - 1 else -1
        dn = hist[prices[lo_i - 1]] if lo_i > 0 else -1
        if up >= dn:
            hi_i += 1
            acc += hist[prices[hi_i]]
        else:
            lo_i -= 1
            acc += hist[prices[lo_i]]
    return prices[hi_i], prices[lo_i], poc


def posthoc_label(days, d, bars):
    """The repo's own 7-type classifier, fed the WHOLE session, is_eod=True."""
    for k, v in LIVE_S1_FLAGS.items():
        os.environ[k] = v
    try:
        from backend.v9.systems.day_type.classifier_core import classify_session
    except Exception as e:                                  # honest failure (Rule 1)
        return dict(day_type=None, err=str(e))

    keys = sorted([k for k in days if k < d])
    prev = days[keys[-1]] if keys else None
    pdh = max(b["h"] for b in prev) if prev else None
    pdl = min(b["l"] for b in prev) if prev else None
    pvah = pval = None
    if prev:
        pvah, pval, _ = value_area(prev)
    ib_hist = []
    for k in keys[-40:]:
        bb = days[k]
        if len(bb) >= IB_BARS:
            ib = bb[:IB_BARS]
            ib_hist.append(max(x["h"] for x in ib) - min(x["l"] for x in ib))
    vols = [sum(x["v"] for x in days[k]) for k in keys[-20:] if len(days[k]) >= 40]
    vr = None
    if vols:
        med = statistics.median(vols)
        if med > 0:
            vr = round(sum(b["v"] for b in bars) / med, 3)
    ib = bars[:IB_BARS]
    ibh, ibl = max(x["h"] for x in ib), min(x["l"] for x in ib)
    _, _, poc_now = value_area(bars)
    _, _, poc_ib = value_area(ib)
    try:
        r = classify_session(
            bars=[dict(o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"]) for b in bars],
            ib_high=ibh, ib_low=ibl, open_price=bars[0]["o"],
            ib_width_hist=ib_hist, profile_shape=None, vol_ratio=vr,
            prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl,
            poc_now=poc_now, poc_at_ib=poc_ib, is_eod=True,
        )
    except Exception as e:
        return dict(day_type=None, err=repr(e))
    m = r.get("measured") or {}
    return dict(day_type=r.get("day_type"), status=r.get("status"),
                direction=r.get("direction"), dir_bias=r.get("dir_bias"),
                confidence=r.get("confidence"), reason=r.get("reason"),
                sides=m.get("sides"), rib=m.get("rib"), one_tf=m.get("one_tf"),
                close_pos=m.get("close_pos"), ib_width=m.get("ib_width"),
                value_migration=m.get("value_migration"))


# ---------------------------------------------------------------- extremes
def phase_of(t):
    """first hour (<=10:30 ET) / after IB lock (10:30-13:00) / late (>=13:00)."""
    if t.time() < dt.time(10, 30):
        return "שעה-ראשונה"
    if t.time() < dt.time(13, 0):
        return "אחרי-נעילת-IB"
    return "מאוחר"


def extremes_of(bars):
    hi_b = max(bars, key=lambda b: b["h"])
    lo_b = min(bars, key=lambda b: b["l"])
    ib = bars[:IB_BARS]
    ibh, ibl = max(x["h"] for x in ib), min(x["l"] for x in ib)
    hi, lo = hi_b["h"], lo_b["l"]
    close = bars[-1]["c"]
    rng = hi - lo
    return dict(
        hi=hi, hi_t=hi_b["t"], hi_i=bars.index(hi_b), hi_phase=phase_of(hi_b["t"]),
        lo=lo, lo_t=lo_b["t"], lo_i=bars.index(lo_b), lo_phase=phase_of(lo_b["t"]),
        ib_high=ibh, ib_low=ibl, ib_w=round(ibh - ibl, 2),
        open=bars[0]["o"], close=close, rng=round(rng, 2),
        drift=round(close - bars[0]["o"], 2),
        close_pos=round((close - lo) / rng, 3) if rng > 0 else None,
        from_hi=round(hi - close, 2), from_lo=round(close - lo, 2),
        ext_up=round(max(0.0, hi - ibh), 2), ext_dn=round(max(0.0, ibl - lo), 2),
        # which extreme was made LAST = the one the day ran into
        last_extreme=("HIGH" if bars.index(hi_b) > bars.index(lo_b) else "LOW"),
    )


def hold_or_extend(ex):
    """Did the day's LAST extreme hold (mean-revert) or extend into the close?"""
    if ex["close_pos"] is None:
        return "-"
    cp = ex["close_pos"]
    if ex["last_extreme"] == "HIGH":
        return "הרחיב" if cp >= 0.80 else ("החזיק-חלקית" if cp >= 0.50 else "נדחה")
    return "הרחיב" if cp <= 0.20 else ("החזיק-חלקית" if cp <= 0.50 else "נדחה")


# ---------------------------------------------------------------- per-day study
def identifiable_trades(bars, legs, trigs, thr, trades, decs, have_arch, topn=3):
    """The trades a CORRECT system should have taken that day + what MEMS did."""
    out = []
    for lg in sorted(legs, key=lambda x: -x["pts"])[:topn]:
        f = lg["feas"]
        rec = dict(t0=lg["t0"].strftime("%H:%M"), t1=lg["t1"].strftime("%H:%M"),
                   dir=lg["dir"], pts=lg["pts"], p0=lg["p0"], p1=lg["p1"],
                   feas=None, status=None, gate=None, trade_ids=[], live_pnl=0.0)
        if f:
            rec["feas"] = dict(kind=f["kind"], entry=f["entry"], stop=f["stop"],
                               risk=f["risk"], target=f["exit"], reason=f["reason"],
                               usd=f["usd"], pts=f["pts"], mfe=f["mfe"],
                               t_in=f["t_in"].strftime("%H:%M"),
                               t_out=f["t_out"].strftime("%H:%M"),
                               rr=round(f["pts"] / f["risk"], 2) if f["risk"] else None,
                               late=f.get("late_pts"))
        t0, t1 = lg["t0"], lg["t1"] + dt.timedelta(minutes=15)
        mine = [t for t in trades if t["dir"] == lg["dir"] and t0 <= t["t_in"] <= t1]
        live = [t for t in mine if t["mode"] == "live"]
        shad = [t for t in mine if t["mode"] != "live"]
        if live:
            rec["status"] = "זוהה+נלקח"
            rec["trade_ids"] = [t["id"] for t in live]
            rec["live_pnl"] = round(sum(t["pnl"] for t in live), 2)
            rec["pats"] = sorted({t["pat"] for t in live})
            continue_ = True
        else:
            dd = [x for x in decs if x["dir"] == lg["dir"] and t0 <= x["t"] <= t1]
            blk = [x for x in dd if x["blocked"]]
            if blk:
                g = collections.Counter(x["blocked"] for x in blk).most_common(1)[0][0]
                rec["status"] = "זוהה+נחסם"
                rec["gate"] = g
                rec["n_blocked"] = len(blk)
            elif dd:
                rec["status"] = "זוהה+לא-הפך-להזמנה"
            elif shad:
                rec["status"] = "צל-בלבד"
                rec["pats"] = sorted({t["pat"] for t in shad})
            elif not have_arch:
                rec["status"] = "אין-ארכיון"
            else:
                rec["status"] = "לא-זוהה-מעולם"
        out.append(rec)
    return out


def study(days, trades, decs, live_labels):
    lo, hi = dt.date.fromisoformat(D_FIRST), dt.date.fromisoformat(D_LAST)
    arch_days = {x["day"] for x in decs}
    rows = []
    for d in sorted(days):
        if not (lo <= d <= hi):
            continue
        bars = days[d]
        if len(bars) < 20:
            continue
        thr = ORA.thr_for(days, d)
        piv = ORA.zigzag(bars, thr)
        legs = ORA.legs_from(bars, piv)
        trigs = ORA.find_triggers(bars, piv, thr)
        for lg in legs:
            lg["feas"] = None
            for t in [x for x in trigs if x["dir"] == lg["dir"]
                      and lg["i0"] <= x["i"] <= lg["i1"]]:
                r = ORA.sim_trade(bars, t["i"], t["dir"], thr)
                if r:
                    r["kind"] = t["kind"]
                    r["late_pts"] = round(lg["dir"] * (r["entry"] - lg["p0"]), 2)
                    lg["feas"] = r
                    break

        td = [t for t in trades if t["day"] == d]
        live = [t for t in td if t["mode"] == "live"]
        shad = [t for t in td if t["mode"] != "live"]
        dd = [x for x in decs if x["day"] == d]

        ex = extremes_of(bars)
        ph = posthoc_label(days, d, bars)
        ll = live_labels.get(d) or {}
        dtypes = collections.Counter(t["day_type"] for t in live if t["day_type"])
        dt_entry = dtypes.most_common(1)[0][0] if dtypes else None
        dtypes_s = collections.Counter(t["day_type"] for t in shad if t["day_type"])
        dt_entry_s = dtypes_s.most_common(1)[0][0] if dtypes_s else None

        # $ layers
        sys_usd = round(sum(t["pnl"] for t in live), 2)
        held = 0.0
        for t in live:
            if t["entry"] is None:
                continue
            idx = [i for i, b in enumerate(bars) if b["t"] <= t["t_in"]]
            if not idx:
                continue
            r = ORA.sim_trade(bars, idx[-1], t["dir"], thr, t["contracts"] or CONTRACTS)
            if r:
                held += r["usd"]
        c2 = round(sum(x["usd"] for x in
                       ORA.causal_sequence(bars, trigs, thr, limit=2)), 2)
        feas = [l["feas"]["usd"] for l in legs if l["feas"]]
        f2 = round(sum(sorted(feas, reverse=True)[:2]), 2)

        ids = identifiable_trades(bars, legs, trigs, thr, td, dd, d in arch_days)

        rows.append(dict(
            day=str(d), era=("live" if str(d) >= D_LIVE0 else "shadow"),
            n_bars=len(bars), thr=thr, ex=ex, hold=hold_or_extend(ex),
            live_label=ll.get("day_type"), live_ib=(ll.get("ib_high"), ll.get("ib_low")),
            live_open_type=ll.get("opening_type"), live_conf=ll.get("confidence"),
            dt_entry=dt_entry, dt_entry_shadow=dt_entry_s, post=ph,
            n_legs=len(legs), legs_top=ids,
            sys=sys_usd, n_sys=len(live), shadow=round(sum(t["pnl"] for t in shad), 2),
            n_shadow=len(shad), held=round(held, 2), c2=c2, feas2=f2,
            has_arch=(d in arch_days), _trigs=trigs,
            legs_all=[dict(t0=str(l["t0"])[11:16], t1=str(l["t1"])[11:16], dir=l["dir"],
                           pts=l["pts"], feas=(l["feas"]["usd"] if l["feas"] else None),
                           kind=(l["feas"]["kind"] if l["feas"] else None),
                           risk=(l["feas"]["risk"] if l["feas"] else None),
                           late=(l["feas"]["late_pts"] if l["feas"] else None))
                      for l in legs],
        ))
    return rows


# ---------------------------------------------------------------- reporting
# The codebase itself treats these as the SAME label: get_live_day_type remaps
# NV->V and daytype_classify_routes.py:329 normalizes before its own cross-check
# ("_norm_map = {'Normal_Variation': 'Variation'}").  Comparing the raw strings
# would manufacture a 92% "disagreement" that is pure naming (verified, Rule 2).
NORM_MAP = {"Normal_Variation": "Variation"}


def norm(lbl):
    if not lbl:
        return "לא-מסווג"
    return NORM_MAP.get(lbl, lbl)


# ---------------------------------------------------------------- playbook grid
def sim_wide(bars, i, dirn, thr, mult, contracts=CONTRACTS):
    """ORA.sim_trade with the structural stop widened by `mult` (stop-placement
    sensitivity for the per-day-type playbook).  Same entry, same trail exit."""
    base = ORA.sim_trade(bars, i, dirn, thr, contracts)
    if not base or mult == 1.0:
        return base
    entry = base["entry"]
    stop = entry - dirn * base["risk"] * mult
    risk = abs(entry - stop)
    if risk > 2.5 * thr:
        return None
    n = len(bars)
    ext = entry
    exit_p = exit_i = None
    reason = "EOD"
    for k in range(i + 1, n):
        b = bars[k]
        if dirn > 0 and b["l"] <= stop:
            exit_p, exit_i, reason = stop - 0.25, k, "STOP"; break
        if dirn < 0 and b["h"] >= stop:
            exit_p, exit_i, reason = stop + 0.25, k, "STOP"; break
        ext = max(ext, b["h"]) if dirn > 0 else min(ext, b["l"])
        if dirn > 0 and b["c"] <= ext - thr:
            exit_p, exit_i, reason = b["c"] - 0.25, k, "TRAIL"; break
        if dirn < 0 and b["c"] >= ext + thr:
            exit_p, exit_i, reason = b["c"] + 0.25, k, "TRAIL"; break
    if exit_p is None:
        exit_p, exit_i = bars[-1]["c"] - dirn * 0.25, n - 1
    pts = dirn * (exit_p - entry)
    out = dict(base)
    out.update(stop=round(stop, 2), risk=round(risk, 2), exit=round(exit_p, 2),
               pts=round(pts, 2), reason=reason, exit_i=exit_i,
               usd=round(ORA.money(pts, contracts) - ORA.costs(contracts), 2))
    return out


def wide_sequence(bars, trigs, thr, mult, limit=None):
    out, busy = [], -1
    for t in trigs:
        if t["i"] <= busy:
            continue
        r = sim_wide(bars, t["i"], t["dir"], thr, mult)
        if not r:
            continue
        r["kind"] = t["kind"]
        out.append(r)
        busy = r["exit_i"]
        if limit and len(out) >= limit:
            break
    return out


PLAYBOOK_VARIANTS = [
    ("N=1  trail", dict(limit=1)),
    ("N=2  trail", dict(limit=2)),
    ("N=3  trail", dict(limit=3)),
    ("N=inf trail", dict()),
    ("N=2  ladder", dict(limit=2, mode="ladder")),
    ("N=inf ladder", dict(mode="ladder")),
    ("N=2  STAIR-only", dict(limit=2, kinds={"STAIR"})),
    ("N=2  STAIR/BREAK", dict(limit=2, kinds={"STAIR", "BREAK"})),
    ("N=2  REJ/PB-only", dict(limit=2, kinds={"REJ", "PB"})),
    ("N=2  +drift", dict(limit=2, drift=True)),
    ("N=2  cutoff12:30", dict(limit=2, cutoff=dt.time(12, 30))),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/daily_extremes_playbook.json")
    a = ap.parse_args()

    cn = psycopg2.connect(DSN)
    cn.set_session(readonly=True, autocommit=True)
    cur = cn.cursor()
    days = load_bars(cur)
    trades = load_all_trades(cur)
    live_labels = load_live_labels(cur)
    cn.close()
    decs = ORA.load_decisions()

    rows = study(days, trades, decs, live_labels)

    print("== PER DAY ==")
    print("day        era    bars  IBw   HIGH        LOW         close_pos hold      "
          "live_lbl        entry_lbl       posthoc         sys$     held$    c2$     f2$")
    for r in rows:
        e = r["ex"]
        print(f"{r['day']}  {r['era']:6s} {r['n_bars']:4d} {e['ib_w']:6.2f} "
              f"{e['hi']:8.2f}@{e['hi_t'].strftime('%H:%M')} "
              f"{e['lo']:8.2f}@{e['lo_t'].strftime('%H:%M')} "
              f"{(e['close_pos'] if e['close_pos'] is not None else -1):6.2f} "
              f"{r['hold']:10s} {norm(r['live_label']):15s} {norm(r['dt_entry']):15s} "
              f"{norm((r['post'] or {}).get('day_type')):15s} "
              f"{r['sys']:8.2f} {r['held']:8.2f} {r['c2']:8.2f} {r['feas2']:8.2f}")

    # ---- extreme timing stats
    print("\n== EXTREME TIMING ==")
    for which in ("hi_phase", "lo_phase"):
        c = collections.Counter(r["ex"][which] for r in rows)
        print(f"   {which:10s} " + "  ".join(f"{k}={v}" for k, v in c.most_common()))
    c = collections.Counter(r["hold"] for r in rows)
    print("   last-extreme " + "  ".join(f"{k}={v}" for k, v in c.most_common()))
    both_first = sum(1 for r in rows
                     if r["ex"]["hi_phase"] == "שעה-ראשונה" and r["ex"]["lo_phase"] == "שעה-ראשונה")
    print(f"   both extremes in the first hour: {both_first}/{len(rows)}")
    one_first = sum(1 for r in rows
                    if r["ex"]["hi_phase"] == "שעה-ראשונה" or r["ex"]["lo_phase"] == "שעה-ראשונה")
    print(f"   at least one extreme in the first hour: {one_first}/{len(rows)}")
    late = sum(1 for r in rows
               if r["ex"]["hi_phase"] == "מאוחר" or r["ex"]["lo_phase"] == "מאוחר")
    print(f"   at least one extreme late (>=13:00): {late}/{len(rows)}")

    # ---- label agreement (NORMALIZED — NV==V, see NORM_MAP)
    print("\n== LABEL AGREEMENT (live vs post-hoc, normalized) ==")
    for src_name, getter in (
            ("history-label", lambda r: r["live_label"]),
            ("day_type_at_entry", lambda r: r["dt_entry"] or r["dt_entry_shadow"])):
        agree = dis = miss = 0
        dis_rows = []
        for r in rows:
            p = norm((r["post"] or {}).get("day_type"))
            lv = norm(getter(r))
            if p == "לא-מסווג" or lv == "לא-מסווג":
                miss += 1
                continue
            if p == lv:
                agree += 1
            else:
                dis += 1
                dis_rows.append((r["day"], r["era"], lv, p, r["sys"]))
        print(f"   [{src_name}] agree={agree} disagree={dis} unusable={miss} "
              f"rate={100.0*dis/max(1,agree+dis):.0f}%")
        for x in dis_rows:
            print("      ", x)
    # live-history vs entry-stamp (both are LIVE sources — pure internal drift)
    hd = [(r["day"], norm(r["live_label"]), norm(r["dt_entry"]), r["sys"])
          for r in rows if r["live_label"] and r["dt_entry"]
          and norm(r["live_label"]) != norm(r["dt_entry"])]
    hn = sum(1 for r in rows if r["live_label"] and r["dt_entry"])
    print(f"   history-label vs day_type_at_entry (both live): {len(hd)}/{hn} disagree")
    for x in hd:
        print("      ", x)
    ibd = [(r["day"], r["ex"]["ib_w"], round((r["live_ib"][0] or 0) - (r["live_ib"][1] or 0), 2))
           for r in rows if r["live_ib"][0] and r["live_ib"][1]
           and abs((r["live_ib"][0] - r["live_ib"][1]) - r["ex"]["ib_w"]) > 2.0]
    print(f"   exported-IB vs bars-IB mismatch >2pt: {len(ibd)} days")
    for x in ibd:
        print("     ", x)

    # ---- by post-hoc day type
    print("\n== BY POST-HOC DAY TYPE (normalized) ==")
    grp = collections.defaultdict(list)
    for r in rows:
        grp[norm((r["post"] or {}).get("day_type"))].append(r)
    print(f"{'type':18s} {'n':>3s} {'nLive':>5s} {'sys$':>9s} {'held$':>9s} {'c2$':>9s} "
          f"{'f2$':>9s} {'rng':>6s} {'IBw':>6s} {'|drift|':>7s} {'hiFirstHr':>9s}")
    for k, v in sorted(grp.items(), key=lambda kv: -sum(x["feas2"] for kv2 in [kv[1]] for x in kv2)):
        nl = sum(1 for x in v if x["era"] == "live")
        print(f"{k:18s} {len(v):3d} {nl:5d} {sum(x['sys'] for x in v):9.2f} "
              f"{sum(x['held'] for x in v):9.2f} {sum(x['c2'] for x in v):9.2f} "
              f"{sum(x['feas2'] for x in v):9.2f} "
              f"{statistics.median([x['ex']['rng'] for x in v]):6.2f} "
              f"{statistics.median([x['ex']['ib_w'] for x in v]):6.2f} "
              f"{statistics.median([abs(x['ex']['drift']) for x in v]):7.2f} "
              f"{sum(1 for x in v if x['ex']['hi_phase']=='שעה-ראשונה' or x['ex']['lo_phase']=='שעה-ראשונה'):9d}")

    # ---- by LIVE label (what the gates actually consumed)
    print("\n== BY LIVE (entry-stamped) DAY TYPE — live era only ==")
    g2 = collections.defaultdict(list)
    for r in rows:
        if r["era"] != "live":
            continue
        g2[norm(r["dt_entry"] or r["live_label"])].append(r)
    for k, v in sorted(g2.items(), key=lambda kv: -sum(x["sys"] for x in kv[1])):
        print(f"{k:18s} n={len(v):2d}  sys={sum(x['sys'] for x in v):9.2f}  "
              f"held={sum(x['held'] for x in v):9.2f}  c2={sum(x['c2'] for x in v):9.2f}  "
              f"f2={sum(x['feas2'] for x in v):9.2f}")

    # ---- identifiable-trade status census
    print("\n== IDENTIFIABLE-TRADE STATUS (top-3 legs/day) ==")
    st = collections.Counter()
    st_usd = collections.Counter()
    gates = collections.Counter()
    gates_usd = collections.Counter()
    for r in rows:
        for lg in r["legs_top"]:
            st[lg["status"]] += 1
            if lg["feas"]:
                st_usd[lg["status"]] += lg["feas"]["usd"]
            if lg["gate"]:
                gates[lg["gate"]] += 1
                if lg["feas"]:
                    gates_usd[lg["gate"]] += lg["feas"]["usd"]
    for k, v in st.most_common():
        print(f"   {k:22s} n={v:4d}  feasible$={st_usd[k]:10.2f}")
    print("   gates:")
    for k, v in gates.most_common():
        print(f"      {k:28s} n={v:3d}  ${gates_usd[k]:9.2f}")

    # ---- extreme-entry vs continuation-entry (the playbook question)
    print("\n== EXTREME-LEG vs CONTINUATION-LEG (feasible mechanics) ==")
    ext_l, cont_l = [], []
    for r in rows:
        e = r["ex"]
        for lg in r["legs_top"]:
            if not lg["feas"]:
                continue
            # a leg that STARTS at the session extreme = "from the extreme"
            at_ext = (abs(lg["p0"] - e["lo"]) <= 1.0 and lg["dir"] > 0) or \
                     (abs(lg["p0"] - e["hi"]) <= 1.0 and lg["dir"] < 0)
            (ext_l if at_ext else cont_l).append(lg["feas"]["usd"])
    for nm, arr in (("from-extreme", ext_l), ("continuation", cont_l)):
        if arr:
            print(f"   {nm:14s} n={len(arr):4d}  tot={sum(arr):10.2f}  "
                  f"avg={statistics.fmean(arr):8.2f}  med={statistics.median(arr):8.2f}  "
                  f"win%={100.0*sum(1 for x in arr if x>0)/len(arr):.0f}")

    # ---- first-hour entry timing
    print("\n== ENTRY-HOUR of the feasible top legs ==")
    hr = collections.Counter()
    hru = collections.Counter()
    for r in rows:
        for lg in r["legs_top"]:
            if lg["feas"]:
                h = int(lg["feas"]["t_in"][:2])
                hr[h] += 1
                hru[h] += lg["feas"]["usd"]
    for h in sorted(hr):
        print(f"   {h:02d}:00  n={hr[h]:4d}  ${hru[h]:10.2f}")

    # ================= PER-DAY-TYPE PLAYBOOK GRID =================
    print("\n\n===================== PLAYBOOK GRID PER DAY TYPE =====================")
    print("(all layers fully causal / no-lookahead; 4 contracts; $1.50 RT/c + 1 tick/side)")
    grp2 = collections.defaultdict(list)
    for r in rows:
        grp2[norm((r["post"] or {}).get("day_type"))].append(r)

    pb = {}
    for k, v in sorted(grp2.items(), key=lambda kv: -len(kv[1])):
        print(f"\n--- {k}  (n={len(v)} sessions, {sum(1 for x in v if x['era']=='live')} live) ---")
        res = {}
        for name, kw in PLAYBOOK_VARIANTS:
            s = n = w = g = 0
            for r in v:
                bars = days[dt.date.fromisoformat(r["day"])]
                tr = ORA.causal_sequence(bars, r["_trigs"], r["thr"], **kw)
                val = sum(t["usd"] for t in tr)
                s += val
                n += len(tr)
                w += sum(1 for t in tr if t["usd"] > 0)
                g += (1 if val > 0 else 0)
            res[name] = round(s, 2)
            print(f"   {name:18s} {s:9.2f}  n={n:3d}  win%={100.0*w/n if n else 0:5.1f}  "
                  f"green {g:2d}/{len(v)}  ${s/len(v):7.2f}/day")
        # stop-width sensitivity
        for mult in (1.0, 1.5, 2.0):
            s = n = 0
            for r in v:
                bars = days[dt.date.fromisoformat(r["day"])]
                tr = wide_sequence(bars, r["_trigs"], r["thr"], mult, limit=2)
                s += sum(t["usd"] for t in tr)
                n += len(tr)
            res[f"stop x{mult}"] = round(s, 2)
            print(f"   stop x{mult:<12.1f} {s:9.2f}  n={n:3d}  ${s/len(v):7.2f}/day")
        # trigger family split
        fam = collections.Counter()
        famn = collections.Counter()
        for r in v:
            bars = days[dt.date.fromisoformat(r["day"])]
            for t in ORA.causal_sequence(bars, r["_trigs"], r["thr"]):
                fam[t["kind"]] += t["usd"]
                famn[t["kind"]] += 1
        print("   families: " + "  ".join(
            f"{kk}={vv:.0f}(n={famn[kk]})" for kk, vv in fam.most_common()))
        # entry hour
        hrs = collections.Counter()
        for r in v:
            bars = days[dt.date.fromisoformat(r["day"])]
            for t in ORA.causal_sequence(bars, r["_trigs"], r["thr"], limit=3):
                hrs[t["t_in"].hour] += t["usd"]
        print("   by hour:  " + "  ".join(f"{h:02d}={hrs[h]:.0f}" for h in sorted(hrs)))
        # shape stats
        print(f"   shape:    median range {statistics.median([x['ex']['rng'] for x in v]):.1f}pt · "
              f"IB {statistics.median([x['ex']['ib_w'] for x in v]):.1f}pt · "
              f"|drift| {statistics.median([abs(x['ex']['drift']) for x in v]):.1f}pt · "
              f"legs {statistics.median([x['n_legs'] for x in v]):.0f} · "
              f"close_pos med {statistics.median([x['ex']['close_pos'] or 0.5 for x in v]):.2f}")
        hp = collections.Counter(x["ex"]["hi_phase"] for x in v)
        lp = collections.Counter(x["ex"]["lo_phase"] for x in v)
        print(f"   HIGH formed: {dict(hp)}   LOW formed: {dict(lp)}")
        print(f"   last-extreme behaviour: {dict(collections.Counter(x['hold'] for x in v))}")
        print(f"   ext beyond IB: up med {statistics.median([x['ex']['ext_up'] for x in v]):.1f}pt · "
              f"dn med {statistics.median([x['ex']['ext_dn'] for x in v]):.1f}pt")
        print(f"   books: sys={sum(x['sys'] for x in v):.2f} ({sum(x['n_sys'] for x in v)} trades) "
              f"held={sum(x['held'] for x in v):.2f}  Δ={sum(x['held'] for x in v)-sum(x['sys'] for x in v):.2f}")
        pb[k] = dict(n=len(v), n_live=sum(1 for x in v if x["era"] == "live"),
                     sys=round(sum(x["sys"] for x in v), 2),
                     n_sys=sum(x["n_sys"] for x in v),
                     held=round(sum(x["held"] for x in v), 2),
                     variants=res, families=dict(fam), hours=dict(hrs),
                     hi_phase=dict(hp), lo_phase=dict(lp))

    # ---- entry budget: what does trade #k of the day earn, per day type?
    print("\n\n===================== ENTRY BUDGET (trade #k of the day) =====================")
    for k, v in sorted(grp2.items(), key=lambda kv: -len(kv[1])):
        byk = collections.Counter()
        nk = collections.Counter()
        for r in v:
            bars = days[dt.date.fromisoformat(r["day"])]
            for j, t in enumerate(ORA.causal_sequence(bars, r["_trigs"], r["thr"]), 1):
                byk[min(j, 6)] += t["usd"]
                nk[min(j, 6)] += 1
        print(f"   {k:16s} " + "  ".join(
            f"#{j}={byk[j]:.0f}(n={nk[j]})" for j in sorted(byk)))

    # ---- scale-in: after a WINNING first trade, is the next same-direction
    #      trigger worth taking (vs the next trigger in any direction)?
    print("\n===================== SCALE-IN / RE-ENTRY AFTER A WINNER =====================")
    for k, v in sorted(grp2.items(), key=lambda kv: -len(kv[1])):
        same = opp = anyd = 0.0
        ns = no_ = na = 0
        for r in v:
            bars = days[dt.date.fromisoformat(r["day"])]
            seq = ORA.causal_sequence(bars, r["_trigs"], r["thr"])
            if not seq or seq[0]["usd"] <= 0:
                continue
            first = seq[0]
            for t in seq[1:2]:
                anyd += t["usd"]; na += 1
                if t["dir"] == first["dir"]:
                    same += t["usd"]; ns += 1
                else:
                    opp += t["usd"]; no_ += 1
        print(f"   {k:16s} after-winner next trade: same-dir ${same:8.2f}(n={ns})  "
              f"opp-dir ${opp:8.2f}(n={no_})  any ${anyd:8.2f}(n={na})")

    # ---- Variation is 2/3 of all days -> split it by observable sub-shape
    print("\n===================== VARIATION SUB-SHAPES (|drift| vs range) =====================")
    vr = grp2.get("Variation", [])
    sub = collections.defaultdict(list)
    for r in vr:
        e = r["ex"]
        ratio = abs(e["drift"]) / e["rng"] if e["rng"] else 0
        cp = e["close_pos"] if e["close_pos"] is not None else 0.5
        if ratio >= 0.40 and (cp >= 0.75 or cp <= 0.25):
            sub["V-רגל (drift>=40% טווח, סגירה בקצה)"].append(r)
        elif ratio < 0.20:
            sub["V-רוטציה (drift<20% טווח)"].append(r)
        else:
            sub["V-ביניים"].append(r)
    for k, v in sub.items():
        s1 = s2 = s3 = sinf = 0.0
        for r in v:
            bars = days[dt.date.fromisoformat(r["day"])]
            s1 += sum(t["usd"] for t in ORA.causal_sequence(bars, r["_trigs"], r["thr"], limit=1))
            s2 += sum(t["usd"] for t in ORA.causal_sequence(bars, r["_trigs"], r["thr"], limit=2))
            s3 += sum(t["usd"] for t in ORA.causal_sequence(bars, r["_trigs"], r["thr"], limit=3))
            sinf += sum(t["usd"] for t in ORA.causal_sequence(bars, r["_trigs"], r["thr"]))
        print(f"   {k:34s} n={len(v):2d}  N1={s1:8.2f}  N2={s2:8.2f}  N3={s3:8.2f}  "
              f"Ninf={sinf:9.2f}  sys={sum(x['sys'] for x in v):8.2f}  "
              f"held={sum(x['held'] for x in v):8.2f}  "
              f"$/day(N1)={s1/len(v):7.2f}")

    # ---- the classic day-type trade the swing triggers do NOT express:
    #      the IB EXTENSION entry.  First close beyond the locked IB edge after
    #      10:30 ET -> enter, structural stop, and three ways to hold it.
    print("\n===================== IB-EXTENSION ENTRY (the day-type trade) =====================")
    print("entry = first 5-min CLOSE beyond the 09:30-10:30 IB edge, after bar 12; "
          "stop = 3-bar structural; 1 entry/day")
    hdr = f"{'type':16s} {'n':>3s} {'took':>4s} {'EOD-hold':>10s} {'trail':>10s} {'ladder':>10s} {'win%EOD':>7s}"
    print(hdr)
    ibx_rows = {}
    for k, v in sorted(grp2.items(), key=lambda kv: -len(kv[1])):
        tot_eod = tot_tr = tot_lad = 0.0
        took = win = 0
        detail = []
        for r in v:
            bars = days[dt.date.fromisoformat(r["day"])]
            if len(bars) <= IB_BARS + 2:
                continue
            ib = bars[:IB_BARS]
            ibh, ibl = max(x["h"] for x in ib), min(x["l"] for x in ib)
            hit = None
            for i in range(IB_BARS, len(bars) - 1):
                if bars[i]["c"] > ibh:
                    hit = (i, 1); break
                if bars[i]["c"] < ibl:
                    hit = (i, -1); break
            if not hit:
                continue
            i, dirn = hit
            base = ORA.sim_trade(bars, i, dirn, r["thr"])
            if not base:
                continue
            took += 1
            entry, stop = base["entry"], base["stop"]
            # EOD-hold: stop only, else 15:55 close
            xp = None
            for kk in range(i + 1, len(bars)):
                b = bars[kk]
                if (dirn > 0 and b["l"] <= stop) or (dirn < 0 and b["h"] >= stop):
                    xp = stop - dirn * 0.25
                    break
            if xp is None:
                xp = bars[-1]["c"] - dirn * 0.25
            pts = dirn * (xp - entry)
            usd = round(ORA.money(pts, CONTRACTS) - ORA.costs(CONTRACTS), 2)
            tot_eod += usd
            win += (1 if usd > 0 else 0)
            tot_tr += base["usd"]
            lad = ORA.sim_ladder(bars, i, dirn, r["thr"])
            tot_lad += (lad["usd"] if lad else 0)
            detail.append((r["day"], bars[i]["t"].strftime("%H:%M"),
                           "L" if dirn > 0 else "S", round(pts, 2), usd, base["usd"]))
        print(f"{k:16s} {len(v):3d} {took:4d} {tot_eod:10.2f} {tot_tr:10.2f} {tot_lad:10.2f} "
              f"{(100.0*win/took if took else 0):7.1f}")
        ibx_rows[k] = dict(n=len(v), took=took, eod=round(tot_eod, 2),
                           trail=round(tot_tr, 2), ladder=round(tot_lad, 2),
                           win=win, detail=detail)
    print("\n   per-day IB-extension detail (day, time, dir, pts, $EOD, $trail):")
    for k, d_ in ibx_rows.items():
        for x in d_["detail"]:
            print(f"      {k:16s} {x[0]} {x[1]} {x[2]} {x[3]:7.2f}pt  EOD${x[4]:8.2f}  trail${x[5]:8.2f}")

    for r in rows:
        r.pop("_trigs", None)
    with open(a.json, "w") as fh:
        json.dump(dict(rows=rows, playbook=pb, ibx=ibx_rows), fh, indent=1, default=str)
    print("\njson ->", a.json)


if __name__ == "__main__":
    main()
