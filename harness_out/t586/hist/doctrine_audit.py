#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Super-agent T1 — DOCTRINE CONFORMANCE AUDIT, one session at a time (Michael 18.10: "עובר על שעות המסחר של כל יום,
ועובר ליום הבא רק לאחר שהמערכת פועלת בהתאם להנחיות הדוקטרינה"). For a harness tag's sessions it checks, from the bars
themselves (Dalton pp.63-74, 19-29) against what the system saw and did:
  OT   opening type the system locked vs the reference read off the first 30 minutes + prior value/range
  DT   day type published at EOD vs the reference from IB / range-extension-with-acceptance / close position
  PV   prior-day value area the tree used (prev_tpo) vs the prior session's own profile (width, levels)
  ST   every live-eligible candidate's stop vs the nearest structural anchor on its side (IB edge, developing VA
       edge/POC, session extreme, prior VA edge/high/low, opening range) — the doctrine puts the stop where the thesis
       is wrong, not at a pattern distance
  T1   T1 >= 1.5R and T1 at a structural target (nearest anchor ahead)
usage: doctrine_audit.py <TAG> <sessions.txt|YYYY-MM-DD ...> [--db=mems26_hist] [--detail] [--out=<csv>]"""
import sys, os, json, subprocess, collections, datetime as dt
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
args = [a for a in sys.argv[1:] if not a.startswith("--")]; opt = {a.split("=")[0][2:]: (a.split("=", 1)[1] if "=" in a else "1") for a in sys.argv[1:] if a.startswith("--")}
TAG = args[0]; DB = opt.get("db", "mems26_hist"); DETAIL = "detail" in opt
sessions = sum((open(a).read().split() if a.endswith(".txt") else [a] for a in args[1:]), [])
TICK = 0.25
def q(sql): return subprocess.run([PSQL, "-d", DB, "-Atc", sql], capture_output=True, text=True).stdout.strip().splitlines()
def rth_bars(s):
    rows = q(f"select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close, volume from v9_bars_5min_woodies where symbol='MES' "
             f"and (ts at time zone 'America/New_York')::date='{s}' and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts")
    return [(r.split("|")[0], *map(float, r.split("|")[1:6])) for r in rows]
def prev_session_profile(s):
    """prior RTH session's TPO value area from its own 5-min bars (30-minute letters, 70% around the POC)."""
    rows = q(f"select (ts at time zone 'America/New_York')::date from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'America/New_York')::date < '{s}' "
             f"and (ts at time zone 'America/New_York')::time between '09:30' and '15:55' order by ts desc limit 1")
    if not rows: return None
    pd_ = rows[0]; bars = rth_bars(pd_)
    if len(bars) < 30: return None
    prof = collections.defaultdict(set)
    for i, b in enumerate(bars):
        letter = i // 6; p = b[3]
        while p <= b[2] + 1e-9:
            prof[round(p / TICK) * TICK].add(letter); p += TICK
    counts = {p: len(v) for p, v in prof.items()}; total = sum(counts.values()); poc = max(counts, key=lambda p: (counts[p], -abs(p - (max(counts) + min(counts)) / 2)))
    lo = hi = poc; acc = counts[poc]
    while acc < 0.7 * total:
        up, dn = counts.get(round((hi + TICK) / TICK) * TICK, 0), counts.get(round((lo - TICK) / TICK) * TICK, 0)
        if up >= dn and up > 0: hi = round((hi + TICK) / TICK) * TICK; acc += up
        elif dn > 0: lo = round((lo - TICK) / TICK) * TICK; acc += dn
        else: break
    return dict(date=pd_, poc=poc, vah=hi, val=lo, high=max(b[2] for b in bars), low=min(b[3] for b in bars))
