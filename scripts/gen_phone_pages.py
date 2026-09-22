#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_phone_pages.py — the phone's trade-review app (Michael 22.09 10:20 + 10:50):

  "עמוד של כל העסקאות עם הנרות, ליום, כדי לראות אם הן נכונות או לא — בראייה גדולה, עם הסבר
   למה הצליחו, איך יכולנו להרוויח יותר, ואם הפסידו למה … כל העסקאות לייב/דמו/צל עם פילטרים …
   גאנט של הפקת-הלקחים והענף שנוצר" · "header עם המבורגר של התפריט … יותר נוח למשתמש בכל
   הכיוונים … רשימה של עסקאות שפספסנו — נרות, ווליום, מיקום".

Static, self-contained HTML (no CDN, inline SVG candles, inline JSON) written to
render_mobile_relay/static/docs/ and served by the relay at /doc/<name> and /doc/days/<name>
(key-protected, deployed with git push). Read-only against the DB. Re-run at EOD and push.

  python3 scripts/gen_phone_pages.py [--days 14] [--out render_mobile_relay/static/docs]

Pages: index.html · days/<date>.html · trades.html · missed.html (from data/missed.json, made by
scripts/missed_trades_study.py) · lessons.html (from docs/plans/LESSONS_TIMELINE.json) · tree.html
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
HEB_WD = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
HEB_WD1 = ["ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳", "א׳"]

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

def phase_of(il):
    hm = il.hour * 60 + il.minute
    return "A" if hm < 16 * 60 + 45 else "B" if hm < 17 * 60 + 30 else "C" if hm < 21 * 60 else "D"

def dev_va(bars_so_far):
    cl = [round(b["c"] / TICK) * TICK for b in bars_so_far]
    if len(cl) < 3:
        return None
    cnt = collections.Counter(cl); poc = cnt.most_common(1)[0][0]
    s = sorted(cl); n = len(s); k = int(round(0.7 * n)); best = None
    for i in range(0, n - k + 1):
        w = s[i + k - 1] - s[i]
        if best is None or w < best[0]:
            best = (w, s[i], s[i + k - 1])
    return {"poc": poc, "val": best[1], "vah": best[2]}

def zone_of(px, va):
    if not va: return "?"
    if px > va["vah"]: return "מעל הבטן"
    if px < va["val"]: return "מתחת לבטן"
    return "חלק עליון של הבטן" if px >= va["poc"] else "חלק תחתון של הבטן"

def facts(t, bars):
    e = float(t["entry_price"]); d = t["direction"]; sign = 1 if d == "LONG" else -1
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
        stop_p = sp if sp > 0.5 else None
    return {"phase": phase_of(t["entry_ts"].astimezone(IL)), "pos": pos, "zone": zone_of(e, va), "va": va,
            "mfe_x": mfe(in_trade), "mae_x": mae(in_trade), "mfe60": mfe(a60), "mfe_eod": mfe(after),
            "realized": realized, "t1p": t1p, "stop_p": stop_p, "day_dir": day_dir, "day_net": net, "day_rng": rng,
            "with_day": (day_dir == "UP" and d == "LONG") or (day_dir == "DOWN" and d == "SHORT"),
            "against_day": (day_dir == "UP" and d == "SHORT") or (day_dir == "DOWN" and d == "LONG"),
            "mins": (x_ts - t["entry_ts"]).total_seconds() / 60.0}

HEB_DIR = {"LONG": "לונג", "SHORT": "שורט"}
PH_HEB = {"A": "שלב A (15 הדקות הראשונות)", "B": "שלב B (16:45–17:30)", "C": "שלב C (17:30–21:00)", "D": "שלב D (אחרי 21:00)"}
REASON_HEB = {"T1_HIT": "יעד ראשון", "T2_HIT": "יעד שני", "STOP_HIT": "סטופ", "MAE_SCRATCH": "סקראץ׳-MAE (הגנה)",
              "EOD": "סגירת-יום", "EOD_FLATTEN": "סגירת-יום", "BE": "נקודת-איזון", "ladder_invalid": "סולם לא-תקין (לא נכתבה פקודה)",
              "STALE_UNRESOLVED": "לא נפתר (צל)", "CANCELLED": "בוטלה", "MANUAL": "ידני"}

def category(t):
    p = t["pnl_usd"]
    if t["exit_reason"] == "ladder_invalid" or (p is None and t["state"] == "CLOSED"): return "UNPRICED"
    if p is None: return "OPEN"
    if p > 2: return "WIN"
    if p < -2: return "LOSS"
    return "SCRATCH"

