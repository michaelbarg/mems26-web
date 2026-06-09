# CC PROMPT — Trades supplement: שמירת כל העסקאות + זיהוי לא-אמיתי + עיצוב

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael) · **מצב:** SHADOW
**הקשר:** בנוסף ל-`CC_PROMPT_TRADES_PAGE_AUDIT_EXPAND` (נשלח), Michael ביקש 3 דברים. diagnose-first · Rule 5 · אפס שינוי order/risk/sizing.

## 1 · לשמור את כל העסקאות מהיום
- אמת ש-**כל עסקה שנורתה היום** (SHADOW) נשמרת ב-`v9_trades` — אפס drops/skips. cardinality: מס' fires = מס' שורות.
- אבחן כל מקום שעלול להפיל עסקה (commit נכשל, חריגה שקטה, dedup אגרסיבי). הדבק ספירה: fires היום מול rows ב-DB.
- ודא שהשמירה רציפה מהיום והלאה (לא תלוי restart — עם ה-LaunchAgent).

## 2 · זיהוי "לא אמיתי" בטריידס (synthetic/test)
- ודא שהמערכת **מזהה ומסמנת** עסקאות לא-אמיתיות (test/phantom/synthetic) — `is_synthetic`. אמת שהזיהוי תופס מקרים כמו @5900 phantom.
- **בפרונטאנד:** במקום פשוט להסתיר (`is_synthetic=0` filter) — להציג אותן עם **badge ברור "TEST/SYNTHETIC"** או toggle, כך ש-Michael **רואה** שהן לא אמיתיות ולא מתבלבל. אמיתי מול לא-אמיתי חייב להיות מובחן ויזואלית.
- (אם יש ספק אם להציג-עם-badge או להשאיר מוסתר-אבל-מסומן — שאל את Michael.)

## 3 · עיצוב עמוד הטריידס — נוח להתמצאות + ראות טובה יותר
- שיפור UX: עמודות ברורות, קיבוץ הגיוני (mode/מערכת/outcome), PnL/R קריאים, **ציר-זמן ניהול-עסקה** (כניסה→תזוזות סטופ→targets→יציאה), badges לסטטוס/synthetic, פילטרים בולטים.
- מטרה: לראות במבט מהיר מה אמיתי, מה נורה, מה התוצאה, ואיך נוהל — בלי לחפש.
- אל תוסיף polling חדש (קצב קיים).

## פלט
`docs/reports/TRADES_SUPPLEMENT_2026-06-01.md`: (1) ספירת fires-vs-rows + תיקון drops · (2) אימות synthetic detection + screenshot של ה-badge · (3) before/after עיצוב (screenshot). Rule 5. עדכון STATUS_BOARD.

**שערים:** diagnose-first למה שעלול להפיל עסקאות. synthetic = תצוגה מסומנת (לא להסתיר בשקט). אפס שינוי order/risk/sizing. תאם עם פרומפט הטריידס הראשי (אותו עמוד).
