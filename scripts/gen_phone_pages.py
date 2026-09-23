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

# ── broker truth (Michael 23.09: "חייבים לאמת מול סיירה מה ההפסד ומה הרווח") ──
# scripts/broker_truth.py reconciles every live trade against Sierra's own closed-trade P&L
# (trade_activity_events.jsonl: CLOSED_TRADE_PNL per round-trip, net of commission) and writes
# v9_trades.pnl_sierra. For LIVE rows the broker figure is the number; the books (pnl_usd —
# target-price arithmetic, no commission, no entry slippage) are shown next to it with Δ.
_bp = os.path.join(OUT, "data", "broker.json")
BROKER = {}
if os.path.exists(_bp):
    try:
        BROKER = {int(r["id"]): r for r in json.load(open(_bp, encoding="utf-8")).get("trades", [])}
    except Exception as _e:
        print("broker.json unreadable:", _e)

def broker_note(t):
    """Why a live trade has no broker number (honest, Rule 1) — or a caveat on the one it has."""
    if t["mode"] != "live": return ""
    b = BROKER.get(int(t["id"]))
    if b and b.get("mixed"): return f"מעורב: הפוזיציה אצל הברוקר הייתה {b.get('qty')} חוזים מול {b.get('contracts')} של המערכת (חוזים ידניים, T-402) — הרווח/הפסד של הפוזיציה כולה {b['broker']:+.2f}$"
    if t["pnl_sierra"] is None:
        if b and b.get("broker") is None: return "אין רישום-ברוקר לעסקה הזו (פיד-הפעילות לא רץ באותה שעה)"
        return "טרם אומת מול הברוקר"
    return ""

def pnl_eff(t):
    """The P&L we show: broker (pnl_sierra) for live when reconciled; books otherwise."""
    if t["mode"] == "live" and t["pnl_sierra"] is not None: return float(t["pnl_sierra"])
    return float(t["pnl_usd"]) if t["pnl_usd"] is not None else None

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
    p = pnl_eff(t)   # broker-first for live (23.09): a MAE_SCRATCH with books NULL but broker −36.25 is a LOSS
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
    elif cat == "LOSS" and t["exit_reason"] == "MAE_SCRATCH":
        why.append(f"נסגרה ע״י שער-ה-MAE (הגנה) בהפסד של {abs(pnl_eff(t) or 0):.2f}$ לפי הברוקר — הספרים לא רשמו מחיר-יציאה ולכן הציגו אותה כ׳לא-נכתבה׳.")
        more.append(f"אחרי היציאה המהלך הגיע ל-{f['mfe_eod']:.1f} נק׳ לטובת הכיוון" + (" — היציאה הייתה מוקדמת." if f["mfe_eod"] >= 8 else " — היציאה הייתה נכונה (הסטופ המלא היה עולה יותר)."))
        lesson = "סקראץ׳-MAE = הפסד קטן במקום גדול; לבדוק את סף-ה-MAE מול MFE אחרי היציאה."
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
    elif cat == "UNPRICED" and t["exit_reason"] == "ladder_invalid":
        why.append("לא נכתבה פקודה: סולם-היעדים לא היה מונוטוני (T-335 / T-438) — בוטלה לפני שנשלחה.")
        more.append(f"מה היה קורה: MFE-שעה {f['mfe60']:.1f} נק׳, MAE {f['mae_x']:.1f}.")
        lesson = "באג-ביצוע, לא החלטת-מסחר — פריט T-438 (נסגר 22.09)."
    elif cat == "UNPRICED":
        why.append(f"נסגרה ({REASON_HEB.get(t['exit_reason'], t['exit_reason'])}) בלי מחיר-יציאה בספרים, ו" + (broker_note(t) or "אין מספר-ברוקר") + ".")
        more.append(f"מה קרה אחרי: MFE עד הסגירה {f['mfe_eod']:.1f} נק׳, MAE בעסקה {f['mae_x']:.1f}.")
        lesson = "ליקוי-רישום, לא החלטת-מסחר — רשימת-הליקויים 23.09."
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
        # 23.09: when exit_price was never written the number shown is the TARGET, not a fill — say so
        "exit_is_target": t["exit_price"] is None and t["exit_reason"] == "T1_HIT" and bool(t["t1"]),
        "exit_time": t["exit_ts"].astimezone(IL).strftime("%H:%M") if t["exit_ts"] else "",
        "reason": t["exit_reason"] or "", "reason_heb": REASON_HEB.get(t["exit_reason"] or "", t["exit_reason"] or ""),
        "pnl": pnl_eff(t),                                                        # what we show (broker-first for live)
        "books": float(t["pnl_usd"]) if t["pnl_usd"] is not None else None,       # our arithmetic
        "pnl_broker": float(t["pnl_sierra"]) if t["pnl_sierra"] is not None else None,
        "bnote": broker_note(t),
        "src": "ברוקר" if (t["mode"] == "live" and t["pnl_sierra"] is not None) else ("ספרים" if t["mode"] == "live" else "תיאורטי"),
        "dt": t["dt"] or "", "phase": f["phase"] if f else "", "cat": category(t),
        "t1p": round(f["t1p"], 2) if f and f["t1p"] is not None else None,
        "mfe60": round(f["mfe60"], 2) if f else None, "mfe_eod": round(f["mfe_eod"], 2) if f else None,
        "mae": round(f["mae_x"], 2) if f else None, "pos": round(f["pos"], 2) if f else None,
        "zone": f["zone"] if f else "", "mins": round(f["mins"]) if f else None,
        "ctx": ctx, "why": why, "more": more, "lesson": lesson,
    })

