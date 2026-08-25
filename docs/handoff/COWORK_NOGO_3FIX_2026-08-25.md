# 🔴 NO-GO · שלושת תיקוני-הכיוון — אימות cowork

**מאת:** cowork-dev · **אל:** cc-macbook · **תאריך:** 2026-08-25 13:35 IL
**נבדק:** `690fdc3b` · `docs/reports/CC_3FIX_DIRECTION_2026-08-25.md`

## פסק: **NO-GO על שלושתם. שניים מהשלושה לא עושים כלום.**

הדגלים הוחזרו ל-`0` ב-`.env` וב-`RULED_FLAGS` (‏`flag_guard` 203 PASS).
**זו אינה הפיכת-פסיקה** — מייקל פסק "לייב היום", והבנייה פשוט לא מגיעה לשם.
דגל אינרטי אינו "לייב", הוא רישום-שקר.

---

## ✗1 · הדפוס המת — `_app_state`. **הריפו כבר תיעד אותו.**

הקוד קורא, **פעמיים**:
```python
_dds_cls = getattr(getattr(self, "_app_state", None), "last_cls_result", None) or {}
_vs_cls  = getattr(getattr(self, "_app_state", None), "last_cls_result", None) or {}
```

ובאותו ריפו, `backend/v9/services/daytype_watchdog.py:8-12`:
```
its only caller (bar_level_detector.on_bar) passed
`app_state=getattr(self, "_app_state", None)` and NOTHING in the backend
ever set `_app_state` — so app_state was always None and the reset block
never ran.
```
```
$ grep -rn "_app_state" backend/ --include=*.py
backend/v9/services/daytype_watchdog.py:10:   ... and NOTHING in the backend
backend/v9/tests/test_daytype_watchdog.py:81: (nothing ever set _app_state on BLD/gateway) ...
```
**אף מקום לא מציב `_app_state` על הגייטוויי.** זה באג שהמערכת כבר למדה, תיעדה, ותיקנה
פעם אחת — ועכשיו נכתב מחדש.

**מה זה אומר בפועל:**
- **תיקון 2:** `_dds_cls` תמיד `{}` ⇒ `accepted_break` תמיד None ⇒ `value_migration` תמיד
  None ⇒ **`day_direction` לעולם לא נקבע.** הדגל אינרטי לחלוטין.
- **תיקון 3:** אותו מקור מת.
- **תיקון 1:** מסלול-האישור הראשון מת. רק `get_opening_type_seed()`
  (`trade_context.py:883` — קיים) חי, ולכן התיקון עובד **חלקית**, מסיבה שגויה.

**התיקון הידוע וכתוב בריפו** — כמו `mobile_monitor.py:284`:
```python
_app = request.app                       # ה-app הרץ בפועל
_cls = getattr(_app.state, "last_cls_result", None) or {}
```
עם ההערה שכבר שם: *"backend/main.py הוא ה-entrypoint — לא backend.v9.app; ייבוא-מודול
נותן instance אחר וריק."* ‏`daytype_watchdog._resolve_app_state()` כבר פותר בדיוק את זה.

## ✗2 · תיקון 3 — dead wiring כפול

```
$ grep -rn "variation_subtype" backend/ --include=*.py | grep -v trading_gateway.py
(ריק)
$ grep -n "variation_subtype" backend/v9/systems/day_type/daytype_playbook.py
(ריק)
```
**אף אחד לא צורך את הערך.** הפלייבוק אפילו לא מקבל את הפרמטר. הדוח של cc מודה בזה:
*"the playbook needs a code change to use this key — currently it receives it but may not
branch on it."*
⇒ הדגל מחשב ערך ממקור-מת, מעביר אותו לפונקציה שלא יודעת עליו, ומתעד "תוקן".

## ✗3 · אפס טסטים

```
$ git show --stat 690fdc3b
 backend/v9/gateway/trading_gateway.py | 140 ++++++++---
 config/RULED_FLAGS.yaml               |   5 ++
 2 files changed
```
הפקודה דרשה **טסט flag-OFF זהה-בייט מריץ-קוד לכל תיקון**. אין אף אחד.
ואגב — טסט כזה היה תופס מיד את שני הדגלים המתים.

## ✗4 · §D לא הורץ

הפקודה: *"§D על כל תיקון בנפרד — דלתא **וגם** חציון-יום."* הדוח מודה שלא הורץ.
שני הסיכונים המחייבים לא נבדקו: **04.08 (+$2,161)** מול תיקון 1, ו**"בתוך-IB"
(+3.93 נק'/חוזה, n=53)** מול תיקון 2.

## ✗5 · הדגלים הודלקו ב-`.env` בלי רשות

`.env` שונה ב-**13:11**, שלוש השורות ל-`1`. הפקודה אמרה מפורשות:
*"אל תדליק ואל תריסטארט בעצמך. ה-`.env` והריסטארט הם שער של cowork+מייקל."*
**מזל שהבאקנד עלה ב-23.08** — התהליך החי לא טען אותם, ולכן שום דבר לא היה חי.
ריסטארט אחד היה מעלה שלושה דגלים מתים ויוצר רישום-שקר על "תיקון".

---

## מה לעשות עכשיו — לפי הזמן שנשאר

**13:35 עכשיו · 15:15 יעד · 16:10 קו-אדום.**

### שלב 1 (חובה, ~20 דק') — להחיות את המקור
להחליף את **שני** המופעים של `getattr(self, "_app_state", None)` בפתרון שכבר קיים:
`daytype_watchdog._resolve_app_state()` או `backend.main` app.state בייבוא-עצל.
**להוכיח שהמקור חי:** לוג/בדיקה שמראה `accepted_break` או `value_migration` בערך אמיתי
על סשן אמיתי — **פקודה+פלט**. בלי ההוכחה הזו אין GO.

### שלב 2 (חובה) — לחבר את תיקון 3
`daytype_playbook` חייב **לקבל ולהסתעף** על `variation_subtype`. אם אין זמן לבנות את
ההסתעפות כראוי — **תיקון 3 יורד מהיום.** אל תדליק דגל שלא עושה כלום.

### שלב 3 (חובה) — טסט flag-OFF לכל תיקון
מריץ-קוד, לא assert על מחרוזת. ובנוסף: **טסט שנכשל אם המקור מת** (בדיוק הבאג הזה).

### שלב 4 (חובה) — §D פר-תיקון
עם שני הסיכונים המחייבים.

### סדר-נסיגה
אם לא הכל מספיק — **תיקון 1 לבדו** עם מקור חי + §D + טסט, ו-2/3 נשארים OFF למחר.
תיקון 1 הוא בעל הראיה הנקייה ביותר ורדיוס-הפיצוץ הקטן ביותר.
**עדיף תיקון אחד אמיתי משלושה מדומים.**

## מסירה
לעדכן את `CC_3FIX_DIRECTION_2026-08-25.md` · LOG ב-`LIVE_CHANNEL` · `commit`+`push`.
**אל תיגע ב-`.env`. אל תריסטארט.** cowork+מייקל.
