#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tree_learner.py — a decision tree that SPLITS ON THE CIRCUMSTANCES of every candidate and grows with the data
(Michael 25.09 11:50: "עץ החלטות שמתפצל כל הזמן זאת הדרך הנכונה"; "אני נגד ציונים").

Not a score. Every node asks one question about the circumstance (opening type? day type? phase? where vs value?
extension? pullback/test? volume? delta? distance from the extreme? producer? with/against the tree's direction?
stop size?) and splits; a leaf is an explicit rule — TAKE or SKIP in that circumstance — with the count behind it.
The split chosen at each node is the one that separates winners from losers best (least mixed children), the
tree keeps splitting until a leaf has fewer than MIN_LEAF candidates or MAX_DEPTH is reached.

Data: every candidate the real engine produced on the 58 clean sessions (harness routes, baseline replay), with the
producer's own stop; outcome = first touch of stop / 1.5R on the 5-min bars, EOD close, one contract, $2.60 RT.
Features are computed CAUSALLY at the candidate's bar (review_lib.features) plus the engine's own labels.

Validation is WALK-FORWARD IN TIME: the tree is grown on the past only and judged on days it never saw
(chronological blocks), scored as a one-position-at-a-time playbook — the only honest way to know whether the
leaves are knowledge or noise. Then the tree is grown on all 58 sessions and printed as rules.

  python3 scripts/tree_learner.py [--min-leaf 40] [--max-depth 5] [--block 6]
Outputs: docs/reports/TREE_LEARNER_<date>.md · render_mobile_relay/static/docs/data/tree_learner.json
"""
import argparse, collections, datetime as dt, glob, json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts")); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
import oracle_engine as oe
import review_lib as rl
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); COMM = 2.60; TODAY = dt.datetime.now(IL).date().isoformat()
B = os.path.join(ROOT, "harness_out", "t458")

ap = argparse.ArgumentParser()
ap.add_argument("--min-leaf", type=int, default=40)
ap.add_argument("--max-depth", type=int, default=5)
ap.add_argument("--block", type=int, default=6, help="walk-forward test block (sessions)")
ap.add_argument("--first-train", type=int, default=24, help="sessions in the first training window")
ap.add_argument("--take-min-avg", type=float, default=3.0, help="a leaf is TAKE when its mean $ ≥ this")
args = ap.parse_args()

# ── candidates ────────────────────────────────────────────────────────────────
sessions = sorted(os.path.basename(p)[8:18] for p in glob.glob(os.path.join(B, "branch1_*.json")))
bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.symbol='MES' and (b.ts at time zone 'Asia/Jerusalem')::date >= :a and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""", {"a": sessions[0]})
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b["d"])].append(b)
alld = sorted(by_day)
prev_va = {}
for k, d in enumerate(alld):
    if k:
        pb = by_day[alld[k - 1]]; prev_va[d] = oe.compute_developing_va(pb, len(pb) - 1) if len(pb) > 5 else {}
try:
    from backend.v9.services.dalton_playbook import entry_kind_for
except Exception:
    entry_kind_for = lambda c: "?"

def sim(bs, i, short, ep, st):
    R = abs(ep - st); tgt = 1.5 * R
    for j in range(i + 1, len(bs)):
        b = bs[j]
        if ((b["h"] >= st) if short else (b["l"] <= st)): return -R, j
        fav = (ep - b["l"]) if short else (b["h"] - ep)
        if fav >= tgt: return tgt, j
    return ((ep - bs[-1]["c"]) if short else (bs[-1]["c"] - ep)), len(bs) - 1