# ── app shell ─────────────────────────────────────────────────────────────────
# (UX pass 22.09 11:30 — Michael: "לעבור על כולם ולהציע שיפורים ולבצע, שתהיה גלישה חלקה וברורה")
# Principles: one header everywhere (☰ + title + context buttons) · bottom tabs for the 5 places ·
# every list = cards with a headline you can scan + a body you open · Hebrew labels only ·
# candles drawn client-side from a tiny JSON (fit-to-screen by default) · pages ≤ 120 KB.
CSS = """
:root{color-scheme:dark;--bg:#0b0e14;--card:#161b22;--line:#30363d;--fg:#e6edf3;--dim:#8b949e;--acc:#58a6ff;--up:#3fb950;--dn:#f85149;--am:#d29922}
*{box-sizing:border-box}
html,body{max-width:100%;overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;font-size:17px;line-height:1.5;padding:0 0 78px}
a{color:var(--acc);text-decoration:none}
.hdr{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:8px;background:#0d1117;border-bottom:1px solid var(--line);padding:8px 10px;padding-top:calc(8px + env(safe-area-inset-top))}
.hdr .t{flex:1;min-width:0;font-weight:700;font-size:17px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hdr .sub{font-size:12px;color:var(--dim);font-weight:400;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ib{background:var(--card);border:1px solid var(--line);color:var(--fg);border-radius:10px;font-size:19px;min-width:42px;height:40px;display:inline-flex;align-items:center;justify-content:center;padding:0 10px;text-decoration:none}
.ib.dis{opacity:.35;pointer-events:none}
.drawer{position:fixed;inset:0;z-index:30;display:none}
.drawer.open{display:block}
.drawer .bg{position:absolute;inset:0;background:rgba(0,0,0,.6)}
.drawer .panel{position:absolute;top:0;right:0;bottom:0;width:min(84vw,340px);background:#0d1117;border-left:1px solid var(--line);padding:14px 12px;overflow-y:auto;padding-top:calc(14px + env(safe-area-inset-top))}
.drawer .brand{display:flex;align-items:center;justify-content:space-between;margin:0 4px 10px;font-weight:700}
.drawer h3{margin:12px 4px 4px;font-size:12px;color:var(--dim);font-weight:600;letter-spacing:.3px}
.drawer a.item{display:flex;align-items:center;gap:10px;padding:11px 10px;border-radius:10px;color:var(--fg);font-size:16px}
.drawer a.item.on{background:#1f2a3a;border:1px solid #1f6feb}
.drawer a.item:active{background:var(--card)}
.drawer a.item small{margin-right:auto;color:var(--dim);font-size:12px}
.wrap{padding:12px 12px 8px}
h1{font-size:21px;margin:6px 0 4px}
h2{font-size:15px;margin:18px 0 8px;color:#c9d1d9;display:flex;align-items:center;gap:8px}
h2 .dim{font-weight:400}
.dim{color:var(--dim);font-size:13px}
.num{direction:ltr;unicode-bidi:embed;font-variant-numeric:tabular-nums}
.kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:10px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px;min-width:0}
.kpi .l{font-size:12px;color:var(--dim)}.kpi .v{font-size:20px;font-weight:700;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.kpi .s{font-size:12px;color:var(--dim)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin:10px 0}
.card.lnk{padding:0}.card.lnk>a{display:block;padding:12px 14px;color:var(--fg)}
.win{border-right:5px solid var(--up)}.loss{border-right:5px solid var(--dn)}.scratch{border-right:5px solid var(--am)}.unpriced{border-right:5px solid var(--dim)}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;background:#21262d;border:1px solid var(--line);margin-left:6px;vertical-align:middle}
.badge.live{background:#1f3a2a;border-color:#2ea043;color:#7ee787}.badge.shadow{background:#2a2a1f;border-color:#9e6a03;color:#e3b341}.badge.demo{background:#1f2a3a;border-color:#1f6feb;color:#79c0ff}
.pos{color:var(--up)}.neg{color:var(--dn)}
.pnl{font-weight:700;font-size:18px;white-space:nowrap}
.row{display:flex;align-items:center;gap:8px;cursor:pointer}
.row .grow{flex:1;min-width:0}
.row .hl{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chev{color:var(--dim);font-size:20px;transition:transform .15s;flex:none}
.card.open .chev{transform:rotate(-90deg)}
.body{display:none;margin-top:10px;border-top:1px solid var(--line);padding-top:10px}
.card.open .body{display:block}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:0 0 8px}
.facts div{background:#0d1117;border-radius:8px;padding:6px 6px;text-align:center;min-width:0}
.facts .l{font-size:10.5px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.facts .v{font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.line{display:flex;gap:8px;margin:7px 0;font-size:15px;line-height:1.45}
.line .ic{flex:none;width:22px;text-align:center}
.chartwrap{overflow-x:auto;direction:ltr;-webkit-overflow-scrolling:touch;background:#0d1117;border:1px solid var(--line);border-radius:12px;padding:4px 0}
.chartwrap svg{display:block}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.chip{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:999px;padding:7px 12px;font-size:14px;cursor:pointer;user-select:none}
.chip.on{background:#1f6feb;border-color:#1f6feb;color:#fff}
.tags{display:flex;gap:6px;margin-top:10px}
.tags button{flex:1;background:#21262d;color:var(--fg);border:1px solid var(--line);border-radius:10px;padding:11px 4px;font-size:15px}
.tags button:active{background:#30363d}
.selrow{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:6px 0}
select{width:100%;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:10px;padding:10px;font-size:16px}
.dayhdr{background:#0d1117;border:1px solid var(--line);border-radius:10px;padding:8px 12px;margin:14px 0 6px;font-weight:600;display:flex;justify-content:space-between;gap:8px}
.trow{display:flex;align-items:center;gap:8px;padding:10px 6px;border-bottom:1px solid #21262d;cursor:pointer}
.trow .grow{flex:1;min-width:0}
.trow .a{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.trow .b{font-size:13px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.detail{display:none;background:#0d1117;border-radius:10px;padding:10px;margin:0 0 6px;font-size:15px}
.tl{position:relative;padding-right:22px;margin:6px 0}
.tl:before{content:"";position:absolute;right:8px;top:0;bottom:0;width:2px;background:var(--line)}
.tl .ev{position:relative;margin:0 0 12px}
.tl .ev:before{content:"";position:absolute;right:-18px;top:8px;width:10px;height:10px;border-radius:50%;background:var(--acc);border:2px solid var(--bg)}
.tl .d{font-weight:700}
.gantt{overflow-x:auto;-webkit-overflow-scrolling:touch;display:none}
.gantt.show{display:block}
.gantt table{border-collapse:collapse;min-width:640px;font-size:12px}
.gantt th,.gantt td{padding:6px 4px;border-bottom:1px solid #21262d;text-align:center;vertical-align:top}
.gantt td.lbl,.gantt th.lbl{text-align:right;white-space:nowrap;font-weight:600;color:#c9d1d9;position:sticky;right:0;background:var(--bg)}
.g{display:inline-block;border-radius:6px;padding:2px 7px;font-size:12px;color:#0b0e14;font-weight:600;margin:2px 2px 2px 0}
.g.a{background:#7ee787}.g.b{background:#79c0ff}.g.c{background:#e3b341}.g.d{background:#ff7b72}.g.e{background:#d2a8ff}
.legend span{display:inline-block;margin-left:10px;font-size:12px;color:var(--dim)}
.bottom{position:fixed;left:0;right:0;bottom:0;z-index:20;display:flex;background:#0d1117;border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}
.bottom a{flex:1;text-align:center;padding:7px 2px 5px;color:var(--dim);font-size:11px}
.bottom a b{display:block;font-size:21px;font-weight:400;line-height:1.2}
.bottom a.on{color:var(--acc)}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid var(--line);background:#21262d;margin:2px 0 2px 4px}
.pill.ok{border-color:#2ea043;color:#7ee787}.pill.bad{border-color:#da3633;color:#ffa198}.pill.warn{border-color:#9e6a03;color:#e3b341}
table.plain{border-collapse:collapse;width:100%;font-size:14px}
table.plain th,table.plain td{padding:7px 6px;border-bottom:1px solid #21262d;text-align:right;vertical-align:top}
table.plain th{color:var(--dim);font-weight:600}
.toast{position:fixed;left:50%;bottom:calc(84px + env(safe-area-inset-bottom));transform:translateX(-50%);background:#1f3a2a;color:#7ee787;border:1px solid #2ea043;border-radius:999px;padding:8px 16px;font-size:14px;z-index:40;display:none}
.toast.show{display:block}
.empty{color:var(--dim);text-align:center;padding:24px 0}
"""
MENU = [("index.html", "🏠", "בית", "הסשן האחרון", "עכשיו"), ("/", "💬", "צ׳אט עם המערכת", "הודעות ופקודות", "עכשיו"),
        ("days.html", "📅", "ימי-מסחר", "נרות + עסקאות ליום", "מסחר"), ("trades.html", "📒", "כל העסקאות", "לייב · דמו · צל", "מסחר"),
        ("missed.html", "⭕", "מה פספסנו", "נרות · ווליום · מיקום", "מסחר"), ("lessons.html", "📈", "לקחים וענפים", "יום אחרי יום", "למידה"),
        ("whatworks.html", "🧪", "מה עובד", "כניסות · מיקום · יציאות — במספרים", "למידה"),
        ("tree.html", "🌳", "עץ-דלתון", "הגרסאות והמצב", "למידה"), ("status_2026-09-20.html", "📄", "עדכון-מצב 20.09", "ענף-הפתיחה", "למידה"),
        ("review.html", "🔎", "סקירת-יום", "מה היה צריך לצאת · מה המערכת ראתה", "למידה"),
        ("defects.html", "🩹", "ליקויי-היומן", "ספרים מול ברוקר — הרשימה והתיקונים", "ניהול"),
        ("/readiness", "📋", "תיק-מוכנות", "48 פתוחים · 13 חוסמים", "ניהול")]
BOTTOM = [("index.html", "🏠", "בית"), ("days.html", "📅", "ימים"), ("trades.html", "📒", "עסקאות"), ("missed.html", "⭕", "פספוסים"), ("lessons.html", "📈", "לקחים")]

