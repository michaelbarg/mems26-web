# CC — MASTER WORKLIST מסודר · Pre-LIVE (2026-05-29)

**כותב:** Cowork (DB+קוד; אין גישה ל-API/לוגים/Sierra → סעיפי [CC-MAC] לאישור על ה-Mac)
**מטרה:** פרומפט אחד מסודר שמאחד את כל החקירות. בצע **לפי הסדר** — כל phase תלוי בקודמו.
**עקרון (CLAUDE.md):** Diagnose first. אל תיגע בקוד לפני אישור השערה מול נתונים.
Smallest correct change + regression test + אימות 4 צירי. "תוקן" = פקודה+פלט גולמי, לא הצהרה.
**שינויי לוגיקת-מסחר (ספים, גייטים, טקטיקות) דורשים אישור Michael לפני מימוש.**

מסמכי עומק נלווים (פירוט מלא לכל נושא):
- `CC_DIAGNOSE_5MIN_AND_FRONTEND_LATENCY_2026-05-29.md` — באג ts + פרונטאנד
- `CC_NEAR_MISS_AND_RELAXATION_2026-05-29.md` — near-miss + ספים
- `CC_MEGA_PROMPT_SYSTEM_READINESS_CHECK_2026-05-29_v2.md` — בדיקות מצב יומיות

---

## סדר הביצוע (TL;DR)

| Phase | נושא | למה בסדר הזה | סיכון |
|-------|------|--------------|-------|
| **1** | **זמן & TZ — השורש** | מרעיל את S1/S2/פרונטאנד גם יחד | קריטי |
| **2** | **היגיינת עסקאות** | רעש footprint + עסקאות וודי לא-אמיתיות מזהמות P&L/ניתוח | גבוה (pre-LIVE) |
| **3** | **S1 Day Type** | תלוי ב-Phase 1 (זמנים) | גבוה |
| **4** | **S2 5-min** | תלוי ב-Phase 1 (buffer) | בינוני |
| **5** | **S4 Woodies near-miss** | אחרי שהרעש נוקה (Phase 2) | בינוני |
| **6** | **הקלות ספים** | רק אחרי ש-1–5 מאומתים | המלצה+אישור |

---

## PHASE 0 — Bootstrap

```bash
cd /Users/michael/Downloads/mems26_web_git
curl -s http://localhost:8000/health | python3 -m json.tool
python3 scripts/sot_health.py --strict 2>&1 | head -40
python3 -c "from zoneinfo import ZoneInfo;from datetime import datetime;e=datetime.now(ZoneInfo('America/New_York'));print('ET',e.strftime('%H:%M:%S'),'min_since_open',e.hour*60+e.minute-570)"
git log --oneline -5
```

---

## PHASE 1 — זמן & TimeZone (השורש שמרעיל הכל)

**הסימפטום:** "נתונים איטיים/לא מגיעים" בפרונטאנד; S2 לא יורה; S1 לא ננעל.
**השורש:** חותמות זמן ב-`v9_bars_5min` פגומות + פרשנות-TZ שגויה לאורך הקוד.

### 1.1 אישור: בארים עתידיים (+שעה) ב-v9_bars_5min
```bash
python3 - << 'PY'
import sqlite3; db=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True)
print("ts | created_at | delta_min")
for r in db.execute("""SELECT ts,created_at,round((julianday(ts)-julianday(created_at))*1440,1) d
  FROM v9_bars_5min ORDER BY created_at DESC LIMIT 15"""):
    print(f"{r[0]} | {r[1]} | {r[2]}{'  <==FUTURE' if r[2] and r[2]>2 else ''}")
print("future total:",db.execute("SELECT COUNT(*) FROM v9_bars_5min WHERE (julianday(ts)-julianday(created_at))*1440>30").fetchone()[0])
PY
```
מצאתי: ~514 שורות עתידיות (132 היום), היסט נקי ~60 דק' = **שגיאת DST: המרת ET→UTC עם
EST(-5) במקום EDT(-4)**.

### 1.2 שלושת מוקדי ה-TZ הבעייתיים (CLAUDE.md Rule 4)
1. **כותב הבארים הפגום** — שני כותבים ל-`v9_bars_5min` עם טיפול שונה:
   `bars.py::post_bars_5min` (UTC נכון, `_ts_from_unix`) מול נתיב ה-aggregator
   (`bar_aggregator_5min.py` · pytz ET · `bar_ingestion.py:86`). **[CC-MAC] זהה בלוג מי יוצר את ה-+1h.**
