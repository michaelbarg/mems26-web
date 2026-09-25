#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tree_measure.py — the nightly measurement of DECISION_TREE_V3: every node and every leaf of the tree gets
its numbers from the replay — how many candidates walked through it, what they went on to do.

Input: harness runs with DECISION_TREE_V3=1 (or shadow) — each route carries `tree_v3` = {leaf, id, path}
(scripts/fwd_harness.py). Every candidate is simulated on the bars with its own stop and a 1.5R target (the
fixed evaluation model: first touch, EOD close, 1 contract, $2.60 RT) — INDEPENDENTLY, so a leaf's Σ$ is the
opinion quality of that leaf, not a portfolio (the day-total harness decides, Michael 24.09). Admitted
candidates also carry the harness's actual trade result (n_live / usd_live).

Outputs:
  config/decision_tree_v3.measured.json                — path → {n, win, usd, n_live, usd_live, source, date}
  render_mobile_relay/static/docs/data/tree_v3.json    — the nested tree with the numbers on every node (the board)
  docs/reports/TREE_V3_MEASURE_<date>.md               — leaves sorted by traffic, the ripe-for-a-split ones marked

  python3 scripts/tree_measure.py [--tag treev3] [--dir harness_out/t466]
"""
import argparse, collections, datetime as dt, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from backend.v9.services import decision_tree as dt3
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); COMM = 2.60; TODAY = dt.datetime.now(IL).date().isoformat()

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="treev3"); ap.add_argument("--dir", default="harness_out/t466")
ap.add_argument("--min-n", type=int, default=30)
args = ap.parse_args()
D = os.path.join(ROOT, args.dir)
files = sorted(glob.glob(os.path.join(D, f"{args.tag}_*.json")))
if not files:
    sys.exit(f"no {args.tag}_*.json in {D}")


def bars_of(d):
    rows = read_all("""select ts, high h, low l, close c from v9_bars_5min_woodies where symbol='MES'
      and (ts at time zone 'Asia/Jerusalem')::date = :d and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by ts""", {"d": d})
    return [dict(ts=r["ts"], h=float(r["h"]), l=float(r["l"]), c=float(r["c"])) for r in rows]


def sim(after, short, ep, st):
    R = abs(ep - st); tgt = 1.5 * R
    for b in after:
        hit_stop = (b["h"] >= st) if short else (b["l"] <= st)
        fav = (ep - b["l"]) if short else (b["h"] - ep)
        if hit_stop: return -R
        if fav >= tgt: return tgt
    return ((ep - after[-1]["c"]) if short else (after[-1]["c"] - ep)) if after else 0.0


def parse(s):
    return dt.datetime.fromisoformat(s.replace(" ", "T"))


def new_stat():
    return dict(n=0, w=0, usd=0.0, n_live=0, usd_live=0.0, take=0, skip=0, shadow=0)


nodes = collections.defaultdict(new_stat)     # path prefix "" (root) … full leaf path
leaf_meta = {}                                  # leaf path → {leaf, id}
sessions = []; n_routes = 0; n_scored = 0
for p in files:
    d = os.path.basename(p)[len(args.tag) + 1:len(args.tag) + 11]
    try:
        j = json.load(open(p))
    except Exception as e:
        print("bad", d, e); continue
    routes = [r for r in (j.get("routes") or []) if isinstance(r.get("tree_v3"), dict)]
    if not routes:
        continue
    sessions.append(d); bs = bars_of(d)
    trades = j.get("trades") or []
    for r in routes:
        n_routes += 1
        tv = r["tree_v3"]; path = tv.get("path") or ""; action = str(tv.get("leaf") or "SKIP").upper()
        leaf_meta[path] = {"leaf": action, "id": tv.get("id")}
        ep = float(r.get("entry") or 0); st = float(r.get("stop") or 0); short = r.get("direction") == "SHORT"
        R = abs(ep - st)
        pts = None
        if bs and ep > 0 and st > 0 and 1.0 <= R <= 30 and r.get("_dbg_clock", {}).get("sg_now"):
            t0 = parse(r["_dbg_clock"]["sg_now"]); after = [b for b in bs if b["ts"] > t0]
            if after:
                pts = sim(after, short, ep, st)
        live_usd = None
        if (r.get("result") or {}).get("live"):
            for t in trades:
                if t.get("classification") == r.get("classification") and t.get("direction") == r.get("direction") \
                        and abs(float(t.get("entry") or 0) - ep) < 0.01:
                    live_usd = float(t.get("pnl_usd") or 0); break
        parts = path.split("/") if path else []
        prefixes = [""] + ["/".join(parts[:i + 1]) for i in range(len(parts))]
        for pre in prefixes:
            s = nodes[pre]
            s[{"TAKE": "take", "SKIP": "skip", "SHADOW": "shadow"}.get(action, "skip")] += 1
            if pts is not None:
                s["n"] += 1; s["w"] += (pts > 0); s["usd"] += pts * 5 - COMM
            if live_usd is not None:
                s["n_live"] += 1; s["usd_live"] += live_usd
        if pts is not None:
            n_scored += 1

# ── the nested tree with the numbers on every node (for the board) ───────────────────────────────
tree = dt3.load_tree()


def attach_full(node, prefix):
    """Recursive attach that recomputes each child's own prefix from the recorded paths (exact join)."""
    st = nodes.get(prefix) or new_stat()
    out = {"n": st["n"], "w": st["w"], "win": round(100 * st["w"] / st["n"]) if st["n"] else None, "usd": round(st["usd"], 1),
           "n_live": st["n_live"], "usd_live": round(st["usd_live"], 1), "take": st["take"], "skip": st["skip"], "shadow": st["shadow"]}
    if "leaf" in node:
        out.update({"leaf": node["leaf"], "id": node.get("id"), "note": node.get("note"), "measured": node.get("measured")})
        return out
    out.update({"split": node["split"], "children": {}})
    depth = len(prefix.split("/")) if prefix else 0
    # recorded prefixes one level below this node
    below = {}
    for pre, s in nodes.items():
        parts = pre.split("/") if pre else []
        if len(parts) != depth + 1 or (prefix and not pre.startswith(prefix + "/")):
            continue
        feat, _, val = parts[-1].partition("=")
        if feat == node["split"]:
            below[val] = pre
    for key, child in (node.get("branches") or {}).items():
        ks = str(key)
        matches = [pre for val, pre in below.items() if (ks == "*" and val.startswith("*(")) or (ks != "*" and not val.startswith("*(") and dt3._match(ks, val))]
        if len(matches) == 1:
            out["children"][ks] = attach_full(child, matches[0])
        elif not matches:
            out["children"][ks] = attach_full(child, prefix + "/" + node["split"] + "=∅" if prefix else node["split"] + "=∅")
        else:
            # several recorded values under one "A|B" key: merge their subtrees by summing stats
            merged = None
            for m in matches:
                sub = attach_full(child, m)
                if merged is None:
                    merged = sub
                else:
                    def add(a, b):
                        for k in ("n", "w", "n_live", "take", "skip", "shadow"):
                            a[k] += b[k]
                        a["win"] = round(100 * a["w"] / a["n"]) if a["n"] else None
                        a["usd"] = round(a["usd"] + b["usd"], 1); a["usd_live"] = round(a["usd_live"] + b["usd_live"], 1)
                        if "children" in a and "children" in b:
                            for ck in a["children"]:
                                if ck in b["children"]:
                                    add(a["children"][ck], b["children"][ck])
                    add(merged, sub)
            out["children"][ks] = merged
    return out


