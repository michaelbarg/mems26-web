#!/usr/bin/env python3
"""awareness_score — ציון-המודעות היומי (T-159). READ-ONLY, מדד ולא שער.

**למה הקובץ הזה קיים:** ציון-המודעות חושב שלוש פעמים (25/26/27.08) מתוך
`/tmp/awareness_fix.py` — קובץ-זרוק שנמחק. מאז 3 מ-4 הצירים בלתי-מדידים,
וכל דוח יומי נאלץ לכתוב "לא-נמדד, לא הומצא מספר". זו אותה מחלקה שהרגה את
`SOURCE_OF_TRUTH.md`: מדד-חובה שאינו סקריפט מחויב-גיט אינו מדד.

**השאלה שהציון עונה עליה:** בכל בר-RTH — האם המערכת *ידעה* את מה שהיתה
צריכה לדעת? ארבעה צירים, מכנה = ברי-ה-RTH בפועל (78 ביום מלא):

  יום      — האם ה-IB של *הסשן הזה* היה ידוע בפתיחת-הבר (צילום-TPO מאותו
             סשן, לפני פתיחת-הבר, שזמנו ≥ סגירת-IB 10:30 ET).
  רמות     — האם POC/VAH/VAL פעילים היו ידועים בפתיחת-הבר (כל צילום שקדם
             לבר, כולל גרירה מסשן קודם — רמה נשארת רמה גם למחרת).
  מועמדים  — מתוך *אירועי-ההזדמנות* של היום (בר שנגע ב-VAH/VAL): בכמה מהם
             הליגר רשם `DETECTED`. **המכנה כאן אינו 78** אלא מספר הנגיעות.
  החלטות   — בכמה ברי-RTH הליגר רשם לפחות אירוע-החלטה אחד
             (DETECTED / EMIT_DECISION / GATE_DECISION / ROUTED).

**כיול מול התקדים (Rule 2 — לאמת לפני שסומכים).** ההגדרות לעיל אינן
המצאה: הן שוחזרו עד-שחזור-מדויק מול הרשומה המאומתת של 25.08
(`STATUS_BOARD.md`: "יום 65/78 · רמות 78/78 · מועמדים 5/10"):
  · רמות → 78/78 ✅ (מדויק)
  · יום   → 65/78 ✅ (מדויק — ה-13 החסרים הם 09:30-10:30 ET, לפני שה-IB נסגר)
  · מועמדים → 10 נגיעות-VA ✅, והחמש שהתקדים מנה כ*מוחמצות*
    (10:00 · 12:35 · 12:40 · 15:00 · 15:55 ET) כולן בתוך העשר.
  · החלטות → **לא ניתן לכייל**: אין ארכיון-ליגר ל-25.08 (הליגר החי מתאפס
    יומית; `data_handoff/` מתחיל 13.08 ואז 06.09). המספר מחושב משורות
    אמיתיות לפי ההגדרה שלמעלה, אבל ההגדרה עצמה לא הוצלבה מול התקדים.

**שתי מלכודות שהקוד מכיר בשמן:**

1. **T-100 — הסטת ‎−3ש' ב-`v9_tpo_history`.** הכותב כתב naive-UTC לעמודת
   `timestamptz` תחת `TZ=Asia/Jerusalem` ⇒ ה-ts מוסט ‎−3ש' מהאמת. **אבל
   התיקון אינו "תמיד להוסיף 3 שעות"**: המדידה מראה שההסטה חיה עד 28.08
   וכבויה מ-31.08 (`created_at - ts`: ‎03:00:05 מול ‎00:00:05). לכן הסקריפט
   **מודד את ההסטה לכל שורה** מול `created_at` (ברירת-מחדל `now()`, ולכן
   תמיד רגע-אמת) ומעגל לשעה שלמה. הוספה עיוורת של 3 שעות היתה הורסת כל יום
   שאחרי 31.08 — זה בדיוק הטיפוס של שגיאה ש-Rule 1 אוסר.

2. **T-420 — "שורות בלי `ts`".** ב-18.09, ‎108 מ-202 שורות-הליגר אינן נושאות
   `ts`. **הן כן נושאות חותמת** — `signal_bar_ts` + `observed_at` (משפחת
   `candidate_ledger.v1`, DETECTED/EMIT_DECISION). פרסר שקורא `ts` בלבד מפיל
   אותן בשקט ומדווח 47% מהנתונים כאילו הם הכל. לכן: קוראים לפי סדר
   `signal_bar_ts` → `ts` → `observed_at`, ומדפיסים מפקד-מכנה מלא
   (`parsed + json-bad + no-usable-ts == סך-השורות`). שורה שבאמת אין בה אף
   שדה-זמן נספרת בנפרד, ואם בגללה אי-אפשר לסגור ציר — הציר מודפס
   `NOT-MEASURABLE (T-420)` עם המונה החלקי לידו. לעולם לא משלימים ts
   מ-`trade_id`, מסדר-השורות או משם-הקובץ.

הרצה:
    python3 scripts/awareness_score.py --day 2026-09-18
    python3 scripts/awareness_score.py --day 2026-09-18 --json

קוד-יציאה: 0 תמיד (מדד, לא שער). 2 רק כאשר ליום המבוקש אין נתונים כלל.
DB: קריאה-בלבד (`set_session(readonly=True)`). אפס כתיבה, אפס נגיעה בדגלים.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import namedtuple
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RTH_START = time(9, 30)      # ET
RTH_END = time(16, 0)        # ET (בלעדי)
IB_END = time(10, 30)        # ET — סגירת ה-Initial Balance (שעה ראשונה)
BAR_MINUTES = 5
THRESHOLD = 0.80             # ≥80% ⇒ ✅, אחרת 🔴
CAND_WINDOW_BARS = 1         # DETECTED נספר לנגיעה אם נרשם על אותו בר או הבא
LEDGER_EVENTS = ("DETECTED", "EMIT_DECISION", "GATE_DECISION", "ROUTED")
LIVE_LEDGER = os.path.expanduser("~/SierraChart_Data/v9_export/gateway_decisions.jsonl")

Bar = namedtuple("Bar", "ts open high low close")
Snap = namedtuple("Snap", "ts poc vah val ib_high ib_low skew_h")
Event = namedtuple("Event", "bar_ts event_type source_field")


# ─────────────────────────── טהור (בר-בדיקה בלי DB) ───────────────────────────

def normalize_tpo(rows):
    """מתקן את T-100 לכל שורה לפי ההסטה הנמדדת מול created_at.

    rows: iterable של (ts, created_at, poc, vah, val, ib_high, ib_low) —
    ts/created_at tz-aware. מחזיר [Snap] ממוין לפי הזמן המתוקן.

    ההסטה נמדדת ולא מונחת: `round((created_at - ts) / 1h)`. הכותב מצלם
    ~5 שניות אחרי הגבול, ולכן יום תקין נותן 0, ויום נגוע-T-100 נותן 3.
    (הכותב לפעמים מאחר בדקות — העיגול לשעה שלמה עומד בזה.)
    """
    out = []
    for ts, created_at, poc, vah, val, ib_high, ib_low in rows:
        skew = 0
        if created_at is not None:
            skew = int(round((created_at - ts).total_seconds() / 3600.0))
            if skew < 0:
                skew = 0            # צילום שנכתב לפני זמנו — לא מתקנים אחורה
        out.append(Snap(ts + timedelta(hours=skew), poc, vah, val, ib_high, ib_low, skew))
    out.sort(key=lambda s: s.ts)
    return out


def active_snapshot(snaps, t, inclusive=False, not_before=None):
    """הצילום הפעיל בזמן t. `inclusive` ⇒ מותר צילום שזמנו בדיוק t.

    למה שתי הצורות: הצירים יום/רמות שואלים "מה היה ידוע כשהבר *נפתח*"
    (`<`), בעוד סריקת-הנגיעות שואלת "איזה VA היה חי *בזמן שהבר נסחר*" —
    וזה כולל את הצילום שנכתב 5 שניות לתוך הבר (`<=`). שתי הצורות יחד הן
    מה שמשחזר את התקדים (65/78 · 78/78 · 10 נגיעות) — לא בחירה אסתטית.
    """
    best = None
    for s in snaps:
        if not_before is not None and s.ts < not_before:
            continue
        if (s.ts <= t) if inclusive else (s.ts < t):
            if best is None or s.ts > best.ts:
                best = s
    return best


def floor_bar(t):
    """מעגל זמן כלפי מטה לגבול בר-5-דקות."""
    return t.replace(minute=(t.minute // BAR_MINUTES) * BAR_MINUTES, second=0, microsecond=0)


def parse_ledger_lines(lines):
    """JSONL → ([Event], census). census סוגר את המכנה (מלכודת T-420).

    סדר-העדיפות של שדה-הזמן: `signal_bar_ts` (הבר עצמו — הכי מדויק) →
    `ts` (שורות GATE_DECISION/ROUTED) → `observed_at`. שורה בלי אף אחד
    מהשלושה נספרת ב-`no_usable_ts` ואינה מומצאת.
    """
    events = []
    # `parsed` = שורות שהניבו אירוע *עם* חותמת שמישה, ולכן מתקיים תמיד
    # parsed + json_bad + no_usable_ts == lines. "parsed" לבדו אינו מכנה.
    census = {"lines": 0, "parsed": 0, "json_bad": 0, "no_usable_ts": 0,
              "unknown_event": 0, "by_event": {}}
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        census["lines"] += 1
        try:
            rec = json.loads(raw)
        except Exception:
            census["json_bad"] += 1
            continue
        et = rec.get("event_type")
        census["by_event"][et] = census["by_event"].get(et, 0) + 1
        if et not in LEDGER_EVENTS:
            census["unknown_event"] += 1
        stamp = field = None
        for key in ("signal_bar_ts", "ts", "observed_at"):
            val = rec.get(key)
            if val:
                stamp, field = val, key
                break
        if stamp is None:
            census["no_usable_ts"] += 1
            continue
        try:
            dtv = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        except Exception:
            census["no_usable_ts"] += 1
            continue
        if dtv.tzinfo is None:                     # חותמת נאיבית = UTC לפי הכותב
            dtv = dtv.replace(tzinfo=ZoneInfo("UTC"))
        census["parsed"] += 1
        events.append(Event(floor_bar(dtv.astimezone(ET)), et, field))
    return events, census


def axis(n, d, note="", measurable=True, reason=""):
    """ציר אחד. לא-מדיד ⇒ n=None — לעולם לא 0 ולא ערך מומצא (Rule 1)."""
    if not measurable or d in (None, 0):
        return {"n": None, "d": d, "pct": None, "ok": None,
                "note": note, "not_measurable": reason or "אין נתון"}
    pct = 100.0 * n / d
    return {"n": n, "d": d, "pct": pct, "ok": pct >= THRESHOLD * 100,
            "note": note, "not_measurable": None}


def score_day(day, bars, snaps, events, census, tpo_available=True, ledger_available=True):
    """מחשב את ארבעת הצירים. פונקציה טהורה — בלי DB, בלי קבצים.

    day: datetime.date (ET) · bars: [Bar] ממוין (ts tz-aware) ·
    snaps: [Snap] כבר מתוקני-T-100 · events: [Event] · census: dict.
    """
    ib_close = datetime.combine(day, IB_END, tzinfo=ET)
    sess_start = datetime.combine(day, RTH_START, tzinfo=ET)
    n_bars = len(bars)

    n_day = n_lvl = 0
    touches = []
    for b in bars:
        if active_snapshot(snaps, b.ts) is not None:
            n_lvl += 1
        d_snap = active_snapshot(snaps, b.ts, not_before=ib_close)
        if d_snap is not None and d_snap.ts >= sess_start:
            n_day += 1
        live = active_snapshot(snaps, b.ts, inclusive=True)
        if live is not None:
            hit = []
            if live.vah is not None and b.low <= live.vah <= b.high:
                hit.append("VAH")
            if live.val is not None and b.low <= live.val <= b.high:
                hit.append("VAL")
            if hit:
                touches.append((b.ts, "+".join(hit)))

    detected_bars = {e.bar_ts for e in events if e.event_type == "DETECTED"}
    decision_bars = {e.bar_ts for e in events if e.event_type in LEDGER_EVENTS}

    aware_touch, missed = 0, []
    for t_ts, kind in touches:
        window = {t_ts + timedelta(minutes=BAR_MINUTES * k) for k in range(CAND_WINDOW_BARS + 1)}
        if window & detected_bars:
            aware_touch += 1
        else:
            missed.append((t_ts.strftime("%H:%M"), kind))

    # T-420: אם שורות-ליגר נפלו בלי חותמת — הציר אינו נסגר, והמונה מוצג כחלקי.
    ledger_partial = census.get("no_usable_ts", 0) > 0 if census else False
    t420 = ""
    if ledger_partial:
        t420 = "T-420: %d/%d שורות-ליגר בלי שדה-זמן שמיש" % (
            census["no_usable_ts"], census["lines"])

    axes = {
        "day": axis(n_day, n_bars,
                    "IB של הסשן ידוע בפתיחת-הבר (צילום-TPO מאותו סשן, לפני הבר, ≥10:30 ET)",
                    measurable=tpo_available,
                    reason="אין שורות v9_tpo_history ליום הזה"),
        "levels": axis(n_lvl, n_bars,
                       "POC/VAH/VAL פעילים ידועים בפתיחת-הבר (כולל גרירה מסשן קודם)",
                       measurable=tpo_available,
                       reason="אין שורות v9_tpo_history ליום הזה"),
        "candidates": axis(aware_touch, len(touches),
                           "נגיעות-VA שהליגר רשם עליהן DETECTED (חלון 0-%d ברים)" % CAND_WINDOW_BARS,
                           measurable=tpo_available and ledger_available and len(touches) > 0
                           and not ledger_partial,
                           reason=(t420 if ledger_partial else
                                   ("אין קובץ-ליגר ליום הזה" if not ledger_available else
                                    ("אין שורות v9_tpo_history ליום הזה" if not tpo_available else
                                     "אפס אירועי-הזדמנות (נגיעות-VA) ביום הזה")))),
        "decisions": axis(len(decision_bars), n_bars,
                          "ברי-RTH עם ≥1 אירוע-ליגר (%s)" % "/".join(LEDGER_EVENTS),
                          measurable=ledger_available and not ledger_partial,
                          reason=(t420 if ledger_partial else "אין קובץ-ליגר ליום הזה")),
    }
    # מונה חלקי לצד NOT-MEASURABLE — שקוף, ולא מתחזה לציון
    if axes["decisions"]["not_measurable"]:
        axes["decisions"]["partial_n"] = len(decision_bars)
        axes["decisions"]["partial_d"] = n_bars
    if axes["candidates"]["not_measurable"]:
        axes["candidates"]["partial_n"] = aware_touch
        axes["candidates"]["partial_d"] = len(touches)

    return {
        "day": day.isoformat(),
        "rth_bars": n_bars,
        "axes": axes,
        "va_touches": [(t.strftime("%H:%M"), k) for t, k in touches],
        "missed_touches": missed,
        "ledger_census": census,
        "tpo_snapshots": len(snaps),
        "tpo_skew_hours": sorted({s.skew_h for s in snaps}) if snaps else [],
    }


# ─────────────────────────────── קלט (DB/קבצים) ───────────────────────────────

def _connect():
    import psycopg2
    cn = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://localhost/mems26"))
    cn.set_session(readonly=True, autocommit=True)   # קריאה-בלבד, אפס כתיבה
    return cn


def load_bars(cur, day):
    cur.execute(
        "SELECT ts, open, high, low, close FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'America/New_York')::date = %s "
        "  AND (ts AT TIME ZONE 'America/New_York')::time >= %s "
        "  AND (ts AT TIME ZONE 'America/New_York')::time <  %s "
        "ORDER BY ts",
        (day.isoformat(), RTH_START.isoformat(), RTH_END.isoformat()))
    return [Bar(r[0].astimezone(ET), r[1], r[2], r[3], r[4]) for r in cur.fetchall()]


def load_tpo(cur, day, lookback_days=5):
    """מושך חלון סביב היום. החלון לאחור נחוץ לציר-הרמות (גרירה מסשן קודם).

    הסינון הוא על `created_at` (רגע-אמת תמיד) ולא על `ts` — ‏ts נגוע-T-100
    היה מוציא את הצילומים של הבוקר מהחלון.
    """
    cur.execute(
        "SELECT ts, created_at, poc, vah, val, ib_high, ib_low FROM v9_tpo_history "
        "WHERE created_at >= %s::date - make_interval(days => %s) "
        "  AND created_at <  %s::date + interval '1 day' ORDER BY ts",
        (day.isoformat(), lookback_days, day.isoformat()))
    return normalize_tpo(cur.fetchall())


def find_ledger(day):
    """(path, lines) לליגר של היום — או (None, None) אם אין.

    סדר: ארכיון-היום ב-`data_handoff/*/<day>/` (צילום-EOD, מקור מועדף) →
    הליגר החי ב-`~/SierraChart_Data/v9_export/` (מתאפס יומית, ולכן נלקח רק
    אם שורותיו באמת של היום המבוקש).
    """
    hits = sorted(glob.glob(os.path.join(ROOT, "data_handoff", "*", day.isoformat(),
                                         "gateway_decisions.jsonl")))
    if hits:
        with open(hits[0], encoding="utf-8") as fh:
            return hits[0], fh.readlines()
    if os.path.exists(LIVE_LEDGER):
        with open(LIVE_LEDGER, encoding="utf-8") as fh:
            lines = fh.readlines()
        stamp = day.isoformat()
        if any(stamp in ln for ln in lines[:5] + lines[-5:]):
            return LIVE_LEDGER, lines
    return None, None


def last_completed_session(cur):
    """התאריך האחרון (ET) שיש לו ברי-RTH והוא קודם להיום — לדיווח מ-fire_drill."""
    cur.execute(
        "SELECT max((ts AT TIME ZONE 'America/New_York')::date) FROM v9_bars_5min_woodies "
        "WHERE (ts AT TIME ZONE 'America/New_York')::time >= %s "
        "  AND (ts AT TIME ZONE 'America/New_York')::time <  %s "
        "  AND (ts AT TIME ZONE 'America/New_York')::date < "
        "      (now() AT TIME ZONE 'America/New_York')::date",
        (RTH_START.isoformat(), RTH_END.isoformat()))
    row = cur.fetchone()
    return row[0] if row else None


def measure(day):
    """מודד יום שלם. מחזיר dict (אותו סכמה כמו score_day) או None אם אין נתון."""
    cn = _connect()
    try:
        cur = cn.cursor()
        bars = load_bars(cur, day)
        if not bars:
            return None
        snaps = load_tpo(cur, day)
    finally:
        cn.close()
    path, lines = find_ledger(day)
    if lines is None:
        events, census = [], {"lines": 0, "parsed": 0, "json_bad": 0,
                              "no_usable_ts": 0, "unknown_event": 0, "by_event": {}}
    else:
        events, census = parse_ledger_lines(lines)
    day_snaps = [s for s in snaps if s.ts.date() == day]
    res = score_day(day, bars, snaps, events, census,
                    tpo_available=bool(day_snaps), ledger_available=lines is not None)
    res["ledger_path"] = path
    res["tpo_snapshots_today"] = len(day_snaps)
    return res


# ──────────────────────────────────── פלט ────────────────────────────────────

LABELS = [("day", "יום"), ("levels", "רמות"), ("candidates", "מועמדים"), ("decisions", "החלטות")]


def render(res):
    out = []
    out.append("ציון-המודעות · %s (ET) · %d ברי-RTH%s"
               % (res["day"], res["rth_bars"],
                  "" if res["rth_bars"] == 78 else "  ⚠️ לא 78 — יום מקוצר/חסר-ברים"))
    for key, label in LABELS:
        a = res["axes"][key]
        if a["n"] is None:
            partial = ""
            if a.get("partial_d"):
                partial = "  [חלקי: %d/%d]" % (a["partial_n"], a["partial_d"])
            out.append("  %-9s NOT-MEASURABLE — %s%s" % (label, a["not_measurable"], partial))
        else:
            out.append("  %-9s %3d/%-3d %6.1f%%  %s   (%s)"
                       % (label, a["n"], a["d"], a["pct"], "✅" if a["ok"] else "🔴", a["note"]))
    ok = sum(1 for k, _ in LABELS if res["axes"][k]["ok"])
    nm = sum(1 for k, _ in LABELS if res["axes"][k]["n"] is None)
    c = res["ledger_census"]
    out.append("  סיכום: %d/4 צירים ≥%d%%%s · ליגר %d שורות (parsed %d + json-bad %d + "
               "no-usable-ts %d) · TPO %d צילומים (הסטת-T-100 %s)"
               % (ok, int(THRESHOLD * 100),
                  (" · %d לא-מדידים" % nm) if nm else "",
                  c["lines"], c["parsed"], c["json_bad"], c["no_usable_ts"],
                  res.get("tpo_snapshots_today", res["tpo_snapshots"]),
                  ("+%dש'" % res["tpo_skew_hours"][0]) if res["tpo_skew_hours"] else "n/a"))
    if res["missed_touches"]:
        out.append("  נגיעות-VA בלי DETECTED: %s"
                   % " · ".join("%s(%s)" % (t, k) for t, k in res["missed_touches"]))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="ציון-המודעות היומי (T-159) — READ-ONLY")
    ap.add_argument("--day", help="YYYY-MM-DD (ET). ברירת-מחדל: היום לפי שעון-ET")
    ap.add_argument("--json", action="store_true", help="פלט-מכונה")
    args = ap.parse_args(argv)
    if args.day:
        try:
            day = date.fromisoformat(args.day)
        except ValueError:
            print("--day חייב להיות YYYY-MM-DD", file=sys.stderr)
            return 2
    else:
        day = datetime.now(ET).date()
    try:
        res = measure(day)
    except Exception as exc:                      # כשל-כנה, לא ערך מסונתז
        print("🔴 ציון-המודעות לא-נמדד — %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    if res is None:
        print("🔴 אין נתונים ל-%s: אפס ברי-RTH ב-v9_bars_5min_woodies "
              "(סוף-שבוע/חג/יום לפני תחילת-האיסוף?). לא חושב ציון." % day.isoformat(),
              file=sys.stderr)
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else render(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