JS = r"""
<script>
var Q=location.search||'';
function withKey(h){if(!h||/^https?:|^#|^mailto:/.test(h)||h.indexOf('key=')>=0)return h;var i=h.indexOf('#');var b=i>=0?h.slice(0,i):h,hs=i>=0?h.slice(i):'';return b+(b.indexOf('?')>=0?'&':'?')+Q.slice(1)+hs;}
function fixLinks(root){(root||document).querySelectorAll('a[href]').forEach(function(a){a.setAttribute('href',withKey(a.getAttribute('href')));});}
fixLinks();
function drawer(o){document.getElementById('dr').classList.toggle('open',o);}
function tog(el){el.classList.toggle('open');}
function toast(t){var e=document.getElementById('toast');e.textContent=t;e.classList.add('show');setTimeout(function(){e.classList.remove('show');},1800);}
function tag(id,label,text){var note=prompt(label+' — הערה (אופציונלי):','');if(note===null)return;
 var msg='תיוג עסקה #'+id+' ('+text+'): '+label+(note?(' — '+note):'');
 fetch('/instruction'+Q,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:msg})})
 .then(function(r){return r.json();}).then(function(d){toast(d.ok?'נרשם ✓':'שגיאה');}).catch(function(){toast('שגיאה בשליחה');});}
if(location.hash){var el=document.getElementById(location.hash.slice(1));if(el){el.classList.add('open');setTimeout(function(){el.scrollIntoView({block:'center'});},60);}}
/* candles: bars=[[hhmm,o,h,l,c,rth]...], marks=[{id,t,e,x,xt,dir,pnl}] */
function candles(bars,marks,mode,W0){
 var n=bars.length;if(!n)return '';var H=330,top=14,bot=28,axis=56;
 var cw=mode==='fit'?Math.max(3,(W0-axis-8)/n):mode;var W=Math.ceil(n*cw+axis+8);
 var hi=-1e9,lo=1e9;bars.forEach(function(b){if(b[2]>hi)hi=b[2];if(b[3]<lo)lo=b[3];});
 marks.forEach(function(m){hi=Math.max(hi,m.e,m.x||m.e);lo=Math.min(lo,m.e,m.x||m.e);});
 var pad=(hi-lo)*0.05||1;hi+=pad;lo-=pad;function y(p){return top+(hi-p)/(hi-lo)*(H-top-bot);}
 var s='<svg xmlns="http://www.w3.org/2000/svg" width="'+W+'" height="'+H+'">';
 var step=(hi-lo)<60?5:(hi-lo)<120?10:25;for(var g=(Math.floor(lo/step)+1)*step;g<hi;g+=step){s+='<line x1="0" y1="'+y(g).toFixed(1)+'" x2="'+(W-axis)+'" y2="'+y(g).toFixed(1)+'" stroke="#21262d"/><text x="'+(W-axis+4)+'" y="'+(y(g)+4).toFixed(1)+'" fill="#8b949e" font-size="11">'+g+'</text>';}
 var idx={};bars.forEach(function(b,i){idx[b[0]]=i;var x=i*cw+cw/2,col=b[5]?(b[4]>=b[1]?'#3fb950':'#f85149'):'#484f58';
  s+='<line x1="'+x.toFixed(1)+'" y1="'+y(b[2]).toFixed(1)+'" x2="'+x.toFixed(1)+'" y2="'+y(b[3]).toFixed(1)+'" stroke="'+col+'"/>';
  var yo=y(b[1]),yc=y(b[4]),h=Math.max(Math.abs(yc-yo),1.2),bw=Math.max(cw*0.64,1.5);
  s+='<rect x="'+(x-bw/2).toFixed(1)+'" y="'+Math.min(yo,yc).toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+h.toFixed(1)+'" fill="'+col+'"/>';
  if(b[0].slice(3)==='00'&&(cw>=5||b[0]<'23')){s+='<text x="'+x.toFixed(1)+'" y="'+(H-7)+'" fill="#8b949e" font-size="10" text-anchor="middle">'+b[0]+'</text>';}});
 function xof(t){if(!t)return null;var k=t.slice(0,3)+(''+(Math.floor(parseInt(t.slice(3),10)/5)*5)).padStart(2,'0');var i=idx[k];return i==null?null:i*cw+cw/2;}
 marks.forEach(function(m){var xe=xof(m.t);if(xe==null)return;var col=(m.pnl||0)>0?'#3fb950':(m.pnl||0)<0?'#f85149':'#d29922';var ye=y(m.e);var sz=cw>=6?7:5;
  if(m.dir==='LONG')s+='<polygon points="'+xe.toFixed(1)+','+(ye+3).toFixed(1)+' '+(xe-sz).toFixed(1)+','+(ye+3+sz*1.6).toFixed(1)+' '+(xe+sz).toFixed(1)+','+(ye+3+sz*1.6).toFixed(1)+'" fill="'+col+'" stroke="#0b0e14"/>';
  else s+='<polygon points="'+xe.toFixed(1)+','+(ye-3).toFixed(1)+' '+(xe-sz).toFixed(1)+','+(ye-3-sz*1.6).toFixed(1)+' '+(xe+sz).toFixed(1)+','+(ye-3-sz*1.6).toFixed(1)+'" fill="'+col+'" stroke="#0b0e14"/>';
  if(m.x!=null&&m.xt){var xx=xof(m.xt);if(xx!=null){s+='<line x1="'+xe.toFixed(1)+'" y1="'+ye.toFixed(1)+'" x2="'+xx.toFixed(1)+'" y2="'+y(m.x).toFixed(1)+'" stroke="'+col+'" stroke-width="2" stroke-dasharray="3,3"/><circle cx="'+xx.toFixed(1)+'" cy="'+y(m.x).toFixed(1)+'" r="3.5" fill="'+col+'"/>';}}
  if(cw>=5)s+='<text x="'+xe.toFixed(1)+'" y="'+((m.dir==='LONG')?(ye+3+sz*1.6+11):(ye-3-sz*1.6-4)).toFixed(1)+'" fill="'+col+'" font-size="10" text-anchor="middle">#'+m.id+'</text>';});
 return s+'</svg>';}
</script>"""

def shell(title, body, extra_js="", prefix="", sub="", active="", right_btns=""):
    def href(h): return h if h.startswith("/") else prefix + h
    sections = []
    for sec in ("עכשיו", "מסחר", "למידה", "ניהול"):
        items = [m for m in MENU if m[4] == sec]
        sections.append(f'<h3>{sec}</h3>' + ''.join(
            f'<a class="item{" on" if h == active else ""}" href="{href(h)}"><span>{ic}</span><span>{html.escape(n)}</span><small>{html.escape(s)}</small></a>'
            for h, ic, n, s, _ in items))
    bottom = ''.join(f'<a href="{href(h)}" class="{"on" if h == active else ""}"><b>{ic}</b>{n}</a>' for h, ic, n in BOTTOM)
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>{html.escape(title)}</title>'
            f'<style>{CSS}</style></head><body>'
            f'<div class="hdr"><button class="ib" onclick="drawer(true)" aria-label="תפריט">☰</button><div class="t">{html.escape(title)}'
            + (f'<div class="sub">{html.escape(sub)}</div>' if sub else '') + f'</div>{right_btns}</div>'
            f'<div class="drawer" id="dr"><div class="bg" onclick="drawer(false)"></div><div class="panel"><div class="brand"><span>MEMS26</span><button class="ib" onclick="drawer(false)">✕</button></div>{"".join(sections)}</div></div>'
            f'<div class="wrap">{body}</div><div class="toast" id="toast"></div><div class="bottom">{bottom}</div>'
            + JS + extra_js + '</body></html>')

def money(v, big=False):
    if v is None: return '<span class="dim">—</span>'
    cls = "pos" if v > 0 else "neg" if v < 0 else ""
    return f'<span class="num {cls}{" pnl" if big else ""}">{v:+,.0f}$</span>' if big else f'<span class="num {cls}">{v:+,.2f}$</span>'

def cat_cls(c): return {"WIN": "win", "LOSS": "loss", "SCRATCH": "scratch"}.get(c, "unpriced")
MODE_HEB = {"live": "לייב", "shadow": "צל", "demo": "דמו"}

def day_summary(d):
    rs = [r for r in recs if r["day"] == d]
    def s(xs):
        p = [x["pnl"] for x in xs if x["pnl"] is not None]
        b = [x["books"] for x in xs if x["books"] is not None]
        return {"n": len(xs), "w": sum(1 for v in p if v > 0), "sum": sum(p) if p else 0.0, "books": sum(b) if b else 0.0,
                "nb": sum(1 for x in xs if x["mode"] == "live" and x["pnl_broker"] is not None)}
    return s([r for r in rs if r["mode"] == "live"]), s([r for r in rs if r["mode"] == "shadow"]), rs

def fact(l, v): return f'<div><div class="l">{l}</div><div class="v">{v}</div></div>'

def trade_card(r, d, open_=False):
    hl = f'<span class="badge {r["mode"]}">{MODE_HEB[r["mode"]]}</span>{r["time"]} · {HEB_DIR.get(r["dir"], r["dir"])} · {html.escape(r["pat"])}'
    sub = f'#{r["id"]} · {html.escape(r["reason_heb"])} · {r["mins"] or 0} דק׳'
    lbl = f'{d} {r["time"]} {html.escape(r["pat"])} {r["dir"]}'
    src_html = ""
    if r["mode"] == "live":
        if r["pnl_broker"] is not None:
            delta = (r["pnl_broker"] - r["books"]) if r["books"] is not None else None
            src_html = (fact("ברוקר (סיירה)", money(r["pnl_broker"]))
                        + fact("ספרים · Δ", (money(r["books"]) + (f' <span class="dim num">Δ{delta:+.2f}</span>' if delta is not None else "")) if r["books"] is not None else '<span class="dim">לא נרשם</span>'))
        else:
            src_html = fact("ברוקר (סיירה)", '<span class="dim">—</span>') + fact("ספרים", money(r["books"]))
    facts_html = ('<div class="facts">' + fact("כניסה", f'<span class="num">{r["entry"]:.2f}</span>')
                  + fact("יעד (מילוי לא נרשם)" if r.get("exit_is_target") else "יציאה", f'<span class="num">{r["exit"]:.2f}</span>' if r["exit"] is not None else "—")
                  + src_html
                  + fact("יעד (נק׳)", f'<span class="num">{r["t1p"]}</span>' if r["t1p"] is not None else "—")
                  + fact("MFE שעה", f'<span class="num">{r["mfe60"]}</span>' if r["mfe60"] is not None else "—")
                  + fact("MAE", f'<span class="num">{r["mae"]}</span>' if r["mae"] is not None else "—")
                  + fact("מקום בטווח", f'<span class="num">{int((r["pos"] or 0)*100)}%</span>' if r["pos"] is not None else "—")
                  + fact("בבטן", html.escape(r["zone"] or "—")) + fact("סוג-יום", html.escape(r["dt"] or "טרם")) + '</div>')
    lines = ((f'<div class="line dim"><span class="ic">⚠️</span><span>{html.escape(r["bnote"])}</span></div>' if r.get("bnote") else "")
             + f'<div class="line"><span class="ic">🧭</span><span>{html.escape(r["ctx"])}</span></div>'
             f'<div class="line"><span class="ic">{"✅" if r["cat"]=="WIN" else "❌" if r["cat"]=="LOSS" else "➖"}</span><b>{html.escape(r["why"])}</b></div>'
             + (f'<div class="line"><span class="ic">💡</span><span>{html.escape(r["more"])}</span></div>' if r["more"] else "")
             + (f'<div class="line dim"><span class="ic">📌</span><span>{html.escape(r["lesson"])}</span></div>' if r["lesson"] else ""))
    return (f'<div class="card {cat_cls(r["cat"])}{" open" if open_ else ""}" id="t{r["id"]}"><div class="row" onclick="tog(this.parentNode)">'
            f'<div class="grow"><div class="hl">{hl}</div><div class="dim">{sub}</div></div>{money(r["pnl"], True)}<span class="chev">‹</span></div>'
            f'<div class="body">{facts_html}{lines}'
            f'<div class="tags"><button onclick="tag({r["id"]},\'✓ נכונה\',\'{lbl}\')">✓ נכונה</button>'
            f'<button onclick="tag({r["id"]},\'✗ לא נכונה\',\'{lbl}\')">✗ לא נכונה</button>'
            f'<button onclick="tag({r["id"]},\'💬 הערה\',\'{lbl}\')">💬 הערה</button></div></div></div>')

