#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-645 trade examiner — shared library (pure, read-only: reads data.json + the replay JSONs; no DB, no writes).

Sessions, yesterday's references, swings, the direction state (מצב-כיוון) and the system's own direction reads
(dir_hint Layer-2, structure, turn_state, LSMA+CVD veto, day type from the replay) — all from CLOSED 5-min bars.
"""
import os, sys, json, glob, statistics, collections, datetime as dt
from zoneinfo import ZoneInfo
ROOT = "/Users/michael/Downloads/mems26_web_git"
sys.path.insert(0, ROOT)
ET = ZoneInfo("America/New_York"); IL = ZoneInfo("Asia/Jerusalem")
TICK = 0.25
HERE = os.path.join(ROOT, "harness_out/t645/examiner")

_D = None
_ST = {}


def data():
    global _D
    if _D is None:
        _D = json.load(open(os.path.join(HERE, "data.json")))
        for b in _D["bars"]:
            t = dt.datetime.fromisoformat(b["ts"])
            b["t"] = t; b["et"] = t.astimezone(ET); b["il"] = t.astimezone(IL)
            b["hm"] = b["il"].strftime("%H:%M")
    return _D


_RTH = None


def use_bars(path):
    """Swap the bar source (e.g. bars81.json for the 81-session candidate check) and reset the caches."""
    global _RTH
    d = data(); B = json.load(open(path))["bars"]
    for b in B:
        t = dt.datetime.fromisoformat(b["ts"]); b["t"] = t; b["et"] = t.astimezone(ET); b["il"] = t.astimezone(IL)
        b["hm"] = b["il"].strftime("%H:%M")
    d["bars"] = B; _RTH = None; _ST.clear()


def rth_days():
    """{ET date iso: [RTH bars]} for every session with ≥ 60 RTH bars (cached)."""
    global _RTH
    if _RTH is not None:
        return _RTH
    out = collections.defaultdict(list)
    for b in data()["bars"]:
        if dt.time(9, 30) <= b["et"].time() < dt.time(16, 0):
            out[b["et"].date().isoformat()].append(b)
    _RTH = {k: v for k, v in out.items() if len(v) >= 60}
    return _RTH


def prev_day(day, days):
    p = [d for d in sorted(days) if d < day]
    return p[-1] if p else None


def eth_bars(day, days):
    p = prev_day(day, days)
    if not p:
        return []
    a = dt.datetime.combine(dt.date.fromisoformat(p), dt.time(16, 0), ET)
    z = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(9, 30), ET)
    return [b for b in data()["bars"] if a <= b["et"] < z]


def ticks(lo, hi):
    n = int(round((hi - lo) / TICK))
    return [round((lo + k * TICK) / TICK) * TICK for k in range(n + 1)]


def tpo_profile(bs):
    if not bs:
        return {}
    t0 = bs[0]["et"]; per = collections.defaultdict(list)
    for b in bs:
        per[int((b["et"] - t0).total_seconds() // 1800)].append(b)
    cnt = collections.Counter()
    for k, pb in per.items():
        for p in ticks(min(x["l"] for x in pb), max(x["h"] for x in pb)):
            cnt[p] += 1
    return cnt


def value_area(counts, frac=0.70):
    if not counts:
        return None
    px = sorted(counts); tot = sum(counts.values()); mid = (px[0] + px[-1]) / 2.0
    poc = max(px, key=lambda p: (counts[p], -abs(p - mid)))
    i = j = px.index(poc); acc = counts[poc]
    while acc < frac * tot and (i > 0 or j < len(px) - 1):
        up = sum(counts[px[k]] for k in range(j + 1, min(j + 3, len(px))))
        dn = sum(counts[px[k]] for k in range(max(i - 2, 0), i))
        if up >= dn and j < len(px) - 1:
            acc += up; j = min(j + 2, len(px) - 1)
        elif i > 0:
            acc += dn; i = max(i - 2, 0)
        else:
            acc += up; j = min(j + 2, len(px) - 1)
    return {"poc": poc, "val": px[i], "vah": px[j]}


def sys_tpo(day):
    """The system's own CASH row for a trading day (v9_tpo_sessions), last row of the day."""
    rows = [r for r in data()["tpo"] if r["trading_date"] == day]
    return rows[-1] if rows else None


