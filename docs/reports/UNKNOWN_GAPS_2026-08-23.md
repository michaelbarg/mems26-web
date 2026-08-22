# פערים שאיש לא דיווח עליהם — ציד שיטתי · 2026-08-23

**מייקל: "האם יש עוד פערים — כאלה שאני לא המצאתי — שקיימים במערכת?"**

**מחבר:** cowork-dev/agent · **קריאה-בלבד על הייצור** (אפס שינויי קוד-רץ / דגל / `.env`,
אפס ריסטארטים, אפס כתיבות-DB). כל `file:line` נקרא היום; כל מספר בא מ-psycopg2
‎`set_session(readonly=True)`‎ מול ‎`postgresql://localhost/mems26`‎ או מ-‎`/tmp/backend.err.log`‎.

**מה **לא** חוזר כאן** (פריטים ידועים — לא נספרים כ"חדשים"): T-29 (‎`EXIT_VERIFY_V1`‎ רשום
רק על 2 מסלולי-יציאה) · T-59 (‎`TREND_STOP_FLOOR_V1`‎ use-before-assign) · ‎`v9_bars_tick_reversal`‎
קפואה 51 יום · ארכוב-לוגים (A7) · ‎HLST/RE_PULLBACK‎ ב-Auth (A4) · 18 מ-32 תבניות
לא-ממופות בפלייבוק · המקדמים-הפסוקים כקוד-מת · ‎`v9_bars_5min`‎ חלקית מול woodies.

---

## 0 · הדירוג — שמונה פערים חדשים

| # | הפער | ‎$‎/בטיחות | תיאורטי או **הכיש כבר** |
|---|---|---|---|
| **1** | **‎`S2_CVD_DETECTION_V1`‎ הוא no-op מוחלט בייצור** — השאילתה מחזירה ‎0 שורות ב-76/76 חלונות | 🔴 **$ ישיר** — שער-הזרימה היחיד של S2 מעולם לא רץ חי | **הכיש** — פוסל דגל-חי ומדידה שפורסמה |
| **2** | **11 טבלאות ‎`v9_*`‎ מאחסנות ‎`ts`‎ כ-‎`character varying`‎** — כל טווח/מיון עליהן לקסיקלי | 🔴 שורש-המחלקה של ‎#1‎; ‎32.8%‎ מהשורות גם מחוץ לרשת-5-הדקות | **הכיש** (דרך ‎#1‎) |
| **3** | **שלוש הגדרות סותרות ל"תאריך"** בין שלוש הטבלאות שכל אבחון מצליב | 🔴 שלמות-מדידה ⇒ **כל** מספר-‎$‎ | **הכיש** — ספירות-המעברים שפורסמו הן על חלון-UTC |
| **4** | **334 בליעות-חריגה שקטות** בנתיב-החי, ואי-אפשר לדעת אילו ירו — הלוג בן יום | 🟠 בטיחות | חלקית — מחלקה מוכחת (T1 08-16), הספירה חדשה |
| **5** | **ערוץ-ה-WARNING הוא ‎96%‎ רעש-עצמי** (‎796‎ מתוך ‎828‎ שורות היום) | 🟠 בטיחות — האזהרה האמיתית היחידה של היום היא ‎1‎ מתוך ‎828‎ | **הכיש** — נמדד היום |
| **6** | **‎`get_live_day_type()`‎ לא יכולה להחזיר ‎`Normal_Variation`‎** — ו-4 מודולים חיים מסתעפים בדיוק על המחרוזת הזו | 🟠 מחלקת-HLST; אחד מהם מת על ‎25/34‎ סשנים | חלקית-חי (‎context_radar‎), חלקית-תיאורטי (2 דגלים כבויים) |
| **7** | **אזעקת-הקיפאון של סוג-היום קוראת את הטבלה במקום את פעימת-הלב שנבנתה בדיוק בשבילה** | 🟠 עייפות-אזעקות | **הכיש** — 26 אזעקות-שווא היום |
| **8** | **מסלולי-נתונים מתים, מדודים** — ‎`v9_tpo_bars`‎ מנוטרת כזרם-חי ושורתה האחרונה מ-‎2023-11-25‎ | 🟡 תשתית + אמון-בלוח | **הכיש** (הלוח מציג זרם שאינו קיים) |

---

## 1 · 🔴 ‎`S2_CVD_DETECTION_V1`‎ הוא no-op מוחלט בייצור — ‎0/76‎ חלונות

