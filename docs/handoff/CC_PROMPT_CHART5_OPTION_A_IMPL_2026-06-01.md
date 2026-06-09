# CC PROMPT — chart #5 Option A: cross-chart input ב-DLL (מימוש)

**תאריך:** 2026-06-01 · **מקור:** Cowork · **החלטת Michael:** ✅ **Option A** (cross-chart input).
**מצב:** SHADOW · **לא חוסם SHADOW** (רץ במקביל; המיטיגציה הנוכחית עובדת).
**⚠️ זה שינוי `sc_study` — anti-regression (CLAUDE.md §7a).** חובה: לקרוא `docs/runbooks/SIERRA_DLL_OPS.md` + §7a לפני נגיעה · **לא לשבור את export של chart #12** · build+deploy רק לפי הrunbook · **strategic-stop** על כל שינוי מעבר ל-Input האדיטיבי. Rule 5 לכל שלב.

## רקע (Phase A, מאומת)
ה-DLL (`MES_AI_DataExport`) רץ על **chart #12** (RTH session) → כל ה-exports RTH-only. **chart #5** (`MESM26_FUT_CME`, 5-Min, 24h Globex + Cumulative Delta) **לא מייצא**. Option A: להוסיף Input ל-DLL שקורא OHLCV+CVD מ-chart #5 (אותה תבנית cross-chart כמו Woodies/TPO), ולייצא סדרה רציפה.

## Task 1 · DLL — cross-chart input (אדיטיבי בלבד)
- הוסף Input חדש `ContinuousChartNumber` (default = **5**; configurable).
- קרא OHLCV + Cumulative Delta מ-chart #5 דרך ACSIL cross-chart (כמו ה-pattern הקיים ל-Woodies/TPO — `sc.GetChartBaseData`/array-from-chart).
- ייצא ל-**קובץ חדש נפרד** (מומלץ: `5min_continuous.json` + `cumulative_delta_continuous.json`) כדי **לא לגעת** ב-`5min.json`/`cumulative_delta.json` של chart #12.
- **אל תשנה** את ה-export הקיים של chart #12 (RTH) — רק תוספת.
- הצג את ה-diff המוצע ל-DLL **לפני** build/deploy (strategic-stop לאישור).

## Task 2 · build + deploy (לפי runbook בלבד)
- `sc_study/` → `./scripts/build_monolithic_cpp.sh --deploy` → `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` → Remote Build → reload study. דפלוי לשני ה-Sierra installs אם נדרש.
- **רגרסיה חובה:** אחרי deploy, אמת ש-chart #12 ממשיך לייצא תקין (5min.json RTH עדיין מתעדכן, 14 קבצים FRESH). הדבק ראיה.

## Task 3 · backend — חיווט כקנוני
- bridge קולט את ה-export הרציף → טבלה קנונית (5-דק' OHLCV + CVD רציף 24h).
- backend מגיש 5-דק' **OHLC** + CVD + מחיר-חי מהמקור הרציף. `_best_price` (midpoint) → **fallback בלבד**.
- chart/פאנל Woodies/טבלה קוראים מהמקור הרציף → גוף הנר נכון overnight (לא רק סמן מחיר).

## Task 4 · אימות (Rule 5, פלט גולמי)
- נרות overnight בעלי **OHLC אמיתי** (לא O=H=L=C קפוא) — דוגמה מ-Globex.
- רציפות: 0 פערים בחלונות עם נתון.
- CVD רציף, reset-aware (18:00 ET).
- chart #12 RTH exports **לא נשברו** (רגרסיה).
- firing נשאר RTH-gated — נרות overnight לא מזינים ירי.
- צילום/JSON: פאנל Woodies + chart מציגים נרות overnight אמיתיים.

## פלט
`docs/reports/CHART5_OPTION_A_IMPL_2026-06-01.md`: diff DLL · ראיית build/deploy + רגרסיית chart #12 · diff backend · אימות end-to-end (OHLC overnight אמיתי + רציפות + CVD). עדכון `STATUS_BOARD.md`.

**שערים:** strategic-stop — הצג diff DLL לפני deploy. אל תשבור chart #12. שינוי sc_study רק לפי runbook. firing RTH-gated ללא שינוי. אפס שינוי order/risk/sizing. אם chart #5 אינו מספר 5 בפועל — עצור ושאל את Michael.