2. **`consumer.py:182`** — `ts.replace(tzinfo=_et)` על זמן naive. זהו **באג pytz LMT**
   (offset -4:56) **וגם** הנחה ש-naive==ET בעוד שהבארים נשמרים naive-UTC. שורש כפול.
3. **`session_classifier.py:51`** — `self.ET.localize(now)` על naive → אם הערך באמת UTC,
   כל סיווג ה-session (PRE_MARKET/FIRST_HOUR/CASH_HOURS) זז בשעות.

### 1.3 [CC-MAC] קריטי — האם הזמנים החוסמים מחושבים נכון?
> זו הנקודה שחשד Michael: "בעיה רצינית בזמנים החוסמים". **נכון.** הגייטים של S1
> (`bar.session_min`, `bar.is_rth`) נגזרים מ-ts הבארים. אם ה-ts פגום/מפורש-שגוי, אז:
> - **חלון הפתיחה (A2)** קולט ברים לא-נכונים → opening_type שגוי/INDETERMINATE.
> - **נעילת IB ב-10:30** (`session_min>=60`, `state_machine.py:477`) ננעלת בשעה הלא-נכונה.
> - **נעילה כפויה ב-13:00** (`session_min>=210`, `:686`) זזה.

```bash
# אמת היכן ואיך נגזרים is_rth + session_min ל-BarInput של DayType:
grep -rn "is_rth\|session_min" backend/v9/systems/day_type/consumer.py backend/v9/systems/day_type/hydration.py | grep -v __pycache__
# אמת מול שעון אמיתי שהסיווג נכון עכשיו:
curl -s http://localhost:8000/api/v9/status | python3 -c "import sys,json;d=json.load(sys.stdin);print('session/clock:',d.get('session') or d.get('clock'))"
```

### 1.4 תיקונים (לפי סדר; אימות אחרי כל אחד)
1. **מקור-אמת UTC יחיד** בכתיבת בארים — כל הנתיבים `datetime.fromtimestamp(unix,tz=utc)`.
   המרות ET→UTC רק עם `ZoneInfo('America/New_York').astimezone(utc)` או pytz `localize+normalize`.
   **אסור** `replace(tzinfo=...)` על זמן-קיר. תקן את `consumer.py:182` ל-`_et.localize(ts)` (pytz) או ZoneInfo.
2. **שער קליטה** ב-`bar_ingestion.py`/`bars.py` — דחה `ts > now_utc + 2min` (אל תסנתז).
3. **ניקוי** (אחרי גיבוי `cp data/mems26_local.db data/...bak`): `DELETE FROM v9_bars_5min WHERE (julianday(ts)-julianday(created_at))*1440>30`.
4. **הקשחת query** — `WHERE ts <= datetime('now','+2 minutes')` ב-`bars_5min_history.py:33-39` ו-`bars.py:924`.
5. **היסטים קשיחים** — `five_min_system.py:256` (`timedelta(hours=-4)` קשיח, ישבר בחורף) → ZoneInfo.

### 1.5 אימות Phase 1 (4 צירים)
```bash
python3 - << 'PY'
import sqlite3; db=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True)
bad=db.execute("SELECT COUNT(*) FROM v9_bars_5min WHERE (julianday(ts)-julianday(created_at))*1440>30").fetchone()[0]
a=db.execute("SELECT ts FROM v9_bars_5min ORDER BY ts DESC LIMIT 1").fetchone()[0]
b=db.execute("SELECT ts FROM v9_bars_5min ORDER BY created_at DESC LIMIT 1").fetchone()[0]
print("Quality future bad_count:",bad,"PASS" if bad==0 else "FAIL")
print("Recency newest-ts==newest-created:",a==b,"| ts:",a,"created-newest:",b)
PY
time curl -s "http://localhost:8000/api/v9/bars/5min?limit=60" | python3 -c "import sys,json;d=json.load(sys.stdin);print('rows',len(d),'last',d[-1].get('ts') if d else None)"
```

---

## PHASE 2 — היגיינת עסקאות (footprint proliferation + Woodies רעש)

**מיפוי מערכות:** `firing_system` הוא ID מספרי. **3 = Footprint/Imbalance · 4 = Woodies.**

