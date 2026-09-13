# §2 · מפקד `[S1-BINARY]` ל-13.09 — עם ביקורת-חיובית

**מי:** `cc-night(cowork-subagent)` · **מתי:** 2026-09-13 23:25-23:27 IL (יום א', שוק סגור).
**הלוג:** `/tmp/backend.err.log` (‏**לא** `backend.log`) — `63,391,481` בתים, `414,036` שורות.

## צורת-השורה (נקראה, לא נוחשה)

```
$ grep -m3 "S1-BINARY" /tmp/backend.err.log
2026-09-11 17:30:05 [WARNING] [mems26] [S1-BINARY] EVENT=acceptance_UP: Normal→Normal (old=Normal) transitions=1 bar=13
2026-09-11 17:35:04 [WARNING] [mems26] [S1-BINARY] EVENT=round_trip_open: Normal→Normal (old=Normal) transitions=1 bar=14
2026-09-11 17:45:02 [INFO]    [mems26] [S1-BINARY] HELD Normal (old would flip to Normal_Variation) bar=16
```

⇒ התאריך מעוגן בתחילת-שורה ⇒ `^2026-09-13` / `^2026-09-11` תקפים.

## המפקד — אותו פרסר בדיוק לשני הימים

```
$ for D in 2026-09-13 2026-09-11; do N=$(grep -c "^${D}.*\[S1-BINARY\]" /tmp/backend.err.log); echo "DENOM ${D} = ${N}"; done
DENOM 2026-09-13 = 0
DENOM 2026-09-11 = 9          ← ביקורת-חיובית: יום-מסחר, אותו פרסר, >0
```

**⇒ האפס של 13.09 אמיתי ואינו עיוורון-פרסר.**

## פילוח 09-11 — מסתכם למכנה שלו

```
$ grep "^2026-09-11.*\[S1-BINARY\]" ... | sed -E 's/.*\[S1-BINARY\] ([A-Za-z_=]+).*/\1/' | sed -E 's/=.*//' | sort | uniq -c
   6 EVENT
   3 HELD
```
`6 + 3 = 9` ✓ **מסתכם**.

## מפקד-על של כל הקובץ — מסתכם גם הוא

```
$ grep -c "\[S1-BINARY\]" /tmp/backend.err.log                    ⇒  10
$ grep "\[S1-BINARY\]" /tmp/backend.err.log | tail -1
2026-09-12 23:03:08 [WARNING] [mems26] [S1-BINARY] EVENT=acceptance_UP: Normal_Variation→Normal_Variation ... bar=80
```
`9` (09-11) `+ 1` (09-12) `+ 0` (09-13) `= 10` ✓

## 🔑 המפריד השני — אפס בלוג **חי** אינו אפס בלוג **מת**

ביקורת-חיובית על הפרסר בלבד אינה מספיקה: אם הבקאנד לא כתב כלום היום, `0` היה מתקבל
גם ממערכת מתה ([[feedback_zero_log_lines_needs_clock_check]]). לכן נמדד גם המכנה-הכולל:

```
$ for D in 2026-09-10 2026-09-11 2026-09-12 2026-09-13; do echo "$D total=$(grep -c "^${D}" /tmp/backend.err.log)"; done
2026-09-10 total_log_lines=0          ← הלוג הנוכחי מתחיל ב-09-11
2026-09-11 total_log_lines=106915
2026-09-12 total_log_lines=236308
2026-09-13 total_log_lines=67916      ← הלוג חי ופעיל היום
$ tail -1 /tmp/backend.err.log
2026-09-13 23:25:16 [WARNING] [backend.v9.api.v9.bars] [bars/woodies_5min] _route_bar BLOCKED stale bar:
    stale_ts (bar 2026-09-11T20:55:00+00:00 older than 1 day, 0:00:00)
$ date '+%Y-%m-%d %H:%M:%S %Z'   ⇒   2026-09-13 23:25:17 IDT
```

**הכתיבה האחרונה קדמה לשעון-המדידה בשנייה אחת.** ⇒ הבקאנד כתב `67,916` שורות היום ו-
**אפס** מהן `[S1-BINARY]`. הבר החדש-ביותר הוא `2026-09-11T20:55Z` = **בר-סגירת-שישי** ⇒
אין ברים חדשים ⇒ אין אירועי-S1. **האפס הוא התשובה הנכונה, לא כשל.**

## 🔴 תיקון-עצמי — פילוח שלא הסתכם, והסיבה

הפילוח הראשון לפי רמה נתן `37,063 + 17,577 + 13,295 = 67,933` מול מכנה `67,916` —
**עודף של 17**. לא דיווחתי את החלקים: הסיבה היא ש**הקובץ גדל בין שתי הקריאות** (הכותב חי).
המפריד — צילום אטומי אחד ופילוח עליו בלבד:

```
$ grep "^2026-09-13" /tmp/backend.err.log > /tmp/d13_snapshot.txt ; rc=0
DENOM_frozen=67953
  37075 WARNING
  17583 ERROR
  13295 INFO
SUM=67953        ✓ מסתכם בדיוק
```

המכנה `67,916 → 67,953` (‏`+37` בכ-2 דקות) ⇒ **אישור ישיר** שהגידול הוא ההסבר.

## 🟠 ממצא-לוואי (נרשם כ-[[T-352]], לא נטען כבאג)

`17,583` שורות `ERROR` ביום-א' שוק-סגור, **כולן** חתימה אחת:
```
[ERROR] [backend.v9.api.v9.bars] [bars/5min] TS-OFFSET-GATE REJECTED batch: newest bar ts 99999s
   behind now (> 900s) while feed advances (1787149800 -> 1789160100) — live-but-mislabeled TS
```
ו-`53,522` מ-`67,953` השורות מגיעות מ-`backend.v9.api.v9.bars` לבדו. שער-התקינות עובד
כמתוכנן, אך הוא פולט `ERROR` לכל batch נדחה ⇒ **קבורת-שגיאות-אמת ברעש**.
**אינו נטען:** לא נקרא קוד-השער, ואין טענה לנזק-נתונים או לפיד-מת — הבר הקפוא הוא
בר-סגירת-שישי וזה **צפוי** בשוק סגור ([[feedback_frozen_bar_is_not_dead_feed]]).
**הצעד הבא שייך לשער-הבוקר:** למדוד מחדש אחרי `01:00` — אם הזרם **נעצר** כשמגיעים ברים
טריים, זו תופעת-שוק-סגור; אם **נמשך**, זו מחלקה חדשה.
