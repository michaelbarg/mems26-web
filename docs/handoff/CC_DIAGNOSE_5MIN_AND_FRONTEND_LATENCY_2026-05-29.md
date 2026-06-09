# CC הוראת עבודה — אבחון S2 (5min) + נתונים איטיים בפרונטאנד

**תאריך:** 2026-05-29 · **כותב הבריף:** Cowork (בדיקות DB+קוד; אין לי גישה ל-`localhost:8000`/לוגים/Sierra)
**עקרון עבודה (CLAUDE.md):** Diagnose first, fix second. אל תיגע בקוד לפני שאישרת את ההשערה
מול נתונים. כל תיקון = smallest correct change + regression test + אימות 4 צירי UAT.

---

## 0. TL;DR — מה מצאתי (מבוסס נתונים, לא זיכרון)

**הסימפטום של "הנתונים מגיעים לאט / לא מגיעים מסיארה" אינו בעיית קבלת נתונים — הנתונים
כן מגיעים.** הבעיה: **חותמות זמן עתידיות בטבלת `v9_bars_5min`.**

קיימות **שתי אוכלוסיות** של בארים 5-דק' שנכתבות לאותה טבלה:

| אוכלוסייה | `ts - created_at` | משמעות |
|-----------|-------------------|--------|
| תקינה | ≈ 0 (שניות) | ts ב-UTC נכון |
| **פגומה** | **+55..60 דק' (שעה שלמה)** | ts מוקדם בשעה אחת קדימה |

ראיות שאספתי (חלון שעתיים אחרון): **5 בארים תקינים מול 10 בארים עתידיים** — הפגומים הם
*הרוב*. סה"כ 514 שורות עתידיות בטבלה, 132 מהן היום.

**הסבר השורש (השערה חזקה):** שגיאת DST — קוד שממיר זמן ET ל-UTC עם היסט קבוע של
**5 שעות (EST/חורף)** במקום **4 שעות (EDT/קיץ)**. ‎09:35 ET שאמור להפוך ל-13:35 UTC
הופך ל-14:35 UTC = **+שעה לעתיד**. ההיסט הנקי של 60 דק' (ראה שורות עם delta=60.0)
תואם בדיוק להפרש EST↔EDT.

**למה זה שובר את הפרונטאנד:** השאילתה היא `ORDER BY ts DESC LIMIT n`
(ראה `backend/v9/api/v9/bars_5min_history.py:38` ו-`bars.py:924`). הבארים העתידיים
*תמיד* ממוינים לראש → קצה הגרף הימני הוא בר־רפאים שעה קדימה, והבארים האמיתיים
"נופלים" מתחתיו. התוצאה: הגרף נראה תקוע/מתעדכן באיחור, למרות שהדאטה זורם כל 5 דק'.

**למה S2 לא יורה כלום:** שתי סיבות נפרדות —
1. **שלב היום (תקין לשעה זו):** ‎09:3X ET, לפני נעילת IB → `day_type=UNKNOWN/PENDING`,
   `current_day_type=None`. הטקטיקות מבוססות סוג-יום (H&S/Double/Flag · Pkg 5a/5b/5c)
   מדולגות בשקט (`five_min_system.py:742`). זה צפוי עד ~10:30 ET.
2. **באג ה-ts:** ה-buffer של S2 וה-freshness שלו נסמכים על סדר ה-ts — בארי-רפאים עתידיים
   מזהמים אותו (CLAUDE.md Rule 3: min/max amplifier).

**ממצא נלווה:** הטבלה `v9_five_min_state` **ריקה לגמרי** — המערכת *קוראת* ממנה
(`five_min_system.py:157`) אבל **לעולם לא כותבת** אליה (היחיד שנכתב הוא
`V9FiveMinSetup`, טבלה אחרת). כל רכיב פרונטאנד/סטטוס שקורא `v9_five_min_state` יראה ריק.

---

## 1. אישור השורש — הרץ קודם (לא לתקן עדיין!)