### 2.1 אישור הרעש (מ-DB)
```bash
python3 - << 'PY'
import sqlite3; db=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True)
def show(t,q):
    print("\n==",t,"=="); cur=db.execute(q)
    print(" | ".join(c[0] for c in cur.description))
    for r in cur.fetchall(): print(" | ".join(str(x) for x in r))
show("trades by system/mode/state today","""SELECT firing_system,mode,state,COUNT(*) n FROM v9_trades
  WHERE entry_ts>datetime('now','-1 day') GROUP BY firing_system,mode,state ORDER BY n DESC""")
show("FOOTPRINT(3) duplicate bursts (same price+minute)","""SELECT entry_price,substr(entry_ts,1,16) m,COUNT(*) n
  FROM v9_trades WHERE firing_system='3' AND entry_ts>datetime('now','-1 day')
  GROUP BY entry_price,m HAVING n>1 ORDER BY n DESC LIMIT 10""")
show("FOOTPRINT(3) entries outside RTH (overnight noise)","""SELECT substr(entry_ts,12,5) t,COUNT(*) n
  FROM v9_trades WHERE firing_system='3' AND entry_ts>datetime('now','-2 day')
  GROUP BY t ORDER BY n DESC LIMIT 8""")
show("WOODIES(4) trades today","""SELECT state,mode,COUNT(*) n FROM v9_trades
  WHERE firing_system='4' AND entry_ts>datetime('now','-1 day') GROUP BY state,mode""")
PY
```

**ממצאים שאני ראיתי (לאישור CC):**
- **Footprint(3): 505 עסקאות היום**, 581 כל-הזמן · **54,948 IMBALANCE signals**.
  בורסטים של **20–26 עסקאות באותו entry_price באותה דקה** (למשל 26× @7589.75 ב-06:53) —
  אלו **לא עסקאות אמיתיות נפרדות** אלא ירי כפול של אותה רמת imbalance על כל update.
  כניסות **מסביב לשעון כולל overnight** (06:xx, 18:xx, 20:xx) → שער RTH לא אפקטיבי על הרישום.
- **Woodies(4): 22 עסקאות**, רובן **shadow** + **12 PARTIAL תקועות** (09:34–10:34, לא נסגרו).

### 2.2 שורש הרעש (קוד)
- **Footprint** `footprint_system.py:426 _fire` — יש `pre_fire_validator` + `_last_fire`, אבל
  **אין dedup לפי רמה/בר** כמו ב-Woodies. כל update של imbalance על אותה רמה → fire נוסף.
  → ה-shadow executor רושם כל אחד כעסקה. **[CC-MAC] אמת בלוג שזה ירי-לכל-update.**
  - הערה חשובה (`footprint_system.py:41-43`): footprint מספק COT/AMT ל-S2, וכרגע
    "COT/AMT random 0..300 → S2 כמעט אף פעם לא יורה". **זה מקשר את הרעש של footprint
    לאפס-הירי של S2** — תקן את ספק ה-COT/AMT.
- **Woodies** `woodies_system.py:401-436` — **יש** dedup per bar_ts (key=pattern+direction).
  הרעש כאן = עסקאות **shadow-mode** (סימולציה, לא אמיתיות) + 12 PARTIAL תקועות שלא נסגרו.

### 2.3 מה CC צריך לעשות (review + ניקוי)
1. **Footprint dedup:** הוסף dedup לפי (price-level + bar_ts) כמו ב-Woodies. למנוע 20–26 ירי/דקה.
2. **Footprint RTH gate:** ודא שאין רישום עסקאות מחוץ ל-RTH (overnight) — filter כמו F17 של Woodies.
3. **COT/AMT provider:** תקן את ה-random 0..300 (footprint_system.py:41-43) — מזין שגוי ל-S2 ול-sizing.
4. **Woodies 12 PARTIAL:** חקור למה תקועות; סגור/תקן reconciliation לפני LIVE.
5. **הבחנת shadow מ-real:** ודא שה-UI/דוחות מסמנים `mode=shadow` בבירור ולא מערבבים עם demo/live.
   **אל תמחק עסקאות shadow ללא גיבוי ואישור Michael** — הן עשויות לשמש ל-backtesting.

