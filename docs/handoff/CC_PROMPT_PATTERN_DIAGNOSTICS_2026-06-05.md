# CC — Pattern Firing Diagnostics · בדיקה כל 30 דק' + EOD + לקחים + תחזית-נגד

**מטרה:** לכל תבנית בכל מערכת, כל 30 דק' ב-RTH — לתעד: נדרכה? נורתה? ואם לא, **למה
בדיוק** (התנאי/השער המדויק שחתך), עם **ערך-הקלט מ-Sierra** שהוביל להחלטה. בסוף-יום:
טבלה מסודרת + לקחים + תחזית-נגד (מה היה קורה אילו נורתה).

**כללי-ברזל:**
- **קריאה/תיעוד בלבד — אל תיגע בלוגיקת-ירי/risk.** זו דיאגנוסטיקה.
- **Sierra = source-of-truth** לערכי-הקלט (CCI/study fields/OHLC) — לא חישובי-בקנד.
  סיבות-הדחייה נלקחות מ-decision_tree של המערכת, אבל **כל ערך-קלט מצליבים מול
  `~/SierraChart_Data/v9_export/`**.
- כל "DONE" = paste פקודה + raw output (Rule 5).

---

## 1. רשימת התבניות (לכסות את כולן)
- **S2 (five_min):** `REACTIVE_LONG/SHORT` · `INITIATIVE_LONG/SHORT` · `INV_HNS` ·
  `HNS_TOP` · `DOUBLE_BOTTOM_EE` · `DOUBLE_TOP_AA` · `BULL_FLAG` · `BEAR_FLAG`.
- **S3 (footprint):** `ABSORPTION` · `STACKED_IMBALANCE` · `SWEEP_RETURN` · `EXHAUSTION`.
- **S4 (woodies):** `ZLR` · `TLB` · `TT` · `GB100` · `HFE` · `HTLB` · `FAMIR`.
- (S1=observer, S5=TPO לא-מחווט, S6=killzone gate — לתעד כ-gates, לא כתבניות-ירי.)

## 2. מה לאסוף — כל 30 דק' (08:30–15:00 CT), לכל תבנית
לכל תבנית, בכל חלון של 30 דק', שורה עם:
| שדה | מקור |
|-----|------|
| `armed` (נדרכה/eligible) | S2: FHB state (ACCUMULATING→EARLY בבר 4 וכו') · אחרות: system running + preconditions |
| `evaluated` (ה-detector רץ על הברים) | decision_tree של המערכת |
| `fired` (נוצרה עסקה) | `v9_trades` (firing_system) |
| `reject_reason` (אם לא נורתה — **התנאי המדויק**) | decision_tree stage + anti-pattern (AP1/AP6/AP8…) + gateway `blocked_by` (session/killzone/chop/cooldown/cluster) |
| `sierra_input` (הערך שחתך) | `~/SierraChart_Data/v9_export/` — CCI-14/TCCI/OHLC הרלוונטי לאותו בר |
| `not_armed_reason` (אם לא נדרכה) | FHB state / mode / opening_type=Nontrend / system down |

**תיעוד:** append שורות לקובץ **`docs/reports/PATTERN_DIAG_2026-06-05.md`** כל 30 דק'
(לא דריסה). פורמט-שורה קצר + raw מאחורי כל החלטה.

## 3. הצלבת-קלט מול Sierra (חובה — "ראיה מושלמת")
לכל `reject_reason` שמבוסס על ערך (למשל ZLR "pullback>12 bars" או "cci<-200"):
הדבק את **ערך-Sierra הגולמי** מאותו בר ליד ערך-הבקנד. אם יש פער Sierra↔backend →
**זה ממצא בפני עצמו** (מפר Sierra=SoT) — סמן אותו.

## 4. דוח EOD (15:00 CT) — טבלה מסודרת
`docs/reports/PATTERN_EOD_2026-06-05.md`:

| מערכת | תבנית | נדרכה # | נורתה # | לא-נדרכה # (סיבות) | לא-נורתה # (פירוק סיבות-דחייה) | תחזית-נגד: W/L, ΣR |
|-------|-------|---------|---------|-------------------|------------------------------|--------------------|

+ **סיכום לקחים:** אילו תבניות נדרכות הרבה ולא יורות (ולמה) · אילו לא נדרכות (ולמה) ·
האם הדחיות נראות **מוצדקות** או **שמרניות-מדי** (לפי התחזית-נגד).

## 5. תחזית-נגד (counterfactual) — "מה היה אילו נורתה"
לכל signal שזוהה-אך-נחסם/לא-נורה: חשב `entry/stop/T1/T2` לפי ספק-התבנית, ואז **שחזר
את הברים שבאו אחריו בפועל** (מ-`v9_bars_5min` / Sierra) וסמן: hit_T1 / hit_T2 /
stop_hit / timeout → `R` ותוצאה משוערת. צבור ל-`ΣR` ול-win-rate היפותטי פר-תבנית.
זה מראה אם הסף שחסם עלה לנו על עסקה טובה או חסך לנו הפסד.

## 6. תיאום זמן
הרץ כ-cron/loop על ה-Mac כל 30 דק' ב-RTH. הראשון: עכשיו. ה-EOD: 15:00 CT.
**אל תריץ dev-server נוסף** — קרא מה-DB/exports של המערכת הרצה.

## 7. NOT-DONE
ציין כל תבנית שלא הצלחת למפות לה reject_reason, וכל פער Sierra↔backend שנמצא.
