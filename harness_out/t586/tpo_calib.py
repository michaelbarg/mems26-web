#!/usr/bin/env python3
"""T-586 — calibrate a TPO builder (30-min letters on 5-min bars) against the live v9_tpo_history snapshots.
Reads v9_bars_5min_woodies + v9_tpo_history for one session (IL date) via psql. Read-only."""
import subprocess, sys, collections, datetime
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
D = sys.argv[1] if len(sys.argv) > 1 else "2026-10-08"
INC = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
def q(sql):
    return [l.split("|") for l in subprocess.run([PSQL, "-d", "mems26", "-Atc", sql], capture_output=True, text=True).stdout.splitlines() if l]
bars = q(f"select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), high, low, volume from v9_bars_5min_woodies where symbol='MES' "
         f"and (ts at time zone 'Asia/Jerusalem')::date='{D}' and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts")
snaps = q(f"select to_char(created_at at time zone 'Asia/Jerusalem','HH24:MI'), poc, vah, val, ib_high, ib_low from v9_tpo_history "
          f"where (created_at at time zone 'Asia/Jerusalem')::date='{D}' order by created_at")
def profile(bars_upto, vamode):
    # letters: one per 30-min bracket; a price level gets the letter if any 5-min bar of that bracket spans it
    lv = collections.defaultdict(set); vol = collections.defaultdict(float)
    for il, h, l, v in bars_upto:
        hh, mm = int(il[:2]), int(il[3:]); br = (hh * 60 + mm - (16 * 60 + 30)) // 30
        p = round(float(l) / INC) * INC; levels = []
        while p <= float(h) + 1e-9:
            lv[round(p, 2)].add(br); levels.append(round(p, 2)); p += INC
        for lp in levels: vol[lp] += float(v or 0) / max(1, len(levels))
    cnt = {p: len(s) for p, s in lv.items()} if vamode != "volume" else {p: vol[p] for p in vol}
    if vamode == "volume": vamode = "single"
    if not cnt: return None
    tot = sum(cnt.values()); poc = max(sorted(cnt), key=lambda p: (cnt[p], -abs(p - (max(cnt) + min(cnt)) / 2)))
    # value area 70%: expand from POC taking the larger of the two neighbours (pairs, Dalton)
    lo = hi = poc; acc = cnt[poc]; prices = sorted(cnt)
    while acc < 0.7 * tot:
        up = [p for p in prices if p > hi][:2]; dn = [p for p in prices if p < lo][-2:]
        su = sum(cnt[p] for p in up); sd = sum(cnt[p] for p in dn)
        if vamode == "pairs":
            if su >= sd and up: hi = up[-1]; acc += su
            elif dn: lo = dn[0]; acc += sd
            else: break
        else:
            u1 = cnt.get(up[0], -1) if up else -1; d1 = cnt.get(dn[-1], -1) if dn else -1
            if u1 >= d1 and up: hi = up[0]; acc += u1
            elif dn: lo = dn[-1]; acc += d1
            else: break
    return poc, hi, lo
for il, poc, vah, val, ibh, ibl in snaps:
    upto = [b for b in bars if b[0] < il]
    if not upto: continue
    for vm in ("pairs", "single", "volume"):
        r = profile(upto, vm)
        print(f"{il} live poc/vah/val {poc}/{vah}/{val} ib {ibh}/{ibl} | {vm:6s} mine {r[0]}/{r[1]}/{r[2]} bars {len(upto)}"
              f" | ib60 {max(float(b[1]) for b in bars[:12])}/{min(float(b[2]) for b in bars[:12])}")