### 2.3b עדכון עסקאות שבור + PARTIAL מזויפות (ממצא חדש — מטבלת ה-Trades של Michael)
מ-DB אישרתי:
- **12 ה-PARTIAL התקועות הן placeholder/דמה**, לא עסקאות אמיתיות: כולן
  `entry_price=5900.0, stop=5900.25, t1=5910, t2=5920` (מספרים עגולים) בזמן שהשוק ב-~7588.
  שוכפלו 12× (09:34–10:34) — אותו entry/stop/t1 בדיוק.
- **לא מתעדכנות:** `updated_at` קפא — id 390–392 עודכנו לאחרונה ב-09:34, לפני **~5.8 שעות**.
  T1 נרשם (`t1_hit_ts`) אבל המצב נתקע ב-PARTIAL ולא מתקדם ל-T2/סגירה.
- **R מנופח בתצוגה:** ב-DB `pnl_r=1.5`, אבל בטבלת ה-UI מוצג "60.00R" — באג חישוב/תצוגה.
- עסקאות וודי **אמיתיות** כן עם מחירים שפויים (7592.25 / 7606 / 7606.25, ב-13:45–15:05).

**מה CC צריך לעשות:**
1. מצא את מקור עסקאות ה-5900 (seed/demo/hardcoded fallback) — `grep -rn "5900\|5910\|5920" backend/v9 --include=*.py`
   ובדוק `trading_gateway/executors/{demo,shadow}.py` ו-`day_type_seed.py`/fixtures.
2. תקן את **lifecycle ה-PARTIAL**: למה `updated_at` קופא? מי אמור להריץ exit/close
   (`services/trade_manager/manager.py`, `trail_engine.py`)? PARTIAL בלי התקדמות = trade manager
   לא מנהל אותן (ייתכן שהן shadow ולא ב-loop, או reference price לא תואם).
3. תקן את **חישוב ה-R בתצוגה** (1.5R ב-DB מול 60R ב-UI) — חפש את ה-formula ב-frontend/trades API.
4. **dedup** — אותו entry/stop/t1 לא אמור להיווצר 12×.
> זה מתחבר לבאג ה-ts (Phase 1): entry=5900 עם MFE 1711 נק' ריצף — מחיר/חישוב מנותקים מהשוק.

### 2.4 אימות Phase 2
```bash
python3 - << 'PY'
import sqlite3; db=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True)
dup=db.execute("""SELECT COUNT(*) FROM (SELECT entry_price,substr(entry_ts,1,16) m,COUNT(*) n
  FROM v9_trades WHERE firing_system='3' AND entry_ts>datetime('now','-1 hour') GROUP BY entry_price,m HAVING n>1)""").fetchone()[0]
print("footprint dup-burst groups last hour:",dup,"PASS" if dup==0 else "still bursting")
print("woodies stuck PARTIAL:",db.execute("SELECT COUNT(*) FROM v9_trades WHERE firing_system='4' AND state='PARTIAL'").fetchone()[0])
PY
```

---

## PHASE 3 — S1 DAY TYPE (זמנים + נעילה + opening) ← תלוי ב-Phase 1

### 3.1 האם S1 בודק את סוג היום כל הזמן? — כן (תשובה לשאלתך)
מ-`state_machine.py`:
- **לפני נעילה:** כל בר מצביע מחדש (B6 re-score, `:589-627`) — מחליף סוג-יום אם conf משתפר ב->0.15.
- **אחרי נעילה:** `_check_reeval` (`:～`) רץ כל בר; אם הטווח חורג מהצפוי או failed-extension
  אחרי נעילה → **מאפס ל-PENDING ומחזיר ל-B2** (לולאת הערכה-מחדש). אז כן, רציף.
- **סיכון:** הלולאה הזו יכולה לגרום לאי-יציבות (lock↔reeval). **[CC-MAC] בדוק בלוג כמה
  פעמים היום קרה reeval/אפס-נעילה.**

### 3.2 מגבלות פתיחת היום / הזמנים החוסמים (תשובה לשאלתך)
| גייט | תנאי | קובץ | תלוי TZ? |
|------|------|------|----------|
| זיהוי Opening | ≥3 ברי RTH (~09:45 ET) · `bar.is_rth` | `state_machine.py:446-458` | **כן** |
| IB tracking | `bar.is_rth`, רק Sierra IB | `:460-478` | **כן** |
| **IB lock** | `session_min >= 60` (10:30 ET) | `:477` | **כן** |
| **נעילה כפויה** | `session_min >= 210` (13:00 ET) | `:686`, `schemas.py:100` | **כן** |
| נעילה על conf | `confidence >= 0.70` | `:684`, `schemas.py:99` | לא |
| נעילה על vote | אותו vote ×2 | `:685` | לא |

