# CC הוראת עבודה — תיקון‑עומק ל‑Frozen-Tail בלי נזק

**תאריך:** 2026-05-30 · **כותב:** Cowork · **עקרון:** Diagnose first, no band-aid, no synthesis.
שינויי DLL/לוגיקת‑מסחר → strategic stop + אישור Michael. כל "תוקן" = פקודה+פלט גולמי (Rule 5).

## 0. למה הפלסטר הקיים מזיק (קרא קודם)

התיקון הנוכחי (**Option A**, v9.4.3-p31.1, `ada6c88`) מזהה clamp ב-`mapIdx` ואז
**נופל ל-CCI מחושב ב-Python** (`v9_calc_cci`) דרך ה-fallback `sv==0`. זו **סינתזה** של
ערך Woodies מתוך הברים — ומפרה ישירות את כלל **מקור‑האמת** ב-CLAUDE.md (§ Sierra real-time
data + § Honest failure > synthetic value). כלומר הוא מחליף "ערך קפוא" ב"ערך מומצא שנראה
אמיתי" — וזה גרוע יותר, כי S4 יורה על מספר שלא הגיע מ-Sierra.

**עדות שזה גם לא עבד:** Cowork בדק 2026-05-30 — 5 ברי Woodies אחרונים ב-DB כולם
`cci_14=-40.49` זהים. ה-frozen-tail עדיין נראה בנתונים (או שהתיקון לא תפס, או שזו שארית
שישי — חייב אימות חי ב-RTH).

**מטרה:** למצוא את שורש ה-clamp ולפתור אותו כך ש‑Sierra נשאר מקור‑האמת — **בלי**
לחשב CCI/SWI ב-DLL/Python. אם ערך באמת לא נגיש → propagate `missing`/`None`, לא להמציא.

## 1. מה כבר ידוע (מהאבחון של CC · אל תחזור על זה)

- `Input #18 (WoodiesChartNumber) = 12` → ה-studies חיים בצ'ארט 12, לא בצ'ארט המארח.
- `mapIdx` ממפה index של הצ'ארט המארח → index בצ'ארט 12 דרך
  `sc.GetContainingIndexForDateTimeIndex(wc, dll_bar_idx)` (`v9_woodies_export.h:455-463`).
- ה-freeze קורה כש‑המיפוי **clamp** — מחזיר את אותו index לכמה ברים רצופים → כל 6 שדות
  ה-study קוראים את אותו ערך מצ'ארט 12 (`v9_woodies_export.h:486-527`).
- נתיב `current_bar` קורא `arr[idx]` ישירות בלי mapIdx (`MES_AI_DataExport.cpp:576-621`).
- `bars.py:223-231` מעדיף `history[-1]` על `current_bar` → S4 מקבל את הזנב הקפוא.

## 2. השערות שורש לבדיקה (כל אחת — עם עדות, לא ניחוש)

| # | השערה | איך לבדוק |
|---|-------|-----------|
| H1 | **אי‑התאמת bar period** בין הצ'ארט המארח לצ'ארט 12 (לא שניהם 5-min, או אחד range/tick) → מיפוי DateTime מחזיר אותו index | בדוק bar period של שני הצ'ארטים ב-Sierra; השווה bar count לאותו חלון |
| H2 | **צ'ארט 12 לא טוען מספיק היסטוריה** (Days to Load קטן) → מיפוי clamp ל-index האחרון | בדוק `Days to Load` בצ'ארט 12; הדפס `GetChartArraySize(12)` מול host |
| H3 | **צ'ארט 12 לא מחושב בזמן** (study recalc lag / chart לא מתעדכן) → ערכים תקועים בקצה | לוג `GetContainingIndexForDateTimeIndex` per bar + ts; בדוק אם הקצה תמיד clamp |
| H4 | **התנהגות RTH בלבד** — freeze רק כשצ'ארט 12 עמוס studies ב-RTH | אמת חי 16:30–23:00 IL; השווה ל-overnight |
| H5 | **הארכיטקטורה cross-chart מיותרת** — להריץ את ה-studies על הצ'ארט המארח (Input=0) ולבטל מיפוי | בדוק אם אפשר להוסיף את 6 ה-studies לצ'ארט המארח; השווה ערכים |