def ref_opening(bars, prev):
    """Dalton pp.63-74 on the first 30 minutes (6 bars). Returns (type, note)."""
    if len(bars) < 6: return "UNKNOWN", "fewer than 6 bars"
    o = bars[0][1]; b0h, b0l = bars[0][2], bars[0][3]
    highs = [b[2] for b in bars[:6]]; lows = [b[3] for b in bars[:6]]; closes = [b[4] for b in bars[:6]]
    up_drive = all(c > o for c in closes[1:]) and min(lows[1:]) >= o - 2 * TICK
    dn_drive = all(c < o for c in closes[1:]) and max(highs[1:]) <= o + 2 * TICK
    if up_drive or dn_drive: return "OPEN_DRIVE", "no re-trade of the open in bars 2-6"
    # test-drive: first 1-2 bars probe one side (beyond a prior reference), then the drive goes the other way and holds
    refs = [prev["high"], prev["low"], prev["vah"], prev["val"]] if prev else []
    probe_up = max(highs[:2]) > max([r for r in refs if r > o], default=1e9) if refs else False
    probe_dn = min(lows[:2]) < min([r for r in refs if r < o], default=-1e9) if refs else False
    if probe_up and all(c < o for c in closes[3:]) : return "OPEN_TEST_DRIVE", "probe above a prior reference, drive down"
    if probe_dn and all(c > o for c in closes[3:]) : return "OPEN_TEST_DRIVE", "probe below a prior reference, drive up"
    # rejection-reverse: a drive of >= 4 pts that comes back through the open within the 30 minutes
    if (max(highs[:3]) - o >= 4 and min(lows[3:]) < o) or (o - min(lows[:3]) >= 4 and max(highs[3:]) > o): return "OPEN_REJECTION_REVERSE", "drive then back through the open"
    if prev and prev["low"] <= o <= prev["high"]: return "OPEN_AUCTION_IN", "rotation around the open inside the prior range"
    return "OPEN_AUCTION_OUT", "rotation around the open outside the prior range" if prev else "no prior reference"
def ref_daytype(bars):
    """Dalton pp.19-29 at EOD: IB = first 60 min; range extension with acceptance = >= 2 consecutive closes beyond the edge."""
    if len(bars) < 24: return "UNKNOWN", {}
    ibh, ibl = max(b[2] for b in bars[:12]), min(b[3] for b in bars[:12]); ib = max(ibh - ibl, TICK)
    def accepted(side):
        run = 0
        for b in bars[12:]:
            beyond = b[4] > ibh + 2 * TICK if side == "up" else b[4] < ibl - 2 * TICK
            run = run + 1 if beyond else 0
            if run >= 2: return True
        return False
    sides = int(accepted("up")) + int(accepted("dn")); hi, lo = max(b[2] for b in bars), min(b[3] for b in bars)
    rng = hi - lo; rib = rng / ib; close_pos = (bars[-1][4] - lo) / rng if rng else 0.5
    feats = dict(ib=round(ib, 2), rib=round(rib, 2), sides=sides, close_pos=round(close_pos, 2), range=round(rng, 2))
    if sides == 0: return ("Nontrend" if rib <= 1.15 else "Normal"), feats
    if sides == 2: return ("Neutral_Extreme" if (close_pos >= 0.85 or close_pos <= 0.15) else "Neutral_Center"), feats
    if rib >= 2.0 and (close_pos >= 0.85 or close_pos <= 0.15): return "Trend_Normal", feats
    return "Normal_Variation", feats
def nearest_anchor(px, anchors, side):
    """nearest anchor at/beyond px on the stop's side ('below' for a long stop, 'above' for a short stop)"""
    # a long's stop sits just BELOW its anchor (anchor >= stop), a short's just ABOVE it (anchor <= stop)
    c = [(abs(a - px), name, a) for name, a in anchors if a is not None and ((a >= px - 2 * TICK) if side == "below" else (a <= px + 2 * TICK))]
    return min(c) if c else (None, None, None)
