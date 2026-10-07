# T-526 · הכותב של דריסת-הברים ב-`v9_bars_5min_woodies` — נמצא, תוקן בשורש, ושומר-דגל-כבוי נבנה

**נכתב:** 2026-10-08 00:10 IL · fix-agent (סוכן-הכיול 23:40, ריצה ראשונה שמשאירה תוצרים) · BRIEF §3.2 (חזרה #2; §3.1 T-259 חסום לסוכן-לילה — `launchctl` אסור, ממתין ללחיצת-מייקל + חלון-שבת)
**סוג-עבודה:** (ג) תיקון-באג מתועד (הדוקסטרינג "Keep this in sync with base_stream.py" לא התקיים) + (ב) בניית-דגל-כבוי (`WOODIES_CLOSED_BAR_GUARD_V1`, ברירת-מחדל זהה-בייט) + מבחן-רגרסיה עם ה-CSV של 01.10.
**אפס נגיעה:** `.env` · `RULED_FLAGS` · העץ החי · LaunchAgents · DB (SELECT בלבד) · ריסטארט. הבקאנד pid 49501 לאורך כל הריצה.

## 1 · הממצא — מי כתב 19:xx על 18:xx, ולמה בדיוק 12 ברים

**הכותב: ה-backfill ההיסטורי של הגשר בעלייה** — `bridge/v9_history.py::historical_load`, שרץ **בכל התחלה של הגשר** לכל זרם (`base_stream.py:196`, "Historical backfill before going live"), קורא את `woodies_5min.json` (50 ברים אחרונים + current_bar) ודוחף אותו ל-`POST /api/v9/bars/woodies_5min`.

**השורש (+4h במקום +5h):** ה-DLL מייצא `ts` כשעון-הקיר של הצ'ארט מקודד כ-UTC. הזרם החי (`bridge/v9_streams/base_stream.py:80`) מפרש אותו לפי `V9_CHART_TZ` — ב-`.env:337` **`America/Chicago`** (וה-plist של הגשר מייצא את זה; `boot V9_CHART_TZ=America/Chicago` בלוג-העלייה) ⇒ **+5h** (CDT). ה-backfill ההיסטורי (`v9_history.py:43/48`) החזיק את האזור **קשיח `America/New_York`** ⇒ **+4h** (EDT) — ניו-יורק מקדימה את שיקגו בשעה כל השנה ⇒ **כל בר ב-history נדחף שעה מוקדם**. הדוקסטרינג באותו קובץ אומר "Keep this in sync with base_stream.py:_fix_chicago_bar_ts" — ולא התקיים מאז ש-`V9_CHART_TZ` נוסף לזרם החי.

**הרגע:** ריסטארט-הלילה של cowork ב-01.10 (`LIVE_CHANNEL` 23:04–23:11): backend עלה ראשון (pid 89459, 23:06), **הגשר ב-23:07:47** (`kickstart com.mems26.bridge → pid 89751 · boot V9_CHART_TZ=America/Chicago 23:07:47`) — בתוך החלון שנרשם ב-T-526 (20:47–23:14).

**למה בדיוק 12 ברים (18:00–18:55):** באותו רגע `woodies_5min.json` החזיק 50 ברים = **19:00–23:05 IL**. ה-backfill כתב אותם תחת **18:00–22:05** (−1h) דרך `INSERT … ON CONFLICT (ts, symbol) DO UPDATE` (`safe_writer._sqlite_to_pg_upsert` מעדכן את כל העמודות). שניות אחר-כך הדחיפה **החיה** הראשונה של אותו גשר (המרה נכונה, +5h) כתבה את אותם 50 ברים תחת 19:00–23:05 ⇒ תיקנה בחזרה את 19:00–22:05 — **והשארית = 18:00–18:55 = 12 ברים בדיוק.** זה מסביר גם למה `created_at` נשאר 18:00:04 (ON CONFLICT לא נוגע בו) ולמה שדות-ה-studies/proj/lsma_above_price של 18:xx = של 19:xx (`harness_out/t524/woodies_1800_1855_before_restore.csv` מול השורות של 19:xx ב-DB — זהות שדה-שדה: `cci_14 108.49/107.61/64.48…`, `proj_hi 7808.25`, `lsma_above_price 1` ב-18:50/18:55).

**למה השערים הקיימים לא תפסו:** `TS_OFFSET_INGEST_GATE_V1=1` דוחה רק אצווה **מתקדמת** (`newest > prev`) שמפגרת >900s — אחרי ריסטארט-backend `_prev is None` ⇒ הדחיפה הראשונה עוברת תמיד; וגם בלי ריסטארט, אצווה שכולה −1h היא "לא-מתקדמת" מול הדחיפה הקודמת ⇒ עוברת. `WOODIES_TS_HOUR_FIX=0`, `TS_WHOLE_HOUR_NORMALIZE_V1=0` (כבויים בפסיקה), ו-`BAR_SEAM_REJECT_V1` משווה רק רצף-מחירים מול השכן (הנתונים המוזזים רציפים).

**למה לא קרה שוב ב-02.10 10:14** (הריסטארט הבא, הראיה בלוג הנוכחי `/tmp/bridge.err.log` שמתחיל שם): `[woodies_5min] History: loading from file (age=9.9h, export_ts=1790889477)` (= 01.10 23:17:57 IL) — אבל הבקאנד היה למטה (`Connection refused` לכל הזרמים) ⇒ הדחיפה נכשלה ⇒ אפס דריסה. **כלומר הסכנה חוזרת בכל ריסטארט-גשר שבו הבקאנד כבר למעלה** — כולל ריסטארט-שבת.

## 2 · אימות שהדריסה אינה נמשכת (T-526 צעד 2)

```raw
psql: SELECT ts,low,high,close FROM v9_bars_5min_woodies WHERE ts BETWEEN '2026-10-01 18:00+03' AND '2026-10-01 18:55+03'
  ⇒ 12 שורות, זהות ל-harness_out/t524/woodies_1800_1855_after_restore.csv (low/high/close שורה-שורה, 18:00 7677.75/7690.75/7680.25 … 18:55 7681.25/7694/7691.5)
max(ts) v9_bars_5min_woodies ⇒ 2026-10-07 23:45:00+03 (גיל 2 דק' ב-23:47) · 78 ברים/יום 16:30–22:55 ל-01.10, 02.10, 05.10, 06.10, 07.10
```
⇒ השחזור החלקי של 01.10 23:24 עומד; הכותב אינו פעיל בין ריסטארטים (הוא רץ רק בעלייה).

## 3 · מה נבנה (קוד + מבחן), בלי להדליק

| # | קובץ | מה | ברירת-מחדל |
|---|---|---|---|
| 1 | `bridge/v9_history.py` | **תיקון-שורש:** האזור נקרא מ-`V9_CHART_TZ` עם אותה ברירת-מחדל (`America/New_York`) כמו הזרם החי — ה-backfill ממיר בדיוק כמו הזרם (+5h על המק הזה). | `V9_CHART_TZ` לא מוגדר ⇒ התנהגות זהה להיום. **נכנס לתוקף רק בעליית-הגשר הבאה** (אין ריסטארט בלילה; חלון-שבת / cowork). |
| 2 | `backend/v9/api/v9/bars.py` | **קו-הגנה שני (BRIEF §3.2 "UPSERT רק אם זהה"):** `WOODIES_CLOSED_BAR_GUARD_V1` — בר **סגור** (מבוגר מ-`WOODIES_CLOSED_BAR_SEC`=900s לפי שעון-השרת) שכבר מאוחסן **לא נכתב מחדש ב-OHLC שונה**: השורה נשמרת, הבר מדולג, שורת-ERROR אחת לדחיפה (`CLOSED-BAR-OVERWRITE REFUSED n/N bars (T-526): payload ts … export_ts … server_now … newest-bar lag …` + 3 דוגמאות = "לוג-הכותבים"), `refused_closed` בתשובה, ו-current_bar שנדחה לא מנותב ל-S4. בר-מתהווה / בר-שזה-עתה-נסגר ממשיכים להתעדכן; דחיפה-חוזרת זהה ובר חדש נכתבים כרגיל; קריאה אחת ל-DB לדחיפה (לא לבר). | **OFF** ⇒ `_cbg_stored is None` ⇒ אף שורה לא רצה; התשובה זהה-בייט. |
| 3 | `tests/v9/regression/test_t526_history_tz_and_closed_bar_guard.py` | 5 מבחנים: (א) ה-backfill ממיר כמו הזרם החי ל-Chicago (+5h) ול-New_York (+4h), וברירת-המחדל ללא הדגל = New_York (= הקוד הישן); (ב) **דגל כבוי = ההתנהגות של 01.10**: 12 הברים המוזזים (ה-CSV) נכתבים, השומר לא נקרא, התשובה ללא `refused_closed`; (ג) **דגל דלוק = הדריסה של 23:07:47 נדחית**: 0 כתיבות, 0 ניתוב, `refused_closed=12`, שורת-הלוג; (ד) דחיפה זהה + בר חדש נכתבים (13/13, 0 דחיות); (ה) חוקי-הסף (מתהווה/סגור/זהה/סובלנות/`WOODIES_CLOSED_BAR_SEC`/ts לא-מספרי). | — |

```raw
$ set -a; source .env; set +a; python3 -m pytest -q tests/v9/regression/test_t526_history_tz_and_closed_bar_guard.py \
    tests/v9/regression/test_ts_offset_ingest_gate.py tests/v9/regression/test_g1_current_bar_paint.py tests/v9/regression/test_bar5_channel_failover.py
  ⇒ 5 passed (T-526) · כל השאר ירוקים
$ python3 scripts/flag_guard.py ⇒ FLAG-GUARD: PASS — all 274 ruled flags match.
```
**כישלונות קיימים-מראש (לא שלי, אומתו על HEAD נקי ב-`git worktree` זמני):** `tests/v9/api/test_bars_woodies_routing.py` ×2 (מצפים ל-`_route_bar` פעם אחת; מאז failover-'5min' של 14.08 הוא נקרא פעמיים) · `tests/v9/bridge/test_streams.py::test_push_api_posts_latest_bar_array` · `tests/v9/db/test_api.py` ×3 (כתיבת-PG תחת pytest נדחית ע"י T-542). נרשם, לא תוקן.

## 4 · מה דורש פסיקה / מה נשאר פתוח

1. **הדלקת `WOODIES_CLOSED_BAR_GUARD_V1=1`** — שינוי `.env` ⇒ פסיקת-מייקל + snapshot + RULED_FLAGS + flag_guard + ריסטארט (חלון 12:00–14:30 או שבת). מחיר: קריאה אחת נוספת ל-DB בכל דחיפת-woodies (כל ~2–3 שנ'); תועלת: גם ריסטארט-גשר עם גשר ישן, גם כל כותב עתידי, לא ידרוס בר סגור בשקט. **לא דחוף** אם #2 מתבצע — תיקון-השורש בגשר סוגר את המקרה שקרה.
2. **אימות תיקון-השורש בתנאי-המקור** = בעליית-הגשר הבאה (שבת): `grep "History: loading" /tmp/bridge.err.log` + `psql` שהברים שלפני חלון-50 לא השתנו (למשל 12 ברים שעתיים לפני העלייה, `SELECT … ` לפני/אחרי). עד אז הסטטוס: **תוקן — ממתין לאימות**.
3. **ריסטארט-גשר כשהבקאנד למעלה ועדיין על הקוד הישן = דריסה חוזרת** (12–50 ברים, מחוץ לחלון-50 של הזרם החי). עד שהגשר עולה עם הקוד החדש: להעלות את הגשר **לפני** הבקאנד (כמו ב-02.10) או `V9_SKIP_HISTORY=1` בעלייה — הערה ל-cowork לחלון-שבת, לא פעולה שלי.
4. **t523smoke של 01.10** (T-526 צעד 3) — הטבלה אומתה (סעיף 2) ⇒ אפשר להריץ מחדש בלילה הבא; לא הורץ הלילה (ההרנס של T-564 תפס את החלון).
5. **לא תוקן בכוונה:** `safe_writer` / `ON CONFLICT` לא רוככו (T-526 ⛔) — השומר יושב בנקודת-הכתיבה של הזרם ודוחה בקול, לא משנה את ה-upsert. `WoodiesSystem._persist_bar` (הכותב השני, `woodies_system.py:1427`) כותב רק ב-LIVE mode ולא נמצא מעורב (zlr=1 בשורות הדרוסות — הוא כותב תמיד 0/NONE); לא נגעתי בו.
