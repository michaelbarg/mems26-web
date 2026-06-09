# רשימת תקלות פתוחות — מוכנות-מסחר היום · 2026-06-09

מקור: תיקוני אתמול-לילה (#1-#5) · `ISSUES_AND_RECOMMENDATIONS_2026-06-09` · אימות-Cowork
(הרצתי את הטסטים בפועל) · `MEMS26_ISSUES_REGISTER` · ההאנד-אוף §5. מטופל **אחת-אחת**.

עיקרון: זו מערכת ב-SHADOW בדרך ל-LIVE — כל שינוי fire-path/trading-logic = **STRATEGIC-STOP +
אישור-Michael** לפני ש-CC נוגע בקוד.

---

## 🔴 A · חוסמי-מסחר (חייב לפני שסומכים על המערכת היום)

**A1 · אימות ירי→שמירה חי (הבאג שפתח הכל)**
אתמול: 0 עסקאות נכתבו ל-`v9_trades`. תוקן בקוד (`23163d9` #2/#4) אבל **לא אומת חי**.
פעולה: ריצת-RTH קצרה → לוודא ב-DB שעסקה נכתבת (`SELECT … v9_trades` + `v9_five_min_setups`).
בלי זה — אי-אפשר לדעת אם המערכת בכלל "סופרת". בעלים: CC (Mac). סטטוס: ⬜.

**A2 · Double-Top יורה 43× על אותו setup (בעיה 3)**
דטקטורים stateless → fire חוזר כל בר אחרי פריצה. בחי = הצפת-פקודות על setup אחד
(ה-cooldown חוסם רוב אבל זה משטח-סיכון אמיתי). תיקון: dedup ברמת-engine
(`last_fire_pattern_id+ts`). trading-logic → **אישור-Michael**. סטטוס: ⬜.

**A3 · סטופים מחווטים נכון לטבלה המוגדרת**
הסטופ+targets מוגדרים per-pattern×day-type. לוודא ש-`compute_stop`/השרשרת באמת קוראת
את הטבלה (`config/*.yaml`) לכל תבנית — לא ערך קשיח. (תיקון #1 הוסיף t1 קשיח של 4 ticks
ל-DLL-fallback — לבדוק שזה תואם את הטבלה.) בעלים: CC. סטטוס: ⬜.

## 🔴 A* · שורשים שאומתו בדוח-האבחון 2026-06-09 (CC + Cowork code-confirmed)

**A*1 · S1 day_type תקוע UNKNOWN (השורש למפל)** — Sierra TPO לא נועל IB (`ib_found=false`) +
`opening_type=NA` → `DayTypeStateMachine` תקוע A3/UNKNOWN → auth ממפה UNKNOWN→Neutral_Center →
INITIATIVE=SKIP + chart-patterns חסומים. **זה הסימפטום של Michael: S1 לא סיווגה אחרי 30 דק' → S2 נעולה
בשעה הראשונה.** (REACTIVE_SHORT כן עבר=FULL → 2 ירי נכתבו ל-`v9_five_min_setups`.) תיקון: FIX 1
ב-`CC_FIX_ROOT_S1_WOODIES_CHART_2026-06-09.md` (diagnose-why→STRATEGIC-STOP). סטטוס: ⬜.

**A*2 · zlr_detected boolean→integer (PG regression)** — `bars_woodies.py:32,36,63 Column(Integer)`
מול כתיבות-boolean → `DatatypeMismatch` → **כל כתיבות woodies_5min נופלות** (8 שורות) → S4 מת + פאנל ריק +
פער-ברים. תיקון: FIX 2. סטטוס: ⬜.

**A*3 · ghost bars / טבלה לא-חיה (סימפטום-Michael #1)** — ts בלי TZ → PG shift ‎-3h; CVD ‎-89,870
לא ב-DB (artifact-תצוגה). תיקון: FIX 3 (UTC מפורש + dedup + עדכון-חי). סטטוס: ⬜.

**A*4 · יציבות** — FiveMinSystem re-hydrate 14× + BarRouter slow 2.3s. תיקון: FIX 4. סטטוס: ⬜.

## 🟡 B · נכונות + אמון (לא חוסם ירי, חוסם הבנת-תוצאה)

**B1 · טסט #3 עדיין מזויף (אומת אמפירית ע"י Cowork)**
הרצתי: החזרת `_det_buf[:-1]→buffer` → הטסט **עדיין עובר** (לא תפס). שניים מתת-הטסטים
משכפלים את החיתוך בתוך הטסט. תיקון: לאמת על פלט `_detect_reactive` האמיתי. (#1+#5 תקינים —
אומתו אדום-on-revert). בעלים: CC. סטטוס: ⬜.

**B2 · I-22 — `pnl_r` מנופח פי-~50**
מטריקת R/P&L שגויה פי-50 → כל חישוב "כמה כסף" שגוי. חייב לתיקון לפני backtest/דוחות.
בעלים: CC (אבחן-קודם). סטטוס: ⬜.

**B3 · CCI של Python ≠ DLL (בעיה 6, פער-CCI §5)** — ✅ **אושר (Michael 2026-06-09)**
Python −98.2 מול DLL שסימן ZLR (≤−100) → Python מפספס ZLR ליד הגבול. **החלטה מאושרת:**
לעבור ל-CCI מה-export של Sierra (source-of-truth); fallback רק אם בר חסר, ואז `source="derived"`
ביושר (Rule 1). מבטל את מחלקת-הפער + מייתר את ה-DLL-fallback. trading-logic → STRATEGIC-STOP בביצוע.

**B4 · I-1 — day_type instance split** (`opening_type=UNKNOWN`/`session_min=0`)
משפיע על סיווג-יום → אילו תבניות מורשות. סטטוס: ⬜.

**B5 · I-18/I-20 — TZ mask / freshness משקר** (`fresh=true` על lag ישן)
תצוגה/אמון; הלוח עלול להראות "טרי" על נתון ישן. סטטוס: ⬜.

**B6 · CVD מקטע-פגום + מיזוג-צ'art** (צילום Michael 2026-06-09) — שתי תקלות נפרדות:
(א) **CVD רץ ל-‎-89,870** מול Sierra ‎-55..1844 → חתימת צבירה-בלי-reset-per-session / סכימת-כפילויות
(Rule 3 · קשור `CC_PROMPT_FIX_5MIN_CVD_DUPLICATION`); + באג-תצוגה: CVD חולק את ציר-המחיר ומנפץ אותו.
**לאמת קודם אם ה-CVD הפגום מזין דטקטור כלשהו** (אז עדיפות גבוהה) או display-only.
(ב) **בר מנותק ב-7440** = artifact של dedup לא-מושלם במיזוג `v9_bars_5min`⊕`woodies` (`bars_5min_history.py`).
הברים עצמם רציפים (hydration תקין). בעלים: CC. סטטוס: ⬜.

## 🟢 C · תשתית/תפעול (לא trading-logic)

**C1 · readiness streams** — ✏️ **S3/footprint לא נוגעים ולא משתמשים עד אחרי LIVE (Michael 2026-06-09).**
לכן I-11 (footprint ingest-break) = **post-LIVE, לא חוסם**. C1 מצטמצם: לוודא ש**זרמי S2+S4 בלבד**
חיים ו-verdict לא נחסם מהם. tick_reversal/tpo כבר non-critical (`a8cb1fb`). סטטוס: ⬜.
**C2 · git** — הענף **26 commits לפני origin**; push מה-Mac לפני כל clone/מעבר. סטטוס: ⬜.
**C3 · בורדים** — ROADMAP+STATUS_BOARD לעדכן ל-5 התיקונים (Cowork). סטטוס: ⬜.
**C4 · אינדקס-דוחות** — אין `_INDEX.md` ל-docs/reports+handoff (~400 קבצים). סטטוס: ⬜.

## 🖥️ E · Frontend (בקשת Michael 2026-06-09 — "לסדר עמוד טריידס + דאשבורד")
לא trading-logic. **אילוצים:** לכבד §Frontend Polling Floors (לא להגדיל אינטרוולים) ·
audit-before-build (למשוך מ-`useBuildStatus` הקיים, לא endpoint חדש).

**E1 · עמוד Trades — ביקורת + תיקון באג (מאוחד עם A1)** — Michael: לעמוד היה באג ולכן
אתמול לא נרשמו/הוצגו עסקאות. **אבחון-שרשרת אחד** (לא להניח את הסיבה): זיהוי → persist
(`v9_five_min_setups`, #2/#4) → `v9_trades` (gateway/trade_manager) → **תצוגת עמוד Trades**.
מצא איפה באמת אבדו, תקן, ואמת ב-DB **וגם** בתצוגה. (אם בנוסף נדרש redesign — `TRADES_PAGE_REDESIGN_2026-06-03.md`.)
בעלים: CC. סטטוס: ⬜.

**E2 · Dashboard — ביקורת + תיקון באג-frontend + חלק-C + ארגון-מחדש** (`CC_COMBINED_DETECTION_FIX_AND_SHADOW` חלק C):
קודם לאבחן+לתקן את באג-הפרונטאנד; ואז:
- (א) פאנל "זיהוי תבניות" (detection) per-pattern S2/S4 (מ-`useBuildStatus`) = **המשטח הבולט/ראשי**.
- (ד) **סקשן TARGETS/STOP** (stop/r_t1/targets/sizing/time per-pattern, רובו "חסר") → **דרופ-דאון/accordion מקופל כברירת-מחדל** — לא בולט; ההדגשה על ה-detection. (ראה צילום Michael 2026-06-09.)
- (ב) תיקון day_type freshness (observer, לא סף-360s) · (ג) זרמים-מושתקים לא אדומים.
בעלים: CC (frontend; §Polling Floors; `useBuildStatus`). סטטוס: ⬜.

## ⚪ D · נדחה במכוון
frontend חלק-C (פאנל SHADOW) · דגל-GRAY (פארק עד #1, שכבר תוקן — לבדוק) · בעיה 7 Initiative
calibration (החלטת-Michael) · בעיה 2 on_bar_close · בעיה 4 ensure_iso_ts · backtester (אפיון נפרד).

---

## סדר-טיפול מוצע (אחת-אחת)
A1 (ירי→שמירה) → A2 (Double-Top dedup) → A3 (סטופים) → B1 (טסט #3) → B2 (pnl_r) →
B3 (CCI) → C1 (readiness) → C2/C3/C4 (תפעול) → D.
**מתחילים ב-A1.** כל פריט: אבחן→ראיה גולמית→STRATEGIC-STOP אם trading-logic→תיקון→אימות (Rule 5).