NORM = {"Variation": "Normal_Variation", "Normal_Variation": "Normal_Variation", "Trend": "Trend_Normal", "Trend_DD": "Trend_Normal"}
census = collections.Counter(); rows_out = []
for s in sessions:
    p = f"harness_out/t466/{TAG}_{s}.json"
    if not os.path.exists(p): print(f"{s}: no {TAG} output"); continue
    j = json.load(open(p)); bars = rth_bars(s); prev = prev_session_profile(s)
    if len(bars) < 24: print(f"{s}: only {len(bars)} RTH bars"); continue
    findings = []
    # OT — the system's locked opening type vs the reference
    sys_ot = next((x.get("ot_locked") for x in reversed(j.get("s1") or []) if x.get("ot_locked")), None)
    ref_ot, why = ref_opening(bars, prev)
    if sys_ot and ref_ot != "UNKNOWN" and sys_ot != ref_ot: findings.append(("OT", f"system {sys_ot} vs bars {ref_ot} ({why})"))
    # DT — published at EOD vs the reference
    pub = next((x.get("published") for x in reversed(j.get("s1") or []) if x.get("published")), None)
    ref_dt, feats = ref_daytype(bars)
    if pub and NORM.get(pub, pub) != NORM.get(ref_dt, ref_dt): findings.append(("DT", f"system {pub} vs bars {ref_dt} {feats}"))
    # PV — the prior-day value area the tree used
    pt = j.get("prev_tpo") or {}
    if prev and pt.get("found"):
        w = (pt.get("vah") or 0) - (pt.get("val") or 0)
        if w < 3 or abs((pt.get("poc") or 0) - prev["poc"]) > 4 or abs((pt.get("vah") or 0) - prev["vah"]) > 4 or abs((pt.get("val") or 0) - prev["val"]) > 4:
            findings.append(("PV", f"tree saw POC/VAH/VAL {pt.get('poc')}/{pt.get('vah')}/{pt.get('val')} (width {w:.2f}) vs prior profile {prev['poc']}/{prev['vah']}/{prev['val']}"))
    # ST / T1 — live-eligible candidates
    ibh, ibl = max(b[2] for b in bars[:12]), min(b[3] for b in bars[:12]); orh, orl = bars[0][2], bars[0][3]
    for r in j.get("routes") or []:
        res = r.get("result") or {}
        if r.get("blocked_by") or r.get("shadow_only") or not (res.get("live") or r.get("live_blocked_by") == "live_slot_occupied"): continue
        try: entry, stop, t1 = float(r["entry"]), float(r["stop"]), float(r.get("t1") or 0)
        except (TypeError, ValueError): continue
        il = r["il"][:5]; m = int(il[:2]) * 60 + int(il[3:5]); past = [b for b in bars if int(b[0][:2]) * 60 + int(b[0][3:5]) < m]
        sh, sl = (max(b[2] for b in past), min(b[3] for b in past)) if past else (None, None)
        anchors = [("IB_high", ibh if len(past) >= 12 else None), ("IB_low", ibl if len(past) >= 12 else None), ("session_high", sh), ("session_low", sl),
                   ("open_range_high", orh), ("open_range_low", orl)] + ([("prev_VAH", prev["vah"]), ("prev_VAL", prev["val"]), ("prev_POC", prev["poc"]), ("prev_high", prev["high"]), ("prev_low", prev["low"])] if prev else [])
        long = r["direction"].upper() == "LONG"; R = abs(entry - stop)
        d, name, a = nearest_anchor(stop, anchors, "below" if long else "above")
        if d is None or d > 1.0: findings.append(("ST", f"{il} {r['classification']} {r['direction']} stop {stop} R={R:.2f}: nearest anchor {name}={a} at {d if d is not None else '∞'} pts"))
        tid = str(((r.get("exec") or {}).get("live") or {}).get("trade_id")); tr = next((t for t in j.get("trades") or [] if str(t.get("trade_id")) == tid), None)
        t1x = float(tr.get("t1_target") or 0) if tr else t1          # taken: the executed target (1.5R floor applied); else the raw setup target
        if t1x and R > 0 and abs(t1x - entry) < 1.5 * R - 0.01: findings.append(("T1", f"{il} {r['classification']} t1 {t1x} = {abs(t1x-entry)/R:.2f}R (< 1.5R){'' if tr else ' [raw setup, floor applies at execution]'}"))
        d2, name2, a2 = nearest_anchor(t1x, anchors, "above" if long else "below") if t1x else (None, None, None)
        if t1x and (d2 is None or d2 > 1.0): findings.append(("TT", f"{il} {r['classification']} t1 {t1x}: nearest structural target {name2}={a2} at {d2 if d2 is not None else '∞'} pts"))
    cats = collections.Counter(c for c, _ in findings); census.update(cats)
    print(f"{s}: OT sys={sys_ot} ref={ref_ot} · DT sys={pub} ref={ref_dt} · findings {dict(cats)}")
    if DETAIL:
        for c, t in findings: print(f"   {c}: {t}")
    rows_out.append(dict(session=s, sys_ot=sys_ot, ref_ot=ref_ot, sys_dt=pub, ref_dt=ref_dt, **{c: cats.get(c, 0) for c in ("OT", "DT", "PV", "ST", "T1", "TT")}))
print(f"\nCENSUS over {len(rows_out)} sessions: {dict(census)}")
if opt.get("out"):
    import csv; w = csv.DictWriter(open(opt["out"], "w", newline=""), fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out); print("→", opt["out"])
