#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-517 (29.09) SCREEN — the second direction change of 28.09: the IB broke down (17:35), the price came back INTO the
IB at 19:20-19:25 and ran +43 pts, while every long 19:00-19:35 died on tree:bias (the session hint stayed SHORT).
Candidate-level only (the doctrine: a screen, not a verdict — only the day-total replay decides).

State from CLOSED bars at the decision time (IB = the first 12 RTH bars, 16:30-17:25 IL):
  failed_down — after the IB the low extended ≥ need below IB low (need = max(2, 0.10×IB range), the same threshold as
                decision_tree.structure_of) AND the last closed bar closed back above IB low (back inside the IB)
  failed_up   — the mirror;  returning_* — extended, retraced ≥ half of the extension, not yet inside the IB
(1) every gateway decision of <TAG> placed in that state, simulated independently at 1.5R on its own stop (first touch,
EOD close, 1 contract, $2.60 RT — gate_audit's model), unique per (session, pattern, direction, entry, stop);
(2) the state as its own producer: at the first close back inside the IB, enter the return direction at the next open,
stop 1 tick beyond the lowest low (highest high) of the last 3 closed bars, 1.5R.
usage: ib_return_screen.py [TAG=t515ref]"""
import collections, datetime as dt, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all

TAG = sys.argv[1] if len(sys.argv) > 1 else "t515ref"; COMM = 2.60; IL = dt.timezone(dt.timedelta(hours=3))


def bars_of(d):
    return [dict(t=r["t"], m=int(r["t"][:2]) * 60 + int(r["t"][3:]), o=float(r["o"]), h=float(r["h"]), l=float(r["l"]),
                 c=float(r["c"])) for r in read_all(
        """select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI') t, open o, high h, low l, close c
        from v9_bars_5min_woodies where symbol='MES' and (ts at time zone 'Asia/Jerusalem')::date = :d
        and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '22:55' order by ts""", {"d": d})]


def state(B, m):
    """IB-return state from the bars CLOSED at minute-of-day m (IL)."""
    closed = [b for b in B if b["m"] + 5 <= m]
    if len(closed) < 13:
        return "ib_forming", None
    ib = closed[:12]; hi = max(b["h"] for b in ib); lo = min(b["l"] for b in ib); need = max(2.0, 0.10 * (hi - lo))
    post = closed[12:]; last = closed[-1]["c"]
    ext_dn = lo - min(b["l"] for b in post); ext_up = max(b["h"] for b in post) - hi
    info = dict(ib_hi=hi, ib_lo=lo, ext_dn=round(ext_dn, 2), ext_up=round(ext_up, 2))
    if ext_dn >= need and ext_up < need:
        if last > lo:
            return "failed_down", info
        if last >= lo - ext_dn / 2:
            return "returning_down", info
        return "extended_down", info
    if ext_up >= need and ext_dn < need:
        if last < hi:
            return "failed_up", info
        if last <= hi + ext_up / 2:
            return "returning_up", info
        return "extended_up", info
    if ext_up >= need and ext_dn >= need:
        return "two_sided", info
    return "inside", info


def sim(after, short, ep, st, k=1.5):
    R = abs(ep - st)
    if R <= 0:
        return None
    for b in after:
        if (b["h"] >= st) if short else (b["l"] <= st):
            return -R
        if ((ep - b["l"]) if short else (b["h"] - ep)) >= k * R:
            return k * R
    return ((ep - after[-1]["c"]) if short else (after[-1]["c"] - ep)) if after else 0.0


REL = {("failed_down", "LONG"): "WITH the return", ("failed_up", "SHORT"): "WITH the return",
       ("failed_down", "SHORT"): "against the return", ("failed_up", "LONG"): "against the return",
       ("returning_down", "LONG"): "with (returning)", ("returning_up", "SHORT"): "with (returning)"}
agg = collections.defaultdict(lambda: [0, 0, 0.0, set()]); ex = collections.defaultdict(list)
prod = collections.defaultdict(lambda: [0, 0, 0.0]); prod_rows = []
for p in sorted(glob.glob(f"harness_out/t466/{TAG}_2026-*.json")):
    d = p[-15:-5]; j = json.load(open(p)); B = bars_of(d)
    if len(B) < 20:
        continue
    seen = set()
    for g in j.get("gateway_decisions") or []:
        mt = g.get("mfe_track") or {}
        if not mt.get("stop") or not g.get("entry"):
            continue
        t = dt.datetime.fromisoformat(g["ts"]).astimezone(IL); m = t.hour * 60 + t.minute
        key = (g.get("pattern"), g.get("direction"), float(g["entry"]), float(mt["stop"]))
        if key in seen:
            continue
        seen.add(key)
        st, _ = state(B, m); rel = REL.get((st, g.get("direction")))
        if not rel:
            continue
        after = [b for b in B if b["m"] >= m]
        pts = sim(after, g.get("direction") == "SHORT", float(g["entry"]), float(mt["stop"]))
        if pts is None:
            continue
        usd = pts * 5 - COMM
        blk = str(g.get("blocked_by") or g.get("outcome") or "?")
        blk = "tree:bias" if blk == "tree:bias" else ("live" if g.get("outcome") == "live" else ("tree:other" if blk.startswith("tree:") else "gate/shadow"))
        for k in ((rel, g.get("direction"), "ALL"), (rel, g.get("direction"), blk)):
            a = agg[k]; a[0] += 1; a[1] += pts > 0; a[2] += usd; a[3].add(d)
        if d == "2026-09-28":
            ex[(rel, blk)].append(f"{t:%H:%M} {g.get('pattern')} {g.get('direction')} @{g['entry']} stop {mt['stop']} ⇒ {usd:+.2f}$")
    # (2) the state as its own producer
    prev = None
    for i in range(13, len(B) - 1):
        st, info = state(B, B[i]["m"])
        if st in ("failed_down", "failed_up") and prev != st:
            short = st == "failed_up"; e = B[i]["o"]; last3 = B[i - 3:i]
            stop = (max(b["h"] for b in last3) + 0.25) if short else (min(b["l"] for b in last3) - 0.25)
            pts = sim(B[i:], short, e, stop)
            if pts is not None and 0.5 <= abs(e - stop) <= 20:
                usd = pts * 5 - COMM; k = ("SHORT after failed up" if short else "LONG after failed down")
                prod[k][0] += 1; prod[k][1] += pts > 0; prod[k][2] += usd
                prod_rows.append((d, B[i]["t"], k, e, round(abs(e - stop), 2), round(usd, 2)))
        prev = st
print(f"(1) gateway decisions of {TAG} in the IB-return states — independent 1.5R sim, unique candidates")
for k, (n, w, s, days) in sorted(agg.items()):
    print(f"   {k[0]:20s} {k[1]:5s} {k[2]:12s} n={n:4d} win {100 * w / n:3.0f}% Σ{s:+9.2f}$  days {len(days)}")
print("   28.09:")
for k, v in ex.items():
    for x in v:
        print(f"      [{k[0]} · {k[1]}] {x}")
print("(2) the state as its own producer (first close back inside the IB ⇒ next open, stop beyond the last 3 bars, 1.5R)")
for k, (n, w, s) in sorted(prod.items()):
    print(f"   {k}: n={n} win {100 * w / max(1, n):.0f}% Σ{s:+.2f}$")
for r in prod_rows:
    if r[0] >= "2026-09-20":
        print("     ", r)
