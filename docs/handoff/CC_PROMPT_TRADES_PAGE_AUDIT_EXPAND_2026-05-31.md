# CC PROMPT — ביקורת מלאה + הרחבה + תיקון של עמוד Trades

**תאריך:** 2026-05-31 · **מקור:** Cowork (בקשת Michael)
**מצב:** SHADOW בלבד · diagnose-first · audit-before-build · Rule 5 (פלט גולמי לכל קביעה) · smallest correct change
**מטרה:** עמוד ה-trades יעבוד מקצה-לקצה — כל הפילטרים, כל החישובים תקינים, כל הקישורים מאומתים, מקבל **נתוני אמת**, ומשקף **ביצוע + תזוזת סטופ** (שהעסקאות מנוהלות כראוי).

---

## חוקי-על
1. **Audit לפני build.** אסור לבנות/לשנות לפני סיווג KEEP/ADAPT/REPLACE לכל רכיב קיים (CLAUDE.md).
2. **Rule 5.** כל "עובד / תקין / מאומת" = פקודה + פלט גולמי מודבק (curl, SQL, pytest, screenshot).
3. **ארבעת צירי UAT** לכל endpoint נתונים: Quality (אין נתון רע), Recency (`endpoint.latest_ts == MAX(ts) ב-DB`), Cardinality (`len(rows)==limit`), Latency (<סף מתועד).
4. **אסור לגעת** ב-order/risk/sizing/polling floors (CLAUDE.md). שינוי בנתיב ניהול-עסקה (כתיבת management log) = smallest correct change + regression test.
5. **לבנות על מה שכבר תוקן** ב-`docs/reports/PIPELINE_TRADES_E2E_2026-05-31.md` (5 תיקוני UI: scratch=0, mode default→ALL, date filter לקסיקלי, WR%+R, truncation 200→500/1000). אל תחזור עליהם — אמת שהחזיקו.

## תלות קריטית (לקרוא לפני שמתחילים)
ה-DB **ריק (0 trades)** והשרת לא רץ → אימות "נתוני אמת + ביצוע + תזוזת סטופ" מחייב **SHADOW חי עם עסקאות** או trade בקרה מקצה-לקצה. חלק A (audit סטטי + תיקוני קוד) ניתן עכשיו; חלק C (UAT חי) דורש סטאק רץ. אם אין נתונים — בצע A+B, וב-C הרץ trade מבוקר דרך מחזור-החיים המלא (FILLED→T1→BE→trail→close) ואמת כל שלב.

---

## הרכיבים בסקופ (קרא את כולם)

**Frontend:** `frontend/v9/src/v9/components/trades/TradesView.tsx` · `TradesTable.tsx` · `TradeDetailsModal.tsx` · `components/strips/TradeHistoryStrip.tsx` · `lib/api.ts` · `lib/tradeTime.ts`
**Backend:** `backend/v9/api/v9/trades.py` (GET `` /`recent`/`active`/`{id}`, POST `/exit`/`/log`) · `services/trade_context.py` (`compute_trade_pnl`, `extract_*`, `_stop_initial_from_trade`) · `services/trade_excursion.py` · `services/trail_engine.py` · `services/trade_manager/manager.py` + `bar_level_detector.py`
**DB:** `v9_trades`, `v9_trade_management_log` (model `db/models/trade_log.py`).

---

## חלק A · ביקורת מלאה (READ-ONLY) → `docs/reports/TRADES_PAGE_AUDIT_2026-05-31.md`

**A1. מפת קישורים מלאה.** לכל אלמנט בעמוד: איזה hook/endpoint הוא קורא → איזה query ב-DB → איזה חישוב. טבלה: UI element → api.ts call → endpoint → DB query → calc fn. סמן KEEP/ADAPT/REPLACE. הדבק ראיות.

**A2. פילטרים — אודיט שכל אחד עובד וקומבינציות.** GET `/trades` תומך `mode`, `firing_system`/`dominant_system`, `limit`. אמת: (a) כל פילטר ב-UI באמת מגיע ל-query ומסנן; (b) קומבינציה (mode+system+date) עובדת; (c) date filter לא לקסיקלי (E2E תיקן — אמת); (d) `is_synthetic=0` מסנן fake; (e) ברירת מחדל mode=ALL. הדבק curl לכל פילטר + ספירה צפויה מול בפועל.