def day_refs(day):
    """Yesterday's value/range (system TPO row when present, else TPO-from-bars), overnight range, today's open/IB."""
    days = rth_days(); bs = days[day]; p = prev_day(day, days); pb = days.get(p) or []
    st = sys_tpo(p) if p else None
    va = value_area(tpo_profile(pb)) if pb else None
    R = dict(day=day, prev=p)
    if pb:
        R.update(p_hi=max(x["h"] for x in pb), p_lo=min(x["l"] for x in pb), p_close=pb[-1]["c"],
                 p_vah_bars=va["vah"], p_val_bars=va["val"], p_poc_bars=va["poc"])
    # primary = TPO from the 5-min bars (the cards' method); the system's own CASH row is kept beside it — on 19.10 the
    # row is the frozen-letter VA (7743–7747, T-590), so the bars are the reliable source for yesterday's value
    if va:
        R.update(p_vah=va["vah"], p_val=va["val"], p_poc=va["poc"], p_src="bars")
    if st and st.get("vah_price") and st.get("val_price"):
        R.update(s_vah=float(st["vah_price"]), s_val=float(st["val_price"]), s_poc=float(st["poc_price"]))
    eb = eth_bars(day, days)
    if eb:
        R.update(on_hi=max(x["h"] for x in eb), on_lo=min(x["l"] for x in eb))
    R["open"] = bs[0]["o"]
    ib = bs[:12]
    R["ib_hi"] = max(x["h"] for x in ib); R["ib_lo"] = min(x["l"] for x in ib)
    R["hi"] = max(x["h"] for x in bs); R["lo"] = min(x["l"] for x in bs); R["close"] = bs[-1]["c"]
    fva = value_area(tpo_profile(bs)); R.update(vah=fva["vah"], val=fva["val"], poc=fva["poc"])
    o = R["open"]
    if "p_vah" in R:
        if R["p_val"] <= o <= R["p_vah"]:
            R["open_loc"] = "בתוך הערך של אתמול"
        elif R["p_lo"] <= o <= R["p_hi"]:
            R["open_loc"] = "מחוץ לערך ובתוך הטווח של אתמול (%s)" % ("מעל VAH" if o > R["p_vah"] else "מתחת VAL")
        else:
            R["open_loc"] = "מחוץ לטווח של אתמול (%s)" % ("מעל השיא" if o > R["p_hi"] else "מתחת לשפל")
    return R


# ── the direction state ───────────────────────────────────────────────────────────────────────────────────────
def theta_series(day, n=20, floor=3.0):
    """θ at the close of each RTH bar i = median(H−L) of the last n CLOSED RTH bars (yesterday's tail fills the start)."""
    days = rth_days(); bs = days[day]; p = prev_day(day, days)
    hist = list((days.get(p) or [])[-n:])
    out = []
    for b in bs:
        hist.append(b); hist = hist[-n:]
        out.append(max(floor, statistics.median([x["h"] - x["l"] for x in hist])))
    return out


