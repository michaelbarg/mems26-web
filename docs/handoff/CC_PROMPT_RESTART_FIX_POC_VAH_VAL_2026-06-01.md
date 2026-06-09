# CC PROMPT — restart + תיקון POC/VAH/VAL של היום · diagnose-first

**תאריך:** 2026-06-01 (RTH פתוח) · **מקור:** Cowork (Michael) · **מצב:** SHADOW · diagnose-first · Rule 5 · אפס שינוי order/risk/sizing · source-of-truth (POC מ-Sierra TPO, אפס סינתוז).

## ⚠️ זהירות — RTH חי, איסוף Day 1, עסקה פעילה
SHADOW אוסף עכשיו; יש **עסקה פעילה S4 HTLB SHORT @7590.50**. restart יוצר פער קצר + מאתחל state בזיכרון.
- **לפני restart:** ודא שה-restart-recovery (R2-9) יטען מחדש: (a) העסקה הפעילה מ-`v9_trades` (BarLevelDetector ממשיך לנטר), (b) day_type/opening_type, (c) IB. אם משהו לא משוחזר — **strategic-stop ודווח ל-Michael** לפני restart.
- מזער את חלון הפער; תעד את הזמן.

## 🎯 הבהרת Michael (1/6): המקור כבר תקין — לבדוק את **הגשר**, לא את ה-DLL
ה-POC/VAH/VAL **כבר נלקחים מ-chart 3 ב-Sierra** (שם ה-TPO/VA הנכון: POC 7594.75/VAH 7593.50/VAL 7582.75). **אין צורך לשנות את ה-DLL/המקור.** החשד: **הגשר (bridge) לא יודע מאיפה לקחת / לא מעביר נכון** את ה-POC לבק-אנד. **בדוק את הגשר — לא לגעת ב-sc_study.**

## Phase A · אבחון הגשר (diagnose-first, READ-ONLY)
1. **איזה קובץ export הגשר קורא** עבור POC/VAH/VAL? (`tpo.json`? קובץ אחר?) מאיזה chart הקובץ הזה מקורו — chart 3 (הנכון) או chart 12/אחר (שגוי)?
2. **השדות:** האם הגשר קורא את שדות ה-poc/vah/val הנכונים מהקובץ ומעביר ל-`/api/v9/...`? האם יש mismatch בשם-שדה / קובץ ישן / לא נקרא בכלל?
3. **השווה:** ערך ב-export שהגשר קורא → ערך שהבק-אנד מקבל → ערך בדאשבורד (7583.25) מול Sierra chart 3 (7594.75). איפה נשבר/מתפצל.
4. `key_levels_routes.py:122-125` = pass-through מ-`sierra.get(...)` → אם הבק-אנד מקבל ערך שגוי, מקורו בגשר (קובץ/שדה לא נכון). **restart לבדו לא יתקן.**
לאמת:
1. **pass-through:** האם `today.poc/vah/val` ב-API == בדיוק הערכים ב-`tpo.json` (Study ID:3) ברגע נתון? מה מצב `va_ok`? הדבק את שניהם.
2. **סיווג השורש:**
   - אם API == tpo.json אך tpo.json עצמו "שגוי" → **בעיית קונפיג Sierra Study ID:3** (איזה session מפרופל / boundary) → **תיקון ב-Sierra (Michael), לא backend.**
   - אם `va_ok=false` או early-RTH → ה-VA לא בשל (מתפתח) — לא באג.
   - אם API ≠ tpo.json (גרסה stale/cache) → באג backend → תקן.
3. **ערכי Sierra chart 12 ground-truth (Michael, צילום 1/6 RTH):**
   IB High **7604.75** · IB Mid 7591.13/7589.50 · IB Low **7577.50** · TPO POC **7594.75** · TPO VAH **7593.50** · TPO VAL **7582.75** · + קבוצה שנייה: TPO POC **7586.25** · TPO VAL **7579.00**.
   **דאשבורד מציג:** TODAY POC 7583.25 / VAH 7588.25 / VAL 7578.25 → **אי-התאמה** (IB כן תואם 7604.75/7577.50). ⚠️ ב-Sierra **שתי קבוצות TPO POC/VAL** — קבע איזה value-area study ה-DLL מייצא כ-Study ID:3, איזה Michael רוצה (היום), והאם הדאשבורד קורא stale/study-שגוי. ייתכן שצריך לכוון את ה-DLL/Sierra לייצא את ה-VA הנכון (strategic-stop אם DLL).
4. **דווח את השורש לפני כל תיקון** — אל תניח שזה backend (ה-IB תואם → ה-pipeline עובד; כנראה study/בחירת-VA שגויה).

## Phase B · תיקון בגשר (לא DLL)
- אם הגשר קורא קובץ/שדה לא נכון ל-POC/VAH/VAL → **תקן את הגשר** שיקרא מהמקור הנכון (chart 3 export) ויעביר לבק-אנד. smallest correct change. **לא לגעת ב-sc_study.**
- אמת: הדאשבורד מציג עכשיו POC 7594.75 / VAH 7593.50 / VAL 7582.75 (תואם Sierra chart 3).

## Phase B+ · שהכל מסונכרן (audit סנכרון מלא — Michael)
אמת שכל השרשרת מסונכרנת: **Sierra → bridge → backend → DB → dashboard**, ושכל הערכים תואמים מקצה-לקצה:
- POC/VAH/VAL · IB · מחיר-חי · Woodies studies · day-type/opening · session range.
- לכל ערך: Sierra (ground-truth מ-Michael) == export == backend == dashboard? סמן כל מקום שמתפצל (קובץ ישן / שדה שגוי / cache / chart שגוי).
- ודא local-only, אפס סינתוז, אפס ערך שגוי שנובע מ-bridge mis-wiring.

## Phase C · restart בטוח + אימות
- restart ה-backend (launchctl/launcher, בדוק listeners קודם).
- אמת (Rule 5, פלט גולמי): health 200 · **העסקה הפעילה שוחזרה** (S4 SHORT עדיין מנוטרת) · **TODAY POC/VAH/VAL נכונים** (RTH של היום, תואמים Sierra) · IB נשמר · האיסוף ממשיך (setups חדשים נרשמים).

## פלט
`docs/reports/RESTART_FIX_POC_VAH_VAL_2026-06-01.md`: מקור+שורש POC/VAH/VAL · diff תיקון · אימות restart (עסקה משוחזרת, POC/VA נכונים, health). עדכון STATUS_BOARD.

**שערים:** strategic-stop אם restart-recovery לא משחזר את העסקה/state. POC מ-Sierra TPO בלבד (אפס סינתוז). אפס שינוי order/risk/sizing. דורש ערכי Sierra ground-truth מ-Michael להשוואת POC/VA.