def explain(t, f):
    d = HEB_DIR.get(t["direction"], t["direction"]); cat = category(t)
    ctx = [f"{d} {t['pat'] or '?'} ב{PH_HEB[f['phase']]}, יום {t['dt'] or 'טרם-סווג'}."]
    if f["day_dir"] in ("UP", "DOWN"):
        ctx.append(("עם כיוון-היום" if f["with_day"] else "נגד כיוון-היום") +
                   f" (היום {'עלה' if f['day_dir']=='UP' else 'ירד'} {abs(f['day_net']):.1f} נק׳ על טווח {f['day_rng']:.1f}).")
    else:
        ctx.append(f"יום-רוטציה (טווח {f['day_rng']:.1f} נק׳, סגירה {f['day_net']:+.1f} מהפתיחה).")
    if f["va"]:
        ctx.append(f"מיקום-הכניסה: {f['zone']} (POC {f['va']['poc']:.2f} · VAH {f['va']['vah']:.2f} · VAL {f['va']['val']:.2f}).")
    chase = (t["direction"] == "LONG" and f["pos"] >= 0.8) or (t["direction"] == "SHORT" and f["pos"] <= 0.2)
    ctx.append(f"מקום בטווח-היום עד הכניסה: {f['pos']*100:.0f}%" + (" — קצה הטווח (רדיפה)." if chase else "."))
    why, more, lesson = [], [], ""
    if cat == "WIN":
        why.append("ניצחה" + (" כי נכנסה עם כיוון-היום" if f["with_day"] else "") +
                   (" ובחלק הנכון של הבטן" if (t["direction"] == "LONG" and "תחתון" in f["zone"]) or (t["direction"] == "SHORT" and "עליון" in f["zone"]) else "") + ".")
        if f["t1p"] is not None:
            gap = max(f["mfe60"] - (f["realized"] or 0), 0)
            if gap >= 6:
                more.append(f"היעד היה {f['t1p']:.2f} נק׳ והמהלך נתן {f['mfe60']:.1f} נק׳ תוך שעה ({f['mfe_eod']:.1f} עד הסגירה) ⇒ נשארו ~{gap:.1f} נק׳ על השולחן. "
                            "הסיבה: יעד מקוצץ (TARGET_REALISM) וחוזה אחד בלי רגל-ראנר.")
                lesson = "יציאה: ביום-מגמה היעד הקבוע קטן מהמהלך — טריילינג/יעד-מבני."
            else:
                more.append(f"היעד ({f['t1p']:.2f} נק׳) מיצה את המהלך (MFE-שעה {f['mfe60']:.1f}).")
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
            more.append(f"היה רווח פתוח של {f['mfe_x']:.1f} נק׳ לפני הסטופ — סטופ-לאיזון/יציאה חלקית הייתה הופכת אותה לסקראץ׳.")
        lesson = reasons[0] + " — לבדוק אם השער צריך לחסום כניסה כזו."
    elif cat == "SCRATCH":
        why.append(f"נסגרה בסקראץ׳ ({REASON_HEB.get(t['exit_reason'], t['exit_reason'])}).")
        more.append(f"אחרי היציאה המהלך הגיע ל-{f['mfe_eod']:.1f} נק׳ לטובת הכיוון" + (" — היציאה הייתה מוקדמת." if f["mfe_eod"] >= 8 else " — היציאה הייתה נכונה."))
        lesson = "לבדוק את סף-הסקראץ׳ מול MFE אחרי היציאה."
    elif cat == "UNPRICED":
        why.append("לא נכתבה פקודה: סולם-היעדים לא היה מונוטוני (T-335 / T-438) — בוטלה לפני שנשלחה.")
        more.append(f"מה היה קורה: MFE-שעה {f['mfe60']:.1f} נק׳, MAE {f['mae_x']:.1f}.")
        lesson = "באג-ביצוע, לא החלטת-מסחר — פריט T-438."
    else:
        why.append("פתוחה.")
    return " ".join(ctx), " ".join(why), " ".join(more), lesson

recs = []
for t in trades:
    d = t["entry_ts"].astimezone(IL).date().isoformat()
    bars = by_day.get(d, [])
    f = facts(t, bars) if bars else None
    ctx, why, more, lesson = explain(t, f) if f else ("", "", "", "")
    e_il = t["entry_ts"].astimezone(IL)
    recs.append({
        "id": t["id"], "mode": t["mode"], "sys": t["sys"], "dir": t["direction"], "pat": t["pat"] or "",
        "day": d, "time": e_il.strftime("%H:%M"), "entry": float(t["entry_price"]),
        "exit": float(t["exit_price"]) if t["exit_price"] is not None else (float(t["t1"]) if (t["exit_reason"] == "T1_HIT" and t["t1"]) else None),
        "exit_time": t["exit_ts"].astimezone(IL).strftime("%H:%M") if t["exit_ts"] else "",
        "reason": t["exit_reason"] or "", "reason_heb": REASON_HEB.get(t["exit_reason"] or "", t["exit_reason"] or ""),
        "pnl": float(t["pnl_usd"]) if t["pnl_usd"] is not None else None,
        "pnl_broker": float(t["pnl_sierra"]) if t["pnl_sierra"] is not None else None,
        "dt": t["dt"] or "", "phase": f["phase"] if f else "", "cat": category(t),
        "t1p": round(f["t1p"], 2) if f and f["t1p"] is not None else None,
        "mfe60": round(f["mfe60"], 2) if f else None, "mfe_eod": round(f["mfe_eod"], 2) if f else None,
        "mae": round(f["mae_x"], 2) if f else None, "pos": round(f["pos"], 2) if f else None,
        "zone": f["zone"] if f else "", "mins": round(f["mins"]) if f else None,
        "ctx": ctx, "why": why, "more": more, "lesson": lesson,
    })