board = attach_full(tree, "")

# ── leaves report ───────────────────────────────────────────────────────────────────────────────
leaf_rows = []
for path, meta in leaf_meta.items():
    s = nodes[path]
    if s["n"] == 0 and s["n_live"] == 0:
        continue
    win = 100 * s["w"] / s["n"] if s["n"] else 0
    ripe = (s["n"] >= args.min_n and 35 <= win <= 65 and (
        (meta["leaf"] == "SKIP" and s["usd"] >= 100) or (meta["leaf"] == "TAKE" and s["usd"] <= -100)))
    leaf_rows.append(dict(path=path, leaf=meta["leaf"], id=meta["id"], n=s["n"], win=round(win), usd=round(s["usd"], 1),
                          n_live=s["n_live"], usd_live=round(s["usd_live"], 1), ripe=ripe))
leaf_rows.sort(key=lambda r: -r["n"])

measured = {r["path"]: dict(n=r["n"], win=r["win"], usd=r["usd"], n_live=r["n_live"], usd_live=r["usd_live"],
                            source=f"{args.dir}/{args.tag} · {len(sessions)} sessions", date=TODAY) for r in leaf_rows}
json.dump(measured, open(os.path.join(ROOT, "config", "decision_tree_v3.measured.json"), "w"), ensure_ascii=False, indent=1)
od = os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data"); os.makedirs(od, exist_ok=True)
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), sessions=len(sessions), routes=n_routes, scored=n_scored,
               tag=args.tag, tree=board, leaves=leaf_rows), open(os.path.join(od, "tree_v3.json"), "w"), ensure_ascii=False)

L = []; A = L.append
A(f"# מדידת עץ-ההחלטות V3 — {len(sessions)} סשנים, {n_routes} מועמדים ({TODAY})")
A("")
A(f"**מקור:** `{args.dir}/{args.tag}_*.json` (הרנס עם `DECISION_TREE_V3=1`). כל מועמד מדומה על הברים עם הסטופ שלו ויעד 1.5R, חוזה 1, אחרי עמלות, **בלתי-תלוי** — זו איכות-הדעה של העלה, לא תיק; הרנס יום-כולל מכריע (24.09). `לייב` = מה שההרנס באמת ביצע דרך העלה הזה.")
A("")
A("| עלה (הנתיב בעץ) | פעולה | מועמדים | win% | Σ$ אילו נלקחו | לייב n · Σ$ | |")
A("|---|---|---|---|---|---|---|")
for r in leaf_rows:
    A(f"| `{r['path']}` | {r['leaf']}:{r['id'] or ''} | {r['n']} | {r['win']}% | {r['usd']:+,.0f}$ | {r['n_live']} · {r['usd_live']:+,.0f}$ | {'🌱 בשל לפיצול' if r['ripe'] else ''} |")
A("")
A(f"**בשל לפיצול** = n ≥ {args.min_n}, תוצאה מעורבת (35–65% win) ו-Σ$ שסותר את הפעולה (SKIP שמסתכם ≥ +100$ · TAKE שמסתכם ≤ −100$). הפיצול הבא הוא השאלה הבאה בסדר הדוקטרינרי (מבנה → מיקום → test → ווליום) — לא ציון.")
mp = os.path.join(ROOT, "docs", "reports", f"TREE_V3_MEASURE_{TODAY}.md"); open(mp, "w", encoding="utf-8").write("\n".join(L))
print(f"sessions={len(sessions)} routes={n_routes} scored={n_scored} leaves={len(leaf_rows)} ripe={sum(1 for r in leaf_rows if r['ripe'])}")
for r in leaf_rows[:25]:
    print(f"  {r['leaf']:6s} n={r['n']:4d} win {r['win']:3d}% Σ{r['usd']:+8.0f}$ live {r['n_live']:3d}·{r['usd_live']:+7.0f}$ {'RIPE' if r['ripe'] else '    '} {r['path']}")
print("→", mp)
