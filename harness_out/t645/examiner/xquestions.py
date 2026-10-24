#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Part E — the examiner's questions (xlib.ask) trade by trade, on the missed-move candidates, and (secondary, candidate
level only) on the 2,929 de-duplicated candidates of the 81-session replay (harness_out/t643/tree_rows.json); plus where the
T-643 splits P1–P5 fire on the examined days. Read-only.

  python3 harness_out/t645/examiner/xquestions.py > harness_out/t645/examiner/questions.txt
"""
import os, sys, json, collections, datetime as dt
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git/harness_out/t645/examiner")
sys.path.insert(0, "/Users/michael/Downloads/mems26_web_git")
import xlib

TR = json.load(open(os.path.join(xlib.HERE, "trades_exam.json")))
MS = json.load(open(os.path.join(xlib.HERE, "missed.json")))
EXAM = set(xlib.data()["days"])

print("## 1. the questions on every real trade (demo 19–23.10 + 07.10, live 05–09.10)")
agg = collections.defaultdict(lambda: collections.defaultdict(list))
for r in TR:
    ets = dt.datetime.fromisoformat([t for t in xlib.data()["trades"] if t["id"] == r["id"]][0]["entry_ts"])
    f = xlib.features(r["day"], ets, r["dir"], r["entry"])
    q = xlib.ask(f)
    v = r["verdict"].get("v") or "?"
    grp = "correct" if v == "correct" else "wrong"
    for x in q:
        agg[x][grp].append(r["id"])
    print("#%s %s %s %-22s %-5s %-8s %-28s state %-4s(%s) pos %.2f A %-16s turn_rel %-7s edge(s/va) %s/%s rev %s clx %s d3 %+.0f/%0.f → %s" % (
        r["id"], r["day"][5:], r["hm"], r["pat"][:22], r["dir"], (str(r["pnl"]) if r["pnl"] is not None else "—"), v + ("/" + r["verdict"]["p"] if r["verdict"].get("p") else ""),
        f["state"], f["rel"], f["pos"], f["ruleA"], f["turn_rel"], f["sess_edge"], f["va_edge"], f["rev_bar"], f["climax"], f["d3"], f["med"], ",".join(q) or "עובר"))
print("\nסיכום לפי שאלה (עסקאות אמיתיות):")
for x in xlib.QUESTIONS:
    print("  %s · חוסמת שגויות %d %s · הורגת נכונות %d %s" % (x, len(agg[x]["wrong"]), agg[x]["wrong"], len(agg[x]["correct"]), agg[x]["correct"]))
allq = set(); killed = set()
for r in TR:
    pass

print("\n## 2. the missed-move candidates: blocked by the system, passed by the questions, and their bar label")
c = collections.Counter(); let = []
for m in MS:
    if m["mode"] != "shadow" or m["label"] is None:
        continue
    passed = not m["q"]
    sysblk = bool(m["blocked"])
    c[(sysblk, passed, m["label"])] += 1
    if sysblk and passed and m["label"] == "good":
        let.append(m)
for k, n in sorted(c.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
    print("  system_blocked=%s questions_pass=%s label=%s : %d" % (k[0], k[1], k[2], n))
print("  good candidates the system blocked and the questions would pass:")
for m in let:
    print("    %s %s %-22s %-5s @%s R %.2f blocked=%s state %s pos %s" % (m["day"][5:], m["hm"], m["pat"][:22], m["dir"], m["entry"], m["R"] or 0, m["blocked"], m["state"], m["pos"]))

# ── 3. the 81 sessions (secondary): every de-duplicated candidate with its label ────────────────────────────
xlib.use_bars(os.path.join(xlib.HERE, "bars81.json"))
rows = json.load(open("/Users/michael/Downloads/mems26_web_git/harness_out/t643/tree_rows.json"))["rows"]
D81 = xlib.rth_days()
stat = collections.defaultdict(collections.Counter); n_ok = 0; per_day = collections.defaultdict(list)
ent = {}
for r in rows:
    if r["day"] not in D81:
        continue
    ts = dt.datetime.fromisoformat(r["ts"])
    # the entry price is not in tree_rows: take it from the replay route (same ts/pattern/dir)
    key = (r["day"], r["ts"], r["pat"], r["dir"])
    ent[key] = None
by_day = collections.defaultdict(list)
for r in rows:
    by_day[r["day"]].append(r)
for day, rs in by_day.items():
    if day not in D81:
        continue
    cands = xlib.replay_candidates(day)
    idx = collections.defaultdict(list)
    for c_ in cands:
        idx[(c_["pat"], c_["dir"])].append(c_)
    for r in rs:
        ts = dt.datetime.fromisoformat(r["ts"])
        cc = min(idx.get((r["pat"], r["dir"]), []), key=lambda c_: abs((c_["ts"] - ts).total_seconds()), default=None)
        if cc is None or abs((cc["ts"] - ts).total_seconds()) > 60 or cc["entry"] is None:
            continue
        f = xlib.features(day, ts, r["dir"], cc["entry"])
        if not f:
            continue
        n_ok += 1
        q = xlib.ask(f)
        r["_q"] = q; r["_f"] = dict(state=f["state"], rel=f["rel"], pos=round(f["pos"], 2))
        leaf = r["leaf"]
        for x in (q or ["—"]):
            stat[(leaf, x)][r["lab"]] += 1
        stat[(leaf, "ALL")][r["lab"]] += 1
        stat[(leaf, "rel=" + f["rel"])][r["lab"]] += 1
        if not q:
            stat[(leaf, "PASS")][r["lab"]] += 1
print("\n## 3. 81 sessions — candidate level (secondary): labelled candidates with an entry %d" % n_ok)
for leaf in ("TAKE", "SKIP", "SHADOW"):
    for x in ("ALL", "rel=with", "rel=BAL", "rel=against") + xlib.QUESTIONS + ("PASS",):
        cc = stat.get((leaf, x))
        if not cc:
            continue
        n = sum(cc.values())
        print("  %-6s %-12s n=%4d good %3d (%2.0f%%) bad %3d (%2.0f%%) flat %3d" % (leaf, x, n, cc["good"], 100.0 * cc["good"] / n, cc["bad"], 100.0 * cc["bad"] / n, cc["flat"]))

print("\n## 4. the T-643 splits P1–P5 on the examined sessions (candidate level, tree_rows) and what the questions say")
SPL = {
    "P1": lambda r: r["fam"] == "TAKE:take_location" and r["f"].get("opening_type") != "OPEN_AUCTION_IN",
    "P2": lambda r: r["fam"] == "TAKE:failed_ext|phase=C" and r["f"].get("ruleA") == "accepted_against",
    "P3": lambda r: r["fam"] == "TAKE:kind=EDGE_FADE|phase=B" and r["f"].get("pos_hour") == "edge",
    "P4": lambda r: r["fam"] == "TAKE:take_with_extension" and r["f"].get("turn_rel") == "none",
    "P5": lambda r: r["leaf"] == "TAKE" and r["f"].get("phase") == "D",
}
for p, fn in SPL.items():
    hit = [r for r in rows if r["day"] in EXAM and fn(r)]
    cc = collections.Counter(r["lab"] for r in hit)
    agree = collections.Counter(("questions refuse" if r.get("_q") else "questions pass") + "/" + r["lab"] for r in hit)
    print("  %s fires on %d candidates (examined days): %s · %s" % (p, len(hit), dict(cc), dict(agree)))
    for r in hit:
        print("     %s %s %-22s %-5s %-28s lab %-5s → questions %s %s" % (r["day"][5:], r["ts"][11:16], r["pat"][:22], r["dir"], r["fam"][5:33], r["lab"],
              ",".join(r.get("_q") or []) or "pass", r.get("_f")))
