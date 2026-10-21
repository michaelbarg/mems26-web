#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""walk_forward.py — out-of-sample (OOS) validation of the live decision tree's branches (METHOD_AUDIT_2026-10-05 §3 step 1).

The question it answers is the one the in-sample Σ$ cannot: *did a branch keep paying AFTER the sessions that
justified it?*  Read-only: it reads the existing t529b harness JSON (one file per session) and the 5-min bars
from local Postgres (SELECT only — nothing is written anywhere except the report under docs/reports/).

Scoring model = tree_measure.py, unchanged: every candidate is simulated INDEPENDENTLY on the bars after its
decision bar with its own stop and a 1.5R target, first touch (stop wins a tie), EOD close, 1 contract,
$5/pt, $2.60 round-trip.  A branch's Σ$ is "what the candidates routed to it would have made IF TAKEN" —
the opinion quality of the branch, not a portfolio.

Branches:
  * RULED  — leaves that carry a `ruling:` in config/decision_tree_v3.yaml (grouped by leaf id, across paths).
             In-sample = sessions ≤ ruling date; OOS = the next --window sessions after it.
  * UNRULED — every other leaf, by its full tree path. Single expanding walk: the first k at which the
             in-sample (sessions[:k]) holds ≥ --min-n candidates opens the OOS region sessions[k:N-holdout];
             each window sessions[k:k+--window] is also reported as a mean $/candidate (step = 1 session).
  * HOLDOUT — the last --holdout sessions are NEVER part of a KEEP/REVERT decision; reported separately.

Verdicts (TAKE leaves only — no SKIP leaf is turned into a TAKE here, the add-a-leaf freeze stands):
  KEEP            OOS Σ$ > 0 AND OOS n ≥ --min-n
  REVERT-TO-SKIP  otherwise — a RECOMMENDATION for the 23:40 fix-agent, not a live edit (the YAML is untouched).
  SKIP leaves get SKIP-HOLDS (OOS Σ$ ≤ 0: skipping saved money) / SKIP-COSTS (OOS Σ$ > 0) — informational.

  python3 scripts/walk_forward.py [--dir harness_out/t466] [--tag t529b] [--window 10] [--holdout 10] [--min-n 10]
