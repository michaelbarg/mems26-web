#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-643 · the proposed tree splits, trade by trade: which of the 60 reviewed trades (verdicts.json) each split would have
blocked, and was that trade correct or wrong by the Dalton review. Read-only (JSON + SELECT).

Each real trade is matched to the replay candidate (tree_rows.json, live config) of the same day, pattern and direction,
nearest in time within 30 minutes; the split is read off that candidate's leaf and features.
  python3 harness_out/t643/trades_vs_splits.py
"""
import os, sys, json, collections, datetime as dt
ROOT = "/Users/michael/Downloads/mems26_web_git"
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
ET = ZoneInfo("America/New_York"); IL = ZoneInfo("Asia/Jerusalem")

V = json.load(open("harness_out/t643/verdicts.json"))
ver = {}
for grp in ("demo", "live"):
    for k, x in V[grp].items():
        ver[int(k)] = dict(x, grp=grp)
T = read_all("""select id, mode, direction, entry_ts, entry_price, stop, pnl_usd, pattern_id_at_entry pat
 from v9_trades where id = any(:ids) order by entry_ts""", {"ids": list(ver)})
R = json.load(open("harness_out/t643/tree_rows.json"))["rows"]
idx = collections.defaultdict(list)
for r in R:
    idx[(r["day"], r["pat"], r["dir"])].append(r)

SPLITS = {
    "P1": ("take_location only when the open is inside yesterday's range",
           lambda r: r["fam"] == "TAKE:take_location" and r["f"].get("opening_type") != "OPEN_AUCTION_IN"),
    "P2": ("failed_ext C: not against an accepted extension (rule A)",
           lambda r: r["fam"] == "TAKE:failed_ext|phase=C" and r["f"].get("ruleA") == "accepted_against"),
    "P3": ("EDGE_FADE B: not at the extreme of the last hour",
           lambda r: r["fam"] == "TAKE:kind=EDGE_FADE|phase=B" and r["f"].get("pos_hour") == "edge"),
    "P4": ("with the extension: only after a turn",
           lambda r: r["fam"] == "TAKE:take_with_extension" and r["f"].get("turn_rel") == "none"),
    "P5": ("no new entries in phase D",
           lambda r: r["leaf"] == "TAKE" and r["f"].get("phase") == "D"),
}
hits = collections.defaultdict(list); unmatched = []; lab_vs_ver = collections.Counter(); per = []
for t in T:
    v = ver[t["id"]]; e = t["entry_ts"]; day = e.astimezone(ET).date().isoformat()
    cs = idx.get((day, t["pat"], t["direction"])) or []
    best = min(cs, key=lambda r: abs((dt.datetime.fromisoformat(r["ts"]) - e).total_seconds()), default=None)
    if best is None or abs((dt.datetime.fromisoformat(best["ts"]) - e).total_seconds()) > 1800:
        unmatched.append(t["id"]); continue
    lab_vs_ver[(v["v"], best["lab"])] += 1
    fl = [k for k, (_, fn) in SPLITS.items() if fn(best)]
    per.append((t, v, best, fl))
    for k in fl:
        hits[k].append((t, v, best))

print("trades %d · matched %d · unmatched %s" % (len(T), len(per), unmatched))
print("\n## the bar label vs the Dalton verdict (matched trades)")
for (vv, lb), n in sorted(lab_vs_ver.items()):
    print("  verdict=%-28s label=%-5s %d" % (vv, lb, n))
print("\n## each split on the reviewed trades")
for k, (desc, _) in SPLITS.items():
    hs = hits.get(k, []); c = collections.Counter(v["v"] for _, v, _ in hs); pnl = sum(float(t["pnl_usd"] or 0) for t, _, _ in hs)
    print("\n%s %s · blocks %d trades: %s · their P&L %+.2f$" % (k, desc, len(hs), dict(c), pnl))
    for t, v, b in hs:
        print("   #%d %s %s %s %s %s · %s%s · label %s · %+.2f$ · %s" % (
            t["id"], v["grp"], t["entry_ts"].astimezone(IL).strftime("%d.%m %H:%M"), t["pat"], t["direction"], b["fam"].replace("TAKE:", ""),
            v["v"], ("/" + v["p"]) if v.get("p") else "", b["lab"], float(t["pnl_usd"] or 0),
            " ".join("%s=%s" % (x, b["f"].get(x)) for x in ("opening_type", "ruleA", "pos_hour", "turn_rel", "phase"))))
print("\n## every matched trade: leaf and verdict")
for t, v, b, fl in per:
    print("#%d %-4s %s %-22s %-5s %-34s %-26s label=%-5s %+8.2f$ %s" % (
        t["id"], v["grp"], t["entry_ts"].astimezone(IL).strftime("%d.%m %H:%M"), t["pat"], t["direction"], b["fam"],
        v["v"] + (("/" + v["p"]) if v.get("p") else ""), b["lab"], float(t["pnl_usd"] or 0), ",".join(fl)))
