#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Secondary check only: the examiner's features for every de-duplicated candidate of the 81-session replay
(harness_out/t643/tree_rows.json, label = +1R before the candidate's own stop) → cand81.json; then the label split by
state relation × location × phase. Read-only.
  python3 harness_out/t645/examiner/xcand81.py > harness_out/t645/examiner/cand81.txt
"""
import os, sys, json, collections, datetime as dt
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
import xlib

xlib.use_bars(os.path.join(xlib.HERE, "bars81.json"))
rows = json.load(open("/Users/michael/Downloads/mems26_web_git/harness_out/t643/tree_rows.json"))["rows"]
D81 = xlib.rth_days()
by_day = collections.defaultdict(list)
for r in rows:
    by_day[r["day"]].append(r)
OUT = []
for day, rs in sorted(by_day.items()):
    if day not in D81:
        continue
    cands = xlib.replay_candidates(day)
    idx = collections.defaultdict(list)
    for c in cands:
        idx[(c["pat"], c["dir"])].append(c)
    for r in rs:
        ts = dt.datetime.fromisoformat(r["ts"])
        cc = min(idx.get((r["pat"], r["dir"]), []), key=lambda c: abs((c["ts"] - ts).total_seconds()), default=None)
        if cc is None or abs((cc["ts"] - ts).total_seconds()) > 60 or cc["entry"] is None:
            continue
        f = xlib.features(day, ts, r["dir"], cc["entry"])
        if not f:
            continue
        q = xlib.ask(f)
        OUT.append(dict(day=day, ts=r["ts"], il=ts.astimezone(xlib.IL).strftime("%H:%M"), pat=r["pat"], dir=r["dir"], leaf=r["leaf"], fam=r["fam"],
                        lab=r["lab"], blocked=r.get("blocked"), outcome=r.get("outcome"), entry=cc["entry"], stop=cc["stop"],
                        R=abs(cc["entry"] - cc["stop"]) if cc["stop"] else None, q=q,
                        f={k: (round(v, 3) if isinstance(v, float) else v) for k, v in f.items()}, tf=r["f"]))
json.dump(OUT, open(os.path.join(xlib.HERE, "cand81.json"), "w"), ensure_ascii=False, default=str)


def st(rs):
    c = collections.Counter(r["lab"] for r in rs); n = len(rs)
    return "n=%4d good %3d (%2.0f%%) bad %3d (%2.0f%%) flat %3d" % (n, c["good"], 100.0 * c["good"] / max(n, 1), c["bad"], 100.0 * c["bad"] / max(n, 1), c["flat"])


print("candidates with features:", len(OUT))
for leaf in ("TAKE", "ALL"):
    S = [o for o in OUT if leaf == "ALL" or o["leaf"] == leaf]
    print("\n## leaf=%s  %s" % (leaf, st(S)))
    for rel in ("with", "BAL", "against"):
        for ph in ("B", "C", "D"):
            for pl in ("edge", "middle", "far"):
                X = [o for o in S if o["f"]["rel"] == rel and o["f"]["phase"] == ph and o["f"]["pos_lab"] == pl]
                if len(X) >= 8:
                    print("  rel=%-7s phase=%s pos=%-6s %s" % (rel, ph, pl, st(X)))
    print("  -- against: the ש1 exception parts")
    A = [o for o in S if o["f"]["rel"] == "against"]
    for nm, fn in (("turn_rel edge/with", lambda o: o["f"]["turn_rel"] in ("edge", "with")),
                   ("day-edge & A!=acc", lambda o: (o["f"]["sess_edge"] or bool(o["f"]["va_edge"])) and o["f"]["ruleA"] != "accepted_against"),
                   ("A accepted", lambda o: o["f"]["ruleA"] == "accepted_against"),
                   ("neither (ש1 refuses)", lambda o: "ש1" in o["q"])):
        X = [o for o in A if fn(o)]
        print("  against %-22s %s" % (nm, st(X)))
    print("  -- effort (Σdelta3 ≥ 3×median against the trade)")
    for rel in ("against", "BAL"):
        X = [o for o in S if o["f"]["rel"] == rel and o["f"]["eff_against"]]
        Y = [o for o in S if o["f"]["rel"] == rel and not o["f"]["eff_against"]]
        print("  rel=%-7s effort-against %s | not %s" % (rel, st(X), st(Y)))
