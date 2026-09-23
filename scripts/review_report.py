#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_report.py — the consolidated replay report over every reviewed day (Michael 23.09 09:20:
"לא קיבלתי דיווח מסודר לגבי ריפליי בגישה הזאת של כל הימים — מה היה צריך לבצע ומה צריך לתקן").

Reads data/review.json (written by scripts/day_review.py) and writes one ordered Hebrew document:
  § A  the scoreboard — per day: moves worth catching, taken/late/opposite/missed, points, live P&L (broker)
  § B  day by day — what SHOULD have been done (ideal entry + maximization) and what the system did
  § C  what to FIX — ranked: gates that blocked ideal entries, producers that only shadow, moves nobody sees,
       exit gaps; each with days · points · the replay it needs
  § D  the branch path
Outputs: docs/reports/REPLAY_REVIEW_<date>.md · render_mobile_relay/static/docs/review_report.html (phone)
         · static/docs/REPLAY_REVIEW_<date>.pdf (headless Chrome, if available)
"""
import os, sys, json, html, collections, datetime as dt, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "render_mobile_relay", "static", "docs")
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem")
NOW = dt.datetime.now(IL); TODAY = NOW.date().isoformat()
RV = json.load(open(os.path.join(OUT, "data", "review.json"), encoding="utf-8"))
days = sorted(RV["days"])
D = RV["days"]
HEB_WD = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
V_HEB = {"TOOK": "✅ בזמן", "LATE": "🕒 מאוחר", "OPPOSITE": "❌ הפוך", "MISSED": "⭕ פוספסה", "UNCATCHABLE": "⚪ בלי בר-אישור"}
KIND_HEB = {"relax_gate": "שער חסם כניסה נכונה", "slot_priority": "עבר הכל, הסלוט היה תפוס", "producer_not_live": "המפיק שראה מחובר רק לצל",
            "shadow_only": "צל ראה, הגייטוויי לא", "no_producer": "אף מפיק לא רואה את זה"}
GATE_HEB = {"dalton_intent:stand_down": "עץ-דלתון: stand-down (שלב/סוג-יום בלי כוונה)", "dalton_intent:kind": "עץ-דלתון: סוג-הכניסה אסור נגד ההטיה",
            "dalton_intent:bias": "עץ-דלתון: ההטיה דוחה את הכיוון", "dalton_intent:location": "עץ-דלתון: מיקום (T-319b)", "extreme_chase_guard": "שער-רדיפה (ELQ)",
            "rr_hard_floor": "רצפת-R:R", "rr_entry_gate": "שער-R:R", "entry_not_confirmed": "בר-אישור לא נסגר", "live_slot_occupied": "סלוט-לייב תפוס"}
ZONE_HEB = {"ABOVE_VA": "מעל הבטן", "BELOW_VA": "מתחת לבטן", "IN_VA": "בתוך הבטן", "AT_POC": "על ה-POC", "UNKNOWN": "?"}
DIR_HEB = {"LONG": "לונג", "SHORT": "שורט"}
def g(x):
    for k, v in GATE_HEB.items():
        if x and x.startswith(k): return v
    return x or ""

# ── § A scoreboard ─────────────────────────────────────────────────────────────
tot = dict(legs=0, avail=0.0, took=0, late=0, opp=0, missed=0, missed_pts=0.0, live_n=0, live_pnl=0.0, dec=0, blocked=0)
for d in days:
    R = D[d]
    tot["legs"] += R["n_legs"]; tot["avail"] += R["available_pts"]; tot["took"] += R["took"]; tot["late"] += R["late"]; tot["opp"] += R["opposite"]
    tot["missed"] += R["missed"]; tot["missed_pts"] += R["missed_pts"]; tot["live_n"] += R["live_n"]; tot["live_pnl"] += R["live_pnl"]; tot["dec"] += R["decisions"]; tot["blocked"] += R["blocked"]
# points actually captured by live trades inside the legs (broker), and points available in those legs
cap = 0.0; avail_in_taken = 0.0
for d in days:
    for l in D[d]["legs"]:
        for e in l["exit_gap"]:
            if e["realized"] is not None: cap += e["realized"]; avail_in_taken += e["available"]

# ── § C what to fix — aggregate ────────────────────────────────────────────────
cands = collections.defaultdict(lambda: dict(n=0, days=set(), pts=0.0, pats=set(), examples=[]))
for d in days:
    for c in D[d]["candidates"]:
        key = (c["kind"], c.get("gate", ""), c["phase"], c["day_type"], c["zone"], c["dir"])
        a = cands[key]; a["n"] += 1; a["days"].add(d); a["pts"] += c["pts"]; a["pats"] |= set(c.get("pats", [])); a["examples"].append(f'{d[8:]}.{d[5:7]} {c["start"]} {DIR_HEB[c["dir"]]} {c["pts"]:.0f}')
fix_rows = sorted(cands.items(), key=lambda kv: (-len(kv[1]["days"]), -kv[1]["pts"]))
# gates that blocked an ideal entry (any leg with verdict MISSED/OPPOSITE/LATE): count by gate
gate_hits = collections.Counter(); gate_pts = collections.Counter(); gate_days = collections.defaultdict(set)
for d in days:
    for l in D[d]["legs"]:
        if l["verdict"] in ("MISSED", "OPPOSITE", "LATE") and l["ideal"]:
            for r in l["seen"]["blocked"]:
                k = r["gate"].split(" ")[0]; gate_hits[k] += 1; gate_pts[k] += l["pts"]; gate_days[k].add(d)
# exit gaps
gaps = []
for d in days:
    for l in D[d]["legs"]:
        for e in l["exit_gap"]:
            if e["realized"] is not None and e["available"] - e["realized"] >= 6:
                gaps.append(dict(day=d, id=e["id"], pat=e["pat"], realized=e["realized"], available=e["available"], gap=e["available"] - e["realized"], maxim=l["maxim"], dt=D[d]["day_type"]))
gaps.sort(key=lambda x: -x["gap"])
# by day type
by_dt = collections.defaultdict(lambda: dict(days=0, legs=0, missed=0, pts=0.0, missed_pts=0.0, took=0))
for d in days:
    R = D[d]; b = by_dt[R["day_type"]]; b["days"] += 1; b["legs"] += R["n_legs"]; b["missed"] += R["missed"]; b["pts"] += R["available_pts"]; b["missed_pts"] += R["missed_pts"]; b["took"] += R["took"]

# ── build markdown + html together ─────────────────────────────────────────────
md = []; H = []
def h(s): return html.escape(s)
def both(md_line, html_line=None):
    md.append(md_line); H.append(html_line if html_line is not None else f"<p>{h(md_line)}</p>")

title = f"דוח-ריפליי מסודר — {len(days)} ימי-מסחר ({days[0][8:]}.{days[0][5:7]}–{days[-1][8:]}.{days[-1][5:7]}) · מה היה צריך לבצע ומה צריך לתקן"
md.append(f"# {title}"); H.append(f"<h1>{h(title)}</h1>")
md.append(f"*נוצר {NOW.strftime('%d.%m.%Y %H:%M')} מ-`scripts/day_review.py` (המבחן-היומי) · המספרים: נקודות MES, חוזה אחד, לייב = ברוקר.*")
H.append(f'<div class="dim">נוצר {NOW.strftime("%d.%m.%Y %H:%M")} מהמבחן-היומי · נקודות MES · חוזה אחד · לייב = מספר-הברוקר</div>')
md.append(""); md.append("**השיטה (ראייה מלאה, סיבתי):** לכל סשן — 5 המהלכים הגדולים (≥ max(12 נק׳, 1.5×ATR)); לכל מהלך הכניסה-האידיאלית = הבר הראשון בחצי-הראשון שממנו סטופ ≤1 ATR מאחורי הבר מחזיק עד 1.5×ATR; ואז מה הגייטוויי ראה ב-±10 דק׳ (מפיד-ההחלטות הסופי: נורה / נחסם-ע״י-שער / עבר-אבל-המפיק-צל-בלבד / אף-אחד).")
H.append('<div class="card" style="padding:10px 12px"><b>השיטה (ראייה מלאה, סיבתי):</b> לכל סשן — 5 המהלכים הגדולים (≥ max(12 נק׳, 1.5×ATR)); לכל מהלך הכניסה-האידיאלית = הבר הראשון בחצי-הראשון שממנו סטופ ≤1 ATR מחזיק עד 1.5×ATR; ואז מה הגייטוויי ראה ב-±10 דק׳ (נורה / נחסם-ע״י-שער / עבר-אבל-המפיק-צל-בלבד / אף-אחד).</div>')

# § A
md += ["", "## א · לוח-התוצאות", "", "| יום | סוג-יום | מהלכים (נק׳) | בזמן | מאוחר | הפוך | פוספסו (נק׳) | לייב (ברוקר) | הגייטוויי: סטאפים / נחסמו |", "|---|---|---|---|---|---|---|---|---|"]
H.append('<h2>א · לוח-התוצאות</h2><div style="overflow-x:auto"><table class="plain"><tr><th>יום</th><th>סוג-יום</th><th>מהלכים</th><th>בזמן</th><th>מאוחר</th><th>הפוך</th><th>פוספסו</th><th>לייב</th><th>סטאפים/נחסמו</th></tr>')
for d in days:
    R = D[d]; dd = dt.date.fromisoformat(d)
    md.append(f"| {HEB_WD[dd.weekday()]} {d[8:]}.{d[5:7]} | {R['day_type']} | {R['n_legs']} ({R['available_pts']:.0f}) | {R['took']} | {R['late']} | {R['opposite']} | **{R['missed']}** ({R['missed_pts']:.0f}) | {R['live_n']} · {R['live_pnl']:+.2f}$ | {R['decisions']} / {R['blocked']} |")
    pn = "pos" if R["live_pnl"] > 0 else "neg" if R["live_pnl"] < 0 else ""
    H.append(f'<tr><td><a href="days/{d}.html">{HEB_WD[dd.weekday()][:1]}׳ {d[8:]}.{d[5:7]}</a></td><td>{h(R["day_type"])}</td><td class="num">{R["n_legs"]} ({R["available_pts"]:.0f})</td><td class="num">{R["took"]}</td><td class="num">{R["late"]}</td><td class="num">{R["opposite"]}</td><td class="num"><b>{R["missed"]}</b> ({R["missed_pts"]:.0f})</td><td class="num"><span class="{pn}">{R["live_pnl"]:+.0f}$</span> ({R["live_n"]})</td><td class="num">{R["decisions"]}/{R["blocked"]}</td></tr>')
md.append(f"| **סה״כ** | {len(days)} ימים | **{tot['legs']} ({tot['avail']:.0f})** | **{tot['took']}** | {tot['late']} | {tot['opp']} | **{tot['missed']} ({tot['missed_pts']:.0f})** | {tot['live_n']} · **{tot['live_pnl']:+.2f}$** | {tot['dec']} / {tot['blocked']} |")
H.append(f'<tr><td><b>סה״כ</b></td><td>{len(days)} ימים</td><td class="num"><b>{tot["legs"]} ({tot["avail"]:.0f})</b></td><td class="num"><b>{tot["took"]}</b></td><td class="num">{tot["late"]}</td><td class="num">{tot["opp"]}</td><td class="num"><b>{tot["missed"]} ({tot["missed_pts"]:.0f})</b></td><td class="num"><b>{tot["live_pnl"]:+.0f}$</b> ({tot["live_n"]})</td><td class="num">{tot["dec"]}/{tot["blocked"]}</td></tr></table></div>')
pct = 100.0 * tot["took"] / max(tot["legs"], 1)
line = (f"**השורה התחתונה:** מתוך {tot['legs']} מהלכים ששווה לתפוס ({tot['avail']:.0f} נק׳ = {tot['avail']*5:,.0f}$ לחוזה) נלקחו בזמן {tot['took']} ({pct:.0f}%), {tot['late']} מאוחר, {tot['opp']} הפוך, ו-**{tot['missed']} פוספסו לגמרי ({tot['missed_pts']:.0f} נק׳ = {tot['missed_pts']*5:,.0f}$)**. "
        f"העסקאות שכן נכנסו בתוך המהלכים לקחו {cap:.1f} נק׳ מתוך {avail_in_taken:.1f} שהמהלך נתן אחריהן ({100*cap/max(avail_in_taken,1):.0f}%). הגייטוויי ראה {tot['dec']} סטאפים וחסם {tot['blocked']} ({100*tot['blocked']/max(tot['dec'],1):.0f}%).")
both(line, f'<div class="card" style="padding:10px 12px">{h(line).replace("**","")}</div>')
md += ["", "**לפי סוג-יום:**", "", "| סוג-יום | ימים | מהלכים (נק׳) | בזמן | פוספסו (נק׳) |", "|---|---|---|---|---|"]
H.append('<h3>לפי סוג-יום</h3><table class="plain"><tr><th>סוג-יום</th><th>ימים</th><th>מהלכים (נק׳)</th><th>בזמן</th><th>פוספסו (נק׳)</th></tr>')
for k, b in sorted(by_dt.items(), key=lambda kv: -kv[1]["missed_pts"]):
    md.append(f"| {k} | {b['days']} | {b['legs']} ({b['pts']:.0f}) | {b['took']} | {b['missed']} ({b['missed_pts']:.0f}) |")
    H.append(f'<tr><td>{h(k)}</td><td class="num">{b["days"]}</td><td class="num">{b["legs"]} ({b["pts"]:.0f})</td><td class="num">{b["took"]}</td><td class="num">{b["missed"]} ({b["missed_pts"]:.0f})</td></tr>')
H.append('</table>')

# § B day by day
md += ["", "## ב · יום אחרי יום — מה היה צריך לבצע, ומה המערכת עשתה", ""]
H.append('<h2>ב · יום אחרי יום — מה היה צריך לבצע, ומה המערכת עשתה</h2>')
for d in reversed(days):
    R = D[d]; dd = dt.date.fromisoformat(d)
    hdr = f"{HEB_WD[dd.weekday()]} {d[8:]}.{d[5:7]} · {R['day_type']} · פתיחה {R['opening']} · טווח {R['range']:.0f} נק׳ · סגירה {R['net']:+.1f} · לייב {R['live_n']} עסקאות {R['live_pnl']:+.2f}$"
    md.append(f"### {hdr}"); H.append(f'<div class="card open"><div class="row"><div class="grow"><div class="hl">{h(hdr)}</div></div></div><div class="body">')
    for l in R["legs"]:
        head = f"{l['start']}→{l['end']} {DIR_HEB[l['dir']]} {l['pts']:.1f} נק׳ — {V_HEB[l['verdict']]}"
        should = ""
        if l["ideal"]:
            i = l["ideal"]; m = l["maxim"]
            best = "טריילינג" if m and m["trail"] > m["t1"] + 2 else "יעד-קבוע"
            should = f"**היה צריך:** {DIR_HEB[l['dir']]} ב-{i['time']} @{i['price']:.2f}, סטופ {i['stop']} נק׳ — המהלך נתן {i['captured']} נק׳; מיקסום: יעד-קבוע {m['t1']} · טריילינג {m['trail']} · מקסימום {m['max']} ⇒ {best}."
        else:
            should = "**היה צריך:** אין בר-אישור עם סטופ ≤1 ATR בחצי-הראשון — מהלך שנסע בלי לתת כניסה (לא נספר כפספוס)."
        s = l["seen"]; saw = []
        if s["passed_fired"]: saw.append("נורה: " + ", ".join(f"{r['pat']} {r['time']}" for r in s["passed_fired"]))
        if s["passed_not_fired"]: saw.append("עבר ולא נורה: " + ", ".join(f"{r['pat']} {r['time']} ← {r['gate_heb']}" for r in s["passed_not_fired"]))
        if s.get("shadow_only"): saw.append("עבר, מפיק-צל-בלבד: " + ", ".join(sorted({r['pat'] for r in s["shadow_only"]})))
        if s["blocked"]:
            byg = collections.defaultdict(set)
            for r in s["blocked"]: byg[r["gate_heb"]].add(r["pat"])
            saw.append("נחסם: " + " · ".join(f"{gg} ← {', '.join(sorted(v))}" for gg, v in byg.items()))
        if s["opposite_passed"]: saw.append("הפוך נורה: " + ", ".join(f"{r['pat']} {r['time']}" for r in s["opposite_passed"]))
        did = "**המערכת:** " + ("; ".join(saw) if saw else "אף מפיק לא ראה.")
        if l["took"]: did += " לייב במהלך: " + ", ".join(f"#{t['id']} {t['pat']} {t['time']} ({t['pnl'] if t['pnl'] is not None else '—'}$)" for t in l["took"])
        fix = " ".join(l["change"])
        md.append(f"- **{head}**"); md.append(f"  - {should}"); md.append(f"  - {did}")
        if fix: md.append(f"  - 🔧 {fix}")
        H.append(f'<div class="line"><span class="ic">📍</span><span><b>{h(head)}</b><br>{h(should).replace("**","")}<br>{h(did).replace("**","")}' + (f'<br>🔧 {h(fix)}' if fix else "") + '</span></div>')
    H.append('</div></div>')
    md.append("")

# § C what to fix
md += ["## ג · מה צריך לתקן — לפי סדר הכסף", "", "### ג1 · השערים שחסמו כניסות נכונות", "", "| שער | פעמים | ימים | נק׳ במהלכים | מה זה אומר |", "|---|---|---|---|---|"]
H.append('<h2>ג · מה צריך לתקן — לפי סדר הכסף</h2><h3>ג1 · השערים שחסמו כניסות נכונות</h3><table class="plain"><tr><th>שער</th><th>פעמים</th><th>ימים</th><th>נק׳</th></tr>')
GATE_MEAN = {"dalton_intent:stand_down": "העץ אומר 'אין כוונה' בשלב/סוג-יום הזה — הכי הרבה כסף: Nontrend/Nonconviction בשלב C, ושלב D בימים שאינם מגמה.",
             "dalton_intent:bias": "ההטיה של היום דחתה כניסה נגדה — ביום Variation ההטיה 'ננעלת' על ההרחבה הראשונה ומחמיצה את החזרה.",
             "dalton_intent:kind": "סוג-הכניסה (REVERSAL/BREAK) לא ברשימת-המותרים נגד ההטיה — בעיקר CEILING_FLIP בשלב B.",
             "dalton_intent:location": "T-319b: לונג רק מהקצה התחתון / שורט רק מהעליון ביום Normal/Neutral.",
             "extreme_chase_guard": "שער-הרדיפה (ELQ): הכניסה 'רדפה' אחרי הקיצון.", "rr_hard_floor": "יחס-סיכון-סיכוי מתחת לרצפה.", "entry_not_confirmed": "בר-האישור לא נסגר."}
for k, n in gate_hits.most_common():
    md.append(f"| {g(k)} | {n} | {len(gate_days[k])} | {gate_pts[k]:.0f} | {GATE_MEAN.get(k, '')} |")
    H.append(f'<tr><td>{h(g(k))}<div class="dim" style="font-size:12px">{h(GATE_MEAN.get(k, ""))}</div></td><td class="num">{n}</td><td class="num">{len(gate_days[k])}</td><td class="num">{gate_pts[k]:.0f}</td></tr>')
H.append('</table>')
md += ["", "### ג2 · המועמדים לתיקון (הקשר מלא: סוג · שער · שלב · סוג-יום · אזור · כיוון)", "", "| # | מה | שער | שלב | סוג-יום | אזור | כיוון | ימים | נק׳ | דוגמאות | מפיקים |", "|---|---|---|---|---|---|---|---|---|---|---|"]
H.append('<h3>ג2 · המועמדים לתיקון — בהקשר מלא</h3><div class="dim">מועמד שחוזר ב-≥3 ימים (או ≥15 מקרים בהרנס) עולה לריפליי; מתחת לזה — ממשיכים לספור.</div><div style="overflow-x:auto"><table class="plain"><tr><th>#</th><th>מה</th><th>שער</th><th>שלב</th><th>סוג-יום</th><th>אזור</th><th>כיוון</th><th>ימים</th><th>נק׳</th><th>דוגמאות</th></tr>')
for i, (k, a) in enumerate(fix_rows[:20], 1):
    kind, gate, ph, dtp, zone, dirn = k
    md.append(f"| {i} | {KIND_HEB.get(kind, kind)} | {g(gate)} | {ph} | {dtp} | {ZONE_HEB.get(zone, zone)} | {DIR_HEB[dirn]} | **{len(a['days'])}** ({a['n']}) | {a['pts']:.0f} | {'; '.join(a['examples'][:4])} | {', '.join(sorted(a['pats']))} |")
    H.append(f'<tr><td>{i}</td><td>{h(KIND_HEB.get(kind, kind))}</td><td>{h(g(gate).split(":")[-1] if gate else "—")}</td><td>{ph}</td><td>{h(dtp)}</td><td>{h(ZONE_HEB.get(zone, zone))}</td><td>{DIR_HEB[dirn]}</td><td class="num"><b>{len(a["days"])}</b> ({a["n"]})</td><td class="num">{a["pts"]:.0f}</td><td style="font-size:12px">{h("; ".join(a["examples"][:3]))}' + (f'<div class="dim">{h(", ".join(sorted(a["pats"])))}</div>' if a["pats"] else "") + '</td></tr>')
H.append('</table></div>')
md += ["", "### ג3 · פערי-יציאה — עסקאות שנכנסו נכון ולקחו מעט", "", "| יום | עסקה | נלקח | המהלך נתן | פער | סוג-יום | מה היה עוזר |", "|---|---|---|---|---|---|---|"]
H.append('<h3>ג3 · פערי-יציאה — נכנסו נכון, לקחו מעט</h3><table class="plain"><tr><th>יום</th><th>עסקה</th><th>נלקח</th><th>נתן</th><th>פער</th><th>מה היה עוזר</th></tr>')
for x in gaps[:15]:
    m = x["maxim"] or {}; help_ = (f"טריילינג 1×ATR = {m.get('trail')} · יעד-קבוע = {m.get('t1')} · מקסימום {m.get('max')}" if m else "—")
    md.append(f"| {x['day'][8:]}.{x['day'][5:7]} | #{x['id']} {x['pat']} | {x['realized']:.1f} | {x['available']:.1f} | **{x['gap']:.1f}** | {x['dt']} | {help_} |")
    H.append(f'<tr><td>{x["day"][8:]}.{x["day"][5:7]}</td><td>#{x["id"]} {h(x["pat"])}</td><td class="num">{x["realized"]:.1f}</td><td class="num">{x["available"]:.1f}</td><td class="num"><b>{x["gap"]:.1f}</b></td><td style="font-size:12px">{h(help_)}</td></tr>')
H.append('</table>')
gap_sum = sum(x["gap"] for x in gaps)
both(f"סה״כ פער-יציאה במהלכים שנלקחו: {gap_sum:.0f} נק׳ ({gap_sum*5:,.0f}$ לחוזה) — זה ענף-היציאות (ריפליי T1 1.5R מול REALISM מול טריילינג; 2 חוזים = רגל-ראנר).",
     f'<div class="card" style="padding:10px 12px">סה״כ פער-יציאה במהלכים שנלקחו: <b>{gap_sum:.0f} נק׳</b> ({gap_sum*5:,.0f}$ לחוזה) — ענף-היציאות: ריפליי T1 1.5R מול REALISM מול טריילינג; 2 חוזים = רגל-ראנר.</div>')

# § C4 — the ordered fix list (the answer)
top = fix_rows[:6]
md += ["", "### ג4 · רשימת-התיקונים המסודרת (מה מריצים בריפליי, בסדר הזה)", ""]
H.append('<h3>ג4 · רשימת-התיקונים המסודרת — מה מריצים בריפליי, בסדר הזה</h3>')
items = []
if gate_hits.get("dalton_intent:stand_down"):
    items.append(f"**שלב D / Nontrend stand-down** — השער שחסם הכי הרבה כניסות נכונות ({gate_hits['dalton_intent:stand_down']} פעמים ב-{len(gate_days['dalton_intent:stand_down'])} ימים, {gate_pts['dalton_intent:stand_down']:.0f} נק׳). ריפליי: שלב D פתוח גם ל-Variation/Normal עם-ההרחבה (לא רק מגמה), ו-Nontrend בשלב C עם EDGE_FADE בקצוות. שורת-v2 בצל ⇒ הרנס 56 סשנים.")
if gate_hits.get("dalton_intent:bias"):
    items.append(f"**ההטיה ביום Variation** — {gate_hits['dalton_intent:bias']} חסימות ב-{len(gate_days['dalton_intent:bias'])} ימים ({gate_pts['dalton_intent:bias']:.0f} נק׳): ההטיה ננעלת על ההרחבה הראשונה ודוחה את החזרה לבטן. ריפליי: 'extension_direction_once_then_BOTH' ⇒ BOTH אחרי חזרה ל-VA (או אחרי 6 ברים נגד).")
np_ = [(k, a) for k, a in fix_rows if k[0] == "no_producer"]
if np_:
    items.append(f"**מהלכים שאף מפיק לא רואה** — {sum(a['n'] for _, a in np_)} מהלכים ({sum(a['pts'] for _, a in np_):.0f} נק׳); ההקשר הנפוץ: " + "; ".join(f"{k[3]} שלב {k[2]} {ZONE_HEB.get(k[4], k[4])} {DIR_HEB[k[5]]} ({len(a['days'])} ימים)" for k, a in np_[:3]) + ". זה חומר למפיק חדש (חתימת-הבר בדוחות היומיים) — צריך ≥15 מקרים בהרנס לפני שכותבים אותו.")
pn = [(k, a) for k, a in fix_rows if k[0] == "producer_not_live"]
if pn:
    items.append(f"**מפיקים שרואים אבל מחוברים רק לצל** ({', '.join(sorted({p for _, a in pn for p in a['pats']}))}) — {sum(a['n'] for _, a in pn)} מהלכים. ריפליי: הסטטיסטיקה של הצל שלהם באותו הקשר (N, win%, $) ⇒ פסיקה אם לחבר ללייב.")
items.append(f"**ענף-היציאות** — {gap_sum:.0f} נק׳ פער בעסקאות שנכנסו נכון. ריפליי שלושת מודלי-היציאה על 56 סשנים לפי סוג-יום; ביום-מגמה טריילינג, ברוטציה יעד-קבוע.")
items.append("**כניסה מאוחרת/הפוכה בפתיחה** — 16:55→17:10 ב-22.09 (#2106 הפוך) ו-17:50 (#2140 מאוחר ב-40 דק׳): המפיקים שראו בזמן היו TREND_STEP/ZLR (צל) — נכלל בסעיף המפיקים.")
for i, t in enumerate(items, 1):
    md.append(f"{i}. {t}"); H.append(f'<div class="card" style="padding:10px 12px"><b>{i}.</b> {h(t).replace("**","")}</div>')

# § D branch path
md += ["", "## ד · איך זה הופך לענף", "", "1. המבחן-היומי רץ ב-EOD ומוסיף את מועמדי-היום ל-`data/review.json` (הטבלה ג2 גדלה מעצמה).",
       "2. מועמד ≥3 ימים / ≥15 מקרים ⇒ שורה ב-`config/dalton_tree_v2_draft.yaml` (צל; שורות TREE_SHADOW ב-`v9_decision_vectors`).",
       "3. `scripts/fwd_harness.py` על 56–85 סשנים עם מודל-ההערכה הקבוע ⇒ N · win% · $ מול העץ הנוכחי.",
       "4. מספר טוב יותר ⇒ פסיקה אחת של מייקל ⇒ הדגל נדלק עם `measured:` ב-`config/RULED_FLAGS.yaml` ⇒ גרסת-עץ חדשה (v1.2 → v1.3). תקרית = מקרה-ריפליי, לא דגל.", ""]
H.append('<h2>ד · איך זה הופך לענף</h2><div class="card" style="padding:10px 12px">1. המבחן-היומי רץ ב-EOD ומוסיף את מועמדי-היום (הטבלה ג2 גדלה מעצמה).<br>2. מועמד ≥3 ימים / ≥15 מקרים ⇒ שורה ב-v2 של עץ-דלתון בצל.<br>3. ריפליי בהרנס על 56–85 סשנים עם מודל-ההערכה הקבוע ⇒ N · win% · $ מול העץ הנוכחי.<br>4. מספר טוב יותר ⇒ פסיקה אחת ⇒ דגל עם measured ⇒ גרסת-עץ חדשה. תקרית = מקרה-ריפליי, לא דגל.</div>')

md_path = os.path.join(ROOT, "docs", "reports", f"REPLAY_REVIEW_{TODAY}.md")
open(md_path, "w", encoding="utf-8").write("\n".join(md))
json.dump({"generated": NOW.isoformat(timespec="minutes"), "title": title, "html": "\n".join(H), "days": days, "tot": tot, "gap_sum": gap_sum,
           "top_fixes": [dict(kind=k[0], gate=k[1], phase=k[2], day_type=k[3], zone=k[4], dir=k[5], days=len(a["days"]), n=a["n"], pts=round(a["pts"], 1), pats=sorted(a["pats"])) for k, a in fix_rows[:20]],
           "gate_hits": {k: dict(n=n, days=len(gate_days[k]), pts=round(gate_pts[k], 1)) for k, n in gate_hits.items()}},
          open(os.path.join(OUT, "data", "review_report.json"), "w"), ensure_ascii=False, indent=0)
# ── PDF (light, print-friendly, RTL) via headless Chrome when available ────────
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
pdf_path = os.path.join(OUT, f"REPLAY_REVIEW_{TODAY}.pdf")
if os.path.exists(CH):
    css = ("body{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;direction:rtl;color:#111;background:#fff;font-size:12.5px;line-height:1.45;margin:18px}"
           "h1{font-size:19px;margin:0 0 4px}h2{font-size:15px;margin:16px 0 6px;border-bottom:1px solid #ccc;padding-bottom:3px}h3{font-size:13px;margin:12px 0 4px}"
           "table.plain{border-collapse:collapse;width:100%;font-size:11px;margin:4px 0}table.plain th,table.plain td{border:1px solid #ddd;padding:4px 5px;text-align:right;vertical-align:top}"
           "table.plain th{background:#f2f2f2}.num{direction:ltr;display:inline-block}.pos{color:#1a7f37}.neg{color:#c62828}.dim{color:#666;font-size:11px}"
           ".card{border:1px solid #ddd;border-radius:6px;padding:8px 10px;margin:6px 0;page-break-inside:avoid}.card .hl{font-weight:700;margin-bottom:4px}.card .row,.card .body{display:block}"
           ".line{display:flex;gap:6px;margin:5px 0;page-break-inside:avoid}.line .ic{flex:none}a{color:#111;text-decoration:none}.kpis{display:none}")
    tmp = os.path.join(OUT, "data", "_print_review_report.html")
    open(tmp, "w", encoding="utf-8").write(f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>{css}</style></head><body>' + "\n".join(H) + '</body></html>')
    try:
        subprocess.run([CH, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", f"file://{tmp}"], capture_output=True, timeout=90)
        os.remove(tmp)
    except Exception as e:
        print("pdf failed:", e)
print(f"report → {md_path} · html fragment → data/review_report.json · pdf {'ok' if os.path.exists(pdf_path) else 'no'} · days {len(days)} · legs {tot['legs']} took {tot['took']} missed {tot['missed']} ({tot['missed_pts']:.0f} pts) · fixes {len(fix_rows)} · gap {gap_sum:.0f}")
