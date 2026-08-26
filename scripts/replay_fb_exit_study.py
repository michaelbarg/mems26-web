#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""replay_fb_exit_study.py — FAILED_BREAK exit-policy study (E0-E5).

Work order: docs/handoff/CC_WORKORDER_EXIT_STUDY_2026-08-26.md
Michael 26.08: "זיהוי נכון + מימושים בזמן = רווח גבוה יותר" ·
               "לזהות לאן המחיר רוצה להגיע — ומימוש מוקדם יותר"

The 48 variant-A entries are FROZEN (same detector, backend/v9/systems/
failed_break.py, byte-identical detection loop as the §D run):
  - bars: v9_bars_5min_woodies RTH 09:30-16:00 ET, MES
  - causal VA: v9_tpo_history (created_at = availability, whatif_report.py style)
  - detection from bar IB_BARS on, window >= 14 bars, already_fired per session
  - sessions: 2026-07-07..2026-08-25, day types Variation+Normal+Neutral
    (classify_session EOD, same flag set as replay_dalton_over_detectors.py)

Exit policies (same entries, same bars, single slot per session):
  E0  baseline — all 3 contracts exit at T1=POC (the §D run; must equal +$118.20)
  E1  C1 out at POC, stop→BE, C2+C3 held to the opposite edge
  E2  all 3 held to the opposite edge; early exit only on acceptance
      (2 consecutive closes) beyond POC against us
  E3  symmetric exit — hold to opposite edge OR exit on an opposite
      failed-break (same detector, opposite direction = exit signal)
  E4  E1 + swing trail on the runner after POC (live swing_trail module,
      rev = prev-session ATR clamp, floor BE, never widens; edge target kept)
  E4b E1 + F5-pure runner: NO fixed target, trail/EOD only (F5 as built)
  E5  front-offset grid over E0-E3: target minus {1,2,3 ticks} and
      {10%,15% of that leg's entry→target distance}

Sim conventions (identical to the §D whatif harness so E0 reproduces):
  - entry at trigger-bar close; sim starts next bar
  - within a bar: stop first (conservative), then targets, then close-based
    exits (acceptance / symmetric), then trail update (affects next bar)
  - all fills at exact price; flat TICK (0.25 pt) per contract deducted
  - NO commission (the §D harness charged none — stated in the report)
  - EOD: remaining contracts exit at the last RTH bar close
  - 3 contracts, $5/pt (MES)

READ-ONLY on the DB (readonly session). Writes stdout + --json.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import statistics
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# S1 flags for the day-type classifier (same set as replay_dalton_over_detectors)
for _k, _v in {
    "S1_NEW_CLASSIFIER": "1", "S1_ENGINE_NEW_CLASSIFIER": "1",
    "S1_OPEN_DRIVE_TREND": "1", "S1_COMMITTED_PROVISIONAL_V1": "1",
    "S1_CONFIDENCE_V2": "1", "S1_IB_SANITY_V1": "1",
    "S1_ACCEPTANCE_RECLASS_V1": "1", "S1_DD_INVALIDATION_V1": "1",
    "S1_VALUE_MIGRATION_V1": "1", "S1_TREND_CONTROL_V1": "1",
    "S1_TREND_ELONGATION_V1": "1", "S1_RECLASS_REQUIRES_IB_EXT_V1": "1",
}.items():
    os.environ.setdefault(_k, _v)

from backend.v9.systems.failed_break import (  # noqa: E402
    detect_failed_break, build_failed_break_setup)
from backend.v9.systems.day_type.classifier_core import classify_session  # noqa: E402
from backend.v9.services.trade_manager.swing_trail import (  # noqa: E402
    swing_rev_threshold, swing_trail_stop)

DSN = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12
POINT_USD = 5.0
TICK = 0.25
CONTRACTS = 3
D0, D1 = "2026-07-07", "2026-08-25"

TICK_OFFSETS = (0.25, 0.50, 0.75)          # 1, 2, 3 ticks
PCT_OFFSETS = (0.10, 0.15)                 # of that leg's entry→target distance


# ────────────────────────── data loading ──────────────────────────

def load_days(cur):
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               open, high, low, close, volume
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date BETWEEN %s AND %s
          AND (ts AT TIME ZONE 'America/New_York')::time >= %s
          AND (ts AT TIME ZONE 'America/New_York')::time < %s
          AND symbol = 'MES'
        ORDER BY ts
    """, (D0, D1, RTH0, RTH1))
    days = collections.OrderedDict()
    for et, o, h, l, c, v in cur.fetchall():
        days.setdefault(et.date(), []).append(
            {"ts": et, "t": et, "o": float(o), "h": float(h), "l": float(l),
             "c": float(c), "v": float(v or 0)})
    return days


def load_tpo_history(cur, d0, d1):
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York')::date AS d,
               (created_at AT TIME ZONE 'America/New_York') AS avail,
               vah, val, poc
        FROM v9_tpo_history
        WHERE (ts AT TIME ZONE 'America/New_York')::date BETWEEN %s AND %s
        ORDER BY created_at
    """, (d0, d1))
    out = collections.defaultdict(list)
    for d, avail, vah, val, poc in cur.fetchall():
        out[d].append({"avail": avail,
                       "vah": float(vah) if vah is not None else None,
                       "val": float(val) if val is not None else None,
                       "poc": float(poc) if poc is not None else None})
    return out