cands = []
for d in sessions:
    bs = by_day.get(d) or []
    if len(bs) < 60: continue
    p = os.path.join(B, f"r15_{d}.json")
    if not os.path.exists(p): p = os.path.join(B, f"branch1_{d}.json")
    j = json.load(open(p)); atr0 = oe.compute_atr(bs, min(20, len(bs) - 1)) or 6.0
    for r in j.get("routes") or []:
        il = (r.get("il") or "")[:5]
        if not il: continue
        hh, mm = int(il[:2]), int(il[3:5]); i = (hh - 16) * 12 + (mm - 30) // 5 - 1     # decision at bar close ⇒ bar index
        if i < 1 or i >= len(bs) - 1: continue
        ep = float(r.get("entry") or 0); st = float(r.get("stop") or 0); short = r.get("direction") == "SHORT"
        R = abs(ep - st)
        if ep <= 0 or st <= 0 or R < 1.0 or R > 30: continue
        f = rl.features(bs, i, short, prev_va.get(d), atr_fallback=atr0)
        if not f: continue
        pts, end_i = sim(bs, i, short, ep, st)
        hint = r.get("dp_dir_hint"); rel = "with" if hint == r.get("direction") else ("against" if hint in ("LONG", "SHORT") else "none")
        res = r.get("result") or {}
        cands.append(dict(
            d=d, i=i, il=il, end_i=end_i, pts=round(pts, 2), usd=round(pts * 5 - COMM, 2), win=pts > 0,
            live=bool(res.get("live")),
            # circumstances
            opening=r.get("dp_ot_seen") or "UNKNOWN", day_type=r.get("dp_day_type") or "?", phase=f["ph"], hour=hh,
            direction=r.get("direction"), producer=r.get("classification") or "?", kind=entry_kind_for(r.get("classification") or ""),
            rel_hint=rel, zone=f["zone"], with_day=f["with_day"], with_ext=f["with_ext"], ext=f["ext"],
            pullback=f["pullback_before"], structure_break=f["structure_break"], trigger_ok=f["trigger_ok"],
            vol_trig=f["vol_trig"], delta_with=f["delta_with"], near_ib=f["near_ib_edge"], near_prev=f["near_prev_edge"],
            at_extreme=f["at_extreme"], bars_from_extreme=f["bars_from_extreme"], move_atr=f["move_from_open_atr"],
            range_atr=f["range_atr"], R_atr=round(R / max(f["atr"], 0.25), 2), R=round(R, 2),
        ))
CAT = ["opening", "day_type", "phase", "direction", "producer", "kind", "rel_hint", "zone", "ext"]
BOOL = ["with_day", "with_ext", "pullback", "structure_break", "trigger_ok", "vol_trig", "delta_with", "near_ib", "near_prev", "at_extreme"]
NUM = ["hour", "bars_from_extreme", "move_atr", "range_atr", "R_atr", "R"]
HEB = {"opening": "סוג-פתיחה", "day_type": "סוג-יום", "phase": "שלב", "direction": "כיוון", "producer": "מפיק", "kind": "סוג-כניסה", "rel_hint": "מול כיוון-העץ",
       "zone": "מיקום מול הערך", "ext": "הרחבת-IB", "with_day": "עם כיוון-היום", "with_ext": "עם ההרחבה", "pullback": "אחרי פולבק/test", "structure_break": "שבירת-מבנה",
       "trigger_ok": "בר-טריגר", "vol_trig": "ווליום-טריגר", "delta_with": "דלתא-עם", "near_ib": "ליד קצה-IB", "near_prev": "ליד ערך-אתמול", "at_extreme": "על הקיצון",
       "bars_from_extreme": "ברים מהקיצון", "hour": "שעה", "move_atr": "מהלך-מהפתיחה/ATR", "range_atr": "טווח-הבר/ATR", "R_atr": "סטופ/ATR", "R": "סטופ (נק׳)"}

# ── the tree ──────────────────────────────────────────────────────────────────
def mean(xs): return sum(xs) / len(xs) if xs else 0.0
def sse(rows):
    if not rows: return 0.0
    m = mean([r["usd"] for r in rows]); return sum((r["usd"] - m) ** 2 for r in rows)