**הקוד.** ‎`backend/v9/systems/five_min/five_min_system.py:743-751`‎:

```python
bar_timestamps = [b.get("ts") for b in bars_5m[-window:] if b.get("ts")]
first_ts, last_ts = bar_timestamps[0], bar_timestamps[-1]
rows = read_all(
    "SELECT cumulative FROM v9_bars_cumulative_delta "
    "WHERE ts >= :t0 AND ts <= :t1 ORDER BY ts ASC",
    {"t0": str(first_ts), "t1": str(last_ts)},
)
```

**מה ‎`b["ts"]`‎ באמת מכיל בייצור.** ‎`backend/v9/api/v9/bars.py:662-669`‎ —
‎`_flat_5min_for_router`‎ בונה ‎`"ts": str(ts)`‎ כאשר ‎`ts = _ts_from_unix(...)`‎ הוא
‎`datetime.fromtimestamp(x, tz=utc)`‎ (‎`bars.py:397-400`‎). ב-Python
‎`str(datetime)`‎ ≡ ‎`isoformat(sep=' ')`‎ ⇒ **‎`'2026-08-21 14:20:00+00:00'`‎ עם רווח**.
מסלול-ההידרציה זהה: ‎`five_min_system.py:448`‎ ‎`"ts": str(row.ts or "")`‎.
המסלול היחיד שייצר ‎`'T'`‎ (‎`bar_aggregator_5min.py:107`‎, ‎`.isoformat()`‎) **כבוי מאז 08-12**
(‎`AGGREGATOR_5MIN_PUBLISH_V1=0`‎).

**מה הטבלה מכילה.** ‎`v9_bars_cumulative_delta.ts`‎ הוא ‎`character varying`‎ ובו
‎`'2026-08-21T20:55:00+00:00'`‎ — **עם ‎`T`‎**.

**האריתמטיקה.** ההשוואה היא **מחרוזתית**. בתו ה-11 ‎`' '` (0x20) < `'T'` (0x54)‎, ולכן כל
שורת-‎`T`‎ **גדולה** מכל חסם-רווח של אותו תאריך ⇒ ‎`ts <= :t1`‎ **אף פעם לא מתקיים**.

**הראיה (‎Rule 5‎) — 79 ברי-RTH של 08-21, 76 חלונות של 4 ברים:**

```
LIVE bound format str(datetime) ->  rows==0 on 76/76 windows ; rows>=4 on 0
ISO   bound format isoformat()  ->  rows==0 on  0/76 windows ; rows>=4 on 50
sample live bound: '2026-08-21 14:20:00+00:00'  vs stored: '2026-08-21T20:55:00+00:00'
```

**המשמעות.**
1. ‎`len(cums) < 2`‎ ⇒ ‎`return None`‎ ⇒ **fail-open בכל בר**. ‎`S2_CVD_DETECTION_V1=1`‎
   (‎`.env:74`‎) דלוק, והשער **מעולם לא רץ בייצור**.
2. ‎`CVD_EFFORT_RESULT §3ב`‎ מדד "‎16.3%‎ מהברים מיושרים" ו"השער שווה ‎+$868.85‎" —
   אבל **הריפליי הזין את ‎`_cvd_sorted`‎ מ-Python ולא דרך ה-SQL הזה**. כלומר המדידה
   תיארה שער שלא רץ. שתי השורות בטבלת-הזרועות של ‎§6‎ ("S2 חי (DB CVD)" מול "S2 עם CVD עיוור")
   הן, במציאות-הייצור, **אותה זרוע**.
