#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_phone_pages.py — the phone's trade-review pages (Michael 22.09 10:20):

  "עמוד של כל העסקאות שבוצעו עם הנרות, ליום, כדי לראות אם הן נכונות או לא — בראייה גדולה,
   עם הסבר למה הצליחו, איך יכולנו להרוויח יותר, ואם הפסידו למה … עמוד של כל העסקאות
   לייב/דמו/צל עם פילטרים … עמוד של דוחות ומשימות, מעין גאנט של הפקת-הלקחים מכל יום
   והענף שנוצר … ותכין לי כבר עכשיו דוח ליום הקודם."

Static, self-contained HTML (no CDN, inline SVG candles, inline JSON) written to
render_mobile_relay/static/docs/ and served by the relay at /doc/<name> (key-protected,
deployed with git push). Read-only against the DB. Re-run daily (EOD) and push.

  python3 scripts/gen_phone_pages.py [--days 14] [--out render_mobile_relay/static/docs]

Pages:
  index.html          — home: links + today/yesterday summary
  days/<date>.html    — day review: candles + live/shadow markers + per-trade explanation + tag buttons
  trades.html         — ledger of every trade (live/demo/shadow) with filters
  lessons.html        — Gantt of lessons per trading day + the branch/version born from each
"""
import os, sys, json, argparse, collections, statistics, html, datetime as dt
from zoneinfo import ZoneInfo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
from backend.env_loader import load_dotenv_file; load_dotenv_file(os.path.join(ROOT, ".env"))
from backend.v9.db.read import read_all

IL = ZoneInfo("Asia/Jerusalem")
TICK = 0.25
ap = argparse.ArgumentParser()
ap.add_argument("--days", type=int, default=14)
ap.add_argument("--out", default=os.path.join(ROOT, "render_mobile_relay", "static", "docs"))
args = ap.parse_args()
OUT = args.out
os.makedirs(os.path.join(OUT, "days"), exist_ok=True)
NOW = dt.datetime.now(IL)
SINCE = (NOW - dt.timedelta(days=args.days)).date()

# ── data ──────────────────────────────────────────────────────────────────────
trades = read_all("""select id, mode, firing_system sys, direction, state, entry_ts, entry_price, stop, t1, t2,
  exit_ts, exit_price, exit_reason, pnl_usd, pnl_r, pnl_sierra, outcome, day_type_at_entry dt,
  pattern_id_at_entry pat, session_at_entry sess
  from v9_trades where entry_ts >= :since and mode in ('live','demo','shadow') order by entry_ts""",
  {"since": dt.datetime.combine(SINCE, dt.time(0, 0), IL)})
bars_rows = read_all("""select ts, open o, high h, low l, close c, volume v from v9_bars_5min_woodies
  where symbol='MES' and ts >= :since and (ts at time zone 'Asia/Jerusalem')::time between '16:00' and '23:00'
  order by ts""", {"since": dt.datetime.combine(SINCE, dt.time(0, 0), IL)})
dth = {str(r["date"]): r for r in read_all(
    "select date, day_type, opening_type, ib_high, ib_low, ib_width_class from v9_day_type_history where date >= :d",
    {"d": SINCE})}

by_day = collections.defaultdict(list)
for b in bars_rows:
    t = b["ts"].astimezone(IL)
    by_day[t.date().isoformat()].append({"ts": b["ts"], "il": t, "o": float(b["o"]), "h": float(b["h"]),
                                         "l": float(b["l"]), "c": float(b["c"]), "v": float(b["v"] or 0),
                                         "rth": t.hour * 60 + t.minute >= 16 * 60 + 30})
days = sorted(d for d in by_day if sum(1 for b in by_day[d] if b["rth"]) >= 30)
tr_by_day = collections.defaultdict(list)
for t in trades:
    tr_by_day[t["entry_ts"].astimezone(IL).date().isoformat()].append(t)

def phase_of(il):
    hm = il.hour * 60 + il.minute
    return "A" if hm < 16 * 60 + 45 else "B" if hm < 17 * 60 + 30 else "C" if hm < 21 * 60 else "D"

def dev_va(bars_so_far):
    """developing value area from closes so far (POC = modal close, 70% of closes around it)."""
    cl = [round(b["c"] / TICK) * TICK for b in bars_so_far]
    if len(cl) < 3:
        return None
    cnt = collections.Counter(cl); poc = cnt.most_common(1)[0][0]
    s = sorted(cl); n = len(s); k = int(round(0.7 * n))
    best = None
    for i in range(0, n - k + 1):
        w = s[i + k - 1] - s[i]
        if best is None or w < best[0]:
            best = (w, s[i], s[i + k - 1])
    return {"poc": poc, "val": best[1], "vah": best[2]}

def zone_of(px, va):
    if not va:
        return "?"
    if px > va["vah"]: return "מעל הבטן"
    if px < va["val"]: return "מתחת לבטן"
    return "חלק עליון של הבטן" if px >= va["poc"] else "חלק תחתון של הבטן"

def facts(t, bars):
    e_il = t["entry_ts"].astimezone(IL); e = float(t["entry_price"]); d = t["direction"]
    sign = 1 if d == "LONG" else -1
    rth = [b for b in bars if b["rth"]]
    before = [b for b in rth if b["ts"] < t["entry_ts"]]
    after = [b for b in rth if b["ts"] >= t["entry_ts"] - dt.timedelta(minutes=5)]
    x_ts = t["exit_ts"] or (rth[-1]["ts"] if rth else t["entry_ts"])
    in_trade = [b for b in after if b["ts"] <= x_ts]
    a60 = [b for b in after if b["ts"] <= t["entry_ts"] + dt.timedelta(minutes=60)]
    def mfe(bs): return max((sign * ((b["h"] if sign > 0 else b["l"]) - e) for b in bs), default=0.0)
    def mae(bs): return max((-sign * ((b["l"] if sign > 0 else b["h"]) - e) for b in bs), default=0.0)
    hi = max((b["h"] for b in before), default=e); lo = min((b["l"] for b in before), default=e)
    pos = (e - lo) / (hi - lo) if hi > lo else 0.5
    va = dev_va(before) if len(before) >= 3 else None
    day_o = rth[0]["o"] if rth else e; day_c = rth[-1]["c"] if rth else e
    day_hi = max(b["h"] for b in rth) if rth else e; day_lo = min(b["l"] for b in rth) if rth else e
    net = day_c - day_o; rng = day_hi - day_lo
    day_dir = "UP" if (rng >= 25 and net >= 0.45 * rng) else "DOWN" if (rng >= 25 and -net >= 0.45 * rng) else "ROT"
    realized = (float(t["exit_price"]) - e) * sign if t["exit_price"] is not None else None
    t1p = abs(float(t["t1"]) - e) if t["t1"] else None
    stop_p = None
    if t["stop"] is not None:
        sp = (e - float(t["stop"])) * sign
        stop_p = sp if sp > 0.5 else None      # a stop already at/beyond entry = moved to BE → initial unknown
    return {"phase": phase_of(e_il), "pos": pos, "zone": zone_of(e, va), "va": va,
            "mfe_x": mfe(in_trade), "mae_x": mae(in_trade), "mfe60": mfe(a60), "mfe_eod": mfe(after),
            "realized": realized, "t1p": t1p, "stop_p": stop_p, "day_dir": day_dir, "day_net": net,
            "day_rng": rng, "with_day": (day_dir == "UP" and d == "LONG") or (day_dir == "DOWN" and d == "SHORT"),
            "against_day": (day_dir == "UP" and d == "SHORT") or (day_dir == "DOWN" and d == "LONG"),
            "mins": (x_ts - t["entry_ts"]).total_seconds() / 60.0}

HEB_DIR = {"LONG": "לונג", "SHORT": "שורט"}
PH_HEB = {"A": "שלב A (15 הדקות הראשונות)", "B": "שלב B (16:45–17:30)", "C": "שלב C (17:30–21:00)", "D": "שלב D (אחרי 21:00)"}
REASON_HEB = {"T1_HIT": "יעד ראשון", "T2_HIT": "יעד שני", "STOP_HIT": "סטופ", "MAE_SCRATCH": "סקראץ׳-MAE (הגנה)",
              "EOD": "סגירת-יום", "EOD_FLATTEN": "סגירת-יום", "BE": "נקודת-איזון", "ladder_invalid": "סולם לא-תקין (לא נכתבה פקודה)",
              "STALE_UNRESOLVED": "לא נפתר (צל)", "CANCELLED": "בוטלה", "MANUAL": "ידני"}

def category(t, f):
    p = t["pnl_usd"]
    if t["exit_reason"] == "ladder_invalid" or (p is None and t["state"] == "CLOSED"):
        return "UNPRICED"
    if p is None: return "OPEN"
    if p > 2: return "WIN"
    if p < -2: return "LOSS"
    return "SCRATCH"

def explain(t, f):
    d = HEB_DIR.get(t["direction"], t["direction"]); cat = category(t, f)
    ctx = []
    ctx.append(f"{d} {t['pat'] or '?'} ב{PH_HEB[f['phase']]}, יום {t['dt'] or 'טרם-סווג'}.")
    if f["day_dir"] in ("UP", "DOWN"):
        ctx.append(("עם כיוון-היום" if f["with_day"] else "נגד כיוון-היום") +
                   f" (היום {'עלה' if f['day_dir']=='UP' else 'ירד'} {abs(f['day_net']):.1f} נק׳ על טווח {f['day_rng']:.1f}).")
    else:
        ctx.append(f"יום-רוטציה (טווח {f['day_rng']:.1f} נק׳, סגירה {f['day_net']:+.1f} מהפתיחה).")
    if f["va"]:
        ctx.append(f"מיקום-הכניסה: {f['zone']} (POC {f['va']['poc']:.2f}, VAH {f['va']['vah']:.2f}, VAL {f['va']['val']:.2f}).")
    chase = (t["direction"] == "LONG" and f["pos"] >= 0.8) or (t["direction"] == "SHORT" and f["pos"] <= 0.2)
    ctx.append(f"מקום בטווח-היום עד הכניסה: {f['pos']*100:.0f}%" + (" — קצה הטווח (רדיפה)." if chase else "."))
    why, more, lesson = [], [], ""
    if cat == "WIN":
        why.append("ניצחה" + (" כי נכנסה עם כיוון-היום" if f["with_day"] else "") +
                   (" ובחלק הנכון של הבטן" if (t["direction"]=="LONG" and "תחתון" in f["zone"]) or (t["direction"]=="SHORT" and "עליון" in f["zone"]) else "") + ".")
        if f["t1p"] is not None:
            gap = max(f["mfe60"] - (f["realized"] or 0), 0)
            if gap >= 6:
                more.append(f"היעד היה {f['t1p']:.2f} נק׳ והמהלך נתן {f['mfe60']:.1f} נק׳ תוך שעה ({f['mfe_eod']:.1f} עד הסגירה) ⇒ נשארו ~{gap:.1f} נק׳ על השולחן. "
                            "הסיבה: יעד מקוצץ (TARGET_REALISM) וחוזה אחד בלי רגל-ראנר — טריילינג-מבני על החוזה היחיד ביום-מגמה היה מרוויח יותר.")
                lesson = "יציאה: ביום-מגמה היעד הקבוע קטן מהמהלך — לעבור לטריילינג/יעד-מבני."
            else:
                more.append(f"היעד ({f['t1p']:.2f} נק׳) מיצה את המהלך — לא היה הרבה יותר לקחת (MFE-שעה {f['mfe60']:.1f}).")
                lesson = "כניסה ויציאה מתואמות — לשמר."
    elif cat == "LOSS":
        reasons = []
        if f["against_day"]: reasons.append("נגד כיוון-היום")
        if chase: reasons.append("כניסה בקצה טווח-היום (רדיפה)")
        if t["direction"] == "LONG" and "מעל" in f["zone"] and f["day_dir"] == "ROT": reasons.append("לונג מעל הבטן ביום-רוטציה")
        if t["direction"] == "SHORT" and "מתחת" in f["zone"] and f["day_dir"] == "ROT": reasons.append("שורט מתחת לבטן ביום-רוטציה")
        if f["phase"] == "D": reasons.append("כניסה מאוחרת ביום (שלב D)")
        if t["exit_reason"] == "STOP_HIT" and f["stop_p"] and f["mfe_eod"] >= (f["t1p"] or 999) and f["mae_x"] <= f["stop_p"] + 1.0:
            reasons.append(f"הסטופ היה צר ({f['stop_p']:.2f} נק׳): אחרי הסטופ המחיר הגיע ליעד")
        if not reasons:
            reasons.append(f"התזה נכשלה: הלכה רק {f['mfe_x']:.1f} נק׳ לטובתנו מול {f['mae_x']:.1f} נגד")
        why.append("הפסידה — " + "; ".join(reasons) + ".")
        if f["mfe_x"] >= 4:
            more.append(f"היה רווח פתוח של {f['mfe_x']:.1f} נק׳ לפני הסטופ — העברת הסטופ לאיזון/יציאה חלקית הייתה הופכת אותה לסקראץ׳.")
        lesson = reasons[0] + " — לבדוק אם השער צריך לחסום כניסה כזו."
    elif cat == "SCRATCH":
        why.append(f"נסגרה בסקראץ׳ ({REASON_HEB.get(t['exit_reason'], t['exit_reason'])}).")
        more.append(f"אחרי היציאה המהלך הגיע ל-{f['mfe_eod']:.1f} נק׳ לטובת הכיוון" + (" — היציאה הייתה מוקדמת." if f["mfe_eod"] >= 8 else " — היציאה הייתה נכונה."))
        lesson = "לבדוק את סף-הסקראץ׳ מול MFE אחרי היציאה."
    elif cat == "UNPRICED":
        why.append("לא נכתבה פקודה: סולם-היעדים שהגיע לביצוע לא היה מונוטוני (T-335 / T-438) — העסקה בוטלה לפני שנשלחה.")
        more.append(f"מה היה קורה: MFE-שעה {f['mfe60']:.1f} נק׳, MAE {f['mae_x']:.1f}.")
        lesson = "באג-ביצוע, לא החלטת-מסחר — פריט T-438."
    else:
        why.append("פתוחה.")
    return " ".join(ctx), " ".join(why), " ".join(more), lesson

# ── per-trade records ─────────────────────────────────────────────────────────
recs = []
for t in trades:
    d = t["entry_ts"].astimezone(IL).date().isoformat()
    bars = by_day.get(d, [])
    f = facts(t, bars) if bars else None
    if f:
        ctx, why, more, lesson = explain(t, f)
    else:
        ctx = why = more = lesson = ""
    e_il = t["entry_ts"].astimezone(IL)
    recs.append({
        "id": t["id"], "mode": t["mode"], "sys": t["sys"], "dir": t["direction"], "pat": t["pat"] or "",
        "day": d, "time": e_il.strftime("%H:%M"), "entry": float(t["entry_price"]),
        "exit": float(t["exit_price"]) if t["exit_price"] is not None else None,
        "exit_time": t["exit_ts"].astimezone(IL).strftime("%H:%M") if t["exit_ts"] else "",
        "reason": t["exit_reason"] or "", "reason_heb": REASON_HEB.get(t["exit_reason"] or "", t["exit_reason"] or ""),
        "pnl": float(t["pnl_usd"]) if t["pnl_usd"] is not None else None,
        "pnl_broker": float(t["pnl_sierra"]) if t["pnl_sierra"] is not None else None,
        "dt": t["dt"] or "", "phase": f["phase"] if f else "", "cat": category(t, f) if f else "OPEN",
        "t1p": round(f["t1p"], 2) if f and f["t1p"] is not None else None,
        "mfe60": round(f["mfe60"], 2) if f else None, "mfe_eod": round(f["mfe_eod"], 2) if f else None,
        "mae": round(f["mae_x"], 2) if f else None, "pos": round(f["pos"], 2) if f else None,
        "zone": f["zone"] if f else "", "mins": round(f["mins"]) if f else None,
        "ctx": ctx, "why": why, "more": more, "lesson": lesson,
    })

# ── HTML helpers ──────────────────────────────────────────────────────────────
CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
html,body{max-width:100%;overflow-x:hidden}
body{margin:0;background:#0b0e14;color:#e6edf3;font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;font-size:16px;line-height:1.5;padding:12px 12px 40px}
a{color:#58a6ff;text-decoration:none}
h1{font-size:21px;margin:4px 0 2px}h2{font-size:17px;margin:18px 0 8px;color:#c9d1d9}
.dim{color:#8b949e;font-size:13px}
.num{direction:ltr;unicode-bidi:embed;font-variant-numeric:tabular-nums}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px}
.nav a{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:8px 12px;font-size:14px}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:12px;margin:10px 0}
.win{border-right:5px solid #3fb950}.loss{border-right:5px solid #f85149}.scratch{border-right:5px solid #d29922}.unpriced{border-right:5px solid #8b949e}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;background:#21262d;border:1px solid #30363d;margin-left:4px}
.badge.live{background:#1f3a2a;border-color:#2ea043;color:#7ee787}.badge.shadow{background:#2a2a1f;border-color:#9e6a03;color:#e3b341}.badge.demo{background:#1f2a3a;border-color:#1f6feb;color:#79c0ff}
.pnl{font-weight:700;font-size:18px}.pos{color:#3fb950}.neg{color:#f85149}
.chartwrap{overflow-x:auto;direction:ltr;-webkit-overflow-scrolling:touch;background:#0d1117;border:1px solid #30363d;border-radius:12px;padding:6px 0}
.tags button{background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:10px;padding:10px 14px;font-size:15px;margin:4px 2px}
.tags button:active{background:#30363d}
.filters{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.filters select,.filters input{background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:8px;padding:8px;font-size:15px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:8px 6px;border-bottom:1px solid #21262d;text-align:right;vertical-align:top}
th{color:#8b949e;font-weight:600;position:sticky;top:0;background:#0b0e14}
tr.row{cursor:pointer}tr.row:active{background:#161b22}
.detail{display:none;background:#0d1117;border-radius:10px;padding:10px;margin:0 0 6px;font-size:14px}
.summary{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0}
.summary div{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:8px 12px;font-size:14px}
.gantt{overflow-x:auto}
.gantt table{min-width:640px}.gantt td{padding:6px 4px;text-align:center;font-size:12px}
.gantt td.lbl{text-align:right;white-space:nowrap;font-weight:600;color:#c9d1d9}
.g{display:block;border-radius:6px;padding:4px 6px;font-size:12px;color:#0b0e14;font-weight:600}
.g.a{background:#7ee787}.g.b{background:#79c0ff}.g.c{background:#e3b341}.g.d{background:#ff7b72}.g.e{background:#d2a8ff}
.zoom button{background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:8px;padding:6px 10px;font-size:13px;margin-left:4px}
.legend span{display:inline-block;margin-left:10px;font-size:12px;color:#8b949e}
"""
NAV = ('<div class="nav"><a href="index.html">🏠 בית</a><a href="trades.html">📒 כל העסקאות</a>'
       '<a href="lessons.html">📈 לקחים וענפים</a><a href="status_2026-09-20.html">📄 עדכון 20.09</a></div>')