def zigzag(bs, th):
    """Causal swings. th = θ per bar (list) or a number. A swing high is CONFIRMED at the close of the first bar that
    closes ≥ θ below the highest high of the current up-leg (mirror for lows). Returns the swing list
    [{type: H|L, px, i (bar of the extreme), ci (bar that confirmed it)}] in confirmation order."""
    th = th if isinstance(th, list) else [th] * len(bs)
    sw = []; leg = None
    hi, hi_i, lo, lo_i = bs[0]["h"], 0, bs[0]["l"], 0

    def low_after(a, i):
        if a < i:
            k = min(range(a + 1, i + 1), key=lambda k: bs[k]["l"]); return bs[k]["l"], k
        return bs[i]["l"], i

    def high_after(a, i):
        if a < i:
            k = max(range(a + 1, i + 1), key=lambda k: bs[k]["h"]); return bs[k]["h"], k
        return bs[i]["h"], i
    for i, b in enumerate(bs):
        T = th[i]
        if leg in (None, "up") and b["h"] > hi:
            hi, hi_i = b["h"], i
        if leg in (None, "down") and b["l"] < lo:
            lo, lo_i = b["l"], i
        if leg in (None, "up") and b["c"] <= hi - T:
            sw.append(dict(type="H", px=hi, i=hi_i, ci=i)); leg = "down"; lo, lo_i = low_after(hi_i, i)
        elif leg in (None, "down") and b["c"] >= lo + T:
            sw.append(dict(type="L", px=lo, i=lo_i, ci=i)); leg = "up"; hi, hi_i = high_after(lo_i, i)
    return sw


def direction_state(bs, th, sw, accept=1, fail_bars=0):
    """The direction state at the CLOSE of every bar (index i ⇒ known from the open of bar i+1).

    Break up   = a close above the last CONFIRMED swing high (confirmed on an earlier bar).
    Break down = a close below the last CONFIRMED swing low.
    accept = how many consecutive closes beyond the broken level the break needs (1 = the break bar itself).
    State: 'BAL' (מאוזן) from the open until the first accepted break · 'UP' after an accepted break up ·
           'DOWN' after an accepted break down. fail_bars > 0: a break that closes back through the broken level within
           fail_bars bars is a FAILED break ⇒ 'BAL' (two-timeframe) until the next accepted break.
    Returns (states, events) — events: (i, kind, level, price) with kind ∈ up/down/fail."""
    th = th if isinstance(th, list) else [th] * len(bs)
    st = []; ev = []; cur = "BAL"; pend = None; last_brk = None
    for i, b in enumerate(bs):
        known = [s for s in sw if s["ci"] < i]
        H = next((s for s in reversed(known) if s["type"] == "H"), None)
        L = next((s for s in reversed(known) if s["type"] == "L"), None)
        c = b["c"]
        # failed break: back through the broken level soon after
        if fail_bars and last_brk and cur in ("UP", "DOWN") and i - last_brk[0] <= fail_bars:
            k, lvl = last_brk[1], last_brk[2]
            if (k == "up" and c < lvl) or (k == "down" and c > lvl):
                cur = "BAL"; ev.append((i, "fail", lvl, c)); last_brk = None
        up = H is not None and c > H["px"]
        dn = L is not None and c < L["px"]
        if up:
            pend = ("up", H["px"], (pend[2] + 1) if (pend and pend[0] == "up" and pend[1] == H["px"]) else 1)
        elif dn:
            pend = ("down", L["px"], (pend[2] + 1) if (pend and pend[0] == "down" and pend[1] == L["px"]) else 1)
        else:
            pend = None
        if pend and pend[2] >= accept:
            new = "UP" if pend[0] == "up" else "DOWN"
            if new != cur or (last_brk is None or last_brk[2] != pend[1]):
                if new != cur:
                    ev.append((i, pend[0], pend[1], c))
                last_brk = (i, pend[0], pend[1])
            cur = new
        st.append(cur)
    return st, ev


