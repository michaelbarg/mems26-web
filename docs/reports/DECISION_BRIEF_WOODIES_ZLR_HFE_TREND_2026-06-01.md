# Decision Brief — Woodies: ZLR / HFE / Trend-State Filtering · 2026-06-01

**תווית החלטה:** `D-WDIAG` (ראה `docs/plans/DECISION_LEDGER.md`)
**סטטוס:** 🟡 **ממתין להחלטת Michael** — נוגע ב-firing logic של S4. **אפס קוד שונה.**
**מחבר:** Cowork agent · **מקור מחקר:** מחקר חיצוני שסיפק Michael (2026-06-01, Woodies CCI doctrine)
**רקע:** `AGENT_FIRE_AUDIT_VISIBLE_WINDOW_2026-06-01.md` §4 · `DAY1_DEEP_ANALYSIS_2026-06-01.md` §4

> ⚠️ **תיקון לדוח ה-fire-audit שלי:** המחקר משנה את הפרשנות של "8 ZLR שפוספסו". ראה §1 — חלקם (זיהוי-pullback של ה-DLL) **לא** היו entries תקפים לפי הדוקטרינה. honest update לפי verify-before-trust.

---

## 1 · ZLR — confirmed bounce הוא הדוקטרינה (Conflict 1)

**מה המחקר אומר:** ZLR תקף = pullback לכיוון ה-ZL **ואז היפוך/hook חזרה לכיוון המגמה** ("the first bar that flips up away from the zero-line"). Wood מפורשות: *"I always wait until it crosses back over the zero line… it really hasn't rejected it until it crosses back over."* pullback בלבד = setup מתהווה, **לא** entry.

**מה הקוד שלנו עושה (מעוגן):**
- `zlr.py::detect` דורש `current > prev` ו-`0<current<200` (Stage 3) — **זה בדיוק Implementation B (confirmed bounce)** → **נאמן לדוקטרינה.** ✅
- **אבל** `woodies_system.py:307-318` (commit `58d6538`, "DLL trust as primary") **עוקף:** אם ה-DLL מסמן `zlr_detected` ו-Python לא זיהה — מוסיף ZLR מה-DLL (conf 0.65) **בלי** בדיקת ה-bounce. ה-DLL מזהה ב-pullback (Implementation A). → **אנחנו יורים על pullback שה-Python (B) דחה נכון — מנוגד לדוקטרינה.**

**משמעות ל-fire-audit §4:** ה-"8 ZLR שה-DLL סימן" — חלקם זיהויי-pullback (Impl A) ש**לא** היו צריכים לירות. רק אלה עם confirmed bounce (current>prev) הם entries תקפים. ה-"miss" קטן ממה שדיווחתי.

**הכרעה מוצעת:** הצמד את ה-confirmed-bounce גם לנתיב ה-DLL — ZLR יורה רק אם **גם** `current>prev` מתקיים (לא pullback בלבד). + פילטר מומנטום: הפרש ~15–20 נק' CCI בין הבר הקודם לבר ה-entry; אל תרדוף אם הבר סוגר מעל ~+120 ("Don't Chase").

## 2 · HFE — counter-trend / exit, לא peer של ZLR (Conflict 2)

