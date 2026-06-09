# CC PROMPT (טיוטה · GATED) — תיקון איכותי: חיבור + נרות מחוץ ל-RTH + hydration באתחול

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael) · **מצב:** SHADOW
**⛔ סטטוס: DRAFT · נעול.** אל תריץ עד: (1) דוח `DIAGNOSE_ONLY_CONNECTIVITY_OOH_2026-06-01.md` חזר, (2) Michael נעל את גישת התיקון. הפרטים המסומנים `‹מהאבחון›` יושלמו מממצאי האבחון — **בלי להניח** (לא פלסטר).
**משמעת:** תיקון מבוסס-שורש בלבד · מאחורי flags כשאפשר · regression לכל תיקון · Rule 5 · source-of-truth (אפס סינתוז · CVD reset-aware) · אפס שינוי order/risk/sizing/polling.

## רקע
אבחון 1/6 מצא: DISCONNECTED (frontend↔backend) · dll_missing · אין נרות מחוץ ל-RTH · DB ריק. Michael אישר כיוון תיקון איכותי (4 סעיפים למטה). השלב הזה מממש **רק** את מה שהאבחון אישר כשורש + בר-ביצוע.

## משימה 1 · שורש ה-DISCONNECTED
תקן את שורש הניתוק שזוהה באבחון (`‹מהאבחון›`: backend לא רץ / WS endpoint / CORS / handler). **לא** "תריץ מחדש" כפתרון — תיקון שמונע הישנות (למשל supervision/health, או באג ה-WS עצמו). regression + Rule 5.

## משימה 2 · נרות מחוץ ל-RTH ממקור רציף (תצוגה בלבד)
- מקור: **טבלת ה-Woodies 5-דק'** (`‹מהאבחון›` — הטבלה שאומתה כפעילה 24/6), אם האבחון אישר שהיא הרציפה. אחרת המקור שהומלץ.
- עומק: **200 נרות אחורה**.
- ה-endpoints של הצ'ארט/levels יחזירו את 200 הנרות מהמקור הזה כשאין feed חי טרי, עם **badge "LAST SESSION · ‹תאריך›"**.
- ⚠️ **תצוגה בלבד** — נרות אלו **אינם** מזינים את מערכות הירי / `BarLevelDetector` כחיים. הירי נשאר gated על נתון חי. אסור סינתוז.

## משימה 3 · hydration רציף בכל אתחול
המטרה: בכל restart המערכת מתחילה **רציף** — טוענת מחדש 200 נרות + כל ה-state, והגשר מדווח per-stream באתחול.
- טען מחדש (מ-DB, reset-aware): **cumulative_delta (CVD), Woodies studies (tail), נרות 5-דק', טווח יומי, POC/VAH/VAL**, ‹+ כל פריט נוסף מרשימת ה-state של האבחון›.
- מה שכבר נטען היום (R2-9: opening_type/day_type/ib_locked) — לא לשבור; להשלים את החסר בלבד (`‹מהאבחון›`).
- הגשר: בהעלאה ידווח load + health (FRESH/STALE/DEAD) לכל stream.
- ⚠️ CVD מתאפס בגבול session → לטעון בתוך חלון ה-session, לא חוצה reset.

## משימה 4 · dll_missing / streams חסרים
תקן את השורש שזוהה (`‹מהאבחון›`) כך שכל ה-streams מגיעים. local-only.

## פלט
`docs/reports/FIX_OOH_RESTART_HYDRATION_2026-06-01.md`: diff לכל תיקון · golden/regression · פלט גולמי (health, 200-bar backfill, hydration log) · אימות שהיסטורי לא מזין ירי. commits נפרדים. עדכון STATUS_BOARD.

**שערים:** נעול עד אישור Michael + דוח אבחון. כל פריט שהאבחון סימן כלא-בר-ביצוע / לא-שורש → strategic-stop, לא לתקן. נרות היסטוריים = תצוגה בלבד.