> **הכיוון המוביל (H1/H2/H5):** clamp ב-`GetContainingIndexForDateTimeIndex` כמעט תמיד =
> לצ'ארט 12 אין בר שמתאים ל-DateTime של הבר המארח (היסטוריה חסרה או period שונה). אז
> הפתרון הנכון הוא **ליישר את שני הצ'ארטים** (אותו period + מספיק היסטוריה), או **לבטל
> את ה-cross-chart** (H5) — לא לחשב ערך חלופי.

## 3. פרוטוקול אבחון (לוגים זמניים ב-DLL, אמת חי, ואז הסר)

```
1. ב-mapIdx: לוג per-bar של (dll_bar_idx → mapped_idx). זהה מאיזה index מתחיל ה-clamp.
2. הדפס GetChartArraySize(host) מול GetChartArraySize(12) + bar period של כל אחד.
3. probe חי של woodies_5min.json כל 30 שניות במשך 30 דק' RTH — האם הקצה נע או קופא?
4. אמת אם current_bar (arr[idx] ישיר) נע בזמן ש-history[-1] (mapIdx) קופא — אם כן,
   זה מאשר שה-clamp הוא הבעיה ולא הצ'ארט עצמו.
```
**אל תתקדם לתיקון לפני ש-§2/§3 מצביעים על שורש יחיד מאומת בעדות.**

## 4. אילוצי הפתרון (מה מותר ומה אסור)

- ❌ **אסור:** לחשב CCI/SWI/CZI/LSMA/EMA/TCCI ב-DLL/Python ולהחזיר כאילו הם של Sierra.
  זה ה"נזק". בדוק גם אם ה-fallback `v9_calc_cci` הקיים מזין כבר את ה-DB ובודד אותו.
- ✅ **מותר ומועדף:** ליישר את צ'ארט 12 למארח (period + Days-to-Load) כך שהמיפוי לא יעשה
  clamp; או H5 — להעביר את ה-studies לצ'ארט המארח ולבטל את המיפוי (Input=0).
- ✅ אם ערך באמת לא נגיש לבר → החזר `found=false`/`None` ותן ל-UI/S4 להציג "missing"
  (CLAUDE.md Rule 1). עדיף freeze גלוי על ערך מומצא.
- ⚠️ `bars.py:223-231` מעדיף history על current_bar — ודא שזה לא מסתיר freeze (שקול: אם
  history[-1]==history[-2] על כל 6 השדות → אל תרשום, סמן stale).

## 5. אימות (חובה — לא שישי, אלא RTH חי)

```bash
python3 - << 'PY'
import sqlite3; db=sqlite3.connect('file:data/mems26_local.db?mode=ro',uri=True)
rows=db.execute("SELECT cci_14,swi_value FROM v9_bars_5min_woodies WHERE ts<'2099-01-01' ORDER BY ts DESC LIMIT 10").fetchall()
dup=sum(1 for a,b in zip(rows,rows[1:]) if a==b)
print("consecutive identical pairs:",dup,"PASS" if dup==0 else "FAIL — still frozen")
print("last10 cci:",[r[0] for r in rows])
PY
# Axis 2 — current_bar ≈ history[-1] (אותו בר משני נתיבים)
# Axis 3 — 0 ערכים מסונתזים (לוג/flag על כל נפילה ל-v9_calc_cci)
# Axis 4 — latency endpoint < סף
```
**PASS אמיתי = הרצה חיה ב-RTH (ראשון 16:30–23:00 IL): 0 זוגות זהים + 0 ערכים מסונתזים.**
+ regression test ל-clamp שלא חוזר. עדכן ROADMAP/STATUS_BOARD (finding→fix→evidence).

## קבצים/מקורות
`sc_study/v9_woodies_export.h:455-527` · `MES_AI_DataExport.cpp:45,118,576-621` ·
`backend/v9/api/v9/bars.py:223-231` · דוחות `CC_DIAG/FIX_DLL_FROZEN_TAIL_2026-05-29.md` ·
`docs/runbooks/SIERRA_DLL_OPS.md` · CLAUDE.md §§ Sierra real-time data · Source-of-Truth.