**הבעיה הרצינית שחשדת בה:** כל הגייטים מבוססי-זמן (`session_min`/`is_rth`) נגזרים מ-ts
הבארים. עם באג ה-+1h ועם `replace(tzinfo=_et)` (Phase 1.2), **הם עלולים להיפתח בשעה הלא-נכונה**.
זה ההסבר הסביר ל-`opening_type=INDETERMINATE` (חלון פתיחה קלט ברים שגויים) ולנעילה שלא קורית.
**חובה לתקן Phase 1 לפני שמסיקים על S1.**

### 3.3 מה קרה היום (מ-DB)
- IB תקין: high=7611.75 low=7586.75 רוחב MEDIUM. `opening_type=INDETERMINATE` →
  Decision Matrix מפיל ל-`Normal` כברירת-מחדל (`decision_matrix.py:59-62`), לא קריאה אמיתית.
- conf=0.68 < 0.70 → לא ננעל. stage תקוע ב-**B2** כל היום (לא הגיע ל-C1). lock_state=PENDING.
- **שני detectors ל-opening** קיימים — `detector.py:detect_opening_type` (משמש A2, לעולם לא
  מחזיר INDETERMINATE) מול `open_type.py:classify_open_type`. **[CC-MAC] אמת מי חי ומאיפה
  נכתב INDETERMINATE בפועל.**

### 3.4 ספי opening (לברים אפשריים — ראה Phase 6)
OPEN_DRIVE `directional_ratio≥0.7` · TEST_DRIVE pullback 0.2–0.6 · REJECTION_REVERSE
`|last|≥|first|×0.5` · AUCTION_OUT (מחוץ ל-PD) · AUCTION_IN (אחרת, conf 0.4). `detector.py:36`.

---

## PHASE 4 — S2 5-MIN near-miss ← תלוי ב-Phase 1 + 2.3(COT/AMT)

שרשרת השערים: mode (FIRST_HOUR→DAY_TYPE_MODE) → Nontrend skip → Reactive/Initiative →
chart(Normal עובר) → flags(Normal עובר) → FHB eligibility → sizing!=reject (COT/AMT 1.2×/0.8×).
(`five_min_system.py:665-785`).

```bash
# [CC-MAC] שלושת הלוגים שמסבירים אפס-ירי:
grep -E "current_day_type is None|FHB gate|NT NO_TRADE|FIRE:" /tmp/mems26_backend.log | tail -40
#   "FHB gate ... blocked" = near-miss אמיתי (pattern זוהה ונחסם)
#   אין שורה = לא זוהה pattern (לא חסימה)
```
חשודים לאפס-ירי: (1) באג ts מזהם buffer (Phase 1); (2) COT/AMT random מ-footprint (Phase 2.3);
(3) day_type=None עד 10:30. **תקן 1+2 לפני מסקנה.** `v9_five_min_state` ריק — המערכת קוראת
אך לא כותבת (`:157`); החלט עם Michael אם לכתוב state או לסמן deprecated.

---

## PHASE 5 — S4 WOODIES near-miss (אחרי ניקוי Phase 2)

S4 פעיל. ה-near-miss = signals שלא הפכו לעסקה. ספים: YELLOW lock חוסם הכל (`woodies_system.py:303`),
sizing=reject על COT/AMT (1.2×/0.8×), dedup per-bar. signals חלשים היום: TLB SHORT 0.49, GB100 0.50.
```bash
grep -E "YELLOW state|reject|FIRE" /tmp/mems26_backend.log | grep -i wood | tail -30
```

---

## PHASE 6 — הקלות ספים (המלצה בלבד · אישור Michael חובה)

| # | מערכת | הקלה | סיכון |
|---|-------|------|-------|
| 1 | S1 | תקן wiring של opening detector (INDETERMINATE→סיווג אמיתי) | בינוני |
| 2 | S1 | conf 0.70→0.65 או הקדמת forced-lock מ-13:00 | נועל ניחוש חלש |
| 3 | S2 | `BELLY_DOMINANCE_RATIO` 1.5→1.3 · COT/AMT 1.2/0.8→1.1/0.9 | +false-positives |
| 4 | S4 | high-priority patterns ב-YELLOW · COT/AMT 1.1/0.9 | +רעש |

