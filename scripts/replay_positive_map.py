#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""replay_positive_map.py — "ממתי ואיך זה כן עובד": תקרה/רצפה-כפולה × סוג-יום × צד-S1 × עידן.

Michael 2026-08-26 (phone 09:08): "כניסה לא בקיצון אלא כאשר מתגבשת תבנית
תקרה-כפולה או רצפה-כפולה מכיוון לכיוון. יעד רווח = POC ולאו דווקא המשך לצד
השני, כי זה צריך להיות זיגזאג."  Anchor: 25.08 ≈ 8 alternating VAH↔VAL legs.

Measurements (read-only research; no live surface touched):
  1. 25.08 anatomy — VAH↔VAL legs; per-turn: did a DOUBLE form, what it paid.
  2. Historical map — the same binary double detector over every judgeable
     session 2026-06-05..2026-08-25. P&L policies: SPLIT (2 @ POC, 1 runner to
     the opposite edge with stop→BE after the POC leg) and ALLPOC (3 @ POC).
     Cells: day-type bucket × S1-side conformity × era.
  3. Same days: double-pattern vs the frozen single FAILED_BREAK detector.
  4. v9_trades S2/S4 — trade direction conform vs non-conform to the day's
     S1 side (EOD-reconstructed), per pattern / era / mode.