```bash
cd /Users/michael/Downloads/mems26_web_git

# 1.1 — שתי האוכלוסיות: תקין מול +שעה (חלון 2h)
python3 << 'PY'
import sqlite3
db=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True)
print("ts | created_at | delta_min")
for r in db.execute("""SELECT ts, created_at,
   round((julianday(ts)-julianday(created_at))*1440,1) d
   FROM v9_bars_5min ORDER BY created_at DESC LIMIT 20"""):
    print(f"{r[0]} | {r[1]} | {r[2]}{'  <== FUTURE' if r[2] and r[2]>2 else ''}")
print("correct(<2m):", db.execute("SELECT COUNT(*) FROM v9_bars_5min WHERE abs(julianday(ts)-julianday(created_at))*1440<2 AND created_at>datetime('now','-2 hours')").fetchone()[0])
print("future(+~1h):", db.execute("SELECT COUNT(*) FROM v9_bars_5min WHERE (julianday(ts)-julianday(created_at))*1440 BETWEEN 50 AND 70 AND created_at>datetime('now','-2 hours')").fetchone()[0])
print("future TOTAL:", db.execute("SELECT COUNT(*) FROM v9_bars_5min WHERE (julianday(ts)-julianday(created_at))*1440 > 30").fetchone()[0])
PY
```

**ציפייה לאישור:** רואים שורות עם delta≈60. אם כן — השורש מאומת, המשך לזיהוי הכותב.

```bash
# 1.2 — זהה איזה כותב יוצר את הבארים העתידיים.
# שני כותבים ל-v9_bars_5min עם טיפול-TZ שונה:
#   (A) backend/v9/api/v9/bars.py::post_bars_5min  -> _ts_from_unix() -> UTC נכון  (bars.py:241,311)
#   (B) backend/v9/services/bar_ingestion.py:86 (מוזן מ-bar_aggregator_5min.py · pytz ET) -> חשוד
grep -nE "_ts_from_unix|fromtimestamp|tz=timezone.utc" backend/v9/api/v9/bars.py | head
sed -n '14,60p' backend/v9/services/bar_aggregator_5min.py     # ET=pytz America/New_York · _bar_start_for
sed -n '165,200p' backend/v9/services/bar_aggregator_5min.py   # persist: "ts": bar.start_ts (ET!)
sed -n '45,100p' backend/v9/services/bar_ingestion.py          # ts = bar_data.get("ts") כפי שהוא

# 1.3 — הוסף תיוג זמני (DIAGNOSTIC ONLY) כדי לראות בלוג מי כותב מה:
#   בכל אחד משני נתיבי הכתיבה הוסף logger.info עם ts לפני ה-commit, restart, צפה 10 דק'.
#   אל תשאיר את הלוגים — זה שלב אבחון בלבד.
```

```bash
# 1.4 — היסטים קשיחים שמפרים CLAUDE.md Rule 4 (TZ ambiguity) — וודא אם אחד מהם בנתיב הבארים
grep -rnE "timedelta\(hours=-4\)|timedelta\(hours=-5\)|hours=-5|hours=-4|tzinfo=_CHICAGO|replace\(tzinfo=" backend bridge --include=*.py | grep -v __pycache__
# ידועים:
#   five_min_system.py:256  -> tz=timezone(timedelta(hours=-4))  (EDT קשיח — ישבר בחורף)
#   services/daily_quality_agent/agent.py:30-31 -> _ET_OFFSET_STANDARD=-5 / _ET_OFFSET_DST=-4
#   bridge/v9_streams/base_stream.py:302, bridge/v9_history.py:70 -> replace(tzinfo=_CHICAGO_TZ)
```

---

## 2. תיקונים מוצעים (לפי סדר עדיפות · smallest correct change)

> **אל תבצע את כולם בבת אחת.** Fix #1 + #2 הם הקריטיים לפרונטאנד וניתנים לאימות מיידי.
> אחרי כל fix — הרץ את אימות §3 והדבק פלט גולמי (Rule 5), ואז עבור לבא.

### Fix #1 — מקור-אמת אחד ל-UTC בכתיבת הבארים (שורש)

לאחר שזיהית את הכותב הפגום ב-§1.2/1.3:
- ודא ששני הנתיבים כותבים **UTC timezone-aware** בלבד. הדפוס הנכון:
  `datetime.fromtimestamp(unix_ts, tz=timezone.utc)` (כמו `_ts_from_unix` הקיים והנכון).
- אם הכותב הפגום ממיר מ-ET: אסור היסט קבוע. השתמש ב-
  `ET.localize(naive).astimezone(timezone.utc)` (pytz) **עם `normalize()`** או ב-
  `zoneinfo` (`ZoneInfo('America/New_York')`). אסור `replace(tzinfo=...)` על זמן קיר.
