# CC — תיקון (לפי אבחון מאומת): S1/IB · woodies-writes · טבלה-חיה · יציבות · 2026-06-09

מבוסס על `docs/reports/DIAGNOSE_CHART_LIVEBARS_NOFIRE_2026-06-09.txt` (אומת ע"י Cowork מול הקוד).
עבוד דרך ה-index · Rule 5 (raw לכל תיקון) · regression לכל באג · **STRATEGIC-STOP** לפני נגיעה
ב-S1-classification/Sierra/DLL/fire-path. אל תדליק דגל default-off · S3 לא נוגעים (post-LIVE).

**מה Michael רואה (חייב להיפתר בפועל):** (1) טבלה מעוותת שלא מתעדכנת חי · (2) ב-Build Status
S1 לא סיווגה אחרי חצי שעה → S2 נעולה בשעה הראשונה כתוצאה.

═══════════════════════════════════════════════
## FIX 1 🔴 ROOT — S1 day_type תקוע UNKNOWN (IB לא ננעל / opening_type=NA)
═══════════════════════════════════════════════
אומת: `v9_day_type_state` כולו NA/UNKNOWN/A3/PENDING; `tpo_routes.py:200 ib_found=bool(raw.get("ib_found"))`;
`state_machine.py:406` תקוע A3 כש-IB None. **זה השורש למפל D→E→C** (UNKNOWN→Neutral_Center→INITIATIVE SKIP + chart-patterns חסומים).
**אבחן-קודם את ה-WHY (אל תתקן עד שברור):**
1. האם Sierra בכלל מייצאת IB/opening? `cat ~/SierraChart_Data/v9_export/tpo*.json` — יש `ib_found`/`ib_high`/`ib_low`/`opening_type`? או שהשדה חסר/false?
2. הבחן: (א) Sierra/TPO study לא מייצא IB (צד-Sierra/DLL → **STRATEGIC-STOP + Michael**, §Sierra) · (ב) ה-export מכיל IB אבל ה-ingest/parse מפיל אותו (תיקון-קוד) · (ג) IB **לגיטימית** עוד לא ננעל (IB=שעה ראשונה; "אחרי 30 דק'" עשוי להיות מוקדם — אבל `opening_type=NA` מרמז על שבר אמיתי, לא תזמון).
3. **opening_type=NA בנפרד:** ה-opening אמור להיות זמין מוקדם (לא תלוי נעילת-IB מלאה). למה NA? `tpo_system.get_current()` מחזיר NA — מאיפה.
**תיקון** רק אחרי שהשורש ברור + (אם Sierra/classification) אישור-Michael. **קריטריון-קבלה:** day_type≠UNKNOWN בחלון-הצפוי → INITIATIVE לא SKIP-אוטומטי → chart-patterns נגישים.

═══════════════════════════════════════════════
## FIX 2 🔴 zlr_detected boolean→integer (כל כתיבות woodies נופלות)
═══════════════════════════════════════════════
אומת: `bars_woodies.py:32,36,63 Column(Integer)` מול כתיבות-boolean (`bars.py:917,825,934,966 bar.get("zlr_detected",False)`);
שורה 815 כן ממירה (`1 if ... else 0`) — שאר הנתיבים לא → `psycopg2 DatatypeMismatch` → כל woodies_5min נופל (8 שורות בלבד) → S4 מת + פאנל-woodies ריק.
**תיקון:** עקבי בכל נתיבי-הכתיבה — או cast `int(bool(...))` בכל מקום, או החלף עמודה ל-`Boolean` (החלטה אחת, לא חצי-חצי). חפש כל `*_detected`/`*_bool` דומה ב-safe_writer (סיכון-רוחבי). regression שמוודא כתיבת-woodies מצליחה ב-PG. **קריטריון-קבלה:** `count(*) v9_bars_5min_woodies` מטפס בזמן-אמת.

═══════════════════════════════════════════════
## FIX 3 🟡 טבלה: עדכון-חי + עיוות (ghost bars / dedup) — סימפטום-Michael #1
═══════════════════════════════════════════════
אומת: 2 ghost bars ב-`v9_bars_5min` (ts בלי TZ → PG פירש כשעון-ישראל, shift ‎-3h); ה-CVD ‎-89,870 **לא** ב-DB (artifact-תצוגה).
1. **ghost bars:** מצא את נתיב-הכתיבה שכותב ts בלי TZ → כתוב `timestamptz` עם UTC מפורש (Rule 4 — אין TZ-ambiguity). + ודא שה-dedup במיזוג (`bars_5min_history.py:90-106`) מסיר כפילויות-ts.
2. **עדכון-חי:** הצ'art קורא `v9_bars_5min_continuous` (193) קודם — ודא שהפרונט **באמת מתרענן חי** (polling/ws) לפי §Frontend Polling Floors (אל תגדיל אינטרוולים). אם הפאנל קפא — אבחן למה (woodies-panel ריק מ-FIX 2? מקור-נתון?).
3. ודא שה-CVD על pane נפרד (`CumulativeDeltaPane.tsx`) ולא על ציר-המחיר. **קריטריון-קבלה:** Michael רואה צ'art שמתעדכן חי, בלי ghost/עיוות.

═══════════════════════════════════════════════
## FIX 4 🟡 יציבות — re-hydrate 14× + BarRouter 2.3s
═══════════════════════════════════════════════
`FiveMinSystem` הִדרֵט 14+ פעמים (16:30-17:12) — אמור startup+בר-חדש בלבד. אבחן למה (לולאת-restart? קריאה-כפולה?) → תקן.
`BarRouter SLOW handler process_bar 2386ms` בזמן fire — אבחן (DB commit? hydrate בתוך process_bar?). שניהם יכולים לגרום ל"קפוא". raw.

═══════════════════════════════════════════════
## פורמט תשובה (Rule 5)
═══════════════════════════════════════════════
לכל FIX: שורש (file:line) · diff/commit · פלט-גולמי שמוכיח (SQL count מטפס / day_type≠UNKNOWN / צ'art חי) · regression.
**קריטריון-קבלה כולל:** S1 מסווגת → S2-INITIATIVE לא SKIP-אוטומטי → chart-patterns נגישים · woodies נכתב · צ'art מתעדכן חי בלי עיוות · **ובירי הבא — שורה ב-`v9_trades` + מוצגת בעמוד Trades** (סגירת הבאג של אתמול).
סדר: FIX 1 (root, diagnose→strategic-stop→fix) → FIX 2 → FIX 3 → FIX 4. NOT-DONE בסוף.