KEYJS = """
<script>
var Q=location.search||'';
document.querySelectorAll('a[href]').forEach(function(a){var h=a.getAttribute('href');if(h&&!/^https?:|^#|^mailto:/.test(h)&&h.indexOf('key=')<0){a.setAttribute('href',h+(h.indexOf('?')>=0?'&':'?')+Q.slice(1));}});
function tag(id, label, text){
  var note = prompt(label+' — הערה (אופציונלי):','') ; if(note===null) return;
  var msg='תיוג עסקה #'+id+' ('+text+'): '+label+(note?(' — '+note):'');
  fetch('/instruction'+Q,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:msg})})
   .then(function(r){return r.json();}).then(function(d){alert(d.ok?'נרשם ✓':'שגיאה');}).catch(function(){alert('שגיאה בשליחה');});
}
</script>"""

def page(title, body, extra_js="", prefix=""):
    nav = NAV.replace('href="', f'href="{prefix}') if prefix else NAV
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)}</title>'
            f'<style>{CSS}</style></head><body>{nav}{body}{KEYJS}{extra_js}</body></html>')

def money(v):
    if v is None: return '<span class="dim">—</span>'
    cls = "pos" if v > 0 else "neg" if v < 0 else ""
    return f'<span class="num {cls}">{v:+,.2f}$</span>'