def structure_state(bs, sw):
    """Classic Dow reading of the last two confirmed swing highs/lows (+ the live close beyond the last one):
    'UP' = HH+HL · 'DOWN' = LH+LL · 'BAL' = mixed or not enough swings."""
    out = []
    for i, b in enumerate(bs):
        known = [s for s in sw if s["ci"] <= i]
        hs = [s["px"] for s in known if s["type"] == "H"][-2:]
        ls = [s["px"] for s in known if s["type"] == "L"][-2:]
        c = b["c"]
        hu = (len(hs) == 2 and hs[1] > hs[0]) or (hs and c > hs[-1])
        hd = len(hs) == 2 and hs[1] < hs[0] and not (c > hs[-1])
        lu = len(ls) == 2 and ls[1] > ls[0] and not (c < ls[-1])
        ld = (len(ls) == 2 and ls[1] < ls[0]) or (ls and c < ls[-1])
        out.append("UP" if (hu and lu) else "DOWN" if (hd and ld) else "BAL")
    return out


def hour_pos(bs, i, price, direction):
    """Where `price` sits in the range of the last 12 CLOSED bars (≤ i), measured from the stop side:
    0 = at the stop-side edge (a long at the hour low), 1 = at the far edge. Returns (pos, label edge|middle|far)."""
    h12 = bs[max(0, i - 11):i + 1]
    hh = max(x["h"] for x in h12); ll = min(x["l"] for x in h12); rg = max(hh - ll, TICK)
    pos = ((hh - price) / rg) if direction == "SHORT" else ((price - ll) / rg)
    return pos, ("edge" if pos <= 0.35 else "middle" if pos <= 0.65 else "far")


def il_hm(b):
    return b["il"].strftime("%H:%M")


def bar_index_at(bs, ts):
    """Index of the last bar CLOSED at time ts (bar ts + 5 min ≤ ts), −1 if none."""
    k = -1
    for i, b in enumerate(bs):
        if b["t"] + dt.timedelta(minutes=5) <= ts:
            k = i
        else:
            break
    return k


def label_candidate(bs, ts, direction, entry, stop):
    """good = +1R before the stop · bad = stop first · flat = neither by the close (the T-643 label, identical rule:
    in the entry bar only the stop counts; a bar touching both = stop first)."""
    if entry is None or stop is None:
        return None, None
    ep = float(entry); R = abs(ep - float(stop))
    if R < 0.5:
        return None, None
    short = direction == "SHORT"
    path = [b for b in bs if b["t"] >= ts - dt.timedelta(seconds=30) - dt.timedelta(minutes=5) and b["t"] + dt.timedelta(minutes=5) > ts]
    path = [b for b in bs if b["t"] + dt.timedelta(minutes=5) > ts]
    for k, b in enumerate(path):
        adv = (b["h"] - ep) if short else (ep - b["l"]); fav = (ep - b["l"]) if short else (b["h"] - ep)
        if adv >= R:
            return "bad", il_hm(b)
        if k > 0 and fav >= R:
            return "good", il_hm(b)
    return "flat", None


def replay(day, variant="live"):
    f = os.path.join(ROOT, "harness_out/t640/days/%s_%s.json" % (variant, day))
    return json.load(open(f)) if os.path.exists(f) else None


def replay_candidates(day, variant="live"):
    """Every candidate of the replay day: routes ⨝ gateway_decisions (parallel lists)."""
    d = replay(day, variant)
    if not d:
        return []
    out = []
    for r, g in zip(d.get("routes") or [], d.get("gateway_decisions") or []):
        ts = dt.datetime.fromisoformat(str(g["ts"]).replace("Z", "+00:00"))
        tv = g.get("tree_v3") or r.get("tree_v3") or {}
        out.append(dict(ts=ts, hm=ts.astimezone(IL).strftime("%H:%M"), pat=g.get("pattern"), dir=g.get("direction"),
                        entry=r.get("entry"), stop=r.get("stop"), t1=r.get("t1"), blocked=g.get("blocked_by"),
                        reason=(g.get("reason") or "")[:140], outcome=g.get("outcome"), leaf=tv.get("leaf"),
                        lid=tv.get("id"), path=tv.get("path"), vec=tv.get("vec") or {}, dir_hint=r.get("dp_dir_hint"),
                        dtype=r.get("dp_day_type"), same=(r.get("classification"), r.get("direction")) == (g.get("pattern"), g.get("direction"))))
    return out


