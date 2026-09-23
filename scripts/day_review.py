#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""day_review.py — the daily exam after every trading day (Michael 23.09 07:40):

  "מבחן על כל ימי המסחר — לסרוק את התמונה של כל יום, לסמן נקודות שבהן עסקה הייתה צריכה לצאת
   ואיך ממקסמים אותה (ראייה מלאה); אחר-כך לבדוק מה המערכת זיהתה היטב בריפליי ומה היה צריך
   לעשות אחרת כדי שזה יתפוס — כלי עבודה יומי אחרי כל יום מסחר."

Three stages per session (RTH 16:30–23:00 IL, 5-min Woodies bars = SoT):

  1. FULL VISION (hindsight)  — every zigzag leg worth catching (≥ max(12, 1.5×ATR) pts, top 5);
     for each: the IDEAL entry (first confirmable bar: stop ≤ 1 ATR behind it holds until 1.5×ATR),
     what was visible there (causal features), and how to MAXIMIZE it: what a fixed T1 (1.5×ATR),
     a chandelier trail (1×ATR) and the best-case excursion would each have captured.
  2. WHAT THE SYSTEM SAW — from `v9_decision_vectors` (kind=DECISION, one row per producer
     decision with `blocked_by` + reason + zone/day_type) joined to the ideal-entry window (±10 min)
     and to the live/shadow trades in the leg: PASSED-and-fired · PASSED-but-not-fired (slot/lock)
     · BLOCKED by gate X · OPPOSITE fired · NOBODY saw it.
  3. WHAT TO CHANGE SO IT CATCHES — a candidate per leg: relax gate X in context C (with the
     evidence counts), or a new producer for signature S, or the exit style that fits the day;
     plus the exit gap of the trades that were taken (realized vs available).

Output: data/review/<day>.json (+ merged data/review.json for the phone page), a Hebrew report
docs/reports/DAY_REVIEW_<day>.md, and the aggregate candidate table across the reviewed days —
the raw material for branches (see § BRANCH PATH in the report). Read-only on the DB. ~5 s/day.

  python3 scripts/day_review.py [--day 2026-09-22] [--days 10]   (default: the last session)