def marks_of(rs):
    return [{"id": r["id"], "t": r["time"], "e": r["entry"], "x": r["exit"], "xt": r["exit_time"], "dir": r["dir"], "pnl": r["pnl"]} for r in rs]

# ── day pages ─────────────────────────────────────────────────────────────────
for k, d in enumerate(days):
    bars = by_day[d]; rth = [b for b in bars if b["rth"]]
    lv, sh, rs = day_summary(d)
    live_recs = [r for r in rs if r["mode"] == "live"]; shadow_recs = [r for r in rs if r["mode"] == "shadow"]; demo_recs = [r for r in rs if r["mode"] == "demo"]
    meta = dth.get(d, {}); dd = dt.date.fromisoformat(d)
    o, h_, l_, c_ = rth[0]["o"], max(b["h"] for b in rth), min(b["l"] for b in rth), rth[-1]["c"]
    prev_d = days[k - 1] if k > 0 else None; next_d = days[k + 1] if k + 1 < len(days) else None
    nav = ((f'<a class="ib" href="{prev_d}.html" title="יום קודם">‹</a>' if prev_d else '<span class="ib dis">‹</span>')
           + (f'<a class="ib" href="{next_d}.html" title="יום הבא">›</a>' if next_d else '<span class="ib dis">›</span>'))
    kpis = (f'<div class="kpis"><div class="kpi"><div class="l">לייב · ברוקר {lv["nb"]}/{lv["n"]}</div><div class="v">{money(lv["sum"], True)}</div><div class="s">{lv["w"]} ניצחונות · ספרים {lv["books"]:+.0f}$</div></div>'
            f'<div class="kpi"><div class="l">צל</div><div class="v">{money(sh["sum"], True)}</div><div class="s">{sh["n"]} עסקאות · {sh["w"]} ניצחונות</div></div>'
            f'<div class="kpi"><div class="l">סוג-יום</div><div class="v" style="font-size:16px">{meta.get("day_type") or "?"}</div><div class="s">פתיחה {meta.get("opening_type") or "?"}</div></div>'
            f'<div class="kpi"><div class="l">טווח</div><div class="v num" style="font-size:16px">{l_:.0f}–{h_:.0f}</div><div class="s num">{h_-l_:.1f} נק׳ · סגירה {c_-o:+.1f}</div></div></div>')
    bars_js = [[b["il"].strftime("%H:%M"), b["o"], b["h"], b["l"], b["c"], 1 if b["rth"] else 0] for b in bars]
    chart = (f'<h2>הנרות <span class="dim">{len(rth)} ברי-5-דק׳ · ▲▼ כניסה · ● יציאה</span></h2>'
             f'<div class="chips"><span class="chip on" id="cfit" onclick="setMode(\'fit\')">כל היום</span><span class="chip" id="c9" onclick="setMode(9)">זום</span><span class="chip" id="c14" onclick="setMode(14)">זום גדול</span>'
             f'<span class="chip" id="csh" onclick="toggleShadow()">+ צל ({len(shadow_recs)})</span></div>'
             f'<div class="chartwrap" id="cw"></div>')
    cards = ['<h2>העסקאות <span class="dim">לחיצה = פרטים, הסבר ותיוג</span></h2>']
    if not rs: cards.append('<div class="empty">אין עסקאות ביום זה</div>')
    cards += [trade_card(r, d, open_=(len(live_recs) <= 3)) for r in live_recs] + [trade_card(r, d) for r in demo_recs]
    if shadow_recs:
        cards.append(f'<div class="card"><div class="row" onclick="tog(this.parentNode)"><div class="grow"><div class="hl">צל — {len(shadow_recs)} עסקאות</div><div class="dim">{sh["w"]} ניצחונות · {money(sh["sum"])} · מה המפיקים ראו בלי לירות</div></div><span class="chev">‹</span></div><div class="body">'
                     + "".join(trade_card(r, d) for r in shadow_recs) + '</div></div>')
    js = ("<script>var BARS=" + json.dumps(bars_js) + ";var ML=" + json.dumps(marks_of(live_recs)) + ";var MS=" + json.dumps(marks_of(shadow_recs)) + ";"
          "var _mode='fit',_sh=false;function draw(){var el=document.getElementById('cw');el.innerHTML=candles(BARS,_sh?ML.concat(MS):ML,_mode,el.clientWidth);"
          "['fit',9,14].forEach(function(m){document.getElementById('c'+(m==='fit'?'fit':m)).classList.toggle('on',m===_mode);});document.getElementById('csh').classList.toggle('on',_sh);}"
          "function setMode(m){_mode=m;draw();}function toggleShadow(){_sh=!_sh;draw();}window.addEventListener('resize',draw);draw();</script>")
    with open(os.path.join(OUT, "days", f"{d}.html"), "w", encoding="utf-8") as fh:
        fh.write(shell(f"{HEB_WD[dd.weekday()]} {dd.strftime('%d.%m.%Y')}", kpis + chart + "".join(cards), js, prefix="../",
                       sub=f'{meta.get("day_type") or "?"} · לייב {lv["n"]} · {lv["sum"]:+.0f}$ · צל {sh["n"]}', active="days.html", right_btns=nav))

# ── days index ────────────────────────────────────────────────────────────────
dl = ['<h1>ימי-מסחר</h1><div class="dim">חדש למעלה. לחיצה פותחת נרות, עסקאות והסברים.</div>']
for d in reversed(days):
    lv, sh, rs = day_summary(d); dd = dt.date.fromisoformat(d); rth = [b for b in by_day[d] if b["rth"]]
    rng = max(b["h"] for b in rth) - min(b["l"] for b in rth); net = rth[-1]["c"] - rth[0]["o"]
    dl.append(f'<div class="card lnk"><a href="days/{d}.html"><div class="row"><div class="grow"><div class="hl">{HEB_WD1[dd.weekday()]} {dd.strftime("%d.%m")} · {dth.get(d,{}).get("day_type") or "?"}</div>'
              f'<div class="dim num">טווח {rng:.0f} · סגירה {net:+.0f} · לייב {lv["n"]} ({lv["w"]} ✓) · צל {sh["n"]}</div></div>{money(lv["sum"], True)}<span class="chev">‹</span></div></a></div>')
with open(os.path.join(OUT, "days.html"), "w", encoding="utf-8") as fh:
    fh.write(shell("ימי-מסחר", "".join(dl), active="days.html", sub=f"{len(days)} ימים אחרונים"))

# ── trades ledger ─────────────────────────────────────────────────────────────
cut7 = (NOW - dt.timedelta(days=8)).date().isoformat()
ledger = [r for r in recs if r["mode"] != "shadow" or r["day"] >= cut7]
slim = []
for r in ledger:
    x = {k: r[k] for k in ("id", "mode", "dir", "pat", "day", "time", "entry", "exit", "reason_heb", "pnl", "books", "src", "cat", "t1p", "mfe60", "mae", "pos", "zone", "mins", "dt")}
    if r["mode"] != "shadow": x.update(ctx=r["ctx"], why=r["why"], more=r["more"], lesson=r["lesson"])
    else: x.update(why=r["why"])
    slim.append(x)