**מה המחקר אומר:** HFE הוא canon מקורי (pattern #7) **אבל counter-trend** שמתחילים לא אמורים לסחור, ומשמש גם כ-**exit** (exit-rule #4). טריגר: CCI ב-±200 ואז hook חזרה ל-ZL. ~50% win (טענת club, לא מאומת).

**מה הקוד שלנו עושה (מעוגן):**
- `hfe.py` — DLL-primary, ±200, hook≥50, AP5 `bars_ago∈[2,12]`, `group=REVERSAL`. ✅ תואם הגדרה.
- `PATTERN_TIER` (woodies_system.py:663) — **HFE לא ברשימה** → `calculate_size` נופל ל-`base_tier='low'`. → **HFE כבר low-tier** (לא peer של ZLR שהוא high). חלקית מיושר עם הדוקטרינה כבר. ✅

**הכרעה מוצעת:** השאר HFE כ-counter-trend/exit; שמור low-tier (size מצומצם/reject); שקול **תפקיד exit ראשי** ליציאה מ-ZLR/TLB with-trend מורווחות. לא לקדם ל-peer של ZLR.

## 3 · Trend-state filter (P-W5 / gray) — הנחה שגויה (Design Q3)

**מה המחקר אומר:** כלל ה-no-trade ב-gray/no-trend הוא דוקטרינה **לתבניות המשך** (ZLR/TLB/TT/GB100). **אבל חסימת HFE ב-gray נשענת על הנחה שגויה:** HFE דורש extreme ±200 שמושג רק במגמה **חזקה ומבוססת** (blue/red עמוק) — כמעט לעולם לא ב-gray. אם המסווג שלנו **כן** חוסם HFE ב-gray → זה **באג תיוג** (trend מתייג ברי-extreme כ-gray, או ש-HFE detector יורה על רעש ליד אפס).

**מה הקוד שלנו עושה (מעוגן):**
- `woodies_system.py:358` — P-W5 LOCK A: YELLOW חוסם את כל 9. DAY1 §4 דיווח: **17 HFE נחסמו ב-GRAY** (P-W5).
- → אם 17 HFE נחסמו ב-GRAY, לפי המחקר זה **בדיוק הסימפטום של באג התיוג** — או ש-trend_state טעה בברי-±200, או ש-HFE זוהה על near-zero.

**הכרעה מוצעת:** (א) שמור no-trade ב-gray ל-תבניות המשך. (ב) **נתק את HFE מפילטר ה-gray** — שער אותו על ±200 + Sidewinder/LSMA + כללי counter-trend, לא על צבע trend. (ג) **AUDIT (ליבת D-WDIAG):** בדוק אם ה-gray classifier אי-פעם יורה על בר-±200 אמיתי. אם כן → באג תיוג לתקן. אם אף פעם → הורד את לוגיקת ה-exemption כמיותרת.

## 4 · אופציות החלטה (Michael)

| # | נושא | אופציות |
|---|------|---------|
| ZLR | נתיב DLL pullback | **A** הצמד confirmed-bounce גם ל-DLL (מומלץ) · **B** revert מלא ל-Python-only · **C** השאר כמו היום (יורה על pullback) |
| HFE | תפקיד | שמור low-tier counter-trend (מומלץ) · + הוסף תפקיד exit · (לא לקדם ל-peer) |
| Gray | P-W5 | הרץ **audit תיוג** קודם (diagnostic) → ואז החלט אם לנתק HFE מ-gray |

**המלצתי:** ZLR=**A**, HFE=שמור low-tier+exit, Gray=**audit קודם**. כל אלה הם **D-WDIAG** — האבחון של "למה Woodies לא ירה" שתוזמן אחרי Reactive+S1.

## 5 · תוכנית אימות
- backtest Impl A (pullback) מול B (confirmed-bounce) על MES 5-דק' אחרי עלויות — אם A לא עדיף מובהק, B הוא ברירת המחדל הדוקטרינרית.
- audit: כמה ברי-±200 (HFE אמיתי) סווגו GRAY? (אם >0 → באג תיוג).
- כמה HFE אמיתיים מתנגשים עם gray? אם ~0 → הורד exemption כמיותר.
- Rule 5 לכל מספר (command + raw output מ-`v9_bars_5min_woodies`/`v9_woodies_signals`).

## 6 · Caveats (מהמחקר — כמו שהם)
- **"WSI" (Wait/Sit/Inspired) לא אומת** כמונח Wood — אל תצטט כ-canon (משמעת הסבלנות עצמה מתועדת היטב, האקרונים לא).
- **~50% win של HFE = טענת Wood/club**, לא סטטיסטיקה מאומתת עצמאית.
- העדף את ה-manual ואת ציטוט Wood על פני מקורות צד-ג' שמתארים ZLR ברופף ("reverses before crossing").
- range-bars מול time-bars: היישום שלנו ב-5-דק' עקבי עם דוגמאות ה-minute-bar של ה-manual — ההגדרות עוברות נקי.

---
*אפס קוד שונה. מסמך החלטה/אבחון בלבד (D-WDIAG). עם אישור → CC מריץ audit תיוג + מימוש לפי האופציות, עם raw verification ועדכון roadmap/ledger.*
