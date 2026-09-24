#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""improvement_report.py — "how much would the system have made on every past day, before vs after the fixes"
(Michael 25.09 00:10: "אני רוצה לראות איך המערכת השתפרה וכמה כסף הייתה עושה על כל הימים הקודמים לאחר התיקונים").

Sources (all real-engine replays, fwd_harness, one contract, first touch on 5-min bars, EOD close):
  OLD  = harness_out/t466/old_<d>.json     — the system as it traded until 23.09: IB_EXT_OVERRIDE_PHASE_GUARD_V1=0
                                             (the phantom-extension bias bug) and no opening-drive branch.
  NEW  = harness_out/t458/r15_<d>.json     — today's live set on the drive sessions (T-451 guard + drive branch @1.5R),
         harness_out/t458/branch1_<d>.json — on the sessions without a confirmed drive (identical to HEAD there).
  LIVE = v9_trades mode='live' per day, pnl_sierra where the broker matched, else books (for the days we traded live).
Commissions: $2.60 per round-trip subtracted from every replayed trade (daily_pnl_harness is gross).

Outputs: docs/reports/IMPROVEMENT_<date>.md · render_mobile_relay/static/docs/data/improvement.json ·
         render_mobile_relay/static/docs/improvement.html (+ PDF via headless Chrome when available)
