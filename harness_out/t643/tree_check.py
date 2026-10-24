#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-643 · how far to trust the tree map (input: tree_map.py --rows harness_out/t643/tree_rows.json).

1. The tree as a whole: good% of the TAKE leaves vs the SKIP leaves (all / each half of the period), TAKE fired vs blocked,
   and three cross-leaf features (rule A, position in the last hour's range, tested) over all TAKE candidates.
2. Walk-forward: splits found on the first 2/3 of the sessions only, then measured on the last 1/3 that the search never saw.
3. The full-period splits shown in the doc: distinct days on each side, and a day-block bootstrap of Δ (90% interval) —
   candidates of one day share one price path, so the day, not the candidate, is the unit of evidence.
  python3 harness_out/t643/tree_check.py harness_out/t643/tree_rows.json
"""
import sys, json, random, collections

D = json.load(open(sys.argv[1])); days = D["days"]; rows = D["rows"]
FEATS = ["opening_type", "phase", "day_type", "structure", "pattern", "kind", "direction", "rel_bias", "zone", "prior_zone",
         "poc_side", "value_migration", "edge", "test", "volume", "delta", "turn", "turn_rel", "ruleA", "with_accepted",
         "pos_hour", "tested", "hour"]
half = days[len(days) // 2]


def gp(rs):
    return (sum(1 for r in rs if r["lab"] == "good") / len(rs)) if rs else float("nan")


def line(name, rs):
    c = collections.Counter(r["lab"] for r in rs)
    h1 = [r for r in rs if r["day"] < half]; h2 = [r for r in rs if r["day"] >= half]
    print("%-34s n=%4d good=%3.0f%% bad=%3.0f%% flat=%3.0f%% · halves %3.0f%% / %3.0f%% · days %d" % (
        name, len(rs), 100 * gp(rs), 100 * c["bad"] / max(len(rs), 1), 100 * c["flat"] / max(len(rs), 1),
        100 * gp(h1), 100 * gp(h2), len(set(r["day"] for r in rs))))


print("sessions %d (%s..%s) · labelled candidates %d · halves split at %s" % (len(days), days[0], days[-1], len(rows), half))
print("\n## 1. the tree as a whole")
T = [r for r in rows if r["leaf"] == "TAKE"]; S = [r for r in rows if r["leaf"] != "TAKE"]
line("ALL", rows); line("TAKE leaves", T); line("SKIP leaves", S)
line("SKIP without time_cutoff", [r for r in S if r["lid"] != "time_cutoff"])
line("SKIP time_cutoff (hour > 21)", [r for r in S if r["lid"] == "time_cutoff"])
line("TAKE · fired", [r for r in T if r["outcome"] != "blocked"])
line("TAKE · blocked after the tree", [r for r in T if r["outcome"] == "blocked"])
for ph in ("B", "C", "D"):
    line("TAKE · phase=%s" % ph, [r for r in T if str(r["f"].get("phase")) == ph])
for ft in ("ruleA", "pos_hour", "tested", "with_accepted"):
    for v, _ in collections.Counter(str(r["f"].get(ft)) for r in T).most_common():
        line("TAKE · %s=%s" % (ft, v), [r for r in T if str(r["f"].get(ft)) == v])


def splits(rs, mn, hcut):
    res = []
    for ft in FEATS:
        for v in set(str(r["f"].get(ft)) for r in rs):
            A = [r for r in rs if str(r["f"].get(ft)) == v]; B = [r for r in rs if str(r["f"].get(ft)) != v]
            if len(A) < mn or len(B) < mn:
                continue
            d = gp(A) - gp(B); ok = True
            for part in ((lambda r: r["day"] < hcut), (lambda r: r["day"] >= hcut)):
                A2 = [r for r in A if part(r)]; B2 = [r for r in B if part(r)]
                if len(A2) < 5 or len(B2) < 5 or ((gp(A2) - gp(B2)) > 0) != (d > 0):
                    ok = False
            res.append(dict(feat=ft, val=v, nA=len(A), d=d, ok=ok))
    res.sort(key=lambda x: (-int(x["ok"]), -abs(x["d"])))
    return res


print("\n## 2. walk-forward: found on the first 2/3 of the sessions, measured on the last 1/3")
cut = days[(2 * len(days)) // 3]
disc_days = [d for d in days if d < cut]; hcut = disc_days[len(disc_days) // 2]
print("discovery %s..%s (%d sessions) · holdout %s..%s (%d sessions)" % (
    disc_days[0], disc_days[-1], len(disc_days), cut, days[-1], len([d for d in days if d >= cut])))
fam = collections.defaultdict(list)
for r in rows:
    fam[r["fam"]].append(r)
kept = tot = 0; dsum = 0.0
for k, rs in sorted(fam.items(), key=lambda kv: -len(kv[1])):
    disc = [r for r in rs if r["day"] < cut]; hold = [r for r in rs if r["day"] >= cut]
    if len(disc) < 30 or len(hold) < 15:
        continue
    top = [x for x in splits(disc, 10, hcut) if x["ok"]][:3]
    print("\n%s  discovery n=%d good=%.0f%% · holdout n=%d good=%.0f%%" % (k, len(disc), 100 * gp(disc), len(hold), 100 * gp(hold)))
    for x in top:
        A = [r for r in hold if str(r["f"].get(x["feat"])) == x["val"]]; B = [r for r in hold if str(r["f"].get(x["feat"])) != x["val"]]
        if len(A) < 3 or len(B) < 3:
            print("   %s=%s: discovery Δ%+.0f (n=%d) · holdout too thin (n=%d)" % (x["feat"], x["val"], 100 * x["d"], x["nA"], len(A)))
            continue
        dh = gp(A) - gp(B); same = (dh > 0) == (x["d"] > 0); tot += 1; kept += int(same); dsum += dh * (1 if x["d"] > 0 else -1)
        print("   %s=%s: discovery Δ%+.0f (n=%d) · holdout Δ%+.0f (n=%d, good %.0f%% vs %.0f%%) · %s" % (
            x["feat"], x["val"], 100 * x["d"], x["nA"], 100 * dh, len(A), 100 * gp(A), 100 * gp(B), "HOLDS" if same else "flips"))
print("\nwalk-forward summary: %d of %d discovered splits keep their sign on the holdout · mean holdout Δ in the found direction %+.1f pts" % (
    kept, tot, 100 * dsum / max(tot, 1)))

print("\n## 3. the full-period splits shown in the doc · day-block bootstrap (1000) of Δ, 90% interval")
SHOW = [("TAKE:failed_ext|phase=C", "ruleA", "accepted_against"), ("TAKE:failed_ext|phase=C", "zone", "near_val"),
        ("TAKE:failed_ext|phase=C", "opening_type", "OPEN_AUCTION_OUT"), ("TAKE:with_hint|phase=C", "day_type", "Trend_Normal"),
        ("TAKE:with_hint|phase=C", "value_migration", "inside"), ("TAKE:with_hint|phase=C", "kind", "REVERSAL"),
        ("TAKE:with_hint|phase=C", "pattern", "GB100"), ("TAKE:take_location", "opening_type", "OPEN_AUCTION_IN"),
        ("TAKE:take_location", "day_type", "Neutral_Extreme"), ("TAKE:take_location", "structure", "two_sided"),
        ("TAKE:take_location", "turn", "down"), ("TAKE:take_with_extension", "turn", "none"),
        ("TAKE:kind=EDGE_FADE|phase=B", "pos_hour", "edge"), ("TAKE:kind=EDGE_FADE|phase=B", "turn_rel", "with"),
        ("SKIP:location", "day_type", "Normal"), ("SKIP:location", "pos_hour", "edge"), ("SKIP:kind", "pos_hour", "middle")]
rnd = random.Random(643)
for k, ft, v in SHOW:
    rs = fam.get(k) or []
    A = [r for r in rs if str(r["f"].get(ft)) == v]; B = [r for r in rs if str(r["f"].get(ft)) != v]
    if not A or not B:
        print("%s · %s=%s: empty" % (k, ft, v)); continue
    byday = collections.defaultdict(list)
    for r in rs:
        byday[r["day"]].append(r)
    dl = sorted(byday); ds = []
    for _ in range(1000):
        pick = [rnd.choice(dl) for _ in dl]
        A2 = [r for d in pick for r in byday[d] if str(r["f"].get(ft)) == v]
        B2 = [r for d in pick for r in byday[d] if str(r["f"].get(ft)) != v]
        if A2 and B2:
            ds.append(gp(A2) - gp(B2))
    ds.sort(); lo = ds[int(0.05 * len(ds))]; hi = ds[int(0.95 * len(ds)) - 1]
    topd = collections.Counter(r["day"] for r in A).most_common(2)
    print("%s · %s=%s: n=%d on %d days (top-2 days hold %d) good %.0f%% vs %.0f%% · Δ%+.0f · 90%% [%+.0f, %+.0f] · %s" % (
        k, ft, v, len(A), len(set(r["day"] for r in A)), sum(c for _, c in topd), 100 * gp(A), 100 * gp(B),
        100 * (gp(A) - gp(B)), 100 * lo, 100 * hi, "CLEAR" if (lo > 0 or hi < 0) else "crosses 0"))


print("\n## 4. the same splits by period: first 2/3 (to %s) vs last 1/3 — picked on the full period, so a consistency view, not a clean test" % disc_days[-1])
for k, ft, v in SHOW:
    rs = fam.get(k) or []; out = []
    for part in ((lambda r: r["day"] < cut), (lambda r: r["day"] >= cut)):
        P = [r for r in rs if part(r)]
        A = [r for r in P if str(r["f"].get(ft)) == v]; B = [r for r in P if str(r["f"].get(ft)) != v]
        out.append("n=%d %.0f%% vs %.0f%% Δ%+.0f" % (len(A), 100 * gp(A), 100 * gp(B), 100 * (gp(A) - gp(B))) if (A and B) else "n=%d" % len(A))
    print("%s · %s=%s: early %s · late %s" % (k, ft, v, out[0], out[1]))
for k in ("TAKE:take_with_extension", "TAKE:with_hint|phase=C", "TAKE:failed_ext|phase=C"):
    rs = fam.get(k) or []
    for ft in ("turn_rel", "direction"):
        for v, _ in collections.Counter(str(r["f"].get(ft)) for r in rs).most_common():
            line("%s · %s=%s" % (k.replace("TAKE:", ""), ft, v), [r for r in rs if str(r["f"].get(ft)) == v])


print("\n## 5. the five proposed splits (P1–P5), alone and together · good/bad per period · fired = what the replay executed")
P = {
    "P1 take_location only on OPEN_AUCTION_IN": lambda r: r["fam"] == "TAKE:take_location" and r["f"].get("opening_type") != "OPEN_AUCTION_IN",
    "P2 failed_ext C not against an accepted ext (rule A)": lambda r: r["fam"] == "TAKE:failed_ext|phase=C" and r["f"].get("ruleA") == "accepted_against",
    "P3 EDGE_FADE B not at the last hour's extreme": lambda r: r["fam"] == "TAKE:kind=EDGE_FADE|phase=B" and r["f"].get("pos_hour") == "edge",
    "P4 with the extension only after a turn": lambda r: r["fam"] == "TAKE:take_with_extension" and r["f"].get("turn_rel") == "none",
    "P5 phase D: no d_with_extension / failed_ext D": lambda r: r["fam"] in ("TAKE:d_with_extension", "TAKE:failed_ext|phase=D"),
}


def gb(rs):
    c = collections.Counter(r["lab"] for r in rs); n = max(len(rs), 1)
    return "n=%4d good %3.0f%% bad %3.0f%%" % (len(rs), 100 * c["good"] / n, 100 * c["bad"] / n)


for name, fn in P.items():
    rs = [r for r in T if fn(r)]
    fi = [r for r in rs if r["outcome"] != "blocked"]
    print("%-52s all %s · early %s · late %s · fired %s" % (name, gb(rs), gb([r for r in rs if r["day"] < cut]),
                                                           gb([r for r in rs if r["day"] >= cut]), gb(fi)))
anyp = lambda r: any(fn(r) for fn in P.values())
for nm, sel in (("TAKE as today", lambda r: True), ("removed by P1–P5", anyp), ("TAKE after P1–P5", lambda r: not anyp(r))):
    rs = [r for r in T if sel(r)]; fi = [r for r in rs if r["outcome"] != "blocked"]
    print("%-52s all %s · early %s · late %s · fired %s" % (nm, gb(rs), gb([r for r in rs if r["day"] < cut]),
                                                           gb([r for r in rs if r["day"] >= cut]), gb(fi)))
