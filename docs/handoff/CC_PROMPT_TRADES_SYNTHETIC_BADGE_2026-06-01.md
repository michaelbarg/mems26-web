# CC PROMPT — Trades: הצגת עסקאות synthetic עם badge "TEST/SYNTHETIC"

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael בחר: badge) · **מצב:** SHADOW · Rule 5 · אפס שינוי order/risk/sizing.
**החלטה:** במקום להסתיר synthetic — **להציג עם badge ברור**, כך ש-Michael רואה מיד מה לא אמיתי.

## Backend
- `GET /trades` + `/trades/recent`: **לכלול** שורות `is_synthetic=1` (להסיר/לרכך את הסינון `is_synthetic==0`), ולהוסיף `is_synthetic` ל-payload של כל שורה.
- ⚠️ **לא לזהם סטטיסטיקות:** WR% · total PnL · daily stats · aggregates — **לחשב רק על עסקאות אמיתיות** (`is_synthetic=0`). synthetic מוצג ברשימה אך **לא נספר** במדדים.
- ⚠️ אל תחזיר את באג ה-@5900: בידוד test-DB (`tests/.../conftest.py`) חייב להישאר — אסור ש-synthetic **חדשות** ייווצרו בפרוד. רק להציג קיימות מסומנות.

## Frontend (`TradesTable.tsx` + modal)
- שורת synthetic → **badge "TEST/SYNTHETIC"** + בידול ויזואלי (עמום/מסגרת/צבע) כך שאמיתי מול לא-אמיתי ברור במבט.
- אופציונלי: פילטר/מיון "הצג/הסתר synthetic" (ברירת מחדל: מוצג עם badge).

## אימות (Rule 5)
- שורות synthetic קיימות (למשל @5900 המסומנות) מופיעות **עם badge**; שורות אמיתיות ללא שינוי.
- WR%/PnL aggregate **לא כוללים** synthetic (הדבק חישוב לפני/אחרי).
- אפס synthetic חדשות בפרוד אחרי ריצת טסטים.
- screenshot של ה-badge.

## פלט
`docs/reports/TRADES_SYNTHETIC_BADGE_2026-06-01.md`: diff backend (filter+payload+aggregate guard) · diff frontend (badge) · screenshot · אימות aggregates נקיים. עדכון STATUS_BOARD.

**שערים:** synthetic = תצוגה מסומנת + מוחרג מסטטיסטיקות · בידוד test-DB נשמר (אפס synthetic חדשות) · אפס שינוי order/risk/sizing.
