# CC PROMPT — ספים תמיד יחסיים + הרצת פתיחה + חסימת-תבנית גלויים

**תאריך:** 2026-06-01 · **מקור:** Cowork (Michael) · **מצב:** SHADOW · Rule 5 · אפס שינוי order/risk/sizing · strategic-stop על שינוי לוגיקה.
**הערה:** #2/#3 (day-type/opening לא רצו) = באג bar_count=0 (`_day_type_on_bar` נשבר) — מטופל ב-`CC_PROMPT_FIX_DAYTYPE_INIT_IB_BUILDSTATUS`. הפריטים כאן נעשים משמעותיים אחרי שהברים זורמים.

## #1 · ספים תמיד יחסיים (ATR/volume), לעולם לא מספר קבוע, בכל סוג-יום
Michael: כל סף חייב להיות **יחסי** (מתכוונן לתנודתיות), אף פעם לא נקודה קבועה — בכל day-type.
- **audit:** עבור על כל הספים ב-S1/S2/S3/S4 (EXPANSION, POC_RET, PROXIMITY, SR, FLOOR, POLE, HEAD, IB width, gap, MIN_LEVEL_VOL, range_ticks, וכו'). לכל אחד: האם יחסי (כשהדגל ON) או עדיין fixed? הדבק טבלה.
- **מדיניות:** הפוך את הנתיב היחסי ל**ברירת מחדל קבועה** (דגלים always-on / להסיר את נתיב ה-OFF אחרי soak), כך שלא משנה סוג-היום — הסף תמיד יחס×ATR/median.
- **fallback ATR=None** (ברים מוקדמים/אין נתון) = מתועד, לא מדיניות "מספר קבוע". 
- **k-values** (היחסים עצמם) נשארים **יחסים** תמיד, מכוילים אחרי soak — אף פעם לא נקודה קבועה.
- 🚩 flag כל מקום שעדיין fixed-per-day-type. **strategic-stop** לפני שינוי ערכי k (priors).

## #4 · הרצת פתיחה מוסברת ב-Build Status
הצג ב-Build Status: `opening_type` + **איך נקבע** — directional_ratio (|net_move|/range), איזה כלל ירה (DRIVE ≥0.7 / TEST_DRIVE pullback 20-60% / REJECTION reversal ≥50% / AUCTION), confidence, ומקור (price / CVD כשהדגל ON + footprint deltas). כך Michael רואה ש**עבד ומה ההיגיון**.

## #5 · לכל תבנית — מה חוסם אותה (גלוי)
לכל תבנית/מערכת (S2 OFA+Chart, S3 4 גלאים, S4 9 patterns): הצג ב-Build Status את **סיבת החסימה המדויקת** בשפה ברורה — איזה תנאי/gate לא מתקיים (day_type_gate / auth SKIP / FHB / chop / mode / detection condition / RTH gate / no-setup). הרחב את ה-"Missing: ..." הקיים ל-S2 לכל התבניות והמערכות. הבחן "חסום-באג" מ-"אין setup כרגע".

## פלט
`docs/reports/RELATIVE_ALWAYS_OPENING_BLOCKERS_2026-06-01.md`: (1) טבלת audit ספים fixed-vs-relative + diff להפיכה ליחסי-קבוע · (2) opening בל-Build Status (screenshot) · (3) per-pattern block reason (screenshot). עדכון STATUS_BOARD.

**שערים:** #1 = מדיניות יחסי-תמיד; strategic-stop על שינוי ערכי k. #4/#5 = observability (תצוגה). אפס שינוי order/risk/sizing. תאם עם `BUILD_STATUS_DAYTYPE_OPENING_VISIBILITY` + `FIX_DAYTYPE_INIT_IB`.