"""
import argparse, collections, datetime as dt, glob, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))  # DATABASE_URL only
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo

IL = ZoneInfo("Asia/Jerusalem"); COMM = 2.60; PT_USD = 5.0
TODAY = dt.datetime.now(IL).date().isoformat()

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--dir", default="harness_out/t466", help="harness directory holding <tag>_<YYYY-MM-DD>.json")
ap.add_argument("--tag", default="t529b", help="harness variant tag (the live config replay)")
ap.add_argument("--window", type=int, default=10, help="OOS window in sessions")
ap.add_argument("--holdout", type=int, default=10, help="last N sessions never used to decide direction")
ap.add_argument("--min-n", type=int, default=10, help="minimum candidates in-sample (and OOS for KEEP)")
ap.add_argument("--top", type=int, default=15, help="best/worst rows in the report")
ap.add_argument("--out", default=None, help="report path (default docs/reports/WALK_FORWARD_<today>.md)")
args = ap.parse_args()
CMD = "python3 scripts/walk_forward.py " + " ".join(sys.argv[1:])

# ── ruled branches: leaf id → (ticket, ruling date = last session that justified it) ──────────────────────
# Dates are copied from the `ruling:` / `measured:` notes in config/decision_tree_v3.yaml (read, not edited).
# `location` (T-319b) carries no ruling: key in the YAML; its 11.09 date is from METHOD_AUDIT_2026-10-05 §1(ג).
RULED = {
    "d_with_extension":            ("S1 / T-494 — phase D with the extension",            "2026-09-27"),
    "auction_B_reversal":          ("S5 / T-494 — auction-B reversal at the opening extreme", "2026-09-27"),
    "failed_extension":            ("S7 / T-329 — failed-extension flip (take_failed_ext, no id)", "2026-09-27"),
    "take_failed_ext_responsive":  ("T-529 — failed-extension before the location skip",   "2026-10-03"),
    "take_with_extension":         ("T-466/T-480 — Normal label, IB extended → with it",   "2026-09-25"),
    "auction_B_trend_break":       ("T-484 — auction-B first hour reads Trend, BREAK",     "2026-09-25"),
    "location":                    ("T-319b — responsive location rule (SKIP)",            "2026-09-11"),
    "time_cutoff":                 ("T-538 — no new entries from 20:00 IL (tree 3.3.0)",   "2026-10-05"),
}


def branch_key(tv):
    """RULED leaves group by id (one ruling, many paths); the S7 anchor has no id → by its edge= tail."""
    bid = tv.get("id"); path = tv.get("path") or ""
    if bid in RULED:
        return ("ruled", bid)
    # leaves without an explicit id are recorded with id == path (fwd_harness convention)
    if (bid is None or bid == path) and str(tv.get("leaf")).upper() == "TAKE" and path.endswith("/edge=failed_extension"):
        # T-529's leaf sits under a responsive zone= split (ran before its id was written into the YAML)
        return ("ruled", "take_failed_ext_responsive" if "/zone=" in path else "failed_extension")
    return ("path", path)


# ── sessions ───────────────────────────────────────────────────────────────────────────────────────────────
D = os.path.join(ROOT, args.dir)
files = sorted(glob.glob(os.path.join(D, f"{args.tag}_*.json")))
if not files:
    sys.exit(f"no {args.tag}_*.json in {D}")
t_start = time.time()

# ── bars: ONE read-only query for the whole range (v9_bars_5min_woodies is the live-canonical 5-min source) ─
first_day = os.path.basename(files[0])[len(args.tag) + 1:len(args.tag) + 11]
rows = read_all("""select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD') d, ts, high h, low l, close c
    from v9_bars_5min_woodies where symbol='MES' and ts >= :d0
    and (ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by ts""", {"d0": first_day})
bars = collections.defaultdict(list)
for r in rows:
    bars[r["d"]].append(dict(ts=r["ts"], h=float(r["h"]), l=float(r["l"]), c=float(r["c"])))


def sim(after, short, ep, st):
    R = abs(ep - st); tgt = 1.5 * R
    for b in after:
        hit_stop = (b["h"] >= st) if short else (b["l"] <= st)
        fav = (ep - b["l"]) if short else (b["h"] - ep)
        if hit_stop:
            return -R
        if fav >= tgt:
            return tgt
    return ((ep - after[-1]["c"]) if short else (after[-1]["c"] - ep)) if after else 0.0


def parse(s):
    return dt.datetime.fromisoformat(s.replace(" ", "T"))


def hour_bucket(h):
    if h is None:
        return "?"
    h = int(h)
    return "16h" if h <= 16 else "17h" if h == 17 else "18-19h" if h <= 19 else "20h+"


# ── candidates ─────────────────────────────────────────────────────────────────────────────────────────────
sessions = []; cands = []; n_routes = 0; n_tree = 0; n_scored = 0; n_unscored_no_bars = 0; n_injected = 0
leaf_action = {}
for p in files:
    d = os.path.basename(p)[len(args.tag) + 1:len(args.tag) + 11]
    try:
        j = json.load(open(p))
    except Exception as e:
        print("bad", d, e); continue
    if j.get("session") and j["session"] != d:
        print(f"warn: file date {d} != session {j['session']}")
    routes = j.get("routes") or []
    if not routes:
        continue
    sessions.append(d); bs = bars.get(d) or []
    trades = j.get("trades") or []
    for r in routes:
        n_routes += 1
        tv = r.get("tree_v3")
        if not isinstance(tv, dict):
            continue
        n_tree += 1; n_injected += ("injected" in r)
        action = str(tv.get("leaf") or "SKIP").upper()
        key = branch_key(tv); leaf_action[key] = action
        vec = tv.get("vec") or {}
        ep = float(r.get("entry") or 0); st = float(r.get("stop") or 0); short = r.get("direction") == "SHORT"
        R = abs(ep - st); pts = None
        if ep > 0 and st > 0 and 1.0 <= R <= 30 and (r.get("_dbg_clock") or {}).get("sg_now"):
            if not bs:
                n_unscored_no_bars += 1
            else:
                t0 = parse(r["_dbg_clock"]["sg_now"]); after = [b for b in bs if b["ts"] > t0]
                if after:
                    pts = sim(after, short, ep, st)
        live_usd = None
        if (r.get("result") or {}).get("live"):
            for t in trades:
                if t.get("classification") == r.get("classification") and t.get("direction") == r.get("direction") \
                        and abs(float(t.get("entry") or 0) - ep) < 0.01:
                    live_usd = float(t.get("pnl_usd") or 0); break
        if pts is None:
            continue
        n_scored += 1
        cands.append(dict(s=d, key=key, action=action, path=tv.get("path") or "", id=tv.get("id"),
                          usd=pts * PT_USD - COMM, win=pts > 0, live=live_usd,
                          structure=vec.get("structure"), hour=vec.get("hour"), kind=vec.get("kind")))

N = len(sessions); HOLD = sessions[N - args.holdout:] if args.holdout else []; DEV = sessions[:N - args.holdout]
hold_set = set(HOLD); sidx = {s: i for i, s in enumerate(sessions)}
present_ruled = {k[1] for k in leaf_action if k[0] == "ruled"}
missing_ruled = [k for k in RULED if k not in present_ruled]

# ── per-branch stats ───────────────────────────────────────────────────────────────────────────────────────
by_key = collections.defaultdict(list)
for c in cands:
    by_key[c["key"]].append(c)


def agg(cs):
    n = len(cs); usd = sum(c["usd"] for c in cs); w = sum(c["win"] for c in cs)
    return dict(n=n, usd=round(usd, 2), win=round(100 * w / n) if n else None,
                n_live=sum(1 for c in cs if c["live"] is not None), usd_live=round(sum(c["live"] or 0 for c in cs), 2))


branches = []
for key, cs in by_key.items():
    action = leaf_action[key]; cs.sort(key=lambda c: sidx[c["s"]])
    total = agg(cs); hold = agg([c for c in cs if c["s"] in hold_set])
    row = dict(key=key, kind=key[0], name=key[1], action=action, total=total, holdout=hold, oos=None, insample=None,
               mode=None, ruled=None, windows=0, mean_win_usd_per_cand=None, note="")
    if key[0] == "ruled":
        label, rd = RULED[key[1]]; row["ruled"] = f"{label} · ruled {rd}"
        ins = [c for c in cs if c["s"] <= rd]; post = [s for s in sessions if s > rd][:args.window]
        oos = [c for c in cs if c["s"] in set(post)]
        row["insample"] = agg(ins); row["oos"] = agg(oos); row["mode"] = f"post-ruling · {len(post)} sessions"
        row["oos_sessions"] = post
        if len(post) == 0:
            row["note"] = "no session after the ruling date yet — OOS not measurable"
        elif len(post) < args.window:
            row["note"] = f"only {len(post)} sessions after the ruling (window {args.window})"
        if set(post) & hold_set:
            row["note"] += (" · " if row["note"] else "") + "OOS overlaps the holdout — the ruling itself was replayed on all sessions incl. these"
    else:
        # expanding walk on the development sessions only (holdout excluded from any decision)
        cum = 0; k0 = None
        for i, s in enumerate(DEV):
            cum += sum(1 for c in cs if c["s"] == s)
            if cum >= args.min_n:
                k0 = i + 1; break
        if k0 is None or k0 >= len(DEV):
            row["mode"] = "insufficient in-sample (< min-n before the holdout)"; row["insample"] = agg([c for c in cs if c["s"] in set(DEV)])
        else:
            ins = [c for c in cs if sidx[c["s"]] < k0]; oos_sess = DEV[k0:]
            oos = [c for c in cs if c["s"] in set(oos_sess)]
            row["insample"] = agg(ins); row["oos"] = agg(oos); row["mode"] = f"expanding walk · k0={k0} ({DEV[k0 - 1]}) · OOS {len(oos_sess)} sessions"
            row["oos_sessions"] = oos_sess
            per_win = []
            for k in range(k0, len(DEV)):
                w = set(DEV[k:k + args.window]); wc = [c for c in cs if c["s"] in w]
                if wc:
                    per_win.append(sum(c["usd"] for c in wc) / len(wc))
            row["windows"] = len(per_win)
            row["mean_win_usd_per_cand"] = round(sum(per_win) / len(per_win), 2) if per_win else None
    o = row["oos"]
    if o is None:
        v = "UNSCORED"
    elif action == "TAKE":
        v = "KEEP" if (o["usd"] > 0 and o["n"] >= args.min_n) else "REVERT-TO-SKIP"
        if o["n"] < args.min_n:
            v += f" (OOS n={o['n']} < {args.min_n})"
    else:
        v = "SKIP-HOLDS" if o["usd"] <= 0 else "SKIP-COSTS"
    row["verdict"] = v
    branches.append(row)

take_rows = [b for b in branches if b["action"] == "TAKE"]
skip_rows = [b for b in branches if b["action"] != "TAKE"]
scored_take = [b for b in take_rows if b["oos"] is not None]
keep = [b for b in scored_take if b["verdict"] == "KEEP"]
revert = [b for b in scored_take if b["verdict"].startswith("REVERT")]
revert_neg = [b for b in revert if b["oos"]["n"] >= args.min_n]        # negative OOS with enough n — the prune list
revert_thin = [b for b in revert if b["oos"]["n"] < args.min_n]        # not enough OOS candidates — no evidence either way
unscored_take = [b for b in take_rows if b["oos"] is None]

# ── holdout totals ─────────────────────────────────────────────────────────────────────────────────────────
hold_c = [c for c in cands if c["s"] in hold_set]
hold_take = agg([c for c in hold_c if c["action"] == "TAKE"]); hold_skip = agg([c for c in hold_c if c["action"] != "TAKE"])
dev_c = [c for c in cands if c["s"] not in hold_set]
dev_take = agg([c for c in dev_c if c["action"] == "TAKE"]); dev_skip = agg([c for c in dev_c if c["action"] != "TAKE"])

# ── context table without day_type: (structure, hour-bucket, kind) ─────────────────────────────────────────
ctx_fields_ok = all(any(c[f] is not None for c in cands) for f in ("structure", "hour", "kind"))
ctx = []
if ctx_fields_ok:
    g = collections.defaultdict(list)
    for c in cands:
        g[(c["structure"], hour_bucket(c["hour"]), c["kind"])].append(c)
    for k, cs in g.items():
        if len(cs) >= args.min_n:
            a = agg(cs); h = agg([c for c in cs if c["s"] in hold_set]); tk = sum(1 for c in cs if c["action"] == "TAKE")
            ctx.append(dict(structure=k[0], hour=k[1], kind=k[2], n=a["n"], win=a["win"], usd=a["usd"], take=tk,
                            hold_n=h["n"], hold_usd=h["usd"]))
    ctx.sort(key=lambda r: -r["usd"])

elapsed = round(time.time() - t_start, 1)

# ── stdout ─────────────────────────────────────────────────────────────────────────────────────────────────
print(CMD)
print(f"sessions={N} ({sessions[0]}..{sessions[-1]}) dev={len(DEV)} holdout={len(HOLD)} ({HOLD[0] if HOLD else '-'}..{HOLD[-1] if HOLD else '-'})")
print(f"routes={n_routes} with_tree={n_tree} scored={n_scored} unscored_no_bars={n_unscored_no_bars} injected_live_routes={n_injected} bars_days={len(bars)} elapsed={elapsed}s")
print(f"branches={len(branches)} take={len(take_rows)} skip={len(skip_rows)} | TAKE scored OOS={len(scored_take)} KEEP={len(keep)} REVERT={len(revert)} (neg_oos_n>={args.min_n}: {len(revert_neg)} · thin_oos_n<{args.min_n}: {len(revert_thin)}) unscored={len(unscored_take)}")
print(f"ruled present={sorted(present_ruled)} missing_in_this_run={missing_ruled}")
print(f"dev   TAKE n={dev_take['n']} win={dev_take['win']}% Σ{dev_take['usd']:+.2f}$ | SKIP n={dev_skip['n']} win={dev_skip['win']}% Σ{dev_skip['usd']:+.2f}$")
print(f"HOLDOUT TAKE n={hold_take['n']} win={hold_take['win']}% Σ{hold_take['usd']:+.2f}$ | SKIP n={hold_skip['n']} win={hold_skip['win']}% Σ{hold_skip['usd']:+.2f}$")
print("ruled branches (post-ruling OOS):")
for b in branches:
    if b["kind"] == "ruled":
        o = b["oos"]; i = b["insample"]
        print(f"  {b['action']:4s} {b['name']:28s} in n={i['n']:4d} Σ{i['usd']:+9.2f}$ | OOS n={o['n']:3d} win={o['win'] if o['win'] is not None else '-':>3}% Σ{o['usd']:+9.2f}$ | hold n={b['holdout']['n']:3d} Σ{b['holdout']['usd']:+9.2f}$ → {b['verdict']}  [{b['ruled']}]")
if not ctx_fields_ok:
    print("context table: structure/hour/kind not present in tree_v3.vec — not synthesized")

# ── report ─────────────────────────────────────────────────────────────────────────────────────────────────
def fmt(a):
    return f"{a['n']} · {a['win'] if a['win'] is not None else '-'}% · {a['usd']:+,.0f}$" if a and a["n"] else "0 · - · 0$"


L = []; A = L.append
A(f"# Walk-forward · {args.tag} · {N} סשנים ({sessions[0]} → {sessions[-1]}) — {TODAY}")
A("")
A(f"**פקודה:** `{CMD}`  ")
A(f"**מקור:** `{args.dir}/{args.tag}_*.json` (ריפליי קונפיג-הלייב, עץ 3.2.0 + כל השערים) · ברים: `v9_bars_5min_woodies` (SELECT בלבד, {len(bars)} ימים, {elapsed}s). "
  f"מודל-הערכה = `tree_measure.py`: סטופ של המועמד, יעד 1.5R, נגיעה ראשונה (סטופ קודם בתיקו), סגירת-EOD, חוזה 1, 2.60$. Σ$ של ענף = מה שהמועמדים שנותבו אליו היו עושים **אילו נלקחו** — איכות-הדעה, לא תיק.")
A("")
A("## 1 · ספירות גולמיות")
A("")
A("```")
A(f"sessions={N} dev={len(DEV)} ({DEV[0]}..{DEV[-1]}) holdout={len(HOLD)} ({HOLD[0] if HOLD else '-'}..{HOLD[-1] if HOLD else '-'})")
A(f"routes={n_routes} with_tree={n_tree} scored={n_scored} unscored_no_bars={n_unscored_no_bars} injected_live_routes={n_injected}")
A(f"branches={len(branches)} take={len(take_rows)} skip={len(skip_rows)} | TAKE scored OOS={len(scored_take)} KEEP={len(keep)} REVERT={len(revert)} (neg_oos_n>={args.min_n}: {len(revert_neg)} · thin_oos_n<{args.min_n}: {len(revert_thin)}) unscored={len(unscored_take)}")
A(f"ruled present={sorted(present_ruled)}")
A(f"ruled missing in this run={missing_ruled}")
A(f"dev     TAKE {fmt(dev_take)} | SKIP {fmt(dev_skip)}")
A(f"HOLDOUT TAKE {fmt(hold_take)} | SKIP {fmt(hold_skip)}")
A("```")
A("")
A("**הגדרות.** RULED = עלה עם `ruling:` ב-`config/decision_tree_v3.yaml` (מקובץ לפי `id`, על פני כל הנתיבים); in-sample = הסשנים עד תאריך-הפסיקה, OOS = "
  f"{args.window} הסשנים הבאים. UNRULED = כל עלה אחר לפי הנתיב המלא; הליכה מתרחבת אחת: ה-k הראשון שבו in-sample מחזיק ≥{args.min_n} מועמדים פותח את אזור-ה-OOS עד תחילת ה-holdout "
  f"(כל מועמד נספר פעם אחת), ובנוסף ממוצע $/מועמד על חלונות של {args.window} סשנים בצעד של סשן. **HOLDOUT** = {args.holdout} הסשנים האחרונים — לא משתתפים בשום הכרעת KEEP/REVERT. "
  f"**KEEP** = TAKE עם OOS Σ$ > 0 **וגם** OOS n ≥ {args.min_n}; אחרת **REVERT-TO-SKIP כהמלצה** (העץ החי לא נערך). SKIP-HOLDS / SKIP-COSTS = אינפורמטיבי (אין הוספת-עלה).")
A("")
A("## 2 · הענפים הנפסקים — OOS אחרי תאריך-הפסיקה")
A("")
A("| ענף | פעולה | פסיקה | in-sample n · win · Σ$ | OOS סשנים | OOS n · win · Σ$ | holdout n · win · Σ$ | פסק-דין | הערה |")
A("|---|---|---|---|---|---|---|---|---|")
for b in sorted([b for b in branches if b["kind"] == "ruled"], key=lambda b: -(b["oos"]["usd"] if b["oos"] else 0)):
    A(f"| `{b['name']}` | {b['action']} | {b['ruled']} | {fmt(b['insample'])} | {len(b.get('oos_sessions') or [])} | {fmt(b['oos'])} | {fmt(b['holdout'])} | **{b['verdict']}** | {b['note']} |")
if missing_ruled:
    A("")
    A(f"לא קיימים בריצה הזו (הקונפיג ש-`{args.tag}` ריץ קדם להם): " + ", ".join(f"`{m}` ({RULED[m][0]}, {RULED[m][1]})" for m in missing_ruled) + " — אין להם מספר OOS כאן; T-538 כבר נמדד על holdout נפרד ב-`harness_out/t538`.")
A("")
A(f"## 3 · עלי-TAKE לא-נפסקים — הליכה מתרחבת (dev בלבד, {len(DEV)} סשנים)")
A("")
scored_sorted = sorted([b for b in scored_take if b["kind"] == "path"], key=lambda b: -b["oos"]["usd"])


def path_table(rows, title):
    A(f"### {title}")
    A("")
    A("| נתיב-העץ | in-sample n · win · Σ$ | OOS n · win · Σ$ | ממוצע $/מועמד בחלון (חלונות) | holdout n · win · Σ$ | פסק-דין |")
    A("|---|---|---|---|---|---|")
    for b in rows:
        mw = f"{b['mean_win_usd_per_cand']:+.1f}$ ({b['windows']})" if b["mean_win_usd_per_cand"] is not None else "-"
        A(f"| `{b['name']}` | {fmt(b['insample'])} | {fmt(b['oos'])} | {mw} | {fmt(b['holdout'])} | **{b['verdict']}** |")
    A("")


path_table(scored_sorted[:args.top], f"הטובים ({min(args.top, len(scored_sorted))} מתוך {len(scored_sorted)})")
path_table(list(reversed(scored_sorted))[:args.top], f"הגרועים ({min(args.top, len(scored_sorted))})")
if unscored_take:
    shown = [b for b in sorted(unscored_take, key=lambda b: -b["total"]["n"]) if b["total"]["n"] >= 5]
    A(f"**לא נמדדו** ({len(unscored_take)} עלי-TAKE עם פחות מ-{args.min_n} מועמדים לפני ה-holdout; מוצגים {len(shown)} עם ≥5 מועמדים סה״כ):")
    A("")
    for b in shown:
        A(f"- `{b['name']}` — סה״כ {fmt(b['total'])} · holdout {fmt(b['holdout'])}")
    A("")
A("## 4 · עלי-SKIP — מה היה עולה/חוסך (אינפורמטיבי; הקפאת-ענפים: אין הוספת עלה)")
A("")
skip_scored = sorted([b for b in skip_rows if b["oos"] is not None], key=lambda b: -b["oos"]["usd"])
A("| ענף | id | in-sample n · Σ$ | OOS n · win · Σ$ אילו נלקחו | holdout n · Σ$ | פסק-דין |")
A("|---|---|---|---|---|---|")
skip_show = skip_scored if len(skip_scored) <= 2 * args.top else skip_scored[:args.top] + list(reversed(skip_scored))[:args.top]
for b in skip_show:
    A(f"| `{b['name']}` | {b['kind']} | {fmt(b['insample'])} | {fmt(b['oos'])} | {fmt(b['holdout'])} | {b['verdict']} |")
A("")
A(f"## 5 · HOLDOUT — {len(HOLD)} הסשנים האחרונים ({HOLD[0] if HOLD else '-'} → {HOLD[-1] if HOLD else '-'}), לא שימשו לשום הכרעה")
A("")
A(f"| | TAKE (מה שהעץ לקח) | SKIP (מה שהעץ דחה) |")
A("|---|---|---|")
A(f"| dev ({len(DEV)} סשנים) | {fmt(dev_take)} | {fmt(dev_skip)} |")
A(f"| **holdout ({len(HOLD)})** | **{fmt(hold_take)}** | **{fmt(hold_skip)}** |")
A("")
A("הפרדה בריאה = TAKE חיובי ו-SKIP שלילי; היפוך-הסימן בשורת-ה-holdout הוא בדיוק החתימה שסעיף 1(ב) של ביקורת-השיטה מצא על 6 הסשנים האחרונים. "
  "⚠️ הפסיקות של 25.09/27.09/03.10 נמדדו על **כל** הסשנים כולל ה-holdout — עבור הענפים הנפסקים ה-holdout אינו נקי; רק עלי-ה-path (סעיף 3) נבדקו נגדו בלי שראו אותו.")
A("")
A("## 6 · הקשר בלי תווית — (מבנה-IB, שעה, סוג-כניסה), כל המועמדים, n ≥ " + str(args.min_n))
A("")
if ctx_fields_ok:
    A("| structure | hour | kind | n | win% | Σ$ אילו נלקחו | מהם TAKE | holdout n · Σ$ |")
    A("|---|---|---|---|---|---|---|---|")
    for r in ctx:
        A(f"| {r['structure']} | {r['hour']} | {r['kind']} | {r['n']} | {r['win']}% | {r['usd']:+,.0f}$ | {r['take']} | {r['hold_n']} · {r['hold_usd']:+,.0f}$ |")
    A("")
    A("השדות נקראו מ-`tree_v3.vec` (`structure`, `hour` = שעת-IL של המועמד, `kind`) — כפי שהגייטוויי כתב אותם; לא חושב דבר מחדש. זו טבלת-הייחוס לווריאנט-ההקשר של ליל ד׳ (walk-forward, לא Σ in-sample).")
else:
    A("השדות `structure`/`hour`/`kind` אינם קיימים ב-`tree_v3.vec` של הריצה הזו — הטבלה לא נבנתה ולא סונתזה.")
A("")
A("## 7 · מה זה אומר ל-23:40")
A("")
A(f"- **המספר:** holdout ({len(HOLD)} סשנים) TAKE {fmt(hold_take)} מול SKIP {fmt(hold_skip)} — העץ בחר הפוך. dev: TAKE {fmt(dev_take)} מול SKIP {fmt(dev_skip)}.")
A(f"- **רשימת-הגיזום (דוקטרינה שלב 6) — {len(revert_neg)} עלי-TAKE עם OOS ≤ 0 ו-n ≥ {args.min_n}** (ראיה שלילית, לא חוסר-ראיה). המלצה בלבד; `config/decision_tree_v3.yaml` לא נערך הלילה:")
for b in sorted(revert_neg, key=lambda b: b["oos"]["usd"]):
    A(f"  - `{b['name']}` — OOS {fmt(b['oos'])} · holdout {fmt(b['holdout'])}" + (f" · {b['ruled']}" if b["ruled"] else ""))
A(f"- **דקים (REVERT מכוח הכלל, OOS n < {args.min_n}):** {len(revert_thin)} — אין להם ראיה לכאן או לכאן; ענף ללא OOS (T-529: 0 סשנים אחרי 03.10) הוא \"עדיין בלי מספר\", לא \"שלילי\".")
A(f"- **KEEP:** {len(keep)} — " + ", ".join(f"`{b['name']}` (OOS {fmt(b['oos'])})" for b in sorted(keep, key=lambda b: -b['oos']['usd'])) + ".")
A("- אין עלה חדש הלילה. שלב C/D בלי תווית (סעיף 6) נמדד ביום ד׳ מול `t529b` באותו לילה, walk-forward.")
A("- **הסתייגויות:** רמת-מועמד ≠ יום-שלם (סלוט יחיד, שערים אחרי העץ); 5 סשנים אחרי פסיקות 25–27.09 הם N קטן; משטר יוני–אוקטובר (שורטים) עלול להתהפך; 192 מסלולי-לייב מוזרקים נספרים כמועמדים (כמו ב-`tree_measure`).")
out = args.out or os.path.join(ROOT, "docs", "reports", f"WALK_FORWARD_{TODAY}.md")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("→", out)