pats = sorted({r["pat"] for r in ledger if r["pat"]})
body = ('<h1>כל העסקאות</h1><div class="dim">לייב מלא · צל 7 ימים. לחיצה על שורה = פרטים; על התאריך = הנרות.<br>'
        'לייב: המספר הוא <b>הרווח/הפסד של הברוקר (סיירה, נטו עמלות)</b>; הספרים שלנו בסוגריים. צל/דמו: תיאורטי.</div>'
        '<div class="chips" id="cm"><span class="chip on" data-v="live">לייב</span><span class="chip" data-v="demo">דמו</span><span class="chip" data-v="shadow">צל</span><span class="chip" data-v="">הכל</span></div>'
        '<div class="chips" id="cc"><span class="chip on" data-v="">כל התוצאות</span><span class="chip" data-v="WIN">✓ ניצחון</span><span class="chip" data-v="LOSS">✗ הפסד</span><span class="chip" data-v="SCRATCH">סקראץ׳</span><span class="chip" data-v="UNPRICED">לא-נכתבה</span></div>'
        '<div class="selrow"><select id="fDay"><option value="">כל הימים</option>' + "".join(f'<option value="{d}">{d[8:]}.{d[5:7]}</option>' for d in sorted(set(r["day"] for r in ledger), reverse=True)) + '</select>'
        '<select id="fDir"><option value="">כל הכיוונים</option><option value="LONG">לונג</option><option value="SHORT">שורט</option></select>'
        '<select id="fPat" style="grid-column:1/3"><option value="">כל התבניות</option>' + "".join(f'<option value="{html.escape(p)}">{html.escape(p)}</option>' for p in pats) + '</select></div>'
        '<div class="kpis" id="sum"></div><div id="tb"></div>')
ljs = ("<script>var T=" + json.dumps(slim, ensure_ascii=False) + ";var HD={LONG:'לונג',SHORT:'שורט'},MH={live:'לייב',shadow:'צל',demo:'דמו'};var F={m:'live',c:'',d:'',dr:'',p:''};"
       "function fmt(v){if(v===null||v===undefined)return '<span class=dim>—</span>';return '<span class=\"num '+(v>0?'pos':v<0?'neg':'')+'\">'+(v>0?'+':'')+v.toFixed(2)+'$</span>';}"
       "function chips(id,key){document.querySelectorAll('#'+id+' .chip').forEach(function(c){c.onclick=function(){document.querySelectorAll('#'+id+' .chip').forEach(function(x){x.classList.remove('on');});c.classList.add('on');F[key]=c.getAttribute('data-v');render();};});}"
       "chips('cm','m');chips('cc','c');['fDay','fDir','fPat'].forEach(function(i){document.getElementById(i).onchange=function(){F[{fDay:'d',fDir:'dr',fPat:'p'}[i]]=this.value;render();};});"
       "function render(){var rows=T.filter(function(r){return (!F.m||r.mode==F.m)&&(!F.d||r.day==F.d)&&(!F.dr||r.dir==F.dr)&&(!F.c||r.cat==F.c)&&(!F.p||r.pat==F.p);});"
       "var n=rows.length,w=rows.filter(function(r){return r.pnl>0;}).length,s=rows.reduce(function(a,r){return a+(r.pnl||0);},0);"
       "document.getElementById('sum').innerHTML='<div class=kpi><div class=l>עסקאות</div><div class=v>'+n+'</div></div><div class=kpi><div class=l>ניצחונות</div><div class=v>'+w+' <span class=dim style=\"font-size:13px\">('+(n?Math.round(100*w/n):0)+'%)</span></div></div><div class=kpi style=\"grid-column:1/3\"><div class=l>סה\"כ</div><div class=v>'+fmt(s)+'</div></div>';"
       "var h='',last='';rows.slice().reverse().forEach(function(r){if(r.day!=last){last=r.day;var dd=rows.filter(function(x){return x.day==r.day;});var ds=dd.reduce(function(a,x){return a+(x.pnl||0);},0);h+='<div class=dayhdr><a href=\"days/'+r.day+'.html\">📅 '+r.day.slice(8)+'.'+r.day.slice(5,7)+'</a><span>'+dd.length+' · '+fmt(ds)+'</span></div>';}"
       "h+='<div class=trow onclick=\"tg('+r.id+')\"><div class=grow><div class=a>'+r.time+' · '+(HD[r.dir]||r.dir)+' · '+r.pat+' <span class=\"badge '+r.mode+'\">'+MH[r.mode]+'</span></div><div class=b>#'+r.id+' · '+r.reason_heb+' · '+(r.mins||0)+' דק׳'+(r.t1p!=null?' · יעד '+r.t1p+' · MFE '+(r.mfe60==null?'—':r.mfe60):'')+(r.mode=='live'&&r.src=='ברוקר'&&r.books!=null?' · ספרים '+(r.books>0?'+':'')+r.books.toFixed(2):'')+(r.mode=='live'&&r.src!='ברוקר'?' · <span class=num>'+r.src+'</span>':'')+'</div></div>'+fmt(r.pnl)+'</div>';"
       "h+='<div class=detail id=\"d'+r.id+'\">'+(r.ctx?'<div>🧭 '+r.ctx+'</div>':'')+'<div><b>'+(r.why||'')+'</b></div>'+(r.more?'<div>💡 '+r.more+'</div>':'')+(r.lesson?'<div class=dim>📌 '+r.lesson+'</div>':'')+'<div style=\"margin-top:6px\"><a href=\"days/'+r.day+'.html#t'+r.id+'\">↗ הנרות, הפרטים והתיוג</a></div></div>';});"
       "document.getElementById('tb').innerHTML=h||'<div class=empty>אין עסקאות בפילטר הזה</div>';fixLinks(document.getElementById('tb'));}"
       "function tg(id){var e=document.getElementById('d'+id);e.style.display=e.style.display=='block'?'none':'block';}render();</script>")
with open(os.path.join(OUT, "trades.html"), "w", encoding="utf-8") as fh:
    fh.write(shell("כל העסקאות", body, ljs, active="trades.html", sub="לייב · דמו · צל"))

