# CC — מאוחד: תיקון detection בר-חלקי (שורש) + near-miss/ראיות + Pattern-Detection ב-Shadow tab · 2026-06-08

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md` + `CC_VERIFICATION_PROTOCOL.md`. כל "DONE" = פקודה + **פלט גולמי** (Rule 5) + NOT-DONE.
**קרא קודם:** `CLAUDE.md` (§Chop Gates · §"S2 ⟂ S3" · §Index) + `MEMS26_ISSUES_REGISTER.md`.
מאחד שני פרומפטים: (חלק A) תיקון-השורש שמצאת, (חלק B+C) ההמשך מ-`CC_FOLLOWUP_NEARMISS_AND_SHADOW_PATTERNS_2026-06-08.md`.

> ## ⛔ אבחן-ופ-עצור לפני ביצוע (gate מחייב — חלק A)
> **אסור לגעת בקוד של חלק A לפני שלב-האבחון אושר.** קודם **אבחן בלבד** והוכח את ההשערה עם **דאטה גולמית**
> (Pre-LIVE: "Diagnose first, fix second · verify the hypothesis with data BEFORE touching code"):
> 1. **הוכח שה-b4 חלקי בזמן-detection** — לוג-חי של OHLC+vol של b4 ב-push-הראשון של בר חדש מול הערך הסופי של אותו בר (לא הסקה מהקוד — דאטה).
> 2. **מַפֵּה את הנתיב המדויק** — `process_bar` (`:874-886` is_new_bar/append/return) → `:917 _detect_reactive(self._bar_buffer)` → `:532 b4=bars[-1]` → קונפירמציה `:585/619`. צטט שורות אמיתיות.
> 3. **הוכח את הפער engine↔inspector בדאטה** — אותו בר: מה ה-engine העריך (push-ראשון) מול מה ש-`s2_pattern_probe` מראה (זמן-שאילתה).
> 4. **מַפֵּה מה ה-emit צורך** (entry/stop/targets — `:102`) כדי שהתיקון לא יתפצל.
> 5. **הצע את התיקון** (איזה קריאות מקבלות `buffer[:-1]`, מה נשאר על הבאפר-המלא) — **בלי לבצע**.
>
> ⛔ **STRATEGIC-STOP:** מסור את חבילת-האבחון (raw) ל-Michael. **Cowork יבקר אותה (Rule 5)** — ורק אחרי
> אישור-Cowork **+ אישור-Michael** תעבור ליישום חלק A. חלקי B (חקירה) ו-C (frontend, לא-fire-path) מותר להתחיל במקביל;
> **חלק A נעול עד-אישור.**

═══════════════════════════════════════════════════
## חלק A — תיקון השורש: detection רץ על בר-חלקי (b4) [עדיפות עליונה]
═══════════════════════════════════════════════════

### 🎯 GROUND-TRUTH של Michael (2026-06-08) — יעד-אימות מחייב
המערכת **לא ירתה** למרות setups אמיתיים שאומתו ב-Sierra:
- **Woodies/S4:** ה-study של Sierra (Chart Woodies-CCI) סימן **3 ZLR** היום (חצים אדומים "ZLR"). ⇒ ZLR **כן** התרחשו, Sierra זיהתה, המנוע **לא ירה**. הוכחה שזה באג-זיהוי, לא "אין setup".
- **S2/Five-Min:** Michael מזהה **4 עסקאות-איכות** ב-Chart-3 (5-דק') שהמערכת הייתה צריכה למצוא (אחת מהן הוא לקח ידנית: 2@7432, +54.5P).
**חובה על CC — שני מסלולים נפרדים (אל תערבב):**
- **S2 (4 עסקאות) = באג-בר-חלקי.** שחזר בר-אחר-בר: מה ה-engine העריך כש-b4 חלקי, מול active_patterns ומול ה-inspector.
- **S4/ZLR (3 ZLR) = מסלול-DLL, לא b4.** Woodies סומך על דגל-ה-DLL `wb.zlr_detected` ישירות (`woodies_system.py:262-263,310-313`).
  עקוב אחרי `zlr_detected` מ-יצוא-Sierra → `bar` → `wb` → `patterns` → `decision_tree._a1_trend_gate` → fire, ומצא היכן נשבר:
  (1) השדה מאוכלס/נקרא ביצוא? (2) נחסם downstream — A1 `GRAY+conf<0.55` / sizing=reject / RTH-gate? (3) **חשד-Cowork:**
  `woodies_system` עושה `append` לבאפר על **כל push** (`:235-237,301`), לא רק על בר-חדש ⇒ ~20 עותקים חלקיים של אותו
  בר-5דק' בבאפר → detection רב-ברי משובש. אמת זאת והדבק את הבאפר בזמן-ZLR.
הצלב מול חותמות-הזמן של ה-ZLR ב-`~/SierraChart_Data/v9_export/`.
**אבחון מאומת (Cowork הצליב מול הקוד):** `process_bar` מריץ detection **רק על ה-push הראשון של ts חדש**
(`five_min_system.py:874-886`), אחרי שהבר-החדש כבר `append` (`:878`), ו-`:917 _detect_reactive(self._bar_buffer)`
מקבל באפר שמסתיים בבר-החדש. `:532 b4=bars[-1]` — ולכן **בר-הקונפירמציה/הכניסה (b4) תמיד מוערך כשהוא בבנייה**
(OHLC חלקי), אף פעם לא בסגירתו → הקונפירמציה לא מתקיימת → S2 כמעט אף פעם לא יורה.
**תיקון Cowork לאבחון שלך:** הבר החלקי הוא **b4** (`bars[-1]`), לא b1 — b1/b2/b3 (`bars[-4..-2]`) כבר מלאים. כוון לבר הנכון.

**התיקון — בכיוון שהצעת (detection על החלון שמסתיים בבר המלא האחרון), תחת 4 תנאים מחייבים:**

1. **engine + inspector על אותו חלון-מלא.** ה-inspector (`s2_pattern_probe.py:81`) גם משתמש ב-`bars[-1]` כ-b4 אבל
   בזמן-שאילתה (b4 מלא יותר) ⇒ מראה "armed" בעוד ה-engine נכשל. תקן את **שניהם** לעבוד על אותו חלון
   (הבר האחרון המלא), אחרת ה-inspector ימשיך לשקר.
2. **שינוי כירורגי + emit עקבי.** רק קריאות ה-detection של 4-הברים (`:917 _detect_reactive`, `:919 _detect_initiative`,
   `:936+` chart-patterns) צריכות את החלון-המלא (`self._bar_buffer[:-1]`). **אל תיגע** ב-FHB/ATR (`:888-899`) ובספירת-הברים —
   הם צריכים את הבאפר המלא. ודא ש-entry/stop/targets (`:102 entry_price`) נגזרים מהבר-המלא, לא תערובת.
3. **flag-gated + regression.** דגל env (למשל `S2_DETECT_ON_CLOSED_BAR`, default-ON אחרי אימות; או OFF→ON עם אישור-Michael).
   טסט אנטי-טאוטולוגי: fixture שבו b4-חלקי נכשל בהתנהגות-הישנה ו**עובר** בחדשה (`if reverted → RED because b4 partial`).
4. **הוכח את הפרמיסה קודם (Rule 5).** הדבק **לוג-חי**: OHLC+vol של b4 ב-push-הראשון (זמן-detection) מול הערך הסופי של
   אותו בר — להוכיח שהוא באמת חלקי. (הקוד אומר "bridge pushes ~20x while building" → תומך, אבל צריך ראיה.)

⚠️ זה **fire-path / trading-logic** → strategic-stop + אישור-Michael לפני שמדליקים default-ON.
**הקשר:** גם אחרי הסרת chop+COT/AMT (היום), S2 לא יירה אם b4 תמיד חלקי. זה השכבה-העמוקה; שלושתם נחוצים יחד.

═══════════════════════════════════════════════════
## חלק B — להשלים את חקירת "למה לא ירה" (4 הגאפים מביקורת-Cowork)
═══════════════════════════════════════════════════
**א · עמודת "חוסם בחלון-ההזדמנות" ל-S4.** שחזר מ-`v9_bars_5min_woodies` + snapshots את החוסם **בתוך** חלונות-ה-trend
(BLUE 18:05-18:20 · RED 18:50-19:10), לא ה-GRAY של 20:10. למשל ZLR: "חלון RED: CCI 98.2-, פספס 100- ב-1.8".

**ב · ראיות Phase 0/2 גולמיות שלא נמסרו.** git log (commit לשינויי-Cowork) · 3 הטסטים החדשים GREEN
(`test_chop_gates_disabled` · `test_readiness_noncritical_s3_streams` · `test_s2_independent_of_s3`) · restart-verify
(`S2_CHOPPINESS_GATE`/`LAYER0_CHOP_GATE`/`S2_REQUIRE_COT_AMT` unset · readiness לא `dead: tick_reversal_15,tpo`) · 2 צילומי Build-Status.

**ג · סיבת-ה-DEGRADED.** הדבק את מערך `readiness.checks` המלא וסמן את ה-check שמוריד ל-DEGRADED (כנראה `opening_type=UNKNOWN`/imbalance) + סווג display/real.

**ד · טבלת near-misses לכיול** → `docs/reports/PATTERN_NEARMISS_2026-06-08.md`: **תבנית | סף | בפועל | פער** לכל תבנית armed.
**אל תשנה K** — רק תעד; Michael מאשר כיול.

═══════════════════════════════════════════════════
## חלק C — Pattern-Detection ב-Shadow tab, מקובץ לפי מערכת
═══════════════════════════════════════════════════
**אודיט קודם (KEEP/ADAPT/REPLACE):** `tabs/PatternsTab.tsx` · `build_tree/BuildTreeView.tsx` + `hooks/useBuildStatus.ts` · `tabs/TraderTab.tsx`/`TradeTab.tsx` (נושאי "Per-System P&L (SHADOW)" = ה-Shadow view). ודא איזה tab הוא "ה-Shadow".
**יישום:** בטאב ה-SHADOW פאנל **"זיהוי תבניות"** מקובץ לפי מערכת — **S2 · Five-Min** (10) · **S4 · Woodies** (9). לכל תבנית: שם · badge-סטטוס · **החוסם-היחיד** · תג **REAL/DISPLAY**. מקור: `useBuildStatus` הקיים (בלי backend חדש). רענון manual (מוסכמה קיימת). S3-מושתק לא יוצג כאדום — "disabled (S3_MUTE)" נפרד או מוסתר.
**+ ניקוי-frontend (מהפרומפט הקודם):** day_type לא יוצג עם סף-זרם-360s/"Sierra תקוע" (observer); זרמים מושתקים/לא-מחווטים לא אדומים-BLOCKED; הסר סתירת "● חי"↔"תקוע".

## Acceptance Criteria (בינארי ✓/✗)
- [ ] A: detection על בר-מלא (engine+inspector) · flag+regression (RED-on-revert) · לוג-חי שמוכיח b4-חלקי · emit עקבי · FHB/ATR לא נגעו.
- [ ] B: עמודת-א · ראיות Phase 0/2 גולמיות · readiness.checks+סיבת-DEGRADED · near-miss table.
- [ ] C: פאנל "זיהוי תבניות" בטאב SHADOW מקובץ S2/S4 + אודיט אנטי-כפילות + ניקוי day_type/זרמים-מושתקים. צילום.

## NOT-DONE (חובה) + מה Cowork יבקר
מסור: לוג-b4 חי · git log · raw 3 טסטים+restart · עמודת-א · readiness.checks · near-miss · צילומי SHADOW.
**Cowork יצליב (Rule 5):** שהפרמיסה (b4-חלקי) הוכחה בדאטה-חי · ש-engine+inspector אותו חלון · שה-emit לא התפצל · שעמודת-א מהיסטוריה אמיתית · שפאנל-SHADOW לא משכפל PatternsTab.