# ── app shell ─────────────────────────────────────────────────────────────────
CSS = """
:root{color-scheme:dark;--bg:#0b0e14;--card:#161b22;--line:#30363d;--fg:#e6edf3;--dim:#8b949e;--acc:#58a6ff;--up:#3fb950;--dn:#f85149;--am:#d29922}
*{box-sizing:border-box}
html,body{max-width:100%;overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;font-size:17px;line-height:1.5;padding:0 0 76px}
a{color:var(--acc);text-decoration:none}
.hdr{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:10px;background:#0d1117;border-bottom:1px solid var(--line);padding:10px 12px;padding-top:calc(10px + env(safe-area-inset-top))}
.hdr .t{flex:1;font-weight:700;font-size:17px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hdr .sub{font-size:12px;color:var(--dim);font-weight:400}
.hdr button,.hdr a.btn{background:var(--card);border:1px solid var(--line);color:var(--fg);border-radius:10px;font-size:20px;width:44px;height:40px;display:flex;align-items:center;justify-content:center}
.drawer{position:fixed;inset:0;z-index:30;display:none}
.drawer.open{display:block}
.drawer .bg{position:absolute;inset:0;background:rgba(0,0,0,.55)}
.drawer .panel{position:absolute;top:0;right:0;bottom:0;width:min(84vw,340px);background:#0d1117;border-left:1px solid var(--line);padding:16px 12px;overflow-y:auto;padding-top:calc(16px + env(safe-area-inset-top))}
.drawer h3{margin:8px 4px 4px;font-size:13px;color:var(--dim);font-weight:600;text-transform:uppercase}
.drawer a.item{display:flex;align-items:center;gap:10px;padding:12px 10px;border-radius:10px;color:var(--fg);font-size:17px}
.drawer a.item:active{background:var(--card)}
.drawer a.item small{margin-right:auto;color:var(--dim);font-size:13px}
.wrap{padding:12px 12px 8px}
h1{font-size:22px;margin:6px 0 4px}
h2{font-size:16px;margin:20px 0 8px;color:#c9d1d9;display:flex;align-items:center;gap:8px}
.dim{color:var(--dim);font-size:13px}
.num{direction:ltr;unicode-bidi:embed;font-variant-numeric:tabular-nums}
.kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:10px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.kpi .l{font-size:12px;color:var(--dim)}.kpi .v{font-size:20px;font-weight:700;margin-top:2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:10px 0}
.win{border-right:5px solid var(--up)}.loss{border-right:5px solid var(--dn)}.scratch{border-right:5px solid var(--am)}.unpriced{border-right:5px solid var(--dim)}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;background:#21262d;border:1px solid var(--line);margin-left:6px;vertical-align:middle}
.badge.live{background:#1f3a2a;border-color:#2ea043;color:#7ee787}.badge.shadow{background:#2a2a1f;border-color:#9e6a03;color:#e3b341}.badge.demo{background:#1f2a3a;border-color:#1f6feb;color:#79c0ff}
.pos{color:var(--up)}.neg{color:var(--dn)}
.pnl{font-weight:700;font-size:18px}
.row{display:flex;align-items:center;gap:8px;cursor:pointer}
.row .grow{flex:1;min-width:0}
.row .hl{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chev{color:var(--dim);font-size:18px;transition:transform .15s}
.card.open .chev{transform:rotate(90deg)}
.body{display:none;margin-top:10px;border-top:1px solid var(--line);padding-top:10px}
.card.open .body{display:block}
.chartwrap{overflow-x:auto;direction:ltr;-webkit-overflow-scrolling:touch;background:#0d1117;border:1px solid var(--line);border-radius:12px;padding:6px 0}
.tools{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.tools button{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:999px;padding:7px 12px;font-size:14px}
.tools button.on{background:#1f6feb;border-color:#1f6feb;color:#fff}
.tags{display:flex;gap:6px;margin-top:10px}
.tags button{flex:1;background:#21262d;color:var(--fg);border:1px solid var(--line);border-radius:10px;padding:11px 6px;font-size:15px}
.tags button:active{background:#30363d}
.filters{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:8px 0}
.filters select{width:100%;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:10px;padding:10px;font-size:16px}
.dayhdr{background:#0d1117;border:1px solid var(--line);border-radius:10px;padding:8px 12px;margin:14px 0 6px;font-weight:600;display:flex;justify-content:space-between}
.trow{display:flex;align-items:center;gap:8px;padding:10px 6px;border-bottom:1px solid #21262d}
.trow .grow{flex:1;min-width:0}
.trow .a{font-weight:600}.trow .b{font-size:13px;color:var(--dim)}
.detail{display:none;background:#0d1117;border-radius:10px;padding:10px;margin:0 0 6px;font-size:15px}
.gantt{overflow-x:auto;-webkit-overflow-scrolling:touch}
.gantt table{border-collapse:collapse;min-width:640px;font-size:12px}
.gantt th,.gantt td{padding:6px 4px;border-bottom:1px solid #21262d;text-align:center;vertical-align:top}
.gantt td.lbl,.gantt th.lbl{text-align:right;white-space:nowrap;font-weight:600;color:#c9d1d9;position:sticky;right:0;background:var(--bg)}
.g{display:block;border-radius:6px;padding:4px 6px;font-size:12px;color:#0b0e14;font-weight:600;margin:2px 0}
.g.a{background:#7ee787}.g.b{background:#79c0ff}.g.c{background:#e3b341}.g.d{background:#ff7b72}.g.e{background:#d2a8ff}
.legend span{display:inline-block;margin-left:10px;font-size:12px;color:var(--dim)}
.bottom{position:fixed;left:0;right:0;bottom:0;z-index:20;display:flex;background:#0d1117;border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}
.bottom a{flex:1;text-align:center;padding:8px 2px 6px;color:var(--dim);font-size:11px}
.bottom a b{display:block;font-size:20px;font-weight:400}
.bottom a.on{color:var(--acc)}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid var(--line);background:#21262d;margin:2px 2px 2px 0}
.pill.ok{border-color:#2ea043;color:#7ee787}.pill.bad{border-color:#da3633;color:#ffa198}.pill.warn{border-color:#9e6a03;color:#e3b341}
table.plain{border-collapse:collapse;width:100%;font-size:14px}
table.plain th,table.plain td{padding:7px 6px;border-bottom:1px solid #21262d;text-align:right;vertical-align:top}
table.plain th{color:var(--dim);font-weight:600}
"""
MENU = [("index.html", "🏠", "בית", ""), ("/", "💬", "צ׳אט עם המערכת", "הודעות ופקודות"),
        ("days.html", "📅", "ימי-מסחר", "נרות + עסקאות ליום"), ("trades.html", "📒", "כל העסקאות", "לייב · דמו · צל"),
        ("missed.html", "⭕", "מה פספסנו", "10 סשנים אחרונים"), ("lessons.html", "📈", "לקחים וענפים", "גאנט"),
        ("tree.html", "🌳", "עץ-דלתון", "הגרסאות והמצב"), ("status_2026-09-20.html", "📄", "עדכוני-מצב", "20.09"),
        ("/readiness", "📋", "תיק-מוכנות", "משימות")]
BOTTOM = [("index.html", "🏠", "בית"), ("days.html", "📅", "ימים"), ("trades.html", "📒", "עסקאות"), ("missed.html", "⭕", "פספוסים"), ("lessons.html", "📈", "לקחים")]