# ── missed trades ─────────────────────────────────────────────────────────────
mp = os.path.join(OUT, "data", "missed.json")
if os.path.exists(mp):
    M = json.load(open(mp, encoding="utf-8"))
    V_HEB = {"TOOK": ("✅ נלקחה בזמן", "ok"), "LATE": ("🕒 נלקחה מאוחר", "warn"), "OPPOSITE": ("❌ נכנסנו הפוך", "bad"), "MISSED": ("⭕ פוספסה", "bad"), "UNCATCHABLE": ("⚪ לא ניתנת-לתפיסה", "")}
    DEPTH = {"HIGH": "עומק גבוה", "NORMAL": "עומק רגיל", "LOW": "עומק נמוך"}
    FEAT = {"with_day": "עם כיוון-היום", "with_ext": "עם ההרחבה", "at_extreme": "על הקיצון", "near_ib_edge": "ליד קצה-IB", "near_prev_edge": "ליד ערך-אתמול",
            "trigger_ok": "בר-טריגר חזק", "structure_break": "שבירת-מבנה", "pullback_before": "אחרי פולבק", "range_ge_08atr": "טווח ≥0.8 ATR", "vol_trig": "ווליום ×1.3", "delta_with": "דלתא עם-הכיוון"}
    legs = M["legs"]; nm = sum(1 for r in legs if r["verdict"] == "MISSED"); nt = sum(1 for r in legs if r["verdict"] == "TOOK")
    mb = [f'<h1>מה פספסנו</h1><div class="dim">{len(M["sessions"])} סשנים · מהלכים ≥12 נק׳ ו-≥3 ברים · לפי נרות, ווליום ומיקום — לא תבניות</div>',
          f'<div class="kpis"><div class="kpi"><div class="l">מהלכים גדולים</div><div class="v">{len(legs)}</div></div><div class="kpi"><div class="l">פוספסו</div><div class="v neg">{nm}</div><div class="s num">{sum(r["pts"] for r in legs if r["verdict"]=="MISSED"):.0f} נק׳ שהיו ניתנות-לתפיסה</div></div>'
          f'<div class="kpi"><div class="l">נלקחו בזמן</div><div class="v pos">{nt}</div></div><div class="kpi"><div class="l">מאוחר / הפוך</div><div class="v">{sum(1 for r in legs if r["verdict"]=="LATE")} / {sum(1 for r in legs if r["verdict"]=="OPPOSITE")}</div></div></div>',
          '<h2>לפי סוג-יום × עומק <span class="dim">מה משותף לכניסות הנכונות</span></h2>']
    for g in M["groups"]:
        s = g["signature"] or {}
        pills = "".join(f'<span class="pill {"ok" if v >= 70 else ""}">{FEAT.get(k, k)} {v}%</span>' for k, v in s.items() if isinstance(v, int) and k != "n")
        strong = " + ".join(FEAT.get(k, k) for k in g["strong"]) if g["strong"] else "אין חתימה חזקה עדיין (N קטן) — מצטבר כל ערב"
        mb.append(f'<div class="card"><div class="row" onclick="tog(this.parentNode)"><div class="grow"><div class="hl">{html.escape(g["day_type"])} · {DEPTH[g["depth"]]}</div>'
                  f'<div class="dim">{g["legs"]} מהלכים · פוספסו {g["missed"]} ({g["missed_pts"]:.0f} נק׳) · נלקחו {g["took"]} · מאוחר {g["late"]} · הפוך {g["opposite"]}</div></div><span class="chev">‹</span></div>'
                  f'<div class="body"><div class="line"><span class="ic">🌿</span><b>ענף מוצע: {html.escape(strong)}</b></div><div>{pills}</div>'
                  f'<div class="dim" style="margin-top:6px">N={s.get("n",0)} כניסות · אזורים {html.escape(str(s.get("zones", {})))} · שלבים {html.escape(str(s.get("phases", {})))}</div></div></div>')
    mb.append('<h2>יום אחרי יום <span class="dim">חדש למעלה</span></h2>')
    for d in reversed(M["sessions"]):
        rs = [r for r in legs if r["day"] == d]
        if not rs: continue
        r0 = rs[0]; dd = dt.date.fromisoformat(d)
        items = []
        for r in rs:
            vh, vc = V_HEB.get(r["verdict"], (r["verdict"], ""))
            took = ("".join(f'<div class="dim">↳ #{t["id"]} {t["pat"]} {t["time"]} ({("%+.0f$" % t["pnl"]) if t["pnl"] is not None else "—"})</div>' for t in r["took"])) if r["took"] else ""
            ideal = ""
            if r["ideal"]:
                i = r["ideal"]
                ideal = ('<div class="facts" style="grid-template-columns:repeat(3,1fr)">' + fact("כניסה אידיאלית", f'{i["time"]} @<span class="num">{i["price"]:.2f}</span>') + fact("סטופ (נק׳)", f'<span class="num">{i["stop"]}</span>') + fact("היה נותן", f'<span class="num">{i["captured"]}</span> נק׳') + '</div>'
                         f'<div class="line"><span class="ic">🕯</span><span>{html.escape(i["desc"])}</span></div>'
                         f'<div class="line dim"><span class="ic">👁</span><span>מפיקי-צל שראו את זה (±10 דק׳): {html.escape(", ".join(i["seen_by"]) if i["seen_by"] else "אף אחד")}</span></div>')
            else:
                ideal = '<div class="line dim"><span class="ic">🕯</span><span>לא היה בר-אישור עם סטופ ≤1 ATR בחצי הראשון — המהלך נסע בלי לתת כניסה מחזיקה.</span></div>'
            items.append(f'<div class="card"><div class="row" onclick="tog(this.parentNode)"><div class="grow"><div class="hl"><span class="num">{r["start"]}→{r["end"]}</span> · {HEB_DIR[r["dir"]]} · <span class="num">{r["pts"]:.0f}</span> נק׳</div>'
                         f'<div class="dim"><span class="pill {vc}">{vh}</span> <span class="num">{r["from_px"]:.2f}→{r["to_px"]:.2f}</span></div></div><span class="chev">‹</span></div><div class="body">{took}{ideal}</div></div>')
        mb.append(f'<div class="dayhdr"><a href="days/{d}.html">📅 {HEB_WD1[dd.weekday()]} {dd.strftime("%d.%m")} · {html.escape(r0["day_type"])} · {DEPTH[r0["depth"]]}</a><span>{len(rs)} מהלכים</span></div>' + "".join(items))
    with open(os.path.join(OUT, "missed.html"), "w", encoding="utf-8") as fh:
        fh.write(shell("מה פספסנו", "".join(mb), active="missed.html", sub=f'{len(M["sessions"])} סשנים · {nm} פספוסים'))

# ── what works (from scripts/what_works_study.py) ─────────────────────────────
wp = os.path.join(OUT, "data", "whatworks.json")
if os.path.exists(wp):
    W = json.load(open(wp, encoding="utf-8"))
    def cell(x, key, win=True):
        v = x[key]["sum"]; cls = "pos" if v > 0 else "neg" if v < 0 else ""
        return f'<span class="num {cls}">{v:+,}$</span>' + (f' <span class="dim">({x[key]["win"]}%)</span>' if win else "")
    wb = [f'<h1>מה עובד</h1><div class="dim">{W["n"]:,} כניסות (לייב+צל) מאז {W["since"][8:]}.{W["since"][5:7]} · אותו מודל-הערכה לכולן · חדש: {W["generated"][:16]}</div>',
          '<div class="card" style="font-size:14px"><b>איך לקרוא:</b> <b>ספרים</b> = מה שנרשם בפועל · <b>T1 קבוע</b> = חוזה אחד, סטופ 1×ATR, יעד 1.5×ATR · <b>סולם-2</b> = שני חוזים, T1 ו-T2=2.5×ATR · <b>טרייל</b> = סטופ רודף 1×ATR. אחוז = ניצחונות. N קטן מ-30 = רמז, לא הכרעה.</div>']
    for tb in W["tables"]:
        wb.append(f'<h2>{html.escape(tb["title"])}</h2>')
        if not tb["rows"]: wb.append('<div class="empty">אין מספיק נתונים</div>'); continue
        wb.append('<div style="overflow-x:auto"><table class="plain"><tr><th>קבוצה</th><th>N</th><th>ספרים</th><th>T1 קבוע</th><th>סולם-2</th><th>טרייל</th></tr>')
        for r in tb["rows"]:
            wb.append(f'<tr><td>{html.escape(r["name"])}</td><td class="num">{r["n"]}</td><td>{cell(r,"books")}</td><td>{cell(r,"m1")}</td><td>{cell(r,"m2",False)}</td><td>{cell(r,"trail")}</td></tr>')
        wb.append('</table></div>')
    with open(os.path.join(OUT, "whatworks.html"), "w", encoding="utf-8") as fh:
        fh.write(shell("מה עובד", "".join(wb), sub="כניסות · מיקום · יציאות — במספרים"))

# ── lessons: vertical timeline (default) + Gantt (toggle) ─────────────────────
LESSONS = json.load(open(os.path.join(ROOT, "docs", "plans", "LESSONS_TIMELINE.json"), encoding="utf-8"))
tdays = [x["day"] for x in LESSONS["days"]][::-1]
live_by_day = {}
for r in recs:
    if r["mode"] == "live" and r["pnl"] is not None:
        live_by_day.setdefault(r["day"], []).append(r["pnl"])
K_HEB = {"a": "ענף/גרסה", "b": "מדידה", "c": "באג תוקן", "d": "תקרית", "e": "פסיקה"}
gl = ['<h1>לקחים וענפים</h1><div class="dim">מה למדנו בכל יום-מסחר, ואיזה ענף/מדידה/פסיקה נולדו ממנו. חדש למעלה.</div>',
      '<div class="chips"><span class="chip on" id="vt" onclick="viewL(\'t\')">ציר-זמן</span><span class="chip" id="vg" onclick="viewL(\'g\')">טבלה (גאנט)</span></div>',
      '<div class="legend"><span class="g a">ענף/גרסה</span><span class="g b">מדידה</span><span class="g c">באג תוקן</span><span class="g d">תקרית</span><span class="g e">פסיקה</span></div>',
      '<div class="tl" id="tl">']
for x in LESSONS["days"][::-1]:
    d = x["day"]; dd = dt.date.fromisoformat(d)
    items = [(th["name"], it) for th in LESSONS["threads"] for it in th["items"] if it["day"] == d]
    chips = "".join(f'<span class="g {it.get("k","b")}" title="{html.escape(th)}">{html.escape(it["t"])}</span>' for th, it in items)
    pnl = f' · לייב {money(sum(live_by_day[d]), True)}' if d in live_by_day else ""
    gl.append(f'<div class="ev"><div class="card"><div class="d">{HEB_WD1[dd.weekday()]} {dd.strftime("%d.%m")}{pnl}' + (f' <a href="days/{d}.html">↗ נרות</a>' if d in days else "") + f'</div><div style="margin:6px 0">{html.escape(x["lesson"])}</div><div>{chips}</div></div></div>')
gl.append('</div><div class="gantt" id="gt"><table><thead><tr><th class="lbl"></th>' + "".join(f'<th>{d[8:]}.{d[5:7]}</th>' for d in tdays) + '</tr></thead><tbody>')
gl.append('<tr><td class="lbl">לייב $</td>' + "".join((f'<td class="num"><span class="{"pos" if sum(live_by_day[d])>0 else "neg"}">{sum(live_by_day[d]):+.0f}</span></td>' if d in live_by_day else '<td class="dim">—</td>') for d in tdays) + '</tr>')
for th in LESSONS["threads"]:
    cells = ['<td>' + "".join(f'<span class="g {it.get("k","b")}">{html.escape(it["t"])}</span>' for it in th["items"] if it["day"] == d) + '</td>' for d in tdays]
    gl.append(f'<tr><td class="lbl">{html.escape(th["name"])}</td>' + "".join(cells) + '</tr>')