**A3. חישובים — אמת נכונות מתמטית.** `compute_trade_pnl` (pnl_usd, pnl_r, pnl_mode, contracts_pnl), `compute_trade_excursion`, WR%, ו-`/active` (C1/C2/C3: `risk_usd=|entry-stop|×5`, per-contract pnl, R). לכל חישוב: דוגמה מספרית ידנית מול פלט הקוד (Rule 2 — verify before trust). חפש את באג ה-bar-open-vs-fill (Bug C) ותעד.

**A4. נתוני אמת (source-of-truth).** אמת שהעמוד מציג DB אמיתי (לא סינתטי/mock): 4 צירי UAT על `/trades`, `/recent`, `/active`. אמת `latest_ts==MAX(entry_ts)`, אין rows עתידיים, `is_synthetic=0`.

**A5. ⚠️ ביצוע + תזוזת סטופ (הליבה של הבקשה).** חשד מאומת מראש: **TrailEngine מזיז stop ורושם רק ל-logger (`trail_engine.py:786`), לא לטבלת `v9_trade_management_log`** (grep ל-V9TradeManagementLog ב-trail_engine = 0). גם Smart-BE (`manager.py`) — לאמת אם כותב management log. ה-endpoint `/trades/{id}` מחזיר `management_log` מהטבלה הזו → **אם אף אחד לא כותב אליה, ה-UI לא יראה תזוזות סטופ/BE/trail.** אמת מי (אם בכלל) כותב ל-`v9_trade_management_log`, והדבק grep. תעד את הפער כ-finding.

---

## חלק B · תיקון + הרחבה + סידור

**B1. תקן כל פילטר שלא עובד** (לפי A2). smallest correct change + טסט לכל תיקון.
**B2. תקן כל חישוב שגוי** (לפי A3) + regression test עם הדוגמה המספרית.
**B3. חיווט management log (לפי A5):** כשהסטופ זז (Smart-BE+1T, C.2 trail, C.4 lock-in, C.6 time-decay) או בכניסה/יציאה/target-hit → כתוב שורת `V9TradeManagementLog` (action ∈ STOP_MOVE/SMART_BE/TRAIL/LOCKIN/T1_HIT/EXIT, value=before/after). זו **observability** (לא לוגיקת-מסחר) — אבל נוגע בנתיב הניהול → smallest change + regression test. כך ה-UI יציג ציר-זמן ניהול אמיתי.
**B4. הרחבה + סידור UX:** הצג בעמוד/במודאל **ציר-זמן ניהול-עסקה** (כניסה → תזוזות סטופ → target hits → יציאה) עם before/after; עמודת stop-movement; דגלי `_stop_note`/`_stop_issue` (T1_NO_BE) בולטים; ארגון עמודות/קיבוץ. אל תוסיף polling חדש — השתמש בקצב הקיים.

## חלק C · UAT מקצה-לקצה
**C1. 4 צירי UAT** על שלושת ה-endpoints (פלט גולמי).
**C2. trade מנוהל מקצה-לקצה:** הרץ עסקה (SHADOW חי או trade בקרה) דרך FILLED→T1 hit→Smart-BE+1T→trail→close. אמת שכל שלב מופיע בעמוד עם PnL/R נכונים, ושהתזוזות נרשמו ב-management log ומוצגות. הדבק ראיות (SQL + screenshot/JSON).

---

## פלט מצופה
1. `docs/reports/TRADES_PAGE_AUDIT_2026-05-31.md` (חלק A, ראיות).
2. `docs/reports/TRADES_PAGE_FIX_UAT_2026-05-31.md` (חלק B+C: diffs, פלט טסטים, UAT 4 צירים, ראיות trade מנוהל).
3. commits נפרדים לפי תיקון. עדכון `STATUS_BOARD.md` (finding→fix→evidence, Rule 5).

**שערים:** אם אין נתוני SHADOW → בצע A+B + C עם trade בקרה, ודווח מה דורש סטאק חי. כל שינוי שנוגע בלוגיקת-מסחר/סיכון = strategic-stop + אישור Michael (חיווט management log = observability, מותר עם regression). אל תיגע ב-Auth Table / MAX_CONTRACTS / D-094 (threads נפרדים).
