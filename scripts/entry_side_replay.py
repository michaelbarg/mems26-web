#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
entry_side_replay.py — E1/E2/E3 ENTRY-SIDE replays over every live-era session.

Michael (2026-08-22): "stop answering yes/no — replay everything and show tables
that say what would have worked better."

E1  ATR-relative pivot tolerance   k x ATR5m on the swing-pivot test, and a
                                   1-bar vs 2-bar right-side confirmation.
E2  Entry timing                   limit/stop AT THE STRUCTURAL LEVEL (filled on
                                   touch, tick-exact from the Sierra .scid) vs
                                   today's market-on-close-of-confirmation-bar.
E3  Live day-type adaptation       switch the OPEN trade's management policy when
                                   the causal day-type label changes mid-trade.

ENGINES ARE REUSED, NOT REBUILT
    scripts/oracle_study.py                       -> bars, ATR, ZigZag, triggers,
                                                      sim_trade / sim_ladder, costs
    backend/v9/systems/five_min/patterns/*        -> the LIVE pattern detectors
    backend/v9/systems/day_type/classifier_core   -> the LIVE 7-type classifier
    config/daytype_playbook.yaml                  -> the LIVE per-day-type mgmt style
    ~/SierraChart/Data/MESU26_FUT_CME.scid        -> tick-by-tick truth for E2

READ-ONLY on production.  Direct psycopg2 (never backend.v9.db.read).
Writes nothing but stdout + the JSON dump given by --json.

Usage:  python3 scripts/entry_side_replay.py --json /tmp/esr.json
        python3 scripts/entry_side_replay.py --only e2
"""

import argparse
import collections
import datetime as dt
import importlib.util as _ilu
import json
import os
import statistics
import struct
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ---- reuse the ORACLE_STUDY engine verbatim -------------------------------
_OS_PATH = os.path.join(ROOT, "scripts", "oracle_study.py")
_spec = _ilu.spec_from_file_location("oracle_study", _OS_PATH)
ORA = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(ORA)

DSN = os.environ.get("MEMS26_DSN", "postgresql://localhost/mems26")
D0, D1 = "2026-07-07", "2026-08-21"       # live era, extended to yesterday
WARM = "2026-06-25"
RTH0, RTH1 = dt.time(9, 30), dt.time(16, 0)
IB_BARS = 12
TICK = 0.25
CONTRACTS = 4
POINT_USD = 5.0
COMM_RT = 1.50
SLIP_LEVELS = (0, 1, 2)                   # ticks per side, as in week_replay.py
ET_UTC_OFFSET = dt.timedelta(hours=4)     # EDT during the whole live era

SCID = os.path.expanduser("~/SierraChart/Data/MESU26_FUT_CME.scid")
SCID_PRICE_DIV = 100.0                    # verified: 768750 -> 7687.50

# live detector window: _bar_buffer capped at 20, _det_buf = buffer[:-1]
LIVE_DET_WINDOW = 19
PKG5A_DAYTYPES = ("Neutral_Extreme", "Neutral_Center", "Normal", "Variation")
DEDUP_COOLDOWN = 30                       # bars, per KIND_DIR (five_min_system A2)

# S1 flag-set that was live (same list daily_extremes_playbook.py uses)
LIVE_S1_FLAGS = {
    "S1_NEW_CLASSIFIER": "1", "S1_ENGINE_NEW_CLASSIFIER": "1",
    "S1_OPEN_DRIVE_TREND": "1", "S1_COMMITTED_PROVISIONAL_V1": "1",
    "DELTA_FEATURES_V1": "0", "MULTIDAY_CONTEXT_V1": "0",
}


def money(pts, c=CONTRACTS):
    return pts * c * POINT_USD


def costs(c=CONTRACTS):
    return COMM_RT * c


def med(xs):
    return round(statistics.median(xs), 2) if xs else 0.0


# classify_replay emits "Normal_Variation"; every consumer (playbook, gates)
# keys on "Variation" — same remap as daytype_classify_routes.py:329.
_DT_NORM = {"Normal_Variation": "Variation"}


def norm_dt(x):
    return _DT_NORM.get(x, x)


# ============================================================ data
def load_bars(cur):
    ORA.D1 = D1
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
        days.setdefault(et.date(), []).append(
            dict(t=et, o=float(o), h=float(h), l=float(l), c=float(c), v=float(v or 0))
        )
    return days


def live_days(days):
    a = dt.date.fromisoformat(D0)
    b = dt.date.fromisoformat(D1)
    return [d for d in sorted(days) if a <= d <= b and len(days[d]) >= 30]


def load_live_trades(cur):
    cur.execute(
        """
        select id, pattern_id_at_entry, direction, mode,
               (entry_ts at time zone 'America/New_York'),
               (exit_ts   at time zone 'America/New_York'),
               entry_price, exit_price, stop, pnl_usd, pnl_r, exit_reason,
               day_type_at_entry
        from v9_trades
        where state='CLOSED' and mode='live' and entry_ts is not null
          and (entry_ts at time zone 'America/New_York')::date between %s and %s
        order by entry_ts
        """,
        (D0, D1),
    )
    out = []
    for (tid, pat, d, mode, ein, eout, ep, xp, st, pnl, pr, xr, dtype) in cur.fetchall():
        out.append(dict(id=tid, pat=pat or "-", dir=(1 if d == "LONG" else -1),
                        t_in=ein, t_out=eout,
                        entry=float(ep) if ep is not None else None,
                        exit=float(xp) if xp is not None else None,
                        stop=float(st) if st is not None else None,
                        pnl=float(pnl or 0), reason=xr or "-",
                        day=ein.date(), day_type=dtype))
    return out


def atr5(bars, i, period=14):
    """live _current_atr_5m: Wilder ATR-14 on the (<=20 bar) rolling buffer."""
    from backend.v9.shared.atr import atr_5min
    buf = bars[max(0, i - 19):i + 1]
    return atr_5min(buf, period)


# ============================================================ E1
def make_pivots(tol, lb_left, lb_right, side):
    """Swing-pivot finder with an ATR-relative tolerance.

    Baseline (tol=0, lb_left=lb_right=2) reduces EXACTLY to the live
    _swing_lows/_swing_highs in double_bt.py / head_shoulders.py:
        a neighbour disqualifies the pivot when neighbour <= pivot.
    With tol>0 a neighbour only disqualifies when it is MATERIALLY beyond:
        neighbour <= pivot - tol            (lows)
        neighbour >= pivot + tol            (highs)
    Adjacent near-equal bars can then both qualify, so pivots inside
    `lb_left` bars of each other are merged (the more extreme one wins).
    """
    def f(bars, lookback=None):
        n = len(bars)
        key = "l" if side == "low" else "h"
        raw = []
        for i in range(lb_left, n - lb_right):
            p = bars[i][key]
            ok = True
            for j in range(1, lb_left + 1):
                q = bars[i - j][key]
                if (q <= p - tol) if side == "low" else (q >= p + tol):
                    ok = False
                    break
            if ok:
                for j in range(1, lb_right + 1):
                    q = bars[i + j][key]
                    if (q <= p - tol) if side == "low" else (q >= p + tol):
                        ok = False
                        break
            if ok:
                raw.append((i, p))
        out = []
        for i, p in raw:
            if out and i - out[-1][0] <= lb_left:
                better = (p < out[-1][1]) if side == "low" else (p > out[-1][1])
                if better:
                    out[-1] = (i, p)
                continue
            out.append((i, p))
        return out
    return f


def e1_scan_session(bars, labels, k, right_bars, adam_fix=False,
                    window=LIVE_DET_WINDOW):
    """Bar-by-bar causal run of the LIVE Pkg-5a detector chain with patched pivots.

    Chain order is the live one (five_min_system.py:1755-1763):
        inverse_hns -> hns_top -> double_bottom_ee -> double_top_aa
    Day-type gate chart_patterns_allowed(dt,'5a') is applied with the CAUSAL label.
    A2 fire-dedup (30 bars per KIND_DIR) is replicated.
    """
    from backend.v9.systems.five_min.patterns import double_bt as DBT
    from backend.v9.systems.five_min.patterns import head_shoulders as HNS

    # ADAM-FIX arm: the Adam&Adam peak-width test needs peaks NARROWER than 2
    # bars, but it shares get_trough_tolerance() with the Eve trough test, which
    # needs troughs WIDER than 3 bars.  With S2_ATR_RELATIVE=true (live, .env:20)
    # that tolerance is 0.75xATR (4.15pt on 2026-08-21) -> measured median peak
    # width 11 bars, only 7/74 peaks <= 2 -> DOUBLE_TOP_AA can never fire.
    # adam_fix keeps Eve ATR-relative and puts Adam back on the 2-tick tolerance.
    if not hasattr(DBT, "_ORIG_PEAK"):
        DBT._ORIG_PEAK = DBT._peak_width_bars
    DBT._peak_width_bars = ((lambda b, i2, p, atr_5m=None: DBT._ORIG_PEAK(b, i2, p, None))
                            if adam_fix else DBT._ORIG_PEAK)

    fires, dedup = [], {}
    n = len(bars)
    for i in range(12, n):
        lab = norm_dt(labels[i])
        # live gate: S2_CHART_ALL_DAYTYPES=1 in .env:66 -> any known type but Nontrend
        if not lab or lab in ("UNKNOWN", "Nontrend"):
            continue
        a = atr5(bars, i)
        tol = (k * a) if (a and k) else 0.0
        lo_f = make_pivots(tol, 2, right_bars, "low")
        hi_f = make_pivots(tol, 2, right_bars, "high")
        DBT._swing_lows, DBT._swing_highs = lo_f, hi_f
        HNS._swing_lows, HNS._swing_highs = lo_f, hi_f
        # live detection buffer: the last COMPLETED bars only
        buf = bars[max(0, i - window + 1):i + 1]
        d = c = None
        info = {}
        for fn, kw in ((HNS.detect_inverse_hns, {}), (HNS.detect_hns_top, {}),
                       (DBT.detect_double_bottom_ee, {"atr_5m": a}),
                       (DBT.detect_double_top_aa, {"atr_5m": a})):
            d, c, info = fn(buf, **kw)
            if d:
                break
        if not d:
            continue
        kind = info.get("kind", "?")
        key = f"{kind}_{d}"
        if i - dedup.get(key, -999) < DEDUP_COOLDOWN:
            continue
        dedup[key] = i
        fires.append(dict(i=i, dir=(1 if d == "LONG" else -1), kind=kind,
                          conf=round(float(c), 2), t=bars[i]["t"]))
    return fires


def take_sequential(bars, cands, thr, slip):
    """One position at a time, chronological, MEMS-style ladder management."""
    ORA.SLIP_TICKS = slip
    out, busy = [], -1
    for cd in cands:
        if cd["i"] <= busy:
            continue
        r = ORA.sim_ladder(bars, cd["i"], cd["dir"], thr, CONTRACTS)
        if not r:
            continue
        r["kind"] = cd["kind"]
        out.append(r)
        busy = r["exit_i"]
    ORA.SLIP_TICKS = 1
    return out


# ============================================================ E2 · tick data
class Scid:
    HDR, REC = 56, 40
    EPOCH = dt.datetime(1899, 12, 30)

    def __init__(self, path):
        self.f = open(path, "rb")
        hdr = self.f.read(self.HDR)
        assert hdr[:4] == b"SCID", "not a .scid file"
        self.rec = struct.unpack("<I", hdr[8:12])[0]
        self.n = (os.path.getsize(path) - self.HDR) // self.rec

    def ts(self, i):
        self.f.seek(self.HDR + i * self.rec)
        return struct.unpack("<q", self.f.read(8))[0]      # us since 1899-12-30

    def _us(self, t):
        return int((t - self.EPOCH).total_seconds() * 1_000_000)

    def find(self, t):
        lo, hi, tgt = 0, self.n, self._us(t)
        while lo < hi:
            m = (lo + hi) // 2
            if self.ts(m) < tgt:
                lo = m + 1
            else:
                hi = m
        return lo

    def slice(self, t0, t1):
        """[(datetime_utc, last, bidvol, askvol)] for [t0,t1) UTC."""
        a, b = self.find(t0), self.find(t1)
        if b <= a:
            return []
        self.f.seek(self.HDR + a * self.rec)
        raw = self.f.read((b - a) * self.rec)
        out = []
        for j in range(b - a):
            v = struct.unpack_from("<q4f4I", raw, j * self.rec)
            out.append((self.EPOCH + dt.timedelta(microseconds=v[0]),
                        v[4] / SCID_PRICE_DIV, v[7], v[8]))
        return out


def bar_ticks(sc, bar_t_et):
    """Ticks inside one 5-min bar, given the bar's ET OPEN time."""
    u0 = bar_t_et + ET_UTC_OFFSET
    return sc.slice(u0, u0 + dt.timedelta(minutes=5))


# ============================================================ E2 · replay
def e2_session(bars, sc, thr, slip):
    """BREAK-family only: the one family where 'level' is unambiguous.

    active long level  = last CONFIRMED swing-high pivot + 1 tick   (ORA zigzag)
    active short level = last CONFIRMED swing-low  pivot - 1 tick
    Each level is consumed by its first touch (mirrors ORA's used_break set).

    (b) CLOSE  = today: market at the close of the first bar that CLOSES through
    (a) TOUCH  = limit/stop at the level, tick-exact fill on first trade at/through
    (a2) TOUCH+FLOW = TOUCH, but only if the 60s aggressor delta after the touch
                      agrees with the trade direction (buyers/sellers stepping in)
    """
    piv = ORA.zigzag(bars, thr)
    n = len(bars)
    used = set()
    rows = []
    for i in range(3, n):
        conf = [p for p in piv if p["confirm_i"] <= i - 1 and p["i"] < i]
        for side, kind in ((1, "H"), (-1, "L")):
            p = next((q for q in reversed(conf) if q["kind"] == kind), None)
            if not p or (kind, p["i"]) in used:
                continue
            lvl = p["price"] + side * TICK
            b = bars[i]
            touched = (b["h"] >= lvl) if side > 0 else (b["l"] <= lvl)
            if not touched:
                continue
            used.add((kind, p["i"]))
            closed = (b["c"] > lvl) if side > 0 else (b["c"] < lvl)
            tk = bar_ticks(sc, b["t"])
            t_touch = None
            for (tt, px, bv, av) in tk:
                if (px >= lvl) if side > 0 else (px <= lvl):
                    t_touch = tt
                    break
            flow = 0
            if t_touch:
                cut = t_touch + dt.timedelta(seconds=60)
                for (tt, px, bv, av) in tk:
                    if t_touch <= tt <= cut:
                        flow += (av - bv)
            rows.append(dict(i=i, dir=side, lvl=round(lvl, 2),
                             closed_through=closed, close=b["c"],
                             t_touch=t_touch, flow=flow, ticks=len(tk)))
    return rows


def e2_sim(bars, sc, row, thr, slip, entry_at_level):
    """Simulate one E2 entry with ORA ladder mechanics.

    entry_at_level=True  -> fill at the level (touch), then the REST of the entry
                            bar is checked tick-by-tick for an immediate stop-out
                            (the honest cost of entering intrabar).
    entry_at_level=False -> fill at the entry bar's close (today's mechanism).
    """
    i, d = row["i"], row["dir"]
    ORA.SLIP_TICKS = slip
    if entry_at_level:
        shim = list(bars)
        shim[i] = dict(bars[i])
        shim[i]["c"] = row["lvl"]
        base = ORA.sim_trade(shim, i, d, thr, CONTRACTS)
        if not base:
            ORA.SLIP_TICKS = 1
            return None
        stop = base["stop"]
        if row["t_touch"]:
            for (tt, px, bv, av) in bar_ticks(sc, bars[i]["t"]):
                if tt < row["t_touch"]:
                    continue
                if (d > 0 and px <= stop) or (d < 0 and px >= stop):
                    entry = row["lvl"] + d * slip * TICK
                    pts = d * (stop - d * slip * TICK - entry)
                    ORA.SLIP_TICKS = 1
                    return dict(usd=round(money(pts) - costs(), 2), pts=round(pts, 2),
                                reason="STOP_SAME_BAR", exit_i=i, entry=entry, dir=d, i=i)
        r = ORA.sim_ladder(shim, i, d, thr, CONTRACTS)
    else:
        r = ORA.sim_ladder(bars, i, d, thr, CONTRACTS)
    ORA.SLIP_TICKS = 1
    return r


# ============================================================ E3
def value_area(bars, pct=0.70):
    hist = collections.Counter()
    for b in bars:
        lo, hi = b["l"], b["h"]
        m = max(1, int(round((hi - lo) / 0.25)) + 1)
        share = (b["v"] or 1.0) / m
        for k in range(m):
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


def causal_labels(days, d, bars):
    """The LIVE 7-type classifier replayed BAR BY BAR (is_eod only on the last bar).

    v9_day_type_state only holds 08-20..08-22, so the intraday label timeline for
    the live era does not exist in the DB — it is reconstructed here from the
    repo's own classifier (same flags the engine ran with).
    """
    for k, v in LIVE_S1_FLAGS.items():
        os.environ[k] = v
    from backend.v9.systems.day_type.classifier_core import classify_session

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
    ib = bars[:IB_BARS]
    ibh, ibl = max(x["h"] for x in ib), min(x["l"] for x in ib)
    _, _, poc_ib = value_area(ib)
    out = [None] * len(bars)
    for i in range(IB_BARS, len(bars)):
        seg = bars[:i + 1]
        _, _, poc_now = value_area(seg)
        try:
            r = classify_session(
                bars=[dict(o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"]) for b in seg],
                ib_high=ibh, ib_low=ibl, open_price=bars[0]["o"],
                ib_width_hist=ib_hist, profile_shape=None, vol_ratio=None,
                prior_vah=pvah, prior_val=pval, pdh=pdh, pdl=pdl,
                poc_now=poc_now, poc_at_ib=poc_ib, is_eod=(i == len(bars) - 1),
            )
            out[i] = r.get("day_type")
        except Exception:
            out[i] = None
    return out


def load_style():
    import yaml
    with open(os.path.join(ROOT, "config", "daytype_playbook.yaml")) as f:
        return (yaml.safe_load(f) or {}).get("daytype_style", {})


def e3_policy(style, lab):
    """The two management dimensions the playbook actually defines per day-type."""
    s = style.get(norm_dt(lab)) or {}
    return dict(runner=s.get("runner", "none"),
                target=s.get("target"),
                action=s.get("action"),
                contracts=s.get("contracts"))


def e3_run(bars, i_in, d, entry, stop, thr, atr, ibh, ibl, slip, pol_seq):
    """Bar-by-bar exit under a per-bar management POLICY (may change mid-trade).

    pol_seq[k] = the policy dict in force at bar k.  Dimensions modelled — the
    only two the playbook states unambiguously per day-type:

      runner 'none'             -> flatten the remainder at that bar's close
                                   (Neutral_Center / Nontrend / Nonconviction)
      runner 'trail'            -> exit on the first close giving back `thr`
                                   from the running extreme (ORA rule)
      runner 'trail_chandelier' -> exit on the first close giving back 3 x ATR14
                                   from the running extreme (Trend_Normal)
      target 'location'         -> additionally cap at the opposite IB edge
      target 'movement'         -> no location cap (hold to close)

    Stop is always the trade's real stop, checked before anything else.
    """
    ext = entry
    for k in range(i_in + 1, len(bars)):
        b = bars[k]
        p = pol_seq[k] if k < len(pol_seq) and pol_seq[k] else pol_seq[i_in]
        if (d > 0 and b["l"] <= stop) or (d < 0 and b["h"] >= stop):
            px = stop - d * slip * TICK
            return round(money(d * (px - entry)) - costs(), 2), "STOP", k
        if p.get("action") == "SKIP" or p.get("contracts") in (0,) or p.get("runner") == "none":
            px = b["c"] - d * slip * TICK
            return round(money(d * (px - entry)) - costs(), 2), "FLAT_POLICY", k
        ext = max(ext, b["h"]) if d > 0 else min(ext, b["l"])
        if p.get("target") == "location" and ibh is not None:
            tgt = ibl if d < 0 else ibh
            opp = (ibl - (ibh - ibl)) if d < 0 else (ibh + (ibh - ibl))
            lvl = opp
            if (d > 0 and b["h"] >= lvl) or (d < 0 and b["l"] <= lvl):
                px = lvl - d * slip * TICK
                return round(money(d * (px - entry)) - costs(), 2), "LOC_TARGET", k
        give = thr if p.get("runner") != "trail_chandelier" else 3.0 * (atr or thr)
        if (d > 0 and b["c"] <= ext - give) or (d < 0 and b["c"] >= ext + give):
            px = b["c"] - d * slip * TICK
            return round(money(d * (px - entry)) - costs(), 2), "TRAIL", k
    px = bars[-1]["c"] - d * slip * TICK
    return round(money(d * (px - entry)) - costs(), 2), "EOD", len(bars) - 1


DTS_ET_FROM_UTC_H = 4   # v9_day_type_state.ts is naive UTC — see below


def load_live_label_timeline(cur, days):
    """The REAL intraday label timeline the engine wrote (v9_day_type_state).

    TWO documented defects in this table, both verified before use (Rule 2):

    1) Coverage is 2026-08-20..2026-08-22 ONLY — the table holds no live-era
       history, which is why the causal replay above exists.
    2) `ts` is `timestamp WITHOUT time zone` holding a NAIVE **UTC** instant —
       unlike v9_trades.entry_ts / v9_bars_5min_woodies.ts, which are timestamptz.
       Applying `AT TIME ZONE 'America/New_York'` to it (the usual idiom in this
       repo) therefore SHIFTS IT +7h instead of converting it.  Anchors that pin
       the real meaning, from docs/reports/EOD_DIAGNOSIS_2026-08-21.md §1.2:
           naive 2026-08-21 13:35:04 UNKNOWN   == report "16:35 IL"     (ET 09:35)
           naive 2026-08-21 13:54:54 UNKNOWN   == report "16:54:54 IL"  (ET 09:54)
           naive 2026-08-21 15:27:54 Variation == report "18:27:54 IL"  (ET 11:27)
       ET = naive - 4h (EDT).  Read raw, never via AT TIME ZONE.
    """
    cur.execute(
        "select ts, day_type from v9_day_type_state where ts >= %s order by ts", (D0,))
    per = collections.defaultdict(list)
    for t, dtp in cur.fetchall():
        if getattr(t, "tzinfo", None) is not None:
            t = t.replace(tzinfo=None)
        t = t - dt.timedelta(hours=DTS_ET_FROM_UTC_H)
        per[t.date()].append((t, dtp))
    out = {}
    for d, rows in per.items():
        if d not in days:
            continue
        bars = days[d]
        seq = [None] * len(bars)
        cur_lab = None
        j = 0
        for i, b in enumerate(bars):
            end = b["t"] + dt.timedelta(minutes=5)
            while j < len(rows) and rows[j][0] < end:
                cur_lab = rows[j][1]
                j += 1
            seq[i] = cur_lab
        out[d] = seq
    return out


def bar_index(bars, t):
    for i, b in enumerate(bars):
        if b["t"] <= t < b["t"] + dt.timedelta(minutes=5):
            return i
    return None


# ============================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/tmp/esr.json")
    ap.add_argument("--only", default="all")
    a = ap.parse_args()

    cn = psycopg2.connect(DSN)
    cn.set_session(readonly=True)
    cur = cn.cursor()
    days = load_bars(cur)
    ds = live_days(days)
    trades = load_live_trades(cur)
    print(f"[data] sessions={len(ds)}  {ds[0]}..{ds[-1]}  live trades={len(trades)}")

    thr = {d: ORA.thr_for(days, d) for d in ds}
    labs = {}
    for d in ds:
        labs[d] = causal_labels(days, d, days[d])
    print("[labels] causal day-type timeline built for %d sessions" % len(labs))

    res = {"sessions": [str(d) for d in ds]}
    tl = []
    for d in ds:
        seq = [norm_dt(x) for x in labs[d] if x]
        tr = sum(1 for a2, b2 in zip(seq, seq[1:]) if a2 != b2)
        tl.append(dict(day=str(d), transitions=tr, labels=sorted(set(seq)),
                       first=(seq[0] if seq else None), last=(seq[-1] if seq else None)))
    res["labels"] = tl
    print("[labels] sessions with >=1 causal transition: %d/%d"
          % (sum(1 for x in tl if x["transitions"]), len(tl)))

    # ---------------- E1
    if a.only in ("all", "e1"):
        arms = ([(0.0, 2, 0), (0.0, 2, 1)]
                + [(k, r, ad) for k in (0.10, 0.15, 0.25) for r in (1, 2) for ad in (0, 1)])
        e1 = {}
        fire_cache = {}
        for (k, r, ad) in arms:
            per = {}
            for d in ds:
                fire_cache[(d, k, r, ad)] = e1_scan_session(days[d], labs[d], k, r,
                                                            adam_fix=bool(ad))
            for slip in SLIP_LEVELS:
                tot, nt, rows = 0.0, 0, []
                for d in ds:
                    tr = take_sequential(days[d], fire_cache[(d, k, r, ad)], thr[d], slip)
                    s = round(sum(x["usd"] for x in tr), 2)
                    tot += s
                    nt += len(tr)
                    rows.append(dict(day=str(d), usd=s, n=len(tr),
                                     trades=[dict(i=x["i"], kind=x["kind"], dir=x["dir"],
                                                  usd=x["usd"], reason=x["reason"]) for x in tr]))
                per[slip] = dict(total=round(tot, 2), n=nt, days=rows)
            e1[f"k{k}_r{r}_a{ad}"] = dict(
                fires=sum(len(fire_cache[(d, k, r, ad)]) for d in ds),
                fire_list=[dict(day=str(d), i=x["i"], kind=x["kind"], dir=x["dir"],
                                conf=x["conf"])
                           for d in ds for x in fire_cache[(d, k, r, ad)]],
                by_slip=per)
        res["e1"] = e1
        for key, v in e1.items():
            print(f"[E1] {key:14s} fires={v['fires']:3d} "
                  + " ".join(f"s{s}=${v['by_slip'][s]['total']:>9.2f}/n{v['by_slip'][s]['n']}"
                             for s in SLIP_LEVELS))

    # ---------------- E2
    if a.only in ("all", "e2"):
        sc = Scid(SCID)
        print(f"[E2] scid records={sc.n:,}")
        e2 = {"days": []}
        for d in ds:
            bars = days[d]
            rows = e2_session(bars, sc, thr[d], 1)
            e2["days"].append(dict(day=str(d), n_levels=len(rows),
                                   rows=[dict(i=x["i"], dir=x["dir"], lvl=x["lvl"],
                                              closed=x["closed_through"], close=x["close"],
                                              flow=x["flow"], ticks=x["ticks"],
                                              t_touch=(x["t_touch"].isoformat()
                                                       if x["t_touch"] else None))
                                         for x in rows]))
            print(f"  {d} levels={len(rows)} closed_through="
                  f"{sum(1 for x in rows if x['closed_through'])}")
        # mechanisms
        mech = {}
        for slip in SLIP_LEVELS:
            m = {"CLOSE": [], "TOUCH": [], "TOUCH_FLOW": [], "TOUCH_CONFIRMED": []}
            for d in ds:
                bars = days[d]
                rows = e2_session(bars, sc, thr[d], slip)
                for name in m:
                    busy = -1
                    for row in rows:
                        if row["i"] <= busy:
                            continue
                        if name in ("CLOSE", "TOUCH_CONFIRMED") and not row["closed_through"]:
                            continue
                        if name == "TOUCH_FLOW" and row["dir"] * row["flow"] <= 0:
                            continue
                        r = e2_sim(bars, sc, row, thr[d], slip,
                                   entry_at_level=(name != "CLOSE"))
                        if not r:
                            continue
                        busy = r.get("exit_i", row["i"])
                        m[name].append(dict(day=str(d), i=row["i"], dir=row["dir"],
                                            lvl=row["lvl"], close=row["close"],
                                            closed=row["closed_through"], flow=row["flow"],
                                            usd=r["usd"], reason=r["reason"]))
            mech[slip] = m
            for name, xs in m.items():
                print(f"[E2] slip{slip} {name:11s} n={len(xs):3d} "
                      f"${sum(x['usd'] for x in xs):>9.2f}")
        e2["mech"] = mech
        res["e2"] = e2

    # ---------------- E3
    if a.only in ("all", "e3"):
        style = load_style()
        live_tl = load_live_label_timeline(cur, days)
        for src, LB in (("causal", labs), ("db_live", live_tl)):
            e3 = []
            for t in trades:
                d = t["day"]
                if d not in LB or d not in days or t["entry"] is None or t["t_out"] is None:
                    continue
                bars = days[d]
                i_in = bar_index(bars, t["t_in"])
                i_out = bar_index(bars, t["t_out"])
                if i_in is None:
                    continue
                if i_out is None:
                    i_out = len(bars) - 1
                lseq = LB[d]
                seq = [(i, norm_dt(lseq[i])) for i in range(i_in, min(i_out, len(bars) - 1) + 1)
                       if i < len(lseq) and lseq[i]]
                if not seq:
                    continue
                l0 = seq[0][1]
                chg = next(((i, L) for i, L in seq if L != l0), None)
                if not chg:
                    continue
                i_sw, l1 = chg
                p0, p1 = e3_policy(style, l0), e3_policy(style, l1)
                stop = t["stop"] if t["stop"] is not None else (
                    min(b["l"] for b in bars[max(0, i_in - 2):i_in + 1]) - TICK if t["dir"] > 0
                    else max(b["h"] for b in bars[max(0, i_in - 2):i_in + 1]) + TICK)
                ib = bars[:IB_BARS]
                ibh, ibl = max(x["h"] for x in ib), min(x["l"] for x in ib)
                atr = atr5(bars, i_in)
                pol_base = [p0] * len(bars)
                pol_sw = [(p0 if i < i_sw else e3_policy(style, norm_dt(
                    next((L for j, L in reversed(seq) if j <= i), l1))))
                    for i in range(len(bars))]
                row = dict(src=src, id=t["id"], day=str(d), pat=t["pat"], dir=t["dir"],
                           lab0=l0, lab1=l1, i_in=i_in, i_sw=i_sw, i_out=i_out,
                           booked=t["pnl"], reason=t["reason"], p0=p0, p1=p1,
                           differs=(p0 != p1))
                for slip in SLIP_LEVELS:
                    b_, br_, _ = e3_run(bars, i_in, t["dir"], t["entry"], stop, thr[d],
                                        atr, ibh, ibl, slip, pol_base)
                    s_, sr_, _ = e3_run(bars, i_in, t["dir"], t["entry"], stop, thr[d],
                                        atr, ibh, ibl, slip, pol_sw)
                    row[f"base_s{slip}"] = b_
                    row[f"basereason_s{slip}"] = br_
                    row[f"sw_s{slip}"] = s_
                    row[f"swreason_s{slip}"] = sr_
                e3.append(row)
            res["e3_" + src] = e3
            for slip in SLIP_LEVELS:
                act = [r for r in e3 if r["differs"]]
                print(f"[E3:{src}] slip{slip} label-changed={len(e3)} policy-differs={len(act)} "
                      f"delta=${round(sum(r[f'sw_s{slip}'] - r[f'base_s{slip}'] for r in act), 2)}")
        res["e3"] = res.get("e3_causal", [])

    # ---------------- COMBINED  (E1 + E2 + E3 on one candidate stream)
    if a.only in ("all", "comb"):
        style = load_style()
        sc = Scid(SCID)
        comb = {}
        specs = {
            "base_trail":     (0.0, 2, 0, "CLOSE", False, "trail"),
            "E1_trail":       (0.25, 1, 1, "CLOSE", False, "trail"),
            "E2_trail":       (0.0, 2, 0, "TOUCH_FLOW", False, "trail"),
            "E3_trail":       (0.0, 2, 0, "CLOSE", True, "trail"),
            "E1+E2_trail":    (0.25, 1, 1, "TOUCH_FLOW", False, "trail"),
            "ALL_trail":      (0.25, 1, 1, "TOUCH_FLOW", True, "trail"),
            "base_ladder":    (0.0, 2, 0, "CLOSE", False, "ladder"),
            "E1_ladder":      (0.25, 1, 1, "CLOSE", False, "ladder"),
            "E2_ladder":      (0.0, 2, 0, "TOUCH_FLOW", False, "ladder"),
            "E1+E2_ladder":   (0.25, 1, 1, "TOUCH_FLOW", False, "ladder"),
        }
        for tag, (kk, rr, aa, mech, adapt, mgmt) in specs.items():
            per_slip = {}
            for slip in SLIP_LEVELS:
                perday, n_tr = [], 0
                for d in ds:
                    bars = days[d]
                    ib = bars[:IB_BARS]
                    ibh, ibl = max(x["h"] for x in ib), min(x["l"] for x in ib)
                    pol = []
                    entry_lab = None
                    for i in range(len(bars)):
                        L = norm_dt(labs[d][i]) if labs[d][i] else None
                        pol.append(e3_policy(style, L) if L else None)
                    cands = []
                    for f in e1_scan_session(bars, labs[d], kk, rr, adam_fix=bool(aa)):
                        cands.append(dict(i=f["i"], dir=f["dir"], kind=f["kind"],
                                          lvl=None, src="E1"))
                    for row in e2_session(bars, sc, thr[d], slip):
                        if mech == "CLOSE" and not row["closed_through"]:
                            continue
                        if mech == "TOUCH_FLOW" and row["dir"] * row["flow"] <= 0:
                            continue
                        cands.append(dict(i=row["i"], dir=row["dir"], kind="BREAK",
                                          lvl=(None if mech == "CLOSE" else row["lvl"]),
                                          src="E2"))
                    cands.sort(key=lambda x: (x["i"], x["src"]))
                    busy, tot = -1, 0.0
                    for cd in cands:
                        i = cd["i"]
                        if i <= busy:
                            continue
                        base = ORA.sim_trade(bars, i, cd["dir"], thr[d], CONTRACTS)
                        if not base:
                            continue
                        entry = (cd["lvl"] + cd["dir"] * slip * TICK) if cd["lvl"] \
                            else (bars[i]["c"] + cd["dir"] * slip * TICK)
                        if mgmt == "ladder":
                            shim = list(bars)
                            if cd["lvl"]:
                                shim[i] = dict(bars[i]); shim[i]["c"] = cd["lvl"]
                            ORA.SLIP_TICKS = slip
                            lr = ORA.sim_ladder(shim, i, cd["dir"], thr[d], CONTRACTS)
                            ORA.SLIP_TICKS = 1
                            if not lr:
                                continue
                            usd, xi = lr["usd"], lr["exit_i"]
                        else:
                            p_in = pol[i] or e3_policy(style, "Normal")
                            seq = [(p_in if (not adapt or j <= i) else (pol[j] or p_in))
                                   for j in range(len(bars))]
                            usd, why, xi = e3_run(bars, i, cd["dir"], entry, base["stop"],
                                                  thr[d], atr5(bars, i), ibh, ibl, slip, seq)
                        tot += usd
                        n_tr += 1
                        busy = xi
                    perday.append(dict(day=str(d), usd=round(tot, 2)))
                per_slip[slip] = dict(total=round(sum(x["usd"] for x in perday), 2),
                                      n=n_tr, days=perday)
            comb[tag] = per_slip
            print(f"[COMB] {tag:16s} " + " ".join(
                f"s{s}=${per_slip[s]['total']:>9.2f}/n{per_slip[s]['n']}" for s in SLIP_LEVELS))
        res["comb"] = comb

    with open(a.json, "w") as f:
        json.dump(res, f, default=str)
    print("[out]", a.json)


if __name__ == "__main__":
    main()