def zigzag_ext(bs, th):
    """Causal swings on bar EXTREMES (the standard high/low zigzag): a swing high is CONFIRMED at the close of the first
    bar whose LOW is ≥ θ below the highest high of the current up-leg (mirror for lows). Same output as zigzag()."""
    th = th if isinstance(th, list) else [th] * len(bs)
    sw = []; leg = None
    hi, hi_i, lo, lo_i = bs[0]["h"], 0, bs[0]["l"], 0
    for i, b in enumerate(bs):
        T = th[i]
        if leg is None:
            if b["h"] > hi: hi, hi_i = b["h"], i
            if b["l"] < lo: lo, lo_i = b["l"], i
            if hi - lo >= T:
                if hi_i < lo_i:      # high came first: a swing high, now in a down-leg from it
                    sw.append(dict(type="H", px=hi, i=hi_i, ci=i)); leg = "down"
                elif lo_i < hi_i:
                    sw.append(dict(type="L", px=lo, i=lo_i, ci=i)); leg = "up"
            continue
        if leg == "up":
            if b["h"] > hi:
                hi, hi_i = b["h"], i
            if b["l"] <= hi - T and hi_i < i:
                sw.append(dict(type="H", px=hi, i=hi_i, ci=i)); leg = "down"
                k = min(range(hi_i + 1, i + 1), key=lambda k: bs[k]["l"]); lo, lo_i = bs[k]["l"], k
            elif b["l"] <= hi - T and hi_i == i and b["c"] <= hi - T:
                # one bar made the high and closed a full θ below it: the high is confirmed by the close
                sw.append(dict(type="H", px=hi, i=i, ci=i)); leg = "down"; lo, lo_i = b["l"], i
        else:
            if b["l"] < lo:
                lo, lo_i = b["l"], i
            if b["h"] >= lo + T and lo_i < i:
                sw.append(dict(type="L", px=lo, i=lo_i, ci=i)); leg = "up"
                k = max(range(lo_i + 1, i + 1), key=lambda k: bs[k]["h"]); hi, hi_i = bs[k]["h"], k
            elif b["h"] >= lo + T and lo_i == i and b["c"] >= lo + T:
                sw.append(dict(type="L", px=lo, i=i, ci=i)); leg = "up"; hi, hi_i = b["h"], i
    return sw


# ── THE direction state of the examiner (final definition, see REPORT.md §ב) ─────────────────────────────────
HE = {"UP": "עולה", "DOWN": "יורד", "BAL": "מאוזן"}


