#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""marks_vs_tree.py — every mark on the canvas (Michael's, and ours = the day-review ideal entries) becomes a
question to the decision tree: at that moment, in that direction, what did the producers offer, what did the
tree say (leaf + path), what did the gates after it do, and what did the system actually trade?
(Michael 25.09: "ואז אני רוצה שנשפר את המערכת על סמך העבר ועל סמך מה שסומן".)

Classes per mark:
  took            a live trade in the mark's direction within the window
  tree_skip:<id>  candidates existed, the tree refused them (the leaf id) → a SPLIT candidate on that leaf
  downstream:<g>  the tree admitted, a later safety gate refused (ELQ, rr, slot, eod…)
  shadow_only     the tree admitted, the producer is shadow-only → a "make it live" candidate
  no_producer     no pattern fired near the mark → a PRODUCER question, not a tree question

Sources: docs/marks/<d>.json (Michael) · static data/review.json legs.ideal (ours) · the day's decisions:
harness_out/t466/treev3_<d>.json routes (tree paths, replay) else data_handoff/מק-1/<d>/gateway_decisions.jsonl
(live feed; carries tree_v3 from 25.09 on).

  python3 scripts/marks_vs_tree.py [YYYY-MM-DD ...]     # default: every day that has marks
Outputs: docs/reports/MARKS_VS_TREE_<date>.md · render_mobile_relay/static/docs/data/marks_report.json
"""
import collections, datetime as dt, glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); TODAY = dt.datetime.now(IL).date().isoformat()
WIN_BEFORE, WIN_AFTER = 10, 15   # minutes around the mark's entry time
STATIC = os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data")


def mins(t):
    try:
        h, m = t[:5].split(":"); return int(h) * 60 + int(m)
    except Exception:
        return None


def load_marks(d):
    out = []
    p = os.path.join(ROOT, "docs", "marks", f"{d}.json")
    if os.path.exists(p):
        for m in json.load(open(p, encoding="utf-8")).get("marks", []):
            out.append(dict(m, author=m.get("author") or "michael"))
    try:
        rv = json.load(open(os.path.join(STATIC, "review.json"), encoding="utf-8")).get("days", {}).get(d) or {}
        for lg in rv.get("legs", []) or []:
            idl = lg.get("ideal") or {}
            if idl.get("time"):
                out.append(dict(dir=lg.get("dir"), t0=idl["time"], p0=idl.get("price"), t1=lg.get("end"), p1=lg.get("to_px"),
                                note=f'{lg.get("pts")} נק׳ · {lg.get("verdict")}', author="oracle"))
    except Exception:
        pass
    return out


def load_decisions(d):
    """[{il, pattern, direction, entry, leaf, id, path, outcome, blocked_by}] for the day."""
    rows = []
    hp = os.path.join(ROOT, "harness_out", "t466", f"treev3_{d}.json")
    if os.path.exists(hp):
        for r in json.load(open(hp)).get("routes", []):
            tv = r.get("tree_v3") or {}; res = r.get("result") or {}
            rows.append(dict(il=r.get("il", "")[:5], pattern=r.get("classification"), direction=r.get("direction"), entry=r.get("entry"),
                             leaf=tv.get("leaf"), id=tv.get("id"), path=tv.get("path"),
                             outcome="live" if res.get("live") else ("shadow" if (res.get("shadow") or r.get("shadow_only")) else ("blocked" if (r.get("blocked_by") or r.get("live_blocked_by")) else "none")),
                             blocked_by=r.get("blocked_by") or r.get("live_blocked_by"), src="replay"))
        return rows
    gp = os.path.join(ROOT, "data_handoff", "מק-1", d, "gateway_decisions.jsonl")
    if os.path.exists(gp):
        for line in open(gp, encoding="utf-8"):
            try:
                j = json.loads(line)
            except Exception:
                continue
            ts = j.get("ts") or ""
            try:
                il = dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(IL).strftime("%H:%M")
            except Exception:
                il = ts[11:16]
            tv = j.get("tree_v3") or {}
            rows.append(dict(il=il, pattern=j.get("pattern"), direction=j.get("direction"), entry=j.get("entry"),
                             leaf=tv.get("leaf"), id=tv.get("id"), path=tv.get("path"), outcome=j.get("outcome"),
                             blocked_by=j.get("blocked_by") or j.get("live_blocked_by"), src="live"))
    return rows


def classify(mark, decs):
    t = mins(mark.get("t0") or "")
    if t is None:
        return "bad_mark", []
    near = [r for r in decs if r["direction"] == mark.get("dir") and mins(r["il"]) is not None and t - WIN_BEFORE <= mins(r["il"]) <= t + WIN_AFTER]
    if any(r["outcome"] == "live" for r in near):
        return "took", near
    if not near:
        return "no_producer", []
    admitted = [r for r in near if r["leaf"] == "TAKE" or (r["leaf"] is None and not str(r.get("blocked_by") or "").startswith(("dalton_intent", "tree:")))]
    if admitted:
        if any(r["outcome"] == "shadow" or (r["blocked_by"] is None and r["outcome"] != "live") for r in admitted):
            if all(r["blocked_by"] is None for r in admitted):
                return "shadow_only", near
        gates = collections.Counter(str(r["blocked_by"] or "").split(" ")[0] for r in admitted if r["blocked_by"])
        if gates:
            return "downstream:" + gates.most_common(1)[0][0], near
        return "shadow_only", near
    ids = collections.Counter((r["id"] or str(r.get("blocked_by") or "").replace("dalton_intent:", "")) for r in near)
    return "tree_skip:" + str(ids.most_common(1)[0][0]), near


days = sys.argv[1:] or sorted(os.path.basename(p)[:10] for p in glob.glob(os.path.join(ROOT, "docs", "marks", "*.json")))
if not days:
    sys.exit("no marks yet (docs/marks/<date>.json) — draw on /doc/mark.html")
report = {"generated": dt.datetime.now(IL).isoformat(timespec="minutes"), "days": {}}
agg = collections.Counter(); agg_leaf = collections.Counter(); agg_pts = collections.defaultdict(float)
for d in days:
    marks = load_marks(d); decs = load_decisions(d)
    rows = []
    for m in marks:
        cls, near = classify(m, decs)
        pts = None
        try:
            if m.get("p0") is not None and m.get("p1") is not None:
                pts = round((float(m["p1"]) - float(m["p0"])) * (1 if m.get("dir") == "LONG" else -1), 2)
        except Exception:
            pts = None
        rows.append(dict(author=m.get("author"), dir=m.get("dir"), t0=m.get("t0"), p0=m.get("p0"), t1=m.get("t1"), p1=m.get("p1"), pts=pts,
                         note=m.get("note"), cls=cls,
                         near=[dict(il=r["il"], pattern=r["pattern"], leaf=r["leaf"], id=r["id"], outcome=r["outcome"], blocked_by=r["blocked_by"], path=r["path"]) for r in near[:6]]))
        if m.get("author") == "michael":
            agg[cls.split(":")[0]] += 1; agg_leaf[cls] += 1
            if pts:
                agg_pts[cls] += pts
    report["days"][d] = dict(marks=rows, n_decisions=len(decs), src=(decs[0]["src"] if decs else None))
    L = [f"# הסימונים מול העץ — {d} ({TODAY})", "",
         f"**{len(marks)} סימונים** ({sum(1 for m in marks if m.get('author') == 'michael')} של מייקל · {sum(1 for m in marks if m.get('author') == 'oracle')} שלנו) מול {len(decs)} החלטות-גייטוויי ({(decs[0]['src'] if decs else '—')}). חלון: {WIN_BEFORE} דק׳ לפני הסימון עד {WIN_AFTER} אחריו, באותו כיוון.", "",
         "| מי | כיוון | כניסה | יציאה | נק׳ | מה קרה | מי ראה (העץ · התוצאה) |", "|---|---|---|---|---|---|---|"]
    HEB = {"took": "✅ נלקח", "no_producer": "⭕ אף מפיק לא ראה — שאלה למפיק, לא לעץ", "shadow_only": "🫧 העץ אישר — המפיק צל-בלבד", "bad_mark": "?"}
    for r in rows:
        c = r["cls"]; heb = HEB.get(c) or ("⛔ העץ סירב — עלה " + c.split(":", 1)[1] + " ⇒ מועמד-לפיצול" if c.startswith("tree_skip") else "🚧 העץ אישר, שער אחרי-העץ סירב: " + c.split(":", 1)[1])
        near = " · ".join(f'{x["il"]} {x["pattern"]} → {x["leaf"] or "?"}{(":" + x["id"]) if x["id"] else ""} / {x["outcome"]}{(" " + str(x["blocked_by"]).split(" ")[0]) if x["blocked_by"] else ""}' for x in r["near"][:3]) or "—"
        L.append(f"| {'מייקל' if r['author'] == 'michael' else 'שלנו'} | {r['dir']} | {r['t0']} @{r['p0']} | {r['t1'] or ''} @{r['p1'] or ''} | {r['pts'] if r['pts'] is not None else ''} | {heb} | {near} |")
    open(os.path.join(ROOT, "docs", "reports", f"MARKS_VS_TREE_{d}.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"{d}: {len(marks)} marks / {len(decs)} decisions →", dict(collections.Counter(r['cls'] for r in rows)))
report["summary"] = {"michael_marks": sum(agg.values()), "by_class": dict(agg), "by_leaf": dict(agg_leaf), "pts_by_class": {k: round(v, 1) for k, v in agg_pts.items()}}
os.makedirs(STATIC, exist_ok=True)
json.dump(report, open(os.path.join(STATIC, "marks_report.json"), "w"), ensure_ascii=False, default=str)
if agg:
    print("Michael's marks by class:", dict(agg)); print("split candidates (tree leaves his marks hit):", {k: v for k, v in agg_leaf.items() if k.startswith("tree_skip")})
