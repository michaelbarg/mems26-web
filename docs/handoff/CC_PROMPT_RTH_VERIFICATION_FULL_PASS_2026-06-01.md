# CC PROMPT — אימות RTH + מעבר end-to-end על כל המשטחים (לרוץ ב/אחרי פתיחת RTH ~16:30 IL)

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael אישר sign-off ל-SHADOW + ביצוע) · **מצב:** SHADOW · flags ON.
**מטרה:** לאמת ש-(א) המערכת עובדת מלא **חי ב-RTH** ויורה, ו-(ב) **כל משטח מציג נתונים, יש נתיב ברור, והכל מובן** (dashboard · build status · trades). Rule 5 (פלט גולמי) · firing RTH-gated · אפס שינוי order/risk/sizing.

## חלק 1 · אימות חי ב-RTH (אחרי 09:30 ET / 16:30 IL)
1. **DLL frozen-tail Phase B (חוסם-LIVE פתוח):** 0 זוגות `(cci_14, swi)` זהים רצופים על **ברים שונים** ב-RTH. סגור או דווח.
2. **day-type מסווג** (לא unknown) → מערכות נכנסות לכשירות.
3. **אפקט flag-ON בנתונים שנאספים** (לא רק שהדגל True): S3 `min_level_vol=0.3×median`, S1 opening מ-CVD, IB ATR-tiers, staging cap. הראה ערכים אמיתיים שמשקפים את הלוגיקה החדשה.
4. **setups ראשונים נרשמים** ב-`v9_trades` (SHADOW) · קצב ירי/התפלגויות סבירים · 5-דק' freshness תקין (לא stale).

## חלק 2 · מעבר end-to-end — כל משטח: נתונים מגיעים + נתיב + ברור
לכל משטח, טבלה: **נתונים מגיעים? Y/N · נתיב (UI→endpoint→DB→מקור) · ברור/דו-משמעי**. סמן כל פאנל ריק/לא-מוסבר.
- **Dashboard:** 6 פאנלים מאוכלסים (S1 day-type · S2 · S3 · S4 Woodies · S5 TPO · S6 Killzone) · מחיר-חי זז בכולם (כולל פאנל Woodies) · levels (POC/VAH/VAL) · **IB מתעדכן ומוצג בפרונט אחרי הפתיחה** (Michael — לא None אחרי 09:30 ET; ערכי IB high/low RTH מופיעים בדאשבורד).
- **Build Status:** כל stage מציג Live/Required/Present/Value · אפס MISSING לא-מוסבר.
- **Trades page:** setups/עסקאות מופיעים · חישובים נכונים (PnL/R) · **management-log (תזוזות סטופ/BE) מוצג** · פילטרים עובדים.
- 4 צירי UAT על ה-endpoints המרכזיים (`/cockpit/systems-snapshot`, `/trades`, chart) — Quality/Recency/Cardinality/Latency.

## חלק 3 · נתיב הירי חי
אם נרשמו setups ב-RTH — עקוב אחר אחד מקצה לקצה: detection → 5 שערי סיכון → TradeManager → DB → `/trades` → UI. הוכח שהשרשרת שלמה וגלויה.

## פלט
`docs/reports/RTH_VERIFICATION_FULL_PASS_2026-06-01.md`: (1) ממצאי RTH חיים + verdict frozen-tail · (2) טבלת משטחים (נתונים/נתיב/ברור) · (3) נתיב ירי חי · ראיות גולמיות (curl/SQL/צילום). עדכון `STATUS_BOARD.md` + סגירת חוסם frozen-tail אם עבר.

**שערים:** SHADOW בלבד · firing RTH-gated · אם משטח לא מציג נתון ב-RTH (לא מוסבר ע"י gate) — דווח כבאג עם נתיב. אפס שינוי order/risk/sizing.