def dstate(bs, th, sw=None, accept=2, fail_bars=6, halfback=True):
    """מצב-כיוון at the CLOSE of every bar (from closed bars only).
      swings: zigzag_ext (bar extremes, threshold θ = one normal bar)
      a. accepted break: `accept` consecutive closes beyond the last confirmed swing (high ⇒ UP, low ⇒ DOWN)
      b. transition: the first close beyond the opposite swing while UP/DOWN ⇒ BAL
      c. failed break: within `fail_bars` bars of the accepted break, a close back through the broken level ⇒ BAL
      d. half-back: a close that gives back half of the leg (from the break's origin swing to the extreme since) ⇒ BAL
      e. from the open until the first accepted break ⇒ BAL
    Returns (states, events) — events: dict(i, to, why, level, px)."""
    th = th if isinstance(th, list) else [th] * len(bs)
    sw = sw if sw is not None else zigzag_ext(bs, th)
    st = []; ev = []; cur = "BAL"; run = None; brk = None
    for i, b in enumerate(bs):
        known = [s for s in sw if s["ci"] < i]
        H = next((s for s in reversed(known) if s["type"] == "H"), None)
        L = next((s for s in reversed(known) if s["type"] == "L"), None)
        c = b["c"]; new = cur; why = None; lvl = None
        if H is not None and c > H["px"]:
            run = ("up", H["px"], (run[2] + 1) if (run and run[0] == "up" and run[1] == H["px"]) else 1)
        elif L is not None and c < L["px"]:
            run = ("down", L["px"], (run[2] + 1) if (run and run[0] == "down" and run[1] == L["px"]) else 1)
        else:
            run = None
        if brk and cur in ("UP", "DOWN"):
            if cur == "UP":
                brk["ext"] = max(brk["ext"], b["h"])
            else:
                brk["ext"] = min(brk["ext"], b["l"])
        if run and run[2] >= accept:
            tgt = "UP" if run[0] == "up" else "DOWN"
            if tgt != cur:
                new, why, lvl = tgt, "שבירה מקובלת (%d סגירות) %s %s" % (accept, "מעל שיא-סווינג" if tgt == "UP" else "מתחת לשפל-סווינג", run[1]), run[1]
                org = (L["px"] if (tgt == "UP" and L) else H["px"] if (tgt == "DOWN" and H) else None)
                ext0 = max(x["h"] for x in bs[max(0, i - accept + 1):i + 1]) if tgt == "UP" else min(x["l"] for x in bs[max(0, i - accept + 1):i + 1])
                brk = dict(i=i, dir=tgt, level=run[1], origin=org, ext=ext0)
            elif brk is None or brk["level"] != run[1]:
                brk = dict(i=i, dir=tgt, level=run[1], origin=(L["px"] if tgt == "UP" and L else H["px"] if H else None),
                           ext=(b["h"] if tgt == "UP" else b["l"]))
        elif run and run[2] == 1 and ((cur == "UP" and run[0] == "down") or (cur == "DOWN" and run[0] == "up")):
            new, why, lvl = "BAL", "מעבר: סגירה ראשונה %s %s" % ("מתחת לשפל-סווינג" if run[0] == "down" else "מעל שיא-סווינג", run[1]), run[1]
        elif cur in ("UP", "DOWN") and brk:
            if fail_bars and i - brk["i"] <= fail_bars and ((cur == "UP" and c < brk["level"]) or (cur == "DOWN" and c > brk["level"])):
                new, why, lvl = "BAL", "שבירה נכשלה: סגירה חזרה %s %s תוך %d ברים" % ("מתחת" if cur == "UP" else "מעל", brk["level"], i - brk["i"]), brk["level"]
            elif halfback and brk.get("origin") is not None:
                mid = (brk["origin"] + brk["ext"]) / 2.0
                if (cur == "UP" and c <= mid and brk["ext"] > brk["origin"]) or (cur == "DOWN" and c >= mid and brk["ext"] < brk["origin"]):
                    new, why, lvl = "BAL", "חצי-חזרה: סגירה %s באמצע הרגל %s→%s (%.2f)" % (c, brk["origin"], brk["ext"], mid), mid
        if new != cur:
            ev.append(dict(i=i, to=new, frm=cur, why=why, level=lvl, px=c))
            cur = new
            if cur == "BAL":
                brk = None
        st.append(cur)
    return st, ev


