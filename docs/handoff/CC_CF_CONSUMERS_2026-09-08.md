# מפרט · 08.09 — שני צרכני תקרה/רצפה כפולה · **אחרי הפתיחה, לא לפניה**

**מאת:** cowork-dev · **אל:** cc-macbook · **‏`--re d6d31562`** ·
**פסיקת-מייקל 08.09 08:30: "כן" — לבנות את שני הצרכנים החסרים.**

**‏🔴 עיתוי: לא לגעת עד 20:00.** מ-15:00 המערכת קפואה לפתיחה. הבנייה מתחילה אחרי הסגירה.

---

## הרקע — מה קיים ומה חסר

```
ceiling_floor_state.py         detect_ceiling_floor()  →  {"state":"CEILING_FAILED"|"FLOOR_FAILED",
                                 "p1","p2","confirm_level"(=הצוואר),"edge_source","key",...}
five_min_system.py:1514-1524   "detection and reporting half ONLY. It places no order, moves no
                                stop, blocks no entry and never touches route_setup."
CEILING_FLOOR_STATE_V1=shadow  · CEILING_FLIP_SHORT_V1=shadow  (הצרכן השלישי — קיים, בצל)
```
**שלושת הצרכנים שהמפרט המקורי (‏28.08) הגדיר — שניים לא נבנו:**

| | | מצב |
|---|---|---|
| ‏א | **לבנק את הלונג** — תקרה כפולה כשאנחנו LONG ⇒ להדק/לממש | **חסר** |
| ‏ב | **לנעול את הקצה** — לא לפתוח לונג חדש מתחת לתקרה שנכשלה | **חסר** |
| ‏ג | **להתהפך** (`ceiling_flip.py`) | קיים, `shadow` |

## ‏🔴 המגבלה שקובעת את כל התכנון — אין יציאה חלקית

`op=EXIT` **שבור** (פסיקה עומדת ב-CLAUDE.md): כל חוזה יוצא עם OCO צמוד ⇒ אין חוזה חופשי ⇒ `r=-1`.
**מה שכן עובד: `MODIFY_STOP` · `MODIFY_TARGET` · ‏T1/T2/T3 (OCO של סיירה) · `FLATTEN_ACCOUNT`.**

**⇒ "לבנק את הלונג" חייב להיות מנוסח כהידוק-סטופ ו/או משיכת-יעד — לא כמימוש חלקי.**
כל מפרט שאומר "לצאת מחצי" הוא בלתי-ניתן-למימוש היום. אל תנסה. אל תחווט ל-`_emit_exit`.

---

## ‏א · `CF_BANK_LONG_V1` — הידוק על תקרה כפולה נגד הפוזיציה

**טריגר:** `detect_ceiling_floor` מחזיר `CEILING_FAILED` **ויש פוזיציה חיה LONG**
(‏`FLOOR_FAILED` + SHORT = המראה). **פעולה — לפי הסדר, ורק מה שמותר:**

1. **סטופ ל-BE** אם `entry < price` ו-`stop < entry` ⇒ `MODIFY_STOP` ל-`entry` (או `entry+1T`).
   **המנגנון קיים** — `SYSTEM6_AUTOCORRECT=protective` כבר פולט `MODIFY_STOP` בלבד.
2. **סטופ מתחת לצוואר** אם הצוואר (`confirm_level`) גבוה מ-BE ⇒ `MODIFY_STOP` ל-`confirm_level − 2T`.
   **לעולם לא להרפות סטופ** — הידוק בלבד, כיוון-אחד, בדיוק כמו `RUNNER_TRAIL`.
3. **‏`MODIFY_TARGET` — לא בגרסה הראשונה.** ‏§4 (`STOP_MOVE_TARGET_RESTORE_V1`) עדיין `0` בגלל
   הגדרת-סיירה *Maintain Same Offset*; משיכת-יעד תגרור את הסטופ אחריה. **אחרי שמייקל מכבה אותה.**

**דגל:** `CF_BANK_LONG_V1` (default OFF; **`shadow` = לוג בלבד, אפס `MODIFY_STOP`**).
**קבלה:** ריפליי 11 יום — כמה `CEILING_FAILED` קרו כשפוזיציה חיה, ומה **‏Σpt** של הידוק-מול-לא-הידוק
(‏MFE שנשמר מול הסטופ שהיה). **בלי שורת-Σ זה NOT-DONE.**

## ‏ב · `CF_EDGE_LOCK_V1` — וטו-כניסה מתחת לקצה שנכשל

**טריגר:** אחרי `CEILING_FAILED` — כל setup **LONG** שה-`entry` שלו בין `confirm_level` ל-`p2`
(כלומר קונה לתוך התקרה) ⇒ `blocked_by="cf_edge_lock"`. **פג-תוקף** כשמחיר סוגר מעל `p2 + 2T`
(התקרה נפרצה ⇒ אינה תקרה), או בסוף הסשן.

**זה שער — ולכן הזהירות הכפולה:** ‏`awaiting_release` ו-`entry_not_confirmed` הראו בריפליי
שהם **מגנים** (‏−$416 / −$776 כשמכבים), אבל שער חדש הוא **חוסם-רווח פוטנציאלי**.
**חובה: `shadow` תחילה — לספור כמה כניסות הוא היה חוסם ומה ה-Σ שלהן.** אם הוא חוסם מנצחות — לא עולה.

**דגל:** `CF_EDGE_LOCK_V1` (default OFF; `shadow` = `logger.info` + רישום, **בלי `blocked_by`**).

## ‏ג · `CEILING_FLIP_SHORT_V1` — למדוד לפני שמדליקים

קיים ב-`shadow` מ-02.09 (‏T-140) — **ואין לי מספר.** ריפליי 11 יום + `Σpt` **לפני** שמייקל נשאל
אם להדליק. **אל תבקש ממנו פסיקה בלי המספר.**

---

## סדר ותנאים

**‏1. ריפליי לשלושתם (מדידה בלבד) → 2. `Σ` ל-`RULED_FLAGS` → 3. בנייה ב-`shadow` → 4. שבוע צל → 5. פסיקת-מייקל.**

**כל אחד מהם נבנה כמתודה `_maybe_cf_*` ליד `_maybe_ceiling_floor_state`** — **לא** בתוך קן
`FIRST_HOUR_TACTICAL`/`OPENING_ENTRY_V1`. `tests/v9/regression/test_detector_placement.py`
יאכוף את זה: **הוסף את שני הדגלים החדשים ל-`ALL_SESSION_DETECTORS` באותו קומיט.**

**טסט לכל אחד:** דרך המתודה האמיתית (הדגם: `test_re_acceptance_production_path.py`) — לא
דרך הפונקציה הפנימית — **ומוטציה שמפילה.**

## אסור

לגעת בקוד לפני 20:00 · `_emit_exit`/`write_exit`/`op=EXIT` בשום צורה · להרפות סטופ · `MODIFY_TARGET`
לפני שמייקל מכבה את *Maintain Same Offset* · להדליק ל-`1` · לבקש פסיקה בלי שורת-ריפליי.