- **אל תסנתז ערכים** — רק לתקן את ההמרה (CLAUDE.md § Honest failure).

### Fix #2 — שער קליטה: דחה בארים עם ts עתידי

ב-`backend/v9/services/bar_ingestion.py` (סביב שורה 50-87, שם כבר יש "Rejected invalid bar")
ו/או ב-`bars.py::post_bars_5min` — הוסף בדיקה:
```python
if ts > datetime.now(timezone.utc) + timedelta(minutes=2):
    logger.warning("[BarIngestion] Rejected FUTURE bar ts=%s (now+2m guard)", ts)
    return  # אל תכתוב; אל תסנתז
```
זה עוצר הצטברות שורות-רפאים מיידית, גם אם השורש חוזר. **הוסף regression test.**

### Fix #3 — ניקוי 514 שורות הרפאים הקיימות (אחרי גיבוי)

```bash
# גיבוי קודם!
cp data/mems26_local.db data/mems26_local.db.bak_$(date +%Y%m%d_%H%M%S)
# מחיקת שורות עתידיות (אחרי ש-Fix #1/#2 פעילים, אחרת יחזרו)
python3 -c "
import sqlite3
db=sqlite3.connect('data/mems26_local.db')
n=db.execute(\"DELETE FROM v9_bars_5min WHERE (julianday(ts)-julianday(created_at))*1440 > 30\").rowcount
db.commit(); print('deleted future-ts rows:', n)
"
```
**שים לב:** יש `UNIQUE(ts, symbol)` (bars.py:260). הבארים העתידיים אינם מתנגשים עם
התקינים (ts שונה ב-שעה) ולכן ה-UPSERT לא מנע אותם — הניקוי בטוח.

### Fix #4 — הקשח את שאילתת הפרונטאנד מפני ts עתידי (הגנה כפולה)

ב-`backend/v9/api/v9/bars_5min_history.py:33-39` ובשאילתות `ORDER BY ts DESC` (bars.py:924,452):
הוסף `WHERE ts <= datetime('now','+2 minutes')` כך שגם אם תיכנס שורת-רפאים, הגרף לא יקפוץ
לעתיד. שמור על מיון asc סופי כפי שכבר קיים (lightweight-charts דורש סדר עולה).

### Fix #5 — היסטים קשיחים (חוב, לא דחוף לפני LIVE אבל סכנת-חורף)

- `five_min_system.py:256` — `timezone(timedelta(hours=-4))` קשיח. החלף ל-
  `ZoneInfo('America/New_York')` כדי שלא ישבר במעבר ל-EST.
- ודא ש-`daily_quality_agent` בוחר `_ET_OFFSET_DST/STANDARD` לפי תאריך ולא קבוע.

### Fix #6 — `v9_five_min_state` לא נכתב (S2 state בלתי-נראה)

המערכת קוראת מ-`V9FiveMinState` (`five_min_system.py:157`) אך לא כותבת. החלט עם Michael:
- אם הפרונטאנד/סטטוס אמורים להציג mode/day_type/choppiness מהטבלה → הוסף persist של
  state בסוף `process_bar` / במעברי mode (UPSERT לפי `session_date=et_today()`).
- אם המצב נשמר רק בזיכרון בכוונה → עדכן את הצרכנים לקרוא מה-API ולא מהטבלה הריקה,
  וסמן את הטבלה כ-deprecated. **שאל את Michael איזו כוונה נכונה לפני מימוש.**

### Fix #7 — טקטיקות לפי סוג-פתיחה לא מחווטות (פער תכוני)

`opening_type` נשמר ב-`five_min_system.py` (69,200,217,281) ומוצג בפלט (1003) אבל
**לא משפיע על שום החלטת טקטיקה/sizing/time-stop**. הלוגיקה
`(opening_type,direction)→(sizing,time_stop)` יושבת ב-
`backend/v9/systems/five_min/archive/first_hour_matrix.py` ו**לא מיובאת בשום קוד חי**.
אם הכוונה ש-S2 יתאים טקטיקה לסוג הפתיחה — צריך לחווט את `first_hour_matrix` ל-
`calculate_size`/`time_stop_mapper` בנתיב הירי. **שאל את Michael אם זה בתחום (scope)**
לפני המימוש — זו תוספת לוגיקת-מסחר וצריכה אישור (CLAUDE.md § Strategic stop).