def best_split(rows, min_leaf):
    base = sse(rows); best = None
    for feat in CAT + BOOL:
        vals = sorted({r[feat] for r in rows}, key=str)
        for v in vals:
            a = [r for r in rows if r[feat] == v]; b = [r for r in rows if r[feat] != v]
            if len(a) < min_leaf or len(b) < min_leaf: continue
            gain = base - sse(a) - sse(b)
            if best is None or gain > best[0]: best = (gain, feat, "==", v, a, b)
    for feat in NUM:
        xs = sorted({r[feat] for r in rows if r[feat] is not None})
        if len(xs) < 3: continue
        qs = [xs[int(len(xs) * q)] for q in (0.2, 0.35, 0.5, 0.65, 0.8)]
        for t in sorted(set(qs)):
            a = [r for r in rows if r[feat] is not None and r[feat] <= t]; b = [r for r in rows if r[feat] is None or r[feat] > t]
            if len(a) < min_leaf or len(b) < min_leaf: continue
            gain = base - sse(a) - sse(b)
            if best is None or gain > best[0]: best = (gain, feat, "<=", t, a, b)
    return best

def grow(rows, depth, min_leaf, max_depth, path):
    node = dict(n=len(rows), usd=round(sum(r["usd"] for r in rows), 1), avg=round(mean([r["usd"] for r in rows]), 2), win=round(100 * mean([1.0 if r["win"] else 0.0 for r in rows])), path=path)
    sp = best_split(rows, min_leaf) if depth < max_depth and len(rows) >= 2 * min_leaf else None
    if sp is None or sp[0] <= 0:
        node["leaf"] = True; node["action"] = "TAKE" if node["avg"] >= args.take_min_avg else "SKIP"; return node
    gain, feat, op, v, a, b = sp
    node["split"] = dict(feat=feat, op=op, value=v, gain=round(gain))
    node["yes"] = grow(a, depth + 1, min_leaf, max_depth, path + [(feat, op, v, True)])
    node["no"] = grow(b, depth + 1, min_leaf, max_depth, path + [(feat, op, v, False)])
    return node

def decide(node, r):
    while not node.get("leaf"):
        s = node["split"]; f, op, v = s["feat"], s["op"], s["value"]
        yes = (r[f] == v) if op == "==" else (r[f] is not None and r[f] <= v)
        node = node["yes"] if yes else node["no"]
    return node

def playbook(rows):
    """one position at a time per session"""
    tot = 0.0; n = 0; w = 0; days = collections.defaultdict(float)
    for d in sorted({r["d"] for r in rows}):
        busy = -1
        for r in sorted([r for r in rows if r["d"] == d], key=lambda r: r["i"]):
            if r["i"] <= busy: continue
            busy = r["end_i"]; tot += r["usd"]; n += 1; w += r["win"]; days[d] += r["usd"]
    return tot, n, (100 * w / n if n else 0), sum(1 for v in days.values() if v > 0), sum(1 for v in days.values() if v < 0)

def live_set_usd(sess):
    tot = 0.0; n = 0
    for d in sess:
        p = os.path.join(B, f"r15_{d}.json")
        if not os.path.exists(p): p = os.path.join(B, f"branch1_{d}.json")
        j = json.load(open(p)); tr = j.get("trades") or []
        tot += float(j.get("daily_pnl_harness") or 0) - COMM * len(tr); n += len(tr)
    return tot, n

# ── walk-forward ──────────────────────────────────────────────────────────────
sess = sorted({r["d"] for r in cands})
folds = []; k = args.first_train
while k < len(sess):
    train = sess[:k]; test = sess[k:k + args.block]
    tr_rows = [r for r in cands if r["d"] in train]; te_rows = [r for r in cands if r["d"] in test]
    tree = grow(tr_rows, 0, args.min_leaf, args.max_depth, [])
    taken = [r for r in te_rows if decide(tree, r)["action"] == "TAKE"]
    t_usd, t_n, t_w, t_pos, t_neg = playbook(taken)
    a_usd, a_n, a_w, _, _ = playbook(te_rows)
    l_usd, l_n = live_set_usd(test)
    folds.append(dict(train=len(train), test=test, tree_usd=round(t_usd, 1), tree_n=t_n, tree_win=round(t_w), tree_days=f"+{t_pos}/−{t_neg}",
                      all_usd=round(a_usd, 1), all_n=a_n, live_usd=round(l_usd, 1), live_n=l_n, taken_cands=len(taken), test_cands=len(te_rows)))
    k += args.block