def cat_cls(c): return {"WIN": "win", "LOSS": "loss", "SCRATCH": "scratch"}.get(c, "unpriced")

# ── candle SVG ────────────────────────────────────────────────────────────────
def candle_svg(bars, day_recs, cw=9, H=340):
    if not bars: return ""
    n = len(bars); W = n * cw + 70; top, bot = 14, 30
    hi = max(b["h"] for b in bars); lo = min(b["l"] for b in bars)
    for r in day_recs:
        hi = max(hi, r["entry"], r["exit"] or r["entry"]); lo = min(lo, r["entry"], r["exit"] or r["entry"])
    pad = (hi - lo) * 0.05 or 1; hi += pad; lo -= pad
    def y(p): return top + (hi - p) / (hi - lo) * (H - top - bot)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" style="display:block;direction:ltr">']
    # grid: every 5 pts
    step = 5 if hi - lo < 60 else 10 if hi - lo < 120 else 25
    g = (int(lo / step) + 1) * step
    while g < hi:
        out.append(f'<line x1="0" y1="{y(g):.1f}" x2="{W-66}" y2="{y(g):.1f}" stroke="#21262d" stroke-width="1"/>'
                   f'<text x="{W-62}" y="{y(g)+4:.1f}" fill="#8b949e" font-size="11">{g:.0f}</text>')
        g += step
    for i, b in enumerate(bars):
        x = i * cw + cw / 2
        up = b["c"] >= b["o"]; col = "#3fb950" if up else "#f85149"
        if not b["rth"]: col = "#484f58"
        out.append(f'<line x1="{x:.1f}" y1="{y(b["h"]):.1f}" x2="{x:.1f}" y2="{y(b["l"]):.1f}" stroke="{col}" stroke-width="1"/>')
        yo, yc = y(b["o"]), y(b["c"]); h = max(abs(yc - yo), 1.2)
        out.append(f'<rect x="{x - cw*0.32:.1f}" y="{min(yo, yc):.1f}" width="{cw*0.64:.1f}" height="{h:.1f}" fill="{col}"/>')
        if b["il"].minute == 0:
            out.append(f'<text x="{x:.1f}" y="{H-8}" fill="#8b949e" font-size="11" text-anchor="middle">{b["il"].strftime("%H:%M")}</text>'
                       f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{H-bot}" stroke="#161b22" stroke-width="1"/>')
    idx = {b["il"].strftime("%H:%M"): i for i, b in enumerate(bars)}
    def xof(hhmm):
        i = idx.get(hhmm[:3] + str(int(hhmm[3:]) // 5 * 5).zfill(2))
        return None if i is None else i * cw + cw / 2
    for r in day_recs:
        xe = xof(r["time"]);
        if xe is None: continue
        col = "#3fb950" if (r["pnl"] or 0) > 0 else "#f85149" if (r["pnl"] or 0) < 0 else "#d29922"
        ye = y(r["entry"])
        if r["dir"] == "LONG":
            out.append(f'<polygon points="{xe:.1f},{ye+3:.1f} {xe-6:.1f},{ye+13:.1f} {xe+6:.1f},{ye+13:.1f}" fill="{col}" stroke="#0b0e14" stroke-width="1"/>')
        else:
            out.append(f'<polygon points="{xe:.1f},{ye-3:.1f} {xe-6:.1f},{ye-13:.1f} {xe+6:.1f},{ye-13:.1f}" fill="{col}" stroke="#0b0e14" stroke-width="1"/>')
        if r["exit"] is not None and r["exit_time"]:
            xx = xof(r["exit_time"])
            if xx is not None:
                out.append(f'<line x1="{xe:.1f}" y1="{ye:.1f}" x2="{xx:.1f}" y2="{y(r["exit"]):.1f}" stroke="{col}" stroke-width="2" stroke-dasharray="3,3"/>'
                           f'<circle cx="{xx:.1f}" cy="{y(r["exit"]):.1f}" r="3.5" fill="{col}"/>')
        out.append(f'<text x="{xe:.1f}" y="{(ye+26) if r["dir"]=="LONG" else (ye-17):.1f}" fill="{col}" font-size="10" text-anchor="middle">#{r["id"]}</text>')
    out.append("</svg>")
    return "".join(out)

# ── day pages ─────────────────────────────────────────────────────────────────
def day_summary(d):
    rs = [r for r in recs if r["day"] == d]
    live = [r for r in rs if r["mode"] == "live"]; sh = [r for r in rs if r["mode"] == "shadow"]
    def s(xs):
        p = [x["pnl"] for x in xs if x["pnl"] is not None]
        return {"n": len(xs), "w": sum(1 for v in p if v > 0), "sum": sum(p) if p else 0.0}
    return s(live), s(sh), rs

for d in days:
    bars = by_day[d]; rth = [b for b in bars if b["rth"]]
    lv, sh, rs = day_summary(d)
    live_recs = [r for r in rs if r["mode"] == "live"]
    meta = dth.get(d, {})
    dd = dt.date.fromisoformat(d); heb_day = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"][dd.weekday()]
    o, h_, l_, c_ = rth[0]["o"], max(b["h"] for b in rth), min(b["l"] for b in rth), rth[-1]["c"]
    head = (f'<h1>יום {heb_day} {dd.strftime("%d.%m.%Y")}</h1>'
            f'<div class="dim">סוג-יום (EOD): <b>{meta.get("day_type") or "?"}</b> · פתיחה: {meta.get("opening_type") or "?"} · '
            f'טווח <span class="num">{l_:.2f}–{h_:.2f}</span> ({h_-l_:.1f} נק׳) · פתיחה <span class="num">{o:.2f}</span> סגירה <span class="num">{c_:.2f}</span> ({c_-o:+.1f})</div>'
            f'<div class="summary"><div>לייב: <b>{lv["n"]}</b> עסקאות · {lv["w"]} ניצחונות · {money(lv["sum"])}</div>'
            f'<div>צל: {sh["n"]} · {sh["w"]} ניצחונות · {money(sh["sum"])}</div></div>')
    chart = (f'<h2>הנרות ({len(rth)} ברי-5-דק׳) + עסקאות-הלייב</h2><div class="legend"><span>▲/▼ כניסה</span><span>● יציאה</span><span>אפור = לפני הפתיחה</span></div>'
             f'<div class="zoom"><button onclick="zoomC(6)">צר</button><button onclick="zoomC(9)">רגיל</button><button onclick="zoomC(14)">רחב</button>'
             f'<button onclick="toggleShadow()">צל: הצג/הסתר</button></div>'
             f'<div class="chartwrap" id="cw">{candle_svg(bars, live_recs)}</div>')
    svgs = {cw: candle_svg(bars, live_recs, cw=cw) for cw in (6, 9, 14)}
    svgs_sh = {cw: candle_svg(bars, [r for r in rs if r["mode"] in ("live", "shadow")], cw=cw) for cw in (6, 9, 14)}
    cards = ['<h2>העסקאות — מה קרה ולמה</h2>']
    order = live_recs + [r for r in rs if r["mode"] == "demo"] + [r for r in rs if r["mode"] == "shadow"]
    if not order:
        cards.append('<div class="card">אין עסקאות ביום זה.</div>')
    for r in order:
        cards.append(
            f'<div class="card {cat_cls(r["cat"])}" id="t{r["id"]}">'
            f'<div><span class="badge {r["mode"]}">{r["mode"]}</span><b>#{r["id"]}</b> · {r["time"]} · {HEB_DIR.get(r["dir"], r["dir"])} · {html.escape(r["pat"])}'
            f' <span class="pnl">{money(r["pnl"])}</span></div>'
            f'<div class="dim num">כניסה {r["entry"]:.2f} → יציאה {r["exit"] if r["exit"] is not None else "—"} ({r["exit_time"]}) · {html.escape(r["reason_heb"])} · {r["mins"] or 0} דק׳</div>'
            f'<div style="margin-top:6px">{html.escape(r["ctx"])}</div>'
            f'<div style="margin-top:6px"><b>{html.escape(r["why"])}</b></div>'
            + (f'<div style="margin-top:6px">💡 {html.escape(r["more"])}</div>' if r["more"] else "")
            + (f'<div class="dim" style="margin-top:6px">לקח: {html.escape(r["lesson"])}</div>' if r["lesson"] else "")
            + f'<div class="tags"><button onclick="tag({r["id"]},\'✓ נכונה\',\'{d} {r["time"]} {html.escape(r["pat"])} {r["dir"]}\')">✓ נכונה</button>'
            f'<button onclick="tag({r["id"]},\'✗ לא נכונה\',\'{d} {r["time"]} {html.escape(r["pat"])} {r["dir"]}\')">✗ לא נכונה</button>'
            f'<button onclick="tag({r["id"]},\'💬 הערה\',\'{d} {r["time"]} {html.escape(r["pat"])} {r["dir"]}\')">💬 הערה</button></div></div>')
    js = ("<script>var SV=" + json.dumps(svgs) + ";var SVS=" + json.dumps(svgs_sh) + ";var _cw=9,_sh=false;"
          "function draw(){document.getElementById('cw').innerHTML=(_sh?SVS:SV)[_cw];}"
          "function zoomC(w){_cw=w;draw();}function toggleShadow(){_sh=!_sh;draw();}</script>")
    with open(os.path.join(OUT, "days", f"{d}.html"), "w", encoding="utf-8") as fh:
        fh.write(page(f"MEMS26 · {d}", head + chart + "".join(cards), js, prefix="../"))

# ── trades ledger ─────────────────────────────────────────────────────────────
ledger = [r for r in recs]
pats = sorted({r["pat"] for r in ledger if r["pat"]})
body = ('<h1>📒 כל העסקאות</h1><div class="dim">לייב · דמו · צל — לחיצה על שורה פותחת את ההסבר; "יום" פותח את עמוד-היום עם הנרות.</div>'
        '<div class="filters">'
        '<select id="fMode"><option value="live">לייב</option><option value="">כל המצבים</option><option value="demo">דמו</option><option value="shadow">צל</option></select>'
        '<select id="fDay"><option value="">כל הימים</option>' + "".join(f'<option value="{d}">{d[8:]}.{d[5:7]}</option>' for d in sorted(set(r["day"] for r in ledger), reverse=True)) + '</select>'
        '<select id="fDir"><option value="">כיוון</option><option value="LONG">לונג</option><option value="SHORT">שורט</option></select>'
        '<select id="fCat"><option value="">תוצאה</option><option value="WIN">ניצחון</option><option value="LOSS">הפסד</option><option value="SCRATCH">סקראץ׳</option><option value="UNPRICED">לא-נכתבה</option></select>'
        '<select id="fPat"><option value="">תבנית</option>' + "".join(f'<option value="{html.escape(p)}">{html.escape(p)}</option>' for p in pats) + '</select>'
        '</div><div class="summary" id="sum"></div>'
        '<table><thead><tr><th>#</th><th>יום</th><th>שעה</th><th>מצב</th><th>תבנית</th><th>כיוון</th><th>$</th></tr></thead><tbody id="tb"></tbody></table>')
ljs = ("<script>var T=" + json.dumps(ledger, ensure_ascii=False) + ";"
       "var HD={LONG:'לונג',SHORT:'שורט'};"
       "function fmt(v){if(v===null||v===undefined)return '—';var s=(v>0?'+':'')+v.toFixed(2)+'$';return '<span class=\"num '+(v>0?'pos':v<0?'neg':'')+'\">'+s+'</span>';}"
       "function render(){var m=fMode.value,d=fDay.value,dr=fDir.value,c=fCat.value,p=fPat.value;var rows=T.filter(function(r){return (!m||r.mode==m)&&(!d||r.day==d)&&(!dr||r.dir==dr)&&(!c||r.cat==c)&&(!p||r.pat==p);});"
       "var n=rows.length,w=rows.filter(function(r){return r.pnl>0;}).length,s=rows.reduce(function(a,r){return a+(r.pnl||0);},0);"
       "document.getElementById('sum').innerHTML='<div>N='+n+'</div><div>ניצחונות '+w+' ('+(n?Math.round(100*w/n):0)+'%)</div><div>Σ '+fmt(s)+'</div>';"
       "var h='';rows.slice().reverse().forEach(function(r){h+='<tr class=\"row\" onclick=\"tg('+r.id+')\"><td>'+r.id+'</td><td><a href=\"days/'+r.day+'.html#t'+r.id+'\">'+r.day.slice(8)+'.'+r.day.slice(5,7)+'</a></td><td class=num>'+r.time+'</td><td><span class=\"badge '+r.mode+'\">'+r.mode+'</span></td><td>'+r.pat+'</td><td>'+(HD[r.dir]||r.dir)+'</td><td>'+fmt(r.pnl)+'</td></tr>';"
       "h+='<tr><td colspan=7><div class=detail id=\"d'+r.id+'\"><div class=\"dim\">'+r.reason_heb+'</div><div class=\"dim num\">כניסה '+r.entry.toFixed(2)+' → '+(r.exit===null?'—':r.exit.toFixed(2))+' · T1 '+(r.t1p===null?'—':r.t1p)+' נק׳ · MFE-שעה '+(r.mfe60===null?'—':r.mfe60)+' · MAE '+(r.mae===null?'—':r.mae)+' · '+(r.zone||'')+'</div><div>'+r.ctx+'</div><div><b>'+r.why+'</b></div>'+(r.more?'<div>💡 '+r.more+'</div>':'')+(r.lesson?'<div class=dim>לקח: '+r.lesson+'</div>':'')+'</div></td></tr>';});"
       "document.getElementById('tb').innerHTML=h;document.querySelectorAll('#tb a[href]').forEach(function(a){var x=a.getAttribute('href');if(x.indexOf('key=')<0)a.setAttribute('href',x.replace('#','?'+Q.slice(1)+'#'));});}"
       "function tg(id){var e=document.getElementById('d'+id);e.style.display=e.style.display=='block'?'none':'block';}"
       "['fMode','fDay','fDir','fCat','fPat'].forEach(function(i){document.getElementById(i).onchange=render;});render();</script>")
with open(os.path.join(OUT, "trades.html"), "w", encoding="utf-8") as fh:
    fh.write(page("MEMS26 · כל העסקאות", body, ljs))

# ── lessons Gantt ─────────────────────────────────────────────────────────────
LESSONS = json.load(open(os.path.join(ROOT, "docs", "plans", "LESSONS_TIMELINE.json"), encoding="utf-8"))
tdays = [x["day"] for x in LESSONS["days"]][::-1]
threads = LESSONS["threads"]
gantt = ['<h1>📈 לקחים וענפים — יום אחרי יום</h1><div class="dim">כל עמודה יום-מסחר; כל שורה חוט-עבודה. בתא: מה נלמד / איזה ענף נולד. צבע: ירוק=ענף/גרסה, כחול=מדידה, צהוב=באג שתוקן, אדום=תקרית, סגול=פסיקה.</div>',
         '<div class="gantt"><table><thead><tr><th></th>' + "".join(f'<th>{d[8:]}.{d[5:7]}</th>' for d in tdays) + '</tr></thead><tbody>']
live_by_day = {}
for r in recs:
    if r["mode"] == "live" and r["pnl"] is not None:
        live_by_day.setdefault(r["day"], []).append(r["pnl"])
gantt.append('<tr><td class="lbl">לייב $</td>' + "".join(
    f'<td class="num">{("<span class=pos>" if sum(live_by_day.get(d, [0]))>0 else "<span class=neg>") + f"{sum(live_by_day.get(d, [0])):+.0f}" + "</span>" if d in live_by_day else "—"}</td>' for d in tdays) + '</tr>')
for th in threads:
    cells = []
    for d in tdays:
        items = [it for it in th["items"] if it["day"] == d]
        cells.append('<td>' + "".join(f'<span class="g {it.get("k","b")}" title="{html.escape(it.get("ref",""))}">{html.escape(it["t"])}</span>' for it in items) + '</td>')
    gantt.append(f'<tr><td class="lbl">{html.escape(th["name"])}</td>' + "".join(cells) + '</tr>')
gantt.append('</tbody></table></div>')
gantt.append('<h2>הלקח של כל יום</h2>')
for x in LESSONS["days"][::-1]:
    gantt.append(f'<div class="card"><b>{x["day"][8:]}.{x["day"][5:7]}</b> — {html.escape(x["lesson"])}' + (f' <a href="days/{x["day"]}.html">↗ הנרות</a>' if x["day"] in days else "") + '</div>')
with open(os.path.join(OUT, "lessons.html"), "w", encoding="utf-8") as fh:
    fh.write(page("MEMS26 · לקחים וענפים", "".join(gantt)))

# ── index ─────────────────────────────────────────────────────────────────────
idx = ['<h1>MEMS26 — תיעוד למסחר</h1><div class="dim">נוצר ' + NOW.strftime("%d.%m.%Y %H:%M") + ' · הדפים סטטיים ומתרעננים בכל ריצת-EOD</div>']
idx.append('<h2>ימי-מסחר</h2>')
for d in reversed(days):
    lv, sh, rs = day_summary(d)
    dd = dt.date.fromisoformat(d)
    idx.append(f'<div class="card"><a href="days/{d}.html"><b>{["ב","ג","ד","ה","ו","ש","א"][dd.weekday()]}\' {dd.strftime("%d.%m")}</b> · {dth.get(d,{}).get("day_type") or "?"} · לייב {lv["n"]} ({lv["w"]} ✓) {money(lv["sum"])} · צל {sh["n"]} {money(sh["sum"])}</a></div>')
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(page("MEMS26 · תיעוד", "".join(idx)))
print(f"pages: index, trades ({len(ledger)} rows), lessons, days ×{len(days)} → {OUT}")