def shell(title, body, extra_js="", prefix="", sub="", active="", left_btn=""):
    def href(h):
        return h if h.startswith("/") else prefix + h
    drawer = ''.join(f'<a class="item" href="{href(h)}"><span>{ic}</span><span>{html.escape(n)}</span><small>{html.escape(s)}</small></a>' for h, ic, n, s in MENU)
    bottom = ''.join(f'<a href="{href(h)}" class="{"on" if h == active else ""}"><b>{ic}</b>{n}</a>' for h, ic, n in BOTTOM)
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>{html.escape(title)}</title>'
            f'<style>{CSS}</style></head><body>'
            f'<div class="hdr"><button onclick="drawer(true)" aria-label="תפריט">☰</button><div class="t">{html.escape(title)}'
            + (f'<div class="sub">{html.escape(sub)}</div>' if sub else '') + f'</div>{left_btn}</div>'
            f'<div class="drawer" id="dr"><div class="bg" onclick="drawer(false)"></div><div class="panel"><h3>MEMS26</h3>{drawer}</div></div>'
            f'<div class="wrap">{body}</div><div class="bottom">{bottom}</div>'
            + KEYJS + extra_js + '</body></html>')

KEYJS = """
<script>
var Q=location.search||'';
document.querySelectorAll('a[href]').forEach(function(a){var h=a.getAttribute('href');if(h&&!/^https?:|^#|^mailto:/.test(h)&&h.indexOf('key=')<0){var i=h.indexOf('#');var base=i>=0?h.slice(0,i):h,hash=i>=0?h.slice(i):'';a.setAttribute('href',base+(base.indexOf('?')>=0?'&':'?')+Q.slice(1)+hash);}});
function drawer(o){document.getElementById('dr').classList.toggle('open',o);}
function tog(el){el.classList.toggle('open');}
function tag(id, label, text){
  var note = prompt(label+' — הערה (אופציונלי):',''); if(note===null) return;
  var msg='תיוג עסקה #'+id+' ('+text+'): '+label+(note?(' — '+note):'');
  fetch('/instruction'+Q,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:msg})})
   .then(function(r){return r.json();}).then(function(d){alert(d.ok?'נרשם ✓':'שגיאה');}).catch(function(){alert('שגיאה בשליחה');});
}
if(location.hash){var el=document.getElementById(location.hash.slice(1));if(el){el.classList.add('open');setTimeout(function(){el.scrollIntoView();},50);}}
</script>"""

def money(v, big=False):
    if v is None: return '<span class="dim">—</span>'
    cls = "pos" if v > 0 else "neg" if v < 0 else ""
    return f'<span class="num {cls}{" pnl" if big else ""}">{v:+,.0f}$</span>' if big else f'<span class="num {cls}">{v:+,.2f}$</span>'

def cat_cls(c): return {"WIN": "win", "LOSS": "loss", "SCRATCH": "scratch"}.get(c, "unpriced")

