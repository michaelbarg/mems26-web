# Restart Recovery Plan — 2026-05-30 (v2, Michael-approved)

**עיקרון:** לכל שדה מקור-אמת אחד. בהפעלה מחדש **טוענים מחדש מהמקור הסמכותי —
לא מחשבים מחדש ולא ממציאים placeholder.** נתוני שוק = Sierra; החלטות S1 = השורה
השמורה ב-DB (תאריך ET, לא ROLLED_OVER). כשבאמת אין נתון → INDETERMINATE אמיתי
(יורד ל-Normal), לא ניחוש.

## Problem 1 — 5-min bar gaps after restart (MANDATORY)
**Root:** `Bars5MinStream._push_api()` שולח רק `bars[-1]` בכל poll. אחרי restart
באמצע RTH, הברים שבין הרשומה האחרונה ב-DB לבין ה-export הנוכחי אובדים לתמיד.
**Fix:** ב-startup `SELECT MAX(ts) FROM v9_bars_5min`; בדחיפה הראשונה לשלוח את **כל**
הברים שאחרי ה-ts (backfill), ואז לחזור ל-latest-only (דגל `_first_push`).
**סטטוס:** חובה (Michael). אין החלטה — תיקון מכני.

## Problem 2 — S1 day_type resets on restart (✅ APPROVED v2)
**Root האמיתי:** `day_type_seed.py:111` **כופה `opening_type=INDETERMINATE`** בהפעלה
מחדש במקום לטעון את הערך השמור. כך נתון תקין נזרק (הוכחה: 27/5 נשמר OPEN_DRIVE, אך
seed היה הופך ל-INDETERMINATE).
**Fix (Michael-approved 2026-05-30) — בלי replay, בלי כלל 13:00:**
1. IB + טווח → מ-Sierra/TPO (`maybe_seed_ib_from_tpo` — כבר עובד).
2. `opening_type` / `day_type` / `lock_state` / `confidence` → **לטעון מהשורה של היום
   ב-`v9_day_type_history`** אם `date == et_today()` ו-`status != 'ROLLED_OVER'`.
3. רק אם אין שורה כזו → `opening_type=INDETERMINATE` אמיתי (degrades to Normal).
**מבוטל מהגרסה הקודמת:** replay של 6 ברי פתיחה + דילוג-13:00 — מיותרים ברגע שטוענים
מה-DB, ומוסיפים סיכון re-eval. נמחקו לפי החלטת Michael.

## Implementation Priority
שניהם pre-LIVE ואושרו. Problem 1 (backfill) + Problem 2 (load-from-DB) — מימוש מינימלי
+ regression. אין עוד heuristics להחלטה.

## אימות
- restart אחרי שנשמר `OPEN_DRIVE` → לאחר seed `opening_type == 'OPEN_DRIVE'` (לא INDETERMINATE).
- restart באמצע RTH → אין חורים: ברי 5min רציפים ללא פערים מאז MAX(ts) שלפני הנפילה.
- אין שורה להיום → INDETERMINATE (לא crash, יורד ל-Normal).