"""
import collections, datetime as dt, glob, html, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all
from zoneinfo import ZoneInfo
IL = ZoneInfo("Asia/Jerusalem"); COMM = 2.60
TODAY = dt.datetime.now(IL).date().isoformat()
OUT = os.path.join(ROOT, "render_mobile_relay", "static", "docs")

def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None

def day_of(j):
    """net day total (commissions applied) + trade list"""
    tr = j.get("trades") or []
    gross = float(j.get("daily_pnl_harness") or 0.0)
    return gross - COMM * len(tr), [(t["classification"], t["direction"], t["entry"], t["outcome"], round(t["pnl_usd"] - COMM, 1), (t.get("fired_il") or "")[:5]) for t in tr]

sessions = sorted(os.path.basename(p)[8:18] for p in glob.glob(os.path.join(ROOT, "harness_out", "t458", "branch1_*.json")))
dth = {str(r["date"]): r for r in read_all("select date, day_type, opening_type from v9_day_type_history where date >= :d", {"d": sessions[0]})}
live = collections.defaultdict(float); live_n = collections.Counter()
for r in read_all("""select (entry_ts at time zone 'Asia/Jerusalem')::date d, coalesce(pnl_sierra, pnl_usd) p
                     from v9_trades where mode='live' and state='CLOSED' and entry_ts is not null and entry_ts >= :d""", {"d": sessions[0]}):
    if r["p"] is not None:
        live[str(r["d"])] += float(r["p"]); live_n[str(r["d"])] += 1
rows = []
for d in sessions:
    new_p = os.path.join(ROOT, "harness_out", "t458", f"r15_{d}.json")
    if not os.path.exists(new_p): new_p = os.path.join(ROOT, "harness_out", "t458", f"branch1_{d}.json")
    old_p = os.path.join(ROOT, "harness_out", "t466", f"old_{d}.json")
    jn, jo = load(new_p), load(old_p)
    if not jn:
        continue
    new_usd, new_tr = day_of(jn)
    old_usd, old_tr = day_of(jo) if jo else (None, [])
    rows.append(dict(d=d, dt=(dth.get(d, {}) or {}).get("day_type") or "?", ot=(dth.get(d, {}) or {}).get("opening_type") or "",
                     old=old_usd, new=new_usd, delta=(None if old_usd is None else new_usd - old_usd),
                     new_trades=new_tr, old_trades=old_tr, live=(live[d] if d in live else None), live_n=live_n.get(d, 0)))
def S(key, rs=None):
    rs = rows if rs is None else rs
    return sum(r[key] for r in rs if r.get(key) is not None)
n = len(rows); n_old = sum(1 for r in rows if r["old"] is not None)
pos_new = sum(1 for r in rows if r["new"] > 0); neg_new = sum(1 for r in rows if r["new"] < 0)
pos_old = sum(1 for r in rows if r["old"] is not None and r["old"] > 0); neg_old = sum(1 for r in rows if r["old"] is not None and r["old"] < 0)
better = sum(1 for r in rows if r["delta"] is not None and r["delta"] > 0.01); worse = sum(1 for r in rows if r["delta"] is not None and r["delta"] < -0.01)
bym = collections.OrderedDict()
for r in rows:
    k = r["d"][:7]; m = bym.setdefault(k, dict(days=0, old=0.0, new=0.0, live=0.0, live_days=0))
    m["days"] += 1; m["new"] += r["new"]; m["old"] += (r["old"] or 0.0)
    if r["live"] is not None: m["live"] += r["live"]; m["live_days"] += 1
bydt = collections.defaultdict(lambda: dict(days=0, old=0.0, new=0.0))
for r in rows:
    m = bydt[r["dt"]]; m["days"] += 1; m["new"] += r["new"]; m["old"] += (r["old"] or 0.0)
cum_new = 0.0; cum_old = 0.0
for r in rows:
    cum_new += r["new"]; cum_old += (r["old"] or 0.0); r["cum_new"] = round(cum_new, 2); r["cum_old"] = round(cum_old, 2)
best = max(rows, key=lambda r: r["new"]); worst = min(rows, key=lambda r: r["new"])
live_rows = [r for r in rows if r["live"] is not None]

# ── markdown
L = []; A = L.append
A(f"# שיפור המערכת — כמה כסף הייתה עושה על כל הימים הקודמים, לפני ואחרי התיקונים ({TODAY})")
A("")
A("**מייקל 25.09 00:10:** *\"אני רוצה לראות איך המערכת השתפרה וכמה כסף הייתה עושה על כל הימים הקודמים לאחר התיקונים\"*.")
A("")
A("**איך נמדד:** המנוע האמיתי (`fwd_harness`) על כל הסשנים הנקיים מ-15.06, חוזה אחד, מגע-ראשון על ברים של 5 דק׳, סגירה ב-EOD, 2.60$ עמלה לכל סיבוב. "
  "**\"לפני\"** = המערכת כפי שסחרה עד 23.09 (באג-ההטיה של הקיצון-המזויף פעיל, בלי ענף-דרייב). **\"אחרי\"** = מה שרץ מחר: תיקון-ההטיה (T-451/T-456) + ענף-דרייב-הפתיחה ביעד 1.5R (T-457, פסיקת 24.09). "
  "**\"בפועל\"** = מה שקרה בחשבון בימים שסחרנו לייב (מחיר-ברוקר כשיש). הספרים של הריפליי הם אופטימיים ב-3–5 טיקים לעסקה (בלי סליפג׳).")
A("")
A("## 1 · השורה התחתונה")
A("")
A(f"| | לפני התיקונים | אחרי התיקונים | Δ |")
A("|---|---|---|---|")
A(f"| Σ על {n} סשנים | **{S('old'):+,.0f}$** | **{S('new'):+,.0f}$** | **{S('new')-S('old'):+,.0f}$** |")
A(f"| ממוצע לסשן | {S('old')/max(n_old,1):+.1f}$ | {S('new')/n:+.1f}$ | |")
A(f"| ימים חיוביים / שליליים | {pos_old} / {neg_old} | {pos_new} / {neg_new} | ימים שהשתפרו {better} · הורעו {worse} |")
A(f"| היום הטוב / הרע ביותר (אחרי) | | {best['d']} {best['new']:+.0f}$ · {worst['d']} {worst['new']:+.0f}$ | |")
if live_rows:
    A(f"| בפועל בחשבון ({len(live_rows)} ימי-לייב) | | ריפליי-אחרי על אותם ימים {S('new', live_rows):+.0f}$ · **בפועל {S('live', live_rows):+.0f}$** | |")
A("")
A("## 2 · לפי חודש")
A("")
A("| חודש | ימים | לפני | אחרי | Δ | בפועל (ימי-לייב) |")
A("|---|---|---|---|---|---|")
for k, m in bym.items():
    A(f"| {k} | {m['days']} | {m['old']:+,.0f}$ | **{m['new']:+,.0f}$** | {m['new']-m['old']:+,.0f}$ | {('%+.0f$ (%d ימים)' % (m['live'], m['live_days'])) if m['live_days'] else '—'} |")
A("")
A("## 3 · לפי סוג-יום (אחרי התיקונים)")
A("")
A("| סוג-יום | ימים | לפני | אחרי | Δ | ממוצע/יום אחרי |")
A("|---|---|---|---|---|---|")
for k, m in sorted(bydt.items(), key=lambda kv: -kv[1]["days"]):
    A(f"| {k} | {m['days']} | {m['old']:+,.0f}$ | **{m['new']:+,.0f}$** | {m['new']-m['old']:+,.0f}$ | {m['new']/m['days']:+.1f}$ |")
A("")
A("## 4 · יום-אחר-יום")
A("")
A("| יום | סוג-יום | פתיחה | לפני | אחרי | Δ | מצטבר אחרי | העסקאות אחרי התיקונים | בפועל |")
A("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    trs = " · ".join(f"{t[5]} {t[0]} {t[1]} @{t[2]:g} {t[3]} {t[4]:+.0f}$" for t in r["new_trades"]) if r["new_trades"] else "—"
    A(f"| {r['d']} | {r['dt']} | {r['ot']} | {('%+.0f$' % r['old']) if r['old'] is not None else '—'} | **{r['new']:+.0f}$** | {('%+.0f$' % r['delta']) if r['delta'] is not None else '—'} | {r['cum_new']:+.0f}$ | {trs} | {('%+.0f$' % r['live']) if r['live'] is not None else '—'} |")
A("")
A("## 5 · מה עוד לא בפנים (ונמדד שלילי הלילה — לא הודלק)")
A("")
A("ניהול-סטופ לפני T1 (כל גרסה מפסידה, BE@1R +51$ רעש) · מבנה-לפני-תווית −85$ · TOUCH2 שורט-מוקדם −14$ · Open-Auction עם כיוון −124$ · ענף-ההמשך VAR_CONT ≈ +16$ נטו (לא מובהק). "
  "מה שמשפר את היום הוא ענף-הדרייב; הבא בתור לריפליי: המסווג עצמו (6 היפוכי-תווית ב-24.09), עדיפות-סלוט, דילוג-הווליום של מנוע-הפתיחה.")
A("")
md = "\n".join(L)
md_path = os.path.join(ROOT, "docs", "reports", f"IMPROVEMENT_{TODAY}.md")
open(md_path, "w", encoding="utf-8").write(md)
os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
json.dump(dict(generated=dt.datetime.now(IL).isoformat(timespec="minutes"), sessions=n, sum_old=round(S("old"), 2), sum_new=round(S("new"), 2),
               by_month=bym, by_day_type=bydt, rows=rows), open(os.path.join(OUT, "data", "improvement.json"), "w"), ensure_ascii=False, default=str)

# ── phone page (dark) + PDF (light) — same minimal md→html as the other report pages
import re
def md2html(md):
    out, in_tbl, first = [], False, False
    for line in md.split("\n"):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells): continue
            if not in_tbl: out.append('<div style="overflow-x:auto"><table class="plain">'); in_tbl = True; first = True
            tag = "th" if first else "td"; first = False
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"); continue
        if in_tbl: out.append("</table></div>"); in_tbl = False
        if line.startswith("# "): out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "): out.append(f"<h2>{line[3:]}</h2>")
        elif line.strip(): out.append(f"<p>{line}</p>")
    if in_tbl: out.append("</table></div>")
    h = "\n".join(out)
    h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h); h = re.sub(r"\*(.+?)\*", r"<i>\1</i>", h); h = re.sub(r"`(.+?)`", r"<code>\1</code>", h)
    return h
body = md2html(md)
dark = ("body{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;direction:rtl;color:#e6edf3;background:#0b0e14;font-size:12.5px;line-height:1.5;margin:18px}"
        "h1{font-size:18px;margin:0 0 6px}h2{font-size:14.5px;margin:14px 0 6px;border-bottom:1px solid #30363d;padding-bottom:3px}"
        "table.plain{border-collapse:collapse;width:100%;font-size:11px;margin:6px 0}table.plain th,table.plain td{border:1px solid #30363d;padding:4px 5px;text-align:right;vertical-align:top}"
        "table.plain th{background:#161b22}code{font-family:Menlo,monospace;font-size:11px;direction:ltr;unicode-bidi:embed}a{color:#79c0ff}")
light = dark.replace("#e6edf3", "#111").replace("#0b0e14", "#fff").replace("#30363d", "#ccc").replace("#161b22", "#f2f2f2")
open(os.path.join(OUT, "improvement.html"), "w", encoding="utf-8").write(
    f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>שיפור המערכת</title><style>{dark}</style></head><body><p><a href="index.html">← תפריט</a></p>{body}</body></html>')
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
pdf = os.path.join(OUT, f"IMPROVEMENT_{TODAY}.pdf")
if os.path.exists(CH):
    tmp = os.path.join(OUT, "data", "_print_improvement.html")
    open(tmp, "w", encoding="utf-8").write(f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>שיפור המערכת</title><style>{light}</style></head><body>{body}</body></html>')
    try:
        subprocess.run([CH, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", f"file://{tmp}"], capture_output=True, timeout=90); os.remove(tmp)
    except Exception as e:
        print("pdf failed:", e)
print(f"sessions={n} (old on {n_old}) · OLD Σ{S('old'):+.0f}$ · NEW Σ{S('new'):+.0f}$ · Δ{S('new')-S('old'):+.0f}$ · better {better} / worse {worse} · live days {len(live_rows)} replay {S('new', live_rows):+.0f}$ vs actual {S('live', live_rows):+.0f}$")
print(f"→ {md_path} · improvement.html · {'pdf ok' if os.path.exists(pdf) else 'no pdf'}")