oos_tree = sum(f["tree_usd"] for f in folds); oos_live = sum(f["live_usd"] for f in folds); oos_all = sum(f["all_usd"] for f in folds)
oos_sessions = sum(len(f["test"]) for f in folds)

# ── final tree on everything ──────────────────────────────────────────────────
final = grow(cands, 0, args.min_leaf, args.max_depth, [])
def rules(node, out):
    if node.get("leaf"):
        cond = " ∧ ".join((f"{HEB.get(f, f)} {'=' if op == '==' else '≤'} {v}" if yes else f"{HEB.get(f, f)} {'≠' if op == '==' else '>'} {v}") for f, op, v, yes in node["path"]) or "(שורש)"
        out.append(dict(rule=cond, action=node["action"], n=node["n"], win=node["win"], usd=node["usd"], avg=node["avg"])); return
    rules(node["yes"], out); rules(node["no"], out)
leaves = []; rules(final, leaves)
take_leaves = [l for l in leaves if l["action"] == "TAKE"]
ins_take = [r for r in cands if decide(final, r)["action"] == "TAKE"]
ins_usd, ins_n, ins_w, ins_pos, ins_neg = playbook(ins_take)

# ── report ────────────────────────────────────────────────────────────────────
L = []; A = L.append
A(f"# עץ-ההחלטות שמתפצל על הנסיבות — {len(sess)} סשנים, {len(cands)} מועמדים ({TODAY})")
A("")
A("**מייקל 25.09:** *\"עץ החלטות שמתפצל כל הזמן זאת הדרך הנכונה\"* · *\"אני נגד ציונים\"*. זה לא ציון: כל צומת שואל שאלה אחת על הנסיבה ומתפצל; כל עלה הוא כלל מפורש — **לקחת** או **לא** — עם מספר הדגימות מאחוריו. "
  f"מינימום {args.min_leaf} דגימות לעלה, עומק ≤{args.max_depth}. התכונות: סוג-פתיחה, סוג-יום, שלב, שעה, כיוון, מפיק, סוג-כניסה, מול כיוון-העץ, מיקום מול הערך, הרחבה, עם/נגד היום, פולבק/test, שבירת-מבנה, בר-טריגר, ווליום, דלתא, ליד-IB, ליד ערך-אתמול, על הקיצון, ברים מהקיצון, מהלך-מהפתיחה, טווח-הבר, גודל-הסטופ. "
  "מודל-הערכה קבוע: הסטופ של המפיק, יעד 1.5R, מגע-ראשון, EOD, חוזה 1, אחרי עמלות.")
A("")
A("## 1 · המבחן שקובע — אימות קדימה בזמן (העץ גדל על העבר, נשפט על ימים שלא ראה)")
A("")
A("| בלוק-מבחן | אימון | ימים | העץ: Σ$ · עסקאות · win% · ימים +/− | לקחת-הכל: Σ$ · עסקאות | הסט-הלייב של המנוע: Σ$ · עסקאות |")
A("|---|---|---|---|---|---|")
for f in folds:
    A(f"| {f['test'][0]} → {f['test'][-1]} | {f['train']} | {len(f['test'])} | **{f['tree_usd']:+.0f}$** · {f['tree_n']} · {f['tree_win']}% · {f['tree_days']} | {f['all_usd']:+.0f}$ · {f['all_n']} | {f['live_usd']:+.0f}$ · {f['live_n']} |")
