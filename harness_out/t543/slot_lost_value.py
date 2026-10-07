# -*- coding: utf-8 -*-
"""Read-only: the candidate-level value (fixed model: own stop, 1.5R, first touch, EOD, $5/pt, 2.60$) of the candidates the
strongest branch lost to the single live slot (live_blocked_by=live_slot_occupied) and to the chaser gate, t529b, 65 sessions."""
import collections, glob, json, os, subprocess
os.chdir("/Users/michael/Downloads/mems26_web_git")
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"; COMM = 2.60; PT = 5.0; RR = 1.5
out = subprocess.run(PSQL + " -d mems26 -Atc \"select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), high, low, close from v9_bars_5min_woodies where symbol='MES' and ts>='2026-06-01' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts\"", shell=True, capture_output=True, text=True).stdout
bars = collections.defaultdict(list)
for r in out.splitlines():
    p = r.split("|")
    if len(p) == 5: bars[p[0]].append((p[1], float(p[2]), float(p[3]), float(p[4])))

def score(day, t_il, direction, entry, stop):
    risk = abs(entry - stop); tgt = entry + RR * risk if direction == "LONG" else entry - RR * risk
    seq = [b for b in bars.get(day, []) if b[0] > t_il]
    if not seq: return None
    for _, h, l, c in seq:
        if direction == "LONG":
            if l <= stop: return (stop - entry) * PT - COMM
            if h >= tgt: return (tgt - entry) * PT - COMM
        else:
            if h >= stop: return (entry - stop) * PT - COMM
            if l <= tgt: return (entry - tgt) * PT - COMM
    c = seq[-1][3]; return ((c - entry) if direction == "LONG" else (entry - c)) * PT - COMM

PATHS = ["opening_type=OPEN_DRIVE/phase=C/day_type=Trend_Normal/rel_bias=with",
         "opening_type=OPEN_AUCTION_IN/phase=B/day_type=*(FORMING)/kind=REVERSAL",
         "opening_type=OPEN_REJECTION_REVERSE/phase=B/day_type=*(FORMING)/rel_bias=with"]
for P in PATHS:
    buckets = collections.defaultdict(list)
    for f in sorted(glob.glob("harness_out/t466/t529b_2026-*.json")):
        j = json.load(open(f)); d = os.path.basename(f)[6:16]
        for r in j.get("routes") or []:
            tv = r.get("tree_v3") or {}
            if not isinstance(tv, dict) or tv.get("path") != P or r.get("shadow_only"): continue
            try: e, s = float(r.get("entry")), float(r.get("stop"))
            except (TypeError, ValueError): continue
            if not (1.0 <= abs(e - s) <= 30): continue
            sc = score(d, (r.get("il") or "")[:5], r.get("direction"), e, s)
            if sc is None: continue
            res = r.get("result") or {}
            key = "FIRED" if (res.get("live") or res.get("demo")) else (("gate: " + r["blocked_by"]) if r.get("blocked_by") else ("slot: " + str(r.get("live_blocked_by"))))
            buckets[key].append(sc)
    print("\n== " + P)
    for k, v in sorted(buckets.items(), key=lambda kv: -sum(kv[1])):
        print("   %-32s n=%3d  win %3.0f%%  sum %+8.1f$  per %+6.1f$" % (k, len(v), 100 * sum(1 for x in v if x > 0) / len(v), sum(v), sum(v) / len(v)))