def turning_points(bs, thr):
    """Hindsight swings of the full session (bar extremes, threshold thr points) — the 'actual' turning points."""
    pts = []; leg = None; hi, hi_i, lo, lo_i = bs[0]["h"], 0, bs[0]["l"], 0
    for i, b in enumerate(bs):
        if leg is None:
            if b["h"] > hi: hi, hi_i = b["h"], i
            if b["l"] < lo: lo, lo_i = b["l"], i
            if hi - lo >= thr:
                if hi_i < lo_i:
                    pts.append(("H", hi, hi_i)); leg = "down"
                else:
                    pts.append(("L", lo, lo_i)); leg = "up"
                continue
        elif leg == "up":
            if b["h"] > hi: hi, hi_i = b["h"], i
            if b["l"] <= hi - thr and hi_i < i:
                pts.append(("H", hi, hi_i)); leg = "down"
                k = min(range(hi_i + 1, i + 1), key=lambda k: bs[k]["l"]); lo, lo_i = bs[k]["l"], k
        else:
            if b["l"] < lo: lo, lo_i = b["l"], i
            if b["h"] >= lo + thr and lo_i < i:
                pts.append(("L", lo, lo_i)); leg = "up"
                k = max(range(lo_i + 1, i + 1), key=lambda k: bs[k]["h"]); hi, hi_i = bs[k]["h"], k
    # the final open leg's extreme
    if leg == "up":
        pts.append(("H", hi, hi_i))
    elif leg == "down":
        pts.append(("L", lo, lo_i))
    # the session open as the first point when the first turn is not at bar 0
    return pts


# ── candidate features at a moment (closed bars only) + the examiner's questions ──────────────────────────────


def day_state(day):
    """(bars, θ, swings, states, events) for a session, cached."""
    if day not in _ST:
        bs = rth_days()[day]; th = theta_series(day); sw = zigzag_ext(bs, th)
        st, ev = dstate(bs, th, sw)
        _ST[day] = (bs, th, sw, st, ev)
    return _ST[day]