3. **🔴 ‎`A1`‎ בפקודת-יום-שני לא מתקן את זה.** ‎`A1`‎ מוסיף ‎`if len(cums) < window: return None + warning`‎ —
   אבל ‎`cums`‎ כבר ריק, אז התיקון יוסיף ‎WARNING‎ בכל בר וישנה **אפס** התנהגות.
   **התיקון הנכון:** לבנות את החסמים כ-‎`.isoformat()`‎ (או, נכון יותר, להמיר את העמודה
   ל-‎`timestamptz`‎ — ‎#2‎), ורק אז ‎`A1`‎ הופך למשמעותי.
4. **אזהרת-כיוון:** תיקון זה **מדליק** שער-סינון שלא רץ מעולם ⇒ פחות ירי ⇒
   **שינוי משטח-סיכון-מסחר** ⇒ עצירה-אסטרטגית + פסיקת-מייקל, לא "תיקון-באג".

---

## 2 · 🔴 ‎`ts`‎ כמחרוזת ב-11 טבלאות — מחלקת-השורש של ‎#1‎

```
v9_bars_cumulative_delta.ts   character varying   ← מקור-ה-CVD של S2
v9_woodies_signals.ts         character varying   ← איתותי-S4
v9_woodies_signals_archive.ts character varying
v9_bars_imbalance.ts          character varying
v9_bars_volume_profile.ts     character varying
v9_bars_woodies.ts            character varying
v9_bars_stacked_imbalance.ts  character varying
v9_footprint_journal.ts       character varying
v9_footprint_setups.ts        character varying
v9_chop_score.ts              character varying
v9_day_type_shadow_transitions.ts / v9_reversal_enrichment.bar_ts / v9_session_meta.updated_at
```

כל ‎`WHERE ts BETWEEN`‎ / ‎`ORDER BY ts`‎ עליהן הוא **לקסיקלי**. שני מוקשים כבר בשטח:

* **שני אורכי-מחרוזת מתקיימים במקביל** ב-‎`v9_bars_cumulative_delta`‎ (‎4,995‎ באורך 25,
  ‎224‎ באורך 26) ⇒ הסדר הלקסיקלי אינו זהה לסדר הכרונולוגי בגבול.
* **‎1,714‎ מתוך ‎5,219‎ שורות (‎32.8%‎) אינן על רשת-5-הדקות** — למשל ‎`2026-08-21T20:49:59+00:00`‎.
  גם אחרי תיקון החסמים, "חלון של 4 ברים" **לא יחזיר 4 שורות**. זה, ולא רק הכיסוי, מסביר
  את ההתפלגות ‎0/2/3/4‎ שנצפתה ב-‎`CVD_EFFORT §3ב`‎.

**התיקון:** ‎`ALTER … TYPE timestamptz USING ts::timestamptz`‎ + התאמת הכותבים, או לכל הפחות
**נרמול חד-פורמט + עיגון-לרשת בכתיבה**. עד אז — כל שאילתת-טווח על 11 הטבלאות האלה חשודה.

---

## 3 · 🔴 שלוש הגדרות סותרות ל"תאריך" בין הטבלאות שכל אבחון מצליב

| מקור | טיפוס | מה ‎`::date`‎ מחזיר בפועל |
|---|---|---|
| ‎`v9_bars_5min_woodies.ts`‎ · ‎`v9_bars_5min.ts`‎ · ‎`v9_trades.entry_ts`‎ | ‎`timestamptz`‎ | **יום לפי ‎Asia/Jerusalem‎** (‎`show timezone` → Asia/Jerusalem`‎) |
| ‎`v9_day_type_state.ts`‎ | ‎`timestamp WITHOUT time zone`‎ שנכתב ‎`datetime.now(timezone.utc).isoformat()`‎ (‎`state_persist.py:70,77`‎) | **יום לפי UTC** |
| כל סקריפטי-הריפליי | ‎`(ts at time zone 'America/New_York')::date`‎ | **יום לפי ET** |

**הראיה:**

```
date(ts) [Asia/Jerusalem] on v9_bars_5min_woodies : 08-17..21 = 276,276,276,276,276
(ts at time zone 'America/New_York')::date        : 08-16=72 · 08-17..20=276 · 08-21=204
```

הפרש של **6 שעות בגבול** — כלומר ‎72‎ ברים משויכים לסשן הלא-נכון בכל שאילתה שמשתמשת
ב-‎`date(ts)`‎. ‎`prev_day.load_previous_day_context`‎ (‎`prev_day.py:47-52`‎) עושה בדיוק את זה
(‎`WHERE date(ts)=:prev_date`‎) על ‎`v9_bars_5min`‎ ומזין את ‎`pd_high/pd_low`‎ ל-S1
ואת ‎`opening_detector`‎ (OA_IN מול OA_OUT). היום זה יוצא נכון **רק במקרה** — ‎`v9_bars_5min`‎
מכילה ‎126‎ שורות/יום (חלון קצר) ולכן אין לה שורות בגבול; ברגע שהכיסוי יורחב, ‎`pd_high/pd_low`‎
יזוזו בשקט.

**מה זה כבר עשה:** הפרוב שפורסם ב-‎`S1_S2_FIRING_GAP_MAP`‎ נספח §1 —
"‎(2026-08-20, rows=39, transitions=3) · (2026-08-21, rows=36, transitions=4)‎" — רץ עם
‎`ts::date`‎ על ‎`v9_day_type_state`‎, כלומר על **חלון-UTC** שמערבב ‎20:00 ET‎ של הערב הקודם
עם היום הנמדד. ספירות-המעברים שעליהן נשענת ההערכה של ‎F6‎ אינן ספירות-סשן.

זו הפרה ישירה של **‎CLAUDE.md כלל-4** ("‎TZ ambiguity is forbidden in spec inputs‎"), והיא
**חוצה-מודולים**, לא נקודתית. בונוס: ה-TZ של ה-session הוא הגדרת-שרת **מחוץ ל-git** —
כלומר שינוי שלה (או לקוח אחר) משנה תוצאות בלי שום commit.

---

## 4 · 🟠 ‎334‎ בליעות-חריגה שקטות בנתיב-החי — והראיה למי מהן ירתה **נמחקה**

מפקד (‎`except Exception`‎ / ‎`except:`‎ שגופו **אינו** מכיל ‎log/print/raise/alert‎):

| קובץ | בליעות שקטות | מה זה יכול לאכול |
|---|---|---|
| ‎`gateway/trading_gateway.py`‎ | **65** | ‎`:4082/:4113/:4121/:4133/:4173`‎ באזור ‎`pre_send_entry_guard`‎ ⇒ **ירי**; ‎`:1309`‎ ‎`_pb_conf_ok = True`‎ ⇒ ביטול-וטו-פלייבוק בשקט; ‎`:674`‎ ‎`rr_min = 1.0`‎ ⇒ סף-RR שקט |
| ‎`services/trade_manager/bar_level_detector.py`‎ | **32** | ‎`:931/:952/:1044/:1067/:1089/:1094`‎ סביב ‎FLATTEN/MAE-scratch‎ ⇒ **יציאה** |
| ‎`systems/five_min/five_min_system.py`‎ | **27** | ‎`:762`‎ (=‎#1‎) ⇒ **שער-CVD**; ‎`:2430`‎ fail-open בשרשרת-הפליטה ⇒ **ירי** |
| ‎`services/trade_manager/manager.py`‎ | 19 | ‎`:789`‎ fail-open על BE; ‎`:1385`‎ ‎"no levels"‎ ⇒ **ניהול** |
| ‎`services/sierra_position_reconciler.py`‎ | 17 | ‎`:287`‎ בולע את **התראת-הפלאפון**, ‎`:958/:979`‎ fail-safe על בעלות ⇒ **אזעקה** |
| ‎`services/fill_poller.py`‎ | 17 | ‎`:521/:540/:561/:788/:806/:906/:913/:1079`‎ ⇒ **מילוי/יציאה** |
| ‎`systems/direction_context_live.py`‎ | 10 | ‎`:232`‎ ‎`dir_sustained = "NEUTRAL"`‎ — כישלון-DB נראה לגייטוויי כמו "אין מגמה" |
| ‎`services/trade_context.py`‎ | 10 | ‎`:703`‎ מחזיר את המסווג-הישן בשקט ⇒ **תווית-יום** |
| ‎`services/sierra_command.py`‎ | 2 | ‎`:521`‎ ‎`return None`‎ על קריאת-הפוזיציה, ‎`:540`‎ בולע את **התראת "חוזים זרים"** |
| שאר 44 הקבצים | 137 | — |
| **סה"כ** | **334** | (מתוך ‎576‎ ‎`except Exception`‎ בשלוש הספריות) |

**הפער האמיתי אינו הספירה — הוא שאי-אפשר לענות "אילו מהן ירו".**
‎`/tmp/backend.err.log`‎ הוא **942 שורות שמתחילות היום** (‎2026-08-22 18:11‎). כל
‎`grep -c`‎ ל-‎`ExitVerify`‎ / ‎`ARCHIVED`‎ / ‎`no DLL ACK`‎ / ‎`FOREIGN CONTRACTS`‎ / ‎`poll error`‎
מחזיר **‎0‎** — לא כי הם לא ירו, אלא כי ההיסטוריה אינה קיימת. זה בדיוק
‎`COWORK_DAILY_READ §3.6`‎ ("היעדר שורת-לוג ≠ פיצ'ר שבור") — ומכאן ש-**‎A7‎ (ארכוב-לוגים)
הוא תנאי-קדם לכל טריאז' של 334 הבליעות**, לא פריט-נוחות.

**המינימום שאפשר לעשות מיד:** מונה גלובלי (‎`swallow_counter[file:line] += 1`‎) שנחשף
ב-‎`/api/v9/health`‎ — הופך 334 נקודות-עיוורון ל-334 מספרים, בלי לשנות שום התנהגות.

---

## 5 · 🟠 ערוץ-ה-WARNING הוא ‎96%‎ רעש-עצמי

היסטוגרמה של ‎`/tmp/backend.err.log`‎ (‎942‎ שורות: ‎828 WARNING‎ + ‎96 INFO‎):

```
383  [woodies_chart_routes] [Woodies chart] stale export age=N > N (serving bars for display)
229  [tpo_routes]           [tpo] Sierra tpo.json stale age=N > N — serving anyway
184  [cumulative_delta_routes] [CVD] cumulative_delta.json stale: age=N > N — serving anyway
 26  [direction_context_live] [DayType] v9_day_type_state STALE … writer may be dead (SYS-2)
  1  [fill_poller] ORDER_SUBMITTED parent_id=N but no PENDING demo/live trade to map …
```

‎796‎ מתוך ‎828‎ (‎96.1%‎) הן שלוש שורות-‎"stale, serving anyway"‎ **מתוכננות** מ-3 ראוטים,
שנורות בכל פולינג של ה-frontend. ‎26‎ נוספות הן אזעקת-שווא (‎§7‎). **האזהרה
המבצעית היחידה של היום — ‎`ORDER_SUBMITTED … no PENDING trade to map`‎ — היא ‎1‎ מתוך ‎828‎.**

זו הפרה ישירה של ‎CLAUDE.md‎ ‎§Pre-LIVE‎ ("‎No silent failures … surface drift early‎"):
הכלל הוחל על ‎`logger.debug`‎, אבל התוצאה בפועל היא שה-‎WARNING‎ **הפך ל-debug**.
**התיקון הקטן:** להוריד את שלוש שורות-ה-stale ל-‎INFO‎ או לחנוק אותן (‎`_rate_limited_warn`‎
כבר קיים ב-‎`build_status/aggregator.py:84`‎) — אפס סיכון, והופך את הערוץ לקריא.

---

## 6 · 🟠 ‎`Normal_Variation`‎ — מחלקת-HLST, בכיוון ההפוך

‎`get_live_day_type()`‎ ממפה ‎`Normal_Variation → Variation`‎ **בשני מוצאיה**:
‎`trade_context.py:602`‎ ו-‎`:700`‎. גם ‎`main.py:501`‎ ממפה לאנום ‎`_DT.Variation`‎ לפני הכתיבה
ל-‎`v9_day_type_state`‎. ⇒ **המחרוזת ‎`"Normal_Variation"`‎ אינה מגיעה לאף צרכן-לייב.**
אבל ארבעה מודולים חיים מסתעפים עליה בדיוק:

| מודול | ‎`file:line`‎ | המצב |
|---|---|---|
| ‎`balance_imbalance_toggle`‎ | ‎`:37`‎ ‎`_BALANCE_TYPES = {"Balance","Neutral_Center","Neutral_Extreme","Normal_Variation"}`‎ | 🔴 **חי** (נקרא מ-‎`context_radar.py:219`‎). ‎`"Variation"`‎ **אינו** בקבוצה ⇒ ב-‎25‎ מ-‎34‎ הסשנים הקריאה לעולם לא תאמר Balance. משטח-החלטה שמייקל קורא. |
| ‎`edge_fade`‎ | ‎`:58`‎ ‎`FADE_DAY_TYPES_EXTENDED`‎ · ‎`:93-94`‎ | **מת פעמיים**: (א) המחרוזת לא מגיעה; (ב) הקורא ‎`five_min_system.py:1598`‎ בודק ‎`_ef_dt in FADE_DAY_TYPES`‎ — ה-tuple **הלא-מורחב** (‎`Normal, Neutral_Center, Neutral_Extreme`‎) ⇒ ‎`evaluate_edge_fade`‎ לא נקראת מלכתחילה. הדגלים כבויים ⇒ תיאורטי, אבל **כל ריפליי-D1 עתידי ימדוד אפס**. |
| ‎`five_min_system`‎ (‎TREND_STOP_FLOOR‎) | ‎`:1964`‎ ‎`_tsf_day_type == "Normal_Variation"`‎ | ענף "Variation עם רגל חיה" — הענף שנבנה בדיוק בשביל תקרית-08-03 — **בלתי-נגיש**. הדגל כבוי ⇒ תיאורטי היום, קטלני ביום ההדלקה. |
| ‎`day_context_extras`‎ | ‎`:142`‎ | נקרא מ-‎`classifier_core:225`‎ עם התווית הגולמית ⇒ **תקין**, לא פער. |

בנוסף: ‎`config_loader._VALID_DAY_TYPES`‎ (‎`:30-33`‎) מכיל ‎7‎ שמות ואינו כולל
‎`Normal_Variation`‎ ואינו כולל ‎`Nonconviction`‎ — בעוד ‎`daytype_classifier.py`‎ מסוגל לפלוט
את שניהם (‎`:65,:67,:327`‎), ‎`config/daytype_playbook.yaml`‎ מכיל תא ‎`Nonconviction`‎,
ו-‎`S1_NONCONVICTION_V1=1`‎ **דלוק** ב-‎`.env:271`‎ (הפלט חי; רק ההפעלה
‎`NONCONVICTION_ACTIVE_V1`‎ כבויה). הוולידטור ב-‎`:83/:138/:162`‎ פוסל שורה שלמה — או קובץ
שלם — על שם לא-מוכר, **בשקט, עם fallback לקשיח**. זו בדיוק אנטומיית-ה-HLST.

*(נבדק ונשלל: ‎`config/s2_reactive_calibration.yaml`‎ מכיל **גם** ‎`Variation`‎ **וגם**
‎`Normal_Variation`‎ ⇒ ‎`load_s2_reactive_calibration`‎ מוצא מפתח בשני המקרים. לא פער.)*

---

## 7 · 🟠 אזעקת-הקיפאון קוראת את הטבלה במקום את פעימת-הלב שנבנתה בשבילה

‎`state_persist.py:60-66`‎ מציב ‎`app_state._daytype_writer_heartbeat`‎ **בכל קריאה**, גם
כשה-write-on-change מדלג, עם הערה מפורשת: *"the watchdog reads this to distinguish
'writer alive but idle' from 'writer dead'"*.

‎`direction_context_live.py`‎ **לא קורא את זה** — הוא בודק ‎`max(ts)`‎ בטבלה, ולכן ירה היום
‎26‎ פעמים:

```
[WARNING] [DayType] v9_day_type_state STALE: last write 2026-08-21 18:50:0N (Ns ago)
          — writer may be dead (SYS-2)
```

**אימות שהכותב חי:** ‎`compute_sig()`‎ מרכיב את החתימה מ-‎(day_type, stage, round(conf,2),
lock_state)‎; ארבע השורות האחרונות של 08-21 (18:30/18:35/18:45/18:50) מראות ‎conf‎
‎0.08→0.00→0.25→0.33‎ ואז יציבות — כלומר **write-on-change דילג כדין**.
⇒ **קורא-בלי-כותב הפוך:** נבנתה פעימת-לב, אף אחד לא צרך אותה, והתוצאה היא אזעקת-שווא
מובטחת בכל ערב שקט. במחלקה שבה כבר היו ‎113‎ אזעקות-אורפן-שווא (T5, 08-16), זו בדיוק
המכניקה שמאמנת אותנו להתעלם.

---

## 8 · 🟡 מסלולי-נתונים מתים — סריקה של כל ‎51‎ טבלאות ‎`v9_*`‎

| ממצא | ראיה | סוג |
|---|---|---|
| ‎`v9_tpo_bars`‎ — **שורה אחרונה ‎2023-11-25 23:55‎** (‎5,605‎ שורות), ובכל זאת ‎`build_status/bridge_inspector.py:38`‎ מנטרת אותה כזרם-חי (‎`("tpo","v9_tpo_bars","ts",360,False)`‎) | ‎`max(ts)`‎ | **קורא-בלי-כותב** ⇒ משבצת-זרם באדום-מושתק לנצח ב-StreamHealthPanel |
| ‎`v9_bars_30min_woodies`‎ — ‎373,750‎ שורות, נכתבת ב-‎`api/v9/bars.py:1172`‎, **אפס קוראים** בכל ה-backend, קפואה מ-‎2026-07-02‎ | grep + ‎`max(ts)`‎ | **כותב-בלי-קורא** |
| ‎12‎ טבלאות ‎`v9_*`‎ עם ‎0 שורות‎ שיש להן מודל ואין להן לא-כותב-ולא-קורא: ‎`v9_five_min_state`‎ · ‎`v9_account_status`‎ · ‎`v9_killzone_log`‎ · ‎`v9_woodies_patterns`‎ · ‎`v9_system_markers`‎ · ‎`v9_chop_score`‎ · ‎`v9_bars_woodies`‎ · ‎`v9_bars_stacked_imbalance`‎ · ‎`v9_daily_quality_reports`‎ · ‎`v9_build_status_archive`‎ · ‎`v9_audit_events`‎ · ‎`v9_system_configs`‎ | ‎`count(*)=0`‎ + grep | סכימה-מתה |
| ‎`v9_footprint_journal.ts`‎ מכיל ‎`1780663879`‎ — **מספר-epoch** בעמודה שכל שאר הקוד מתייחס אליה כמחרוזת-ISO | ‎`max(ts)`‎ | אי-התאמת-טיפוס בתוך ‎#2‎ |
| ‎`v9_tpo_sessions.range_high/range_low`‎ = ‎`NULL`‎ ב-**כל 13 הסשנים** מ-08-05 ואילך, בעוד ‎`ib_high/ib_low/poc/vah/val`‎ מלאים | ‎`select … where session_type='CASH'`‎ | ‎`prev_day.py:67`‎ ניצל ב-‎`or bars_high`‎ — אבל ‎`key_levels_routes.py:224`‎ מפרסם ‎`range_high`‎ כ-‎`sierra.tpo.prior_day`‎ ⇒ **שדה-UI ריק שמוצג כמקור-אמת** |
| ‎`tpo_history_snapshotter`‎ מודיע בעלייה ‎`db=/…/data/mems26_local.db`‎ (‎`:73-76`‎, ‎`V9_DB_PATH`‎) — נתיב ה-SQLite | שורת-לוג היום | ‎`v9_tpo_history`‎ ב-PG **כן** טרייה (‎08-21 19:30‎) ⇒ הנתונים בסדר, **הלוג משקר**. אותה מחלקה: ‎`trading_gateway.py:14,198-199`‎ עדיין ‎`import sqlite3`‎ ו-‎`DB_PATH="./data/mems26_local.db"`‎; קובץ ה-SQLite בן ‎446MB‎ עדיין על הדיסק, mtime ‎08-20‎ |

---

## 9 · שני פערים נוספים, ראויים לרישום

**9א · ‎`drain_command_queue`‎ — חסימת-ראש-תור על פקודה מגֵנה.**
‎`sierra_command.py:234-241,286-298`‎: פקודה שנשלחה ולא קיבלה ACK **עוצרת את הניקוז**
(‎`STOP draining`‎) עד ‎`SIERRA_CMD_ACK_GRACE_S=15`‎, ואז מאורכבת ל-‎`archived_stale/`‎
עם ‎WARNING‎ ו**לעולם לא נשלחת שוב** ("no ACK is indistinguishable from executed").
בהינתן ‎`SIERRA_CMD_TTL_S=90`‎, ‎`FLATTEN_ACCOUNT`‎ שנכנס מאחורי פקודה תקועה יכול
לחכות ‎15ש'‎ ואז — אם הוא עצמו לא מקבל ACK — **להיעלם בשקט**. אין הבחנה בין ‎op‎
מגֵן ל-‎op‎ רגיל, ואין פוש-פלאפון על ארכוב. תיאורטי (אפס ‎`ARCHIVED`‎ בלוג — אבל הלוג בן יום).

**9ב · מדיניות-מטמון סותרת ב-‎`config_loader`‎.**
‎`load_s2_firing`‎ (‎:281‎) ו-‎`load_s2_reactive_calibration`‎ (‎:335‎) שומרים במטמון **לצמיתות**
(ה-reset מסומן "for testing only"), בעוד ‎`load_auth_matrix`‎ (‎:60‎) · ‎`load_targets`‎ (‎:120‎) ·
‎`load_pattern_t1_points`‎ (‎:176‎) · ‎`load_stop_params`‎ (‎:214‎) · ‎`load_stop_anchors`‎ (‎:355‎)
קוראים מהדיסק **בכל קריאה**. ⇒ עריכת YAML באמצע-סשן משנה **חצי** מהמערכת מיידית
ואת החצי השני בכלל לא, **בלי שורת-לוג לאף כיוון**. זה סותר את הפסיקה
"config-tunable stop/exits/contracts — הכל YAML בלי קוד": אי-אפשר לענות על
"האם העריכה שלי נכנסה לתוקף".

---

## 10 · מה נבדק ו**נשלל** (כדי שלא ייחקר שוב)

* ‎`prev_day.py`‎ ‎`db_path=DEFAULT_DB_PATH`‎ (נתיב SQLite) — **פרמטר שיורי**; הפונקציה משתמשת
  ב-‎`read_one`‎ מנועי (PG). לא פער. *(ה-‎`date(ts)`‎ שבתוכה כן פער — ‎§3‎.)*
* ‎`v9_day_type_state`‎ "הכותב מת ב-18:50 ב-08-21" — **לא**. write-on-change + חתימה
  שלא זזה. אומת מול ‎`compute_sig`‎ ומול ארבע השורות האחרונות. *(האזעקה כן פער — ‎§7‎.)*
* ‎`load_s2_reactive_calibration`‎ ואי-התאמת ‎`Variation`/`Normal_Variation`‎ — ה-YAML מכיל
  **את שני המפתחות**. לא פער.
* ‎`bridge_inspector._parse_ts`‎ מניח ש-‎`v9_bars_5min`‎ נאיבית-ET בעוד היא ‎`timestamptz`‎ —
  שפיר היום (הדרייבר מחזיר aware עם offset ⇒ ענף-ה-ET לא נכנס), אבל מלכודת רדומה בתוך ‎§3‎.

---

## נספח · פקודות (‎Rule 5‎)

```bash
# §1 — ההוכחה: חסם-הייצור מול חסם-ISO על 76 חלונות של 08-21
python3 - <<'EOF'
import psycopg2, datetime as dt
cn=psycopg2.connect("postgresql://localhost/mems26"); cn.set_session(readonly=True, autocommit=True); cu=cn.cursor()
cu.execute("""select ts from v9_bars_5min_woodies
 where (ts at time zone 'America/New_York')::date='2026-08-21'
   and (ts at time zone 'America/New_York')::time between '09:30' and '16:00' order by ts""")
bars=[r[0].astimezone(dt.timezone.utc) for r in cu.fetchall()]
for name, fmt in (("str(datetime)", str), ("isoformat()", lambda d: d.isoformat())):
    zero=sum(1 for i in range(3,len(bars))
             if (cu.execute("select count(*) from v9_bars_cumulative_delta where ts>=%s and ts<=%s",
                            (fmt(bars[i-3]), fmt(bars[i]))) or cu.fetchone()[0])==0)
    print(name, "-> rows==0 on", zero, "/", len(bars)-3)
EOF

# §2 — טיפוסי ts + שורות מחוץ לרשת
psql postgresql://localhost/mems26 -c "select table_name,column_name,data_type
 from information_schema.columns where table_schema='public' and table_name like 'v9_%'
 and column_name in ('ts','bar_ts') and data_type='character varying' order by 1"
psql postgresql://localhost/mems26 -c "select count(*) from v9_bars_cumulative_delta
 where substring(ts from 15 for 5) not in ('00:00','05:00','10:00','15:00','20:00','25:00',
 '30:00','35:00','40:00','45:00','50:00','55:00')"      -- 1714 / 5219

# §3 — שלוש ההגדרות של 'תאריך'
psql postgresql://localhost/mems26 -c "show timezone"    -- Asia/Jerusalem
psql postgresql://localhost/mems26 -c "select date(ts) d,count(*) from v9_bars_5min_woodies
 where ts>='2026-08-17' group by 1 order by 1"
psql postgresql://localhost/mems26 -c "select (ts at time zone 'America/New_York')::date d,
 count(*) from v9_bars_5min_woodies where ts>='2026-08-17' group by 1 order by 1"

# §5 — היסטוגרמת ה-WARNING
sed -E 's/^[0-9-]+ [0-9:]+ //' /tmp/backend.err.log | sed -E 's/[0-9]+\.[0-9]+/N/g; s/[0-9]{3,}/N/g' \
  | sort | uniq -c | sort -rn | head -6

# §8 — טריות כל טבלאות v9_*
psql postgresql://localhost/mems26 -c "select max(ts) from v9_tpo_bars"          -- 2023-11-25
psql postgresql://localhost/mems26 -c "select max(ts) from v9_bars_30min_woodies" -- 2026-07-02
psql postgresql://localhost/mems26 -c "select trading_date,range_high,range_low,ib_high
 from v9_tpo_sessions where session_type='CASH' and trading_date>='2026-08-05' order by 1"
```

*בוצע READ-ONLY ב-2026-08-23 ע"י cowork-dev/agent. לא שונו קוד-רץ, דגל, `.env`, DB או שירות.*
