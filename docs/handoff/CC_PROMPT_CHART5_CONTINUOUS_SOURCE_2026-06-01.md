# CC PROMPT — chart #5 כמקור קנוני רציף (5-דק' + CVD + מחיר-חי) · diagnose-first

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael אישר) · **מצב:** SHADOW בלבד
**עדכון 1/6 (אחרי SHADOW readiness report):** הסימפטום של **מחיר תקוע** כבר **טופל** — `80e37ba` מזריק live midpoint לפאנל Woodies (7590.50→7610.88) ולכל המשטחים. **אבל זה טלאי על המחיר בלבד:** לפי "Known Limitations" בדוח, `sc.Close` עדיין **קופא overnight** → ה-**OHLC של הנרות עצמן** stale/חסר ב-Globex (רק סמן המחיר מוטלא). chart #5 הוא התיקון השורשי לכך.
**רקע:** Michael הצביע על **Sierra chart #5** (`MESM26_FUT_CME`, 5 Min) שרץ **רציף 24h** (נרות overnight 0:25→5:05) עם subgraph **Cumulative Delta Bars**.
**מטרה (שדרוג איכותי, לא חוסם SHADOW):** להפוך את chart #5 ל-**מקור-אמת קנוני** ל-5-דק' **OHLCV** + CVD + מחיר-חי — כך שהנרות עצמן נכונות overnight (לא רק סמן המחיר), ולהחליף את טלאי ה-midpoint + ה-OHLC הקפוא. **לא חוסם פתיחת SHADOW** (שמוכן עם המיטיגציה הנוכחית) — אפשר במקביל/אחרי. firing נשאר RTH-gated.
**משמעת:** **diagnose-first — לא לשנות לפני שמיפינו את נתיב הנתונים** · Rule 5 (פלט גולמי) · **sc_study = anti-regression** (CLAUDE.md §7a + `docs/runbooks/SIERRA_DLL_OPS.md` — אסור לשבור את export של chart 12/Woodies) · אפס שינוי order/risk/sizing · אפס סינתוז · reset-aware CVD.

## Phase A · גילוי (READ-ONLY, ראיות)
1. **האם chart #5 כבר מייצא?** בדוק `~/SierraChart_Data/v9_export/` — יש קובץ JSON שמקורו chart #5 (5-דק' רציף + cumulative delta)? מתי עודכן? איזה study מייצא ממנו? (ה-DLL `MES_AI_DataExport` כיום על chart 12 לפי CLAUDE.md — האם מופע נוסף/אחר על chart #5?)
2. **איזו טבלת DB מקבלת נתון רציף 24h?** השווה overnight coverage: `v9_bars_5min` vs `v9_bars_5min_woodies` vs `v9_bars_cumulative_delta` — מי מהן באמת מתעדכנת overnight ומאיזה chart. הדבק טווחים+ספירות overnight.
3. **מסקנה:** האם הנתון של chart #5 כבר מגיע (ואז רק לחבר), או שצריך תוספת export. דווח לפני Phase B.

## Phase B · הגדרת המקור (החלטה, אם צריך export)
- אם chart #5 כבר מזין טבלה → דלג ל-Phase C.
- אם לא → הגדר את **תוספת ה-export המינימלית** מ-chart #5 (5-דק' OHLCV + cumulative delta) לפי `SIERRA_DLL_OPS.md`. ⚠️ **לא לשבור** את export chart 12. תוספת זו = שינוי sc_study → strategic-stop + אישור Michael לפני deploy (הצג את ה-diff המוצע, אל תפרוס).

## Phase C · חיווט קנוני (אחרי שהמקור זמין)
- **5-דק' OHLCV:** backend serves מ-chart #5 source (רציף) → chart endpoint + buffers. מבטל את הצורך ב-merge/gap-fill המסובך.
- **מחיר-חי + OHLC:** פאנל Woodies/טבלה כבר מקבלים מחיר חי (midpoint, `80e37ba`) — **המטרה כאן: להחליף את ה-midpoint ואת ה-OHLC הקפוא** במקור הרציף של chart #5, כך שגם גוף הנר (O/H/L/C) נכון overnight, לא רק סמן המחיר. `_best_price` (midpoint) נשאר fallback בלבד.
- **CVD:** מה-Cumulative Delta של chart #5 → `v9_bars_cumulative_delta`; reset-aware (אמת אם מתאפס 18:00 ET).
- **hydration באתחול:** טען 5-דק' + CVD מהמקור הזה.

## Phase D · בטיחות + אימות
- שערי RTH ללא שינוי — נרות overnight = תצוגה/הקשר, **לא** מזינים ירי (אמת D-091/D-092).
- אפס סינתוז — פער-maintenance נשאר פער.
- **אימות end-to-end:** מחיר-חי זז בכל המשטחים (פס עליון + **פאנל Woodies** + טבלה) — צילום/JSON before/after; 5-דק' רציף; CVD רציף ונכון.

## פלט
`docs/reports/CHART5_CONTINUOUS_SOURCE_2026-06-01.md`: מפת הגילוי (Phase A, ראיות) → החלטת מקור → diff חיווט → אימות end-to-end (כולל פאנל Woodies זז). עדכון `STATUS_BOARD.md`.

**שערים:** diagnose-first — דווח Phase A לפני שינוי. כל שינוי sc_study = strategic-stop + אישור Michael + runbook. firing RTH-gated ללא שינוי. אפס שינוי order/risk/sizing.