---

## 3. אימות (4 צירי UAT — חובה אחרי כל fix)

```bash
# Quality — אין יותר בארים עתידיים
python3 -c "
import sqlite3; db=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True)
bad=db.execute(\"SELECT COUNT(*) FROM v9_bars_5min WHERE (julianday(ts)-julianday(created_at))*1440>30\").fetchone()[0]
print('future-ts bad_count =', bad, 'PASS' if bad==0 else 'FAIL')
"

# Recency — הבר האחרון לפי ts == הבר האחרון לפי created_at (לא רפאים)
python3 -c "
import sqlite3; db=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True)
a=db.execute('SELECT ts FROM v9_bars_5min ORDER BY ts DESC LIMIT 1').fetchone()[0]
b=db.execute('SELECT ts FROM v9_bars_5min ORDER BY created_at DESC LIMIT 1').fetchone()[0]
print('newest-by-ts:',a,'| newest-by-created:',b,'| PASS' if a==b else '| FAIL — ts ordering still poisoned')
"

# Cardinality + Latency — דרך ה-API (רץ על ה-Mac)
time curl -s "http://localhost:8000/api/v9/bars/5min?limit=60" | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('rows:',len(d)); print('last ts:', d[-1].get('ts') if d else None)
"
# Cardinality: len==60 (או כמה שיש). Latency: < הסף המתועד. last ts לא בעתיד.

# Frontend חי
curl -s -o /dev/null -w "frontend :3000 -> %{http_code}\n" http://localhost:3000
```

**הגדרת "תקין" (GO):** `future bad_count=0`, newest-by-ts == newest-by-created,
הגרף בפרונטאנד מתעדכן כל ≤5 דק' עם הבר האחרון בזמן הנכון, ו-S2 חוזר לעבוד מבחינת
buffer/freshness. (ירי טקטיקות סוג-יום עדיין מותנה בנעילת day_type אחרי ~10:30 ET — זה תקין.)

---

## 4. סדר ביצוע מומלץ ל-CC

1. הרץ §1 → הדבק פלט גולמי, אשר השורש, **זהה את הכותב הפגום** (§1.2/1.3).
2. **עצור ודווח ל-Michael** עם הממצא לפני שינוי קוד-מסחר (Fix #6/#7 דורשים אישור).
3. בצע Fix #1 + #2 → אימות §3 → הדבק פלט.
4. Fix #3 (ניקוי, אחרי גיבוי) → אימות recency.
5. Fix #4 (הקשחת query) → אימות frontend.
6. Fix #5 (חוב TZ) — אם הזמן מאפשר.
7. סכם בדו"ח `docs/reports/` + `git log --oneline -5`. אל תתקדם ל-P-ID הבא לפני הדו"ח.

**קבצים מרכזיים:**
- כתיבה: `backend/v9/api/v9/bars.py` (241,260,305-343), `backend/v9/services/bar_ingestion.py` (50-87), `backend/v9/services/bar_aggregator_5min.py` (14-60,165-200)
- קריאה/פרונטאנד: `backend/v9/api/v9/bars_5min_history.py` (20-61), `bars.py` (452,924)
- S2: `backend/v9/systems/five_min/five_min_system.py` (157 state-read, 256 hardcoded -4, 665-866 process_bar/fire, 742 day_type gate)
- TZ חשודים: `five_min_system.py:256`, `daily_quality_agent/agent.py:30-31`, `bridge/v9_streams/base_stream.py:302`, `bridge/v9_history.py:70`

---

## 5. מה שאסור (CLAUDE.md)

- אל תסנתז ts/בארים. שורש שותק → דחה/`None`, לא ערך מומצא.
- אל תיגע ב-`sc_study/`, bridge market-data routes ללא קריאת §7a ב-`P30_AGENT_INBOX_PRE_LIVE.md`.
- אל תעלה תדירויות polling בפרונטאנד (טבלת Polling Floors ב-CLAUDE.md) — הבעיה אינה תדירות.
- אל תשנה את כתובת ה-bridge מ-localhost. אם רואים `API push FAILED to https://` — עצור.
- "תוקן" = הדבקת פקודה + פלט גולמי, לא הצהרה (Rule 5).
```
