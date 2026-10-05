#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""context_table.py — bar-by-bar calibration per day type (Michael 05.10 15:30: "לעבור בר-בר … ולהתאים את ההחלטות שבזיהוי
כל סוג-יום נמקסם את המערכת — לבצע עכשיו"). Read-only; prints the rule layer and its train/holdout numbers.

Every candidate of the live-config replay (routes with the tree path) is scored with the fixed model (its own stop, 1.5R,
first touch, EOD close). Train = sessions <= --split, holdout = later sessions (never used to pick rules).
Rules: context = (day_type at decision, hour bucket, pattern, direction). VETO a context the current tree TAKEs when train
n >= N_MIN and per-candidate $ <= VETO_PER and win <= VETO_WIN. ALLOW a context the current tree SKIPs when train n >= N_MIN,
per-candidate $ >= ALLOW_PER and win >= ALLOW_WIN. Plus the hour cutoff (no entries from --cutoff IL).
usage: python3 scripts/context_table.py [--tag t529b] [--split 2026-09-19] [--cutoff 20]
"""
import collections, datetime as dt, glob, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
ARG = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa
TAG = ARG("--tag", "t529b"); SPLIT = ARG("--split", "2026-09-19"); CUTOFF = int(ARG("--cutoff", "20"))
N_MIN = 20; VETO_PER = -4.0; VETO_WIN = 42; ALLOW_PER = 6.0; ALLOW_WIN = 50
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
    risk = abs(entry - stop); tgt = entry + RR * risk if direction == "LONG" else entry - RR * risk
    seq = [b for b in bars.get(day, []) if b[0] > t_il]
    if not seq:
        return None
    for _, h, l, c in seq:
        if direction == "LONG":
            if l <= stop: return (stop - entry) * PT - COMM
            if h >= tgt: return (tgt - entry) * PT - COMM
        else:
            if h >= stop: return (entry - stop) * PT - COMM
            if l <= tgt: return (entry - tgt) * PT - COMM
    c = seq[-1][3]
    return ((c - entry) if direction == "LONG" else (entry - c)) * PT - COMM


def hbucket(h):
    return "16-17" if h <= 17 else ("18-19" if h <= 19 else "20+")


cands = []
for p in sorted(glob.glob("harness_out/t466/%s_2026-*.json" % TAG)):
    d = os.path.basename(p)[len(TAG) + 1:len(TAG) + 11]
    try:
        j = json.load(open(p))
    except Exception:
        continue
    for r in (j.get("routes") or []):
        tv = r.get("tree_v3")
        if not isinstance(tv, dict):
            continue
        ep = fl(r.get("entry")); stp = fl(r.get("stop")); direction = r.get("direction")
        if not (ep and stp and 1.0 <= abs(ep - stp) <= 30):
            continue
        t_il = (r.get("il") or "00:00:00")[:5]
        sc = score(d, t_il, direction, ep, stp)
        if sc is None:
            continue
        v = tv.get("vec") or {}
        cands.append({"day": d, "hour": int(t_il[:2]), "hb": hbucket(int(t_il[:2])), "pattern": r.get("classification") or "?", "dir": direction,
                      "leaf": str(tv.get("leaf") or "SKIP").upper(), "dt": v.get("day_type") or "?", "phase": v.get("phase") or "?",
                      "structure": v.get("structure") or "?", "score": sc, "shadow": bool(r.get("shadow_only"))})
train = [c for c in cands if c["day"] <= SPLIT]; hold = [c for c in cands if c["day"] > SPLIT]
days_tr = sorted(set(c["day"] for c in train)); days_ho = sorted(set(c["day"] for c in hold))
print("candidates %d · train %d (%d sessions <= %s) · holdout %d (%d sessions)" % (len(cands), len(train), len(days_tr), SPLIT, len(hold), len(days_ho)))


def stats(rows):
    s = [c["score"] for c in rows]
    return (len(s), (sum(1 for x in s if x > 0) / len(s) * 100) if s else 0, sum(s), (sum(s) / len(s)) if s else 0)


def key(c):
    return (c["dt"], c["hb"], c["pattern"], c["dir"])


# current tree on train / holdout (TAKE pool only — what the system would fire before the later gates)
for name, rows in (("train", train), ("holdout", hold)):
    tk = [c for c in rows if c["leaf"] == "TAKE"]; n, w, s, per = stats(tk)
    print("current tree TAKE on %-7s n=%4d win %3.0f%% S %+8.0f$ per %+5.1f$" % (name, n, w, s, per))

# the context table from TRAIN only
ctx = collections.defaultdict(list)
for c in train:
    ctx[key(c)].append(c)
veto, allow = [], []
for k, rows in ctx.items():
    n, w, s, per = stats(rows)
    if n < N_MIN:
        continue
    takes = sum(1 for c in rows if c["leaf"] == "TAKE")
    if takes >= 0.5 * n and per <= VETO_PER and w <= VETO_WIN:
        veto.append((k, n, w, s, per))
    skips = n - takes
    live_cap = sum(1 for c in rows if not c["shadow"]) >= 0.5 * n
    if skips >= 0.5 * n and per >= ALLOW_PER and w >= ALLOW_WIN and live_cap:
        allow.append((k, n, w, s, per))
veto.sort(key=lambda x: x[3]); allow.sort(key=lambda x: -x[3])
print("\n-- VETO (the tree takes, the data says no; train n>=%d, per<=%s$, win<=%d%%) --" % (N_MIN, VETO_PER, VETO_WIN))
for k, n, w, s, per in veto:
    print("   %-16s %-6s %-24s %-5s n=%3d win %3.0f%% S %+7.0f$ per %+5.1f$" % (k[0], k[1], k[2], k[3], n, w, s, per))
print("-- ALLOW (the tree skips, the data says yes, live-capable; train n>=%d, per>=%s$, win>=%d%%) --" % (N_MIN, ALLOW_PER, ALLOW_WIN))
for k, n, w, s, per in allow:
    print("   %-16s %-6s %-24s %-5s n=%3d win %3.0f%% S %+7.0f$ per %+5.1f$" % (k[0], k[1], k[2], k[3], n, w, s, per))
VETO = set(k for k, *_ in veto); ALLOW = set(k for k, *_ in allow)


def new_take(c):
    if c["hour"] >= CUTOFF:
        return False
    if key(c) in VETO:
        return False
    if key(c) in ALLOW:
        return True
    return c["leaf"] == "TAKE"


print("\n-- the rule layer applied (cutoff %d:00 + veto + allow) --" % CUTOFF)
for name, rows in (("train", train), ("holdout", hold)):
    old = [c for c in rows if c["leaf"] == "TAKE"]; new = [c for c in rows if new_take(c)]
    n0, w0, s0, p0 = stats(old); n1, w1, s1, p1 = stats(new)
    print("   %-7s OLD n=%4d win %3.0f%% S %+8.0f$ | NEW n=%4d win %3.0f%% S %+8.0f$ | delta %+8.0f$" % (name, n0, w0, s0, n1, w1, s1, s1 - s0))
    for part, f in (("cutoff only", lambda c: c["leaf"] == "TAKE" and c["hour"] < CUTOFF), ("veto only", lambda c: c["leaf"] == "TAKE" and key(c) not in VETO),
                    ("allow only", lambda c: c["leaf"] == "TAKE" or key(c) in ALLOW)):
        n2, w2, s2, p2 = stats([c for c in rows if f(c)])
        print("      %-11s n=%4d win %3.0f%% S %+8.0f$ (delta %+7.0f$)" % (part, n2, w2, s2, s2 - s0))
json.dump({"split": SPLIT, "cutoff": CUTOFF, "veto": [list(k) + [n, w, s, per] for k, n, w, s, per in veto], "allow": [list(k) + [n, w, s, per] for k, n, w, s, per in allow]},
          open("harness_out/t529/context_table.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
