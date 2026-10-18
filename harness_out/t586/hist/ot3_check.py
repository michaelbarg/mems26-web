#!/usr/bin/env python3
# 18.10 19:0x — why does the DayTypeMachine's 15-min opening read say OPEN_DRIVE on 147/166 OOS sessions?
# Re-runs detect_opening_type's DRIVE rule on the first 3 RTH bars straight from the DB.
import subprocess, collections, sys
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
DB = sys.argv[1] if len(sys.argv) > 1 else "mems26_hist"
SES = sys.argv[2] if len(sys.argv) > 2 else "/Users/michael/mems26_hist/hist_sessions.txt"
sql = ("select (ts at time zone 'America/New_York')::date, to_char(ts at time zone 'America/New_York','HH24:MI'), open,high,low,close "
       "from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'America/New_York')::time between '09:30' and '09:40' order by ts")
raw = subprocess.run([PSQL, "-d", DB, "-Atc", sql], capture_output=True, text=True).stdout.split("\n")
B = collections.defaultdict(list)
for l in raw:
    if not l: continue
    d, t, o, h, lo, c = l.split("|"); B[d].append((t, float(o), float(h), float(lo), float(c)))
sess = open(SES).read().split()
cnt = collections.Counter(); ex = []
for s in sess:
    b = B.get(s)
    if not b or len(b) < 3: cnt["nobars"] += 1; continue
    net = b[-1][4] - b[0][1]; rng = max(x[2] for x in b) - min(x[3] for x in b)
    up = all(x[4] >= x[1] for x in b); dn = all(x[4] <= x[1] for x in b)
    dr = rng > 0 and abs(net) / rng >= 0.7 and (up or dn)
    cnt["DRIVE" if dr else "other"] += 1
    if len(ex) < 4: ex.append((s, b, round(net, 2), round(rng, 2), up, dn))
print(cnt)
for e in ex: print(e)
