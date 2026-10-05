#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""supervisor.py — פיקוח והמלצות (T-536, Michael 05.10: "פיקוח והמלצות לשיפור המערכת כדי למקסם רווחים כבר מהיום",
"האם המערכת מספיק חכמה לזהות הבדלים בין כל יום מרגע שהתחלת לקבל מידע ועד היום").

Read-only. Four questions, answered from the data and never from a guess:
  1. ימים-אנלוגיים — a fingerprint for every session since the data began (prior RTH range/net · overnight range/net ·
     gap · IB width/net · first-30 net) and the K nearest sessions to today (pre-open: the overnight/prior features;
     after 17:30: the IB features too) — with their EOD day-type label, the live-config replay P&L (harness tag) and
     the live P&L. "What did the current tree do on days like today?" — observation, not a gate.
  2. ההחלטות של היום מול המספר של העלה — every DECISION row of today, blocked ones mapped to the measured leaf
     (config/decision_tree_v3.measured.json): a SKIP whose candidate-level Σ is positive is a measurement candidate.
  3. בריאות — feed age, listener, agents, flag_guard, position, label timeline (flicker count).
  4. המלצות — rules over 1–3; every recommendation is "measure X" (never "flip X"), per the 09.09 doctrine.
Outputs: docs/reports/SUPERVISION_<date>_<HHMM>.md (+ SUPERVISION_LATEST.md), render_mobile_relay/static/docs/supervision.html,
render_mobile_relay/static/docs/data/supervision.json.   usage: python3 scripts/supervisor.py [--tag t529b] [--k 8] [--quiet]
"""
import collections, datetime as dt, glob, html, json, math, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"
TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "t529b"
K = int(sys.argv[sys.argv.index("--k") + 1]) if "--k" in sys.argv else 8
QUIET = "--quiet" in sys.argv
NOW = dt.datetime.now(); TODAY = NOW.date(); HHMM = NOW.strftime("%H%M")


def sh(cmd, timeout=60):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout
    except Exception as e:  # noqa
        return "ERR %s" % e


def q(sql):
    out = sh('%s -d mems26 -Atc "%s"' % (PSQL, sql.replace('"', '\\"')), 120)
    return [r.split("|") for r in out.splitlines() if r and not r.startswith("ERR")]


def f(x):
    try:
        return float(x)
    except Exception:
        return None


# ── 1. sessions: fingerprints from the continuous 5-min bars ───────────────────────────────────────
bars = q("select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), open, high, low, close "
         "from v9_bars_5min_woodies where symbol='MES' and ts >= '2026-06-01' order by ts")
by_day = collections.OrderedDict()
for r in bars:
    if len(r) != 6:
        continue
    by_day.setdefault(r[0], []).append((r[1], f(r[2]), f(r[3]), f(r[4]), f(r[5])))


def seg(rows, a, b):
    s = [x for x in rows if a <= x[0] <= b and x[1] is not None]
    if not s:
        return None
    return {"open": s[0][1], "close": s[-1][4], "high": max(x[2] for x in s), "low": min(x[3] for x in s), "n": len(s)}


sessions = collections.OrderedDict()
prev_rth = None
for d, rows in by_day.items():
    on = seg(rows, "01:00", "16:25"); rth = seg(rows, "16:30", "22:55"); ib = seg(rows, "16:30", "17:25"); f30 = seg(rows, "16:30", "16:55")
    wd = dt.date.fromisoformat(d).weekday()
    rec = {"date": d, "weekday": wd, "has_rth": bool(rth and rth["n"] >= 30),
           "on_range": (on["high"] - on["low"]) if on else None, "on_net": (on["close"] - on["open"]) if on else None,
           "prior_range": (prev_rth["high"] - prev_rth["low"]) if prev_rth else None,
           "prior_net": (prev_rth["close"] - prev_rth["open"]) if prev_rth else None,
           "gap": (rth["open"] - prev_rth["close"]) if (rth and prev_rth) else ((on["close"] - prev_rth["close"]) if (on and prev_rth) else None),
           "ib_width": (ib["high"] - ib["low"]) if ib else None, "ib_net": (ib["close"] - ib["open"]) if ib else None,
           "f30_net": (f30["close"] - f30["open"]) if f30 else None,
           "rth_range": (rth["high"] - rth["low"]) if rth else None, "rth_net": (rth["close"] - rth["open"]) if rth else None}
    sessions[d] = rec
    if rth and rth["n"] >= 30 and wd < 5:
        prev_rth = rth
today = sessions.get(TODAY.isoformat()) or {"date": TODAY.isoformat(), "has_rth": False}
hist = [s for d, s in sessions.items() if s["has_rth"] and d < TODAY.isoformat() and s["weekday"] < 5]

# EOD labels (last DECISION label of the session) · replay P&L (harness tag) · live P&L
labels = {}
for r in q("select to_char(ts at time zone 'Asia/Jerusalem','YYYY-MM-DD'), (array_agg(vector->>'day_type' order by ts desc) filter (where coalesce(vector->>'day_type','')<>''))[1] "
           "from v9_decision_vectors where kind='DECISION' and ts>='2026-06-01' group by 1"):
    if len(r) == 2 and r[1]:
        labels[r[0]] = r[1]
for r in q("select to_char(coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem','YYYY-MM-DD'), mode() within group (order by day_type_at_entry) "
           "from v9_trades where day_type_at_entry is not null and day_type_at_entry<>'' group by 1"):
    if len(r) == 2 and r[1]:
        labels.setdefault(r[0], r[1])
live_pnl = {r[0]: f(r[1]) for r in q("select to_char(coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem','YYYY-MM-DD'), sum(coalesce(pnl_sierra,pnl_usd,0)) "
                                       "from v9_trades where mode='live' and state='CLOSED' group by 1") if len(r) == 2}
replay = {}
for p in glob.glob(os.path.join(ROOT, "harness_out", "t466", "%s_2026-*.json" % TAG)):
    d = os.path.basename(p)[len(TAG) + 1:len(TAG) + 11]
    try:
        j = json.load(open(p))
        replay[d] = {"pnl": f(j.get("daily_pnl_harness")) or 0.0,
                     "trades": [{"p": t.get("classification"), "d": t.get("direction"), "usd": f(t.get("pnl_usd")) or 0.0, "o": t.get("outcome")} for t in j.get("trades", [])]}
    except Exception:
        pass

# analogs: standardized distance over the features known now
pre_feats = ["prior_range", "prior_net", "on_range", "on_net", "gap"]
post_feats = pre_feats + ["ib_width", "ib_net", "f30_net"]
feats = post_feats if (today.get("ib_width") and NOW.strftime("%H:%M") >= "17:30") else pre_feats
feats = [k for k in feats if today.get(k) is not None]
stats = {}
for k in feats:
    vals = [s[k] for s in hist if s.get(k) is not None]
    if len(vals) >= 5:
        m = sum(vals) / len(vals); sd = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals)) or 1.0
        stats[k] = (m, sd)
feats = [k for k in feats if k in stats]
analogs = []
for s in hist:
    if any(s.get(k) is None for k in feats):
        continue
    dist = math.sqrt(sum(((s[k] - today[k]) / stats[k][1]) ** 2 for k in feats)) if feats else 9.9
    analogs.append((dist, s))
analogs.sort(key=lambda x: x[0])
analog_rows = []
for dist, s in analogs[:K]:
    d = s["date"]; rp = replay.get(d)
    analog_rows.append({"date": d, "dist": round(dist, 2), "label": labels.get(d, "?"), "replay": (rp["pnl"] if rp else None),
                        "live": live_pnl.get(d), "rth_range": s.get("rth_range"), "rth_net": s.get("rth_net"),
                        "replay_trades": [t for t in (rp["trades"] if rp else [])]})
an_rep = [a["replay"] for a in analog_rows if a["replay"] is not None]
an_sum = round(sum(an_rep), 2) if an_rep else None
an_pos = sum(1 for v in an_rep if v > 0)
leaf_on_analogs = collections.defaultdict(lambda: [0, 0.0])
for a in analog_rows:
    for t in a["replay_trades"]:
        leaf_on_analogs[t["p"] or "?"][0] += 1; leaf_on_analogs[t["p"] or "?"][1] += t["usd"]

# history by label: replay P&L of the current config by EOD label (the "does it know day types" answer, in numbers)
by_label = collections.defaultdict(lambda: [0, 0.0, 0])
for d, rp in replay.items():
    lb = labels.get(d, "?"); by_label[lb][0] += 1; by_label[lb][1] += rp["pnl"]; by_label[lb][2] += 1 if rp["pnl"] > 0 else 0

# ── 2. today's decisions vs the measured leaf ──────────────────────────────────────────────────────
try:
    measured = json.load(open(os.path.join(ROOT, "config", "decision_tree_v3.measured.json"), encoding="utf-8"))
except Exception:
    measured = {}
dec = q("select to_char(ts at time zone 'Asia/Jerusalem','HH24:MI'), classification, direction, entry, coalesce(blocked_by,''), coalesce(reason,''), coalesce(vector->>'day_type',''), coalesce(vector->>'phase','') "
        "from v9_decision_vectors where kind='DECISION' and (ts at time zone 'Asia/Jerusalem')::date = current_date order by ts")
decisions = []; label_seq = []
for r in dec:
    if len(r) < 8:
        continue
    t, cls, direction, entry, blocked, reason, dtl, ph = r[:8]
    m = re.search(r"\[(opening_type=[^\]]+)\]", reason); path = m.group(1) if m else ""
    leaf = measured.get(path) or {}
    decisions.append({"t": t, "pattern": cls, "dir": direction, "entry": f(entry), "blocked": blocked, "path": path, "day_type": dtl, "phase": ph,
                      "leaf_n": leaf.get("n"), "leaf_win": leaf.get("win"), "leaf_usd": leaf.get("usd")})
    if dtl and t >= "16:30":  # T-542: RTH rows only — pre-open rows carry pending/replayed labels
        label_seq.append(dtl)
transitions = sum(1 for i in range(1, len(label_seq)) if label_seq[i] != label_seq[i - 1])
fired = [d for d in decisions if not d["blocked"]]
blocked_pos = sorted([d for d in decisions if d["blocked"] and (d["leaf_n"] or 0) >= 30 and (d["leaf_usd"] or 0) >= 100], key=lambda d: -(d["leaf_usd"] or 0))
live_today = q("select id, pattern_id_at_entry, direction, entry_price, exit_price, outcome, coalesce(pnl_sierra,pnl_usd), to_char(entry_ts at time zone 'Asia/Jerusalem','HH24:MI') "
               "from v9_trades where mode='live' and (coalesce(entry_ts,created_at) at time zone 'Asia/Jerusalem')::date=current_date order by entry_ts")

# ── 3. health ──────────────────────────────────────────────────────────────────────────────────────
mx = q("select round(extract(epoch from (now()-max(ts)))/60) from v9_bars_5min_woodies"); feed_age_min = f(mx[0][0]) if mx and mx[0] else None
listener = sh("lsof -nP -iTCP:8000 -sTCP:LISTEN | tail -n +2 | awk '{print $2}'").strip()
agents = sh("launchctl list | grep -c mems26").strip()
fg = subprocess.run("python3 scripts/flag_guard.py >/dev/null 2>&1; echo $?", shell=True, capture_output=True, text=True).stdout.strip()
try:
    st = json.load(open("/Users/michael/SierraChart_Data/v9_export/sierra_state.json"))
    pos, cash = st.get("position_qty"), st.get("acct_cash_balance")
except Exception:
    pos, cash = None, None
ctx = {}
try:
    ctx = (json.loads(sh("curl -s -m 6 http://127.0.0.1:8000/api/v9/tree/state")) or {}).get("context") or {}
except Exception:
    pass
health = {"feed_age_min": feed_age_min, "listener_pid": listener, "agents": agents, "flag_guard_rc": fg, "position": pos, "cash": cash,
          "label_now": ctx.get("day_type"), "phase": ctx.get("phase"), "structure": ctx.get("structure"), "hint": ctx.get("hint") or ctx.get("tree_hint"),
          "price": ctx.get("price"), "label_transitions_today": transitions, "labels_today": label_seq[-12:]}
red = []
if feed_age_min is not None and feed_age_min > 10 and NOW.weekday() < 5 and "16:30" <= NOW.strftime("%H:%M") <= "23:00":
    red.append("feed: הבר האחרון בן %d דק׳ בתוך RTH" % feed_age_min)
if not listener:
    red.append("אין מאזין על :8000")
if agents != "9":
    red.append("LaunchAgents רשומים: %s/9" % agents)
if fg != "0":
    red.append("flag_guard נכשל")
if transitions >= 3:
    red.append("תווית סוג-היום ריצדה %d פעמים היום" % transitions)

# ── 4. recommendations (measure, never flip) ──────────────────────────────────────────────────────
recs = []
for d in blocked_pos[:3]:
    recs.append("למדוד יום-שלם: `%s` %s @%s נחסם `%s` על עלה שמרוויח ברמת-מועמד (n=%s · %s%% · %+.0f$) — וריאנט בהרנס מול ייחוס-אותו-לילה, לא דגל." % (d["pattern"], d["dir"], d["entry"], d["blocked"], d["leaf_n"], d["leaf_win"], d["leaf_usd"] or 0))
for d in fired:
    if (d["leaf_n"] or 0) >= 30 and (d["leaf_usd"] or 0) <= -100:
        recs.append("ירינו על עלה שמפסיד ברמת-מועמד: `%s` %s (n=%s · %+.0f$) — לבדוק את העלה ביום-שלם." % (d["pattern"], d["dir"], d["leaf_n"], d["leaf_usd"]))
if an_sum is not None:
    recs.append("ימים-אנלוגיים (%d הקרובים לפי %s): קונפיג-הלייב בריפליי Σ %+.2f$ · %d/%d ימים חיוביים — תצפית, לא שער: היום עצמו יענה." % (len(an_rep), " · ".join(feats), an_sum, an_pos, len(an_rep)))
if transitions >= 3:
    recs.append("תווית סוג-היום ריצדה %d פעמים — מועמד להיסטרזיס (בר-אישור לפני החלפת-תווית), דגל-כבוי + מדידה (WORK_PLAN שבוע 2)." % transitions)
if not recs:
    recs.append("אין המלצה חדשה מהנתונים של עכשיו — המדידות הפתוחות: T-531 · T-528 · T-530 · T-535 (סוכן-התיקונים).")

out = {"generated": NOW.strftime("%Y-%m-%d %H:%M"), "tag": TAG, "today": today, "features_used": feats, "analogs": analog_rows,
       "analog_sum": an_sum, "analog_pos": an_pos, "leaf_on_analogs": {k: {"n": v[0], "usd": round(v[1], 2)} for k, v in leaf_on_analogs.items()},
       "by_label": {k: {"days": v[0], "usd": round(v[1], 2), "pos_days": v[2]} for k, v in by_label.items()},
       "decisions": decisions, "fired": len(fired), "blocked_pos": blocked_pos[:5], "live_today": live_today, "health": health, "red": red, "recs": recs,
       "sessions_total": len(hist), "labeled": sum(1 for s in hist if s["date"] in labels)}
os.makedirs("render_mobile_relay/static/docs/data", exist_ok=True)
json.dump(out, open("render_mobile_relay/static/docs/data/supervision.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)

# ── markdown ───────────────────────────────────────────────────────────────────────────────────────
def fmt(v, nd=2):
    return "—" if v is None else ("%+.*f" % (nd, v))


L = ["# פיקוח והמלצות · %s (ייחוס-ריפליי `%s`)" % (out["generated"], TAG), ""]
L.append("**בריאות:** feed %s דק׳ · מאזין %s · סוכנים %s/9 · flag_guard %s · פוזיציה %s · מזומן %s · תווית עכשיו %s (שלב %s, מבנה %s, הטיה %s) · מחיר %s · ריצודי-תווית היום: %d" %
         (health["feed_age_min"], health["listener_pid"] or "—", health["agents"], "PASS" if fg == "0" else "FAIL", pos, cash, health["label_now"], health["phase"], health["structure"], health["hint"], health["price"], transitions))
if red:
    L.append("\n🔴 **אדומים:** " + " · ".join(red))
L.append("\n## 1 · האם המערכת מבחינה בין ימים? — המספרים\n")
L.append("סשנים עם RTH מאז יוני: **%d** · עם תווית-EOD: **%d** · עם ריפליי של קונפיג-הלייב: **%d**. ריפליי קונפיג-הלייב לפי תווית-EOD:\n" % (len(hist), out["labeled"], len(replay)))
L.append("| תווית | ימים | Σ ריפליי | ימים חיוביים |\n|---|---|---|---|")
for k, v in sorted(by_label.items(), key=lambda kv: -kv[1][0]):
    L.append("| %s | %d | %s | %d |" % (k, v[0], fmt(v[1]), v[2]))
L.append("\n## 2 · ימים-אנלוגיים להיום (מאפיינים: %s)\n" % (" · ".join(feats) or "—"))
L.append("היום: " + " · ".join("%s=%s" % (k, fmt(today.get(k))) for k in feats))
L.append("\n| תאריך | מרחק | תווית-EOD | ריפליי | לייב | טווח-RTH | נטו-RTH | עסקאות-ריפליי |\n|---|---|---|---|---|---|---|---|")
for a in analog_rows:
    L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (a["date"], a["dist"], a["label"], fmt(a["replay"]), fmt(a["live"]), fmt(a["rth_range"]), fmt(a["rth_net"]),
                                                     " · ".join("%s %s %+.0f" % (t["p"], (t["d"] or "")[:1], t["usd"]) for t in a["replay_trades"]) or "—"))
L.append("\n**על האנלוגים:** Σ ריפליי %s · %d/%d ימים חיוביים. לפי תבנית: %s" % (fmt(an_sum), an_pos, len(an_rep), " · ".join("%s n=%d %+.0f$" % (k, v[0], v[1]) for k, v in sorted(leaf_on_analogs.items(), key=lambda kv: -kv[1][1])) or "—"))
L.append("\n## 3 · ההחלטות של היום (%d) · ירו %d · לייב %d\n" % (len(decisions), len(fired), len(live_today)))
L.append("| שעה | תבנית | כיוון | מחיר | חסימה | העלה (n · win · $) |\n|---|---|---|---|---|---|")
for d in decisions[-40:]:
    L.append("| %s | %s | %s | %s | %s | %s |" % (d["t"], d["pattern"], d["dir"], d["entry"], d["blocked"] or "✅ ירה", ("%s · %s%% · %s" % (d["leaf_n"], d["leaf_win"], fmt(d["leaf_usd"], 0))) if d["leaf_n"] else "—"))
if live_today:
    L.append("\n**לייב היום:** " + " · ".join("#%s %s %s @%s → %s %s" % (r[0], r[1], r[2], r[3], r[5], fmt(f(r[6]))) for r in live_today if len(r) >= 7))
L.append("\n## 4 · המלצות (מדידה — לא הדלקה)\n")
for i, rc in enumerate(recs, 1):
    L.append("%d. %s" % (i, rc))
md = "\n".join(L) + "\n"
os.makedirs("docs/reports", exist_ok=True)
open("docs/reports/SUPERVISION_%s_%s.md" % (TODAY.isoformat(), HHMM), "w", encoding="utf-8").write(md)
open("docs/reports/SUPERVISION_LATEST.md", "w", encoding="utf-8").write(md)

# ── phone page (self-contained) ────────────────────────────────────────────────────────────────────
def esc(s):
    return html.escape(str(s))


rows_an = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(a["date"]), esc(a["label"]), esc(fmt(a["replay"])), esc(fmt(a["live"])), esc(fmt(a["rth_net"])),
                  esc(" · ".join("%s %+.0f" % (t["p"], t["usd"]) for t in a["replay_trades"]) or "—")) for a in analog_rows)
rows_lb = "".join("<tr><td>%s</td><td>%d</td><td>%s</td><td>%d</td></tr>" % (esc(k), v[0], esc(fmt(v[1])), v[2]) for k, v in sorted(by_label.items(), key=lambda kv: -kv[1][0]))
rows_dec = "".join("<tr><td>%s</td><td>%s %s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(d["t"]), esc(d["pattern"]), esc((d["dir"] or "")[:1]), esc(d["entry"]), esc(d["blocked"] or "✅"),
                   esc(("%s·%s%%·%s" % (d["leaf_n"], d["leaf_win"], fmt(d["leaf_usd"], 0))) if d["leaf_n"] else "—")) for d in decisions[-40:])
recs_html = "".join("<li>%s</li>" % esc(rc).replace("`", "") for rc in recs)
red_html = ("<div class='red'>🔴 " + esc(" · ".join(red)) + "</div>") if red else "<div class='ok'>🟢 אין אדומים</div>"
page = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>פיקוח והמלצות · MEMS26</title><style>body{font-family:-apple-system,Segoe UI,Arial;background:#0b0f14;color:#e6edf3;margin:0;padding:12px}
h1{font-size:18px;margin:0 0 6px}h2{font-size:15px;margin:16px 0 6px;color:#9fd3ff}table{border-collapse:collapse;width:100%%;font-size:12px}td,th{border-bottom:1px solid #223;padding:4px 5px;text-align:right}
th{color:#9fb3c8}.red{background:#3a1212;padding:8px;border-radius:8px}.ok{background:#12301c;padding:8px;border-radius:8px}.k{color:#9fb3c8;font-size:12px}li{margin:6px 0}
.box{background:#121a24;border-radius:10px;padding:10px;margin:8px 0}</style></head><body>
<h1>🛡️ פיקוח והמלצות</h1><div class="k">נוצר %s · ייחוס-ריפליי %s · <a style="color:#9fd3ff" href="index.html">← תפריט</a></div>
<div class="box">%s<div class="k" style="margin-top:6px">feed %s דק׳ · מאזין %s · סוכנים %s/9 · flag_guard %s · פוזיציה %s · מזומן %s · תווית %s (שלב %s · מבנה %s · הטיה %s) · מחיר %s · ריצודי-תווית %d</div></div>
<h2>1 · האם המערכת מבחינה בין ימים — במספרים</h2><div class="k">סשנים מאז יוני %d · עם תווית %d · עם ריפליי %d. ריפליי קונפיג-הלייב לפי תווית-EOD:</div>
<table><tr><th>תווית</th><th>ימים</th><th>Σ ריפליי</th><th>חיוביים</th></tr>%s</table>
<h2>2 · ימים-אנלוגיים להיום</h2><div class="k">מאפיינים: %s · היום: %s</div>
<table><tr><th>תאריך</th><th>תווית</th><th>ריפליי</th><th>לייב</th><th>נטו-RTH</th><th>עסקאות-ריפליי</th></tr>%s</table>
<div class="k">Σ ריפליי על האנלוגים %s · %d/%d חיוביים — תצפית, לא שער.</div>
<h2>3 · ההחלטות של היום (%d · ירו %d)</h2><table><tr><th>שעה</th><th>תבנית</th><th>מחיר</th><th>חסימה</th><th>העלה n·win·$</th></tr>%s</table>
<h2>4 · המלצות (מדידה, לא הדלקה)</h2><ol>%s</ol>
</body></html>""" % (esc(out["generated"]), esc(TAG), red_html, esc(health["feed_age_min"]), esc(health["listener_pid"] or "—"), esc(health["agents"]), "PASS" if fg == "0" else "FAIL", esc(pos), esc(cash),
                     esc(health["label_now"]), esc(health["phase"]), esc(health["structure"]), esc(health["hint"]), esc(health["price"]), transitions,
                     len(hist), out["labeled"], len(replay), rows_lb, esc(" · ".join(feats) or "—"), esc(" · ".join("%s=%s" % (k, fmt(today.get(k))) for k in feats)), rows_an,
                     esc(fmt(an_sum)), an_pos, len(an_rep), len(decisions), len(fired), rows_dec, recs_html)
open("render_mobile_relay/static/docs/supervision.html", "w", encoding="utf-8").write(page)
if not QUIET:
    print("supervision: sessions %d · labeled %d · replay %d · analogs %d (Σ %s, %d pos) · decisions today %d (fired %d) · red %d · recs %d" %
          (len(hist), out["labeled"], len(replay), len(analog_rows), an_sum, an_pos, len(decisions), len(fired), len(red), len(recs)))
