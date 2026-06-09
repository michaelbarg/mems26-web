# CC PROMPT — IB (Initial Balance) חייב להישאר RTH-only אחרי chart #5 · diagnose-first

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael) · **מצב:** SHADOW
**חשש (Michael):** אחרי ש-chart #5 (24h continuous) הפך למקור ה-5-דק', יש סיכון שה-**IB** (וכל חישוב RTH-bound) יילקח/יזדהם מנרות ה-overnight. **IB חייב להיות רק משעות המסחר הרציף (09:30-10:30 ET).** IB=0 כרגע — לוודא שזה pre-RTH ולא רגרסיה מהמקור הרציף.
**משמעת:** diagnose-first · Rule 5 · אפס שינוי order/risk/sizing · firing RTH-gated.

## Phase A · אבחון (READ-ONLY)
1. **מאיפה IB מגיע?** Sierra IB study (chart #12) / מחושב מ-bars ב-`state_machine` IB tracker / אחר? הדבק את הקוד.
2. **האם נרות chart #5 הרציפים מזינים את ה-IB / day-type RTH-range / TPO?** בדוק: ה-stream `5min_continuous` → `bar_ingestion` → האם הברים נושאים `is_rth` נכון, או שהם נכנסים כ-5min רגיל ללא תיוג session? האם ה-IB tracker / TPO / day-type RTH-range מסננים לפי `is_rth`?
3. **למה IB=0?** אשר שזה pre-RTH (אין session RTH עדיין) ולא כי המקור הרציף שבר את החישוב.

## Phase B · הבטחה/תיקון (אם דולף)
- נרות chart #5 הרציפים (24h) מזינים **רק**: 5-דק' לתצוגה + CVD + מחיר-חי.
- **IB · day-type RTH-session-range · TPO** — נשארים **RTH-only**: רק ברי `is_rth=True` (או מקור ה-Sierra IB study על chart #12). ודא/הוסף guard בנתיב הקליטה של `5min_continuous` כך שברי overnight **לעולם** לא נכנסים ל-IB/RTH-range/TPO.
- אל תשבור את הזרימה הרציפה לתצוגה — רק לגדר את ה-RTH-bound.

## Phase C · אימות (ב-RTH, Rule 5)
- IB מחושב מחלון RTH בלבד (09:30-10:30 ET), ≠0 בטעות, לא כולל ברי overnight.
- day-type מסווג נכון (ה-IB width/range תקינים).
- נרות overnight עדיין מוצגים (תצוגה) אך לא נכנסים ל-IB/TPO.

## פלט
`docs/reports/IB_RTH_ONLY_GUARD_2026-06-01.md`: מקור IB (ראיה) · האם דלף מ-chart #5 · diff guard אם נדרש · אימות RTH ש-IB RTH-only ו-day-type נכון.

**שערים:** diagnose-first — דווח מקור IB + האם דולף לפני תיקון. אפס שינוי order/risk/sizing. firing RTH-gated. תאם עם `RTH_VERIFICATION_FULL_PASS` (אותו חלון RTH).