DOUBLE pattern — binary geometric definition (Michael's spec, operationalized):
  touch(TOP)  = bar with high >= causal_VAH - 2.0  AND close < causal_VAH
  touch(BOT)  = bar with low  <= causal_VAL + 2.0  AND close > causal_VAL
  double      = two touches i<j, j-i <= 12 bars, |extreme_i - extreme_j| <= 2.0,
                with at least one bar between them fully out of the edge zone
                (high < VAH-2.0 for TOP / low > VAL+2.0 for BOT) — two distinct
                pushes, not one churn.
  trigger     = close of the SECOND rejection bar (entry there);
                stop beyond the double extreme +1.5 pts, capped 12 pts from
                entry; target = causal POC at trigger.

Data loading + sim conventions CLONED from scripts/replay_fb_exit_study.py
(frozen §D harness): bars = v9_bars_5min_woodies RTH 09:30-16:00 ET · causal
VA = v9_tpo_history with created_at = availability · entry at trigger-bar
close, sim starts next bar · stop first within a bar · EOD flat at last RTH
close · 0.25 pt flat slip per contract · single slot per session · triggers
only from bar index >= 13 (window >= 14, as the FB study).
Costs (house, per docs/reports/CC_EXIT_STUDY_2026-08-26.md §G):
  slip 0.25 pt/contract (§D convention)  +  COMM_RT = $1.50/contract round-turn.
READ-ONLY on the DB. Writes stdout + --json (/tmp/positive_map.json).
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

# S1 flags for the day-type classifier (same set as replay_fb_exit_study.py)
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

DSN = os.environ.get("DATABASE_URL", "postgresql://localhost/mems26")
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12
MIN_TRIG_BAR = 13          # FB study: window >= 14 → earliest trigger index 13
POINT_USD = 5.0
TICK = 0.25
SLIP = 0.25                # §D harness flat slip per contract (pts)
COMM_RT = 1.50             # house commission per contract round-turn ($)
CONTRACTS = 3
TOL = 2.0                  # ±2 pts: edge-zone half width AND extreme-match tol
MAX_GAP = 12               # bars between the two touches
STOP_OFF = 1.5
STOP_CAP = 12.0
D0_BARS, D0, D1 = "2026-06-01", "2026-06-05", "2026-08-25"
FB_D0 = "2026-07-07"       # the frozen-48 window start (comparison universe)
ERA_B1 = dt.date(2026, 7, 17)   # machine cutover
ERA_B2 = dt.date(2026, 8, 13)


# ────────────────────────── data loading (cloned) ──────────────────────────

def load_days(cur, d0, d1):
    cur.execute("""
        SELECT (ts AT TIME ZONE 'America/New_York') AS et,
               open, high, low, close, volume
        FROM v9_bars_5min_woodies
        WHERE (ts AT TIME ZONE 'America/New_York')::date BETWEEN %s AND %s
          AND (ts AT TIME ZONE 'America/New_York')::time >= %s
          AND (ts AT TIME ZONE 'America/New_York')::time < %s
          AND symbol = 'MES'
        ORDER BY ts
    """, (d0, d1, RTH0, RTH1))
    days = collections.OrderedDict()
    for et, o, h, l, c, v in cur.fetchall():
        days.setdefault(et.date(), []).append(
            {"ts": et, "o": float(o), "h": float(h), "l": float(l),
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


# ────────────────────────── session classification ──────────────────────────

def classify_day_full(days, tpo, d):
    """classify_session EOD — returns the FULL result dict (day_type + direction
    strategy + dir_bias). Same call shape as replay_fb_exit_study.classify_day."""
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
    strat = eod.get("direction")
    bias = eod.get("dir_bias")
    side = "%s(%s)" % (strat, bias) if strat and bias else (strat or bias or "none")
    return {"day_type": eod.get("day_type", "UNKNOWN"),
            "strategy": strat, "dir_bias": bias, "side": side}


def daytype_bucket(day_type):
    s = day_type or ""
    if "Trend" in s:
        return "Trend"
    if "Variation" in s:
        return "Variation"
    if "Neutral" in s:
        return "Neutral"
    if "Normal" in s:
        return "Normal"
    return s or "Other"


DIRECTIONAL_STRATS = ("with_extension", "with_trend", "winner_side")


def allowed_dirs(strategy, bias):
    """S1-side semantics (Michael): fade_both → both; with_extension(X) → only
    the fade of the opposite extreme = trade in the extension direction.
    The classifier also emits with_trend(X) / winner_side(X) (Trend-day
    strategies) — plain semantics: trade in direction X."""
    if strategy == "fade_both":
        return {"LONG", "SHORT"}
    if strategy in DIRECTIONAL_STRATS:
        if bias == "UP":
            return {"LONG"}
        if bias == "DOWN":
            return {"SHORT"}
        return None
    return None


def side_bucket(strategy, bias):
    if strategy == "fade_both":
        return "fade_both"
    if strategy in DIRECTIONAL_STRATS:
        return "%s(%s)" % (strategy, bias or "?")
    return "none"


def era_of(d):
    if d < ERA_B1:
        return "A_pre_0717"
    if d < ERA_B2:
        return "B_0717_0812"
    return "C_0813_plus"


# ────────────────────────── DOUBLE detector ──────────────────────────

def bar_va(bars, snaps):
    return [causal_va(snaps, b["ts"]) for b in bars]


def detect_doubles(bars, snaps):
    """All double-top/bottom trigger candidates in one session (binary spec)."""
    vas = bar_va(bars, snaps)
    n = len(bars)
    up_touch, dn_touch = {}, {}          # bar idx -> extreme price
    up_out, dn_out = [False] * n, [False] * n
    ambig = 0
    for t in range(n):
        va = vas[t]
        if not va:
            continue
        b = bars[t]
        is_up = b["h"] >= va["vah"] - TOL and b["c"] < va["vah"]
        is_dn = b["l"] <= va["val"] + TOL and b["c"] > va["val"]
        if is_up and is_dn:
            ambig += 1          # bar spans both edge zones — not judgeable
        else:
            if is_up:
                up_touch[t] = b["h"]
            if is_dn:
                dn_touch[t] = b["l"]
        up_out[t] = b["h"] < va["vah"] - TOL
        dn_out[t] = b["l"] > va["val"] + TOL
    cands = []

    def scan(touches, out_flags, side):
        idxs = sorted(touches)
        for j in idxs:
            if j < MIN_TRIG_BAR:
                continue
            va = vas[j]
            best_i = None
            for i in reversed([x for x in idxs if x < j]):
                if j - i > MAX_GAP:
                    break
                if abs(touches[i] - touches[j]) > TOL:
                    continue
                if not any(out_flags[k] for k in range(i + 1, j)):
                    continue    # one continuous churn — not two pushes
                best_i = i
                break
            if best_i is None:
                continue
            entry = bars[j]["c"]
            poc = va.get("poc")
            if side == "TOP":
                direction = "SHORT"
                extreme = max(touches[best_i], touches[j])
                stop = min(extreme + STOP_OFF, entry + STOP_CAP)
                edge_opp = va["val"]
                room = poc is not None and poc < entry
            else:
                direction = "LONG"
                extreme = min(touches[best_i], touches[j])
                stop = max(extreme - STOP_OFF, entry - STOP_CAP)
                edge_opp = va["vah"]
                room = poc is not None and poc > entry
            status = "OK"
            if poc is None:
                status = "NO_POC"
            elif not room:
                status = "NO_ROOM"
            cands.append({
                "bar": j, "i": best_i, "side": side, "dir": direction,
                "time": bars[j]["ts"].strftime("%H:%M"),
                "t_first": bars[best_i]["ts"].strftime("%H:%M"),
                "entry": round(entry, 2), "stop": round(stop, 2),
                "extreme": round(extreme, 2),
                "ext_first": round(touches[best_i], 2),
                "ext_second": round(touches[j], 2),
                "poc": None if poc is None else round(poc, 2),
                "edge_opp": round(edge_opp, 2),
                "vah": round(va["vah"], 2), "val": round(va["val"], 2),
                "status": status})

    scan(up_touch, up_out, "TOP")
    scan(dn_touch, dn_out, "BOT")
    cands.sort(key=lambda c: c["bar"])
    return cands, ambig


# ────────────────────────── simulator (harness conventions) ──────────────────

def leg_pnl(q, pts, cost):
    if cost == "par":            # §D convention: slip only, no commission
        return q * (pts - SLIP) * POINT_USD
    if cost == "house":          # slip + commission
        return q * ((pts - SLIP) * POINT_USD - COMM_RT)
    if cost == "comm_only":      # exact fills + commission (Michael's task-1 spec)
        return q * (pts * POINT_USD - COMM_RT)
    raise ValueError(cost)


def simulate(bars, i0, direction, entry, stop0, legs_spec, be_after, cost):
    """legs_spec = [[qty, target-or-None], ...]. Harness conventions:
    sim from bar i0+1 · stop first · then targets in order · BE move after
    legs_spec[be_after] fills · EOD flat at last close."""
    sign = 1.0 if direction == "LONG" else -1.0
    stop = float(stop0)
    left = [lg[0] for lg in legs_spec]
    tgts = [lg[1] for lg in legs_spec]
    out_legs = []
    exit_i = len(bars) - 1
    n = len(bars)

    def _flat(k, price, reason):
        for gi in range(len(left)):
            if left[gi]:
                out_legs.append((left[gi], price, reason, k))
                left[gi] = 0

    for k in range(i0 + 1, n):
        b = bars[k]
        if (direction == "LONG" and b["l"] <= stop) or \
           (direction == "SHORT" and b["h"] >= stop):
            _flat(k, stop, "STOP" if abs(stop - entry) > 1e-9 else "BE")
            exit_i = k
            break
        for gi, q in enumerate(left):
            t = tgts[gi]
            if not q or t is None:
                continue
            if (direction == "LONG" and b["h"] >= t) or \
               (direction == "SHORT" and b["l"] <= t):
                out_legs.append((q, t, "T%d" % (gi + 1), k))
                left[gi] = 0
                if be_after is not None and gi == be_after:
                    if (direction == "LONG" and entry > stop) or \
                       (direction == "SHORT" and entry < stop):
                        stop = entry
        if not any(left):
            exit_i = k
            break
    if any(left):
        _flat(n - 1, bars[-1]["c"], "EOD")
        exit_i = n - 1

    pnl = 0.0
    gross_pts = 0.0
    for q, px, reason, k in out_legs:
        pts = (px - entry) * sign
        pnl += leg_pnl(q, pts, cost)
        gross_pts += q * pts
    runner_hit = any(r == "T2" for _, _, r, _ in out_legs)
    return {"pnl": round(pnl, 2), "gross_pts": round(gross_pts, 2),
            "legs": [(q, px, r) for q, px, r, _ in out_legs],
            "exit_i": exit_i, "runner_hit": runner_hit}


def sim_double(bars, cand, policy, cost):
    entry, stop = cand["entry"], cand["stop"]
    poc, edge = cand["poc"], cand["edge_opp"]
    direction = cand["dir"]
    sign = 1.0 if direction == "LONG" else -1.0
    runner_t = edge
    degenerate = False
    if (direction == "SHORT" and not edge < poc) or \
       (direction == "LONG" and not edge > poc):
        runner_t = poc           # degenerate VA geometry — runner banks at POC
        degenerate = True
    if policy == "SPLIT":
        legs = [[2, poc], [1, runner_t]]
        be_after = 0
    elif policy == "ALLPOC":
        legs = [[3, poc], ]
        be_after = None
    else:
        raise ValueError(policy)
    r = simulate(bars, cand["bar"], direction, entry, stop, legs, be_after, cost)
    r["degenerate_runner"] = degenerate
    r["dist_poc"] = round(abs(poc - entry), 2)
    r["dist_edge"] = round(abs(edge - entry), 2)
    r["risk"] = round(abs(stop - entry), 2)
    return r


# ────────────────────────── FB (frozen detector) ──────────────────────────

def detect_fb_candidates(bars, snaps):
    """FROZEN detection — byte-identical loop to replay_fb_exit_study.py."""
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


def sim_fb(bars, cand, policy, cost):
    setup = cand["setup"]
    entry = float(setup["entry_price"])
    stop = float(setup["stop"])
    t1, t2 = float(setup["t1"]), float(setup["t2"])
    if policy == "E0":
        legs = [[3, t1], ]
        be_after = None
    elif policy == "SPLIT":
        legs = [[2, t1], [1, t2]]
        be_after = 0
    else:
        raise ValueError(policy)
    return simulate(bars, cand["bar"], setup["direction"], entry, stop,
                    legs, be_after, cost)


# ────────────────────────── slot-run over a session ──────────────────────────

def run_session(bars, cands, sim_fn, policy, cost):
    """Single slot per session; candidates in trigger order; NO_ROOM/NO_POC skipped."""
    trades, skipped_slot, skipped_bad = [], 0, 0
    slot_free = 0
    for c in cands:
        if c.get("status", "OK") != "OK":
            skipped_bad += 1
            continue
        if c["bar"] < slot_free:
            skipped_slot += 1
            continue
        r = sim_fn(bars, c, policy, cost)
        slot_free = r["exit_i"] + 1
        trades.append((c, r))
    return trades, skipped_slot, skipped_bad


# ────────────────────────── cells / stats ──────────────────────────

def cell_stats(pnls):
    n = len(pnls)
    if n == 0:
        return {"n": 0}
    wins = [p for p in pnls if p > 0]
    tot = sum(pnls)
    top2 = sorted(pnls, reverse=True)[:2]
    top2_share = None
    if tot > 0:
        top2_share = round(100.0 * sum(top2) / tot, 1)
    return {"n": n, "usd": round(tot, 2),
            "win_pct": round(100.0 * len(wins) / n, 1),
            "median": round(statistics.median(pnls), 2),
            "top2_share_pct": top2_share,
            "low_n": n < 5}


# ────────────────────────── 25.08 anatomy ──────────────────────────

def legs_anatomy(bars, snaps):
    vas = bar_va(bars, snaps)
    switches = []          # (bar_idx, side)
    cur = None
    ambig = 0
    for t, b in enumerate(bars):
        va = vas[t]
        if not va:
            continue
        up = b["h"] >= va["vah"] - TOL
        dn = b["l"] <= va["val"] + TOL
        if up and dn:
            ambig += 1
            continue
        side = "UP" if up else ("DN" if dn else None)
        if side and side != cur:
            switches.append((t, side))
            cur = side
    visits = []
    for k, (t0, side) in enumerate(switches):
        t1 = switches[k + 1][0] - 1 if k + 1 < len(switches) else len(bars) - 1
        seg = bars[t0:t1 + 1]
        if side == "UP":
            ext = max(b["h"] for b in seg)
            ext_t = max(range(t0, t1 + 1), key=lambda x: bars[x]["h"])
        else:
            ext = min(b["l"] for b in seg)
            ext_t = min(range(t0, t1 + 1), key=lambda x: bars[x]["l"])
        visits.append({"side": side, "t0": t0, "t1": t1, "ext": round(ext, 2),
                       "ext_time": bars[ext_t]["ts"].strftime("%H:%M")})
    legs = []
    for k in range(len(visits) - 1):
        a, b_ = visits[k], visits[k + 1]
        legs.append({"leg": k + 1,
                     "from": "%s@%s(%s)" % (a["side"], a["ext"], a["ext_time"]),
                     "to": "%s@%s(%s)" % (b_["side"], b_["ext"], b_["ext_time"]),
                     "dir": "DOWN" if a["side"] == "UP" else "UP",
                     "size_pts": round(abs(a["ext"] - b_["ext"]), 2)})
    return visits, legs, ambig


# ────────────────────────── main ──────────────────────────

def main():
    global MAX_GAP, TOL
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/positive_map.json")
    ap.add_argument("--max-gap", type=int, default=MAX_GAP,
                    help="bars between the two touches (spec=12; other values "
                         "are LABELED SENSITIVITY runs, not the spec)")
    ap.add_argument("--tol", type=float, default=TOL,
                    help="edge-zone / extreme-match tolerance pts (spec=2.0)")
    args = ap.parse_args()
    MAX_GAP, TOL = args.max_gap, args.tol
    if MAX_GAP != 12 or TOL != 2.0:
        print("*** SENSITIVITY RUN (max_gap=%d tol=%.1f) — NOT the spec ***"
              % (MAX_GAP, TOL))

    conn = psycopg2.connect(DSN)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    days = load_days(cur, D0_BARS, D1)
    tpo_hist = load_tpo_history(cur, D0, D1)
    tpo_sess = load_tpo_sessions(cur)
    cur.execute("""
        SELECT id, mode, is_synthetic, firing_system, direction,
               (entry_ts AT TIME ZONE 'America/New_York') AS et,
               pattern_id_at_entry, day_type_at_entry, pnl_usd, outcome, state
        FROM v9_trades
        WHERE entry_ts IS NOT NULL
          AND (entry_ts AT TIME ZONE 'America/New_York')::date <= %s
        ORDER BY entry_ts
    """, (D1,))
    trade_rows = cur.fetchall()
    conn.close()

    # ---------- session prep ----------
    sessions = []
    not_judgeable = []
    excluded_bars = []
    for d in sorted(days):
        if str(d) < D0:
            continue
        if len(days[d]) < 20:
            excluded_bars.append((str(d), "bars=%d" % len(days[d])))
            continue
        cls = classify_day_full(days, tpo_sess, d)
        snaps = tpo_hist.get(d, [])
        usable = [s for s in snaps if s["vah"] is not None and s["val"] is not None]
        if not usable:
            not_judgeable.append((str(d), "no causal VA snapshots"))
            # still usable for the S2/S4 side join — keep classification
            sessions.append({"date": d, "bars": days[d], "snaps": [],
                             "cls": cls, "judgeable": False})
            continue
        sessions.append({"date": d, "bars": days[d], "snaps": snaps,
                         "cls": cls, "judgeable": True})

    side_map = {S["date"]: S["cls"] for S in sessions}
    n_judge = sum(1 for S in sessions if S["judgeable"])
    print("sessions=%d (judgeable=%d, NOT_JUDGEABLE=%d: %s; excluded bars<20: %s)"
          % (len(sessions), n_judge, len(not_judgeable), not_judgeable,
             excluded_bars))

    # ---------- detection ----------
    total_ambig = 0
    for S in sessions:
        if S["judgeable"]:
            S["dbl"], amb = detect_doubles(S["bars"], S["snaps"])
            S["fb"] = detect_fb_candidates(S["bars"], S["snaps"])
            total_ambig += amb
        else:
            S["dbl"], S["fb"] = [], []
    n_dbl = sum(len(S["dbl"]) for S in sessions)
    n_dbl_ok = sum(1 for S in sessions for c in S["dbl"] if c["status"] == "OK")
    n_fb = sum(len(S["fb"]) for S in sessions)
    print("double candidates=%d (OK=%d, NO_ROOM/NO_POC=%d, ambig-bars=%d) · "
          "fb candidates=%d" % (n_dbl, n_dbl_ok, n_dbl - n_dbl_ok, total_ambig,
                                n_fb))

    # ---------- REPRO CHECK (Rule 5): FB E0 on the frozen-48 universe ----------
    fb_par_total, fb_house_total, fb_n = 0.0, 0.0, 0
    for S in sessions:
        if str(S["date"]) < FB_D0:
            continue
        if daytype_bucket(S["cls"]["day_type"]) not in ("Variation", "Normal",
                                                        "Neutral"):
            continue
        trades, _, _ = run_session(S["bars"], S["fb"], sim_fb, "E0", "par")
        fb_par_total += sum(r["pnl"] for _, r in trades)
        fb_n += len(trades)
        trades_h, _, _ = run_session(S["bars"], S["fb"], sim_fb, "E0", "house")
        fb_house_total += sum(r["pnl"] for _, r in trades_h)
    print("\nREPRO CHECK — FB E0 on %s..%s (Var/Normal/Neutral): n=%d "
          "par=$%+.2f (published +118.20) house=$%+.2f (published -97.80)"
          % (FB_D0, D1, fb_n, fb_par_total, fb_house_total))

    # ---------- policies over all judgeable sessions ----------
    all_rows = {"SPLIT": [], "ALLPOC": []}
    fb_rows = {"E0": [], "SPLIT": []}
    skip_stats = collections.Counter()
    for S in sessions:
        if not S["judgeable"]:
            continue
        d = S["date"]
        cls = S["cls"]
        allowed = allowed_dirs(cls["strategy"], cls["dir_bias"])
        meta = {"date": str(d), "era": era_of(d),
                "day_type": cls["day_type"], "dt_bucket": daytype_bucket(cls["day_type"]),
                "side": side_bucket(cls["strategy"], cls["dir_bias"])}
        for pol in ("SPLIT", "ALLPOC"):
            trades, sk_slot, sk_bad = run_session(S["bars"], S["dbl"],
                                                  sim_double, pol, "house")
            if pol == "SPLIT":
                skip_stats["slot"] += sk_slot
                skip_stats["bad"] += sk_bad
            for c, r in trades:
                conform = ("UNMAPPED" if allowed is None else
                           ("CONFORM" if c["dir"] in allowed else "NONCONF"))
                row = dict(meta)
                row.update({"time": c["time"], "dir": c["dir"],
                            "side_pat": c["side"], "entry": c["entry"],
                            "stop": c["stop"], "poc": c["poc"],
                            "edge_opp": c["edge_opp"],
                            "conform": conform, "pnl": r["pnl"],
                            "gross_pts": r["gross_pts"],
                            "legs": r["legs"], "runner_hit": r["runner_hit"],
                            "degenerate_runner": r.get("degenerate_runner"),
                            "risk": r["risk"], "dist_poc": r["dist_poc"]})
                all_rows[pol].append(row)
        for pol in ("E0", "SPLIT"):
            trades, _, _ = run_session(S["bars"], S["fb"], sim_fb, pol, "house")
            for c, r in trades:
                drc = c["setup"]["direction"]
                conform = ("UNMAPPED" if allowed is None else
                           ("CONFORM" if drc in allowed else "NONCONF"))
                fb_rows[pol].append({
                    "date": str(d), "era": era_of(d),
                    "dt_bucket": daytype_bucket(cls["day_type"]),
                    "side": side_bucket(cls["strategy"], cls["dir_bias"]),
                    "time": c["time"], "dir": drc, "conform": conform,
                    "pnl": r["pnl"], "legs": r["legs"]})

    # ---------- print map ----------
    def agg(rows, keys):
        buckets = collections.defaultdict(list)
        for t in rows:
            buckets[tuple(t[k] for k in keys)].append(t["pnl"])
        return {k: cell_stats(v) for k, v in sorted(buckets.items())}

    for pol in ("SPLIT", "ALLPOC"):
        rows = all_rows[pol]
        st = cell_stats([t["pnl"] for t in rows])
        rh = sum(1 for t in rows if t["runner_hit"])
        print("\nDOUBLE %s (house costs): n=%d $%+.2f win=%.1f%% median=%+.2f "
              "top2=%s%% runner_hit=%d" % (pol, st["n"], st["usd"], st["win_pct"],
                                           st["median"], st.get("top2_share_pct"),
                                           rh))
        for keys, label in (( ("dt_bucket",), "day-type"),
                            (("side",), "S1-side"),
                            (("conform",), "conformity"),
                            (("era",), "era"),
                            (("dt_bucket", "conform"), "day-type × conform"),
                            (("era", "conform"), "era × conform"),
                            (("dt_bucket", "side", "conform"), "full cell")):
            print("  by %s:" % label)
            for k, v in agg(rows, keys).items():
                if v["n"] == 0:
                    continue
                print("    %-42s n=%-3d $%+9.2f win=%5.1f%% med=%+8.2f top2=%s%s"
                      % ("×".join(k), v["n"], v["usd"], v["win_pct"], v["median"],
                         v.get("top2_share_pct"), " LOW_N" if v["low_n"] else ""))

    for pol in ("E0", "SPLIT"):
        rows = fb_rows[pol]
        st = cell_stats([t["pnl"] for t in rows])
        print("\nFB %s all sessions (house): n=%d $%+.2f win=%.1f%% median=%+.2f"
              % (pol, st["n"], st["usd"], st["win_pct"], st["median"]))
        for k, v in agg(rows, ("dt_bucket", "conform")).items():
            print("    %-42s n=%-3d $%+9.2f win=%5.1f%% med=%+8.2f%s"
                  % ("×".join(k), v["n"], v["usd"], v["win_pct"], v["median"],
                     " LOW_N" if v["low_n"] else ""))

    # ---------- 25.08 anatomy ----------
    print("\n" + "=" * 70)
    print("ANATOMY 2026-08-25")
    d25 = dt.date(2026, 8, 25)
    S25 = next((S for S in sessions if S["date"] == d25), None)
    anatomy = {}
    if S25 and S25["judgeable"]:
        bars, snaps = S25["bars"], S25["snaps"]
        visits, legs, amb = legs_anatomy(bars, snaps)
        last_va = causal_va(snaps, bars[-1]["ts"])
        print("day H=%.2f L=%.2f · final causal VA: VAH=%.2f VAL=%.2f POC=%s"
              % (max(b["h"] for b in bars), min(b["l"] for b in bars),
                 last_va["vah"], last_va["val"], last_va["poc"]))
        print("EOD class: %s · side: %s · live v9_day_type_state 25.08: "
              "Variation / with_extension(DOWN)→with_extension"
              % (S25["cls"]["day_type"], S25["cls"]["side"]))
        print("edge visits=%d → legs=%d (Michael's anchor ≈8) · ambig bars=%d"
              % (len(visits), len(legs), amb))
        for lg in legs:
            print("  leg %d %-4s %s → %s  size=%.2f pts"
                  % (lg["leg"], lg["dir"], lg["from"], lg["to"], lg["size_pts"]))
        print("double candidates on 25.08 (status — task-1 spec sim):")
        rows25 = []
        for c in S25["dbl"]:
            base = ("  %s %s 2nd-touch@%s (1st@%s) entry=%.2f stop=%.2f "
                    "ext=%.2f poc=%s [%s]"
                    % (c["time"], c["dir"], c["ext_second"], c["t_first"],
                       c["entry"], c["stop"], c["extreme"], c["poc"], c["status"]))
            if c["status"] == "OK":
                r_h = sim_double(bars, c, "ALLPOC", "house")
                r_c = sim_double(bars, c, "ALLPOC", "comm_only")
                r_s = sim_double(bars, c, "SPLIT", "house")
                print(base + " → ALLPOC comm_only=$%+.2f house=$%+.2f "
                      "SPLIT house=$%+.2f legs=%s"
                      % (r_c["pnl"], r_h["pnl"], r_s["pnl"], r_h["legs"]))
                rows25.append({"cand": c, "allpoc_comm": r_c["pnl"],
                               "allpoc_house": r_h["pnl"],
                               "split_house": r_s["pnl"],
                               "legs": r_h["legs"]})
            else:
                print(base)
                rows25.append({"cand": c})
        anatomy = {"visits": visits, "legs": legs, "ambig": amb,
                   "final_va": last_va, "day_type": S25["cls"]["day_type"],
                   "side": S25["cls"]["side"], "cands": rows25}
        # what the slot-constrained day pays (task-1 P&L, both cost views)
        for cost in ("comm_only", "house"):
            for pol in ("ALLPOC", "SPLIT"):
                tr, sk, bad = run_session(bars, S25["dbl"], sim_double, pol, cost)
                tot = sum(r["pnl"] for _, r in tr)
                print("25.08 slot-run %s %s: n=%d $%+.2f (slot-skip %d, bad %d)"
                      % (pol, cost, len(tr), tot, sk, bad))
                anatomy["slot_%s_%s" % (pol, cost)] = {
                    "n": len(tr), "usd": round(tot, 2),
                    "trades": [{"time": c["time"], "dir": c["dir"],
                                "pnl": r["pnl"], "legs": r["legs"]}
                               for c, r in tr]}
    else:
        print("25.08 NOT JUDGEABLE — missing bars or VA")

    # ---------- S2/S4 conformity (v9_trades) ----------
    print("\n" + "=" * 70)
    print("S2/S4 × S1-side (v9_trades, EOD-reconstructed side)")
    tr_out = []
    skipped_tr = collections.Counter()
    for (tid, mode, synth, fsys, tdir, et, pat, dt_at, pnl, outcome, state) \
            in trade_rows:
        d = et.date()
        if pat == "SIM_TEST":
            skipped_tr["SIM_TEST"] += 1
            continue
        if pnl is None:
            skipped_tr["pnl_null"] += 1
            continue
        if tdir not in ("LONG", "SHORT"):
            skipped_tr["no_dir"] += 1
            continue
        cls = side_map.get(d)
        if cls is None:
            conform = "NO_SESSION"
        else:
            allowed = allowed_dirs(cls["strategy"], cls["dir_bias"])
            conform = ("UNMAPPED" if allowed is None else
                       ("CONFORM" if tdir in allowed else "NONCONF"))
        tr_out.append({"id": tid, "date": str(d), "era": era_of(d),
                       "mode": mode, "system": fsys, "dir": tdir,
                       "pattern": pat or "?",
                       "day_type_at_entry": dt_at,
                       "dt_bucket": daytype_bucket(cls["day_type"]) if cls else "?",
                       "side": side_bucket(cls["strategy"], cls["dir_bias"])
                       if cls else "?",
                       "conform": conform, "pnl": round(float(pnl), 2)})
    print("trades used=%d · skipped=%s" % (len(tr_out), dict(skipped_tr)))

    def tagg(rows, keys, min_n=0):
        buckets = collections.defaultdict(list)
        for t in rows:
            buckets[tuple(t[k] for k in keys)].append(t["pnl"])
        out = {}
        for k, v in sorted(buckets.items()):
            st = cell_stats(v)
            if st["n"] >= min_n:
                out["×".join(map(str, k))] = st
        return out

    s2s4_out = {}
    for label, keys in (("conform", ("conform",)),
                        ("mode×conform", ("mode", "conform")),
                        ("system×conform", ("system", "conform")),
                        ("era×conform", ("era", "conform")),
                        ("mode×era×conform", ("mode", "era", "conform")),
                        ("pattern×conform", ("pattern", "conform")),
                        ("system×pattern×conform", ("system", "pattern", "conform"))):
        s2s4_out[label] = tagg(tr_out, keys)
        print("  by %s:" % label)
        for k, v in s2s4_out[label].items():
            print("    %-48s n=%-4d $%+10.2f win=%5.1f%% med=%+8.2f%s"
                  % (k, v["n"], v["usd"], v["win_pct"], v["median"],
                     " LOW_N" if v["low_n"] else ""))

    # live-belief cross-check: day_type_at_entry vs EOD bucket
    mism = sum(1 for t in tr_out
               if t["day_type_at_entry"] and t["dt_bucket"] != "?"
               and daytype_bucket(t["day_type_at_entry"]) != t["dt_bucket"])
    have = sum(1 for t in tr_out if t["day_type_at_entry"])
    print("  day_type_at_entry vs EOD-bucket mismatches: %d/%d" % (mism, have))

    # ---------- JSON ----------
    out = {
        "meta": {"d0": D0, "d1": D1, "contracts": CONTRACTS,
                 "cost_house": {"slip_pts": SLIP, "comm_rt_usd": COMM_RT},
                 "detector": {"tol_pts": TOL, "max_gap_bars": MAX_GAP,
                              "stop_off": STOP_OFF, "stop_cap": STOP_CAP,
                              "min_trigger_bar": MIN_TRIG_BAR},
                 "sessions": len(sessions), "judgeable": n_judge,
                 "not_judgeable": not_judgeable,
                 "excluded_bars": excluded_bars,
                 "dbl_candidates": n_dbl, "dbl_ok": n_dbl_ok,
                 "ambig_bars": total_ambig,
                 "skip_stats": dict(skip_stats),
                 "repro_check": {"fb_e0_n": fb_n,
                                 "fb_e0_par": round(fb_par_total, 2),
                                 "fb_e0_house": round(fb_house_total, 2),
                                 "published_par": 118.20,
                                 "published_house": -97.80}},
        "sessions": [{"date": str(S["date"]), "era": era_of(S["date"]),
                      "day_type": S["cls"]["day_type"],
                      "side": S["cls"]["side"], "judgeable": S["judgeable"],
                      "n_dbl": len(S["dbl"]), "n_fb": len(S["fb"])}
                     for S in sessions],
        "anatomy_2508": anatomy,
        "dbl_trades": all_rows,
        "fb_trades": fb_rows,
        "s2s4": {"rows": tr_out, "aggregates": s2s4_out,
                 "skipped": dict(skipped_tr),
                 "daytype_at_entry_mismatch": [mism, have]},
    }
    with open(args.json, "w") as f:
        json.dump(out, f, indent=1, default=str, ensure_ascii=False)
    print("\nJSON → %s" % args.json)


if __name__ == "__main__":
    main()
