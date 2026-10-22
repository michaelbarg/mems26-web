#!/usr/bin/env python3
"""tree_readiness_matrix.py — T-631 (22.10): what the live decision tree does for every opening type × day type × phase.

Read-only. Walks config/decision_tree_v3.<version>.yaml (the loader's `root`) with opening_type / phase / day_type
fixed and enumerates every leaf still reachable through the remaining splits (structure, pattern, kind, direction,
rel_bias, zone, edge, hour…). A cell whose only leaf is `stand_down` has no doctrine row — the system is not "ready"
for that circumstance in the sense Michael asked on 22.10 ("שבכל סוג יום וכל סוג פתיחה המערכת מוכנה").
Usage: python3 scripts/tree_readiness_matrix.py [config/decision_tree_v3.3.4.0.yaml] [--json out.json] [--md out.md]
"""
import json, sys, collections
import yaml

OPENINGS = ["OPEN_DRIVE", "OPEN_TEST_DRIVE", "OPEN_REJECTION_REVERSE", "OPEN_AUCTION_IN", "OPEN_AUCTION_OUT", "UNKNOWN"]
DAY_TYPES = ["FORMING", "Trend_Normal", "Trend_DD", "Variation", "Normal_Variation", "Normal", "Neutral_Center",
             "Neutral_Extreme", "Nontrend", "Nonconviction"]
PHASES = ["A", "B", "C", "D"]
HOUR = {"A": 16, "B": 17, "C": 18, "D": 21}


def pick_branch(branches, value):
    if value in branches:
        return value
    for k in branches:
        if "|" in str(k) and value in str(k).split("|"):
            return k
    return "*" if "*" in branches else None


def walk(node, fixed, path, out):
    if not isinstance(node, dict):
        return
    if "leaf" in node:
        out.append({"leaf": node.get("leaf"), "id": node.get("id"), "path": path, "measured": node.get("measured"),
                    "note": node.get("note")})
        return
    split = node.get("split")
    branches = node.get("branches") or {}
    if split in fixed:
        key = pick_branch(branches, str(fixed[split]))
        if key is None:
            out.append({"leaf": "NONE", "id": "no_branch_%s" % split, "path": path, "measured": None, "note": None})
            return
        walk(branches[key], fixed, path + ["%s=%s" % (split, key)], out)
    else:
        for key, child in branches.items():
            walk(child, fixed, path + ["%s=%s" % (split, key)], out)


def summarize(leaves):
    c = collections.Counter(l["leaf"] for l in leaves)
    takes = [l for l in leaves if l["leaf"] == "TAKE"]
    kinds = sorted({seg.split("=", 1)[1] for l in takes for seg in l["path"] if seg.startswith("kind=")})
    pats = sorted({seg.split("=", 1)[1] for l in takes for seg in l["path"] if seg.startswith("pattern=")})
    ids = sorted({l["id"] for l in leaves if l["leaf"] == "SKIP" and l["id"]})
    meas_n = sum((l.get("measured") or {}).get("n", 0) or 0 for l in takes if isinstance(l.get("measured"), dict))
    meas_usd = sum((l.get("measured") or {}).get("usd", 0) or 0 for l in takes if isinstance(l.get("measured"), dict))
    only_stand_down = c.get("TAKE", 0) == 0 and c.get("SHADOW", 0) == 0 and ids and set(ids) <= {"stand_down", "time_cutoff"}
    return {"take": c.get("TAKE", 0), "skip": c.get("SKIP", 0), "shadow": c.get("SHADOW", 0), "none": c.get("NONE", 0),
            "take_kinds": kinds, "take_patterns": pats, "skip_ids": ids, "measured_n": meas_n, "measured_usd": round(meas_usd, 2),
            "status": "stand_down" if only_stand_down else ("ready" if c.get("TAKE", 0) else "skip_only")}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tree_path = args[0] if args else "config/decision_tree_v3.3.4.0.yaml"
    y = yaml.safe_load(open(tree_path))
    root = y["root"]
    out = {"tree": tree_path, "version": y.get("version"), "cells": {}}
    rows = []
    for ot in OPENINGS:
        for ph in PHASES:
            for dt in DAY_TYPES:
                leaves = []
                walk(root, {"opening_type": ot, "phase": ph, "day_type": dt, "hour": HOUR[ph]}, [], leaves)
                s = summarize(leaves)
                out["cells"]["%s|%s|%s" % (ot, ph, dt)] = s
                rows.append((ot, ph, dt, s))
    md = ["# מוכנות העץ %s לכל סוג-פתיחה × שלב × סוג-יום (T-631, 22.10)" % y.get("version"), "",
          "סטטוס: **ready** = יש לפחות עלה TAKE · **skip_only** = יש שורות אבל כולן SKIP · **stand_down** = אין שורת-דוקטרינה (העץ עומד בצד).",
          "עמודת TAKE = מספר העלים המאשרים; kinds = סוגי-הכניסה המותרים; measured = n/usd מהעלים (tree_measure).", ""]
    for ot in OPENINGS:
        md.append("## %s" % ot)
        md.append("| שלב | סוג-יום | סטטוס | TAKE | SKIP | SHADOW | kinds ב-TAKE | SKIP ids | measured n / usd |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for (o, ph, dt, s) in rows:
            if o != ot:
                continue
            md.append("| %s | %s | %s | %d | %d | %d | %s | %s | %d / %+.0f |" % (
                ph, dt, s["status"], s["take"], s["skip"], s["shadow"], ", ".join(s["take_kinds"]) or "—",
                ", ".join(s["skip_ids"]) or "—", s["measured_n"], s["measured_usd"]))
        md.append("")
    # totals
    st = collections.Counter(s["status"] for (_, _, _, s) in rows)
    md.append("**סיכום:** %d תאים · ready %d · skip_only %d · stand_down %d" % (len(rows), st["ready"], st["skip_only"], st["stand_down"]))
    text = "\n".join(md)
    for i, a in enumerate(sys.argv):
        if a == "--json":
            json.dump(out, open(sys.argv[i + 1], "w"), ensure_ascii=False, indent=1)
        if a == "--md":
            open(sys.argv[i + 1], "w", encoding="utf-8").write(text + "\n")
    print(text[-1600:])


if __name__ == "__main__":
    main()