gl.append('</tbody></table></div>')
gjs = "<script>function viewL(v){document.getElementById('tl').style.display=v==='t'?'block':'none';document.getElementById('gt').classList.toggle('show',v==='g');document.getElementById('vt').classList.toggle('on',v==='t');document.getElementById('vg').classList.toggle('on',v==='g');}</script>"
with open(os.path.join(OUT, "lessons.html"), "w", encoding="utf-8") as fh:
    fh.write(shell("לקחים וענפים", "".join(gl), gjs, active="lessons.html", sub="יום אחרי יום"))

# ── tree identity page ────────────────────────────────────────────────────────
tp = os.path.join(ROOT, "docs", "spec_authority", "DALTON_TREE_IDENTITY.md")
if os.path.exists(tp):
    import re
    md = open(tp, encoding="utf-8").read()
    def md2html(md):
        out, in_tbl, first = [], False, False
        for line in md.split("\n"):
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells): continue
                if not in_tbl: out.append('<div style="overflow-x:auto"><table class="plain">'); in_tbl = True; first = True
                tag_ = "th" if first else "td"; first = False
                out.append("<tr>" + "".join(f"<{tag_}>{c}</{tag_}>" for c in cells) + "</tr>")
                continue
            if in_tbl: out.append("</table></div>"); in_tbl = False
            if line.startswith("# "): out.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "): out.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("- "): out.append(f"<div class='card' style='padding:8px 12px'>{line[2:]}</div>")
            elif re.match(r"^\d+\. ", line): out.append(f"<div class='card' style='padding:8px 12px'>{line}</div>")
            elif line.strip(): out.append(f"<p>{line}</p>")
        if in_tbl: out.append("</table></div>")
        h = "\n".join(out)
        h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h); h = re.sub(r"`(.+?)`", r"<code>\1</code>", h)
        return h
    with open(os.path.join(OUT, "tree.html"), "w", encoding="utf-8") as fh:
        fh.write(shell("עץ-דלתון", md2html(md), sub="תעודת-זהות וסקירה"))

# ── day review — the daily exam (Michael 23.09: "מבחן על כל ימי המסחר … כלי עבודה יומי") ──
rvp = os.path.join(OUT, "data", "review.json")
if os.path.exists(rvp):
    RV = json.load(open(rvp, encoding="utf-8"))
    RV_HEB = {"TOOK": ("✅ נלקחה בזמן", "ok"), "LATE": ("🕒 נלקחה מאוחר", "warn"), "OPPOSITE": ("❌ נכנסנו הפוך", "bad"), "MISSED": ("⭕ פוספסה", "bad"), "UNCATCHABLE": ("⚪ בלי בר-אישור", "")}
    KIND_HEB = {"relax_gate": "שער לבדיקה", "slot_priority": "עדיפות-סלוט", "producer_not_live": "מפיק צל-בלבד", "shadow_only": "צל בלי שער", "no_producer": "אף מפיק לא ראה"}
    ZONE_R = {"ABOVE_VA": "מעל הבטן", "BELOW_VA": "מתחת לבטן", "IN_VA": "בתוך הבטן", "AT_POC": "על ה-POC", "UNKNOWN": "?"}
    rdays = sorted(RV.get("days", {}), reverse=True)
    rb = ['<h1>סקירת-יום</h1><div class="dim">שלושה שלבים לכל יום: (1) ראייה מלאה — איפה עסקה הייתה צריכה לצאת ואיך ממקסמים · (2) מה הגייטוויי ראה, מי נחסם ולמה · (3) מה לשנות כדי שזה ייתפס. רץ אחרי כל יום-מסחר.</div>',
          '<div class="chips" id="rdays">' + "".join(f'<span class="chip{" on" if k == 0 else ""}" data-d="{d}">{d[8:]}.{d[5:7]}</span>' for k, d in enumerate(rdays)) + '</div>']
    for k, d in enumerate(rdays):
        R = RV["days"][d]; dd = dt.date.fromisoformat(d)
        sec = [f'<div class="rday" id="r{d}" style="display:{"block" if k == 0 else "none"}">',
               f'<h2>{HEB_WD[dd.weekday()]} {dd.strftime("%d.%m")} <span class="dim">{R["day_type"]} · פתיחה {R["opening"]} · טווח {R["range"]:.0f} · סגירה {R["net"]:+.1f}</span>' + (f' <a href="days/{d}.html">↗ נרות</a>' if d in days else "") + '</h2>',
               f'<div class="kpis"><div class="kpi"><div class="l">מהלכים ששווה לתפוס</div><div class="v">{R["n_legs"]}</div><div class="s num">{R["available_pts"]:.0f} נק׳</div></div>'
               f'<div class="kpi"><div class="l">פוספסו</div><div class="v neg">{R["missed"]}</div><div class="s num">{R["missed_pts"]:.0f} נק׳ · הפוך {R["opposite"]} · מאוחר {R["late"]}</div></div>'
               f'<div class="kpi"><div class="l">נלקחו בזמן</div><div class="v pos">{R["took"]}</div><div class="s">לייב {R["live_n"]} · {money(R["live_pnl"])}</div></div>'
               f'<div class="kpi"><div class="l">הגייטוויי ראה</div><div class="v">{R["decisions"]}</div><div class="s">נחסמו {R["blocked"]} · צל-בלבד {R.get("shadow_only", 0)} · נורו {R.get("fired", 0)}</div></div></div>']
        if R.get("gates"):
            sec.append('<div class="dim" style="margin:-4px 0 8px">שערים: ' + " · ".join(f'{html.escape(k.split(":")[-1])} {v}' for k, v in R["gates"].items()) + '</div>')
        for l in R["legs"]:
            lbl, cls = RV_HEB.get(l["verdict"], ("?", ""))
            hl = f'{l["start"]}→{l["end"]} · {HEB_DIR.get(l["dir"], l["dir"])} · <span class="num">{l["pts"]:.1f}</span> נק׳'
            body = []
            if l["ideal"]:
                i = l["ideal"]; m = l["maxim"] or {}
                body.append(f'<div class="line"><span class="ic">🎯</span><span><b>כניסה-אידיאלית {i["time"]} @{i["price"]:.2f}</b> (סטופ {i["stop"]} · נתן {i["captured"]} נק׳): {html.escape(i["desc"])}</span></div>')
                body.append(f'<div class="line"><span class="ic">📐</span><span>מיקסום: יעד-קבוע <b>{m.get("t1")}</b> · טריילינג <b>{m.get("trail")}</b> · מקסימום {m.get("max")} נק׳</span></div>')
            else:
                body.append('<div class="line dim"><span class="ic">🎯</span><span>אין בר-אישור עם סטופ ≤1 ATR בחצי הראשון — המהלך נסע בלי לתת כניסה.</span></div>')
            s = l["seen"]; seen_txt = []
            if s["passed_fired"]: seen_txt.append("עבר ונורה: " + ", ".join(f'{r["pat"]} {r["time"]}' for r in s["passed_fired"]))
            if s["passed_not_fired"]: seen_txt.append("עבר ולא נורה: " + ", ".join(f'{r["pat"]} {r["time"]} ← {r["gate_heb"]}' for r in s["passed_not_fired"]))
            if s.get("shadow_only"): seen_txt.append("עבר, מפיק-צל-בלבד: " + ", ".join(f'{r["pat"]} {r["time"]}' for r in s["shadow_only"]))
            if s["blocked"]:
                byg = collections.defaultdict(list)
                for r in s["blocked"]: byg[r["gate_heb"]].append(f'{r["pat"]} {r["time"]}')
                seen_txt.append("נחסם: " + " · ".join(f'{g} ← {", ".join(v)}' for g, v in byg.items()))
            if s["opposite_passed"]: seen_txt.append("הפוך נורה: " + ", ".join(f'{r["pat"]} {r["time"]}' for r in s["opposite_passed"]))
            body.append(f'<div class="line"><span class="ic">👁</span><span><b>מה המערכת ראתה:</b> {html.escape(" | ".join(seen_txt)) if seen_txt else "<b>אף אחד לא ראה.</b>"}</span></div>')
            if l["took"]: body.append('<div class="line"><span class="ic">📒</span><span>לייב במהלך: ' + ", ".join(f'#{t["id"]} {t["pat"]} {t["time"]} ({money(t["pnl"]) if t["pnl"] is not None else "—"})' for t in l["took"]) + '</span></div>')
            for c in l["change"]: body.append(f'<div class="line"><span class="ic">🔧</span><span>{html.escape(c)}</span></div>')
            sec.append(f'<div class="card{" open" if l["verdict"] in ("MISSED", "OPPOSITE") else ""}"><div class="row" onclick="tog(this.parentNode)"><div class="grow"><div class="hl">{hl}</div><div class="dim"><span class="pill {cls}">{lbl}</span></div></div><span class="chev">‹</span></div><div class="body">{"".join(body)}</div></div>')
        if R["candidates"]:
            sec.append('<h2>מועמדים לענפים מהיום</h2>' + "".join(f'<div class="card" style="padding:8px 12px"><b>{KIND_HEB.get(c["kind"], c["kind"])}</b> {html.escape(c.get("gate","").split(":")[-1])} · שלב {c["phase"]} · {c["day_type"]} · {ZONE_R.get(c["zone"], c["zone"])} · {HEB_DIR.get(c["dir"], c["dir"])} · {c["start"]} ({c["pts"]} נק׳)' + (f' · {", ".join(c["pats"])}' if c.get("pats") else "") + '</div>' for c in R["candidates"]))
        sec.append('</div>')
        rb.append("".join(sec))
    tbl = RV.get("candidates", [])
    if tbl:
        rb.append('<h2>רשימת-הענפים המצטברת <span class="dim">מועמד שחוזר ב-≥3 ימים עולה לריפליי</span></h2><div style="overflow-x:auto"><table class="plain"><tr><th>סוג</th><th>שער</th><th>שלב</th><th>סוג-יום</th><th>אזור</th><th>כיוון</th><th>ימים</th><th>נק׳</th></tr>'
                  + "".join(f'<tr><td>{KIND_HEB.get(r["kind"], r["kind"])}</td><td>{html.escape(r["gate"].split(":")[-1])}</td><td>{r["phase"]}</td><td>{r["day_type"]}</td><td>{ZONE_R.get(r["zone"], r["zone"])}</td><td>{HEB_DIR.get(r["dir"], r["dir"])}</td><td class="num"><b>{len(r["days"])}</b> ({r["n"]})</td><td class="num">{r["pts"]:.0f}</td></tr>' for r in tbl[:15]) + '</table></div>')
    rb.append('<div class="card" style="padding:10px 12px"><b>איך זה הופך לענף:</b> מועמד שחוזר ב-≥3 ימים (או ≥15 מקרים בהרנס) ← שורה ב-v2 של עץ-דלתון בצל ← ריפליי על 56–85 סשנים עם מודל-ההערכה הקבוע ← אם המספר טוב יותר: פסיקה אחת של מייקל, דגל עם measured, גרסת-עץ חדשה. תקרית = מקרה-ריפליי, לא דגל.</div>')
    rjs = "<script>document.querySelectorAll('#rdays .chip').forEach(function(c){c.onclick=function(){document.querySelectorAll('#rdays .chip').forEach(function(x){x.classList.remove('on');});c.classList.add('on');document.querySelectorAll('.rday').forEach(function(e){e.style.display='none';});document.getElementById('r'+c.getAttribute('data-d')).style.display='block';};});</script>"
    with open(os.path.join(OUT, "review.html"), "w", encoding="utf-8") as fh:
        fh.write(shell("סקירת-יום", "".join(rb), rjs, active="review.html", sub=f"{len(rdays)} ימים · המבחן היומי"))

