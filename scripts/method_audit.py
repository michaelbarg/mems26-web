#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""method_audit.py — is the method right, do the branches work (Michael 05.10 15:1x). Read-only.
Sources: harness_out/t466/<tag>_<session>.json (live-config replay: decisions with the tree path + stop/t1, realized trades
with MFE/MAE), v9_bars_5min_woodies (candidate-level scoring), v9_trades (live), decision vectors (labels).
usage: python3 scripts/method_audit.py [--tag t529b]"""
import collections, datetime as dt, glob, json, math, os, statistics, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "t529b"
COMM = 2.60; PT = 5.0; RR = 1.5


def q(sql):
    out = subprocess.run('%s -d mems26 -Atc "%s"' % (PSQL, sql.replace('"', '\\"')), shell=True, capture_output=True, text=True, timeout=180).stdout
    return [r.split("|") for r in out.splitlines() if r]


def fl(x):
    try:
        return float(x)
    except Exception:
        return None


bars = collections.defaultdict(list)
for r in q("select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), high, low, close "
           "from v9_bars_5min_woodies where symbol='MES' and ts>='2026-06-01' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts"):
    if len(r) == 5:
        bars[r[0]].append((r[1], fl(r[2]), fl(r[3]), fl(r[4])))


def score(day, t_il, direction, entry, stop):
    """fixed model: stop/target first touch after the decision bar (stop first in a tie), EOD close."""
    if entry is None or stop is None or stop == entry:
        return None
    risk = abs(entry - stop); tgt = entry + RR * risk if direction == "LONG" else entry - RR * risk
    seq = [b for b in bars.get(day, []) if b[0] > t_il]
    if not seq:
        return None
    for _, h, l, c in seq:
        if direction == "LONG":
            if l <= stop:
                return (stop - entry) * PT - COMM
            if h >= tgt:
                return (tgt - entry) * PT - COMM
        else:
            if h >= stop:
                return (entry - stop) * PT - COMM
            if l <= tgt:
                return (entry - tgt) * PT - COMM
    c = seq[-1][3]
    return ((c - entry) if direction == "LONG" else (entry - c)) * PT - COMM


sess = {}
for p in sorted(glob.glob("harness_out/t466/%s_2026-*.json" % TAG)):
    d = os.path.basename(p)[len(TAG) + 1:len(TAG) + 11]
    try:
        sess[d] = json.load(open(p))
    except Exception:
        pass
days = sorted(sess)
cands = []
for d in days:
    j = sess[d]
    trades_d = j.get("trades", [])
    for r in (j.get("routes") or []):
        tv = r.get("tree_v3")
        if not isinstance(tv, dict):
            continue
        ep = fl(r.get("entry")); stp = fl(r.get("stop")); direction = r.get("direction")
        t_il = (r.get("il") or "00:00:00")[:5]
        sc = None
        if ep and stp and 1.0 <= abs(ep - stp) <= 30:
            sc = score(d, t_il, direction, ep, stp)
        tr = None
        if (r.get("result") or {}).get("live"):
            for t in trades_d:
                if t.get("classification") == r.get("classification") and t.get("direction") == direction and abs((fl(t.get("entry")) or 0) - ep) < 0.01:
                    tr = t; break
        cands.append({"day": d, "t": t_il, "pattern": r.get("classification"), "dir": direction, "leaf": str(tv.get("leaf") or "SKIP").upper(), "id": tv.get("id"),
                      "path": tv.get("path", ""), "vec": tv.get("vec") or {}, "blocked": r.get("blocked_by"), "outcome": (r.get("result") or {}).get("blocked_by"),
                      "score": sc, "fired": bool(tr), "trade_pnl": (fl(tr.get("pnl_usd")) if tr else None), "trade": tr})
scored = [c for c in cands if c["score"] is not None]
print("== A · candidate-level raw edge (fixed model: stop from the setup, target %.1fR, first touch, EOD close) ==" % RR)
print("sessions %d · candidates %d · scored %d" % (len(days), len(cands), len(scored)))


def agg(rows, key):
    g = collections.defaultdict(list)
    for c in rows:
        g[key(c)].append(c["score"])
    out = []
    for k, v in g.items():
        out.append((k, len(v), sum(1 for x in v if x > 0) / len(v) * 100, sum(v)))
    return sorted(out, key=lambda x: -x[1])


def show(title, rows, key, top=12):
    print("-- %s" % title)
    for k, n, w, s in agg(rows, key)[:top]:
        print("   %-46s n=%4d win %3.0f%% S %+8.0f$ · per cand %+6.1f$" % (str(k)[:46], n, w, s, s / n))


allsum = sum(c["score"] for c in scored)
print("ALL: n=%d win %.0f%% S %+.0f$ (per candidate %+.1f$)" % (len(scored), sum(1 for c in scored if c["score"] > 0) / len(scored) * 100, allsum, allsum / len(scored)))
show("by tree leaf (selection check: TAKE vs SKIP)", scored, lambda c: c["leaf"])
show("by pattern", scored, lambda c: c["pattern"], 18)
show("by phase", scored, lambda c: c["vec"].get("phase"))
show("by day_type (label at decision)", scored, lambda c: c["vec"].get("day_type"))
show("by zone", scored, lambda c: c["vec"].get("zone"))
show("by rel_bias", scored, lambda c: c["vec"].get("rel_bias"))
periods = [("<=09-08 pre-doctrine", lambda d: d <= "2026-09-08"), ("09-09..09-26 tree v1-3.0", lambda d: "2026-09-09" <= d <= "2026-09-26"), (">=09-27 package+", lambda d: d >= "2026-09-27")]
print("-- TAKE vs SKIP by period (candidate-level)")
for name, f in periods:
    sub = [c for c in scored if f(c["day"])]
    for leaf in ("TAKE", "SKIP"):
        v = [c["score"] for c in sub if c["leaf"] == leaf]
        if v:
            print("   %-26s %-5s n=%4d win %3.0f%% S %+8.0f$ per cand %+6.1f$" % (name, leaf, len(v), sum(1 for x in v if x > 0) / len(v) * 100, sum(v), sum(v) / len(v)))

print("\n== B · ruled branches — before the ruling date (in-sample) vs from the ruling date (out-of-sample) ==")
ruled = {"auction_B_trend_break": "2026-09-25", "take_with_extension": "2026-09-24", "d_with_extension": "2026-09-27",
         "take_failed_ext_responsive": "2026-10-03", "take_location": "2026-09-11", "take_failed_ext (T-329/S7 27.09)": "2026-09-27"}
by_id = collections.defaultdict(list)
for c in scored:
    cid = c["id"] or ""
    if cid in ruled:
        by_id[cid].append(c)
    elif "edge=failed_extension" in c["path"] and c["leaf"] == "TAKE":
        by_id["take_failed_ext (T-329/S7 27.09)"].append(c)


def st(v):
    s = [c["score"] for c in v]; tr = [c["trade_pnl"] for c in v if c["trade_pnl"] is not None]
    return "n=%3d win %3.0f%% Scand %+7.0f$ (per %+5.1f) · trades %d S %+7.0f$" % (len(s), (sum(1 for x in s if x > 0) / len(s) * 100) if s else 0, sum(s), (sum(s) / len(s)) if s else 0, len(tr), sum(tr))


for cid, rows in sorted(by_id.items(), key=lambda kv: -len(kv[1])):
    d0 = ruled.get(cid, "2026-09-27")
    pre = [c for c in rows if c["day"] < d0]; post = [c for c in rows if c["day"] >= d0]
    print("   %-36s ruled %s\n      before: %s\n      after : %s" % (cid[:36], d0, st(pre), st(post)))

print("\n== C · the live-config replay, trade-level ==")
trades = [(d, t) for d in days for t in sess[d].get("trades", [])]
pnls = [fl(t.get("pnl_usd")) or 0 for _, t in trades]
daily = [fl(sess[d].get("daily_pnl_harness")) or 0 for d in days]
mean = statistics.mean(daily); sd = statistics.pstdev(daily); tstat = mean / (sd / math.sqrt(len(daily))) if sd else 0
eq = 0; peak = 0; dd = 0
for v in daily:
    eq += v; peak = max(peak, eq); dd = min(dd, eq - peak)
print("sessions %d · trades %d · S %+.2f$ · per trade %+.2f$ · win %.0f%% · daily mean %+.2f sd %.2f t=%.2f · max DD %.2f · best %+.2f worst %+.2f" %
      (len(days), len(trades), sum(pnls), sum(pnls) / max(1, len(pnls)), sum(1 for p in pnls if p > 0) / max(1, len(pnls)) * 100, mean, sd, tstat, dd, max(daily), min(daily)))
bym = collections.defaultdict(list)
for d, v in zip(days, daily):
    bym[d[:7]].append(v)
print("   by month: " + " · ".join("%s %+.0f (%d d, %d+)" % (m, sum(v), len(v), sum(1 for x in v if x > 0)) for m, v in sorted(bym.items())))
wins = [t for _, t in trades if (fl(t.get("pnl_usd")) or 0) > 0]; loss = [t for _, t in trades if (fl(t.get("pnl_usd")) or 0) <= 0]


def risk(t):
    e, s = fl(t.get("entry")), fl(t.get("stop_initial"))
    return abs(e - s) if (e is not None and s is not None and e != s) else None


mfeR = [(fl(t.get("mfe_pts")) or 0) / risk(t) for t in wins + loss if risk(t)]
if mfeR:
    print("   MFE in R (all trades): median %.2f · >=2R %.0f%% · >=3R %.0f%% · >=5R %.0f%%" % (statistics.median(mfeR), sum(1 for x in mfeR if x >= 2) / len(mfeR) * 100, sum(1 for x in mfeR if x >= 3) / len(mfeR) * 100, sum(1 for x in mfeR if x >= 5) / len(mfeR) * 100))
cap = sum(fl(t.get("t1_pts")) or 0 for t in wins); mfe_w = sum(fl(t.get("mfe_pts")) or 0 for t in wins)
print("   winners %d: S taken %.0f pts of S MFE %.0f pts = capture %.0f%%" % (len(wins), cap, mfe_w, cap / mfe_w * 100 if mfe_w else 0))
lossR = [(fl(t.get("mfe_pts")) or 0) / risk(t) for t in loss if risk(t)]
print("   losers %d: reached >=1R before the stop %.0f%% · >=0.5R %.0f%%" % (len(loss), sum(1 for x in lossR if x >= 1) / max(1, len(lossR)) * 100, sum(1 for x in lossR if x >= 0.5) / max(1, len(lossR)) * 100))
htc = sum(fl(t.get("hold_to_close_pts")) or 0 for _, t in trades) * PT - COMM * len(trades)
print("   hold-to-close alternative S %+.0f$ vs realized %+.0f$ · stop-only alternative S %+.0f$" % (htc, sum(pnls), sum(fl(t.get("pnl_stop_only_usd")) or 0 for _, t in trades)))
show("replay trades by pattern (realized)", [{"score": fl(t.get("pnl_usd")) or 0, "pattern": t.get("classification")} for _, t in trades], lambda c: c["pattern"], 14)

print("\n== D · live (broker) vs the current-config replay, same days ==")
live_day = {r[0]: (fl(r[1]) or 0, int(r[2])) for r in q("select to_char(coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem','YYYY-MM-DD'), sum(coalesce(pnl_sierra,pnl_usd,0)), count(*) "
                                                       "from v9_trades where mode='live' and state='CLOSED' group by 1") if len(r) == 3}
common = [d for d in days if d in live_day]
lv = sum(live_day[d][0] for d in common); rp = sum(fl(sess[d].get("daily_pnl_harness")) or 0 for d in common)
print("common days %d · live S %+.2f$ (%d trades) · replay S %+.2f$ (%d trades) · gap %+.2f$" % (len(common), lv, sum(live_day[d][1] for d in common), rp, sum(len(sess[d].get("trades", [])) for d in common), rp - lv))
for name, f in periods:
    cd = [d for d in common if f(d)]
    if cd:
        r_ = sum(fl(sess[d].get("daily_pnl_harness")) or 0 for d in cd); l_ = sum(live_day[d][0] for d in cd)
        print("   %-26s days %2d · live %+8.2f · replay %+8.2f · gap %+8.2f" % (name, len(cd), l_, r_, r_ - l_))
print("-- live record (all live days, broker where known)")
allv = sorted(live_day.items())
eq = 0; peak = 0; dd = 0
for d, (v, n) in allv:
    eq += v; peak = max(peak, eq); dd = min(dd, eq - peak)
print("   live days %d · S %+.2f$ · trades %d · max DD %.2f · first %s last %s" % (len(allv), sum(v for _, (v, n) in allv), sum(n for _, (v, n) in allv), dd, allv[0][0] if allv else "-", allv[-1][0] if allv else "-"))
bym = collections.defaultdict(lambda: [0.0, 0, 0])
for d, (v, n) in allv:
    bym[d[:7]][0] += v; bym[d[:7]][1] += n; bym[d[:7]][2] += 1
print("   by month: " + " · ".join("%s %+.0f (%d trades, %d days)" % (m, v[0], v[1], v[2]) for m, v in sorted(bym.items())))
fr = q("select round(avg(pnl_sierra - pnl_usd)::numeric,2), count(*) from v9_trades where mode='live' and state='CLOSED' and pnl_sierra is not null and pnl_usd is not null and coalesce(entry_ts,created_at)>='2026-09-01'")
print("   friction (broker - books) per live trade since 01.09: %s$ on %s trades" % (fr[0][0] if fr and fr[0] else "?", fr[0][1] if fr and len(fr[0]) > 1 else "?"))
pat = q("select pattern_id_at_entry, count(*), round(sum(coalesce(pnl_sierra,pnl_usd,0))::numeric,2), round(100.0*sum(case when coalesce(pnl_sierra,pnl_usd,0)>0 then 1 else 0 end)/count(*)) from v9_trades where mode='live' and state='CLOSED' group by 1 order by 2 desc limit 12")
print("   live by pattern: " + " · ".join("%s n=%s S%s win%s%%" % tuple(r) for r in pat if len(r) == 4))

print("\n== E · day-type label: intraday vs EOD ==")
agree = 0; tot = 0; trans = []; conf = collections.Counter()
for d in days:
    seq = [(c["t"], c["vec"].get("day_type")) for c in cands if c["day"] == d and c["vec"].get("day_type") not in (None, "", "FORMING")]
    if not seq:
        continue
    eod = seq[-1][1]
    at1730 = next((lb for t, lb in seq if t >= "17:30"), None)
    if at1730:
        tot += 1; agree += 1 if at1730 == eod else 0; conf[(at1730, eod)] += 1
    labels = [lb for _, lb in seq]
    trans.append(sum(1 for i in range(1, len(labels)) if labels[i] != labels[i - 1]))
print("sessions with labels %d · label at 17:30 == EOD label: %.0f%% · label changes per session: median %s · >=3 changes: %d sessions" %
      (tot, agree / tot * 100 if tot else 0, statistics.median(trans) if trans else "-", sum(1 for x in trans if x >= 3)))
print("   17:30 -> EOD: " + " · ".join("%s->%s %d" % (a, b, n) for (a, b), n in conf.most_common(10)))
