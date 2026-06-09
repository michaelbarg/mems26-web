# CC PROMPT — Trades page: שיפור עיצוב (נוח לשימוש + קריאוּת שורות/תוכן)

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael) · **מצב:** SHADOW · frontend (Tier-2) · Rule 5 (screenshots) · אפס שינוי order/risk/sizing · אל תוסיף polling (קצב קיים).
**מטרה:** עמוד הטריידס נוח יותר לשימוש — לראות תוכן ושורות בקלות, להבין במבט מה קרה בכל עסקה.
**הערה:** הפריסה/קריאוּת ניתנות לבנייה **עכשיו** (גם עם 0/synthetic rows); כיוונון ויזואלי סופי ב-RTH עם נתונים אמיתיים.

## קבצים
`frontend/v9/src/v9/components/trades/TradesTable.tsx` · `TradeDetailsModal.tsx` · `components/strips/TradeHistoryStrip.tsx`

## מה לשפר
1. **טבלה קריאה:** היררכיית עמודות ברורה (# · mode · system · direction · entry · exit · stop · PnL$ · R · outcome · time). יישור מספרים לימין, רוחבים אחידים, sticky header, ריווח שורות נוח, hover.
2. **צביעה לפי תוצאה:** WIN ירוק · LOSS אדום · BE אפור · OPEN/PARTIAL מודגש. synthetic = עמום + **badge "TEST"** (מתואם עם פרומפט ה-badge).
3. **badges סטטוס:** state (OPEN/PARTIAL/CLOSED) · דגל `T1_NO_BE` בולט · synthetic.
4. **מודאל — ציר-זמן ניהול:** הצג את `management_log` יפה: כניסה → תזוזות stop (from→to+reason) → T1/T2/T3 hits → יציאה, כרצף קריא עם זמנים. (הנתונים נכתבים עכשיו אחרי חיווט ה-management-log.)
5. **פילטרים בולטים + מיון:** mode/system/date/synthetic נגישים; מיון לפי time/PnL/R.
6. **קריאוּת תוכן:** מחירים/PnL בפורמט אחיד (2 ספרות, $ ו-R), תאריך/שעה קריא (TZ ברור).

## אימות (Rule 5)
- screenshots **before/after** (עם השורות הקיימות — synthetic/empty).
- הטבלה קריאה, השורות מובחנות, המודאל מציג ציר-זמן.
- אפס רגרסיה בפילטרים/חישובים (שנבדקו ב-audit).

## פלט
`docs/reports/TRADES_UX_REDESIGN_2026-06-01.md`: diff frontend + screenshots before/after. עדכון STATUS_BOARD. **כיוונון סופי + UAT ויזואלי → ב-RTH עם נתונים חיים.**

**שערים:** frontend בלבד · אפס polling חדש · אפס שינוי order/risk/sizing · לתאם עם פרומפטי הטריידס (badge + management-log) — אותו עמוד.
