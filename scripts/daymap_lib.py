#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daymap_lib.py — pure helpers for DAYMAP («פירוק-יום», version base-20.10).

Read-only on the databases and on every file it touches. Used by scripts/day_dissect.py,
scripts/daymap_aggregate.py and scripts/daymap_pages.py.

Conventions
  * Bars are dicts {ts (epoch UTC, bar START), il 'HH:MM', et 'HH:MM', em (ET minute of day), d (ET date iso),
    o, h, l, c, v} — the same keys review_lib / oracle_engine expect (h, l, c, o).
  * Session logic runs in ET (America/New_York); display in Israel time (Asia/Jerusalem).
    RTH = bar starts 09:30–15:55 ET. Phases (ET): 0 <09:30 · A 09:30–10:00 · B 10:00–10:30 ·
    C 10:30–14:00 · D 14:00–16:15 (manage-only from 14:00, entries cutoff 15:00, EOD flat 15:50).
  * An event derived from a bar CLOSE is stamped with the time the close was known (bar start + 5 min).
  * Simulations: 1 contract, stop-first when one bar touches both stop and target, EOD flat at the close of the
    15:45 ET bar (= 15:50 ET), no costs.

The reference (rule-based Dalton) functions session_profile / ref_opening / ref_daytype are COPIED from
scripts/eod_journal.py (itself copied from harness_out/t586/hist/opening_type_30d.py — the super-agent's reading
of Dalton pp. 19–29 / 63–74; thresholds are not Michael's) and adapted to take bar dicts as arguments,
because eod_journal executes at import time.
"""
import os, sys, re, io, json, math, contextlib, subprocess, collections, datetime as dt
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ET, IL, UTC = ZoneInfo("America/New_York"), ZoneInfo("Asia/Jerusalem"), dt.timezone.utc
TICK, USD_PT = 0.25, 5.0
VERSION_DEFAULT, VERSION_HEB = "base-20.10", "בסיס-20.10"
BACKEND_LOG = "/tmp/backend.err.log"
EXPORT_DIR = os.path.expanduser("~/SierraChart_Data/v9_export")
OPEN_MIN, CLOSE_MIN = 570, 960            # 09:30 / 16:00 ET in minutes of day
LAST_RTH_BAR_MIN, EOD_FLAT_BAR_MIN = 955, 945   # 15:55 bar start / 15:45 bar (its close = 15:50 flat)
ENTRY_CUTOFF_MIN, MANAGE_ONLY_MIN = 900, 840    # 15:00 / 14:00 ET
SESSION_END_MIN = 975                     # 16:15 ET — events after this belong to the next session's phase 0
# checkpoint label (IL at the normal 7 h offset) → minutes after the 09:30 ET open (= RTH bars so far / 5)
CHECKPOINTS = [("17:30", 60), ("18:30", 120), ("20:00", 210), ("21:00", 270), ("23:00", 390)]
PHASES = ["0", "A", "B", "C", "D"]
PHASE_HEB = {"0": "לפני הפתיחה", "A": "פתיחה 16:30–17:00", "B": "בניית IB 17:00–17:30", "C": "התפתחות 17:30–21:00", "D": "ניהול 21:00–23:00"}

# ── review_lib / oracle_engine by import (their import chdir()s, loads .env into os.environ and prints a line —
#    neutralised here: stdout swallowed, environment and cwd restored). Local fallbacks if the import fails. ──
_rl = _oe = None
try:
    _env, _cwd = dict(os.environ), os.getcwd()
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import review_lib as _rl          # noqa: E402
        import oracle_engine as _oe       # noqa: E402
    os.environ.clear(); os.environ.update(_env); os.chdir(_cwd)
except Exception:                          # pragma: no cover — fallbacks below
    _rl = _oe = None
    try:
        os.environ.clear(); os.environ.update(_env); os.chdir(_cwd)
    except Exception:
        pass
LIB_SRC = "review_lib" if _rl else "local-fallback"


def compute_atr(bars, idx, period=14):
    """oracle_engine.compute_atr (causal ATR at idx over bars[0..idx]); local copy if the import failed."""
    if _oe is not None:
        return _oe.compute_atr(bars, idx, period)
    if idx < period:
        return None
    trs = [max(bars[k]['h'] - bars[k]['l'], abs(bars[k]['h'] - bars[k - 1]['c']), abs(bars[k]['l'] - bars[k - 1]['c']))
           for k in range(idx - period + 1, idx + 1)]
    return sum(trs) / len(trs)


def _zigzag_local(bs, thr):   # copy of review_lib.zigzag
    piv = []; mode = None; ext_i = 0; ext_p = bs[0]['c']
    for i, b in enumerate(bs):
        if mode is None:
            if b['h'] - ext_p >= thr: mode = 'up'; ext_i, ext_p = i, b['h']; piv.append((0, bs[0]['l'], 'L'))
            elif ext_p - b['l'] >= thr: mode = 'down'; ext_i, ext_p = i, b['l']; piv.append((0, bs[0]['h'], 'H'))
            continue
        if mode == 'up':
            if b['h'] > ext_p: ext_i, ext_p = i, b['h']
            elif ext_p - b['l'] >= thr: piv.append((ext_i, ext_p, 'H')); mode = 'down'; ext_i, ext_p = i, b['l']
        else:
            if b['l'] < ext_p: ext_i, ext_p = i, b['l']
            elif b['h'] - ext_p >= thr: piv.append((ext_i, ext_p, 'L')); mode = 'up'; ext_i, ext_p = i, b['h']
    piv.append((ext_i, ext_p, 'H' if mode == 'up' else 'L'))
    return piv


def zigzag(bs, thr):
    return _rl.zigzag(bs, thr) if _rl is not None else _zigzag_local(bs, thr)


def legs_of(bs, atr0, mult=1.5, floor=12.0, top=99):
    """Zigzag legs ≥ max(floor, mult×ATR) pts and ≥ 3 bars (review_lib.legs_of; top raised to keep every leg)."""
    if len(bs) < 4:
        return []
    if _rl is not None:
        return _rl.legs_of(bs, atr0, mult=mult, floor=floor, top=top)
    piv = _zigzag_local(bs, max(4.0, 1.0 * atr0))
    legs = [dict(i0=i0, i1=i1, pts=abs(p1 - p0), short=(p1 < p0), p0=p0, p1=p1)
            for (i0, p0, k0), (i1, p1, k1) in zip(piv, piv[1:]) if i1 > i0]
    thr = max(floor, mult * atr0)
    legs = [l for l in legs if l['pts'] >= thr and (l['i1'] - l['i0']) >= 3]
    legs = sorted(legs, key=lambda l: -l['pts'])[:top]; legs.sort(key=lambda l: l['i0'])
    return legs


def session_atr(rth):
    """The convention of day_review / missed_trades_study: ATR14 at bar min(20, n-1), default 6.0."""
    if len(rth) < 2:
        return 6.0
    return compute_atr(rth, min(20, len(rth) - 1)) or 6.0


# ── time helpers ─────────────────────────────────────────────────────────────────────────────────
def et_dt(d, hh, mm=0, ss=0):
    """Aware datetime at ET wall time hh:mm on date d (date or iso string)."""
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    return dt.datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=ET)


def il_dt(d, hhmm):
    """Aware datetime for an IL wall time 'HH:MM[:SS]' on date d."""
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    p = [int(x) for x in str(hhmm).split(":")[:3]]
    while len(p) < 3:
        p.append(0)
    return dt.datetime(d.year, d.month, d.day, p[0], p[1], p[2], tzinfo=IL)


def epoch(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return int(x)
    if isinstance(x, str):
        x = dt.datetime.fromisoformat(x.replace("Z", "+00:00"))
    if x.tzinfo is None:          # naive = UTC (v9_day_type_state convention)
        x = x.replace(tzinfo=UTC)
    return int(x.timestamp())


def il_hm(ep, sec=False):
    if ep is None:
        return None
    return dt.datetime.fromtimestamp(int(ep), IL).strftime("%H:%M:%S" if sec else "%H:%M")


def et_hm(ep):
    return None if ep is None else dt.datetime.fromtimestamp(int(ep), ET).strftime("%H:%M")


def et_min(ep):
    t = dt.datetime.fromtimestamp(int(ep), ET)
    return t.hour * 60 + t.minute


def et_date(ep):
    return dt.datetime.fromtimestamp(int(ep), ET).date().isoformat()


def phase_of(ep, d):
    """Phase of an event at epoch ep for session date d (iso): '0' overnight · A · B · C · D · 'post' (after 16:15 ET)."""
    t = dt.datetime.fromtimestamp(int(ep), ET)
    if t.date().isoformat() < d:
        return "0"
    if t.date().isoformat() > d:
        return "post"
    m = t.hour * 60 + t.minute
    if m < OPEN_MIN:
        return "0"
    if m < 600:
        return "A"
    if m < 630:
        return "B"
    if m < 840:
        return "C"
    if m < SESSION_END_MIN:
        return "D"
    return "post"


def min_after_open(ep, d):
    return round((int(ep) - int(et_dt(d, 9, 30).timestamp())) / 60.0, 1)


def checkpoint_epochs(d):
    """[(label, n_bars, epoch)] — checkpoints defined in ET (immune to the IL/ET DST-gap weeks)."""
    o = int(et_dt(d, 9, 30).timestamp())
    return [(lab, m // 5, o + m * 60) for lab, m in CHECKPOINTS]


# ── DB (read-only) ───────────────────────────────────────────────────────────────────────────────
_CONN = {}


def conn(db="mems26"):
    import psycopg2
    c = _CONN.get(db)
    if c is None or c.closed:
        c = psycopg2.connect(dbname=db)
        c.set_session(readonly=True, autocommit=True)
        _CONN[db] = c
    return c


def query(sql, args=(), db="mems26"):
    cur = conn(db).cursor()
    try:
        cur.execute(sql, args)
        return cur.fetchall()
    finally:
        cur.close()


def rth_dates(db="mems26", since=None, until=None, min_bars=60):
    """ET session dates with ≥ min_bars RTH bars (09:30–15:55 ET bar starts)."""
    w, a = "", []
    if since:
        w += " and ts >= %s"; a.append(et_dt(since, 0, 0))
    if until:
        w += " and ts < %s"; a.append(et_dt(until, 0, 0) + dt.timedelta(days=1))
    rows = query("select (ts at time zone 'America/New_York')::date, count(*) from v9_bars_5min_woodies where symbol='MES' "
                 "and (ts at time zone 'America/New_York')::time between '09:30' and '15:55'" + w + " group by 1 having count(*) >= %s order by 1",
                 tuple(a) + (min_bars,), db)
    return [r[0].isoformat() for r in rows]


def prev_session_date(d, db="mems26", min_bars=30):
    rows = query("select (ts at time zone 'America/New_York')::date, count(*) from v9_bars_5min_woodies where symbol='MES' and ts >= %s and ts < %s "
                 "and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' group by 1 having count(*) >= %s order by 1 desc limit 1",
                 (et_dt(d, 0, 0) - dt.timedelta(days=14), et_dt(d, 0, 0), min_bars), db)
    return rows[0][0].isoformat() if rows else None


def _mk_bar(ep, o, h, l, c, v):
    t = dt.datetime.fromtimestamp(int(ep), ET)
    return dict(ts=int(ep), il=il_hm(ep), et=t.strftime("%H:%M"), em=t.hour * 60 + t.minute, d=t.date().isoformat(),
                o=float(o), h=float(h), l=float(l), c=float(c), v=float(v or 0))


def load_day(d, db="mems26"):
    """→ dict(rth, on (overnight: prev RTH close → this open), prev (prior session: date + its RTH bars), db)."""
    pdate = prev_session_date(d, db)
    t0 = et_dt(pdate, 9, 30) if pdate else et_dt(d, 0, 0) - dt.timedelta(days=1)
    rows = query("select extract(epoch from ts)::bigint, open, high, low, close, volume from v9_bars_5min_woodies "
                 "where symbol='MES' and ts >= %s and ts < %s order by ts", (t0, et_dt(d, 16, 15)), db)
    bars = [_mk_bar(*r) for r in rows]
    rth = [b for b in bars if b["d"] == d and OPEN_MIN <= b["em"] <= LAST_RTH_BAR_MIN]
    prev_rth = [b for b in bars if pdate and b["d"] == pdate and OPEN_MIN <= b["em"] <= LAST_RTH_BAR_MIN]
    c0 = int(et_dt(pdate, 16, 0).timestamp()) if pdate else int(t0.timestamp())
    c1 = int(et_dt(d, 9, 30).timestamp())
    on = [b for b in bars if c0 <= b["ts"] < c1]
    for i, b in enumerate(rth):
        b["i"] = i
    return dict(rth=rth, on=on, prev=dict(date=pdate, rth=prev_rth) if pdate else None, db=db)


# ── reference (rule-based Dalton) — COPIED from scripts/eod_journal.py (prev_session_profile / ref_opening /
#    ref_daytype), adapted to bar dicts. Do not tune here: the thresholds are the super-agent's, not Michael's. ──
def session_profile(bars, date=None):
    """TPO profile of an RTH session (30-min letters = 6 five-minute bars, 70% value area) — eod_journal.prev_session_profile."""
    if not bars:
        return None
    prof = collections.defaultdict(set)
    for i, b in enumerate(bars):
        letter = i // 6; p = b['l']
        while p <= b['h'] + 1e-9:
            prof[round(p / TICK) * TICK].add(letter); p += TICK
    counts = {p: len(v) for p, v in prof.items()}; total = sum(counts.values())
    poc = max(counts, key=lambda p: (counts[p], -abs(p - (max(counts) + min(counts)) / 2)))
    lo = hi = poc; acc = counts[poc]
    while acc < 0.7 * total:
        up, dn = counts.get(round((hi + TICK) / TICK) * TICK, 0), counts.get(round((lo - TICK) / TICK) * TICK, 0)
        if up >= dn and up > 0: hi = round((hi + TICK) / TICK) * TICK; acc += up
        elif dn > 0: lo = round((lo - TICK) / TICK) * TICK; acc += dn
        else: break
    return dict(date=date, poc=poc, vah=hi, val=lo, high=max(b['h'] for b in bars), low=min(b['l'] for b in bars), close=bars[-1]['c'])


def ref_opening(bars, prev):
    """eod_journal.ref_opening — the first 30 min (6 bars) + the prior profile → (type, why)."""
    if len(bars) < 6: return "UNKNOWN", "פחות מ-6 ברים"
    o = bars[0]['o']
    highs = [b['h'] for b in bars[:6]]; lows = [b['l'] for b in bars[:6]]; closes = [b['c'] for b in bars[:6]]
    up_drive = all(c > o for c in closes[1:]) and min(lows[1:]) >= o - 2 * TICK
    dn_drive = all(c < o for c in closes[1:]) and max(highs[1:]) <= o + 2 * TICK
    if up_drive or dn_drive: return "OPEN_DRIVE", "אין חזרה לפתיחה בברים 2–6 (%s)" % ("↑" if up_drive else "↓")
    refs = [prev["high"], prev["low"], prev["vah"], prev["val"]] if prev else []
    probe_up = max(highs[:2]) > max([r for r in refs if r > o], default=1e9) if refs else False
    probe_dn = min(lows[:2]) < min([r for r in refs if r < o], default=-1e9) if refs else False
    if probe_up and all(c < o for c in closes[3:]): return "OPEN_TEST_DRIVE", "בדיקה מעל רפרנס, דרייב למטה"
    if probe_dn and all(c > o for c in closes[3:]): return "OPEN_TEST_DRIVE", "בדיקה מתחת לרפרנס, דרייב למעלה"
    if (max(highs[:3]) - o >= 4 and min(lows[3:]) < o) or (o - min(lows[:3]) >= 4 and max(highs[3:]) > o): return "OPEN_REJECTION_REVERSE", "דרייב ואז חזרה דרך הפתיחה"
    if prev and prev["low"] <= o <= prev["high"]: return "OPEN_AUCTION_IN", "סיבוב סביב הפתיחה בתוך הטווח הקודם"
    return "OPEN_AUCTION_OUT", "סיבוב סביב הפתיחה מחוץ לטווח הקודם" if prev else "אין רפרנס קודם"


def ref_daytype(bars, min_bars=24):
    """eod_journal.ref_daytype — Dalton pp.19-29 at EOD: IB = first 60 min; range extension with acceptance =
    ≥ 2 consecutive closes beyond the edge. min_bars is 24 as in eod_journal (ref_daytype_asof relaxes it)."""
    if len(bars) < min_bars: return "UNKNOWN", {}
    ibh, ibl = max(b['h'] for b in bars[:12]), min(b['l'] for b in bars[:12])
    hi, lo, close = max(b['h'] for b in bars), min(b['l'] for b in bars), bars[-1]['c']
    closes = [b['c'] for b in bars[12:]]
    up = any(closes[i] > ibh and closes[i + 1] > ibh for i in range(len(closes) - 1))
    dn = any(closes[i] < ibl and closes[i + 1] < ibl for i in range(len(closes) - 1))
    sides = int(up) + int(dn); rib = (hi - lo) / max(ibh - ibl, TICK); close_pos = (close - lo) / max(hi - lo, TICK)
    feats = dict(ibh=ibh, ibl=ibl, hi=hi, lo=lo, close=close, rib=round(rib, 2), close_pos=round(close_pos, 2), ext_up=up, ext_dn=dn)
    if sides == 0: return ("Nontrend" if rib <= 1.15 else "Normal"), feats
    if sides == 2: return ("Neutral_Extreme" if (close_pos >= 0.85 or close_pos <= 0.15) else "Neutral_Center"), feats
    if rib >= 2.0 and (close_pos >= 0.85 or close_pos <= 0.15): return "Trend_Normal", feats
    return "Normal_Variation", feats


def ref_daytype_asof(bars, n_bars):
    """The same rules on the first n_bars only (a checkpoint). Before the IB is complete + 1 bar → FORMING."""
    sub = bars[:n_bars]
    if len(sub) < 13:
        return "FORMING", {"n": len(sub)}
    lab, feats = ref_daytype(sub, min_bars=13)
    feats["n"] = len(sub)
    return lab, feats


def open_location(o, prev):
    if not prev or o is None:
        return None
    if prev["val"] <= o <= prev["vah"]: return "in_value"
    if prev["vah"] < o <= prev["high"]: return "above_value_in_range"
    if prev["low"] <= o < prev["val"]: return "below_value_in_range"
    return "above_range" if o > prev["high"] else "below_range"


OPEN_LOC_HEB = {"in_value": "בתוך הערך", "above_value_in_range": "מעל הערך, בתוך הטווח", "below_value_in_range": "מתחת לערך, בתוך הטווח",
                "above_range": "מעל הטווח", "below_range": "מתחת לטווח", None: "—"}


# ── IB and extension events ───────────────────────────────────────────────────────────────────────
def ib_events(rth):
    """IB = first 12 bars. For bars ≥ 12: first close beyond each edge, acceptance (2 consecutive closes beyond),
    and the first close back inside the IB after an acceptance. Each event: {i, ep (close known), t_il, px}."""
    if len(rth) < 12:
        return dict(complete=False, ibh=max([b['h'] for b in rth], default=None), ibl=min([b['l'] for b in rth], default=None))
    ibh, ibl = max(b['h'] for b in rth[:12]), min(b['l'] for b in rth[:12])

    def ev(i):
        b = rth[i]; e = b['ts'] + 300
        return dict(i=i, ep=e, t_il=il_hm(e), px=b['c'])
    out = dict(complete=True, ibh=ibh, ibl=ibl, width=round(ibh - ibl, 2), up_close=None, dn_close=None, up_accept=None, dn_accept=None,
               up_reentry=None, dn_reentry=None, ib_end_il=il_hm(rth[11]['ts'] + 300))
    for i in range(12, len(rth)):
        c = rth[i]['c']; pc = rth[i - 1]['c'] if i > 12 else None
        if c > ibh and out["up_close"] is None: out["up_close"] = ev(i)
        if c < ibl and out["dn_close"] is None: out["dn_close"] = ev(i)
        if pc is not None and c > ibh and pc > ibh and out["up_accept"] is None: out["up_accept"] = ev(i)
        if pc is not None and c < ibl and pc < ibl and out["dn_accept"] is None: out["dn_accept"] = ev(i)
        if ibl <= c <= ibh:
            if out["up_accept"] and out["up_reentry"] is None: out["up_reentry"] = ev(i)
            if out["dn_accept"] and out["dn_reentry"] is None: out["dn_reentry"] = ev(i)
    return out


def ib_events_in(ib, phase_bounds):
    """[(label, t_il)] of IB events whose time falls in [a, b) epoch."""
    a, b = phase_bounds; lab = {"up_close": "סגירה מעל IBH", "dn_close": "סגירה מתחת IBL", "up_accept": "קבלה מעל IBH (2 סגירות)",
                               "dn_accept": "קבלה מתחת IBL (2 סגירות)", "up_reentry": "חזרה לתוך ה-IB (אחרי ↑)", "dn_reentry": "חזרה לתוך ה-IB (אחרי ↓)"}
    out = []
    for k, heb in lab.items():
        e = ib.get(k)
        if e and a <= e["ep"] < b:
            out.append(dict(ev=k, t_il=e["t_il"], px=e["px"], heb=heb))
    return sorted(out, key=lambda x: x["t_il"])


def phase_bounds(d):
    """{phase: (start_epoch, end_epoch)} — '0' starts at the previous evening (open-ended)."""
    o = int(et_dt(d, 9, 30).timestamp())
    return {"0": (0, o), "A": (o, o + 1800), "B": (o + 1800, o + 3600), "C": (o + 3600, o + 16200), "D": (o + 16200, o + 24300)}


def market_of(bars):
    if not bars:
        return None
    o, h, l, c = bars[0]['o'], max(b['h'] for b in bars), min(b['l'] for b in bars), bars[-1]['c']
    return dict(o=o, h=h, l=l, c=c, range=round(h - l, 2), net=round(c - o, 2), n=len(bars))


# ── bar-path simulation (stop-first) ─────────────────────────────────────────────────────────────
def bar_at(bars, ep):
    """Index of the bar in progress at epoch ep (start ≤ ep < start+300); the first bar after ep if in a gap; None past the end."""
    for i, b in enumerate(bars):
        if b['ts'] <= ep < b['ts'] + 300:
            return i
        if b['ts'] > ep:
            return i
    return None


def bar_closed_at(bars, ep, grace=15):
    """Index of the last bar whose close was known at ep (start + 300 ≤ ep + grace)."""
    k = None
    for i, b in enumerate(bars):
        if b['ts'] + 300 <= ep + grace:
            k = i
        else:
            break
    return k


def eod_index(bars):
    """Index of the 15:45 ET bar (its close = the 15:50 EOD flat) or the last bar of a partial day."""
    k = None
    for i, b in enumerate(bars):
        if b['em'] <= EOD_FLAT_BAR_MIN:
            k = i
    return k


def sim_path(bars, i0, short, entry, stop, target, i_end=None):
    """One contract from bar i0 (inclusive) to i_end (default EOD bar): stop-first when a bar touches both.
    → dict(pts, how STOP|T1|EOD|NA, i, t_il (exit time), mfe, mae)."""
    if i0 is None or not bars:
        return dict(pts=None, how="NA", i=None, t_il=None, mfe=None, mae=None)
    i_end = eod_index(bars) if i_end is None else i_end
    if i_end is None or i0 > i_end:
        return dict(pts=None, how="NA", i=None, t_il=None, mfe=None, mae=None)
    mfe = mae = 0.0
    for j in range(i0, i_end + 1):
        b = bars[j]
        fav = (entry - b['l']) if short else (b['h'] - entry)
        adv = (b['h'] - entry) if short else (entry - b['l'])
        hit_s = stop is not None and ((b['h'] >= stop) if short else (b['l'] <= stop))
        hit_t = target is not None and ((b['l'] <= target) if short else (b['h'] >= target))
        if hit_s:
            return dict(pts=round((entry - stop) if short else (stop - entry), 2), how="STOP", i=j, t_il=b['il'], mfe=round(max(mfe, 0), 2), mae=round(max(mae, adv), 2))
        mfe = max(mfe, fav); mae = max(mae, adv)
        if hit_t:
            return dict(pts=round((entry - target) if short else (target - entry), 2), how="T1", i=j, t_il=b['il'], mfe=round(mfe, 2), mae=round(mae, 2))
    c = bars[i_end]['c']
    return dict(pts=round((entry - c) if short else (c - entry), 2), how="EOD", i=i_end, t_il=il_hm(bars[i_end]['ts'] + 300), mfe=round(mfe, 2), mae=round(mae, 2))


def sane_geometry(short, entry, stop, target, atr0):
    """Stop/target on the right side of the entry; otherwise the fallback 1×ATR (≥5) stop / 1.5×ATR target."""
    ok = True
    if stop is None or (short and stop <= entry) or ((not short) and stop >= entry):
        stop = entry + max(5.0, atr0) if short else entry - max(5.0, atr0); ok = False
    if target is None or (short and target >= entry) or ((not short) and target <= entry):
        target = entry - 1.5 * atr0 if short else entry + 1.5 * atr0; ok = False
    return stop, target, ok


def mfe_mae(bars, i0, i1, short, entry):
    if i0 is None or i1 is None or i1 < i0:
        return None, None
    hs = [b['h'] for b in bars[i0:i1 + 1]]; ls = [b['l'] for b in bars[i0:i1 + 1]]
    if not hs:
        return None, None
    return (round(entry - min(ls), 2), round(max(hs) - entry, 2)) if short else (round(max(hs) - entry, 2), round(entry - min(ls), 2))


# ── labels ────────────────────────────────────────────────────────────────────────────────────────
DT_ALIAS = {"Normal_Variation": "Variation", "Trend": "Trend_Normal", "TREND": "Trend_Normal", "": "UNKNOWN", None: "UNKNOWN",
            "FORMING": "UNKNOWN", "NA": "UNKNOWN", "INDETERMINATE": "UNKNOWN"}
DT_FAMILY = {"Trend_Normal": "Trend", "Trend_DD": "Trend", "Variation": "Variation", "Normal": "Normal",
             "Neutral_Center": "Neutral", "Neutral_Extreme": "Neutral", "Nontrend": "Nontrend"}
OT_ALIAS = {"INDETERMINATE": "UNKNOWN", "": "UNKNOWN", None: "UNKNOWN", "NA": "UNKNOWN"}
DT_HEB = {"Trend_Normal": "מגמה", "Trend_DD": "מגמה-DD", "Trend": "מגמה", "Normal": "נורמלי", "Variation": "וריאציה",
          "Normal_Variation": "וריאציה", "Neutral_Center": "ניטרלי-מרכז", "Neutral_Extreme": "ניטרלי-קיצון", "Neutral": "ניטרלי",
          "Nontrend": "ללא-מגמה", "UNKNOWN": "?", "UNCLEAR": "לא-ברור", "FORMING": "נבנה"}
OT_SHORT = {"OPEN_DRIVE": "Drive", "OPEN_TEST_DRIVE": "Test-Drive", "OPEN_REJECTION_REVERSE": "Rejection-Reverse",
            "OPEN_AUCTION_IN": "Auction-In", "OPEN_AUCTION_OUT": "Auction-Out", "UNKNOWN": "?", "UNCLEAR": "לא-ברור"}


def norm_dt(x):
    x = DT_ALIAS.get(x, x)
    return x if x else "UNKNOWN"


def dt_family(x):
    return DT_FAMILY.get(norm_dt(x))


def norm_ot(x):
    x = OT_ALIAS.get(x, x)
    if isinstance(x, str) and "/" in x:   # replay canonical_opening 'OPEN_AUCTION_IN/NEUTRAL'
        x = x.split("/")[0]
    if isinstance(x, str) and x.startswith("UNKNOWN"):
        return "UNKNOWN"
    return x or "UNKNOWN"


def dt_heb(x):
    return DT_HEB.get(x, DT_HEB.get(norm_dt(x), str(x)))


def ot_short(x):
    return OT_SHORT.get(norm_ot(x), str(x))


def fam_of(pattern):
    """Pattern → family: direction / touch / letter suffixes stripped (CEILING_FLIP_TOUCH2 → CEILING_FLIP,
    DOUBLE_BOTTOM_EE_LONG / DOUBLE_TOP_AA_SHORT → DOUBLE_TB, BULL/BEAR_FLAG → FLAG); S4 names stay."""
    p = (pattern or "?").upper()
    if p.startswith("DOUBLE_TOP") or p.startswith("DOUBLE_BOTTOM"):
        return "DOUBLE_TB"
    if p in ("BULL_FLAG_LONG", "BEAR_FLAG_SHORT") or p.endswith("_FLAG"):
        return "FLAG"
    p = re.sub(r"_(LONG|SHORT)$", "", p)
    p = re.sub(r"_TOUCH\d+$", "", p)
    return p or "?"


# ── wrong_if: rule-based alternatives to a trade's day-type thesis ───────────────────────────────
WRONG_RULES = {
    "Trend": [("Variation", "reentry", "חזרה לתוך ה-IB (סגירה בפנים אחרי סגירה בחוץ)"),
              ("Neutral", "other_accept", "הרחבה בצד השני (2 סגירות מעבר לקצה הנגדי של ה-IB)")],
    "Variation": [("Trend", "trend_accept", "קבלה מעבר ל-IB (2 סגירות) וטווח-היום ≥ 2×IB"),
                  ("Neutral", "other_accept", "הרחבה בצד השני (2 סגירות מעבר לקצה הנגדי של ה-IB)")],
    "Normal": [("Variation", "any_accept", "הרחבה עם קבלה (2 סגירות מעבר ל-IB)")],
    "Nontrend": [("Variation", "any_accept", "הרחבה עם קבלה (2 סגירות מעבר ל-IB)")],
    "Neutral": [("Trend", "trend_accept", "קבלה מעבר ל-IB (2 סגירות) וטווח-היום ≥ 2×IB")],
    None: [("Up-ext", "up_accept", "קבלה מעל IBH (2 סגירות)"), ("Down-ext", "dn_accept", "קבלה מתחת IBL (2 סגירות)")],
}


def _confirm_events(rth, ib, kind, short, e0):
    """Epochs (close known) where the confirm condition of `kind` becomes true. → [(ep, i, px)]."""
    if not ib.get("complete"):
        return []
    ibh, ibl, w = ib["ibh"], ib["ibl"], max(ib["ibh"] - ib["ibl"], TICK)
    out = []; prev_c = None; was_out = False; acc_up = acc_dn = False; hi, lo = ibh, ibl; trend_on = False
    pre = [b for b in rth if b['ts'] + 300 <= e0]
    if kind == "other_accept":   # the side opposite to the existing accepted extension at entry, else to the trade
        up_a = ib.get("up_accept") and ib["up_accept"]["ep"] <= e0
        dn_a = ib.get("dn_accept") and ib["dn_accept"]["ep"] <= e0
        side = "dn" if (up_a and not dn_a) else "up" if (dn_a and not up_a) else ("up" if short else "dn")
    for i in range(12, len(rth)):
        b = rth[i]; c = b['c']; ep = b['ts'] + 300; hi = max(hi, b['h']); lo = min(lo, b['l'])
        up2 = prev_c is not None and c > ibh and prev_c > ibh
        dn2 = prev_c is not None and c < ibl and prev_c < ibl
        if kind == "reentry":
            if ibl <= c <= ibh and was_out: out.append((ep, i, c))
            was_out = c > ibh or c < ibl
        elif kind in ("any_accept", "up_accept", "dn_accept", "other_accept"):
            want_up = kind in ("any_accept", "up_accept") or (kind == "other_accept" and side == "up")
            want_dn = kind in ("any_accept", "dn_accept") or (kind == "other_accept" and side == "dn")
            if want_up and up2 and not acc_up: out.append((ep, i, c))
            if want_dn and dn2 and not acc_dn: out.append((ep, i, c))
        elif kind == "trend_accept":
            if (acc_up or acc_dn or up2 or dn2) and (hi - lo) >= 2 * w and not trend_on:
                trend_on = True; out.append((ep, i, c))
        acc_up = acc_up or up2; acc_dn = acc_dn or dn2; prev_c = c
    return out


def wrong_if(thesis_dt, short, rth, ib, e0, e1, sys6=None):
    """For each alternative of the thesis: its confirm rule and whether / when it happened relative to the entry.
    e0 = entry epoch, e1 = exit epoch (None = still open). sys6 = [{ep, action, ...}] of the trade."""
    fam = dt_family(thesis_dt)
    rules = WRONG_RULES.get(fam, WRONG_RULES[None])
    res = []
    for alt, kind, rule in rules:
        evs = _confirm_events(rth, ib, kind, short, e0) if e0 else []
        after = [x for x in evs if x[0] > e0]; before = [x for x in evs if x[0] <= e0]
        pick = after[0] if after else (before[0] if before else None)
        r = dict(alt=alt, rule=rule, t_il=il_hm(pick[0]) if pick else None, px=pick[2] if pick else None,
                 already=bool(pick and not after), open_then=bool(pick and after and (e1 is None or pick[0] < e1)), sys6_then=None)
        if pick and sys6:
            last = [a for a in sys6 if a.get("ep") is not None and a["ep"] <= pick[0]]
            if last:
                r["sys6_then"] = "%s %s" % (last[-1]["action"], last[-1]["t_il"])
        res.append(r)
    return res


# ── backend log (one grep pass per process) ──────────────────────────────────────────────────────
_LOG_CACHE = {}
RX_LOCK = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d) .*T-314: locked opening=(\S+) dir=(\S+)(?: (at bar \d+|.*?))?\s*$")
RX_NEG = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d) .*T-314: NEGATED (\S+) \S+ re-read=(\S+) dir=(\S+)")
RX_BE = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d) .*BE_RULE (.*?)[: ]+trade (\d+)(?: \(reason: (.*)\))?\s*$")
RX_BE2 = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d) .*BE_RULE (.*)$")
RX_T426 = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d) .*T-426 provisional opening type (\S+?)→(\S+) for (\S+) (\S+)")


def scan_backend_log(path=BACKEND_LOG):
    """{date: {'locks': [...], 'negs': [...], 'be': {trade_id: {...}}, 'prov': [...]}} from the T-314 / BE_RULE / T-426 lines.
    One `grep -F` over the whole file (LC_ALL=C, ~2–3 s on 120 MB); cached for the process."""
    if path in _LOG_CACHE:
        return _LOG_CACHE[path]
    out = collections.defaultdict(lambda: dict(locks=[], negs=[], be={}, prov=[]))
    lines = []
    if os.path.exists(path):
        try:
            r = subprocess.run(["grep", "-a", "-F", "-e", "T-314", "-e", "BE_RULE", "-e", "T-426", path], capture_output=True,
                               env=dict(os.environ, LC_ALL="C"), timeout=50)
            lines = r.stdout.decode("utf-8", "replace").splitlines()
        except Exception:
            lines = []
    for ln in lines:
        m = RX_LOCK.match(ln)
        if m:
            out[m.group(1)]["locks"].append(dict(t_il=m.group(2), type=m.group(3), dir=m.group(4), how=(m.group(5) or "").strip())); continue
        m = RX_NEG.match(ln)
        if m:
            out[m.group(1)]["negs"].append(dict(t_il=m.group(2), was=m.group(3), reread=m.group(4), dir=m.group(5))); continue
        m = RX_T426.match(ln)
        if m:
            out[m.group(1)]["prov"].append(dict(t_il=m.group(2), frm=m.group(3), to=m.group(4), pattern=m.group(5), dir=m.group(6)))
        if "BE_RULE" in ln:
            m = RX_BE.match(ln)
            if m:
                out[m.group(1)]["be"].setdefault(m.group(4), dict(t_il=m.group(2), rule=m.group(3).strip(), reason=(m.group(5) or "").strip()))
            else:
                m2 = RX_BE2.match(ln); tid = re.search(r"trade (\d+)", ln)
                if m2 and tid:
                    out[m2.group(1)]["be"].setdefault(tid.group(1), dict(t_il=m2.group(2), rule=m2.group(3)[:80], reason=""))
    _LOG_CACHE[path] = dict(out)
    return _LOG_CACHE[path]


# ── Michael's labels (truth when present) ────────────────────────────────────────────────────────
def load_labels(path):
    try:
        with open(path, encoding="utf-8") as fh:
            j = json.load(fh)
        return dict(exported=j.get("exported"), days=j.get("days") or {}, trades=j.get("trades") or {}, path=path)
    except Exception:
        return dict(exported=None, days={}, trades={}, path=path, missing=True)


# ── gate names (copied from scripts/day_review.py GATE_HEB) ─────────────────────────────────────
GATE_HEB = {"tree:stand_down": "עץ: stand-down (אין שורה לנסיבה)", "tree:kind": "עץ: סוג-הכניסה לא ברשימה", "tree:bias": "עץ: נגד ההטיה",
            "tree:location": "עץ: מיקום מול הערך", "tree:time_cutoff": "עץ: אחרי שעת-הסיום", "dalton_intent:stand_down": "עץ-דלתון: stand-down",
            "dalton_intent:kind": "עץ-דלתון: סוג-כניסה נגד ההטיה", "dalton_intent:bias": "עץ-דלתון: ההטיה דוחה", "dalton_intent:location": "עץ-דלתון: מיקום",
            "opening_lock": "נעילת-פתיחה (T-314)", "live_slot_occupied": "סלוט-לייב תפוס", "extreme_chase_guard": "שער-רדיפה",
            "rr_hard_floor": "רצפת-R:R", "rr_entry_gate": "שער-R:R בכניסה", "entry_not_confirmed": "בר-אישור לא נסגר",
            "entry_location_quality": "איכות-מיקום-כניסה", "pattern_stop_cooldown": "צינון אחרי סטופ", "cold_start_guard": "שומר-התחלה-קרה",
            "fresh_extreme": "קיצון-טרי", "fhb": "חיץ-השעה-הראשונה", "strict_risk": "בדיקות-סיכון", "position_mismatch": "אי-התאמת פוזיציה"}


def gate_heb(g):
    if not g:
        return ""
    for k, v in GATE_HEB.items():
        if g.startswith(k):
            return v
    return g


def r2(x, nd=2):
    try:
        return None if x is None else round(float(x), nd)
    except Exception:
        return None