def day_summary(d):
    rs = [r for r in recs if r["day"] == d]
    def s(xs):
        p = [x["pnl"] for x in xs if x["pnl"] is not None]
        return {"n": len(xs), "w": sum(1 for v in p if v > 0), "sum": sum(p) if p else 0.0}
    return s([r for r in rs if r["mode"] == "live"]), s([r for r in rs if r["mode"] == "shadow"]), rs

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
    step = 5 if hi - lo < 60 else 10 if hi - lo < 120 else 25
    g = (int(lo / step) + 1) * step
    while g < hi:
        out.append(f'<line x1="0" y1="{y(g):.1f}" x2="{W-66}" y2="{y(g):.1f}" stroke="#21262d"/>'
                   f'<text x="{W-62}" y="{y(g)+4:.1f}" fill="#8b949e" font-size="11">{g:.0f}</text>')
        g += step
    for i, b in enumerate(bars):
        x = i * cw + cw / 2
        col = ("#3fb950" if b["c"] >= b["o"] else "#f85149") if b["rth"] else "#484f58"
        out.append(f'<line x1="{x:.1f}" y1="{y(b["h"]):.1f}" x2="{x:.1f}" y2="{y(b["l"]):.1f}" stroke="{col}"/>')
        yo, yc = y(b["o"]), y(b["c"]); h = max(abs(yc - yo), 1.2)
        out.append(f'<rect x="{x - cw*0.32:.1f}" y="{min(yo, yc):.1f}" width="{cw*0.64:.1f}" height="{h:.1f}" fill="{col}"/>')
        if b["il"].minute == 0:
            out.append(f'<text x="{x:.1f}" y="{H-8}" fill="#8b949e" font-size="11" text-anchor="middle">{b["il"].strftime("%H:%M")}</text>'
                       f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{H-bot}" stroke="#161b22"/>')
    idx = {b["il"].strftime("%H:%M"): i for i, b in enumerate(bars)}
    def xof(hhmm):
        i = idx.get(hhmm[:3] + str(int(hhmm[3:]) // 5 * 5).zfill(2))
        return None if i is None else i * cw + cw / 2
    for r in day_recs:
        xe = xof(r["time"])
        if xe is None: continue
        col = "#3fb950" if (r["pnl"] or 0) > 0 else "#f85149" if (r["pnl"] or 0) < 0 else "#d29922"
        ye = y(r["entry"])
        if r["dir"] == "LONG":
            out.append(f'<polygon points="{xe:.1f},{ye+3:.1f} {xe-6:.1f},{ye+13:.1f} {xe+6:.1f},{ye+13:.1f}" fill="{col}" stroke="#0b0e14"/>')
        else:
            out.append(f'<polygon points="{xe:.1f},{ye-3:.1f} {xe-6:.1f},{ye-13:.1f} {xe+6:.1f},{ye-13:.1f}" fill="{col}" stroke="#0b0e14"/>')
        if r["exit"] is not None and r["exit_time"]:
            xx = xof(r["exit_time"])
            if xx is not None:
                out.append(f'<line x1="{xe:.1f}" y1="{ye:.1f}" x2="{xx:.1f}" y2="{y(r["exit"]):.1f}" stroke="{col}" stroke-width="2" stroke-dasharray="3,3"/>'
                           f'<circle cx="{xx:.1f}" cy="{y(r["exit"]):.1f}" r="3.5" fill="{col}"/>')
        out.append(f'<text x="{xe:.1f}" y="{(ye+26) if r["dir"]=="LONG" else (ye-17):.1f}" fill="{col}" font-size="10" text-anchor="middle">#{r["id"]}</text>')
    out.append("</svg>")
    return "".join(out)

def trade_card(r, d):
    hl = f'<span class="badge {r["mode"]}">{r["mode"]}</span>{r["time"]} · {HEB_DIR.get(r["dir"], r["dir"])} · {html.escape(r["pat"])}'
    sub = f'#{r["id"]} · <span class="num">{r["entry"]:.2f} → {r["exit"] if r["exit"] is not None else "—"}</span> · {html.escape(r["reason_heb"])} · {r["mins"] or 0} דק׳'
    lbl = f'{d} {r["time"]} {html.escape(r["pat"])} {r["dir"]}'
    return (f'<div class="card {cat_cls(r["cat"])}" id="t{r["id"]}"><div class="row" onclick="tog(this.parentNode)">'
            f'<div class="grow"><div class="hl">{hl}</div><div class="dim">{sub}</div></div>{money(r["pnl"], True)}<span class="chev">‹</span></div>'
            f'<div class="body"><div>{html.escape(r["ctx"])}</div><div style="margin-top:8px"><b>{html.escape(r["why"])}</b></div>'
            + (f'<div style="margin-top:8px">💡 {html.escape(r["more"])}</div>' if r["more"] else "")
            + (f'<div class="dim" style="margin-top:8px">לקח: {html.escape(r["lesson"])}</div>' if r["lesson"] else "")
            + f'<div class="tags"><button onclick="tag({r["id"]},\'✓ נכונה\',\'{lbl}\')">✓ נכונה</button>'
            f'<button onclick="tag({r["id"]},\'✗ לא נכונה\',\'{lbl}\')">✗ לא נכונה</button>'
            f'<button onclick="tag({r["id"]},\'💬 הערה\',\'{lbl}\')">💬 הערה</button></div></div></div>')

# ── day pages ─────────────────────────────────────────────────────────────────
for k, d in enumerate(days):
    bars = by_day[d]; rth = [b for b in bars if b["rth"]]
    lv, sh, rs = day_summary(d)
    live_recs = [r for r in rs if r["mode"] == "live"]
    meta = dth.get(d, {}); dd = dt.date.fromisoformat(d)
    o, h_, l_, c_ = rth[0]["o"], max(b["h"] for b in rth), min(b["l"] for b in rth), rth[-1]["c"]
    prev_d = days[k - 1] if k > 0 else None; next_d = days[k + 1] if k + 1 < len(days) else None
    nav = ((f'<a class="btn" href="{prev_d}.html">‹</a>' if prev_d else '<span></span>')
           + (f'<a class="btn" href="{next_d}.html">›</a>' if next_d else ''))
    kpis = (f'<div class="kpis"><div class="kpi"><div class="l">לייב</div><div class="v">{money(lv["sum"], True)}</div><div class="dim">{lv["n"]} עסקאות · {lv["w"]} ניצחונות</div></div>'
            f'<div class="kpi"><div class="l">צל</div><div class="v">{money(sh["sum"], True)}</div><div class="dim">{sh["n"]} עסקאות · {sh["w"]} ניצחונות</div></div>'
            f'<div class="kpi"><div class="l">סוג-יום</div><div class="v" style="font-size:16px">{meta.get("day_type") or "?"}</div><div class="dim">פתיחה {meta.get("opening_type") or "?"}</div></div>'
            f'<div class="kpi"><div class="l">טווח</div><div class="v num" style="font-size:16px">{l_:.0f}–{h_:.0f}</div><div class="dim num">{h_-l_:.1f} נק׳ · סגירה {c_-o:+.1f}</div></div></div>')
    svgs = {cw: candle_svg(bars, live_recs, cw=cw) for cw in (6, 9, 14)}
    svgs_sh = {cw: candle_svg(bars, [r for r in rs if r["mode"] in ("live", "shadow")], cw=cw) for cw in (6, 9, 14)}
    chart = (f'<h2>הנרות <span class="dim">({len(rth)} ברי-5-דק׳)</span></h2>'
             f'<div class="tools"><button id="z6" onclick="zoomC(6)">צר</button><button id="z9" class="on" onclick="zoomC(9)">רגיל</button><button id="z14" onclick="zoomC(14)">רחב</button>'
             f'<button id="zs" onclick="toggleShadow()">+ צל</button></div>'
             f'<div class="chartwrap" id="cw">{svgs[9]}</div><div class="legend"><span>▲/▼ כניסה</span><span>● יציאה</span><span>אפור = לפני הפתיחה</span></div>')
    order = live_recs + [r for r in rs if r["mode"] == "demo"] + [r for r in rs if r["mode"] == "shadow"]
    cards = [f'<h2>העסקאות <span class="dim">לחיצה = הסבר ותיוג</span></h2>']
    if not order: cards.append('<div class="card">אין עסקאות ביום זה.</div>')
    if live_recs: cards.append('<div class="dim">לייב</div>')
    cards += [trade_card(r, d) for r in live_recs]
    shadow_recs = [r for r in rs if r["mode"] == "shadow"]
    if shadow_recs:
        cards.append(f'<div class="card"><div class="row" onclick="tog(this.parentNode)"><div class="grow"><div class="hl">צל — {len(shadow_recs)} עסקאות</div><div class="dim">{sh["w"]} ניצחונות · {money(sh["sum"])}</div></div><span class="chev">‹</span></div><div class="body">'
                     + "".join(trade_card(r, d) for r in shadow_recs) + '</div></div>')
    js = ("<script>var SV=" + json.dumps(svgs) + ";var SVS=" + json.dumps(svgs_sh) + ";var _cw=9,_sh=false;"
          "function draw(){document.getElementById('cw').innerHTML=(_sh?SVS:SV)[_cw];[6,9,14].forEach(function(w){document.getElementById('z'+w).classList.toggle('on',w==_cw);});document.getElementById('zs').classList.toggle('on',_sh);}"
          "function zoomC(w){_cw=w;draw();}function toggleShadow(){_sh=!_sh;draw();}</script>")
    with open(os.path.join(OUT, "days", f"{d}.html"), "w", encoding="utf-8") as fh:
        fh.write(shell(f"יום {HEB_WD[dd.weekday()]} {dd.strftime('%d.%m.%Y')}", kpis + chart + "".join(cards), js, prefix="../",
                       sub=f'{meta.get("day_type") or "?"} · לייב {lv["n"]} · {lv["sum"]:+.0f}$', active="days.html", left_btn=nav))

# ── days index ────────────────────────────────────────────────────────────────
dl = ['<h1>ימי-מסחר</h1><div class="dim">לחיצה על יום פותחת נרות, עסקאות והסברים.</div>']
for d in reversed(days):
    lv, sh, rs = day_summary(d); dd = dt.date.fromisoformat(d)
    dl.append(f'<a href="days/{d}.html"><div class="card"><div class="row"><div class="grow"><div class="hl">{HEB_WD1[dd.weekday()]} {dd.strftime("%d.%m")} · {dth.get(d,{}).get("day_type") or "?"}</div>'
              f'<div class="dim">לייב {lv["n"]} ({lv["w"]} ✓) · צל {sh["n"]} {money(sh["sum"])}</div></div>{money(lv["sum"], True)}<span class="chev">‹</span></div></div></a>')
with open(os.path.join(OUT, "days.html"), "w", encoding="utf-8") as fh:
    fh.write(shell("ימי-מסחר", "".join(dl), active="days.html"))

# ── trades ledger ─────────────────────────────────────────────────────────────
pats = sorted({r["pat"] for r in recs if r["pat"]})
body = ('<h1>כל העסקאות</h1><div class="dim">ברירת-מחדל: לייב. לחיצה על שורה = הסבר; לחיצה על התאריך = הנרות של היום.</div>'
        '<div class="filters">'
        '<select id="fMode"><option value="live">לייב</option><option value="">כל המצבים</option><option value="demo">דמו</option><option value="shadow">צל</option></select>'
        '<select id="fDay"><option value="">כל הימים</option>' + "".join(f'<option value="{d}">{d[8:]}.{d[5:7]}</option>' for d in sorted(set(r["day"] for r in recs), reverse=True)) + '</select>'
        '<select id="fDir"><option value="">כל הכיוונים</option><option value="LONG">לונג</option><option value="SHORT">שורט</option></select>'
        '<select id="fCat"><option value="">כל התוצאות</option><option value="WIN">ניצחון</option><option value="LOSS">הפסד</option><option value="SCRATCH">סקראץ׳</option><option value="UNPRICED">לא-נכתבה</option></select>'
        '<select id="fPat" style="grid-column:1/3"><option value="">כל התבניות</option>' + "".join(f'<option value="{html.escape(p)}">{html.escape(p)}</option>' for p in pats) + '</select>'
        '</div><div class="kpis" id="sum"></div><div id="tb"></div>')
ljs = ("<script>var T=" + json.dumps(recs, ensure_ascii=False) + ";var HD={LONG:'לונג',SHORT:'שורט'};"
       "function fmt(v){if(v===null||v===undefined)return '<span class=dim>—</span>';return '<span class=\"num '+(v>0?'pos':v<0?'neg':'')+'\">'+(v>0?'+':'')+v.toFixed(2)+'$</span>';}"
       "function render(){var m=fMode.value,d=fDay.value,dr=fDir.value,c=fCat.value,p=fPat.value;var rows=T.filter(function(r){return (!m||r.mode==m)&&(!d||r.day==d)&&(!dr||r.dir==dr)&&(!c||r.cat==c)&&(!p||r.pat==p);});"
       "var n=rows.length,w=rows.filter(function(r){return r.pnl>0;}).length,s=rows.reduce(function(a,r){return a+(r.pnl||0);},0);"
       "document.getElementById('sum').innerHTML='<div class=kpi><div class=l>עסקאות</div><div class=v>'+n+'</div></div><div class=kpi><div class=l>ניצחונות</div><div class=v>'+w+' <span class=dim style=\"font-size:13px\">('+(n?Math.round(100*w/n):0)+'%)</span></div></div><div class=kpi style=\"grid-column:1/3\"><div class=l>סה\"כ</div><div class=v>'+fmt(s)+'</div></div>';"
       "var h='',last='';rows.slice().reverse().forEach(function(r){if(r.day!=last){last=r.day;var dd=rows.filter(function(x){return x.day==r.day;});var ds=dd.reduce(function(a,x){return a+(x.pnl||0);},0);h+='<div class=dayhdr><a href=\"days/'+r.day+'.html\">'+r.day.slice(8)+'.'+r.day.slice(5,7)+' ↗</a><span>'+dd.length+' · '+fmt(ds)+'</span></div>';}"
       "h+='<div class=trow onclick=\"tg('+r.id+')\"><div class=grow><div class=a>'+r.time+' · '+(HD[r.dir]||r.dir)+' · '+r.pat+' <span class=\"badge '+r.mode+'\">'+r.mode+'</span></div><div class=b>#'+r.id+' · '+r.reason_heb+' · '+(r.mins||0)+' דק׳</div></div>'+fmt(r.pnl)+'</div>';"
       "h+='<div class=detail id=\"d'+r.id+'\"><div class=\"dim num\">כניסה '+r.entry.toFixed(2)+' → '+(r.exit===null?'—':r.exit.toFixed(2))+' · T1 '+(r.t1p===null?'—':r.t1p)+' נק׳ · MFE-שעה '+(r.mfe60===null?'—':r.mfe60)+' · MAE '+(r.mae===null?'—':r.mae)+' · '+(r.zone||'')+'</div><div>'+r.ctx+'</div><div><b>'+r.why+'</b></div>'+(r.more?'<div>💡 '+r.more+'</div>':'')+(r.lesson?'<div class=dim>לקח: '+r.lesson+'</div>':'')+'<div><a href=\"days/'+r.day+'.html#t'+r.id+'\">↗ לנרות ולתיוג</a></div></div>';});"
       "document.getElementById('tb').innerHTML=h||'<div class=card>אין עסקאות בפילטר הזה.</div>';document.querySelectorAll('#tb a[href]').forEach(function(a){var x=a.getAttribute('href');if(x.indexOf('key=')<0){var i=x.indexOf('#');var b=i>=0?x.slice(0,i):x,hh=i>=0?x.slice(i):'';a.setAttribute('href',b+'?'+Q.slice(1)+hh);}});}"
       "function tg(id){var e=document.getElementById('d'+id);e.style.display=e.style.display=='block'?'none':'block';}"
       "['fMode','fDay','fDir','fCat','fPat'].forEach(function(i){document.getElementById(i).onchange=render;});render();</script>")
with open(os.path.join(OUT, "trades.html"), "w", encoding="utf-8") as fh:
    fh.write(shell("כל העסקאות", body, ljs, active="trades.html"))

# ── missed trades ─────────────────────────────────────────────────────────────
mp = os.path.join(OUT, "data", "missed.json")
if os.path.exists(mp):
    M = json.load(open(mp, encoding="utf-8"))
    V_HEB = {"TOOK": ("✅ נלקחה", "ok"), "LATE": ("🕒 מאוחר", "warn"), "OPPOSITE": ("❌ הפוך", "bad"), "MISSED": ("⭕ פוספסה", "bad"), "UNCATCHABLE": ("⚪ לא ניתנת-לתפיסה", "")}
    DEPTH = {"HIGH": "עומק גבוה", "NORMAL": "עומק רגיל", "LOW": "עומק נמוך"}
    legs = M["legs"]; nm = sum(1 for r in legs if r["verdict"] == "MISSED"); nt = sum(1 for r in legs if r["verdict"] == "TOOK")
    mb = [f'<h1>מה פספסנו</h1><div class="dim">{len(M["sessions"])} סשנים · מהלכים ≥ 12 נק׳ ו-≥ 3 ברים · נרות, ווליום ומיקום — לא תבניות · {M["generated"][:16]}</div>',
          f'<div class="kpis"><div class="kpi"><div class="l">מהלכים</div><div class="v">{len(legs)}</div></div><div class="kpi"><div class="l">פוספסו (ניתנות-לתפיסה)</div><div class="v neg">{nm}</div><div class="dim num">{sum(r["pts"] for r in legs if r["verdict"]=="MISSED"):.0f} נק׳</div></div>'
          f'<div class="kpi"><div class="l">נלקחו בזמן</div><div class="v pos">{nt}</div></div><div class="kpi"><div class="l">מאוחר / הפוך</div><div class="v">{sum(1 for r in legs if r["verdict"]=="LATE")} / {sum(1 for r in legs if r["verdict"]=="OPPOSITE")}</div></div></div>',
          '<h2>לפי סוג-יום × עומק — מה משותף לכניסות שהיו נכונות</h2><div class="dim">החתימה = אחוז הכניסות-האידיאליות עם התכונה. ≥70% = חומר לענף.</div>']
    for g in M["groups"]:
        s = g["signature"] or {}
        pills = "".join(f'<span class="pill {"ok" if v >= 70 else ""}">{k} {v}%</span>' for k, v in s.items() if isinstance(v, int) and k != "n")
        mb.append(f'<div class="card"><div class="row" onclick="tog(this.parentNode)"><div class="grow"><div class="hl">{html.escape(g["day_type"])} · {DEPTH[g["depth"]]}</div>'
                  f'<div class="dim">{g["legs"]} מהלכים · פוספסו {g["missed"]} ({g["missed_pts"]} נק׳) · נלקחו {g["took"]} · מאוחר {g["late"]} · הפוך {g["opposite"]}</div></div><span class="chev">‹</span></div>'
                  f'<div class="body">{pills}<div class="dim" style="margin-top:6px">אזורים: {html.escape(str(s.get("zones", {})))} · שלבים: {html.escape(str(s.get("phases", {})))}</div>'
                  f'<div style="margin-top:6px"><b>ענף מוצע:</b> {html.escape(" + ".join(g["strong"]) if g["strong"] else "אין חתימה חזקה (N קטן) — לאסוף עוד ימים")}</div></div></div>')
    mb.append('<h2>יום אחרי יום</h2>')
    for d in M["sessions"]:
        rs = [r for r in legs if r["day"] == d]
        if not rs: continue
        r0 = rs[0]; dd = dt.date.fromisoformat(d)
        items = []
        for r in rs:
            vh, vc = V_HEB.get(r["verdict"], (r["verdict"], ""))
            took = ("<br>" + " · ".join(f'#{t["id"]} {t["pat"]} {t["time"]} ({("%+.0f$" % t["pnl"]) if t["pnl"] is not None else "—"})' for t in r["took"])) if r["took"] else ""
            ideal = ""
            if r["ideal"]:
                i = r["ideal"]
                ideal = (f'<div style="margin-top:6px"><b>כניסה אידיאלית {i["time"]} @<span class="num">{i["price"]:.2f}</span></b> · סטופ {i["stop"]} נק׳ · היה נותן {i["captured"]} נק׳</div>'
                         f'<div>{html.escape(i["desc"])}</div><div class="dim">מפיקי-צל שראו (±10 דק׳): {html.escape(", ".join(i["seen_by"]) if i["seen_by"] else "אף אחד")}</div>')
            items.append(f'<div class="card"><div class="row" onclick="tog(this.parentNode)"><div class="grow"><div class="hl"><span class="num">{r["start"]}→{r["end"]}</span> {HEB_DIR[r["dir"]]} <span class="num">{r["pts"]}</span> נק׳</div>'
                         f'<div class="dim"><span class="pill {vc}">{vh}</span></div></div><span class="chev">‹</span></div><div class="body"><div class="dim num">{r["from_px"]:.2f} → {r["to_px"]:.2f}{took}</div>{ideal}</div></div>')
        mb.append(f'<div class="dayhdr"><a href="days/{d}.html">{HEB_WD1[dd.weekday()]} {dd.strftime("%d.%m")} · {html.escape(r0["day_type"])} · {DEPTH[r0["depth"]]} ↗</a><span>{len(rs)} מהלכים</span></div>' + "".join(items))
    with open(os.path.join(OUT, "missed.html"), "w", encoding="utf-8") as fh:
        fh.write(shell("מה פספסנו", "".join(mb), active="missed.html", sub="נרות · ווליום · מיקום"))

# ── lessons Gantt ─────────────────────────────────────────────────────────────
LESSONS = json.load(open(os.path.join(ROOT, "docs", "plans", "LESSONS_TIMELINE.json"), encoding="utf-8"))
tdays = [x["day"] for x in LESSONS["days"]][::-1]
live_by_day = {}
for r in recs:
    if r["mode"] == "live" and r["pnl"] is not None:
        live_by_day.setdefault(r["day"], []).append(r["pnl"])
gl = ['<h1>לקחים וענפים</h1><div class="dim">חדש מימין. כל עמודה יום-מסחר, כל שורה חוט. ירוק=ענף/גרסה · כחול=מדידה · צהוב=באג שתוקן · אדום=תקרית · סגול=פסיקה. גלילה לצדדים.</div>',
      '<div class="gantt"><table><thead><tr><th class="lbl"></th>' + "".join(f'<th>{d[8:]}.{d[5:7]}</th>' for d in tdays) + '</tr></thead><tbody>']
gl.append('<tr><td class="lbl">לייב $</td>' + "".join(
    (f'<td class="num"><span class="{"pos" if sum(live_by_day[d])>0 else "neg"}">{sum(live_by_day[d]):+.0f}</span></td>' if d in live_by_day else '<td class="dim">—</td>') for d in tdays) + '</tr>')
for th in LESSONS["threads"]:
    cells = ['<td>' + "".join(f'<span class="g {it.get("k","b")}" title="{html.escape(it.get("ref",""))}">{html.escape(it["t"])}</span>' for it in th["items"] if it["day"] == d) + '</td>' for d in tdays]
    gl.append(f'<tr><td class="lbl">{html.escape(th["name"])}</td>' + "".join(cells) + '</tr>')
gl.append('</tbody></table></div><h2>הלקח של כל יום</h2>')
for x in LESSONS["days"][::-1]:
    gl.append(f'<div class="card"><b>{x["day"][8:]}.{x["day"][5:7]}</b> — {html.escape(x["lesson"])}' + (f' <a href="days/{x["day"]}.html">↗ הנרות</a>' if x["day"] in days else "") + '</div>')
with open(os.path.join(OUT, "lessons.html"), "w", encoding="utf-8") as fh:
    fh.write(shell("לקחים וענפים", "".join(gl), active="lessons.html"))

# ── tree identity page (from the markdown, simple render) ─────────────────────
tp = os.path.join(ROOT, "docs", "spec_authority", "DALTON_TREE_IDENTITY.md")
if os.path.exists(tp):
    import re
    md = open(tp, encoding="utf-8").read()
    def md2html(md):
        out, in_tbl = [], False
        for line in md.split("\n"):
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells): continue
                if not in_tbl: out.append('<div style="overflow-x:auto"><table class="plain">'); in_tbl = True
                tag_ = "th" if len(out) and out[-1].endswith("<table class=\"plain\">") else "td"
                out.append("<tr>" + "".join(f"<{tag_}>{c}</{tag_}>" for c in cells) + "</tr>")
                continue
            if in_tbl: out.append("</table></div>"); in_tbl = False
            if line.startswith("# "): out.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "): out.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("- "): out.append(f"<div class='card' style='padding:8px 12px'>{line[2:]}</div>")
            elif line.strip(): out.append(f"<p>{line}</p>")
        if in_tbl: out.append("</table></div>")
        h = "\n".join(out)
        h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h); h = re.sub(r"`(.+?)`", r"<code>\1</code>", h)
        return h
    with open(os.path.join(OUT, "tree.html"), "w", encoding="utf-8") as fh:
        fh.write(shell("עץ-דלתון", md2html(md), sub="תעודת-זהות וסקירה"))

# ── index ─────────────────────────────────────────────────────────────────────
last = days[-1] if days else None
ib = [f'<h1>MEMS26</h1><div class="dim">תיעוד למסחר · נוצר {NOW.strftime("%d.%m %H:%M")} · מתרענן בכל EOD</div>']
if last:
    lv, sh, rs = day_summary(last); dd = dt.date.fromisoformat(last)
    ib.append(f'<h2>הסשן האחרון — {HEB_WD[dd.weekday()]} {dd.strftime("%d.%m")}</h2>'
              f'<div class="kpis"><div class="kpi"><div class="l">לייב</div><div class="v">{money(lv["sum"], True)}</div><div class="dim">{lv["n"]} עסקאות · {lv["w"]} ניצחונות</div></div>'
              f'<div class="kpi"><div class="l">סוג-יום</div><div class="v" style="font-size:16px">{dth.get(last,{}).get("day_type") or "?"}</div><div class="dim">צל {sh["n"]} · {money(sh["sum"])}</div></div></div>'
              f'<a href="days/{last}.html"><div class="card"><div class="row"><div class="grow"><div class="hl">📅 הנרות והעסקאות של {dd.strftime("%d.%m")}</div><div class="dim">הסבר לכל עסקה + תיוג</div></div><span class="chev">‹</span></div></div></a>')
ib.append('<h2>מקומות</h2>')
for h, ic, n, s in MENU[1:]:
    ib.append(f'<a href="{h}"><div class="card"><div class="row"><div class="grow"><div class="hl">{ic} {html.escape(n)}</div><div class="dim">{html.escape(s)}</div></div><span class="chev">‹</span></div></div></a>')
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(shell("MEMS26", "".join(ib), active="index.html"))
print(f"pages: index, days ({len(days)}), trades ({len(recs)} rows), missed, lessons, tree → {OUT}")