"""
import os, sys, json, argparse, collections, statistics, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "scripts")); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
import oracle_engine as oe
import review_lib as rl
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")

ap = argparse.ArgumentParser()
ap.add_argument("--day", default=None, help="session date (IL), default = last session with ≥60 RTH bars")
ap.add_argument("--days", type=int, default=1, help="review the last N sessions (ignored with --day)")
ap.add_argument("--out", default=os.path.join(ROOT, "render_mobile_relay", "static", "docs", "data"))
ap.add_argument("--md_dir", default=os.path.join(ROOT, "docs", "reports"))
# sensitivity knobs (23.09: "האם הדוח אמין?") — the defaults are the fixed evaluation model
ap.add_argument("--leg-mult", type=float, default=1.5, help="leg threshold = max(--leg-floor, mult×ATR)")
ap.add_argument("--leg-floor", type=float, default=12.0)
ap.add_argument("--stop-atr", type=float, default=1.0)
ap.add_argument("--target-atr", type=float, default=1.5)
ap.add_argument("--suffix", default="", help="write data/review<suffix>.json + no md (sensitivity runs)")
args = ap.parse_args()

# ── data ──────────────────────────────────────────────────────────────────────
bars = read_all("""select b.ts, (b.ts at time zone 'Asia/Jerusalem')::date d, (b.ts at time zone 'Asia/Jerusalem')::time t,
 b.open o, b.high h, b.low l, b.close c, b.volume v, cd.delta
 from v9_bars_5min_woodies b left join (select distinct on (ts) ts, delta from v9_bars_cumulative_delta order by ts, created_at desc) cd on cd.ts=b.ts
 where b.symbol='MES' and b.ts >= now() - interval '45 days' and (b.ts at time zone 'Asia/Jerusalem')::time between '16:30' and '23:00' order by b.ts""", {})
by_day = collections.defaultdict(list)
for b in bars: by_day[str(b["d"])].append(b)
alld = [d for d in sorted(by_day) if len(by_day[d]) >= 60]
if args.day:
    if args.day not in by_day: sys.exit(f"no bars for {args.day}")
    days = [args.day]
else:
    days = alld[-args.days:]
prev_va = {}
for k, d in enumerate(alld):
    if k:
        pb = by_day[alld[k - 1]]; prev_va[d] = oe.compute_developing_va(pb, len(pb) - 1) if len(pb) > 5 else {}
dth = {str(r["date"]): r for r in read_all("select date, day_type, opening_type from v9_day_type_history where date >= :d", {"d": alld[0]})}
since = dt.datetime.combine(dt.date.fromisoformat(days[0]), dt.time(0, 0), IL)
trades = read_all("""select id, mode, direction, entry_ts, entry_price, exit_ts, exit_price, exit_reason, pnl_usd, pnl_sierra, pattern_id_at_entry pat, t1, stop
  from v9_trades where entry_ts >= :since and mode in ('live','shadow') order by entry_ts""", {"since": since})
tr_by_day = collections.defaultdict(list)
for t in trades: tr_by_day[t["entry_ts"].astimezone(IL).date().isoformat()].append(t)

# The gateway's own decision feed = the FINAL outcome of every setup (all gates, not just the
# Dalton gate that v9_decision_vectors records): outcome ∈ blocked / shadow_only / live,
# blocked_by (dalton_intent:*, extreme_chase_guard, rr_*, entry_not_confirmed…), live_blocked_by
# (live_slot_occupied…). Rotated daily into decisions_archive/. The situation vector (zone,
# day_type) is joined from v9_decision_vectors by (ts±3s, pattern, direction) when present.
EXPORT = os.path.expanduser("~/SierraChart_Data/v9_export")
def load_decisions(d):
    paths = [os.path.join(EXPORT, "decisions_archive", f"gateway_decisions.{d}.jsonl"), os.path.join(EXPORT, "gateway_decisions.jsonl")]
    rows = []
    for p in paths:
        if not os.path.exists(p): continue
        for line in open(p, encoding="utf-8"):
            try: r = json.loads(line)
            except Exception: continue
            if r.get("event_type") not in ("GATE_DECISION", "ROUTED") or not r.get("ts"): continue
            try: ts = dt.datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
            except Exception: continue
            if ts.astimezone(IL).date().isoformat() != d: continue
            r["_ts"] = ts; rows.append(r)
        if rows: break
    rows.sort(key=lambda r: r["_ts"])
    sv = read_all("""select ts, classification, direction, phase, vector from v9_decision_vectors
      where kind='DECISION' and ts >= :a and ts < :b""", {"a": dt.datetime.combine(dt.date.fromisoformat(d), dt.time(0, 0), IL),
                                                          "b": dt.datetime.combine(dt.date.fromisoformat(d) + dt.timedelta(days=1), dt.time(0, 0), IL)})
    for r in rows:
        m = [s for s in sv if s["classification"] == r["pattern"] and s["direction"] == r["direction"] and abs((s["ts"] - r["_ts"]).total_seconds()) <= 3]
        r["_zone"] = (m[0]["vector"] or {}).get("zone") if m else None
        r["_day_type"] = (m[0]["vector"] or {}).get("day_type") if m else None
        r["_phase"] = m[0]["phase"] if m else None
    return rows
dv_by_day = {}
sess_vol = {d: sum(float(b["v"] or 0) for b in by_day[d]) for d in alld}
med_vol = statistics.median([sess_vol[d] for d in alld[-10:]])

GATE_HEB = {"dalton_intent:stand_down": "עץ-דלתון: stand-down (שלב/סוג-יום בלי כוונה)", "dalton_intent:kind": "עץ-דלתון: סוג-הכניסה לא מותר נגד ההטיה",
            "dalton_intent:bias": "עץ-דלתון: ההטיה דוחה את הכיוון", "dalton_intent:location": "עץ-דלתון: מיקום (T-319b)", "opening_lock": "נעילת-פתיחה (T-314)",
            "live_slot_occupied": "סלוט-לייב תפוס", "extreme_chase_guard": "שער-רדיפה (ELQ/קיצון)", "rr_hard_floor": "רצפת-R:R", "rr_entry_gate": "שער-R:R בכניסה",
            "entry_not_confirmed": "בר-אישור לא נסגר", "fresh_extreme": "קיצון-טרי", "fhb": "חיץ-השעה-הראשונה", "strict_risk": "בדיקות-סיכון (strict)",
            "position_mismatch": "אי-התאמת פוזיציה (T-43)"}
def gate_heb(g):
    if not g: return ""
    for k, v in GATE_HEB.items():
        if g.startswith(k): return v
    return g

def window(dec, dirn, t_from, t_to):
    return [r for r in dec if t_from <= r["_ts"] <= t_to and (dirn is None or r["direction"] == dirn)]

def review_day(d):
    bs = by_day[d]
    atr0 = oe.compute_atr(bs, min(20, len(bs) - 1)) or 6.0
    legs = rl.legs_of(bs, atr0, mult=args.leg_mult, floor=args.leg_floor)
    vr = sess_vol[d] / med_vol if med_vol else 1.0
    depth = "HIGH" if vr >= 1.2 else "LOW" if vr <= 0.8 else "NORMAL"
    meta = dth.get(d, {}); dtype = meta.get("day_type") or "?"
    live = [t for t in tr_by_day[d] if t["mode"] == "live"]; shadow = [t for t in tr_by_day[d] if t["mode"] == "shadow"]
    dec = load_decisions(d)
    o, h_, l_, c_ = bs[0]["o"], max(b["h"] for b in bs), min(b["l"] for b in bs), bs[-1]["c"]
    out_legs = []; candidates = []
    for leg in legs:
        short = leg["short"]; dirn = "SHORT" if short else "LONG"
        t0 = bs[leg["i0"]]["ts"]; t1 = bs[leg["i1"]]["ts"]
        ideal = rl.ideal_entry(bs, leg, atr0, prev_va.get(d), stop_atr=args.stop_atr, target_atr=args.target_atr)
        # ── 1. full vision: maximization from the ideal bar
        maxim = None
        if ideal:
            maxim = rl.exit_models(bs, ideal["i"], short, ideal["atr"])
        # ── 2. what the system saw
        win_live = [t for t in live if t0 <= t["entry_ts"] <= t1]
        same = sorted([t for t in win_live if t["direction"] == dirn], key=lambda t: t["entry_ts"]); opp = [t for t in win_live if t["direction"] != dirn]
        verdict = "MISSED" if ideal else "UNCATCHABLE"
        if same:
            frac = (same[0]["entry_ts"] - t0).total_seconds() / max((t1 - t0).total_seconds(), 1)
            verdict = "TOOK" if frac <= 0.4 else "LATE"
        elif opp: verdict = "OPPOSITE"
        # final outcome of every setup the gateway saw in the window (±10 min around the ideal bar):
        #   live = fired live · slot = passed everything but the live slot was taken · shadow_only = the
        #   producer is not live-enabled (measured in shadow) · blocked = gate X said no
        seen = {"passed_fired": [], "passed_not_fired": [], "shadow_only": [], "blocked": [], "opposite_passed": [], "shadow": []}
        ti = bs[ideal["i"]]["ts"] if ideal else t0
        w0, w1 = ti - dt.timedelta(minutes=10), ti + dt.timedelta(minutes=10)
        for r in window(dec, dirn, w0, w1):
            g = r.get("blocked_by") or r.get("live_blocked_by") or ""
            row = dict(time=r["_ts"].astimezone(IL).strftime("%H:%M"), pat=r["pattern"], phase=r.get("_phase"), entry=r.get("entry"),
                       gate=g, gate_heb=gate_heb(g), reason=(r.get("reason") or r.get("live_block_reason") or "")[:120],
                       zone=r.get("_zone"), day_type=r.get("_day_type"), outcome=r.get("outcome"))
            if r.get("outcome") == "live": seen["passed_fired"].append(row)
            elif r.get("outcome") == "blocked": seen["blocked"].append(row)
            elif r.get("live_blocked_by"): seen["passed_not_fired"].append(row)
            else: seen["shadow_only"].append(row)
        for r in window(dec, "LONG" if short else "SHORT", w0, w1):
            if r.get("outcome") == "live": seen["opposite_passed"].append(dict(time=r["_ts"].astimezone(IL).strftime("%H:%M"), pat=r["pattern"]))
        seen["shadow"] = sorted({t["pat"] for t in shadow if t["direction"] == dirn and w0 <= t["entry_ts"] <= w1})
        # ── 3. what to change
        change = []; cand = None
        if verdict in ("MISSED", "OPPOSITE", "LATE") and ideal:
            f = ideal["f"]; ctx = dict(phase=f["ph"], day_type=dtype, zone=f["zone"], dir=dirn, with_day=f["with_day"])
            if seen["passed_not_fired"]:
                pats = sorted({r["pat"] for r in seen["passed_not_fired"]})
                open_live = [t for t in live if t["entry_ts"] < ti and (t["exit_ts"] is None or t["exit_ts"] > ti)]
                why = f"הסלוט היה תפוס ע״י #{open_live[0]['id']} ({open_live[0]['pat']})" if open_live else gate_heb(seen["passed_not_fired"][0]["gate"])
                change.append(f"עבר את כל השערים ({', '.join(pats)}) אבל לא נורה — {why}. מועמד: עדיפות-לסלוט לפי איכות-הסטאפ, או יציאה מוקדמת מהעסקה הקודמת.")
                cand = dict(kind="slot_priority", gate=seen["passed_not_fired"][0]["gate"], **ctx, pats=pats)
            elif seen["blocked"]:
                gates = collections.Counter(r["gate"].split(" ")[0] for r in seen["blocked"])
                g, n = gates.most_common(1)[0]
                change.append(f"ראו את זה {len(seen['blocked'])} החלטות ({', '.join(sorted({r['pat'] for r in seen['blocked']}))}) ונחסמו ע״י {gate_heb(g)} — מועמד: לבדוק בריפליי אם השער הזה צריך להישאר בשלב {f['ph']} ביום {dtype} ב{rl.ZONE_HEB.get(f['zone'], f['zone'])}.")
                cand = dict(kind="relax_gate", gate=g, **ctx, pats=sorted({r["pat"] for r in seen["blocked"]}))
            elif seen["shadow_only"]:
                pats = sorted({r["pat"] for r in seen["shadow_only"]})
                change.append(f"עבר את העץ ({', '.join(pats)}) — אבל המפיקים האלה מחוברים רק לצל (לא יורים לייב). מועמד: קידום-מפיק — למדוד את {', '.join(pats)} בהקשר הזה ולפסוק אם לחבר ללייב.")
                cand = dict(kind="producer_not_live", gate="", **ctx, pats=pats)
            elif seen["shadow"]:
                change.append(f"מפיקי-צל ראו ({', '.join(seen['shadow'])}) בלי שורת-החלטה בגייטוויי — לבדוק למה הירייה לא הגיעה לשער.")
                cand = dict(kind="shadow_only", gate="", **ctx, pats=seen["shadow"])
            elif not dec:
                change.append("אין פיד-החלטות של הגייטוויי ליום הזה (הארכיון מתחיל 15.09) — אי-אפשר לומר מי ראה.")
            else:
                change.append(f"אף מפיק לא ראה. החתימה בבר-הכניסה: {rl.describe(f, short)}. מועמד: מפיק/ענף חדש לחתימה הזו (צריך ≥15 מקרים בהרנס).")
                cand = dict(kind="no_producer", gate="", **ctx, sig={k: f[k] for k in rl.FLAGS + ["range_ge_08atr", "vol_trig", "delta_with"]})
            if seen["opposite_passed"]:
                change.append(f"ובאותו חלון עבר גם הכיוון ההפוך ({', '.join(sorted({r['pat'] for r in seen['opposite_passed']}))}) — סימן שההטיה לא הייתה ברורה.")
        # exit gap of the trades taken in this leg
        exit_gap = []
        for t in same:
            realized = float(t["pnl_sierra"]) / 5.0 if t["pnl_sierra"] is not None else ((float(t["exit_price"]) - float(t["entry_price"])) * (-1 if short else 1) if t["exit_price"] is not None else None)
            avail = (float(t["entry_price"]) - leg["p1"]) if short else (leg["p1"] - float(t["entry_price"]))
            exit_gap.append(dict(id=t["id"], pat=t["pat"], time=t["entry_ts"].astimezone(IL).strftime("%H:%M"), realized=round(realized, 2) if realized is not None else None,
                                 available=round(avail, 2), reason=t["exit_reason"]))
            if realized is not None and avail - realized >= 6:
                change.append(f"#{t['id']} לקחה {realized:.2f} נק׳ מתוך {avail:.1f} שהמהלך נתן אחרי הכניסה — פער-יציאה {avail - realized:.1f} נק׳ ({'טריילינג היה נותן ' + str(maxim['trail']) if maxim else ''}).")
        if maxim and ideal:
            best = max(maxim, key=lambda k: maxim[k] if k != "max" else -1)
            change.append(f"מיקסום מהבר-האידיאלי: יעד-קבוע {maxim['t1']} · טריילינג {maxim['trail']} · מקסימום {maxim['max']} נק׳ ⇒ {'טריילינג' if maxim['trail'] > maxim['t1'] + 2 else 'יעד-קבוע מספיק'}.")
        out_legs.append(dict(dir=dirn, start=str(bs[leg["i0"]]["t"])[:5], end=str(bs[leg["i1"]]["t"])[:5], pts=round(leg["pts"], 1), from_px=leg["p0"], to_px=leg["p1"],
                             verdict=verdict, ideal=(dict(time=ideal["f"]["hour"], price=ideal["ep"], stop=ideal["stop"], captured=ideal["captured"], desc=rl.describe(ideal["f"], short),
                                                        zone=ideal["f"]["zone"], ph=ideal["f"]["ph"], with_day=ideal["f"]["with_day"]) if ideal else None),
                             maxim=maxim, seen=seen, took=[dict(id=t["id"], pat=t["pat"], time=t["entry_ts"].astimezone(IL).strftime("%H:%M"), pnl=t["pnl_sierra"] if t["pnl_sierra"] is not None else t["pnl_usd"]) for t in same + opp],
                             exit_gap=exit_gap, change=change, candidate=cand))
        if cand: candidates.append(dict(cand, day=d, pts=round(leg["pts"], 1), start=str(bs[leg["i0"]]["t"])[:5]))
    took = sum(1 for l in out_legs if l["verdict"] == "TOOK"); missed = [l for l in out_legs if l["verdict"] == "MISSED"]
    live_pnl = sum(float(t["pnl_sierra"]) if t["pnl_sierra"] is not None else float(t["pnl_usd"] or 0) for t in live)
    return dict(day=d, day_type=dtype, opening=meta.get("opening_type") or "?", depth=depth, vol_ratio=round(vr, 2), atr=round(atr0, 2),
                range=round(h_ - l_, 2), net=round(c_ - o, 2), legs=out_legs, n_legs=len(out_legs), took=took, late=sum(1 for l in out_legs if l["verdict"] == "LATE"),
                opposite=sum(1 for l in out_legs if l["verdict"] == "OPPOSITE"), missed=len(missed), missed_pts=round(sum(l["pts"] for l in missed), 1),
                available_pts=round(sum(l["pts"] for l in out_legs), 1), live_n=len(live), live_pnl=round(live_pnl, 2),
                decisions=len(dec), blocked=sum(1 for r in dec if r.get("outcome") == "blocked"),
                shadow_only=sum(1 for r in dec if r.get("outcome") == "shadow_only"), fired=sum(1 for r in dec if r.get("outcome") == "live"),
                gates=dict(collections.Counter((r.get("blocked_by") or r.get("live_blocked_by") or "").split(" ")[0] for r in dec if r.get("outcome") != "live" and (r.get("blocked_by") or r.get("live_blocked_by"))).most_common(8)),
                candidates=candidates)

# ── run ───────────────────────────────────────────────────────────────────────
os.makedirs(os.path.join(args.out, "review"), exist_ok=True); os.makedirs(args.md_dir, exist_ok=True)
V_HEB = {"TOOK": "✅ נלקחה בזמן", "LATE": "🕒 נלקחה מאוחר", "OPPOSITE": "❌ נכנסנו הפוך", "MISSED": "⭕ פוספסה", "UNCATCHABLE": "⚪ בלי בר-אישור"}
DEPTH_HEB = {"HIGH": "עומק גבוה", "NORMAL": "עומק רגיל", "LOW": "עומק נמוך"}
merged_p = os.path.join(args.out, f"review{args.suffix}.json")
merged = json.load(open(merged_p, encoding="utf-8")) if os.path.exists(merged_p) else {"days": {}}
BRANCH_PATH = [
    "## איך זה הופך לענף (הנתיב, לפי דוקטרינת-הלמידה 09.09)",
    "1. **המבחן היומי** (הכלי הזה, רץ ב-EOD) מוציא לכל מהלך שפוספס *מועמד*: `relax_gate` (ראו ונחסמו ע״י שער X בהקשר: שלב × סוג-יום × אזור-בטן × כיוון), `slot_priority` (עבר את העץ, הסלוט היה תפוס), `producer_not_live`, `shadow_only`, או `no_producer` (אף אחד לא ראה — עם חתימת-הבר).",
    "2. **צבירה**: `data/review.json` סוכם לפי (סוג-מועמד, שער, שלב, סוג-יום, אזור). מועמד שחוזר ב-≥3 ימים או ≥15 מקרים בהרנס-האחורי — עולה לרשימת-הענפים (הטבלה למטה).",
    "3. **ריפליי לפני דגל**: המועמד נכתב כשורה ב-`config/dalton_tree_v2_draft.yaml` (צל — שורות TREE_SHADOW ב-`v9_decision_vectors`) ונמדד ב-`scripts/fwd_harness.py` על 56–85 סשנים עם מודל-ההערכה הקבוע: N, אחוז-ניצחון, $ לחוזה (m1), מול העץ הנוכחי.",
    "4. **פסיקה**: רק אם המספר טוב יותר — מייקל פוסק פעם אחת, הדגל נדלק עם `measured:` ב-`config/RULED_FLAGS.yaml`, וגרסת-העץ עולה (v1.2 → v1.3). תקרית ⇒ מקרה-ריפליי בסט-הרגרסיה, לא דגל.",
    "5. **יציאות**: אותו נתיב — פער-היציאה היומי (נלקח מול זמין) מצטבר לפי סוג-יום; כשטריילינג מנצח יעד-קבוע ב-≥15 מקרים ביום-מגמה — ענף-יציאה במקום פרמטר.",
]
agg = collections.defaultdict(list)
for d in days:
    R = review_day(d)
    merged["days"][d] = R
    if not args.suffix: json.dump(R, open(os.path.join(args.out, "review", f"{d}.json"), "w"), ensure_ascii=False, default=str, indent=0)
    for c in R["candidates"]: agg[(c["kind"], c.get("gate", ""), c["phase"], c["day_type"], c["zone"], c["dir"])].append(c)
    md = [f"# מבחן-היום — {d} · {R['day_type']} · פתיחה {R['opening']} · {DEPTH_HEB[R['depth']]} (×{R['vol_ratio']}) · טווח {R['range']} נק׳ · סגירה {R['net']:+.1f}", "",
          f"**מהלכים ששווה לתפוס:** {R['n_legs']} ({R['available_pts']} נק׳) · נלקחו בזמן {R['took']} · מאוחר {R['late']} · הפוך {R['opposite']} · **פוספסו {R['missed']} ({R['missed_pts']} נק׳)** · לייב {R['live_n']} עסקאות {R['live_pnl']:+.2f}$ (ברוקר)",
          f"**מה הגייטוויי ראה:** {R['decisions']} סטאפים · נורו לייב {R['fired']} · נחסמו {R['blocked']} · עברו אבל המפיק צל-בלבד {R['shadow_only']} · שערים: " + ", ".join(f"{gate_heb(k)} {v}" for k, v in R['gates'].items()), "",
          "## 1 · ראייה מלאה — איפה עסקה הייתה צריכה לצאת ואיך ממקסמים", ""]
    for l in R["legs"]:
        md.append(f"### {l['start']}→{l['end']} {l['dir']} {l['pts']} נק׳ ({l['from_px']:.2f}→{l['to_px']:.2f}) — {V_HEB[l['verdict']]}")
        if l["ideal"]:
            i = l["ideal"]; m = l["maxim"]
            md.append(f"- כניסה-אידיאלית **{i['time']} @{i['price']:.2f}** (סטופ {i['stop']} נק׳ · המהלך נתן {i['captured']} נק׳): {i['desc']}")
            md.append(f"- מיקסום: יעד-קבוע 1.5×ATR = **{m['t1']}** · טריילינג 1×ATR = **{m['trail']}** · מקסימום {m['max']} נק׳")
        else:
            md.append("- אין בר-אישור עם סטופ ≤1 ATR בחצי הראשון — המהלך נסע בלי לתת כניסה")
        s = l["seen"]
        md.append("- **מה המערכת ראתה (±10 דק׳ מהבר-האידיאלי):** " + (
            (f"עבר ונורה: {', '.join(r['pat'] + ' ' + r['time'] for r in s['passed_fired'])}. " if s["passed_fired"] else "") +
            (f"עבר ולא נורה: {', '.join(r['pat'] + ' ' + r['time'] + ' ← ' + r['gate_heb'] for r in s['passed_not_fired'])}. " if s["passed_not_fired"] else "") +
            (f"עבר, מפיק-צל-בלבד: {', '.join(r['pat'] + ' ' + r['time'] for r in s['shadow_only'])}. " if s["shadow_only"] else "") +
            (f"נחסם: {', '.join(r['pat'] + ' ' + r['time'] + ' ← ' + r['gate_heb'] for r in s['blocked'])}. " if s["blocked"] else "") +
            (f"הפוך עבר: {', '.join(r['pat'] + ' ' + r['time'] for r in s['opposite_passed'])}. " if s["opposite_passed"] else "") +
            (f"צל: {', '.join(s['shadow'])}." if s["shadow"] else "") or "**אף אחד לא ראה.**"))
        if l["took"]: md.append("- עסקאות-לייב במהלך: " + ", ".join(f"#{t['id']} {t['pat']} {t['time']} ({t['pnl'] if t['pnl'] is not None else '—'}$)" for t in l["took"]))
        for c in l["change"]: md.append(f"- 🔧 {c}")
        md.append("")
    md += ["## 2 · המועמדים לענפים מהיום הזה", ""]
    if R["candidates"]:
        for c in R["candidates"]:
            md.append(f"- `{c['kind']}` {c.get('gate','')} · שלב {c['phase']} · {c['day_type']} · {rl.ZONE_HEB.get(c['zone'], c['zone'])} · {c['dir']} · {c['start']} ({c['pts']} נק׳)" + (f" · {', '.join(c['pats'])}" if c.get('pats') else ""))
    else:
        md.append("- אין (כל המהלכים נלקחו בזמן או לא ניתנים-לתפיסה)")
    md += [""] + BRANCH_PATH
    if not args.suffix: open(os.path.join(args.md_dir, f"DAY_REVIEW_{d}.md"), "w", encoding="utf-8").write("\n".join(md))
    print(f"{d}: legs {R['n_legs']} took {R['took']} late {R['late']} opp {R['opposite']} missed {R['missed']} ({R['missed_pts']} pts) · decisions {R['decisions']} (blocked {R['blocked']}) · candidates {len(R['candidates'])}")

# aggregate candidate table across all reviewed days (the branch list)
allc = [c for d in merged["days"].values() for c in d["candidates"]]
agg = collections.defaultdict(list)
for c in allc: agg[(c["kind"], c.get("gate", ""), c["phase"], c["day_type"], c["zone"], c["dir"])].append(c)
table = sorted(({"kind": k[0], "gate": k[1], "phase": k[2], "day_type": k[3], "zone": k[4], "dir": k[5], "n": len(v), "days": sorted({c["day"] for c in v}),
                 "pts": round(sum(c["pts"] for c in v), 1), "pats": sorted({p for c in v for p in c.get("pats", [])})} for k, v in agg.items()),
               key=lambda r: (-len(r["days"]), -r["n"]))
merged["candidates"] = table; merged["generated"] = dt.datetime.now(IL).isoformat(timespec="minutes")
merged["days"] = {d: merged["days"][d] for d in sorted(merged["days"])[-15:]}
json.dump(merged, open(merged_p, "w"), ensure_ascii=False, default=str, indent=0)
print(f"branch candidates across {len(merged['days'])} reviewed days: {len(table)} → {merged_p}")
for r in table[:12]:
    print(f"  {r['kind']:18s} {r['gate']:26s} ph={r['phase']} {r['day_type']:12s} {r['zone']:10s} {r['dir']:5s} n={r['n']} days={len(r['days'])} pts={r['pts']}")