# ── journal defects (Michael 23.09: "אני רוצה רשימה של כל הליקויים") ─────────
dfp = os.path.join(ROOT, "docs", "plans", "JOURNAL_DEFECTS.json")
if os.path.exists(dfp):
    DF = json.load(open(dfp, encoding="utf-8"))
    ST = {"done": ("✅ תוקן ואומת", "ok"), "code": ("🔧 תוקן בקוד — נכנס בריסטארט", "warn"), "open": ("⏳ פתוח", "bad")}
    nd = sum(1 for i in DF["items"] if i["status"] == "done"); nc = sum(1 for i in DF["items"] if i["status"] == "code"); no = sum(1 for i in DF["items"] if i["status"] == "open")
    tt = DF.get("totals", {})
    dl_ = [f'<h1>ליקויי יומן-המסחר</h1><div class="dim">עודכן {DF["updated"]} · {html.escape(DF["truth"])}</div>',
           f'<div class="kpis"><div class="kpi"><div class="l">תוקן ואומת</div><div class="v pos">{nd}</div></div><div class="kpi"><div class="l">בקוד, ממתין לריסטארט</div><div class="v" style="color:var(--am)">{nc}</div></div>'
           f'<div class="kpi"><div class="l">פתוח</div><div class="v neg">{no}</div></div><div class="kpi"><div class="l">21.09 · 22.09</div><div class="v num" style="font-size:15px">ספרים {tt.get("2026-09-21",{}).get("books",0):+.0f} / {tt.get("2026-09-22",{}).get("books",0):+.0f}</div><div class="s num">ברוקר {tt.get("2026-09-21",{}).get("broker",0):+.2f} / {tt.get("2026-09-22",{}).get("broker",0):+.2f}</div></div></div>']
    if tt.get("_note"): dl_.append(f'<div class="card" style="padding:10px 12px"><b>{html.escape(tt["_note"])}</b></div>')
    for i in DF["items"]:
        lbl, cls = ST.get(i["status"], ("?", ""))
        dl_.append(f'<div class="card{" open" if i["status"] != "done" else ""}"><div class="row" onclick="tog(this.parentNode)"><div class="grow"><div class="hl">{i["id"]}. {html.escape(i["title"])}</div>'
                   f'<div class="dim"><span class="pill {cls}">{lbl}</span>' + (f' <span class="pill">{html.escape(i["owner"])}</span>' if i.get("owner") else "") + '</div></div><span class="chev">‹</span></div>'
                   f'<div class="body"><div class="line"><span class="ic">👁</span><span><b>מה נראה:</b> {html.escape(i["symptom"])}</span></div>'
                   f'<div class="line"><span class="ic">🔍</span><span><b>שורש:</b> {html.escape(i["root"])}</span></div>'
                   f'<div class="line"><span class="ic">🩹</span><span><b>תיקון:</b> {html.escape(i["fix"])}</span></div>'
                   + (f'<div class="line dim"><span class="ic">🧾</span><span>{html.escape(i["evidence"])}</span></div>' if i.get("evidence") else "") + '</div></div>')
    with open(os.path.join(OUT, "defects.html"), "w", encoding="utf-8") as fh:
        fh.write(shell("ליקויי-היומן", "".join(dl_), active="defects.html", sub=f"{nd} תוקנו · {nc} בקוד · {no} פתוחים"))

# ── home ──────────────────────────────────────────────────────────────────────
last = days[-1] if days else None
ib = []
if last:
    lv, sh, rs = day_summary(last); dd = dt.date.fromisoformat(last)
    week = [d for d in days if d >= (dt.date.fromisoformat(last) - dt.timedelta(days=6)).isoformat()]
    wsum = sum(sum(live_by_day.get(d, [])) for d in week); wn = sum(len(live_by_day.get(d, [])) for d in week); ww = sum(1 for d in week for v in live_by_day.get(d, []) if v > 0)
    ib.append(f'<h2>הסשן האחרון <span class="dim">{HEB_WD[dd.weekday()]} {dd.strftime("%d.%m")}</span></h2>'
              f'<div class="kpis"><div class="kpi"><div class="l">לייב (ברוקר)</div><div class="v">{money(lv["sum"], True)}</div><div class="s">{lv["n"]} עסקאות · {lv["w"]} ניצחונות · ספרים {lv["books"]:+.0f}$</div></div>'
              f'<div class="kpi"><div class="l">סוג-יום</div><div class="v" style="font-size:16px">{dth.get(last,{}).get("day_type") or "?"}</div><div class="s">צל {sh["n"]} · {money(sh["sum"])}</div></div>'
              f'<div class="kpi"><div class="l">השבוע (לייב, ברוקר)</div><div class="v">{money(wsum, True)}</div><div class="s">{wn} עסקאות · {ww} ניצחונות</div></div>'
              f'<div class="kpi"><div class="l">חוזה</div><div class="v">1</div><div class="s">פסיקת 18.09</div></div></div>'
              f'<div class="card lnk"><a href="days/{last}.html"><div class="row"><div class="grow"><div class="hl">📅 הנרות והעסקאות של {dd.strftime("%d.%m")}</div><div class="dim">הסבר לכל עסקה + תיוג ✓/✗</div></div><span class="chev">‹</span></div></a></div>')
ib.append('<h2>מקומות</h2>')
for h, ic, n, s, _ in MENU[1:]:
    ib.append(f'<div class="card lnk"><a href="{h}"><div class="row"><div class="grow"><div class="hl">{ic} {html.escape(n)}</div><div class="dim">{html.escape(s)}</div></div><span class="chev">‹</span></div></a></div>')
ib.append(f'<div class="dim" style="margin-top:14px">נוצר {NOW.strftime("%d.%m %H:%M")} · מתרענן בכל EOD · תיוגים נשמרים כנתונים</div>')
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(shell("MEMS26", "".join(ib), active="index.html", sub="תיעוד למסחר"))
print(f"pages: index, days ({len(days)}), trades ({len(slim)} rows), missed, lessons, tree → {OUT}")