**אסור להקל ספים לפני ש-Phase 1+2 תוקנו ואומת ש-0 הירי אינו תקלה טכנית.**

---

## PHASE 7 — נתונים ל-Decision Tree + Flow Diagram של סוג-היום (ל-Cowork)

Michael רוצה אחרי ה-run: (א) **עץ החלטות** של מה שקרה בפועל היום עם סוג-היום (זמנים,
מערכות מחוברות, היכן בקוד); (ב) **תרשים זרימה** — מה S1 מקבל, מה הוא נותן, למי, מתי, ומה צריך.
את התרשים הארכיטקטוני Cowork כבר בונה מהקוד. כדי למלא את ה**ערכים בפועל של היום**, CC
צריך להחזיר את הפלט הגולמי של:

```bash
# 7.1 — ציר הזמן המלא של מעברי ה-state היום (זמנים בפועל)
sqlite3 data/mems26_local.db << 'SQL'
SELECT substr(ts,12,8) et_utc, stage, day_type, opening_type, lock_state, round(confidence,2)
FROM v9_day_type_state WHERE ts>datetime('now','-1 day')
GROUP BY stage,lock_state,day_type,opening_type ORDER BY MIN(ts);
SQL

# 7.2 — מי צרך את אירועי day_type (S2 ועוד) ומתי
grep -E "day_type|current_day_type|on_day_type|classification" /tmp/mems26_backend.log | tail -60

# 7.3 — מקורות הקלט של S1: PD context, Sierra IB, opening bars
grep -E "\[DayType\].*(IB|opening|PD|prev_day|seed|hydrate|stage)" /tmp/mems26_backend.log | tail -60

# 7.4 — אילו מערכות מחוברות ל-S1 (event subscriptions)
grep -rn "day_type.classification\|system.day_type\|subscribe.*day_type\|on_day_type" backend/v9 --include=*.py | grep -v __pycache__
```

**מבנה שה-Cowork ימלא (CC רק מספק raw):**
- **קלט ל-S1:** ברי 5-דק' (RTH/Globex), Sierra Study IB (high/low), PD context (pd_high/low/close),
  overnight H/L, ATR → היכן: `state_machine.py` BarInput, `prev_day.py`, `extensions.py`.
- **שלבים+זמנים:** A1(09:30)→A2(~09:45 opening)→A3(IB)→A4(10:30 lock)→B1–B6(vote)→C1(lock)→C2→C3(playbook).
- **פלט של S1:** `day_type`, `opening_type`, `ib_*`, `confidence`, `lock_state`, `playbook` →
  ל-`v9_day_type_state`/`v9_day_type_history` + event `system.day_type.classification`.
- **צרכנים:** S2 (`five_min_system.py:_on_day_type_update`, hydrate:157), frontend (DayType strip),
  decision_matrix, targets. מתי: בכל מעבר state + on lock.
- **מה צריך:** Sierra IB אמין + ts תקין (Phase 1!) + PD context + opening bars ב-RTH.

## מפת קבצים
- בארים/ts: `api/v9/bars.py` (241,924), `services/bar_ingestion.py` (86), `services/bar_aggregator_5min.py` (18,53,171), `api/v9/bars_5min_history.py` (33)
- TZ: `common/session_classifier.py` (45,51), `systems/day_type/consumer.py` (181), `five_min_system.py` (256)
- S1: `systems/day_type/state_machine.py` (446 A2,477 IB,684 lock,_check_reeval), `detector.py` (36), `open_type.py`, `decision_matrix.py` (59), `schemas.py` (96-100)
- עסקאות: `systems/footprint/footprint_system.py` (41,426), `systems/woodies/woodies_system.py` (303,401), `services/trading_gateway/executors/{shadow,demo,live}.py`
- S2: `systems/five_min/five_min_system.py` (37,594,665-785,157)

## אסור (CLAUDE.md)
אל תסנתז ts/בארים/COT-AMT. אל תעלה polling. bridge → localhost בלבד. אל תמחק עסקאות ללא
גיבוי+אישור. שינוי לוגיקת-מסחר → strategic stop + אישור Michael. כל "תוקן" = פקודה+פלט גולמי.
```
