# CC PROMPT — תיקון איכותי: חיבור + נרות overnight (Option C) + hydration רציף

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael אישר) · **מצב:** SHADOW
**מבוסס על:** `docs/reports/DIAGNOSE_ONLY_CONNECTIVITY_OOH_2026-06-01.md` (אבחון מאומת Rule 5).
**משמעת:** תיקון מבוסס-שורש (לא פלסטר) · diagnose-first נעשה · regression לכל תיקון · Rule 5 (פלט גולמי) · source-of-truth (אפס סינתוז · CVD reset-aware) · אפס שינוי order/risk/sizing/polling · גיבוי DB לפני שינוי נתונים.
**החלטות Michael:** נרות overnight = **Option C** (טבלת Woodies, צד-קוד) · העלאת backend = **כחלק מהתיקון + LaunchAgent**.

---

## P0 — לפני ה-RTH הבא

1. **backend LaunchAgent + העלאה.** צור `~/Library/LaunchAgents/com.mems26.backend.plist` במתכונת ה-bridge plist: KeepAlive מותנה (`SuccessfulExit=false`), `CLOUD_URL=http://localhost:8000`, `export V9_DISABLE_WATCHDOG=${V9_DISABLE_WATCHDOG:-1}`, אזין על 127.0.0.1:8000. בדוק listeners קיימים לפני (אל תכפיל). העלה את ה-backend. **שורש:** היום אין auto-restart ל-backend (רק לגשר) → מת בשקט ב-10:38.
2. **תיקון `timedelta`.** `backend/v9/services/bar_ingestion.py:8` — הוסף `timedelta` ל-import (כרגע `NameError` ב-:74 חוסם קליטת `v9_bars_5min` → רק 7 שורות). regression: בר נקלט ונספר.
3. **תיקון TZ ב-history loader.** `bridge/v9_history.py:43` — `America/Chicago` → `America/New_York` (להתאים ל-`base_stream.py:74`). שורש: דריפט שעה ב-gap-fill בקיץ.

## P1 — השבוע

4. **Archive schema drift.** `v9_tpo_sessions_archive` 19 עמודות מול `v9_tpo_sessions` 27 → `_archive_yesterday` (`INSERT ... SELECT *`) נכשל → **Y IB dll_missing**. תקן: רשימת עמודות מפורשת ב-`_archive_yesterday` (עדיף) או `ALTER TABLE ... ADD COLUMN` ל-8 החסרות. גיבוי DB קודם. אמת: Y IB חוזר עם ערכים אחרי archive.
5. **Dedup טבלת Woodies.** `v9_bars_5min_woodies` — ~20× שכפול לכל בר (אין UNIQUE), 14,568/14,994 שורות עם תאריך פגום. הוסף `UNIQUE(ts, symbol)` + UPSERT בקליטה, ונקה כפילויות קיימות (גיבוי קודם). שורש: הקליטה כותבת כל poll (~3s) ולא רק bar-close.

## נרות overnight — Option C (טבלת Woodies, תצוגה בלבד)
6. מקור OOH = **`v9_bars_5min_woodies`** (מקבל את הבר החי של ה-DLL גם overnight — הוכח 52 שורות מהלילה). 
   - ב-startup: טען **200 נרות אחרונים** מהטבלה ל-warm-up המערכות + לתצוגה.
   - כשאין feed חי טרי: ה-endpoints יחזירו את ה-session האחרון מהמקור הזה עם **badge "LAST SESSION · <תאריך>"**.
   - **תיוג session phase** (RTH/OVERNIGHT/POST) לכל בר נקלט.
   - ⚠️ **בטיחות — תצוגה בלבד:** נרות overnight/היסטוריים **לא** מזינים ירי / `BarLevelDetector` כחיים. **אמת ש-D-091/D-092 אכן נועלים את כל התבניות ל-RTH** (הדבק ראיה). אפס סינתוז.
   - הערה: ה-`history` array של ה-DLL הוא RTH-only — לכן C צובר נרות overnight **קדימה** (live), ולא מבצע backfill רטרואקטיבי של לילות עבר. זה מקובל.

## P2 — hydration רציף בכל אתחול (התחלה רציפה)
7. טען מחדש את ה-state שאבד היום ב-restart (מהאבחון §6.4):
   - **CVD cumulative** — מ-`v9_bars_cumulative_delta`, **רק מתחילת ה-session הנוכחי** (reset-aware, מתאפס 18:00 ET — לא לטעון חוצה-reset).
   - **Woodies CCI buffer** — replay של 20+ ברים אחרונים דרך WoodiesSystem כדי ש-CCI-14/trend_state תקפים מיד (אחרת GRAY שגוי → שערי תבנית שגויים).
   - **טווח יומי (session high/low)** + **POC/VAH/VAL** — מ-`mes_ai_data.json`/archive (אחרי תיקון 4).
   - אל תשבור את מה שכבר נטען (R2-9: opening_type/day_type/ib_locked).
8. **דוח startup מובנה** + **verification step:** אחרי history_loader+replay, בדוק `buffer_size>0` לכל מערכת והדבק; הגשר ידווח load+health per-stream.

---

## פלט מצופה
`docs/reports/FIX_CONNECTIVITY_OOH_HYDRATION_2026-06-01.md`: diff לכל תיקון · פלט גולמי (curl health 200, lsof :8000, ספירת v9_bars_5min גדלה, Y IB חוזר, dedup לפני/אחרי, 200-bar warm-up, CVD/CCI hydration log) · ראיה ש-D-091/D-092 נועלים ירי ל-RTH (היסטורי לא יורה) · golden/regression. commits נפרדים (P0/P1/OOH/hydration). עדכון `STATUS_BOARD.md`.

**שערים:** גיבוי DB לפני dedup/archive. נרות היסטוריים = תצוגה בלבד, לא מזינים ירי (strategic-stop אם המימוש עלול להפעיל ירי על stale). אפס שינוי order/risk/sizing/polling. אל תיגע ב-Auth V2 / D-094 / calibration-wiring (threads נפרדים) — אבל שים לב: calibration-wiring ו-OOH שניהם נוגעים ב-detection; תאם סדר עם Michael אם יש חפיפה.
