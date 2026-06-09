# CC — תיקון-אב מאוחד (S1/IB · woodies · טבלה-חיה · יציבות · stop/targets · 2026-06-09 ערב)

**ממזג שני אבחונים (Cursor/CC + Cowork) לרשימה אחת מאומתת, מנוכשת-כפילויות, ממוין-שורש.** Cowork אימת כל סעיף מול הקוד+DB החי (raw למטה). עבוד דרך ה-index · **Rule 5 (פקודה+פלט-גולמי לכל תיקון)** · regression לכל באג · **STRATEGIC-STOP לפני נגיעה ב-S1-classification / Sierra / DLL / fire-path**. אל תדליק דגל default-off (`S2_CHOPPINESS_GATE`·`LAYER0_CHOP_GATE`·`S2_REQUIRE_COT_AMT`) · **S3/footprint לא נוגעים (post-LIVE)**.

**מה Michael רואה וחייב להיפתר בפועל:** (1) הטבלה/צ'art מעוות ולא מתעדכן חי · (2) S1 לא סיווגה אחרי חצי שעה → S2 נעולה בשעה הראשונה · (3) **העסקה היחידה של היום (#20) לא בוצעה עם הסטופ והיעדים המוגדרים**.

**עובדות מאומתות (Cowork, raw):**
- `v9_day_type_state` היום: `UNKNOWN/NA/A3`×31 · `UNKNOWN/NA/A2`×7 · `Trend_Normal/NA/B2/EXTREME`×13 — **`opening_type=NA` לכל השורות** (השבר האמיתי). בזמן הירי (16:50) `day_type=UNKNOWN`.
- מחיר אמיתי היום (RTH 5דק'): פתיחה 7458.50 → שיא 7491.00 ב-16:45 → **היפוך וירידה** לסגירה 7415.25 ליד שפל-RTH. NET ‎-43.25 · ‎-76 מהשיא · IB≈75.5נק'. כלומר **דרייב-פתיחה שנכשל → היפוך (≈Variation / טרנד-מטה)** — **לא** Trend_Normal. (כשה-opening_type יתוקן, הסיווג חייב לשקף זאת.)
- `v9_bars_5min_woodies` היום = **17 שורות** (לא 8) → ראה תיקון את חומרת FIX 2.
- עסקה #20 (raw): `day_type_at_entry=None` · `initial_stop=7491.75` · `entry=7489.25` · `t1=7485.75 (1.4R)` · `t2=7482.25 (2.8R)` · הטבלה המוגדרת `targets_table` קובעת **T1=1R לכל day_type**.

═══════════════════════════════════════════════
## FIX 1 🔴 ROOT — S1 day_type תקוע UNKNOWN (`opening_type=NA` · IB לא ננעל)
═══════════════════════════════════════════════
זה השורש למפל UNKNOWN→Neutral_Center(fallback)→INITIATIVE **SKIP** + chart-patterns חסומים (FIX 5 ב-auth תלוי בזה). **אבחן-קודם, אל תתקן עד שהשורש ברור; STRATEGIC-STOP אם זה צד-Sierra/DLL/classification.**

מאומת: `tpo_routes.py:200 ib_found=bool(raw.get("ib_found"))` · `state_machine.py:~405` נופל ל-`Stage.A1`/`DayType.UNKNOWN` כש-IB None · `opening_type=NA` לכל שורות-היום.

1. **מקור-אמת קודם:** `cat ~/SierraChart_Data/v9_export/tpo*.json` — האם יש `ib_found/ib_high/ib_low/opening_type`? או חסר/false? (§Sierra source-of-truth — אל תסנתז; propagate "missing" ביושר, Rule 1.)
2. **הבחן בין שלושה:** (א) Sierra/TPO study לא מייצא IB/opening → **STRATEGIC-STOP + Michael** (צד-Sierra/DLL) · (ב) ה-export מכיל אבל ingest/parse מפיל → תיקון-קוד · (ג) IB לגיטימית עוד לא ננעלה (IB=שעה ראשונה) — **אבל `opening_type=NA` מרמז על שבר אמיתי, לא תזמון**, כי opening_type אמור להיות זמין מוקדם ולא תלוי בנעילת-IB.
3. **spec של Michael (קבוע, לא workaround):** `opening_type` מסווג **≤15 דק'** מהפתיחה · `day_type` ראשוני **≤30 דק'** · **עדכון תוך-יומי שתופס היפוך** (כמו היום: דרייב-מעלה→היפוך-מטה חייב לרדת מ-Trend ל-Variation/מטה) · **נעילת-IB סופית ב-60 דק'**. `S1_DYNAMIC_RECLASS=ON` אבל לא תפס את ההיפוך היום — אבחן למה.
4. **קריטריון-קבלה:** `opening_type≠NA` בחלון-הצפוי · `day_type≠UNKNOWN` אחרי הסיווג · הסיווג **תואם את פעולת-המחיר האמיתית** (היום ≈Variation/מטה, לא Trend_Normal) · INITIATIVE כבר לא SKIP-אוטומטי · chart-patterns נגישים.

═══════════════════════════════════════════════
## FIX 2 🟡 `zlr_detected`/`hfe_detected` boolean↔Integer — חוסר-עקביות (אמת חומרה קודם!)
═══════════════════════════════════════════════
מאומת: עמודה `Integer` (`bars_woodies.py:32,36,63`) · שורה `bars.py:815` ממירה (`1 if ... else 0`) · שורה 919 ממירה hfe · **אבל** שורות `825,917,934,966` כותבות raw-bool (`bar.get("zlr_detected", False)`).
**תיקון לאבחון הקודם:** היום נכתבו **17 שורות woodies** — אז "כל הכתיבות נופלות / S4 מת" **לא מדויק כרגע**. ⇒ **אבחן-קודם איזה נתיב *באמת* נכשל** (אם בכלל): הרץ כתיבה דרך כל INSERT-path ובדוק `DatatypeMismatch` בלוג. **תקן את חוסר-העקביות בכל מקרה** (latent bug): החלטה אחת — או `int(bool(...))` בכל הנתיבים, או החלף עמודה ל-`Boolean` (לא חצי-חצי). **סרוק `safe_writer.py` ל-`*_detected`/בוליאני-לעמודת-Integer דומה** (סיכון-רוחבי, §DB). regression שמוודא כתיבת-woodies מצליחה ב-PG. קריטריון: `count(*) v9_bars_5min_woodies` מטפס בלי שגיאות-לוג.

═══════════════════════════════════════════════
## FIX 3 🟡 טבלה/צ'art: עדכון-חי + עיוות (ghost bars / dedup / CVD) — סימפטום-Michael #1
═══════════════════════════════════════════════
מאומת: ghost bars ב-`v9_bars_5min` (ts בלי TZ → PG פירש כשעון-ישראל, shift ‎-3h) · CVD ‎-89,870 = artifact-תצוגה.
1. **ghost bars:** מצא את נתיב-הכתיבה שכותב `ts` בלי TZ → כתוב `timestamptz` עם **UTC מפורש** (Rule 4 — אין TZ-ambiguity) + ודא dedup-במיזוג (`bars_5min_history.py:~90-106`) מסיר כפילויות-ts.
2. **עדכון-חי:** הצ'art קורא `v9_bars_5min_continuous` קודם — ודא רענון-חי (polling/ws) לפי **§Frontend Polling Floors (אל תגדיל אינטרוולים)**. אם קפא — ייתכן בגלל FIX 2 (woodies-panel ריק) או FIX 4 (process_bar איטי).
3. **CVD על pane נפרד** (`CumulativeDeltaPane.tsx`), לא על ציר-המחיר. קריטריון: צ'art מתעדכן חי בלי ghost/עיוות.

═══════════════════════════════════════════════
## FIX 4 🟡 יציבות — re-hydrate 14× · BarRouter SLOW 2386ms
═══════════════════════════════════════════════
`FiveMinSystem` הִדרֵט 14+ פעמים (16:30-17:12) — אמור startup+בר-חדש בלבד → אבחן (לולאת-restart? קריאה-כפולה?) → תקן. `BarRouter SLOW handler process_bar 2386ms` בזמן fire → אבחן (DB commit סנכרוני? hydrate בתוך process_bar?). שניהם יכולים לגרום ל"קפוא"-תצוגה. raw לכל אחד.

═══════════════════════════════════════════════
## FIX 5 🔴 stop/targets לא לפי הטבלה המוגדרת — הבאג של עסקה #20 (בקשת-Michael מפורשת)
═══════════════════════════════════════════════
מאומת על עסקה #20 (S4 HTLB SHORT): `day_type_at_entry=None` · יעדים `t1=1.4R · t2=2.8R` (יעדי-טיקים קבועים של Woodies/HTLB) — **לא** `targets_table` (שקובע **T1=1R** לכל day_type). בנוסף Calibration: "T1 hit but stop never moved to BE" → ה-BE-move לא בוצע למרות T1.

**הדרישה (per §Standing — stop+exits(T1-Tn)+contracts YAML-tunable, per-pattern×day-type):**
1. **אבחן-קודם:** מאיפה S4/Woodies מושך stop+targets? (`woodies/patterns/htlb.py` · `_pattern_ticks.py` · `woodies_system.py`) — האם הוא **עוקף** את `targets_table`/`stop_anchors` ומשתמש בטיקים-קבועים? הדבק את הנתיב.
2. **תקן:** S4 (וגם S2) מושכים **stop + T1..Tn + מספר-חוזים מהטבלה המוגדרת per-pattern×day-type** (לא טיקים-קבועים מקודדים). כש-`day_type=None` — זה תלוי-FIX 1; עד שמסווג, אל תירה עם יעדים שרירותיים (תעד החלטה: skip או provisional — **STRATEGIC-STOP ל-Michael על מדיניות-הירי בשעה הראשונה**).
3. **BE-move:** על T1-hit, הסטופ זז ל-BE לפי ה-spec — ודא שזה קורה (היום לא קרה). regression: על T1_hit → `stop==entry` (±offset-spec).
4. **regression חוזה:** שחזר את קלטי-עסקה #20 → assert ש-stop+targets **תואמים את הטבלה** ל-(HTLB × day_type הנכון), לא 1.4R/2.8R. הוכח RED-on-revert.

> **trading-logic = STRATEGIC-STOP.** אל תשנה ערכי-טבלה/מדיניות בלי אישור-Michael; כאן התיקון הוא **לצרוך את הטבלה**, לא להמציא ערכים.

═══════════════════════════════════════════════
## FIX 6 🟡 Dashboard — פאנל זיהוי-תבנית + דירוג פר-מערכת (S1/S2/S4) · בקשת-Michael
═══════════════════════════════════════════════
Michael רוצה בטאב **Shadow** (כרגע "coming in later prompts"), פר-מערכת **1·2·4** (S3 לא — post-LIVE; 5/6 הם context), תצוגה של **כל תבנית + סטטוס-זיהוי + דירוג/ציון**, כדי לעקוב פר-מערכת.

מאומת מה-endpoint `GET /api/v9/build/pattern-status` → `systems[]` (list) — כבר מחזיר פר-מערכת `patterns[]` עם `{id,name,status,label}` (status=`armed`/`blocked`) + `interpretations` (S2: `DAY_TYPE_MODE·Trend_Normal·OPEN_DRIVE` · S4: `downtrend continuation SHORT·CCI=-115·1 detected` · S1: `Trend_Normal·OPEN_DRIVE·DEVELOPING`). **חסר: דירוג/ציון פר-תבנית** — ה-`patterns[]` נושא רק status, לא tier/grade.

1. **Backend (additive, לא fire-path):** הוסף לכל איבר ב-`systems[].patterns[]` שדה **`grade`/`tier`** (+ `score`/`confidence` אם קיים) פר-תבנית. המקור הקנוני = ה-**tier מה-Auth Table** פר `pattern × current_day_type` (אותו tier ש-`setup_emitter` כבר מחשב: HIGH/MEDIUM/LOW/SKIP). אל תמציא ציון — משוך מהטבלה (Rule 1). כש-`day_type=UNKNOWN` (תלוי FIX 1) → הצג `tier="—"`/pending ביושר, לא ציון-שקר.
2. **Frontend (`useBuildStatus`; §Polling Floors — אל תגדיל אינטרוולים):** בטאב Shadow, כרטיס פר-מערכת **S1·S2·S4** → רשימת תבניות עם status (🟡/❌/🟢) **+ הדירוג** ליד כל תבנית, ושורת-context מה-`interpretations`. עקבי עם הסגנון של הרצועה העליונה (FIRING/OBSERVING) בצילום.
3. **קריטריון-קבלה:** Michael רואה בטאב Shadow, פר S1/S2/S4, את התבניות עם הדירוג שלהן, מתעדכן חי. (כש-FIX 1 יתוקן, ה-day_type/opening_type בכרטיס-S1 ישקפו את הסיווג האמיתי — מאפשר לתפוס מיסּ-קלסיפיקציה ויזואלית.)

═══════════════════════════════════════════════
## שערי-אימות מקשרים (אחרי התיקונים) — קריטריון-קבלה כולל
═══════════════════════════════════════════════
1. **FIX 1→auth:** `opening_type≠NA` · `day_type≠UNKNOWN` בחלון · הסיווג תואם מציאות (היום ≈Variation/מטה) · `setup_emitter` כבר **לא** עושה `Neutral_Center fallback → SKIP` כש-day_type ידוע · chart-patterns נגישים.
2. **FIX 2:** `v9_bars_5min_woodies` מטפס · אין `DatatypeMismatch` בלוג.
3. **FIX 3:** צ'art חי בלי ghost · CVD ב-pane נפרד.
4. **FIX 5:** הירי הבא נכתב ל-`v9_trades` **עם stop+targets מהטבלה** (לא טיקים-קבועים) · BE זז על T1 · **ומוצג בעמוד Trades** (סגירת הבאג של אתמול).

═══════════════════════════════════════════════
## פורמט תשובה (Rule 5) + סדר
═══════════════════════════════════════════════
לכל FIX: **שורש (file:line) · diff/commit · פלט-גולמי שמוכיח (SQL/לוג/צ'art) · regression (RED-on-revert לבאגים)**. 
**סדר:** FIX 1 (root · diagnose→STRATEGIC-STOP אם Sierra/classification→fix) → FIX 2 → FIX 3 → FIX 4 → FIX 5 → FIX 6 (dashboard). 
**עדכן בורדים** (`ROADMAP_TO_LIVE.html`+`STATUS_BOARD.md`, finding→fix→verification) · **דוח** `docs/reports/MASTER_FIX_2026-06-09.txt` עם **סעיף NOT-DONE** · **commit** (ענף-26 ahead — Michael ידחוף).

**מה ש-Cowork יבדוק בחזרה (Rule 5):** raw של FIX 1 (export+day_type≠UNKNOWN+סיווג-תואם-מציאות) · איזה נתיב-woodies נכשל בפועל (FIX 2) · ghost-bars=0 (FIX 3) · ו-**RED-on-revert של regression עסקה #20** (FIX 5). אל תכריז "done" בלי אלה.