A(f"| **Σ מחוץ-למדגם** | | {oos_sessions} | **{oos_tree:+.0f}$** | {oos_all:+.0f}$ | **{oos_live:+.0f}$** |")
A("")
A(f"**קריאה:** אם שורת ה-Σ של העץ גבוהה מהסט-הלייב של המנוע על אותם ימים — העלים הם ידע ולא רעש, והם הופכים לשורות-עץ במנוע (ואז הרנס יום-כולל, ואז לייב לפי הכלל). אם לא — הפיצולים מתארים את העבר בלבד.")
A("")
A(f"## 2 · העץ על כל {len(sess)} הימים — העלים כמו שהם (בתוך-המדגם: פלייבוק {ins_usd:+.0f}$, {ins_n} עסקאות, {ins_w:.0f}%, ימים +{ins_pos}/−{ins_neg})")
A("")
A("| # | הנסיבה (הענף מהשורש לעלה) | פעולה | n | win% | Σ$ | ממוצע |")
A("|---|---|---|---|---|---|---|")
for k, l in enumerate(sorted(leaves, key=lambda l: -l["avg"]), 1):
    A(f"| {k} | {l['rule']} | **{l['action']}** | {l['n']} | {l['win']}% | {l['usd']:+.0f}$ | {l['avg']:+.1f}$ |")
A("")
A("## 3 · הפיצולים הראשונים (מה מפריד הכי טוב בין מנצחות למפסידות)")
A("")
def walk(node, depth, out):
    if node.get("leaf") or depth > 2: return
    s = node["split"]; out.append(f"{'  ' * depth}- {HEB.get(s['feat'], s['feat'])} {'=' if s['op'] == '==' else '≤'} {s['value']}  (n={node['n']}, Σ{node['usd']:+.0f}$ → כן n={node['yes']['n']} {node['yes']['avg']:+.1f}$/מועמד · לא n={node['no']['n']} {node['no']['avg']:+.1f}$/מועמד)")
    walk(node["yes"], depth + 1, out); walk(node["no"], depth + 1, out)
top = []; walk(final, 0, top); L.extend(top)
A("")
md = "\n".join(L)
mp = os.path.join(ROOT, "docs", "reports", f"TREE_LEARNER_{TODAY}.md"); open(mp, "w", encoding="utf-8").write(md)
od = os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data"); os.makedirs(od, exist_ok=True)
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), params=vars(args), sessions=len(sess), candidates=len(cands), folds=folds,
               oos=dict(tree=oos_tree, live=oos_live, all=oos_all, sessions=oos_sessions), leaves=leaves, tree=final),
          open(os.path.join(od, "tree_learner.json"), "w"), ensure_ascii=False, default=str)
print(f"candidates={len(cands)} sessions={len(sess)} · walk-forward {len(folds)} blocks / {oos_sessions} sessions: TREE {oos_tree:+.0f}$ · LIVE-SET {oos_live:+.0f}$ · TAKE-ALL {oos_all:+.0f}$")
for f in folds:
    print(f"  {f['test'][0]}→{f['test'][-1]} train={f['train']}: tree {f['tree_usd']:+7.0f}$ ({f['tree_n']:3d} tr, {f['tree_win']}%, {f['tree_days']}) · all {f['all_usd']:+7.0f}$ · live {f['live_usd']:+7.0f}$ ({f['live_n']} tr)")
print(f"final tree: {len(leaves)} leaves, {len(take_leaves)} TAKE · in-sample playbook {ins_usd:+.0f}$ / {ins_n} trades / {ins_w:.0f}%")
for l in sorted(leaves, key=lambda l: -l["avg"])[:8]:
    print(f"  {l['action']:4s} n={l['n']:4d} win {l['win']:3d}% Σ{l['usd']:+8.0f}$ avg {l['avg']:+6.1f}$ | {l['rule']}")
print("→", mp)