def features(day, ts, direction, entry):
    """Everything the questions need, computed from the bars CLOSED before ts."""
    from backend.v9.services import turn_state as TS
    bs, th, sw, st, ev = day_state(day)
    k = bar_index_at(bs, ts)
    short = direction == "SHORT"; want = "DOWN" if short else "UP"
    if k < 0 or entry is None:
        return None
    ep = float(entry); seen = bs[:k + 1]; sig = bs[k]
    s = st[k]
    rel = "with" if s == want else ("BAL" if s == "BAL" else "against")
    pos, pl = hour_pos(bs, k, ep, direction)
    ruleA = "ib_forming"
    if k >= 11:
        ibh = max(x["h"] for x in bs[:12]); ibl = min(x["l"] for x in bs[:12])
        last6 = seen[12:][-6:]
        beyond = [x for x in last6 if (x["c"] > ibh if short else x["c"] < ibl)]
        ds = sum((x["d"] or 0) for x in beyond)
        ruleA = "accepted_against" if (len(beyond) >= 3 and ((ds > 0) if short else (ds < 0))) else "no"
    s_hi = max(x["h"] for x in seen); s_lo = min(x["l"] for x in seen); s_rg = max(s_hi - s_lo, 0.25)
    sess_edge = ((s_hi - ep) <= 0.25 * s_rg) if short else ((ep - s_lo) <= 0.25 * s_rg)
    va_edge = None
    if len(seen) >= 6:
        dva = value_area(tpo_profile(seen))
        va_edge = (ep >= dva["vah"] - 0.5 * th[k]) if short else (ep <= dva["val"] + 0.5 * th[k])
    tn = TS.detect_turn([dict(h=x["h"], l=x["l"], c=x["c"]) for x in seen]) if k >= 2 else {"turn": "none"}
    trel = TS.turn_rel(tn, direction, ep)
    o = bs[0]["o"]; rg = max(sig["h"] - sig["l"], 0.25)
    if short:
        rev_bar = sig["h"] >= s_hi - 0.01 and sig["c"] < o and (sig["h"] - sig["c"]) / rg >= 0.67
    else:
        rev_bar = sig["l"] <= s_lo + 0.01 and sig["c"] > o and (sig["c"] - sig["l"]) / rg >= 0.67
    d3 = sum((x["d"] or 0) for x in seen[-3:])
    md = sorted(abs(x["d"] or 0) for x in seen[-20:]); med = md[len(md) // 2] if md else 0
    eff_against = ((d3 > 0) if short else (d3 < 0)) and med > 0 and abs(d3) >= 3.0 * med
    hm = ts.astimezone(IL).strftime("%H:%M")
    phase = "A" if hm < "16:45" else "B" if hm < "17:30" else "C" if hm < "21:00" else "D"
    climax = (sig["h"] - sig["l"]) >= 2.0 * th[k] and ((sig["c"] < sig["o"]) if short else (sig["c"] > sig["o"]))
    # since when is the state what it is, and what was the confirmed direction before it (reversal = opposite)
    last_ev = [e for e in ev if e["i"] <= k]
    since = (k - last_ev[-1]["i"]) if last_ev else k + 1
    prev_dir = None
    for e in reversed(last_ev[:-1] if last_ev else []):
        if e["to"] in ("UP", "DOWN"):
            prev_dir = e["to"]; break
    # a test, not a chase: the entry within 1θ of the last 3 closed bars' extreme on the stop side
    l3 = seen[-3:]
    test = ((max(x["h"] for x in l3) - ep) <= th[k]) if short else ((ep - min(x["l"] for x in l3)) <= th[k])
    return dict(since=since, prev_dir=prev_dir, test=test, k=k, state=s, rel=rel, pos=pos, pos_lab=pl, ruleA=ruleA, sess_edge=sess_edge, va_edge=va_edge, turn=tn.get("turn"),
                turn_rel=trel, rev_bar=rev_bar, d3=d3, med=med, eff_against=eff_against, phase=phase, climax=climax, theta=th[k])


QUESTIONS = ("ש1", "ש2-פתיחה", "ש2-D", "ש2-C", "ש3", "ש4")


def ask(f):
    """The examiner's refusal questions (REPORT.md §ה). Returns the list of questions that would REFUSE the candidate.
      ש1 צד: against the direction state ⇒ only a responsive trade at a DEFENDED edge — the session extreme was
            double-tested and defended (turn_rel edge/with), or the entry is at the edge of the day (outer quarter of
            the session range / at the developing VA edge) and the extension against it is not accepted (rule A).
      ש2 מאוזן (no direction yet / any more):
            ש2-פתיחה  phases A/B (before any accepted break) ⇒ no entry, except the rejection-reverse bar (the signal bar
                      made the session extreme and closed back through the open, in its far third);
            ש2-D      phase D ⇒ no new entry in balance;
            ש2-C      phase C ⇒ not against an accepted extension (rule A) and not into effort (Σdelta of the last 3
                      closed bars ≥ 3 × the median |bar delta| of the last 20, against the trade).
      ש3 בר-שיא: the signal bar is a climax bar (range ≥ 2θ, closed in the trade's direction) and the entry is at the far
            end of the last hour (pos > 0.65) ⇒ wait for acceptance (the next close).
      ש4 אמצע-רוטציה: with the state, but both session extremes are defended (turn = range) and the entry is in the middle
            of the last hour (0.35 < pos ≤ 0.65) ⇒ refuse."""
    if not f:
        return ["ש2-פתיחה"]      # no closed RTH bar yet (16:30 bar still open) — nothing is known
    out = []
    if f["rel"] == "against":
        defended = f["turn_rel"] in ("edge", "with")
        day_edge = (f["sess_edge"] or bool(f["va_edge"])) and f["ruleA"] != "accepted_against"
        if not (defended or day_edge):
            out.append("ש1")
    if f["rel"] == "BAL":
        if f["phase"] in ("A", "B"):
            if not f["rev_bar"]:
                out.append("ש2-פתיחה")
        elif f["phase"] == "D":
            out.append("ש2-D")
        elif f["ruleA"] == "accepted_against" or f["eff_against"]:
            out.append("ש2-C")
    if f["climax"] and f["pos"] > 0.65 and not f["rev_bar"]:
        out.append("ש3")
    if f["rel"] == "with" and f["turn"] == "range" and 0.35 < f["pos"] <= 0.65:
        out.append("ש4")
    return out