def load_tpo_sessions(cur):
    cur.execute("""
        SELECT trading_date, vah_price, val_price
        FROM v9_tpo_sessions WHERE session_type = 'CASH' ORDER BY trading_date
    """)
    tpo = {}
    for td, vah, val in cur.fetchall():
        d = td if isinstance(td, dt.date) else dt.date.fromisoformat(str(td))
        tpo[d] = {"vah": float(vah) if vah else None,
                  "val": float(val) if val else None}
    return tpo


def causal_va(snaps, bar_ts):
    """Most recent VA snapshot known BEFORE/AT bar_ts (whatif_report.py exact)."""
    best = None
    for s in snaps:
        if s["avail"] and s["avail"] <= bar_ts:
            if s["vah"] is not None and s["val"] is not None:
                best = s
    return best


# ────────────────────────── session prep ──────────────────────────

def classify_day(days, tpo, d):
    bars = days[d]
    ibh = max(b["h"] for b in bars[:IB_BARS])
    ibl = min(b["l"] for b in bars[:IB_BARS])
    prev_tpo = [k for k in tpo if k < d]
    pvah = pval = None
    if prev_tpo:
        pd = max(prev_tpo)
        pvah, pval = tpo[pd].get("vah"), tpo[pd].get("val")
    prev_bars = [k for k in days if k < d]
    pdh = pdl = None
    if prev_bars:
        pb = days[max(prev_bars)]
        pdh = max(b["h"] for b in pb)
        pdl = min(b["l"] for b in pb)
    eod = classify_session(
        bars=[{"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
              for b in bars],
        ib_high=ibh, ib_low=ibl, open_price=bars[0]["o"],
        prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl, is_eod=True)
    return eod.get("day_type", "UNKNOWN")


def detect_candidates(bars, snaps):
    """FROZEN detection — byte-identical to the §D whatif loop."""
    cands = []
    fired = set()
    for i in range(IB_BARS, len(bars)):
        window = bars[:i + 1]
        va = causal_va(snaps, bars[i]["ts"])
        if not va or len(window) < 14:
            continue
        trig = detect_failed_break(window, va["vah"], va["val"],
                                   edge_label="VA", already_fired=fired)
        if trig:
            fired.add(trig["type"])
            setup = build_failed_break_setup(trig, contracts=CONTRACTS)
            cands.append({"bar": i, "time": bars[i]["ts"].strftime("%H:%M"),
                          "trig": trig, "setup": setup})
    return cands


# ────────────────────────── policy simulator ──────────────────────────

import math


def _off_target(t, entry, sign, offset_mode):
    """Pull a target closer to entry by the offset. Rounded to tick grid."""
    if t is None or offset_mode is None:
        return t
    kind, val = offset_mode
    if kind == "grid":
        # tradability fix only: round the (possibly off-grid) §D target toward
        # entry to the nearest tick — where a real MES limit must rest.
        if sign > 0:
            return round(math.floor(t / TICK) * TICK, 2)
        return round(math.ceil(t / TICK) * TICK, 2)
    if kind == "ticks":
        o = val
    else:  # pct of that leg's entry→target distance
        o = val * abs(t - entry)
    t2 = t - sign * o
    return round(round(t2 / TICK) * TICK, 2)


def simulate(bars, snaps, cand, policy, *, rev=None, offset_mode=None):
    """One trade under one policy. Returns dict with pnl/legs/exit_i/capture."""
    setup = cand["setup"]
    trig = cand["trig"]
    i0 = cand["bar"]
    direction = setup["direction"]
    sign = 1.0 if direction == "LONG" else -1.0
    entry = float(setup["entry_price"])
    stop = float(setup["stop"])
    poc_t = float(setup["t1"])          # POC leg target (with routable fallback)
    ride_t = float(setup["t2"])         # opposite-edge target (with fallback)
    poc_raw = float(trig["target_poc"])  # raw POC for the acceptance test
    full_dist = abs(ride_t - entry)     # denominator for capture%

    # legs: list of [qty, target or None]
    if policy == "E0":
        legs = [[3, poc_t]]
        be_after = None
    elif policy in ("E1", "E4"):
        legs = [[1, poc_t], [2, ride_t]]
        be_after = 0
    elif policy == "E4b":
        legs = [[1, poc_t], [2, None]]
        be_after = 0
    elif policy in ("E2", "E3"):
        legs = [[3, ride_t]]
        be_after = None
    else:
        raise ValueError(policy)

    if offset_mode is not None:
        for lg in legs:
            lg[1] = _off_target(lg[1], entry, sign, offset_mode)

    trail_on = policy in ("E4", "E4b") and rev is not None
    accept_exit = policy == "E2"
    sym_exit = policy == "E3"

    left = [lg[0] for lg in legs]
    tgts = [lg[1] for lg in legs]
    out_legs = []           # (qty, price, reason, bar_idx)
    adverse_closes = 0
    exit_i = len(bars) - 1
    trailed = False

    def _flat(k, price, reason):
        for gi in range(len(left)):
            if left[gi]:
                out_legs.append((left[gi], price, reason, k))
                left[gi] = 0

    n = len(bars)
    for k in range(i0 + 1, n):
        b = bars[k]
        # 1. stop first (conservative)
        if (direction == "LONG" and b["l"] <= stop) or \
           (direction == "SHORT" and b["h"] >= stop):
            _flat(k, stop, "STOP" if abs(stop - entry) > 1e-9 else "BE")
            exit_i = k
            break
        # 2. targets (resting limits)
        for gi, q in enumerate(left):
            t = tgts[gi]
            if not q or t is None:
                continue
            if (direction == "LONG" and b["h"] >= t) or \
               (direction == "SHORT" and b["l"] <= t):
                out_legs.append((q, t, "T%d" % (gi + 1), k))
                left[gi] = 0
                if be_after is not None and gi == be_after:
                    nb = entry
                    if (direction == "LONG" and nb > stop) or \
                       (direction == "SHORT" and nb < stop):
                        stop = nb
        if not any(left):
            exit_i = k
            break
        # 3. close-based exits
        if accept_exit:
            adverse = (direction == "LONG" and b["c"] < poc_raw) or \
                      (direction == "SHORT" and b["c"] > poc_raw)
            adverse_closes = adverse_closes + 1 if adverse else 0
            if adverse_closes >= 2:
                _flat(k, b["c"], "ACCEPT_POC")
                exit_i = k
                break
        if sym_exit:
            va = causal_va(snaps, b["ts"])
            if va and k + 1 >= 14:
                opp = detect_failed_break(bars[:k + 1], va["vah"], va["val"],
                                          edge_label="VA", already_fired=set())
                if opp and opp["direction"] != direction:
                    _flat(k, b["c"], "SYM_FB")
                    exit_i = k
                    break
        # 4. trail update (closed bars; effective next bar)
        if trail_on and left and not left[0]:
            anchor = swing_trail_stop(bars[:k + 1], direction,
                                      rev=rev, offset_ticks=1)
            if anchor is not None:
                cand_stop = max(anchor, entry) if direction == "LONG" \
                    else min(anchor, entry)
                if (direction == "LONG" and cand_stop > stop) or \
                   (direction == "SHORT" and cand_stop < stop):
                    stop = round(cand_stop, 2)
                    trailed = True

    if any(left):
        _flat(n - 1, bars[-1]["c"], "EOD")
        exit_i = n - 1

    pnl_usd = 0.0
    captured_pts = 0.0
    for q, px, reason, k in out_legs:
        pts = (px - entry) * sign
        pnl_usd += q * (pts - TICK) * POINT_USD
        captured_pts += q * pts
    capture_pct = (captured_pts / CONTRACTS) / full_dist if full_dist > 0 else None
    return {"pnl": round(pnl_usd, 2), "legs": out_legs, "exit_i": exit_i,
            "capture": capture_pct, "full_dist": round(full_dist, 2),
            "trailed": trailed,
            "ride_touched": any(r.startswith("T") and abs(px - ride_t) < 1e-9
                                for q, px, r, k in out_legs)}


# ────────────────────────── study driver ──────────────────────────

def run_policy(sessions, policy, *, offset_mode=None, revs=None, frozen=False):
    """Run one policy over all sessions. sessions = list of dicts.

    frozen=True: iterate ONLY the E0-taken entries (S["frozen_idx"]) — the 48
    frozen entries of the work order. A frozen entry whose bar falls while the
    slot is still occupied under THIS policy is DROPPED (counted in skipped):
    one position at a time is a real execution constraint, and a policy that
    holds longer can lose a later entry. No policy may ADD an entry.
    """
    day_rows = []
    trades = []
    skipped = 0
    for S in sessions:
        bars, snaps, cands, d = S["bars"], S["snaps"], S["cands"], S["date"]
        allowed = S.get("frozen_idx") if frozen else None
        slot_free = 0
        day_pnl = 0.0
        day_trades = []
        for ci, c in enumerate(cands):
            if allowed is not None and ci not in allowed:
                continue
            if c["bar"] < slot_free:
                skipped += 1
                continue
            r = simulate(bars, snaps, c, policy,
                         rev=(revs or {}).get(d), offset_mode=offset_mode)
            slot_free = r["exit_i"] + 1
            day_pnl += r["pnl"]
            tr = {"date": str(d), "day_type": S["day_type"], "cand": ci,
                  "time": c["time"], "dir": c["setup"]["direction"],
                  "entry": c["setup"]["entry_price"],
                  "pnl": r["pnl"], "capture": r["capture"],
                  "full_dist": r["full_dist"],
                  "legs": [(q, px, rr) for q, px, rr, _ in r["legs"]],
                  "ride_touched": r["ride_touched"], "trailed": r["trailed"]}
            day_trades.append(tr)
            trades.append(tr)
        day_rows.append({"date": str(d), "day_type": S["day_type"],
                         "pnl": round(day_pnl, 2), "n": len(day_trades),
                         "trades": day_trades})
    return {"policy": policy, "offset": offset_mode, "days": day_rows,
            "trades": trades, "skipped": skipped}


def summarize(res):
    days = res["days"]
    trades = res["trades"]
    pnls = [t["pnl"] for t in trades]
    day_pnls = [r["pnl"] for r in days]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    captures = [t["capture"] for t in trades if t["capture"] is not None]
    tot = sum(pnls)
    top3 = sorted(pnls, reverse=True)[:3]
    by_bucket = collections.defaultdict(float)
    for r in days:
        by_bucket[daytype_bucket(r["day_type"])] += r["pnl"]
    return {
        "total": round(tot, 2),
        "median_day": round(statistics.median(day_pnls), 2) if day_pnls else 0.0,
        "n_trades": len(trades), "skipped": res["skipped"],
        "win_pct": round(100.0 * len(wins) / len(pnls), 1) if pnls else 0.0,
        "avg_win": round(statistics.mean(wins), 2) if wins else 0.0,
        "avg_loss": round(statistics.mean(losses), 2) if losses else 0.0,
        "capture_mean": round(100.0 * statistics.mean(captures), 1) if captures else None,
        "capture_agg": round(100.0 * (
            sum(t["capture"] * t["full_dist"] for t in trades if t["capture"] is not None)
            / max(sum(t["full_dist"] for t in trades if t["capture"] is not None), 1e-9)), 1)
        if captures else None,
        "days_pos": sum(1 for p in day_pnls if p > 0),
        "days_neg": sum(1 for p in day_pnls if p < 0),
        "n_days": len(day_pnls),
        "top3_sum": round(sum(top3), 2),
        "by_daytype": {k: round(v, 2) for k, v in sorted(by_bucket.items())},
    }


def daytype_bucket(day_type):
    s = day_type or ""
    if "Variation" in s:
        return "Variation"
    if "Neutral" in s:
        return "Neutral"
    if "Normal" in s:
        return "Normal"
    return s or "Other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/fb_exit_study.json")
    ap.add_argument("--base-only", action="store_true")
    args = ap.parse_args()

    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    days = load_days(cur)
    tpo_hist = load_tpo_history(cur, D0, D1)
    tpo_sess = load_tpo_sessions(cur)
    conn.close()

    # classify + filter sessions
    sessions = []
    excluded = []
    for d in sorted(days):
        if len(days[d]) < 20:
            excluded.append((str(d), f"bars={len(days[d])}"))
            continue
        day_type = classify_day(days, tpo_sess, d)
        bucket = daytype_bucket(day_type)
        if bucket not in ("Variation", "Normal", "Neutral"):
            excluded.append((str(d), day_type))
            continue
        cands = detect_candidates(days[d], tpo_hist.get(d, []))
        sessions.append({"date": d, "bars": days[d],
                         "snaps": tpo_hist.get(d, []),
                         "day_type": day_type, "cands": cands})

    n_cands = sum(len(S["cands"]) for S in sessions)
    print(f"sessions={len(sessions)} (excluded {len(excluded)}: {excluded})")
    print(f"frozen candidates={n_cands}")
    fallback_t1 = sum(1 for S in sessions for c in S["cands"]
                      if abs(c["setup"]["t1"] - c["trig"]["target_poc"]) > 1e-9)
    fallback_t2 = sum(1 for S in sessions for c in S["cands"]
                      if abs(c["setup"]["t2"] - c["trig"]["target_opposite"]) > 1e-9)
    print(f"t1(POC) fallbacks={fallback_t1} · t2(opposite) fallbacks={fallback_t2}")

    # rev per day for E4 (prev session ATR, causal)
    revs = {}
    all_days = sorted(days)
    for d in all_days:
        prevs = [k for k in all_days if k < d]
        revs[d] = swing_rev_threshold(days[max(prevs)]) if prevs else None

    # ---------- E0 first pass: freeze the taken entries (the 48) ----------
    res0_all = run_policy(sessions, "E0", revs=revs)
    taken = collections.defaultdict(set)
    for t in res0_all["trades"]:
        taken[t["date"]].add(t["cand"])
    for S in sessions:
        S["frozen_idx"] = taken.get(str(S["date"]), set())
    n_frozen = sum(len(S["frozen_idx"]) for S in sessions)
    print(f"frozen entries (E0-taken) = {n_frozen} "
          f"(detected {n_cands}, slot-skipped in E0: {res0_all['skipped']})")

    # ---------- target map (the frozen 48, before any policy) ----------
    tmap = []
    for S in sessions:
        bars = S["bars"]
        for ci, c in enumerate(S["cands"]):
            if ci not in S["frozen_idx"]:
                continue
            setup, i0 = c["setup"], c["bar"]
            sign = 1.0 if setup["direction"] == "LONG" else -1.0
            entry = float(setup["entry_price"])
            stop = float(setup["stop"])
            ride = float(setup["t2"])
            full = abs(ride - entry)
            best = 0.0
            best_pre_stop = 0.0
            stopped = False
            for k in range(i0 + 1, len(bars)):
                b = bars[k]
                fav = (b["h"] - entry) * sign if sign > 0 else (entry - b["l"])
                if not stopped:
                    if (sign > 0 and b["l"] <= stop) or (sign < 0 and b["h"] >= stop):
                        stopped = True  # strict: exclude this bar's favorable side
                    else:
                        best_pre_stop = max(best_pre_stop, fav)
                best = max(best, fav)
            poc_dist = abs(float(setup["t1"]) - entry)
            tmap.append({"date": str(S["date"]), "cand": ci,
                         "dir": setup["direction"], "time": c["time"],
                         "entry": entry, "stop": stop,
                         "t1": float(setup["t1"]), "t2": float(setup["t2"]),
                         "full": round(full, 2), "poc_dist": round(poc_dist, 2),
                         "mfe_pts": round(best, 2),
                         "mfe_pre_stop_pts": round(best_pre_stop, 2),
                         "mfe_pct": round(100.0 * best / full, 1) if full else None,
                         "mfe_pre_stop_pct": round(100.0 * best_pre_stop / full, 1)
                         if full else None,
                         "poc_shortfall_ticks": round((poc_dist - best_pre_stop) / TICK, 1),
                         "stopped_first": stopped})

    def bucketize(vals):
        b = collections.OrderedDict(
            [("100_touched", 0), ("90-99", 0), ("75-90", 0), ("50-75", 0), ("<50", 0)])
        for v in vals:
            if v is None:
                continue
            if v >= 100.0:
                b["100_touched"] += 1
            elif v >= 90.0:
                b["90-99"] += 1
            elif v >= 75.0:
                b["75-90"] += 1
            elif v >= 50.0:
                b["50-75"] += 1
            else:
                b["<50"] += 1
        return b

    mfe_vals = [t["mfe_pct"] for t in tmap]
    mfe_pre = [t["mfe_pre_stop_pct"] for t in tmap]
    print("\nTARGET MAP (MFE toward opposite edge, % of full distance):")
    print(f"  unconditional (to EOD):   {dict(bucketize(mfe_vals))}"
          f"  median={statistics.median([v for v in mfe_vals if v is not None]):.1f}%")
    print(f"  pre-stop (strict):        {dict(bucketize(mfe_pre))}"
          f"  median={statistics.median([v for v in mfe_pre if v is not None]):.1f}%")

    # shortfall vs the ACTUAL E0 target (POC leg) — where do the stops pile up?
    sf = collections.OrderedDict([("touched_T1", 0), ("miss<=1_tick", 0),
                                  ("miss<=2", 0), ("miss<=3", 0),
                                  ("miss<=8", 0), ("miss>8_ticks", 0)])
    for t in tmap:
        s = t["poc_shortfall_ticks"]
        if s <= 0:
            sf["touched_T1"] += 1
        elif s <= 1:
            sf["miss<=1_tick"] += 1
        elif s <= 2:
            sf["miss<=2"] += 1
        elif s <= 3:
            sf["miss<=3"] += 1
        elif s <= 8:
            sf["miss<=8"] += 1
        else:
            sf["miss>8_ticks"] += 1
    print(f"  shortfall vs POC target (pre-stop, ticks): {dict(sf)}")

    # ---------- policies ----------
    policies = ["E0"] if args.base_only else ["E0", "E1", "E2", "E3", "E4", "E4b"]
    results = {}
    summaries = {}
    for p in policies:
        res = run_policy(sessions, p, revs=revs, frozen=True)
        results[p] = res
        summaries[p] = summarize(res)
        s = summaries[p]
        print(f"\n{p}: total=${s['total']:+.2f} median-day=${s['median_day']:.2f} "
              f"trades={s['n_trades']} (skip {s['skipped']}) win={s['win_pct']}% "
              f"avgW=${s['avg_win']:.2f} avgL=${s['avg_loss']:.2f} "
              f"capture(mean/agg)={s['capture_mean']}/{s['capture_agg']}% "
              f"days+={s['days_pos']}/{s['n_days']} top3=${s['top3_sum']:.2f} "
              f"by_type={s['by_daytype']}")

    # per-day table for E0 (reproduction check against the §D report)
    print("\nE0 per-day (vs published §D rows):")
    for r in results["E0"]["days"]:
        if r["n"]:
            det = " · ".join(f"{t['dir'][0]} {t['pnl']:+.2f}"
                             f"({t['legs'][-1][2]})" for t in r["trades"])
            print(f"  {r['date']} {r['day_type']:22s} {r['pnl']:+9.2f}  {det}")

    # ---------- E5 grid ----------
    grid = {}
    if not args.base_only:
        print("\nE5 front-offset grid (total $ / win% / trades):")
        for base in ("E0", "E1", "E2", "E3"):
            for kind, vals in (("grid", (0.0,)),
                               ("ticks", TICK_OFFSETS), ("pct", PCT_OFFSETS)):
                for v in vals:
                    om = (kind, v)
                    res = run_policy(sessions, base, offset_mode=om,
                                     revs=revs, frozen=True)
                    sm = summarize(res)
                    key = f"{base}-{kind}{v}"
                    grid[key] = sm
                    grid[key + "__res"] = res
                    print(f"  {base} - {kind} {v}: total=${sm['total']:+9.2f} "
                          f"win={sm['win_pct']:4.1f}% n={sm['n_trades']} "
                          f"median-day=${sm['median_day']:.2f} "
                          f"days+={sm['days_pos']}/{sm['n_days']}")

    # anchor 25.08
    print("\n25.08 anchor per policy:")
    for p in policies:
        for r in results[p]["days"]:
            if r["date"] == "2026-08-25":
                for t in r["trades"]:
                    print(f"  {p}: {t['dir']} @{t['entry']} {t['time']} "
                          f"→ {t['pnl']:+.2f} legs={t['legs']} "
                          f"capture={None if t['capture'] is None else round(100*t['capture'],1)}%")

    out = {
        "meta": {"d0": D0, "d1": D1, "contracts": CONTRACTS,
                 "sessions": len(sessions), "candidates": n_cands,
                 "excluded": excluded,
                 "fallback_t1": fallback_t1, "fallback_t2": fallback_t2},
        "target_map": tmap,
        "target_map_hist": {"unconditional": dict(bucketize(mfe_vals)),
                            "pre_stop": dict(bucketize(mfe_pre))},
        "summaries": summaries,
        "grid": {k: v for k, v in grid.items() if not k.endswith("__res")},
        "results": {p: {"days": results[p]["days"]} for p in results},
        "grid_results": {k[:-5]: {"days": v["days"], "trades": v["trades"]}
                         for k, v in grid.items() if k.endswith("__res")},
    }
    with open(args.json, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nJSON → {args.json}")


if __name__ == "__main__":
    main()
